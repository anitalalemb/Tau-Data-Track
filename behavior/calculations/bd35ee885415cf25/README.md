# SCF and relaxation behavior

Source: `tau_mass_defined/tau01/sto_bi_tau01.vertical_relax_restart1.out`

SHA-256: `9bf5e69264f7ac8391f9657949379f9e0cfa05bfb4bfc12d1541f0a8f1da5cf6` (matches the NERSC inventory).

2294 observed electronic iterations; 16 SCF cycles; 15 force evaluations.

![Energy, electronic convergence, force and optimizer histories](history.png)

## Latest run: printed values

| Quantity | Value |
| --- | --- |
| Latest electronic-cycle outcome | UNFINISHED |
| First printed total energy in latest run (Ry) | -1139.56915673 |
| Last printed total energy in latest run (Ry) | -1139.17502897 |
| Last maximum printed atomic-force norm (eV/Å) | 0.17883673596229588 |
| Last QE Total force (Ry/Bohr) | 0.004757 |
| Final reported BFGS steps | No final convergence counter printed |
| Latest program run reached JOB DONE | False |
| Latest program run has runtime error / time limit | False / False |

## Download exact histories

- [Electronic iterations](electronic_iterations.csv.gz): printed QE iteration number, total energy in Ry, estimated SCF accuracy and source lines. Restart numbering is preserved.
- [SCF cycle outcomes](scf_cycles.csv): converged, not converged or unfinished, separately for every electronic cycle.
- [Force evaluations](force_evaluations.csv): QE total force, printed atomic-force maximum/RMS, SCF force correction, energy and associated cycle.
- [Reported optimizer steps](optimizer_events.csv): BFGS/SCF counters and convergence messages at their original source lines.

Force evaluations include trial geometries and are not automatically accepted optimizer steps. The BFGS counter can continue from an earlier restart; no unprinted steps are invented. Curves stop at file/run/cycle boundaries as applicable.

Forces are retained only where QE printed a complete force evaluation; they are not interpolated between electronic iterations. High-verbosity component-force blocks are excluded from the total atomic-force statistics. Printed zero SCF estimates are not shown on the logarithmic axis.

Electronic energies follow the convention printed by QE (including its smearing/free-energy convention). Relative energies are within a single cycle/run, never comparisons between different cells. A final plotted value is not by itself evidence of convergence.
