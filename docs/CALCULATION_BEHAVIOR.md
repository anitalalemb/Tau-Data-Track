# SCF, forces and relaxation-step histories

Use [the behavior index](../behavior/README.md) to browse by tau point or exact
output branch. Each calculation page retains the source path, SHA-256 and
source-line numbers behind the plotted values.

## What is recorded

- **Electronic iterations:** the QE iteration number, printed total energy
  in Ry and estimated SCF accuracy in Ry. The plot uses energy relative to the
  last printed energy in the same electronic cycle; the CSV retains absolute
  energies. A last printed energy can belong to an unconverged calculation.
- **SCF cycles:** one outcome per cycle. Converged, not converged, and
  unfinished cycles remain distinct. A restart beginning at iteration 10 has
  one observed iteration at that point, not ten invented energy samples.
- **Force evaluations:** energy, QE's scalar `Total force`, maximum and RMS
  norms of the first printed total atomic-force block, and the SCF force
  correction. Atomic forces are converted from Ry/Bohr to eV/Å. The scalar
  total force is not the maximum atomic force. Component-force blocks printed
  at high verbosity are excluded from total-force statistics.
- **Optimizer steps:** explicit `number of bfgs steps`, `number of scf cycles`
  and final BFGS-convergence messages. Counts can continue across a restart.
  They are recorded after the associated force evaluation when printed there.
- **Stage C:** the existing step CSVs give FIRE energy and raw/projected force
  maxima. The projected maximum is an optimizer diagnostic, not an ML force
  label. These CSVs do not contain inner electronic-iteration histories.

Force evaluations can include trial geometries. They are not necessarily
accepted ionic steps and do not represent equal amounts of elapsed time.
There are no atomic-force samples between electronic iterations unless QE
actually printed a force evaluation. Files and concatenated run segments are
kept distinct; file ordering is not presented as a verified restart chain.

## Current source coverage

The first extraction covers 187 tau-family output histories and 122
commensurate-angle output histories, all matching the NERSC inventory collected
on 26 October 2026. Together they contain 277,063 observed electronic iterations
and 2,761 force evaluations. This includes all 100 selected original vertical
tau relaxations and all eight selected SCF/relaxation outputs for 22.62°,
28.07°, 36.87° and 53.13°.

The original rigid-SCF iteration traces and many newer/unfinished branches
still require raw-text collection. The inventory saved hashes and completion
markers; it cannot reconstruct energy samples. Pending histories are marked
explicitly in `behavior/calculation_index.csv`.

The selected tau relaxation histories were independently compared against
1,571 existing energy/force records: zero discrepancies in energy association
or atomic-force maxima within printed precision. Regression cases cover
failed electronic convergence despite normal exit, restarted numbering,
concatenated runs, verbose component forces and final BFGS counters.

## Reproduce or extend

The collector uses Python 3.6-compatible standard-library code and reads files
without submitting jobs or altering calculation sources:

```bash
python3 scripts/analysis/qe_behavior.py --root /path/to/10x10 --gzip \
  > /path/to/nersc_behavior.json.gz
```

Build the tables, pages and plots locally with Python and gnuplot:

```bash
python3 scripts/analysis/build_behavior_reports.py \
  --bundle /path/to/nersc_behavior.json.gz \
  --inventory /path/to/nersc_inventory.json \
  --repo . --family tau --plots
```

For the angle repository use `--family angles` and its repository path. The
builder rejects source hashes that differ from the supplied inventory rather
than mixing calculation versions. Electronic CSVs are gzip-compressed;
force/cycle/optimizer CSVs remain directly readable. Plotting never changes
energies or drops source rows.

Electronic total energies retain QE's printed convention, including its
smearing/free-energy convention where applicable. Energy differences are
within a cycle or run, not comparisons between cells of different sizes.
Printed zero SCF estimates are omitted from the logarithmic plot, but retained
in the exact CSV. Missing information is left missing.
