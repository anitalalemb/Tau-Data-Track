#!/usr/bin/env python3

from pathlib import Path
import argparse
import csv
import json
import re

import numpy as np
from ase.io import read, write
from ase.io.trajectory import Trajectory


RY_TO_EV = 13.605693122994
BOHR_TO_ANG = 0.529177210903
RY_BOHR_TO_EV_ANG = RY_TO_EV / BOHR_TO_ANG


def read_text(path):
    return Path(path).read_text(errors="ignore")


def qe_float(x):
    return float(x.replace("D", "E").replace("d", "e"))


def parse_qe_native(text):
    energies_ry = [
        qe_float(x)
        for x in re.findall(
            r"!\s+total energy\s*=\s*([-+0-9.EeDd]+)\s+Ry",
            text,
            flags=re.I,
        )
    ]

    total_forces_ry_bohr = [
        qe_float(x)
        for x in re.findall(
            r"Total force\s*=\s*([-+0-9.EeDd]+)",
            text,
            flags=re.I,
        )
    ]

    scf_convergences = len(
        re.findall(
            r"convergence has been achieved",
            text,
            flags=re.I,
        )
    )

    bfgs_converged = bool(
        re.search(r"bfgs converged", text, flags=re.I)
    )

    end_bfgs = bool(
        re.search(
            r"End of BFGS Geometry Optimization",
            text,
            flags=re.I,
        )
    )

    job_done = "JOB DONE." in text

    max_time = bool(
        re.search(
            r"Maximum CPU time exceeded",
            text,
            flags=re.I,
        )
    )

    return {
        "energies_ry": energies_ry,
        "total_forces_ry_bohr": total_forces_ry_bohr,
        "scf_convergences": scf_convergences,
        "bfgs_converged": bfgs_converged,
        "end_bfgs": end_bfgs,
        "job_done": job_done,
        "max_time": max_time,
    }


def parse_frames(path):
    frames = read(
        str(path),
        index=":",
        format="espresso-out",
    )

    if not isinstance(frames, list):
        frames = [frames]

    return frames


def frame_duplicate(a, b, tol=1.0e-8):
    if len(a) != len(b):
        return False

    if np.max(
        np.abs(a.positions - b.positions)
    ) >= tol:
        return False

    if np.max(
        np.abs(a.cell.array - b.cell.array)
    ) >= tol:
        return False

    return True


def extract_one(output, outdir, tau_label=None):
    output = Path(output).resolve()
    outdir = Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    text = read_text(output)
    native = parse_qe_native(text)
    frames = parse_frames(output)

    # Remove only immediately repeated identical frames.
    unique_frames = []
    original_indices = []

    for i, frame in enumerate(frames):
        if unique_frames and frame_duplicate(
            unique_frames[-1], frame
        ):
            continue

        unique_frames.append(frame)
        original_indices.append(i)

    n_frames = len(unique_frames)
    n_qe_energy = len(native["energies_ry"])
    n_qe_force = len(native["total_forces_ry_bohr"])

    alignment_ok = (
        len(frames) == n_qe_energy == n_qe_force
    )

    if not alignment_ok:
        raise RuntimeError(
            "\nQE/ASE frame alignment failed.\n"
            f"ASE frames        : {len(frames)}\n"
            f"QE energies       : {n_qe_energy}\n"
            f"QE total forces   : {n_qe_force}\n"
            "Refusing to silently associate mismatched data."
        )

    label = tau_label or output.parent.name

    # --------------------------------------------------------
    # EXTXYZ
    # ASE preserves calculator results:
    # energy, forces, stress.
    # --------------------------------------------------------

    extxyz = outdir / "trajectory.extxyz"
    write(
        str(extxyz),
        unique_frames,
        format="extxyz",
    )

    # --------------------------------------------------------
    # ASE .traj
    # --------------------------------------------------------

    traj_path = outdir / "trajectory.traj"

    with Trajectory(str(traj_path), "w") as traj:
        for frame in unique_frames:
            traj.write(frame)

    # --------------------------------------------------------
    # Step-level CSV
    # --------------------------------------------------------

    step_fields = [
        "tau",
        "global_step",
        "source_frame_index",
        "source_file",
        "energy_eV_ASE",
        "energy_Ry_QE",
        "energy_eV_QE",
        "qe_total_force_Ry_Bohr",
        "qe_total_force_eV_A",
        "max_atomic_force_eV_A",
        "rms_atomic_force_eV_A",
        "stress_xx_eV_A3",
        "stress_yy_eV_A3",
        "stress_zz_eV_A3",
        "stress_yz_eV_A3",
        "stress_xz_eV_A3",
        "stress_xy_eV_A3",
        "max_step_displacement_A",
        "rms_step_displacement_A",
    ]

    step_rows = []
    atomic_rows = []

    for global_step, (frame, source_i) in enumerate(
        zip(unique_frames, original_indices)
    ):
        energy_ase = frame.get_potential_energy()

        forces = frame.get_forces()
        force_mag = np.linalg.norm(forces, axis=1)

        max_force = float(force_mag.max())
        rms_force = float(
            np.sqrt(np.mean(force_mag**2))
        )

        stress = list(
            map(
                float,
                frame.get_stress(voigt=True),
            )
        )

        energy_ry = native["energies_ry"][source_i]
        total_force_ry = (
            native["total_forces_ry_bohr"][source_i]
        )

        max_disp = None
        rms_disp = None

        if global_step > 0:
            prev = unique_frames[global_step - 1]
            disp = frame.positions - prev.positions
            disp_mag = np.linalg.norm(disp, axis=1)

            max_disp = float(disp_mag.max())
            rms_disp = float(
                np.sqrt(np.mean(disp_mag**2))
            )

        step_rows.append(
            {
                "tau": label,
                "global_step": global_step,
                "source_frame_index": source_i,
                "source_file": output.name,
                "energy_eV_ASE": energy_ase,
                "energy_Ry_QE": energy_ry,
                "energy_eV_QE": energy_ry * RY_TO_EV,
                "qe_total_force_Ry_Bohr":
                    total_force_ry,
                "qe_total_force_eV_A":
                    total_force_ry
                    * RY_BOHR_TO_EV_ANG,
                "max_atomic_force_eV_A":
                    max_force,
                "rms_atomic_force_eV_A":
                    rms_force,
                "stress_xx_eV_A3": stress[0],
                "stress_yy_eV_A3": stress[1],
                "stress_zz_eV_A3": stress[2],
                "stress_yz_eV_A3": stress[3],
                "stress_xz_eV_A3": stress[4],
                "stress_xy_eV_A3": stress[5],
                "max_step_displacement_A":
                    max_disp,
                "rms_step_displacement_A":
                    rms_disp,
            }
        )

        symbols = frame.get_chemical_symbols()

        for atom_index, (
            symbol,
            pos,
            force,
        ) in enumerate(
            zip(
                symbols,
                frame.positions,
                forces,
            ),
            start=1,
        ):
            atomic_rows.append(
                {
                    "tau": label,
                    "global_step": global_step,
                    "atom_index": atom_index,
                    "species": symbol,
                    "x_A": pos[0],
                    "y_A": pos[1],
                    "z_A": pos[2],
                    "Fx_eV_A": force[0],
                    "Fy_eV_A": force[1],
                    "Fz_eV_A": force[2],
                    "source_file": output.name,
                }
            )

    steps_csv = outdir / "steps.csv"

    with steps_csv.open(
        "w",
        newline="",
    ) as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=step_fields,
        )
        writer.writeheader()
        writer.writerows(step_rows)

    atomic_fields = [
        "tau",
        "global_step",
        "atom_index",
        "species",
        "x_A",
        "y_A",
        "z_A",
        "Fx_eV_A",
        "Fy_eV_A",
        "Fz_eV_A",
        "source_file",
    ]

    atomic_csv = outdir / "atomic_forces.csv"

    with atomic_csv.open(
        "w",
        newline="",
    ) as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=atomic_fields,
        )
        writer.writeheader()
        writer.writerows(atomic_rows)

    # --------------------------------------------------------
    # Final structure
    # --------------------------------------------------------

    final_vasp = outdir / "final_structure.vasp"

    write(
        str(final_vasp),
        unique_frames[-1],
        format="vasp",
        direct=False,
        sort=False,
    )

    # --------------------------------------------------------
    # Manifest / provenance
    # --------------------------------------------------------

    manifest = {
        "tau": label,
        "source_output": str(output),
        "ase_frames_parsed": len(frames),
        "unique_frames_written": n_frames,
        "qe_energy_count": n_qe_energy,
        "qe_total_force_count": n_qe_force,
        "alignment_ok": alignment_ok,
        "scf_convergence_messages":
            native["scf_convergences"],
        "bfgs_converged":
            native["bfgs_converged"],
        "end_bfgs":
            native["end_bfgs"],
        "job_done":
            native["job_done"],
        "maximum_cpu_time_exceeded":
            native["max_time"],
        "final_energy_Ry":
            native["energies_ry"][-1],
        "final_qe_total_force_Ry_Bohr":
            native["total_forces_ry_bohr"][-1],
        "files": {
            "trajectory_extxyz":
                extxyz.name,
            "trajectory_traj":
                traj_path.name,
            "steps_csv":
                steps_csv.name,
            "atomic_forces_csv":
                atomic_csv.name,
            "final_structure_vasp":
                final_vasp.name,
        },
    }

    manifest_path = outdir / "manifest.json"

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        )
        + "\n"
    )

    print()
    print("==============================================")
    print("TAU VERTICAL RELAXATION EXTRACTION")
    print("==============================================")
    print("tau                :", label)
    print("source             :", output)
    print("ASE frames         :", len(frames))
    print("unique frames      :", n_frames)
    print("QE energies        :", n_qe_energy)
    print("QE total forces    :", n_qe_force)
    print("alignment          :", "PASS")
    print(
        "BFGS converged     :",
        native["bfgs_converged"],
    )
    print(
        "End BFGS           :",
        native["end_bfgs"],
    )
    print(
        "JOB DONE           :",
        native["job_done"],
    )
    print(
        "max-time exceeded  :",
        native["max_time"],
    )
    print(
        "final E [Ry]       :",
        native["energies_ry"][-1],
    )
    print(
        "final force [Ry/B] :",
        native["total_forces_ry_bohr"][-1],
    )
    print()
    print("WROTE:")
    print(" ", extxyz)
    print(" ", traj_path)
    print(" ", steps_csv)
    print(" ", atomic_csv)
    print(" ", final_vasp)
    print(" ", manifest_path)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract a validated QE ionic relaxation "
            "trajectory with energy, forces, stress, "
            "coordinates and provenance."
        )
    )

    parser.add_argument(
        "output",
        help="Quantum ESPRESSO relaxation output",
    )

    parser.add_argument(
        "--outdir",
        required=True,
        help="Destination directory",
    )

    parser.add_argument(
        "--tau",
        default=None,
        help="Tau label, e.g. tau04",
    )

    args = parser.parse_args()

    extract_one(
        args.output,
        args.outdir,
        args.tau,
    )


if __name__ == "__main__":
    main()
