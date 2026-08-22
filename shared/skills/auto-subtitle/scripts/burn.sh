#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: burn.sh VIDEO SUBS_ASS OUT_MP4 [HEIGHT] [CRF]" >&2
  exit 1
fi

video=$1
subs=$2
out=$3
height=${4:-1920}
crf=${5:-23}

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "error: ffmpeg not found on PATH" >&2
  exit 2
fi

if ! command -v ffprobe >/dev/null 2>&1; then
  echo "error: ffprobe not found on PATH" >&2
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

subs_abs=$(realpath "$subs")
subs_escaped=${subs_abs//\\/\\\\\\\\}
subs_escaped=${subs_escaped//:/\\\\:}

ffmpeg -v error -stats -y -i "$video" \
  -map 0:v:0 -map 0:a:0 \
  -vf "scale=-2:${height}:flags=lanczos,subtitles=${subs_escaped}" \
  -c:v libx264 -crf "$crf" -preset medium -pix_fmt yuv420p -profile:v high \
  -movflags +faststart \
  -c:a aac -b:a 128k -ac 2 \
  "$out"

size=$(du -h "$out" | cut -f1)
probe=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height:format=duration -of csv=s=x:p=0 "$out")

echo "wrote $out ($size)" >&2
echo "resolution/duration: $probe" >&2
