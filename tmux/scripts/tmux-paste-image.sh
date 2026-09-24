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

if ! powershell.exe -Sta -NoProfile -NonInteractive -Command "$ps_cmd" >/dev/null 2>&1; then
    tmux display-message "tmux-paste-image: no image in Windows clipboard"
    exit 0
fi

if [[ ! -s "$wsl_file" ]]; then
    tmux display-message "tmux-paste-image: failed to write $wsl_file"
    exit 0
fi

ssh_host() {
    if [[ -n "${TMUX_PASTE_IMAGE_HOST:-}" ]]; then
        printf '%s' "$TMUX_PASTE_IMAGE_HOST"
        return
    fi
    local pane_pid fg_pid
    pane_pid=$(tmux display-message -p -t "$pane" '#{pane_pid}')
    fg_pid=$(ps -o tpgid= -p "$pane_pid" | tr -d ' ')
    local -a argv
    read -r -a argv < <(ps -o args= -p "$fg_pid")
    [[ "$(basename "${argv[0]:-}")" == ssh ]] || return 1
    local i=1
    while ((i < ${#argv[@]})); do
        local arg="${argv[i]}"
        case "$arg" in
        --) printf '%s' "${argv[i + 1]:-}"; return ;;
        -[BbcDEeFIiJLlmOoPpQRSWw]) i=$((i + 2)) ;;
        -*) i=$((i + 1)) ;;
        *) printf '%s' "$arg"; return ;;
        esac
    done
    return 1
}

target_path="$wsl_file"
if [[ "$(tmux display-message -p -t "$pane" '#{pane_current_command}')" == ssh ]]; then
    if ! host=$(ssh_host) || [[ -z "$host" ]]; then
        tmux display-message "tmux-paste-image: can't find ssh host; set TMUX_PASTE_IMAGE_HOST"
        exit 0
    fi
    name=$(basename "$wsl_file")
    remote_cmd='d="$HOME/.cache/tmux-paste-image" && mkdir -p "$d" && cat > "$d/'"$name"'" && printf %s "$d/'"$name"'"'
    if ! target_path=$(ssh -o BatchMode=yes "$host" "$remote_cmd" < "$wsl_file"); then
        tmux display-message "tmux-paste-image: upload to $host failed"
        exit 0
    fi
fi

tmux send-keys -t "$pane" -l "$target_path"
tmux display-message "tmux-paste-image: $target_path"
