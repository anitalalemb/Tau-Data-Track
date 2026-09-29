#!/usr/bin/env python3
"""Inventory STO research calculations and identify validated result sets.

This is an archive audit, not an ML exporter.  It records enough evidence to
select the authoritative SCF, relaxation, bands, PDOS, Wannier, and structural
analysis results after raw NERSC directories are copied to the NAS.
"""

from pathlib import Path
import argparse
import csv
import json
import re


TEXT_SUFFIXES = {".in", ".out", ".wout", ".win", ".log", ".txt"}


def material_from_path(relative):
    lower = relative.lower()
    if "monolayer" in lower or "mono_layer" in lower:
        return "monolayer"
    if "bulk" in lower:
        return "bulk"
    if "bilayer" in lower or "twisted_sto" in lower:
        return "bilayer"
    return "unclassified"


def angle_from_path(relative):
    match = re.search(r"theta_([0-9]+p[0-9]+)_m([0-9]+)_n([0-9]+)", relative, re.I)
    if not match:
        return "", "", ""
    return match.group(1).replace("p", "."), match.group(2), match.group(3)


def calculation_kind(name, relative):
    lower = f"{relative}/{name}".lower()
    if "wannier" in lower or name.endswith(("_hr.dat", ".wout", ".win", ".amn", ".mmn", ".eig")):
        return "wannier"
    if "pdos" in lower or "projwfc" in lower:
        return "pdos"
    if "bands" in lower or "bandx" in lower:
        return "bands"
    if "relax" in lower or "vc-relax" in lower:
        return "relax"
    if ".scf." in lower or "_scf" in lower:
        return "scf"
    if any(word in lower for word in ("structural", "corrugation", "off_center", "displacement", "octahed")):
        return "structural_analysis"
    return "other"


def output_status(path):
    if path.suffix not in TEXT_SUFFIXES or path.stat().st_size > 100_000_000:
        return "", "", "", ""
    text = path.read_text(errors="ignore")
    return (
        "JOB DONE." in text,
        "convergence has been achieved" in text.lower()
        and "convergence not achieved" not in text.lower(),
        "bfgs converged" in text.lower()
        and "end of bfgs geometry optimization" in text.lower(),
        "maximum cpu time exceeded" in text.lower(),
    )


def candidate_status(kind, job_done, electronic, ionic, timed_out):
    if kind == "scf":
        return "VALID" if job_done and electronic else "REVIEW"
    if kind == "relax":
        return "VALID" if job_done and ionic and not timed_out else "REVIEW"
    if kind in {"bands", "pdos"}:
        return "REVIEW_REQUIRED"
    if kind == "wannier":
        return "REVIEW_REQUIRED"
    return "REFERENCE_ONLY"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_root")
    parser.add_argument("--output", default="registry/sto_research_inventory.csv")
    args = parser.parse_args()

    root = Path(args.archive_root).resolve()
    output = Path(args.output).resolve()
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        kind = calculation_kind(path.name, relative)
        job_done, electronic, ionic, timed_out = output_status(path)
        angle, m_value, n_value = angle_from_path(relative)
        rows.append({
            "relative_path": relative,
            "material": material_from_path(relative),
            "calculation_kind": kind,
            "twist_angle_deg": angle,
            "m": m_value,
            "n": n_value,
            "bytes": path.stat().st_size,
            "job_done": job_done,
            "electronic_converged": electronic,
            "ionic_converged": ionic,
            "time_limit": timed_out,
            "candidate_status": candidate_status(kind, job_done, electronic, ionic, timed_out),
        })

    fields = list(rows[0]) if rows else [
        "relative_path", "material", "calculation_kind", "twist_angle_deg",
        "m", "n", "bytes", "job_done", "electronic_converged",
        "ionic_converged", "time_limit", "candidate_status",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    summary = {}
    for row in rows:
        key = (row["material"], row["calculation_kind"], row["candidate_status"])
        summary[key] = summary.get(key, 0) + 1
    output.with_suffix(".json").write_text(json.dumps({
        "archive_root": str(root),
        "file_count": len(rows),
        "counts": [
            {"material": key[0], "calculation_kind": key[1], "candidate_status": key[2], "count": count}
            for key, count in sorted(summary.items())
        ],
    }, indent=2) + "\n")
    print(f"Inventoried {len(rows)} files: {output}")


if __name__ == "__main__":
    main()
