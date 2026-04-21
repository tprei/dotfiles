#!/usr/bin/env bash
# Extracts the current Windows clipboard image (WSL) to a temp PNG and
# sends the WSL path into the target tmux pane. Claude Code picks up
# pasted paths and attaches them as images.
#
# Usage (from tmux): run-shell "~/dotfiles/tmux/scripts/tmux-paste-image.sh #{pane_id}"

set -euo pipefail

pane="${1:-${TMUX_PANE:-}}"
if [[ -z "$pane" ]]; then
    echo "tmux-paste-image: missing pane id" >&2
    exit 2
fi

target_dir="${TMUX_PASTE_IMAGE_DIR:-$HOME/.cache/tmux-paste-image}"
mkdir -p "$target_dir"

stamp=$(date +%Y%m%d-%H%M%S)
wsl_file="$target_dir/clip-$stamp.png"
win_file=$(wslpath -w "$wsl_file")

read -r -d '' ps_cmd <<PS || true
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
\$img = [System.Windows.Forms.Clipboard]::GetImage()
if (\$img -eq \$null) { exit 2 }
\$img.Save('$win_file', [System.Drawing.Imaging.ImageFormat]::Png)
PS

if ! powershell.exe -NoProfile -NonInteractive -Command "$ps_cmd" >/dev/null 2>&1; then
    tmux display-message "tmux-paste-image: no image in Windows clipboard"
    exit 0
fi

if [[ ! -s "$wsl_file" ]]; then
    tmux display-message "tmux-paste-image: failed to write $wsl_file"
    exit 0
fi

tmux send-keys -t "$pane" -l "$wsl_file"
tmux display-message "tmux-paste-image: $wsl_file"
