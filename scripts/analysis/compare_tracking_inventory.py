#!/usr/bin/env python3
"""Compare a read-only NERSC inventory with the tracked tau release."""
import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[2]


def completion_markers_ok(record, relaxation=False):
    if not record or record.get("read_status") != "OK":
        return False
    m = record.get("marker_counts", {})
    required = ["job_done", "scf_converged"]
    if relaxation:
        required += ["bfgs_converged", "end_bfgs", "final_coordinates_begin",
                     "final_coordinates_end"]
    return (all(m.get(k, 0) > 0 for k in required) and
            not any(m.get(k, 0) for k in ["scf_failed", "time_limit", "qe_error"]))


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text())
    expected_root = "/pscratch/sd/a/anita14b/SAM/STO/bilayer/twist/grid/10x10"
    files = {f["relative_path"]: f for f in inventory["files"] if f["root"] == expected_root}
    if not files or inventory["errors"]:
        raise ValueError("Expected root is empty or scan errors require review")
    args.output.mkdir(parents=True, exist_ok=True)
    sources = []
    for stage, folder in [("A", "stage_a_rigid"), ("B", "vertical_relax")]:
        for path in sorted((REPO / "data" / folder).glob("*/manifest.json")):
            m = json.loads(path.read_text())
            relative = m.get("source_relative_path", path.parent.name + "/" + m["source_output"])
            live = files.get(relative)
            match = bool(live and live.get("read_status") == "OK" and
                         live.get("sha256") == m["source_sha256"])
            sources.append(dict(stage=stage, tau=path.parent.name,
                                source_relative_path=relative,
                                expected_sha256=m["source_sha256"],
                                observed_sha256=live.get("sha256", "") if live else "",
                                hash_status="MATCH" if match else "REVIEW_REQUIRED",
                                completion_markers_ok=completion_markers_ok(live, stage == "B")))
    write_csv(args.output / "tau_source_verification.csv", sources)

    stage_c = []
    for relative, live in sorted(files.items()):
        match = re.fullmatch(r"(tau\d\d)/(stage_c[^/]+)/status.json", relative)
        if not match:
            continue
        tau, run = match.groups()
        local = REPO / "data/stage_c_fixed_registry" / tau / "manifest.json"
        status = live.get("stage_c_status", {})
        stage_c.append(dict(tau=tau, remote_run=run,
                            remote_status_converged=status.get("converged") is True,
                            remote_fire_steps=status.get("steps", ""),
                            git_compact_dataset_present=local.is_file(),
                            export_review_status="EXISTING_EXPORT" if local.is_file()
                            else "MISSING_EXPORT_REQUIRES_CHECKPOINT_VALIDATION",
                            status_relative_path=relative, status_sha256=live["sha256"]))
    write_csv(args.output / "stage_c_remote_status.csv", stage_c)

    definition_c = []
    for relative, live in sorted(files.items()):
        match = re.fullmatch(r"tau_definition_comparison_all/(equal_weight|mass_weighted)/stage_c_(tau\d\d)/status.json", relative)
        if match:
            family, tau = match.groups()
            status = live.get("stage_c_status", {})
            definition_c.append(dict(family=family, tau=tau,
                                     remote_status_converged=status.get("converged") is True,
                                     remote_fire_steps=status.get("steps", ""),
                                     status_relative_path=relative, status_sha256=live["sha256"],
                                     export_review_status="SEPARATE_CONSTRAINT_FAMILY_REQUIRES_VALIDATION"))
    write_csv(args.output / "definition_comparison_stage_c_status.csv", definition_c)

    newer = []
    for family in ["tau_equal_defined", "tau_mass_defined"]:
        for i in range(100):
            tau = "tau%02d" % i
            prefix = family + "/" + tau + "/"
            for stage in ["A", "B"]:
                records = [f for path, f in files.items()
                           if path.startswith(prefix) and "marker_counts" in f
                           and ((stage == "A" and Path(path).name == "sto_bi_" + tau + ".scf.out")
                                or (stage == "B" and re.fullmatch(
                                    r"sto_bi_" + tau + r"\.vertical_relax.*\.out", Path(path).name)))]
                passing = sorted(f["relative_path"] for f in records
                                 if completion_markers_ok(f, stage == "B"))
                newer.append(dict(family=family, tau=tau, stage=stage,
                                  output_files_seen=len(records),
                                  completion_markers_ok=bool(passing),
                                  candidate_outputs=";".join(passing),
                                  dataset_status="NOT_EXPORTED_NOT_YET_LABEL_VALIDATED"))
    write_csv(args.output / "newer_tau_branch_status.csv", newer)

    newer_files = []
    stage_c_files = []
    for relative, live in sorted(files.items()):
        if re.match(r"tau_(equal|mass)_defined/tau\d\d/", relative):
            newer_files.append(dict(relative_path=relative, bytes=live["bytes"],
                                    sha256=live.get("sha256", ""), read_status=live["read_status"],
                                    input_settings=json.dumps(live.get("input_settings", {}), sort_keys=True),
                                    marker_counts=json.dumps(live.get("marker_counts", {}), sort_keys=True)))
        if re.match(r"tau\d\d/stage_c[^/]+/", relative):
            stage_c_files.append(dict(relative_path=relative, bytes=live["bytes"],
                                      sha256=live.get("sha256", ""), read_status=live["read_status"]))
    write_csv(args.output / "newer_tau_files.csv", newer_files)
    write_csv(args.output / "stage_c_run_files.csv", stage_c_files)

    jobs = []
    for scheduler in inventory["scheduler"]:
        if scheduler["argv"][0] == "sacct" and scheduler.get("returncode") == 0:
            jobs = list(csv.DictReader(io.StringIO(scheduler["stdout"]), delimiter="|"))
    account_history_rows = len(jobs)
    jobs = [j for j in jobs if j.get("WorkDir", "").startswith(expected_root + "/")
            or j.get("WorkDir") == expected_root]
    write_csv(args.output / "scheduler_jobs.csv", jobs)
    metadata = dict(
        inventory_sha256=hashlib.sha256(args.inventory.read_bytes()).hexdigest(),
        inventory_host=inventory["host"], captured_utc=inventory["finished_utc"],
        roots=inventory["roots"], files_recorded=len(inventory["files"]),
        read_status_counts=dict(collections.Counter(f["read_status"] for f in inventory["files"])),
        source_hash_counts=dict(collections.Counter(r["hash_status"] for r in sources)),
        original_stage_c_remote_converged=sum(r["remote_status_converged"] for r in stage_c),
        original_stage_c_missing_exports=[r["tau"] for r in stage_c
                                         if r["remote_status_converged"] and not r["git_compact_dataset_present"]],
        newer_families={family: {stage: sum(r["completion_markers_ok"] for r in newer
                                           if r["family"] == family and r["stage"] == stage)
                                for stage in ["A", "B"]}
                        for family in ["tau_equal_defined", "tau_mass_defined"]},
        scheduler_account_history_rows=account_history_rows,
        scheduler_history_rows=len(jobs),
        scheduler_history_state_counts=dict(collections.Counter(j["State"] for j in jobs)),
        limitations=["Markers do not validate energy/force frame alignment or physical accuracy",
                     "Stage C checkpoint binaries and trajectory contents were not collected",
                     "Only the listed root was scanned; moved or other-cluster runs are outside coverage"])
    (args.output / "verification_summary.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
