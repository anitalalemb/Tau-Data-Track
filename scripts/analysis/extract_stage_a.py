#!/usr/bin/env python3
"""Extract ML-ready rigid-SCF configurations from a 10x10 tau grid."""

from pathlib import Path
import argparse
import csv
import hashlib
import json
import re

import numpy as np
from ase.io import read, write


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_text_lines(path):
    path = Path(path)
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tau_root")
    parser.add_argument("--data-root", default="data/stage_a_rigid")
    parser.add_argument("--summary", default="summaries/stage_a_summary.csv")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    root = Path(args.tau_root).resolve()
    data_root = (repo / args.data_root).resolve()
    rows = []

    for number in range(100):
        tau = f"tau{number:02d}"
        source = root / tau / f"sto_bi_{tau}.scf.out"
        row = {"tau": tau, "status": "MISSING", "source_file": source.name,
               "energy_eV": "", "max_force_eV_A": "", "stress_present": False,
               "source_sha256": ""}
        if not source.is_file():
            rows.append(row)
            continue

        text = source.read_text(errors="replace")
        converged = ("JOB DONE." in text and
                     "convergence has been achieved" in text.lower() and
                     "convergence not achieved" not in text.lower())
        if not converged:
            row["status"] = "INCOMPLETE"
            row["source_sha256"] = sha256(source)
            rows.append(row)
            continue

        frames = read(source, format="espresso-out", index=":")
        if not isinstance(frames, list):
            frames = [frames]
        frame = frames[-1]
        forces = frame.get_forces()
        stress = frame.get_stress(voigt=True)
        out = data_root / tau
        out.mkdir(parents=True, exist_ok=True)

        frame.info.update({"tau": tau, "tau_p": number // 10,
                           "tau_q": number % 10, "stage": "A",
                           "constraint": "rigid_scf", "force_label": "raw_dft"})
        write(out / "configuration.extxyz", frame, format="extxyz")
        write(out / "structure.vasp", frame, format="vasp", direct=False, sort=False)
        normalize_text_lines(out / "structure.vasp")

        with (out / "atomic_forces.csv").open("w", newline="") as handle:
            fields = ["tau", "atom_index", "species", "x_A", "y_A", "z_A",
                      "Fx_eV_A", "Fy_eV_A", "Fz_eV_A"]
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for index, (symbol, pos, force) in enumerate(
                    zip(frame.symbols, frame.positions, forces), start=1):
                writer.writerow(dict(tau=tau, atom_index=index, species=symbol,
                                     x_A=pos[0], y_A=pos[1], z_A=pos[2],
                                     Fx_eV_A=force[0], Fy_eV_A=force[1], Fz_eV_A=force[2]))

        manifest = {
            "schema_version": 1, "tau": tau, "stage": "A",
            "calculation": "rigid_scf", "source_output": source.name,
            "source_sha256": sha256(source), "job_done": True,
            "electronic_converged": True, "frames_parsed": len(frames),
            "selected_frame": len(frames) - 1, "energy_eV": frame.get_potential_energy(),
            "max_atomic_force_eV_A": float(np.linalg.norm(forces, axis=1).max()),
            "stress_voigt_eV_A3": list(map(float, stress)), "force_label": "raw_dft",
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        row.update(status="CONVERGED", energy_eV=manifest["energy_eV"],
                   max_force_eV_A=manifest["max_atomic_force_eV_A"],
                   stress_present=True, source_sha256=manifest["source_sha256"])
        rows.append(row)

    summary = repo / args.summary
    summary.parent.mkdir(parents=True, exist_ok=True)
    with summary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    print(f"Stage A: {sum(r['status'] == 'CONVERGED' for r in rows)}/100 converged")
    print(summary)


if __name__ == "__main__":
    main()
