#!/usr/bin/env bash
set -euo pipefail

MODEL=gemini-3.8-flash-low

if (( $# > 1 )); then
  echo "agy-review: usage: agy-review.sh [prompt-file] (or pipe prompt on stdin)" >&2
  exit 64
fi

if (( $# == 1 )); then
  if [[ ! -f $1 || ! -r $1 ]]; then
    echo "agy-review: cannot read prompt file: $1" >&2
    exit 64
  fi
  prompt=$(cat -- "$1")
else
  prompt=$(cat)
fi

if [[ -z $prompt ]]; then
  echo "agy-review: empty prompt" >&2
  exit 64
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"

if ! agy -p "$prompt" --output-format json --model "$MODEL" --effort low --print-timeout 10m >result.json 2>agy-stderr.txt; then
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

printf '%s\n' "$response"
