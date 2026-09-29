#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 SOURCE_ROOT NAS_DEST RELEASE_ID [--apply]" >&2
  exit 2
fi

source_root=$(cd "$1" && pwd -P)
nas_dest=$2
release_id=$3
mode=${4:---dry-run}

if [[ ! $release_id =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "RELEASE_ID may contain only letters, digits, dot, underscore and dash" >&2
  exit 2
fi

destination=${nas_dest%/}/STO/tau-grid/raw/${release_id}/
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
manifest=$repo_root/registry/raw_${release_id}.csv

python3 "$repo_root/scripts/archive/build_raw_manifest.py" \
  "$source_root" --output "$manifest"

rsync_args=(-a --human-readable --itemize-changes --checksum \
  --exclude='*.wfc*' --exclude='*.save/' --exclude='tmp*/' \
  --exclude='__pycache__/' --exclude='*.pyc' \
  --log-file="$repo_root/nas_sync.log")

if [[ $mode != "--apply" ]]; then
  rsync_args+=(--dry-run)
  echo "DRY RUN: no NAS files will be changed."
fi

echo "Source:      $source_root/"
echo "Destination: $destination"
echo "Manifest:    $manifest"
rsync "${rsync_args[@]}" "$source_root/" "$destination"

if [[ $mode != "--apply" ]]; then
  echo "Review the output, then rerun with --apply."
else
  echo "NAS sync complete. Preserve the manifest in Git."
fi
