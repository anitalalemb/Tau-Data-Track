#!/usr/bin/env python3

from pathlib import Path
import argparse
import csv
import json
import subprocess
import sys

from select_tau_vertical_branch import choose


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tau_root")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int, default=99)
    p.add_argument(
        "--data-root",
        default="data/vertical_relax",
    )
    p.add_argument(
        "--summary",
        default="summaries/vertical_relax_summary.csv",
    )
    args = p.parse_args()

    repo = Path(__file__).resolve().parents[2]
    extractor = (
        repo
        / "scripts"
        / "analysis"
        / "extract_tau_vertical_relax.py"
    )

    tau_root = Path(args.tau_root).resolve()
    data_root = (repo / args.data_root).resolve()
    summary_path = (repo / args.summary).resolve()

    data_root.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    for i in range(args.start, args.end + 1):
        label = f"tau{i:02d}"
        tau_dir = tau_root / label

        selected, runs = choose(tau_dir)

        if selected is None:
            print(f"{label}: NO OUTPUT")
            rows.append({
                "tau": label,
                "status": "NO_OUTPUT",
                "selected_file": "",
                "final_energy_Ry": "",
                "final_total_force_Ry_Bohr": "",
                "frames": "",
                "alternative_runs": "",
            })
            continue

        status = (
            "CONVERGED"
            if selected["converged"]
            else (
                "TIME_LIMIT"
                if selected["max_time"]
                else "INCOMPLETE"
            )
        )

        if not selected["converged"]:
            print(
                f"{label}: {status} — not exporting "
                "as authoritative dataset"
            )

            rows.append({
                "tau": label,
                "status": status,
                "selected_file": selected["path"].name,
                "final_energy_Ry": "",
                "final_total_force_Ry_Bohr":
                    selected["final_force"],
                "frames": selected["n_forces"],
                "alternative_runs": "",
            })
            continue

        outdir = data_root / label

        print()
        print("=" * 72)
        print(
            f"{label}: extracting "
            f"{selected['path'].name}"
        )
        print("=" * 72)

        subprocess.run(
            [
                sys.executable,
                str(extractor),
                str(selected["path"]),
                "--tau",
                label,
                "--outdir",
                str(outdir),
            ],
            check=True,
        )

        manifest_path = outdir / "manifest.json"
        manifest = json.loads(
            manifest_path.read_text()
        )

        alternatives = []

        for r in runs:
            if r["path"] == selected["path"]:
                continue

            alternatives.append({
                "file": r["path"].name,
                "converged": r["converged"],
                "job_done": r["job_done"],
                "maximum_cpu_time_exceeded":
                    r["max_time"],
                "frames": r["n_forces"],
                "final_total_force_Ry_Bohr":
                    r["final_force"],
                "selection":
                    "rejected_alternative",
            })

        manifest["branch_selection"] = {
            "selected":
                selected["path"].name,
            "selection_reason":
                (
                    "Highest-ranked scientifically valid "
                    "branch: converged BFGS preferred; "
                    "then completed execution; then more "
                    "evaluated frames; then lower final "
                    "QE total force."
                ),
            "alternatives":
                alternatives,
        }

        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n"
        )

        rows.append({
            "tau": label,
            "status": "CONVERGED",
            "selected_file":
                selected["path"].name,
            "final_energy_Ry":
                manifest["final_energy_Ry"],
            "final_total_force_Ry_Bohr":
                manifest[
                    "final_qe_total_force_Ry_Bohr"
                ],
            "frames":
                manifest["unique_frames_written"],
            "alternative_runs":
                "; ".join(
                    a["file"]
                    for a in alternatives
                ),
        })

    fields = [
        "tau",
        "status",
        "selected_file",
        "final_energy_Ry",
        "final_total_force_Ry_Bohr",
        "frames",
        "alternative_runs",
    ]

    with summary_path.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=fields,
        )
        w.writeheader()
        w.writerows(rows)

    print()
    print("=" * 72)
    print("DATASET BUILD COMPLETE")
    print("=" * 72)
    print("summary:", summary_path)


if __name__ == "__main__":
    main()
