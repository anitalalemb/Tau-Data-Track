#!/usr/bin/env python3
"""Extract printed QE energy/force/optimizer histories; Python 3.6 compatible."""
import argparse
import datetime
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

FLOAT = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][-+]?\d+)?"
RY_EV = 13.605693122994
BOHR_A = 0.529177210903
FORCE_FACTOR = RY_EV / BOHR_A


def number(value):
    return float(value.replace("D", "E").replace("d", "e"))


def parse_output(path, relative_path=None):
    path = Path(path)
    before = path.stat()
    raw = path.read_bytes()
    lines = raw.decode("utf-8", errors="replace").splitlines()
    record = dict(source_relative_path=relative_path or path.name,
                  source_sha256=hashlib.sha256(raw).hexdigest(), source_bytes=len(raw),
                  electronic_iterations=[], cycles=[], force_evaluations=[], optimizer_events=[], runs=[])
    iterations = record["electronic_iterations"]
    cycles = record["cycles"]
    forces = record["force_evaluations"]
    events = record["optimizer_events"]
    run = None
    cycle = None
    iteration = None
    atom_forces = None
    collecting_total_forces = False
    nat = None

    def ensure_run(line):
        nonlocal run
        if run is None:
            run = dict(run_id=len(record["runs"]) + 1, source_line=line,
                       job_done=False, error=False, time_limit=False, bfgs_converged=False)
            record["runs"].append(run)

    def new_cycle(line):
        nonlocal cycle, iteration
        ensure_run(line)
        cycle = dict(cycle_id=len(cycles) + 1, run_id=run["run_id"], source_line=line,
                     outcome="UNFINISHED", first_printed_iteration=None,
                     last_printed_iteration=None, reported_iterations=None)
        cycles.append(cycle)
        iteration = None

    for line_no, line in enumerate(lines, 1):
        low = line.lower()
        if re.search(r"\bProgram PWSCF\b", line):
            run = None
            ensure_run(line_no)
            cycle = None
            iteration = None
            nat = None
            atom_forces = None
            collecting_total_forces = False
        match = re.search(r"number of atoms/cell\s*=\s*(\d+)", line, re.I)
        if match:
            nat = int(match[1])
        if re.match(r"\s*Self-consistent Calculation\s*$", line, re.I):
            new_cycle(line_no)
        match = re.match(r"\s*iteration\s*#\s*(\d+)", line, re.I)
        if match:
            n = int(match[1])
            if cycle is None or cycle["outcome"] != "UNFINISHED":
                new_cycle(line_no)
            iteration = dict(run_id=run["run_id"], cycle_id=cycle["cycle_id"],
                             observed_iteration=len(iterations) + 1, qe_iteration=n,
                             source_line=line_no, energy_Ry=None, energy_line=None,
                             scf_accuracy_Ry=None, accuracy_line=None,
                             final_energy_marker=False)
            iterations.append(iteration)
            if cycle["first_printed_iteration"] is None:
                cycle["first_printed_iteration"] = n
            cycle["last_printed_iteration"] = n
        match = re.match(r"\s*(!?)\s*total energy\s*=\s*(" + FLOAT + r")\s+Ry", line, re.I)
        if match and iteration is not None:
            iteration.update(energy_Ry=number(match[2]), energy_line=line_no,
                             final_energy_marker=bool(match[1]))
        match = re.search(r"estimated scf accuracy\s*<\s*(" + FLOAT + r")\s+Ry", line, re.I)
        if match and iteration is not None:
            iteration.update(scf_accuracy_Ry=number(match[1]), accuracy_line=line_no)
        if cycle is not None and "convergence has been achieved" in low:
            cycle["outcome"] = "CONVERGED"
            cycle["outcome_line"] = line_no
            match = re.search(r"in\s+(\d+)\s+iterations", line, re.I)
            cycle["reported_iterations"] = int(match[1]) if match else None
        if cycle is not None and "convergence not achieved" in low:
            cycle["outcome"] = "NOT_CONVERGED"
            cycle["outcome_line"] = line_no
        if "forces acting on atoms" in low and ("ry/au" in low or "ry/bohr" in low):
            ensure_run(line_no)
            atom_forces = []
            collecting_total_forces = True
        match = re.match(r"\s*atom\s+(\d+)\s+type\s+\d+\s+force\s*=\s*(" + FLOAT + r")\s+(" + FLOAT + r")\s+(" + FLOAT + r")", line, re.I)
        if match and collecting_total_forces:
            # QE verbosity=high subsequently prints component force blocks;
            # only the first sequential block after the total-force header counts.
            if int(match[1]) == len(atom_forces) + 1:
                atom_forces.append([number(match[i]) for i in [2, 3, 4]])
                if nat is not None and len(atom_forces) == nat:
                    collecting_total_forces = False
            else:
                collecting_total_forces = False
        elif collecting_total_forces and atom_forces and line.strip():
            collecting_total_forces = False
        match = re.search(r"\bTotal force\s*=\s*(" + FLOAT + r")", line, re.I)
        if match:
            ensure_run(line_no)
            complete = bool(atom_forces and nat is not None and len(atom_forces) == nat)
            norms = [math.sqrt(sum(x*x for x in vector)) for vector in atom_forces] if complete else []
            correction = re.search(r"Total SCF correction\s*=\s*(" + FLOAT + r")", line, re.I)
            energy = iteration["energy_Ry"] if iteration else None
            force = dict(run_id=run["run_id"], cycle_id=cycle["cycle_id"] if cycle else None,
                         force_evaluation=len(forces) + 1, source_line=line_no,
                         energy_Ry=energy, energy_line=iteration["energy_line"] if iteration else None,
                         electronic_outcome=cycle["outcome"] if cycle else "UNKNOWN",
                         qe_total_force_Ry_Bohr=number(match[1]),
                         qe_scf_force_correction_Ry_Bohr=number(correction[1]) if correction else None,
                         atom_count_expected=nat, atom_count_read=len(atom_forces or []),
                         max_printed_atomic_force_eV_A=max(norms)*FORCE_FACTOR if norms else None,
                         rms_printed_atomic_force_eV_A=math.sqrt(sum(n*n for n in norms)/len(norms))*FORCE_FACTOR if norms else None,
                         reported_bfgs_step_after=None, reported_scf_cycles_after=None,
                         force_correction_warning=False)
            forces.append(force)
            atom_forces = None
            collecting_total_forces = False
        if "scf correction compared to forces is large" in low and forces:
            forces[-1]["force_correction_warning"] = True
        for key, pattern in [("reported_bfgs_step", r"number of bfgs steps\s*=\s*(\d+)"),
                             ("reported_scf_cycles", r"number of scf cycles\s*=\s*(\d+)")]:
            match = re.search(pattern, line, re.I)
            if match:
                ensure_run(line_no)
                events.append(dict(run_id=run["run_id"], source_line=line_no,
                                   event=key, value=int(match[1]),
                                   preceding_force_evaluation=forces[-1]["force_evaluation"] if forces and forces[-1]["run_id"] == run["run_id"] else None))
                if forces and forces[-1]["run_id"] == run["run_id"]:
                    forces[-1][key + "_after"] = int(match[1])
        if "bfgs converged" in low:
            ensure_run(line_no)
            run["bfgs_converged"] = True
            events.append(dict(run_id=run["run_id"], source_line=line_no,
                               event="bfgs_converged", value=line.strip(),
                               preceding_force_evaluation=forces[-1]["force_evaluation"] if forces else None))
            counts = re.search(r"bfgs converged in\s+(\d+)\s+scf cycles and\s+(\d+)\s+bfgs steps", line, re.I)
            if counts:
                run.update(final_reported_scf_cycles=int(counts[1]),
                           final_reported_bfgs_steps=int(counts[2]))
                if forces and forces[-1]["run_id"] == run["run_id"]:
                    forces[-1].update(reported_scf_cycles_after=int(counts[1]),
                                      reported_bfgs_step_after=int(counts[2]))
        if "job done." in low:
            ensure_run(line_no)
            run["job_done"] = True
        if "error in routine" in low:
            ensure_run(line_no)
            run["error"] = True
        if "maximum cpu time exceeded" in low:
            ensure_run(line_no)
            run["time_limit"] = True
    after = path.stat()
    record["source_stable"] = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    record["summary"] = dict(observed_iterations=len(iterations), scf_cycles=len(cycles),
                             converged_cycles=sum(c["outcome"] == "CONVERGED" for c in cycles),
                             force_evaluations=len(forces), optimizer_events=len(events),
                             last_run=record["runs"][-1] if record["runs"] else None)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default="/pscratch/sd/a/anita14b/SAM/STO/bilayer/twist/grid/10x10")
    p.add_argument("--local-map", type=Path)
    p.add_argument("--gzip", action="store_true")
    p.add_argument("--max-file-mib", type=int, default=128)
    args = p.parse_args()
    if args.local_map:
        pairs = sorted(json.loads(args.local_map.read_text()).items())
    else:
        root = Path(args.root)
        if not root.is_dir():
            raise SystemExit("Calculation root is missing: " + str(root))
        pairs = []
        for directory, subdirs, names in os.walk(root, followlinks=False):
            subdirs[:] = sorted(d for d in subdirs if not (d.startswith(("tmp", ".", "__pycache__"))
                                or d.endswith(".save") or d == "scratch"
                                or (Path(directory)/d).is_symlink()))
            for name in sorted(names):
                path = Path(directory)/name
                if re.search(r"\.out\d*$", name, re.I) and not path.is_symlink():
                    pairs.append((path.relative_to(root).as_posix(), str(path)))
    stream = gzip.GzipFile(fileobj=sys.stdout.buffer, mode="wb", mtime=0) if args.gzip else sys.stdout.buffer
    def emit(value):
        stream.write(value.encode("utf-8"))
    emit('{"schema_version":1,"captured_utc":' + json.dumps(datetime.datetime.now(datetime.timezone.utc).isoformat()) + ',"records":[')
    first = True
    errors = []
    for processed, (relative, path) in enumerate(pairs, 1):
        if processed == 1 or processed % 50 == 0:
            print("Reading QE output %d/%d" % (processed, len(pairs)), file=sys.stderr, flush=True)
        try:
            if Path(path).stat().st_size > args.max_file_mib*1024**2:
                errors.append(dict(source_relative_path=relative, error="SIZE_LIMIT"))
                continue
            record = parse_output(path, relative)
            if not record["electronic_iterations"] and not record["force_evaluations"]:
                continue
            if not first:
                emit(",")
            emit(json.dumps(record, separators=(",", ":")))
            first = False
        except (OSError, ValueError) as exc:
            errors.append(dict(source_relative_path=relative, error=str(exc)))
    emit('],"errors":' + json.dumps(errors) + '}\n')
    if args.gzip:
        stream.close()


if __name__ == "__main__":
    main()
