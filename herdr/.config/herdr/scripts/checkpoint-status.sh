#!/usr/bin/env bash
set -u

herdr_dir="$HOME/.config/herdr"
now=$(date +%s)

mtime() {
    if [[ "$(uname -s)" == "Darwin" ]]; then
        stat -f %m "$1"
    else
        stat -c %Y "$1"
    fi
}

latest=$(ls -1t "$herdr_dir/checkpoints" 2>/dev/null | head -n 1)
if [[ -n "$latest" ]]; then
    since=$((now - $(mtime "$herdr_dir/checkpoints/$latest")))
    case "$since" in
        0) echo "◌ saving"; exit 0 ;;
        1) echo "◑ saving"; exit 0 ;;
        2) echo "● saved"; exit 0 ;;
    esac
fi

age=$((now - $(mtime "$herdr_dir/session.json")))
if ((age < 60)); then
    echo "saved <1m"
elif ((age < 3600)); then
    echo "saved $((age / 60))m"
else
    echo "saved $((age / 3600))h"
fi
