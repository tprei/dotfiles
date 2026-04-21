#!/usr/bin/env bash
set -o pipefail

INPUT=$(cat)
j() { jq -r "$1 // empty" <<<"$INPUT" 2>/dev/null; }
jn() { jq -r "$1 // 0" <<<"$INPUT" 2>/dev/null; }

MODEL=$(j '.model.display_name')
CWD=$(j '.workspace.current_dir // .cwd')
DURATION_MS=$(jn '.cost.total_duration_ms')
COST=$(jn '.cost.total_cost_usd')
LINES_ADDED=$(jn '.cost.total_lines_added')
LINES_REMOVED=$(jn '.cost.total_lines_removed')
CTX_PCT=$(jn '.context_window.used_percentage')
EXCEEDS=$(j '.exceeds_200k_tokens')
OUTPUT_STYLE=$(j '.output_style.name')
RATE_5H=$(jn '.rate_limits.five_hour.used_percentage')
RATE_7D=$(jn '.rate_limits.seven_day.used_percentage')

RESET=$'\033[0m'
DIM=$'\033[2m'
GREEN=$'\033[32m'
BGREEN=$'\033[1;32m'
YELLOW=$'\033[33m'
BYELLOW=$'\033[1;33m'
RED=$'\033[31m'
BRED=$'\033[1;31m'
BLUE=$'\033[1;34m'
BCYAN=$'\033[1;36m'
MAGENTA=$'\033[35m'
CTX_EXCEED=$'\033[1;37;41m'
SEP="${DIM}│${RESET}"

DISPLAY_PATH="${CWD/#$HOME/~}"
USERHOST="${BGREEN}$(whoami)@$(hostname -s)${RESET}"

git_branch() {
    local dir=$1
    [[ -z "$dir" || ! -d "$dir" ]] && return
    local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/claude-statusline"
    mkdir -p "$cache_dir" 2>/dev/null
    local key
    key=$(printf '%s' "$dir" | md5sum | cut -c1-16)
    local cache_file="$cache_dir/$key"
    if [[ -f "$cache_file" ]]; then
        local mtime now
        mtime=$(stat -c %Y "$cache_file" 2>/dev/null)
        now=$(date +%s)
        if (( now - mtime < 2 )); then
            cat "$cache_file"
            return
        fi
    fi
    local branch=""
    branch=$(git -C "$dir" symbolic-ref --short HEAD 2>/dev/null) \
        || branch=$(git -C "$dir" describe --tags --exact-match 2>/dev/null) \
        || branch=$(git -C "$dir" rev-parse --short HEAD 2>/dev/null)
    local out=""
    if [[ -n "$branch" ]]; then
        local dirty=""
        if ! git -C "$dir" diff --quiet 2>/dev/null || ! git -C "$dir" diff --cached --quiet 2>/dev/null; then
            dirty="*"
        fi
        if [[ -n $(git -C "$dir" ls-files --others --exclude-standard 2>/dev/null | head -n 1) ]]; then
            dirty="${dirty}+"
        fi
        out="${branch}${dirty}"
    fi
    if [[ -d "$cache_dir" ]]; then
        { printf '%s' "$out" >"$cache_file"; } 2>/dev/null
    fi
    printf '%s' "$out"
}

BRANCH=$(git_branch "$CWD")

fmt_duration() {
    local ms=$1
    local s=$((ms / 1000))
    local h=$((s / 3600))
    local m=$(( (s % 3600) / 60 ))
    local sec=$((s % 60))
    if (( h > 0 )); then
        printf '%dh%dm' "$h" "$m"
    elif (( m > 0 )); then
        printf '%dm%02ds' "$m" "$sec"
    else
        printf '%ds' "$sec"
    fi
}

ctx_color() {
    local pct=$1
    if [[ "$EXCEEDS" == "true" ]]; then
        printf '%s' "$CTX_EXCEED"
    elif (( pct >= 80 )); then
        printf '%s' "$BRED"
    elif (( pct >= 50 )); then
        printf '%s' "$BYELLOW"
    else
        printf '%s' "$GREEN"
    fi
}

to_int() { local v=$1; v=${v%.*}; printf '%d' "${v:-0}"; }

CTX_INT=$(to_int "$CTX_PCT")
DUR_STR=$(fmt_duration "${DURATION_MS:-0}")

OUT="${USERHOST}:${BLUE}${DISPLAY_PATH}${RESET}"
[[ -n "$BRANCH" ]] && OUT+=" ${YELLOW}(${BRANCH})${RESET}"
OUT+=" ${SEP} ${BCYAN}${MODEL}${RESET}"
if (( CTX_INT > 0 )); then
    OUT+=" $(ctx_color "$CTX_INT")ctx ${CTX_INT}%${RESET}"
fi
if (( DURATION_MS > 0 )); then
    OUT+=" ${SEP} ${DIM}${DUR_STR}${RESET}"
fi
if awk -v c="$COST" 'BEGIN{exit !(c+0 > 0.005)}'; then
    OUT+=" ${DIM}$(printf '$%.2f' "$COST")${RESET}"
fi
if (( LINES_ADDED > 0 || LINES_REMOVED > 0 )); then
    OUT+=" ${SEP} ${GREEN}+${LINES_ADDED}${RESET}/${RED}-${LINES_REMOVED}${RESET}"
fi
R5=$(to_int "$RATE_5H")
R7=$(to_int "$RATE_7D")
if (( R5 >= 75 || R7 >= 75 )); then
    RL_COLOR=$YELLOW
    (( R5 >= 90 || R7 >= 90 )) && RL_COLOR=$RED
    OUT+=" ${SEP} ${RL_COLOR}rl ${R5}%/${R7}%${RESET}"
fi
if [[ -n "$OUTPUT_STYLE" && "$OUTPUT_STYLE" != "default" ]]; then
    OUT+=" ${MAGENTA}[${OUTPUT_STYLE}]${RESET}"
fi

printf '%s' "$OUT"
