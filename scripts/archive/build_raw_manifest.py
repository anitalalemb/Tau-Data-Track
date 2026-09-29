#!/usr/bin/env python3
"""Create a portable inventory of raw data without copying the raw files."""

from pathlib import Path
import argparse
import csv
import hashlib
import json


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(path):
    name = path.name
    if name.endswith(".in"): return "qe_input"
    if name.endswith(".out"): return "qe_output"
    if name.endswith(".traj"): return "ase_trajectory"
    if name in {"status.json", "validation.jsonl", "fire.log", "provenance.json", "config.json"}:
        return "stage_c_record"
    if ".save" in path.parts or name.startswith("wfc") or "charge-density" in name:
        return "qe_restart_state"
    return "other"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root")
    parser.add_argument("--output", required=True)
    parser.add_argument("--include-restart-state", action="store_true")
    args = parser.parse_args()
    root, output = Path(args.source_root).resolve(), Path(args.output).resolve()
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        kind = classify(path)
        if kind == "qe_restart_state" and not args.include_restart_state:
            continue
        relative = path.relative_to(root).as_posix()
        tau = next((part for part in path.parts if len(part) == 5 and
                    part.startswith("tau") and part[3:].isdigit()), "")
        stage = ("C" if "stage_c" in relative else
                 "B" if "vertical_relax" in relative else
                 "A" if ".scf." in relative else "")
        rows.append({"relative_path": relative, "tau": tau, "stage": stage,
                     "kind": kind, "bytes": path.stat().st_size,
                     "sha256": digest(path)})
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["relative_path", "tau", "stage", "kind", "bytes", "sha256"]
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    metadata = {"schema_version": 1, "source_root": str(root),
                "file_count": len(rows), "total_bytes": sum(r["bytes"] for r in rows),
                "restart_state_included": args.include_restart_state}
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(output, len(rows), "files")
if __name__ == "__main__":
    main()
