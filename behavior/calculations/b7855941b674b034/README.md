# SCF and relaxation behavior

Source: `tau_mass_defined/tau20/sto_bi_tau20.scf.out`

SHA-256: `0bad33f0372bb4845b365752b3608574f0a95f29ef2aa0a7204ec6f7bcae3fe2` (matches the NERSC inventory).

77 observed electronic iterations; 1 SCF cycles; 1 force evaluations.

![Energy, electronic convergence, force and optimizer histories](history.png)

## Latest run: printed values

| Quantity | Value |
| --- | --- |
| Latest electronic-cycle outcome | CONVERGED |
| First printed total energy in latest run (Ry) | -1139.00126067 |
| Last printed total energy in latest run (Ry) | -1139.02542023 |
| Last maximum printed atomic-force norm (eV/Å) | 5.111166171965797 |
| Last QE Total force (Ry/Bohr) | 0.29348 |
| Final reported BFGS steps | No final convergence counter printed |
| Latest program run reached JOB DONE | True |
| Latest program run has runtime error / time limit | False / False |

## Download exact histories

- [Electronic iterations](electronic_iterations.csv.gz): printed QE iteration number, total energy in Ry, estimated SCF accuracy and source lines. Restart numbering is preserved.
- [SCF cycle outcomes](scf_cycles.csv): converged, not converged or unfinished, separately for every electronic cycle.
- [Force evaluations](force_evaluations.csv): QE total force, printed atomic-force maximum/RMS, SCF force correction, energy and associated cycle.

Force evaluations include trial geometries and are not automatically accepted optimizer steps. The BFGS counter can continue from an earlier restart; no unprinted steps are invented. Curves stop at file/run/cycle boundaries as applicable.

Forces are retained only where QE printed a complete force evaluation; they are not interpolated between electronic iterations. High-verbosity component-force blocks are excluded from the total atomic-force statistics. Printed zero SCF estimates are not shown on the logarithmic axis.

Electronic energies follow the convention printed by QE (including its smearing/free-energy convention). Relative energies are within a single cycle/run, never comparisons between different cells. A final plotted value is not by itself evidence of convergence.
