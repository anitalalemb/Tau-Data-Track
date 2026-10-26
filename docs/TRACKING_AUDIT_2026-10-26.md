# Calculation-tracking audit — 26 October 2026

## Verified repository findings

Baseline: `f5cbe6baaad591d3d47547f8874bfcaddd9949b4` on `main`.
This is a repository and historical-record audit. Live NERSC access required
authentication and has not been verified on this date.

| Stage | Compact datasets present | Summary status | Limitation |
| --- | ---: | --- | --- |
| A: rigid SCF | 100 | 100 converged | Raw source hashes have not been compared with live NERSC |
| B: xy-fixed, z-free relaxation | 100 | 100 converged | Selected branches are recorded; complete restart histories still depend on the raw archive |
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

## What is still missing

- A fresh NERSC inventory, current scheduler evidence, and source-hash comparison.
- Newer equal-weight/mass-weighted tau branches are absent from the September
  raw manifest. Their remote existence, completion and compatibility must be
  checked before adding them. They must retain separate constraint conventions.
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
hashes and pending NERSC verification. Large raw files remain in the archive;
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
