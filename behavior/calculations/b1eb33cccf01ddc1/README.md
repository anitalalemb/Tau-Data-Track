# SCF and relaxation behavior

Source: `tau_mass_defined/tau02/sto_bi_tau02.vertical_relax_8h.out`

SHA-256: `62fd0fe6dde0b70aa0eb222db6f10dec34b0ea422241e00fd6adacea18414ef1` (matches the NERSC inventory).

1683 observed electronic iterations; 20 SCF cycles; 19 force evaluations.

![Energy, electronic convergence, force and optimizer histories](history.png)

## Latest run: printed values

| Quantity | Value |
| --- | --- |
| Latest electronic-cycle outcome | UNFINISHED |
| First printed total energy in latest run (Ry) | -1139.0172185 |
| Last printed total energy in latest run (Ry) | -1139.18065314 |
| Last maximum printed atomic-force norm (eV/Å) | 0.15516455988535224 |
| Last QE Total force (Ry/Bohr) | 0.00101 |
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
