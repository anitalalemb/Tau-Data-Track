# Tau-Data-Track

Data-processing and provenance repository for the 10x10 stacking-displacement
(tau) grid of SrTiO3 bilayers.

## Purpose

The repository tracks the workflow used to generate, relax, validate, and
extract stacking-dependent SrTiO3 bilayer data.

Large raw Quantum ESPRESSO calculation directories remain on NERSC scratch.
This repository stores the reproducible workflow scripts and compact scientific
datasets derived from validated DFT calculations.

## Vertical pre-relaxation dataset

The current dataset corresponds to Stage B: vertical pre-relaxation.

For these calculations:

- the in-plane atomic coordinates are fixed;
- atomic z coordinates are allowed to relax;
- the calculation uses Quantum ESPRESSO structural relaxation;
- energies, atomic forces, stress, and ionic configurations are retained.

For every validated tau point, the extracted dataset contains:

- `trajectory.extxyz` — complete evaluated ionic trajectory with ASE calculator data;
- `trajectory.traj` — ASE trajectory;
- `steps.csv` — frame-level energies, forces, stress, and displacements;
- `atomic_forces.csv` — coordinates and Cartesian force components for every atom and frame;
- `final_structure.vasp` — final relaxed structure;
- `manifest.json` — source calculation, convergence information, and branch provenance.

The global status table is:

`summaries/vertical_relax_summary.csv`

## Branch provenance

Some tau points were calculated in more than one independent run.

The analysis workflow does not automatically treat the newest output as
authoritative. Candidate branches are inspected for BFGS convergence,
successful termination, number of evaluated configurations, and final
Quantum ESPRESSO total force.

The selected source and rejected alternatives are recorded in each
`manifest.json`.

This is particularly important for calculations where a later short rerun
terminated at its time limit while an earlier calculation had already
converged.

## Repository structure

```text
Tau-Data-Track/
├── data/
│   └── vertical_relax/
├── scripts/
│   ├── analysis/
│   ├── generation/
│   └── slurm/
├── summaries/
├── requirements.txt
└── README.md

> ## Analysis environment
>
> The initial validated extraction was performed with:
>
> - Python 3.13
> - ASE 3.29.0
> - NumPy 2.x
>
> Install the required Python packages with:
>
> ```bash
> python -m pip install -r requirements.txt
> ```
>
> ## Current validated dataset
>
> The first validated dataset contains tau00 through tau15.
>
> All 16 selected calculations passed:
>
> - ASE/QE frame alignment;
> - BFGS convergence;
> - end-of-optimization detection;
> - successful QE termination;
> - coordinate extraction;
> - energy extraction;
> - per-atom force extraction;
> - QE total-force extraction;
> - stress extraction;
> - branch-provenance validation.
>
> The remaining tau points can be added using the same extraction and validation
> workflow as their Stage-B calculations complete.
