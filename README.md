# Tau-Data-Track

Reproducible data and provenance for the 10 × 10 stacking-displacement (tau)
grid of SrTiO3 bilayers.

## What this repository tracks

The scientific dataset is organized by calculation stage:

- **Stage A — rigid SCF:** one imposed-registry structure per tau point;
- **Stage B — vertical relaxation:** x/y fixed and z relaxed;
- **Stage C — fixed-registry FIRE:** internal atomic x/y and z motion, while
  the equal-weight x/y centroid of each layer remains fixed.

Every ML-ready configuration retains its total energy, raw Cartesian DFT
forces, atomic coordinates, constraint metadata, and source provenance.
Stress is retained when it exists in the archived source. The current Stage C
ASE checkpoints omit stress, so those fields are explicitly unavailable rather
than filled with zeros. Stage C projected forces are stored only as convergence
diagnostics and must not be used as training labels.

## Git versus NAS

This repository contains compact, reviewable products:

- EXTXYZ and ASE trajectories;
- per-step and per-atom CSV files;
- final structures;
- status summaries, manifests, and SHA-256 checksums;
- generation, extraction, validation, and archival scripts.

Large raw Quantum ESPRESSO outputs and restart state belong on the NAS. NERSC
scratch is an active workspace and is not the permanent archive.

See [docs/DATA_AND_NAS_LAYOUT.md](docs/DATA_AND_NAS_LAYOUT.md) for the
canonical layout, retention rules, and dry-run-first NAS synchronization.
For bulk, monolayer, bilayer, commensurate-angle, bands, PDOS, Wannier, and
structural-analysis records, see [docs/STO_RESEARCH_CATALOG.md](docs/STO_RESEARCH_CATALOG.md).

## Repository structure

```text
Tau-Data-Track/
├── data/
│   ├── stage_a_rigid/
│   ├── vertical_relax/
│   └── stage_c_fixed_registry/
├── registry/
│   ├── dataset_index.csv
│   ├── dataset_release.json
│   └── checksums.sha256
├── scripts/
│   ├── analysis/
│   ├── archive/
│   ├── generation/
│   └── slurm/
├── summaries/
├── templates/
└── workflow/
```

## Extraction commands

From the repository root, with ASE 3.29.0 and NumPy installed:

```bash
python scripts/analysis/extract_stage_a.py /path/to/10x10

python scripts/analysis/build_tau_vertical_dataset.py \
  /path/to/10x10 --start 0 --end 99

python scripts/analysis/extract_stage_c.py /path/to/10x10

python scripts/analysis/build_dataset_index.py
```

The Stage B selector inspects all `vertical_relax*.out` branches, including
restart and tight branches. A later filename is never accepted merely because
it is newer.

## Validation rules

- Stage A requires electronic convergence and `JOB DONE`.
- Stage B requires BFGS convergence, final-coordinate completion, and aligned
  QE/ASE energy-force frames.
- Stage C requires `status.json`, matching checkpoint/validation counts, and
  independent reproduction of every raw-force maximum.
- Manifests record source branch and hashes.
- `registry/checksums.sha256` protects compact Git-tracked data.

## Current scope

This release contains validated Stage B products for all 100 tau points and the
complete 35-frame Stage C trajectory available locally for tau37. The
downloaded audit archive contains Stage A inputs but no Stage A SCF outputs, so
the Stage A summary records all 100 points as missing. Likewise, Stage C jobs
completed later on NERSC are not included until their files are archived and
extracted. Missing data are recorded as missing rather than inferred.
