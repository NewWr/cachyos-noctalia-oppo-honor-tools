#!/usr/bin/env bash
# Install a private path source without replacing desktop settings.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/noctalia-device-toolkit/plugins"
SOURCE_NAME='device-toolkit'
if [[ ${1:-} == --help ]]; then
    echo 'Usage: bash scripts/install-plugins.sh [--dry-run]'
    exit 0
fi
[[ $# == 0 || ( $# == 1 && $1 == --dry-run ) ]] || { echo 'Invalid arguments.' >&2; exit 2; }
if [[ ${1:-} == --dry-run ]]; then
    printf 'Copy plugins to: %s\nRegister path source: %s\nEnable three plugins. Add UI entries manually.\n' "$DEST" "$SOURCE_NAME"
    exit 0
fi
(( EUID != 0 )) || { echo 'Run as the desktop user, without sudo.' >&2; exit 1; }
command -v noctalia >/dev/null || { echo 'Install Noctalia first.' >&2; exit 1; }
[[ ! -e "$DEST" ]] || { echo 'Destination already exists; use the documented manual update procedure.' >&2; exit 1; }
for name in oppo-pods honor-fan honor-battery-profile; do
    noctalia plugins lint "$ROOT/plugins/$name"
done
mkdir -p -- "$(dirname -- "$DEST")"
cp -R -- "$ROOT/plugins" "$DEST"
if ! noctalia msg plugins source add "$SOURCE_NAME" path "$DEST"; then
    printf 'Copied files, but source registration failed. Start Noctalia in this user session and run:\nnoctalia msg plugins source add %s path "%s"\n' "$SOURCE_NAME" "$DEST" >&2
    exit 1
fi
for id in osp54/oppo-pods dc/honor-fan dc/honor-battery-profile; do
    noctalia msg plugins enable "$id"
done
echo 'Source registered and plugins enabled. Add OPPO Pods to the bar and HONOR shortcuts to Control Center in Settings.'
