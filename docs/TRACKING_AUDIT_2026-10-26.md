# Calculation-tracking audit — 26 October 2026

## Verified repository findings

Baseline: `f5cbe6baaad591d3d47547f8874bfcaddd9949b4` on `main`.
The initial repository audit was followed by a user-authenticated NERSC scan
on `login21`, completed at 18:06:04 UTC (19:06 Berlin) on this date.

| Stage | Compact datasets present | Summary status | Limitation |
| --- | ---: | --- | --- |
| A: rigid SCF | 100 | 100 converged | All source hashes now match live NERSC; physical accuracy is a separate check |
| B: xy-fixed, z-free relaxation | 100 | 100 converged | All selected source hashes now match; complete restart histories still depend on the raw archive |
| C: fixed-registry FIRE | 4 | tau00, tau25, tau37, tau55 converged | 96 missing from Git; their current NERSC state is unknown |

All 1,024 entries in `registry/checksums.sha256` matched the checked-out files.
All 204 dataset-index manifest hashes matched their manifests. This verifies
internal integrity, not the physical accuracy or current remote availability
of the calculations.

All 100 Stage A source hashes and all 100 selected Stage B source hashes also
match the historical raw manifest. The Stage C seed-output hashes resolve for
all four records. Two refer to a different branch from the selected Stage B
product: tau00 uses `sto_bi_tau00.vertical_relax_8h.out` while its Stage B
selection uses `sto_bi_tau00.vertical_relax.out`; tau55 uses
`sto_bi_tau55.vertical_relax_tight.out` while its Stage B selection uses
`sto_bi_tau55.vertical_relax_restart3.out`. Different output hashes alone do
not prove different endpoint coordinates. Check those geometries and actual
seed directories before treating A/B/C as one continuous trajectory.

## Corrections

1. The index builder used a relaxation-only fallback for Stage A. Consequently,
   all 100 rigid-SCF index rows said `converged=False`, although all 100 manifests
   contain `electronic_converged=true` and `job_done=true`. The builder now uses
   stage-specific completion evidence, and the regenerated index agrees with
   the manifests and summaries.
2. The README still said Stage A was missing and Stage C contained only tau37.
   It now reports the actual 100/100/4 release coverage.
3. Six angle-selection paths omitted subdirectories. The raw release manifest
   resolves 28.07° and 18.92° under `test_calculation/`, and 16.26° under
   `test_calculation/two_node_tests/`. These are path repairs to the existing
   historical selections; they do not promote any calculation's status.

## Live NERSC verification

The supplied inventory contains 6,045 files, with zero scan errors and no
size-limit skips or files changing during their individual reads. Its SHA-256
is `37c82dfb3031ef26c85d42807523f66a0b06420acd883e4a1cd82fb02350375e`.
The scan covers `/pscratch/sd/a/anita14b/SAM/STO/bilayer/twist/grid/10x10`
and its included subdirectories. It excludes restart state and binary
trajectory checkpoints; it is not a snapshot of other clusters or moved runs.

All 100 original Stage A source hashes and all 100 selected Stage B source
hashes match live NERSC files. All 200 outputs also pass the recorded
stage-specific completion-marker check. The 34 angle input/output ledger files
in the companion repository also match. No new BFGS-converged branches were
found for the six historically unfinished angles in the scanned angle folders.

Twelve original-family Stage C status files report convergence. Only four have
compact Git datasets. Missing exports: **tau11, tau22, tau44, tau50, tau56,
tau68, tau73 and tau99**. These are remote status claims awaiting checkpoint,
validation-count and raw-force checks, not eight newly accepted ML datasets.
The other 88 original tau points have no matching Stage C status record in
this scan. Absence in this scope does not prove no calculation exists elsewhere.

| Newer family | Rigid SCF points with completion markers | Vertical-relaxation points with a branch passing completion markers |
| --- | ---: | ---: |
| `tau_equal_defined` | 100/100 | 78/100 |
| `tau_mass_defined` | 100/100 | 77/100 |

These counts apply within those two family directories, include all matching
`vertical_relax*.out` branches, and count each tau point once. They do not
replace the original completed Stage B grid. Candidate outputs still need
geometry, constraint, energy/force alignment and source-provenance validation.
Keep both definitions separate during export. The 400 point/stage records
include the exact passing branch paths.

There are also separate status-converged Stage C tau00 pilots under both
`tau_definition_comparison_all/equal_weight` and `mass_weighted`. Their
constraint conventions must remain separate from the original-family exports.

`squeue` returned no current jobs for the account at collection time. Of 220
account-history rows returned for the requested period, 189 have a work
directory within the scanned root. Only those 189 rows are included in the
published scheduler CSV; scheduler completion is not scientific convergence.

Evidence and per-point tables are in `registry/nersc_2026-10-26/`.
Reproduce the comparison with:

```bash
python3 scripts/analysis/compare_tracking_inventory.py \
  --inventory /path/to/nersc_inventory.json --output /path/to/comparison
```

## What is still missing

- Export and independent validation of the eight additional Stage C results.
- Newer equal-weight/mass-weighted tau branches are absent from the September
  raw manifest. Their remote files and marker-level coverage are now recorded,
  but their compact labels and constraint compatibility still need validation.
  They must retain separate constraint conventions.
- Stage C stress is absent from the four compact datasets. Preserve this as
  unavailable; recover it only from matching raw QE outputs if present.
- Standardized final-SCF/property coverage is not established by A/B completion.
  Keep rigid SCF, vertical relaxation, FIRE, and final-property SCFs distinct.
- The NAS is not mounted on this Mac during this audit. The historical
  3,138-file raw manifest is available in Git, but the raw NAS bytes were not
  independently rehashed.

## Twisted-angle tracking

The companion private repository is
[twisted-STO-moire-workflow](https://github.com/anitalalemb/twisted-STO-moire-workflow).
At its baseline `7e80baec65147fef1dad200ad7dd605f1fffe0ff`, it contains older
analysis scripts/figures but no production QE inputs/outputs or actual structures.
It has 22.62°, 36.87° and 53.13° result entries, and no 28.07° result directory.
The historical selection table here records four usable angles, three
reference-SCF-only angles and three not-valid angles.

The companion update adds an explicit historical file ledger with archived
hashes and live NERSC file-hash verification. Large raw files remain in the archive;
compact structures, complete trajectories, provenance and selected analysis
products still need importing after their source identities are checked.

## Notion evidence

- [Overview of calculations](https://www.notion.so/3ba68ec96206801db670ea2d33457c17):
  selected input/output names and the September calculation status.
- [Commensurate-angle index](https://www.notion.so/3fa68ec9620681db9c0ce3a16899eb34):
  four-angle structural reports and numerical limitations.
- [TAU calculation strategy](https://www.notion.so/3d668ec9620680468527dfe5bc0d6cc7):
  stage definitions and the separate standardized final-SCF objective. Its
  tau55-pending paragraph is older than this Git release and is not current
  evidence of an unfinished vertical grid.

The overview's Stage-C tau37-only wording is also older than the four datasets
now in Git. Preserve its historical context when updating Notion.
