#!/usr/bin/env python3
"""Build a single index and checksums for every Git-tracked dataset item."""

from pathlib import Path
import csv
import hashlib
import json


REPO = Path(__file__).resolve().parents[2]
STAGES = {
    "A": ("data/stage_a_rigid", "rigid_scf"),
    "B": ("data/vertical_relax", "vertical_relax"),
    "C": ("data/stage_c_fixed_registry", "fixed_registry_fire"),
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    rows, checksums = [], []
    for stage, (relative, calculation) in STAGES.items():
        root = REPO / relative
        for tau_dir in sorted(root.glob("tau[0-9][0-9]")):
            manifest_path = tau_dir / "manifest.json"
            if not manifest_path.is_file():
                continue
            manifest = json.loads(manifest_path.read_text())
            converged = manifest.get("converged")
            if converged is None:
                converged = (manifest.get("bfgs_converged", False) and
                             manifest.get("job_done", False))
            trajectory = next((name for name in ("trajectory.extxyz", "configuration.extxyz")
                               if (tau_dir / name).is_file()), "")
            rows.append({"dataset_id": f"sto_tau10x10_{stage}_{tau_dir.name}",
                         "stage": stage, "calculation": calculation,
                         "tau": tau_dir.name, "tau_p": int(tau_dir.name[3]),
                         "tau_q": int(tau_dir.name[4]), "converged": bool(converged),
                         "force_label": manifest.get("force_label", "raw_dft"),
                         "relative_directory": tau_dir.relative_to(REPO).as_posix(),
                         "trajectory": trajectory,
                         "manifest_sha256": digest(manifest_path)})
            for path in sorted(p for p in tau_dir.rglob("*") if p.is_file()):
                checksums.append(f"{digest(path)}  {path.relative_to(REPO).as_posix()}")

    registry = REPO / "registry"
    registry.mkdir(exist_ok=True)
    with (registry / "dataset_index.csv").open("w", newline="") as handle:
        fields = ["dataset_id", "stage", "calculation", "tau", "tau_p", "tau_q",
                  "converged", "force_label", "relative_directory", "trajectory",
                  "manifest_sha256"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    (registry / "checksums.sha256").write_text("\n".join(checksums) + "\n")
    counts = {stage: sum(r["stage"] == stage for r in rows) for stage in STAGES}
    (registry / "dataset_release.json").write_text(json.dumps(
        {"schema_version": 1, "name": "STO_tau_10x10",
         "counts": counts,
         "labels": "DFT energy and raw Cartesian forces; stress where available",
         "warning": "Projected Stage-C forces are diagnostics, not ML labels."},
        indent=2) + "\n")
    print(f"indexed {len(rows)} tau-stage records: {counts}")


if __name__ == "__main__":
    main()
