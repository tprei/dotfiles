import argparse
import difflib
import json
import re
import sys

NB = "\u00a0"


def parse_mute_window(value):
    match = re.fullmatch(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)", value)
    if not match:
        raise argparse.ArgumentTypeError(f"invalid --mute window {value!r}: expected START-END in seconds")
    start, end = float(match.group(1)), float(match.group(2))
    if end <= start:
        raise argparse.ArgumentTypeError(f"invalid --mute window {value!r}: end must be greater than start")
    return start, end


def parse_play_res(value):
    match = re.fullmatch(r"(\d+)x(\d+)", value)
    if not match:
        raise argparse.ArgumentTypeError(f"invalid --play-res {value!r}: expected WIDTHxHEIGHT")
    return int(match.group(1)), int(match.group(2))


def norm(token):
    token = token.lower().replace(NB, " ")
    token = re.sub(r"\(.*?\)", "", token)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", token)


def align_words(src, tokens):
    matcher = difflib.SequenceMatcher(
        None, [norm(w["text"]) for w in src], [norm(t) for t in tokens], autojunk=False
    )
    timed = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                timed.append((src[i1 + offset]["start"], src[i1 + offset]["end"], tokens[j1 + offset]))
            continue
        if j1 == j2:
            continue
        if i1 < i2:
            start, end = src[i1]["start"], src[i2 - 1]["end"]
        else:
            start = src[i1 - 1]["end"] if i1 > 0 else 0.0
            end = src[i1]["start"] if i1 < len(src) else start + 0.4 * (j2 - j1)
            if end <= start:
                end = start + 0.4 * (j2 - j1)
        step = (end - start) / (j2 - j1)
        for offset in range(j2 - j1):
            timed.append((start + offset * step, start + (offset + 1) * step, tokens[j1 + offset]))
    return timed


def chunk_cues(timed, max_words, max_dur, max_gap):
    cues = []
    cur = []
    for start, end, text in timed:
        if cur:
            breaks = (
                len(cur) >= max_words
                or end - cur[0][0] > max_dur
                or start - cur[-1][1] > max_gap
                or cur[-1][2][-1] in ".!?,"
            )
            if breaks:
                cues.append(cur)
                cur = []
        cur.append((start, end, text))
    if cur:
        cues.append(cur)
    return cues


def overlaps_mute(cue, mutes):
    cue_start, cue_end = cue[0][0], cue[-1][1]
    return any(cue_end > start and cue_start < end for start, end in mutes)


def ts(value):
    cs = int(round(value * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def build_events(cues, highlight, primary):
    lines = []
    for c, cue in enumerate(cues):
        limit = cues[c + 1][0][0] if c + 1 < len(cues) else cue[-1][1] + 0.4
        limit = min(limit, cue[-1][1] + 0.4)
        cursor = cue[0][0]
        for idx, (start, _, _) in enumerate(cue):
            seg_start = max(start, cursor)
            seg_end = cue[idx + 1][0] if idx + 1 < len(cue) else limit
            seg_end = min(seg_end, limit)
            if seg_end - seg_start < 0.02:
                continue
            cursor = seg_end
            parts = []
            for k, (_, _, text) in enumerate(cue):
                parts.append(f"{{\\c{highlight}}}{text}{{\\c{primary}}}" if k == idx else text)
            body = " ".join(parts)
            lines.append(f"Dialogue: 0,{ts(seg_start)},{ts(seg_end)},Pop,,,,,{body}")
    return lines


def render_header(font, font_size, primary, outline_colour, outline, margin_h, margin_v, play_res):
    play_res_x, play_res_y = play_res
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,{font},{font_size},{primary},{primary},{outline_colour},&H00000000&,-1,0,0,0,100,100,0,0,1,{outline},0,2,{margin_h},{margin_h},{margin_v},1

[Events]
Format: Layer, Start, End, Style, MarginL, MarginR, MarginV, Effect, Text
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Build a karaoke-style ASS subtitle track from word timings and a corrected script.")
    parser.add_argument("--words", required=True, help="path to words.json produced by transcribe.py")
    parser.add_argument("--script", required=True, help="path to the human-corrected transcript text file")
    parser.add_argument("--out", required=True, help="output .ass path")
    parser.add_argument("--max-words", type=int, default=4, help="max words per cue")
    parser.add_argument("--max-dur", type=float, default=2.6, help="max cue duration in seconds")
    parser.add_argument("--max-gap", type=float, default=0.7, help="max inter-word gap in seconds before a new cue starts")
    parser.add_argument("--font", default="Noto Sans CJK SC", help="style font name")
    parser.add_argument("--font-size", type=int, default=74, help="style font size")
    parser.add_argument("--margin-v", type=int, default=300, help="style vertical margin")
    parser.add_argument("--margin-h", type=int, default=90, help="style left/right margin")
    parser.add_argument("--outline", type=int, default=6, help="style outline width")
    parser.add_argument("--primary", default="&H00FFFFFF&", help="primary (and secondary) text colour, ASS &HAABBGGRR& format")
    parser.add_argument("--highlight", default="&H000AD6FF&", help="active-word highlight colour, ASS &HAABBGGRR& format")
    parser.add_argument("--outline-colour", dest="outline_colour", default="&H00101010&", help="text outline colour, ASS &HAABBGGRR& format")
    parser.add_argument("--play-res", type=parse_play_res, default=(1080, 1920), help="script play resolution as WIDTHxHEIGHT")
    parser.add_argument("--mute", action="append", type=parse_mute_window, default=[], help="START-END window in seconds to drop cues from, repeatable")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.words, encoding="utf-8") as fh:
        src = json.load(fh)
    with open(args.script, encoding="utf-8") as fh:
        tokens = re.split(r"[ \t\r\n]+", fh.read().strip())

    timed = align_words(src, tokens)
    cues = chunk_cues(timed, args.max_words, args.max_dur, args.max_gap)
    kept = [cue for cue in cues if not overlaps_mute(cue, args.mute)]
    dropped = len(cues) - len(kept)

    header = render_header(
        args.font,
        args.font_size,
        args.primary,
        args.outline_colour,
        args.outline,
        args.margin_h,
        args.margin_v,
        args.play_res,
    )
    lines = build_events(kept, args.highlight, args.primary)

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(header + "\n".join(lines) + "\n")

    last_end = kept[-1][-1][1] if kept else 0.0
    print(
        f"cues={len(kept)} events={len(lines)} dropped={dropped} last={last_end:.1f}s",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
