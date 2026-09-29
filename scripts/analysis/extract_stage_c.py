#!/usr/bin/env python3
"""Extract raw DFT labels and constrained-FIRE diagnostics from Stage C."""

from pathlib import Path
import argparse
import csv
import hashlib
import json

import numpy as np
from ase.io import read, write
from ase.io.trajectory import Trajectory
from ase.calculators.calculator import PropertyNotImplementedError


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_text_lines(path):
    path = Path(path)
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")


def extract(run_dir, out_dir, tau):
    run_dir, out_dir = Path(run_dir).resolve(), Path(out_dir).resolve()
    status = json.loads((run_dir / "status.json").read_text())
    validation = [json.loads(line) for line in
                  (run_dir / "validation.jsonl").read_text().splitlines() if line.strip()]
    paths = sorted(run_dir.glob("step_*.traj"))
    frames = [read(path) for path in paths]
    if len(frames) != len(validation):
        raise RuntimeError(f"{tau}: trajectory/validation length mismatch")
    if not frames:
        raise RuntimeError(f"{tau}: no complete checkpoints")

    out_dir.mkdir(parents=True, exist_ok=True)
    step_rows, atom_rows = [], []
    for frame_index, (path, frame, check) in enumerate(zip(paths, frames, validation)):
        raw = frame.get_forces(apply_constraint=False)
        raw_fmax = float(np.linalg.norm(raw, axis=1).max())
        if not np.isclose(raw_fmax, check["raw_fmax_eV_A"], atol=1e-12, rtol=0):
            raise RuntimeError(f"{tau} step {frame_index}: raw-force validation failed")
        try:
            stress = list(map(float, frame.get_stress(voigt=True)))
        except PropertyNotImplementedError:
            # ASE checkpoint files in the audited Stage-C package retain
            # energy and forces but not the QE stress result.  Empty values
            # explicitly mean unavailable; they must never be read as zero.
            stress = [""] * 6
        frame.info.update({"tau": tau, "tau_p": int(tau[3]), "tau_q": int(tau[4]),
                           "stage": "C", "constraint": "fixed_layer_xy_centroids",
                           "force_label": "raw_dft",
                           "projected_fmax_eV_A": check["projected_fmax_eV_A"]})
        step_rows.append({"tau": tau, "step": check["step"],
                          "energy_eV": frame.get_potential_energy(),
                          "raw_fmax_eV_A": raw_fmax,
                          "projected_fmax_eV_A": check["projected_fmax_eV_A"],
                          "stress_xx_eV_A3": stress[0], "stress_yy_eV_A3": stress[1],
                          "stress_zz_eV_A3": stress[2], "stress_yz_eV_A3": stress[3],
                          "stress_xz_eV_A3": stress[4], "stress_xy_eV_A3": stress[5],
                          "checkpoint_sha256": sha256(path)})
        for atom_index, (symbol, pos, force) in enumerate(
                zip(frame.symbols, frame.positions, raw), start=1):
            atom_rows.append({"tau": tau, "step": check["step"],
                              "atom_index": atom_index, "species": symbol,
                              "x_A": pos[0], "y_A": pos[1], "z_A": pos[2],
                              "Fx_raw_eV_A": force[0], "Fy_raw_eV_A": force[1],
                              "Fz_raw_eV_A": force[2]})

    write(out_dir / "trajectory.extxyz", frames, format="extxyz")
    with Trajectory(out_dir / "trajectory.traj", "w") as traj:
        for frame in frames: traj.write(frame)
    write(out_dir / "final_structure.vasp", frames[-1], format="vasp", direct=False, sort=False)
    normalize_text_lines(out_dir / "final_structure.vasp")
    for filename, rows in [("steps.csv", step_rows), ("atomic_forces.csv", atom_rows)]:
        with (out_dir / filename).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)
    config = json.loads((run_dir / "config.json").read_text())
    provenance = json.loads((run_dir / "provenance.json").read_text())
    manifest = {"schema_version": 1, "tau": tau, "stage": "C",
                "calculation": "fixed_registry_fire", "converged": status["converged"],
                "fire_steps": status["steps"], "evaluated_frames": len(frames),
                "force_label": "raw_dft", "convergence_force": "projected",
                "final_raw_fmax_eV_A": step_rows[-1]["raw_fmax_eV_A"],
                "final_projected_fmax_eV_A": step_rows[-1]["projected_fmax_eV_A"],
                "stress_available": all(value != "" for value in stress),
                "stress_note": ("Stored ASE checkpoints do not contain stress; "
                                "recover it from raw QE outputs when archived."),
                "fmax_target_eV_A": config["fmax_eV_A"],
                "constraint": {"name": "fixed_layer_xy_centroids",
                               "frame_convention": config["frame_convention"],
                               "bottom_zero_based": config["bottom"],
                               "top_zero_based": config["top"]},
                "source": {"run_directory_name": run_dir.name,
                           "provenance": provenance}}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tau_root")
    parser.add_argument("--data-root", default="data/stage_c_fixed_registry")
    parser.add_argument("--summary", default="summaries/stage_c_summary.csv")
    parser.add_argument("--run-name", action="append",
                        default=["stage_c_batch12_attempt01", "stage_c_attempt01"])
    args = parser.parse_args()
    repo, root = Path(__file__).resolve().parents[2], Path(args.tau_root).resolve()
    rows = []
    for number in range(100):
        tau = f"tau{number:02d}"
        candidates = [root / tau / name for name in args.run_name]
        run = next((p for p in candidates if (p / "status.json").is_file()), None)
        if run is None:
            rows.append({"tau": tau, "status": "MISSING", "run": "",
                         "steps": "", "final_energy_eV": "",
                         "final_raw_fmax_eV_A": "", "final_projected_fmax_eV_A": ""})
            continue
        manifest = extract(run, repo / args.data_root / tau, tau)
        rows.append({"tau": tau,
                     "status": "CONVERGED" if manifest["converged"] else "INCOMPLETE",
                     "run": run.name, "steps": manifest["fire_steps"],
                     "final_energy_eV": read(sorted(run.glob("step_*.traj"))[-1]).get_potential_energy(),
                     "final_raw_fmax_eV_A": manifest["final_raw_fmax_eV_A"],
                     "final_projected_fmax_eV_A": manifest["final_projected_fmax_eV_A"]})
    summary = repo / args.summary
    with summary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    print(f"Stage C: {sum(r['status'] == 'CONVERGED' for r in rows)}/100 converged")
    print(summary)


if __name__ == "__main__":
    main()
