#!/bin/bash
#SBATCH --job-name=sto-tau10-scf
#SBATCH --account=m4269
#SBATCH --constraint=cpu
#SBATCH --qos=regular
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=128
#SBATCH --cpus-per-task=1
#SBATCH --time=02:00:00
#SBATCH --array=0-12%13
#SBATCH --output=tau_scf_group_%A_%a.out
#SBATCH --error=tau_scf_group_%A_%a.err

set -euo pipefail
module load espresso/7.5-libxc-7.0.0-cpu
export OMP_NUM_THREADS=1
export OMP_PLACES=cores
export OMP_PROC_BIND=spread
ROOT="${SLURM_SUBMIT_DIR}"
GROUP_SIZE=8
START=$((SLURM_ARRAY_TASK_ID*GROUP_SIZE)); END=$((START+GROUP_SIZE-1)); ((END>99)) && END=99
pids=(); labels=()
for idx in $(seq "$START" "$END"); do
  i=$((idx/10)); j=$((idx%10)); label="tau${i}${j}"; dir="${ROOT}/${label}"; input="sto_bi_${label}.scf.in"; output="sto_bi_${label}.scf.out"
  [[ -f "${dir}/${input}" ]] || { echo "Missing ${dir}/${input}"; exit 2; }
  echo "Launching ${label} with 16 MPI ranks"
  (cd "$dir" && srun --exclusive -N 1 -n 16 -c 1 --cpu-bind=cores pw.x -in "$input" > "$output" 2>&1) &
  pids+=("$!"); labels+=("$label")
done
fail=0
for k in "${!pids[@]}"; do wait "${pids[$k]}" && echo "DONE ${labels[$k]}" || { echo "FAILED ${labels[$k]}"; fail=1; }; done
exit "$fail"
