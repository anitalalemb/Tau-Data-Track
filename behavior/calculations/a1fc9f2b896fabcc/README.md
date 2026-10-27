# SCF and relaxation behavior

Source: `tau01/sto_bi_tau01.vertical_relax.out`

SHA-256: `c6c65cfc3debdc67253dcda6d43053a5b534e86d2dd0763c411869ad2a1c65ea` (matches the NERSC inventory).

548 observed electronic iterations; 12 SCF cycles; 12 force evaluations.

![Energy, electronic convergence, force and optimizer histories](history.png)

## Latest run: printed values

| Quantity | Value |
| --- | --- |
| Latest electronic-cycle outcome | CONVERGED |
| First printed total energy in latest run (Ry) | -1139.26542119 |
| Last printed total energy in latest run (Ry) | -1139.26676067 |
| Last maximum printed atomic-force norm (eV/Å) | 0.8423880908240466 |
| Last QE Total force (Ry/Bohr) | 0.001139 |
| Final reported BFGS steps | 11 |
| Latest program run reached JOB DONE | True |
| Latest program run has runtime error / time limit | False / False |

## Download exact histories

- [Electronic iterations](electronic_iterations.csv.gz): printed QE iteration number, total energy in Ry, estimated SCF accuracy and source lines. Restart numbering is preserved.
- [SCF cycle outcomes](scf_cycles.csv): converged, not converged or unfinished, separately for every electronic cycle.
- [Force evaluations](force_evaluations.csv): QE total force, printed atomic-force maximum/RMS, SCF force correction, energy and associated cycle.
- [Reported optimizer steps](optimizer_events.csv): BFGS/SCF counters and convergence messages at their original source lines.

Force evaluations include trial geometries and are not automatically accepted optimizer steps. The BFGS counter can continue from an earlier restart; no unprinted steps are invented. Curves stop at file/run/cycle boundaries as applicable.

Forces are retained only where QE printed a complete force evaluation; they are not interpolated between electronic iterations. High-verbosity component-force blocks are excluded from the total atomic-force statistics. Printed zero SCF estimates are not shown on the logarithmic axis.

Electronic energies follow the convention printed by QE (including its smearing/free-energy convention). Relative energies are within a single cycle/run, never comparisons between different cells. A final plotted value is not by itself evidence of convergence.
