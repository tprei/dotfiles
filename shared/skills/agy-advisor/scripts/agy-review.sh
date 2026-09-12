#!/usr/bin/env bash
set -euo pipefail

MODEL=gemini-3.8-flash-high

if (( $# > 1 )); then
  echo "agy-review: usage: agy-review.sh [prompt-file] (or pipe prompt on stdin)" >&2
  exit 64
fi

if (( $# == 1 )); then
  if [[ -d $1 ]]; then
    echo "agy-review: not a file: $1" >&2
    exit 64
  fi
  if ! prompt=$(cat -- "$1" 2>/dev/null); then
    echo "agy-review: cannot read prompt file: $1" >&2
    exit 64
  fi
else
  if [[ -t 0 ]]; then
    echo "agy-review: usage: agy-review.sh [prompt-file] (or pipe prompt on stdin)" >&2
    exit 64
  fi
  if ! prompt=$(cat); then
    echo "agy-review: cannot read prompt on stdin" >&2
    exit 64
  fi
fi

if [[ -z $prompt ]]; then
  echo "agy-review: empty prompt" >&2
  exit 64
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"

if ! agy -p "$prompt" --output-format json --model "$MODEL" --effort high --print-timeout 10m --disable-slash-commands >result.json 2>agy-stderr.txt; then
  echo "agy-review: agy run failed" >&2
  cat agy-stderr.txt >&2
  exit 1
fi

if ! jq empty result.json 2>/dev/null; then
  echo "agy-review: agy returned unparseable output" >&2
  cat result.json >&2
  exit 1
fi

status=$(jq -r '.status // ""' result.json)
if [[ $status != SUCCESS ]]; then
  echo "agy-review: agy status: ${status:-<none>}" >&2
  cat agy-stderr.txt >&2
  exit 1
fi
if grep -qiE 'timeout|truncat|partial' agy-stderr.txt; then
  echo "agy-review: response may be truncated:" >&2
  cat agy-stderr.txt >&2
  exit 1
fi

denied=$(jq -c '.denied_actions // []' result.json)
if [[ $denied != '[]' ]]; then
  echo "agy-review: request denied:" >&2
  jq '.denied_actions' result.json >&2
  exit 1
fi

response=$(jq -r '.response // ""' result.json)
if [[ -z $response ]]; then
  echo "agy-review: empty response" >&2
  exit 1
fi

printf '%s\n' "$response" || exit 0
