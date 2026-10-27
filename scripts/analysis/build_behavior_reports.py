#!/usr/bin/env python3
"""Build per-output Markdown, CSV and gnuplot histories from qe_behavior JSON."""
import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

RY_EV = 13.605693122994
FORCE_FACTOR = RY_EV / 0.529177210903


def write_csv(path, rows, compressed=False):
    if not rows:
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    handle = io.TextIOWrapper(gzip.GzipFile(filename=str(path), mode="wb", mtime=0), newline="") if compressed else open(path, "wt", newline="")
    with handle:
        w = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def plot_commands(title, output, electronic, ionic):
    # Data columns: observed iteration, relative cycle energy, accuracy;
    # force evaluation, relative run energy, max atomic force, total force, BFGS.
    edata = [row.split() for row in electronic.splitlines() if row.strip()]
    idata = [row.split() for row in ionic.splitlines() if row.strip()]
    energy_present = any(row[1] != "NaN" for row in edata)
    accuracy_values = [float(row[2]) for row in edata if row[2] != "NaN" and float(row[2]) > 0]
    ionic_energy_present = any(row[1] != "NaN" for row in idata)
    steps_present = any(row[4] != "NaN" for row in idata)
    force_present = any(row[2] != "NaN" or row[3] != "NaN" for row in idata)
    gp = ["reset", "set terminal pngcairo size 1440,1040 enhanced font 'Helvetica,13'",
          "set output " + quote(output), "set encoding utf8",
          "set multiplot layout 2,2 rowsfirst title " + quote(title),
          "set grid back lc rgb '#e1e5e9'", "set border 3", "set tics nomirror",
          "set key outside top center horizontal", "set datafile missing 'NaN'",
          "$Electronic << EOD", electronic, "EOD", "$Ionic << EOD", ionic, "EOD",
          "set title 'Electronic energy history'", "set xlabel 'Observed electronic iteration (cycles separated)'",
          "set ylabel 'E - last printed E in same cycle (eV)'", "set format y '%g'"]
    if energy_present:
        gp += ["plot $Electronic using 1:2 with lines lw 1.6 lc rgb '#245c8a' notitle"]
    else:
        gp += ["set xrange [0:1]", "set yrange [0:1]", "set label 1 'No inner SCF trace in this source' at graph 0.1,0.5", "plot NaN notitle", "unset label 1", "set autoscale"]
    gp += ["set title 'Electronic convergence estimate'", "set ylabel 'Printed estimated SCF accuracy (Ry)'",
           "set logscale y", "set format y '10^{%L}'"]
    # Explicit ranges allow missing/printed-zero estimates without a plot error.
    if accuracy_values:
        gp += ["set yrange [%g:%g]" % (min(accuracy_values)*0.5, max(accuracy_values)*2),
               "plot $Electronic using 1:($3>0?$3:1/0) with lines lw 1.4 lc rgb '#245c8a' notitle"]
    else:
        gp += ["set xrange [0:1]", "set yrange [1e-12:1]", "set label 1 'No positive printed estimate' at graph 0.1,0.5", "plot NaN notitle", "unset label 1", "set autoscale x"]
    gp += ["unset logscale y", "set autoscale", "set format y '%g'",
           "set title 'Ionic energy and reported optimizer steps'",
           "set xlabel 'Force evaluation within this output (includes trials)'",
           "set ylabel 'E - first evaluated E in same run (eV)'",
           "set y2label 'Reported BFGS step after evaluation'", "set y2tics", "set ytics nomirror"]
    if ionic_energy_present:
        gp += ["set y2range [0:*]" if steps_present else "set y2range [0:1]"]
        command = "plot $Ionic using 1:2 with linespoints pt 7 ps 0.35 lw 1.4 lc rgb '#245c8a' title 'Energy'"
        if steps_present:
            command += ", $Ionic using 1:5 axes x1y2 with steps lw 1.3 dt 2 lc rgb '#777777' title 'BFGS step'"
        gp.append(command)
    else:
        gp += ["set xrange [0:1]", "set yrange [0:1]", "set y2range [0:1]", "set label 1 'No complete printed force evaluation' at graph 0.08,0.5", "plot NaN notitle", "unset label 1", "set autoscale"]
    gp += ["unset y2tics", "unset y2label", "set title 'Force evolution'",
           "set ylabel 'Printed force magnitude (eV/Å)'", "set xlabel 'Force evaluation within this output'",
           "set key outside top center horizontal"]
    if force_present:
        gp += ["plot $Ionic using 1:3 with linespoints pt 7 ps 0.35 lw 1.4 lc rgb '#b54a35' title 'Max atomic norm', $Ionic using 1:4 with lines lw 1.3 lc rgb '#8b6b24' title 'QE Total force'"]
    else:
        gp += ["set xrange [0:1]", "set yrange [0:1]", "plot NaN notitle", "set autoscale"]
    gp += ["unset multiplot", "unset output"]
    return "\n".join(gp) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--family", choices=["tau", "angles"], required=True)
    p.add_argument("--plots", action="store_true")
    args = p.parse_args()
    repo = args.repo.resolve()
    dest = repo / "behavior"
    dest.mkdir(exist_ok=True)
    bundle = json.load(gzip.open(args.bundle, "rt"))
    inventory = json.loads(args.inventory.read_text())
    remote = {f["relative_path"]: f for f in inventory["files"]}
    include = lambda path: path.startswith("commensurate/") if args.family == "angles" else not path.startswith("commensurate/")
    catalog = []
    all_gp = []
    parsed = set()
    iteration_count = force_count = 0
    for record in bundle["records"]:
        source = record["source_relative_path"]
        if not include(source):
            continue
        if source not in remote or remote[source]["sha256"] != record["source_sha256"] or not record["source_stable"]:
            raise ValueError("Source does not match NERSC inventory: " + source)
        parsed.add(source)
        ident = hashlib.sha256(source.encode()).hexdigest()[:16]
        folder = dest / "calculations" / ident
        folder.mkdir(parents=True, exist_ok=True)
        its = record["electronic_iterations"]
        fs = record["force_evaluations"]
        iteration_count += len(its)
        force_count += len(fs)
        write_csv(folder / "electronic_iterations.csv.gz", its, True)
        write_csv(folder / "scf_cycles.csv", record["cycles"])
        write_csv(folder / "force_evaluations.csv", fs)
        write_csv(folder / "optimizer_events.csv", record["optimizer_events"])
        (folder / "manifest.json").write_text(json.dumps({k: v for k, v in record.items() if k not in ["electronic_iterations", "cycles", "force_evaluations", "optimizer_events"]}, indent=2) + "\n")
        last_energy = {i["cycle_id"]: i["energy_Ry"] for i in its if i["energy_Ry"] is not None}
        electronic = []
        previous = None
        for i in its:
            if previous != (i["run_id"], i["cycle_id"]):
                electronic.append("")
            e = (i["energy_Ry"] - last_energy[i["cycle_id"]])*RY_EV if i["energy_Ry"] is not None else None
            electronic.append("%d %s %s" % (i["observed_iteration"], e if e is not None else "NaN", i["scf_accuracy_Ry"] if i["scf_accuracy_Ry"] is not None else "NaN"))
            previous = (i["run_id"], i["cycle_id"])
        first = {}
        ionic = []
        previous = None
        for f in fs:
            if f["run_id"] != previous:
                ionic.append("")
            if f["energy_Ry"] is not None:
                first.setdefault(f["run_id"], f["energy_Ry"])
            e = (f["energy_Ry"]-first[f["run_id"]])*RY_EV if f["energy_Ry"] is not None else None
            ionic.append(" ".join(str(x) if x is not None else "NaN" for x in [f["force_evaluation"], e, f["max_printed_atomic_force_eV_A"], f["qe_total_force_Ry_Bohr"]*FORCE_FACTOR, f["reported_bfgs_step_after"]]))
            previous = f["run_id"]
        title = (Path(source).parent.name + " / " + Path(source).name).replace("_", " ")
        if len(title) > 135:
            title = title[:132] + "..."
        if args.plots:
            all_gp.append(plot_commands(title, folder / "history.png", "\n".join(electronic), "\n".join(ionic)))
        summary = record["summary"]
        latest_run = record["runs"][-1] if record["runs"] else {}
        latest_energies = [i["energy_Ry"] for i in its if i["run_id"] == latest_run.get("run_id") and i["energy_Ry"] is not None]
        latest_forces = [f for f in fs if f["run_id"] == latest_run.get("run_id")]
        last_force = latest_forces[-1] if latest_forces else {}
        latest_cycle = record["cycles"][-1] if record["cycles"] else {}
        values = [("Latest electronic-cycle outcome", latest_cycle.get("outcome", "Unavailable")),
                  ("First printed total energy in latest run (Ry)", latest_energies[0] if latest_energies else "Unavailable"),
                  ("Last printed total energy in latest run (Ry)", latest_energies[-1] if latest_energies else "Unavailable"),
                  ("Last maximum printed atomic-force norm (eV/Å)", last_force.get("max_printed_atomic_force_eV_A", "Unavailable")),
                  ("Last QE Total force (Ry/Bohr)", last_force.get("qe_total_force_Ry_Bohr", "Unavailable")),
                  ("Final reported BFGS steps", latest_run.get("final_reported_bfgs_steps", "No final convergence counter printed")),
                  ("Latest program run reached JOB DONE", latest_run.get("job_done", False)),
                  ("Latest program run has runtime error / time limit", str(latest_run.get("error", False)) + " / " + str(latest_run.get("time_limit", False)))]
        page = ["# SCF and relaxation behavior", "", "Source: `"+source+"`", "",
                "SHA-256: `"+record["source_sha256"]+"` (matches the NERSC inventory).", "",
                "%d observed electronic iterations; %d SCF cycles; %d force evaluations." % (len(its), len(record["cycles"]), len(fs)), "",
                "![Energy, electronic convergence, force and optimizer histories](history.png)" if args.plots else "",
                "", "## Latest run: printed values", "", "| Quantity | Value |", "| --- | --- |"]
        page += ["| "+key+" | "+str(value)+" |" for key, value in values]
        page += ["", "## Download exact histories", "",
                "- [Electronic iterations](electronic_iterations.csv.gz): printed QE iteration number, total energy in Ry, estimated SCF accuracy and source lines. Restart numbering is preserved.",
                "- [SCF cycle outcomes](scf_cycles.csv): converged, not converged or unfinished, separately for every electronic cycle."]
        if fs:
            page.append("- [Force evaluations](force_evaluations.csv): QE total force, printed atomic-force maximum/RMS, SCF force correction, energy and associated cycle.")
        if record["optimizer_events"]:
            page.append("- [Reported optimizer steps](optimizer_events.csv): BFGS/SCF counters and convergence messages at their original source lines.")
        page += ["", "Force evaluations include trial geometries and are not automatically accepted optimizer steps. The BFGS counter can continue from an earlier restart; no unprinted steps are invented. Curves stop at file/run/cycle boundaries as applicable.", "",
                 "Forces are retained only where QE printed a complete force evaluation; they are not interpolated between electronic iterations. High-verbosity component-force blocks are excluded from the total atomic-force statistics. Printed zero SCF estimates are not shown on the logarithmic axis.", "",
                 "Electronic energies follow the convention printed by QE (including its smearing/free-energy convention). Relative energies are within a single cycle/run, never comparisons between different cells. A final plotted value is not by itself evidence of convergence."]
        (folder / "README.md").write_text("\n".join(page) + "\n")
        catalog.append(dict(source_relative_path=source, source_sha256=record["source_sha256"],
                            history_status="EXTRACTED_HASH_MATCH", electronic_iterations=len(its),
                            scf_cycles=len(record["cycles"]), force_evaluations=len(fs),
                            report="calculations/"+ident+"/README.md"))
    for source, live in sorted(remote.items()):
        if include(source) and source not in parsed and any(live.get("marker_counts", {}).values()):
            catalog.append(dict(source_relative_path=source, source_sha256=live["sha256"],
                                history_status="RAW_TEXT_HISTORY_NOT_COLLECTED", electronic_iterations="",
                                scf_cycles="", force_evaluations="", report=""))
    catalog.sort(key=lambda row: row["source_relative_path"])
    write_csv(dest / "calculation_index.csv", catalog)
    stage_c_pages = []
    if args.family == "tau":
        for steps in sorted((repo / "data/stage_c_fixed_registry").glob("tau*/steps.csv")):
            tau = steps.parent.name
            rows = list(csv.DictReader(steps.open()))
            manifest = json.loads((steps.parent / "manifest.json").read_text())
            folder = dest / "stage_c_exports" / tau
            folder.mkdir(parents=True, exist_ok=True)
            base = float(rows[0]["energy_eV"])
            data = "\n".join("%s %.12g %s %s" % (r["step"], float(r["energy_eV"])-base, r["raw_fmax_eV_A"], r["projected_fmax_eV_A"]) for r in rows)
            if args.plots:
                all_gp.append("\n".join([
                    "reset", "set terminal pngcairo size 1440,720 enhanced font 'Helvetica,14'",
                    "set output " + quote(folder / "history.png"),
                    "set multiplot layout 1,2 title " + quote(tau + " / Stage C fixed-registry FIRE"),
                    "set grid back", "set border 3", "set tics nomirror", "$Fire << EOD", data, "EOD",
                    "set xlabel 'Recorded FIRE step'", "set ylabel 'E - first recorded E (eV)'",
                    "plot $Fire using 1:2 with linespoints pt 7 ps 0.6 lw 1.8 lc rgb '#245c8a' notitle",
                    "set ylabel 'Maximum force norm (eV/Å)'", "set key outside top center",
                    "plot $Fire using 1:3 with lines lw 1.8 lc rgb '#b54a35' title 'Raw DFT', $Fire using 1:4 with lines lw 1.8 lc rgb '#245c8a' title 'Projected optimizer', " + str(manifest["fmax_target_eV_A"]) + " with lines dt 2 lc rgb '#777777' title 'Projected-force target'",
                    "unset multiplot", "unset output"]) + "\n")
            (folder / "README.md").write_text("# " + tau + " — Stage C behavior\n\n"
                "![Energy and raw/projected force histories](history.png)\n\n"
                "[Exact step data](../../../data/stage_c_fixed_registry/" + tau + "/steps.csv) · "
                "[Source manifest](../../../data/stage_c_fixed_registry/" + tau + "/manifest.json)\n\n"
                "The x axis is the recorded FIRE step. Raw DFT forces and projected optimizer forces remain distinct; only the projected force is compared with the optimizer target. No inner electronic-iteration history is available from these step CSVs.\n")
            stage_c_pages.append("- [" + tau + ": FIRE energy and forces](stage_c_exports/" + tau + "/README.md)")
    index = ["# SCF energy, force and relaxation behavior", "",
             "One record per exact output branch. Raw source hashes match the dated NERSC inventory. Electronic iterations, force evaluations and reported optimizer steps are separate quantities.", "",
             "Current coverage: **%d output histories, %d electronic iterations, %d force evaluations**." % (len(parsed), iteration_count, force_count), "",
             "The inventory alone cannot reconstruct iteration energies. Rows marked `RAW_TEXT_HISTORY_NOT_COLLECTED` require the read-only history collector; they are not fabricated from final energies.", "",
             "[Complete coverage index](calculation_index.csv)", ""]
    if args.family == "tau":
        point_dir = dest / "tau_points"
        point_dir.mkdir(exist_ok=True)
        index += ["## Browse by tau point", "",
                  " · ".join("[tau%02d](tau_points/tau%02d.md)" % (i, i) for i in range(100)), ""]
        report_by_source = {r["source_relative_path"]: r["report"] for r in catalog if r["report"]}
        for i in range(100):
            tau = "tau%02d" % i
            page = ["# " + tau + " — calculation behavior", "",
                    "Each output branch remains separate. The same tau label in a different constraint family is not the same calculation.", ""]
            for stage, directory in [("A: rigid SCF", "stage_a_rigid"), ("B: vertical relaxation", "vertical_relax")]:
                manifest_path = repo / "data" / directory / tau / "manifest.json"
                if manifest_path.is_file():
                    m = json.loads(manifest_path.read_text())
                    source = m.get("source_relative_path", tau + "/" + m["source_output"])
                    report = report_by_source.get(source)
                    page += ["## " + stage, "", "Selected output: `" + source + "`", "",
                             "[Energy, force and step histories](../"+report+")" if report else "Inner electronic-iteration trace is not collected yet. The existing final dataset is not a substitute for that trace.", ""]
            if (dest / "stage_c_exports" / tau / "README.md").is_file():
                page += ["## C: fixed-registry FIRE", "", "[Recorded FIRE energy and raw/projected force histories](../stage_c_exports/"+tau+"/README.md)", ""]
            page += ["## Other collected output branches", ""]
            for row in catalog:
                if row["report"] and re.search(r"(?:^|/)"+tau+r"/", row["source_relative_path"]):
                    page.append("- ["+row["source_relative_path"]+"](../"+row["report"]+")")
            (point_dir / (tau+".md")).write_text("\n".join(page)+"\n")
    else:
        angle_dir = dest / "angles"
        angle_dir.mkdir(exist_ok=True)
        index += ["## Browse by twist angle", ""]
        for angle in ["53p13", "36p87", "28p07", "22p62", "18p92", "16p26", "14p25", "12p68", "11p42", "09p53"]:
            matching = [r for r in catalog if "/theta_"+angle+"_" in r["source_relative_path"]]
            page = ["# " + angle.replace("p", ".") + "° — SCF and relaxation behavior", "",
                    "Each source output has its own energy, force and optimizer history. Output filenames are not a validated restart chronology.", "",
                    "| Exact output branch | History |", "| --- | --- |"]
            for row in matching:
                page.append("| `"+row["source_relative_path"]+"` | "+("[Plots and data](../"+row["report"]+")" if row["report"] else "History collection pending")+" |")
            (angle_dir / (angle+".md")).write_text("\n".join(page)+"\n")
            index.append("- ["+angle.replace("p", ".")+"°](angles/"+angle+".md)")
        index.append("")
    if stage_c_pages:
        index += ["## Existing Stage C exports", ""] + stage_c_pages + [""]
    index += ["## QE output histories", "", "| Output branch | History |", "| --- | --- |"]
    for row in catalog:
        index.append("| `"+row["source_relative_path"]+"` | "+("[Plots and data]("+row["report"]+")" if row["report"] else "History collection pending")+" |")
    (dest / "README.md").write_text("\n".join(index)+"\n")
    (dest / "coverage.json").write_text(json.dumps(dict(extracted_outputs=len(parsed), electronic_iterations=iteration_count,
        force_evaluations=force_count, pending_outputs=sum(not row["report"] for row in catalog),
        source_inventory_sha256=hashlib.sha256(args.inventory.read_bytes()).hexdigest()), indent=2)+"\n")
    if args.plots:
        if not shutil.which("gnuplot"):
            raise RuntimeError("gnuplot is required for --plots")
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "histories.gp"
            script.write_text("\n".join(all_gp))
            result = subprocess.run(["gnuplot", str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode:
                raise RuntimeError(result.stderr.decode(errors="replace")[-4000:])
    print((dest / "coverage.json").read_text())


if __name__ == "__main__":
    main()
