# Reusable tau workflow

This directory describes the portable workflow associated with
Tau-Data-Track.

The scripts under `scripts/` contain the production workflow used for
the current SrTiO3 tau-grid calculations. Some production scripts retain
NERSC-specific paths and Slurm settings intentionally so that the exact
calculation provenance is preserved.

The portable workflow should instead obtain machine-dependent and
calculation-dependent parameters from a configuration file such as:

`templates/tau_config.example.yaml`

## Scientific workflow

The intended workflow is:

1. Define an authoritative reference bilayer structure.
2. Generate a periodic tau grid in configuration space.
3. Construct one bilayer structure for every tau point.
4. Perform the rigid single-point DFT calculation.
5. Perform the Stage-B vertical pre-relaxation.
6. Validate all relaxation outputs.
7. Select the scientifically authoritative branch when multiple runs exist.
8. Extract coordinates, energies, forces, stress, and provenance.
9. Assemble the compact tau dataset.
10. Perform the later fixed-tau internal relaxation as a separate stage.

## Tau grid

For a 10 x 10 grid,

tau_pq = (p/10) a1 + (q/10) a2

with p,q = 0,...,9.

The tau grid samples periodic stacking configuration space. The 100 cells
are not literal pieces that are pasted together to construct a moire
supercell.

## Stage A: rigid calculation

The rigid structure at every tau point is evaluated without ionic
relaxation.

Typical outputs include:

- total energy;
- atomic forces;
- stress;
- electronic structure information when requested.

## Stage B: vertical pre-relaxation

The vertical pre-relaxation fixes the in-plane atomic coordinates and
allows the z coordinates to relax.

For Quantum ESPRESSO this corresponds to

    0 0 1

on each ATOMIC_POSITIONS line.

This stage captures stacking-dependent height and vertical rumpling while
preventing the structure from changing its imposed in-plane registry.

## Data extraction

Validated relaxation outputs are converted into compact datasets containing:

- complete ionic trajectories;
- Cartesian coordinates;
- total energies;
- per-atom forces;
- Quantum ESPRESSO total-force values;
- stress tensors;
- step-to-step displacements;
- final relaxed structures;
- convergence information;
- source-file and branch provenance.

The current extraction tools are located in:

`scripts/analysis/`

## Multiple calculation branches

A later calculation is not automatically considered more authoritative
than an earlier one.

When multiple outputs exist for the same tau point, the workflow checks
whether each branch:

- reached BFGS convergence;
- reached the end of geometry optimization;
- terminated normally;
- hit the time limit;
- contains complete evaluated ionic configurations.

The selected and rejected branches are recorded in the dataset manifest.

## Machine portability

Machine-specific parameters belong in a user configuration rather than in
the reusable workflow code.

Examples include:

- pseudopotential directory;
- calculation root;
- Slurm account;
- queue/QOS;
- QE module;
- node topology;
- wall time.

The historical production Slurm scripts remain under `scripts/slurm/` as
provenance for the calculations used to produce the present dataset.
