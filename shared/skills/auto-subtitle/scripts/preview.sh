#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "usage: preview.sh VIDEO SUBS_ASS OUT_DIR T [T...]" >&2
  exit 1
fi

video=$1
subs=$2
out_dir=$3
shift 3

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "error: ffmpeg not found on PATH" >&2
  exit 2
fi

if [[ ! -f "$video" ]]; then
  echo "error: video file not found: $video" >&2
  exit 2
fi

if [[ ! -f "$subs" ]]; then
  echo "error: subtitle file not found: $subs" >&2
  exit 2
fi

mkdir -p "$out_dir"

subs_abs=$(realpath "$subs")
subs_escaped=${subs_abs//\\/\\\\\\\\}
subs_escaped=${subs_escaped//:/\\\\:}

for t in "$@"; do
  frame="$out_dir/frame_${t}.png"
  ffmpeg -v error -y -copyts -ss "$t" -t 0.2 -i "$video" \
    -vf "scale=-2:1920:flags=lanczos,subtitles=${subs_escaped}" \
    -frames:v 1 -an "$frame"
  echo "$frame"
done
