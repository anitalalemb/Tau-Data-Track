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

## Audit before selection

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
