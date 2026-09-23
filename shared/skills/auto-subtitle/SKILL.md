---
name: auto-subtitle
description: Transcribe a video locally with Whisper and burn in TikTok/Reels-style karaoke captions, with a human correction pass for names, jargon, and hanzi. Use when the user asks to auto-subtitle, caption, or add subtitles to a video without a paid editor.
---

# Auto subtitle

Turn a talking-head video into a vertical clip with word-by-word highlighted captions, using local Whisper and ffmpeg. Also handles re-rendering after transcript corrections.

```
transcribe.py  ->  words.json + draft.txt
(human correction pass)  ->  script.txt
build_ass.py   ->  subs.ass
burn.sh        ->  final .mp4
```

`words.json` holds word timings and never changes. `script.txt` holds corrected words. `build_ass.py` aligns them, so corrections keep real timing and re-run in seconds.

1. Probe: `ffprobe` for duration, resolution, and audio codec; report them. Check CUDA with `nvidia-smi`. Without it, CPU int8 with `medium` on 4 cores takes about 45 s per audio minute.
2. Transcribe through the process supervisor, not a blocking shell (it takes minutes). Seed `--prompt` with known names; it improves proper nouns.
   ```
   uv run --with faster-whisper python scripts/transcribe.py VIDEO --out-dir WORKDIR \
     --prompt "proper nouns, product names, jargon likely in this video"
   ```
3. Correct: show `draft.txt` and collect all corrections in one round, then write `script.txt`.
   - Whitespace-separated prose in audio order. Substitute words, never reorder.
   - Join a hanzi term and its pinyin with a non-breaking space so they stay one token: `猎人\u00a0(lièrén)`. Same for any unit that must not split.
   - Ask once whether the audience reads simplified or traditional hanzi; apply everywhere.
   - Sections where the user already has burned-in graphics get no captions.
4. Build the ASS. `--mute START-END` drops cues overlapping that window; use it over the user's own graphics. Defaults are the house style (see below).
   ```
   python scripts/build_ass.py --words WORKDIR/words.json --script script.txt --out subs.ass \
     --mute 103-107
   ```
5. Preview before the full encode (seconds, not minutes). Confirm captions clear the face and existing graphics, mute windows are blank, and the highlight lands on the spoken word.
   ```
   scripts/preview.sh VIDEO subs.ass /tmp/prev 12 49 105 173
   ```
6. Burn. 4K to 1080×1920 at CRF 23 cuts size about 20× with no visible loss on a phone.
   ```
   scripts/burn.sh VIDEO subs.ass OUT.mp4 1920 23
   ```
7. Verify the output file (not the preview): sample frames across the timeline, including every mute window, and view them. Report size, resolution, and what each frame showed.
8. Style and text changes rerun steps 4 to 7 only. Never re-transcribe; keep `words.json`.

House style: 4 words per cue; Noto Sans CJK SC Bold 74 px (Latin, pinyin, and hanzi in one font); white with 6 px near-black outline, no shadow; active word `#FFD60A`; `MarginV 300` (below the face, above platform UI); one Dialogue event per word instead of `\k`, so the line never re-wraps.

Traps:
- `str.split()` splits on U+00A0. Tokenize with `re.split(r"[ \t\r\n]+", ...)`, as `build_ass.py` does. Don't "simplify" it.
- Preview frames need `-copyts`; with bare `-ss` the subtitles filter restarts at zero and you review the wrong caption.
- MP4 can't hold `pcm_s24le`; transcode audio to AAC.
- Stacked text means overlapping cues from a hand-edited ASS; the builder clamps each event to the next cue's start.
- Whisper mangles names, URLs, and foreign phrases. Never ship the raw transcript.
- `subtitles=` paths need double escaping: a `:` must arrive as `\\:` or ffmpeg parses it as `original_size` and fails with an image-size error. The scripts handle it; hand-written commands must too.

Scripts: `transcribe.py` (audio extraction and word-level transcription), `build_ass.py` (alignment and karaoke ASS), `burn.sh` (downscale and hardsub), `preview.sh` (frame previews at timestamps).
