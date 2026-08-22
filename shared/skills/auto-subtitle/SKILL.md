---
name: auto-subtitle
description: Transcribe a video locally with Whisper and burn in TikTok/Reels-style karaoke captions, with a human correction pass for names, jargon, and hanzi. Use when the user asks to auto-subtitle, caption, or add subtitles to a video without a paid editor.
---

# Auto subtitle

Turn a raw talking-head video into a shipped vertical clip with word-by-word highlighted captions, using local Whisper and ffmpeg only.

## When to use

- The user asks to subtitle, caption, or auto-sub a video file.
- The user wants CapCut-style animated captions without a paid editor.
- The user asks to re-render captions after correcting the transcript.

## Pipeline

Four stages. Stage 2 is a conversation with the user, not an automated step.

```
transcribe.py  ->  words.json + draft.txt
     (human correction pass)  ->  script.txt
build_ass.py   ->  subs.ass
burn.sh        ->  final .mp4
```

`words.json` holds the word-level timings and never changes. `script.txt` holds the corrected words. `build_ass.py` aligns the two, so corrections keep real speech timing and can be re-run in seconds.

## Instructions

1. **Probe the source.** `ffprobe` for duration, resolution, audio codec. Report them. Check for CUDA (`nvidia-smi`); absent means CPU int8, roughly 45 s of compute per minute of audio with the `medium` model on 4 cores.

2. **Transcribe.**
   ```
   uv run --with faster-whisper python scripts/transcribe.py VIDEO --out-dir WORKDIR \
     --prompt "proper nouns, product names, jargon likely in this video"
   ```
   Run it through the process supervisor, not a blocking shell call — it takes minutes. Seed `--prompt` with names you already know; it measurably improves proper nouns.

3. **Correction pass.** Read `draft.txt` and show the user the transcript. Ask for corrections in one round rather than drip-feeding. Then write `script.txt` with every fix applied. Rules for that file:
   - It is plain prose, whitespace-separated. Word order must still match the audio; only substitute, never reorder.
   - Join a hanzi term and its pinyin gloss with a non-breaking space so they stay one caption token: `猎人\u00a0(lièrén)`. Same for any unit that must never be split across cues.
   - Use the script the user's audience reads — simplified vs traditional hanzi is a real preference; ask once, apply everywhere.
   - Keep the user's own on-screen graphics in mind: sections where they already have burned-in text want no captions at all.

4. **Build the ASS.**
   ```
   python scripts/build_ass.py --words WORKDIR/words.json --script script.txt --out subs.ass \
     --mute 103-107
   ```
   `--mute START-END` drops every cue overlapping that window; use it wherever the user has their own graphics. Defaults produce the house style: 4 words per cue, 74 px Noto Sans CJK SC bold, white with a 6 px near-black outline, active word in `#FFD60A`, `MarginV 300`.

5. **Check frames before the full encode.**
   ```
   scripts/preview.sh VIDEO subs.ass /tmp/prev 12 49 105 173
   ```
   Look at the PNGs. Confirm caption position clears the speaker's face and any existing graphics, that mute windows are actually blank, and that the highlight lands on the spoken word. A full render is minutes; a preview is seconds.

6. **Burn in.**
   ```
   scripts/burn.sh VIDEO subs.ass OUT.mp4 1920 23
   ```
   Downscaling 4K to 1080×1920 at CRF 23 is what makes the file small enough to upload — expect roughly 20× reduction with no visible loss on a phone.

7. **Verify the render.** Sample frames from the *output* file (not the preview) across the timeline, including inside every mute window, and view them. Report file size, resolution, and what each sampled frame showed.

8. **Iterate cheaply.** Style and text changes only need steps 4–7 — never re-transcribe. `words.json` is the expensive artifact; keep it.

## Style defaults

| Property | Value | Why |
|----------|-------|-----|
| Words per cue | 4 | Short bursts read faster than full sentences on a phone. |
| Highlight | `#FFD60A` on white | One accent colour, high contrast against video of any brightness. |
| Font | Noto Sans CJK SC Bold | Covers Latin, pinyin diacritics, and hanzi in one file, so no fallback seams. |
| Outline | 6 px near-black, no shadow | Survives bright and dark backgrounds. |
| `MarginV` | 300 | Below the face, above the platform's bottom UI. |
| Highlight mechanism | one Dialogue event per word | Full control over the active word; simpler than `\k` and never re-wraps. |

## Traps

- **`str.split()` splits on U+00A0.** Tokenize the corrected script with `re.split(r"[ \t\r\n]+", ...)`, or hanzi and pinyin land in different cues. `build_ass.py` already does this; do not "simplify" it.
- **Preview frames need `-copyts`.** With a bare `-ss`, the subtitles filter restarts its timeline at zero and you review the wrong caption.
- **MP4 cannot hold `pcm_s24le`.** Transcode audio to AAC when muxing or the container write fails.
- **Cue overlap looks like flicker.** Events must be clamped to the next cue's start; the builder does this, so any stacked text means the ASS was hand-edited.
- **Whisper mangles domain terms.** Names, product URLs, and foreign-language phrases are wrong until a human fixes them. Never ship the raw transcript.
- **`subtitles=` paths need double escaping.** The filter re-splits on colons after the filtergraph parser unescapes, so a path containing `:` must arrive as `\\:` or ffmpeg reads it as `original_size` and fails with an image-size error. The scripts handle this; hand-written ffmpeg commands must too.

## Reference files

| File | Contents |
|------|----------|
| `scripts/transcribe.py` | Audio extraction plus faster-whisper word-level transcription; writes `words.json` and `draft.txt`. |
| `scripts/build_ass.py` | Aligns the corrected script to word timings and emits karaoke ASS. |
| `scripts/burn.sh` | Downscale plus hardsub encode to a share-ready MP4. |
| `scripts/preview.sh` | Single-frame previews at given timestamps for visual checks. |
