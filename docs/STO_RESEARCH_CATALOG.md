# STO research-data catalog

## Archive layout

Store each calculation family in the NAS as an immutable release:

```text
STO/
├── bulk/raw/RELEASE_ID/
├── monolayer/raw/RELEASE_ID/
├── bilayer/raw/RELEASE_ID/
│   ├── untwisted/
│   └── commensurate/theta_XXpXX_mM_nN/
└── releases/RELEASE_ID/
    ├── sto_research_inventory.csv
    ├── selection_log.csv
    └── git_commit.txt
```

The raw directories preserve provenance. The Git repository contains only
validated compact data, selection tables, analysis scripts, and figures.

## What counts as correct data

| Calculation | Accept only when | Keep with it |
|---|---|---|
| SCF | `JOB DONE`, electronic convergence, forces and stress present | input, output, final structure, pseudopotential and k-point metadata |
| Relaxation | `JOB DONE`, ionic/BFGS convergence, no time-limit termination | full ionic trajectory, final structure, raw forces and stress |
| Bands | a validated parent SCF plus successful band calculation and plotted band data | SCF identifier, k-path, Fermi-energy convention |
| PDOS | a validated parent SCF plus successful `projwfc`/PDOS output | orbital projection definition, energy reference, broadening |
| Wannier | a validated parent SCF plus `.win`, converged `.wout`, and `_hr.dat` | disentanglement/frozen windows, spread history, band-interpolation comparison |
| Structural analysis | a validated relaxation and a recorded mathematical definition | source structure IDs, pairing method, units, and plotting scale |

Do not select results by filename alone. Every selected electronic-structure
result must name its parent SCF, and every structural figure must name its
parent relaxed geometry.

## Commensurate angles

Use one directory per `theta_XXpXX_mM_nN` structure. The inventory records the
angle and the commensuration integers. Keep SCF, relax, bands, PDOS, Wannier,
and structural-analysis products underneath the same angle directory so they
cannot be confused with another moiré cell.

The authoritative currently finished set is listed in
`registry/commensurate_angle_selection.csv`: 53.13°, 36.87°, 28.07°, and
22.62°. These folders are already present inside the NAS tau-grid raw release.
The table also marks 18.92°, 16.26°, 14.25°, 12.68°, 11.42°, and 9.53° as
reference-only or not-valid, so they cannot be accidentally used as completed
relaxed calculations.

## Audit before selection

Copy an additional calculation family from NERSC with:

```bash
scripts/archive/copy_nersc_family_to_mounted_nas.sh \
  /pscratch/sd/a/anita14b/SAM/STO/PATH_TO_FAMILY \
  bilayer/commensurate \
  2026-09-29_commensurate_v1
```

Review the dry-run file list, then append `--apply`. Use `bulk`, `monolayer`,
`bilayer/untwisted`, or `bilayer/commensurate` as the NAS family, according to
the calculation source.

After copying a material family to the NAS, run:

```bash
python scripts/analysis/audit_sto_research_archive.py \
  /Volumes/Shared/Anita/STO/bilayer/raw/RELEASE_ID \
  --output registry/sto_research_inventory.csv
```

The inventory marks SCF and relax calculations as `VALID` only when their
completion markers support that decision. Bands, PDOS, and Wannier results are
marked `REVIEW_REQUIRED`: their parent-SCF linkage and physical settings need
scientific review before they enter a final dataset or manuscript figure.

## Cubic bulk STO release

The raw release `2026-09-29_bulk_v1` is stored at
`STO/bulk/raw/2026-09-29_bulk_v1` on the NAS. Its source was
`/pscratch/sd/a/anita14b/SAM/larson/bulk_2`; the older `bulk_1` directory was
empty apart from restart-directory scaffolding. The file-level manifest is
`registry/raw_bulk_2026-09-29_bulk_v1.csv`, and the scientific disposition is
recorded in `registry/bulk_cubic_selection.csv`.

The valid structural result is the cubic `vc-relax` in
`optimization/input/lat_opt.out`. It reached a lattice parameter of
3.94094776 Angstrom, a final volume of 61.20713 Angstrom cubed, and a final
enthalpy of -569.6688337221 Ry. BFGS converged in three SCF cycles and two BFGS
steps. The final SCF snapshot embedded in the same output has energy
-569.66894087 Ry, zero symmetry-enforced total force, and 0.54 kbar pressure.

The standalone SCF outputs in `optimization/scf/` and `scf/` are zero-byte
files and are invalid. The band-path PWSCF output reached `JOB DONE`, but its
archived parent SCF output is empty and no `bands.x` output or processed band
data are present; it therefore remains `REVIEW_REQUIRED`. The PDOS run failed
because `../nscf/sto_bulk1.save/data-file-schema.xml` was missing. Its `CRASH`
and error logs are retained only as provenance and must not be used for plots,
physical conclusions, or machine-learning labels.
