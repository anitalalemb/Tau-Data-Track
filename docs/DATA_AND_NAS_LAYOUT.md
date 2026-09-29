# Data organization for DFT, machine learning, Git, and NAS

## Storage roles

Git and the NAS have different jobs.

| Location | Store | Do not store |
|---|---|---|
| Git | extraction code, compact EXTXYZ, CSV summaries, final structures, manifests, checksums, provenance | QE scratch, `.save`, wavefunctions, charge density, large raw logs |
| NAS | immutable raw inputs/outputs, Slurm records, Stage C checkpoints, release manifests, optional restart states | untracked hand-edited copies |
| NERSC scratch | active calculations and temporary restart state | the only copy of a completed dataset |

## Scientific stages

| Stage | Structure | Labels retained | Constraint metadata |
|---|---|---|---|
| A: rigid SCF | imposed tau registry, no ionic motion | energy, raw DFT atomic forces, stress | `rigid_scf` |
| B: vertical relaxation | x/y fixed, z relaxed | every evaluated energy, raw DFT atomic forces, stress, coordinates | `xy_fixed_z_free` |
| C: fixed-registry FIRE | internal x/y and all z free; each layer centroid fixed in x/y | energy, **raw DFT forces**, coordinates; stress when retained by the source; projected force only as convergence metadata | `fixed_layer_xy_centroids` |

Never use Stage C projected forces as machine-learning force labels. They are optimizer diagnostics. The trajectories save raw QE forces for training.

The currently archived Stage C ASE checkpoints do not contain stress, even
though the calculator configuration requested it. Empty Stage C stress columns
mean “not available,” not zero. Preserve the raw QE calculation output on the
NAS so stress can be recovered when that output is present.

## Canonical NAS tree

```text
STO/tau-grid/
├── raw/
│   └── 2026-09-29_stageABC_v1/
│       ├── tau00/
│       ├── tau01/
│       └── ...
├── releases/
│   └── 2026-09-29_stageABC_v1/
│       ├── raw_manifest.csv
│       ├── raw_manifest.json
│       ├── dataset_index.csv
│       ├── checksums.sha256
│       └── git_commit.txt
└── restart-archive/
    └── OPTIONAL_expensive_QE_restart_states/
```

Use an immutable release ID. If data change, create `v2`; do not silently replace `v1`.

## Per-tau Git products

```text
data/
├── stage_a_rigid/tauNN/
│   ├── configuration.extxyz
│   ├── atomic_forces.csv
│   ├── structure.vasp
│   └── manifest.json
├── vertical_relax/tauNN/
│   ├── trajectory.extxyz
│   ├── trajectory.traj
│   ├── steps.csv
│   ├── atomic_forces.csv
│   ├── final_structure.vasp
│   └── manifest.json
└── stage_c_fixed_registry/tauNN/
    └── same compact trajectory products
```

The `registry/dataset_index.csv` file is the join table for later ML ingestion. Every item has a stable dataset ID, stage, tau point, constraint, and manifest checksum.

## NAS synchronization

For Anita's mounted Synology share, transfer directly from NERSC through the
Mac. The script defaults to a dry run and prompts for the NERSC Password + OTP:

```bash
scripts/archive/copy_nersc_to_mounted_nas.sh --dry-run
scripts/archive/copy_nersc_to_mounted_nas.sh --apply
```

The fixed destination is
`/Volumes/Shared/Anita/STO/tau-grid/raw/2026-09-29_stageABC_v1/`.

For another NAS or source location, use the general workflow below.

First create and review a dry run:

```bash
scripts/archive/sync_to_nas.sh \
  /pscratch/sd/a/USER/PROJECT/STO/bilayer/twist/grid/10x10 \
  /mounted/NAS/projects \
  2026-09-29_stageABC_v1
```

After reviewing every proposed transfer, add `--apply`:

```bash
scripts/archive/sync_to_nas.sh SOURCE_ROOT NAS_ROOT RELEASE_ID --apply
```

The default transfer omits QE `.save`, wavefunctions, charge-density files, and `tmp*` directories. Archive those separately only when their restart value justifies their size.

After transfer, copy the raw manifest, dataset index, checksums, and Git commit into the NAS release directory. Verify a sample of files with SHA-256 before deleting anything from scratch.
