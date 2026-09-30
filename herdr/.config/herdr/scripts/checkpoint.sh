#!/usr/bin/env bash
set -euo pipefail

herdr_dir="$HOME/.config/herdr"
session="$herdr_dir/session.json"
checkpoints="$herdr_dir/checkpoints"
keep=20
coalesce_seconds=60
max_bytes=1048576

mtime() {
    if [[ "$(uname -s)" == "Darwin" ]]; then
        stat -f %m "$1"
    else
        stat -c %Y "$1"
    fi
}

if (($(wc -c < "$session") > max_bytes)); then
    echo "session.json is larger than $max_bytes bytes, not checkpointing" >&2
    exit 1
fi

mkdir -p "$checkpoints"

target="$checkpoints/$(date +%Y%m%d-%H%M%S).json"
latest=$(ls -1t "$checkpoints" | sed -n 1p)
if [[ -n "$latest" ]]; then
    latest_path="$checkpoints/$latest"
    if cmp -s "$session" "$latest_path"; then
        touch "$latest_path"
        exit 0
    fi
    if (($(date +%s) - $(mtime "$latest_path") < coalesce_seconds)); then
        target="$latest_path"
    fi
fi

tmp=$(mktemp "$checkpoints/.tmp.XXXXXX")
trap 'rm -f "$tmp"' EXIT
cp "$session" "$tmp"
mv "$tmp" "$target"

ls -1t "$checkpoints" | tail -n +$((keep + 1)) | while read -r old; do
    rm -f "$checkpoints/$old"
done
