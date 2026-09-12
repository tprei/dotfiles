#!/usr/bin/env bash
set -u

dir="${HERDR_ACTIVE_PANE_CWD:-$PWD}"

if [[ "$(uname -s)" == "Darwin" ]]; then
    open "$dir"
else
    explorer.exe "$(wslpath -w "$dir")" 2>/dev/null || true
fi
