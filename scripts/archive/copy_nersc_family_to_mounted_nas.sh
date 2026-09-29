#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "Usage: $0 NERSC_SOURCE_PATH NAS_FAMILY RELEASE_ID [--apply]" >&2
  exit 2
fi

remote_source=$1
family=$2
release_id=$3
mode=${4:---dry-run}
nas_root="/Volumes/Shared/Anita/STO"

if [[ $mode != "--dry-run" && $mode != "--apply" ]]; then
  echo "The optional fourth argument must be --apply." >&2
  exit 2
fi
if [[ ! $family =~ ^[A-Za-z0-9._/-]+$ || ! $release_id =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "NAS_FAMILY and RELEASE_ID contain unsupported characters." >&2
  exit 2
fi
if [[ ! -d $nas_root ]]; then
  echo "NAS is not mounted at $nas_root" >&2
  exit 1
fi

destination="$nas_root/$family/raw/$release_id/"
mkdir -p "$destination"

rsync_args=(
  -av --human-readable --itemize-changes --partial --progress
  --exclude='*.save/' --exclude='tmp/' --exclude='tmp_*/' --exclude='scratch/'
  --exclude='*.wfc*' --exclude='charge-density*.hdf5' --exclude='__pycache__/'
  --exclude='*.pyc' --exclude='qe/' --exclude='*.tar' --exclude='*.tar.gz'
)
if [[ $mode == "--dry-run" ]]; then
  rsync_args+=(--dry-run)
  echo "DRY RUN: no NAS files will be changed."
fi

echo "NERSC source: bella:$remote_source/"
echo "NAS target:   $destination"
rsync "${rsync_args[@]}" "bella:${remote_source%/}/" "$destination"

if [[ $mode == "--apply" ]]; then
  repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
  manifest="$repo_root/registry/raw_${family//\//_}_${release_id}.csv"
  python3 "$repo_root/scripts/archive/build_raw_manifest.py" \
    "$destination" --output "$manifest"
  echo "Transfer complete. Raw-data manifest: $manifest"
fi
