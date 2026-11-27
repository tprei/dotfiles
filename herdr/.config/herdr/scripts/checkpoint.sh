#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

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
saved=("$checkpoints"/*)
if ((${#saved[@]})); then
    latest_path=${saved[${#saved[@]} - 1]}
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

saved=("$checkpoints"/*)
for ((i = 0; i < ${#saved[@]} - keep; i++)); do
    rm -f "${saved[i]}"
done
