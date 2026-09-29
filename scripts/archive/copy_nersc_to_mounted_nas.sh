#!/usr/bin/env bash
set -euo pipefail

mode=${1:---dry-run}
release_id=${2:-2026-09-29_stageABC_v1}
remote_source="bella:/pscratch/sd/a/anita14b/SAM/STO/bilayer/twist/grid/10x10/"
nas_root="/Volumes/Shared/Anita"
destination="$nas_root/STO/tau-grid/raw/$release_id/"

if [[ $mode != "--dry-run" && $mode != "--apply" ]]; then
  echo "Usage: $0 [--dry-run|--apply] [RELEASE_ID]" >&2
  exit 2
fi

if [[ ! -d $nas_root ]]; then
  echo "NAS is not mounted at $nas_root" >&2
  echo "Connect Finder to smb://Anita@141.23.34.10/Shared first." >&2
  exit 1
fi

mkdir -p "$destination"

rsync_args=(
  -av
  --human-readable
  --itemize-changes
  --partial
  --progress
  --exclude='*.save/'
  --exclude='tmp/'
  --exclude='tmp_*/'
  --exclude='scratch/'
  --exclude='*.wfc*'
  --exclude='charge-density*.hdf5'
  --exclude='__pycache__/'
  --exclude='*.pyc'
  --exclude='qe/'
  --exclude='*.tar'
  --exclude='*.tar.gz'
)

if [[ $mode == "--dry-run" ]]; then
  rsync_args+=(--dry-run)
  echo "DRY RUN: no NAS files will be changed."
fi

echo "NERSC source: $remote_source"
echo "NAS target:   $destination"
echo "You will be prompted for your NERSC Password + OTP."
rsync "${rsync_args[@]}" "$remote_source" "$destination"

if [[ $mode == "--apply" ]]; then
  repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
  manifest="$repo_root/registry/raw_${release_id}.csv"
  python3 "$repo_root/scripts/archive/build_raw_manifest.py" \
    "$destination" --output "$manifest"
  echo "Transfer complete. Raw-data manifest: $manifest"
else
  echo "Review the file list, then rerun with --apply."
fi
