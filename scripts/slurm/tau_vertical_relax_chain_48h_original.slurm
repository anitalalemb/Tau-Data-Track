#!/bin/bash
#SBATCH --job-name=sto-tau-zrelax
#SBATCH --account=m4269
#SBATCH --constraint=cpu
#SBATCH --qos=regular
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=128
#SBATCH --cpus-per-task=1
#SBATCH --time=48:00:00
#SBATCH --output=tau_zrelax_%j.out
#SBATCH --error=tau_zrelax_%j.err

# ============================================================
# STO 10x10 tau grid
# Stage B: vertical pre-relaxation
#
# SELF-SUBMITTING CHAIN
#
# Usage:
#     sbatch tau_vertical_relax_chain.slurm 0
#
# Portions:
#     0  -> tau00-tau07
#     1  -> tau08-tau15
#     2  -> tau16-tau23
#     ...
#     12 -> tau96-tau99
#
# Each portion receives its OWN 48-hour Slurm allocation.
#
# Within one portion:
#     up to 8 independent tau calculations
#     16 MPI ranks per tau
#     8 x 16 = 128 MPI ranks
#
# After ALL calculations in a portion complete successfully,
# this job automatically submits the next portion.
#
# If any tau fails, the chain stops.
# ============================================================

set -euo pipefail

# ------------------------------------------------------------
# Portion number
# ------------------------------------------------------------

if [[ $# -ne 1 ]]; then
    echo "Usage: sbatch tau_vertical_relax_chain.slurm PORTION"
    echo "PORTION must be 0-12."
    exit 2
fi

PORTION="$1"

if ! [[ "${PORTION}" =~ ^[0-9]+$ ]] || \
   (( PORTION < 0 || PORTION > 12 )); then
    echo "ERROR: PORTION must be an integer from 0 to 12."
    exit 2
fi

# ------------------------------------------------------------
# Environment
# ------------------------------------------------------------

module load espresso/7.5-libxc-7.0.0-cpu

export OMP_NUM_THREADS=1
export OMP_PLACES=cores
export OMP_PROC_BIND=spread

ROOT="${SLURM_SUBMIT_DIR}"
SCRIPT="${ROOT}/tau_vertical_relax_chain.slurm"

GROUP_SIZE=8
START=$(( PORTION * GROUP_SIZE ))
END=$(( START + GROUP_SIZE - 1 ))

if (( END > 99 )); then
    END=99
fi

echo "============================================================"
echo "STO TAU VERTICAL PRE-RELAXATION — STAGE B"
echo "============================================================"
echo "Job ID       : ${SLURM_JOB_ID}"
echo "Portion      : ${PORTION}/12"
printf "Tau range    : tau%02d - tau%02d\n" "${START}" "${END}"
echo "Root         : ${ROOT}"
echo "QE           : $(which pw.x)"
echo "MPI/tau      : 16"
echo "Slurm limit  : 48 h"
echo "QE max       : 170000 s from individual inputs"
echo "Start        : $(date)"
echo "============================================================"
echo


run_one_tau() {

    local idx="$1"
    local label
    local dir
    local input
    local output
    local save
    local nwfc
    local nconstraint

    label=$(printf "tau%02d" "${idx}")
    dir="${ROOT}/${label}"

    input="sto_bi_${label}.vertical_relax.in"
    output="sto_bi_${label}.vertical_relax.out"
    save="${dir}/tmp_vertical_relax/sto_bi_${label}.save"

    echo "[${label}] PRE-RUN CHECKS"

    # ========================================================
    # Required input
    # ========================================================

    if [[ ! -f "${dir}/${input}" ]]; then
        echo "[${label}] ERROR: missing input:"
        echo "${dir}/${input}"
        return 10
    fi

    # ========================================================
    # Required electronic initialization
    # ========================================================

    if [[ ! -d "${save}" ]]; then
        echo "[${label}] ERROR: missing save directory:"
        echo "${save}"
        return 11
    fi

    if [[ ! -f "${save}/charge-density.hdf5" ]]; then
        echo "[${label}] ERROR: missing charge-density.hdf5"
        return 12
    fi

    if [[ ! -f "${save}/data-file-schema.xml" ]]; then
        echo "[${label}] ERROR: missing data-file-schema.xml"
        return 13
    fi

    nwfc=$(find "${save}" -maxdepth 1 \
        -type f -name 'wfc*.hdf5' | wc -l)

    if [[ "${nwfc}" -eq 0 ]]; then
        echo "[${label}] ERROR: no wfc*.hdf5 files"
        return 14
    fi

    echo "[${label}] wavefunction files: ${nwfc}"

    # ========================================================
    # Important input settings
    # ========================================================

    if ! grep -q "calculation = 'relax'" "${dir}/${input}"; then
        echo "[${label}] ERROR: calculation != relax"
        return 15
    fi

    if ! grep -q "outdir = './tmp_vertical_relax'" "${dir}/${input}"; then
        echo "[${label}] ERROR: wrong outdir"
        return 16
    fi

    if ! grep -q "max_seconds = 170000" "${dir}/${input}"; then
        echo "[${label}] ERROR: max_seconds != 170000"
        return 17
    fi

    if ! grep -q "etot_conv_thr = 1.0d-4" "${dir}/${input}"; then
        echo "[${label}] ERROR: wrong etot_conv_thr"
        return 18
    fi

    if ! grep -q "forc_conv_thr = 1.0d-3" "${dir}/${input}"; then
        echo "[${label}] ERROR: wrong forc_conv_thr"
        return 19
    fi

    if ! grep -q "startingpot = 'file'" "${dir}/${input}"; then
        echo "[${label}] ERROR: startingpot != file"
        return 20
    fi

    if ! grep -q "startingwfc = 'file'" "${dir}/${input}"; then
        echo "[${label}] ERROR: startingwfc != file"
        return 21
    fi

    # ========================================================
    # Confirm all 10 atoms are x/y fixed, z free
    # ========================================================

    nconstraint=$(awk '
        /ATOMIC_POSITIONS/ {p=1; next}
        p && $1 ~ /^(Sr|Ti|O)$/ {
            if ($(NF-2)==0 && $(NF-1)==0 && $NF==1) n++
        }
        END {print n+0}
    ' "${dir}/${input}")

    if [[ "${nconstraint}" -ne 10 ]]; then
        echo "[${label}] ERROR:"
        echo "only ${nconstraint}/10 atoms have 0 0 1"
        return 22
    fi

    # ========================================================
    # Protect existing results
    # ========================================================

    if [[ -f "${dir}/${output}" ]]; then

        if grep -q "JOB DONE" "${dir}/${output}" && \
           grep -q "End of BFGS Geometry Optimization" "${dir}/${output}"; then

            echo "[${label}] already completed -> SKIP"
            return 0

        else

            echo "[${label}] ERROR:"
            echo "existing incomplete output found:"
            echo "${dir}/${output}"
            echo
            echo "Refusing to overwrite it."
            return 23

        fi
    fi

    # ========================================================
    # Run QE
    # ========================================================

    echo "[${label}] START: $(date)"

    (
        cd "${dir}"

        srun --exclusive \
             -N 1 \
             -n 16 \
             -c 1 \
             --cpu-bind=cores \
             pw.x -in "${input}" > "${output}" 2>&1
    )

    local rc=$?

    if (( rc != 0 )); then
        echo "[${label}] ERROR: pw.x exit code ${rc}"
        return "${rc}"
    fi

    # ========================================================
    # Validate completion
    # ========================================================

    if ! grep -q "JOB DONE" "${dir}/${output}"; then
        echo "[${label}] ERROR: JOB DONE not found"
        return 24
    fi

    if ! grep -q "End of BFGS Geometry Optimization" "${dir}/${output}"; then
        echo "[${label}] ERROR:"
        echo "End of BFGS Geometry Optimization not found"
        return 25
    fi

    echo "[${label}] CONVERGED: $(date)"

    return 0
}


# ============================================================
# Launch current portion
# ============================================================

echo
echo "Launching current portion..."

pids=()
labels=()

for idx in $(seq "${START}" "${END}"); do

    label=$(printf "tau%02d" "${idx}")

    echo "Launching ${label} with 16 MPI ranks"

    run_one_tau "${idx}" \
        > "${ROOT}/${label}/vertical_relax_wrapper.log" 2>&1 &

    pids+=("$!")
    labels+=("${label}")

done


# ============================================================
# Wait for every tau in this portion
# ============================================================

portion_fail=0

echo
echo "Waiting for portion to complete..."

for k in "${!pids[@]}"; do

    if wait "${pids[$k]}"; then

        echo "OK: ${labels[$k]}"

    else

        echo "FAILED: ${labels[$k]}"
        echo "  See ${labels[$k]}/vertical_relax_wrapper.log"

        portion_fail=1

    fi

done


# ============================================================
# Record failures, but ALWAYS continue the chain
# ============================================================

mkdir -p "${ROOT}/vertical_relax_chain_state"

if (( portion_fail != 0 )); then

    echo
    echo "============================================================"
    echo "PORTION ${PORTION} FINISHED WITH ONE OR MORE FAILURES"
    echo "Failed tau calculations will be inspected/rerun later."
    echo "The chain WILL continue to the next portion."
    echo "End: $(date)"
    echo "============================================================"

    {
        echo "job=${SLURM_JOB_ID}"
        echo "portion=${PORTION}"
        printf "tau_range=tau%02d-tau%02d\n" "${START}" "${END}"
        echo "status=FINISHED_WITH_FAILURES"
        echo "finished=$(date)"
    } > "${ROOT}/vertical_relax_chain_state/portion_${PORTION}_FAILED.txt"

else

    echo
    echo "============================================================"
    echo "PORTION ${PORTION} COMPLETED SUCCESSFULLY"
    printf "Completed: tau%02d - tau%02d\n" "${START}" "${END}"
    echo "End: $(date)"
    echo "============================================================"

    {
        echo "job=${SLURM_JOB_ID}"
        echo "portion=${PORTION}"
        printf "tau_range=tau%02d-tau%02d\n" "${START}" "${END}"
        echo "status=SUCCESS"
        echo "finished=$(date)"
    } > "${ROOT}/vertical_relax_chain_state/portion_${PORTION}_SUCCESS.txt"

fi


# ============================================================
# Submit next portion automatically
# ============================================================

NEXT=$(( PORTION + 1 ))

if (( NEXT <= 12 )); then

    echo
    echo "Submitting next portion: ${NEXT}"

    NEXT_JOB=$(sbatch --parsable "${SCRIPT}" "${NEXT}")

    echo "Next job ID: ${NEXT_JOB}"

    # Record the chain for provenance.
    mkdir -p "${ROOT}/vertical_relax_chain_state"

    {
        echo "previous_job=${SLURM_JOB_ID}"
        echo "completed_portion=${PORTION}"
        echo "next_portion=${NEXT}"
        echo "next_job=${NEXT_JOB}"
        echo "submitted=$(date)"
    } > "${ROOT}/vertical_relax_chain_state/portion_${PORTION}_to_${NEXT}.txt"

    echo
    echo "Chain continues automatically."

else

    echo
    echo "============================================================"
    echo "ALL 13 PORTIONS COMPLETED"
    echo "ALL tau00-tau99 VERTICAL PRE-RELAXATIONS FINISHED"
    echo "============================================================"

    mkdir -p "${ROOT}/vertical_relax_chain_state"
    date > "${ROOT}/vertical_relax_chain_state/ALL_VERTICAL_RELAXATIONS_FINISHED.time"

fi

exit 0
