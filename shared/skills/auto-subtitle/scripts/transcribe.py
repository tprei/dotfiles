import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from faster_whisper import WhisperModel


def parse_args():
    parser = argparse.ArgumentParser(description="Transcribe a video into word-level timestamps.")
    parser.add_argument("video")
    parser.add_argument("--out-dir", default=".")
    parser.add_argument("--model", default="medium")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--language", default=None)
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--threads", type=int, default=os.cpu_count())
    return parser.parse_args()


def extract_audio(ffmpeg_bin, video, wav_path):
    subprocess.run(
        [
            ffmpeg_bin,
            "-v", "error",
            "-y",
            "-i", str(video),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            str(wav_path),
        ],
        check=True,
    )


def main():
    args = parse_args()

    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin is None:
        print("error: ffmpeg not found on PATH", file=sys.stderr)
        sys.exit(2)

    video = Path(args.video)
    if not video.is_file():
        print(f"error: video file not found: {video}", file=sys.stderr)
        sys.exit(2)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    wav_path = out_dir / "audio.wav"
    words_path = out_dir / "words.json"
    draft_path = out_dir / "draft.txt"

    extract_audio(ffmpeg_bin, video, wav_path)

    model = WhisperModel(
        args.model,
        device="cpu",
        compute_type=args.compute_type,
        cpu_threads=args.threads,
    )

    transcribe_kwargs = dict(
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400),
        language=args.language,
    )
    if args.prompt:
        transcribe_kwargs["initial_prompt"] = args.prompt

    segments, info = model.transcribe(str(wav_path), **transcribe_kwargs)

    words = []
    transcript_parts = []
    for seg in segments:
        seg_text = seg.text.strip()
        if seg_text:
            transcript_parts.append(seg_text)
        for w in seg.words or []:
            token = w.word.strip()
            if token:
                words.append({"start": round(w.start, 3), "end": round(w.end, 3), "text": token})
        print(f"  {seg.end:7.1f}s  {seg_text[:70]}", file=sys.stderr, flush=True)

    with open(words_path, "w", encoding="utf-8") as fh:
        json.dump(words, fh, ensure_ascii=False, indent=2)

    draft = textwrap.fill(" ".join(transcript_parts), width=100)
    with open(draft_path, "w", encoding="utf-8") as fh:
        fh.write(draft + "\n")

    print(
        f"language={info.language} words={len(words)} "
        f"audio={wav_path} words_json={words_path} draft={draft_path}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
