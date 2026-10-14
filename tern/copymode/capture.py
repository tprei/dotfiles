#!/usr/bin/env python3

import argparse
import codecs
import os
import subprocess
import sys
import threading
from html.parser import HTMLParser

CHUNK = 65536
PANE_IDENTITY = ("TERN_PANE", "TERN_PANE_SOCKET", "TERN_WINDOW_KEY", "TERN_WINDOW_SOCKET")


def fail(message: str) -> int:
    print("copymode: %s" % message, file=sys.stderr)
    return 1


def discard(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        return
    except OSError as e:
        print("copymode: cannot remove %s: %s" % (path, e.strerror or e), file=sys.stderr)


def parse_color(value: str):
    if value.startswith("#"):
        digits = value[1:]
        if len(digits) == 3:
            return tuple(int(c * 2, 16) for c in digits)
        if len(digits) == 6:
            return tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4))
        return None
    if value.startswith("rgb(") and value.endswith(")"):
        parts = [part.strip() for part in value[4:-1].split(",")]
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            return tuple(int(part) for part in parts)
    return None


def parse_style(text: str) -> dict:
    style: dict = {}
    for decl in text.split(";"):
        prop, sep, value = decl.partition(":")
        prop = prop.strip().lower()
        value = value.strip().lower()
        if not sep or not prop or not value:
            continue
        if prop == "color":
            rgb = parse_color(value)
            if rgb:
                style["fg"] = rgb
        elif prop == "background-color":
            rgb = parse_color(value)
            if rgb:
                style["bg"] = rgb
        elif prop == "font-weight":
            if value == "bold" or (value.isdigit() and int(value) >= 600):
                style["bold"] = True
        elif prop == "opacity":
            if value.endswith("%"):
                value = value[:-1]
            try:
                alpha = float(value)
            except ValueError:
                continue
            if alpha < 1:
                style["faint"] = True
        elif prop == "font-style":
            if value == "italic":
                style["italic"] = True
        elif prop == "text-decoration":
            if "underline" in value:
                style["underline"] = True
            if "line-through" in value:
                style["strike"] = True
    return style


def sgr_for(style: dict) -> str:
    parts = []
    if style.get("bold"):
        parts.append("1")
    if style.get("faint"):
        parts.append("2")
    if style.get("italic"):
        parts.append("3")
    if style.get("underline"):
        parts.append("4")
    if style.get("strike"):
        parts.append("9")
    fg = style.get("fg")
    if fg:
        parts.append("38;2;%d;%d;%d" % fg)
    bg = style.get("bg")
    if bg:
        parts.append("48;2;%d;%d;%d" % bg)
    if not parts:
        return "\x1b[0m"
    return "\x1b[0m\x1b[" + ";".join(parts) + "m"


class HtmlToAnsi(HTMLParser):
    def __init__(self, out):
        super().__init__(convert_charrefs=True)
        self.out = out
        self.stack: list[dict] = []

    def effective(self) -> dict:
        style: dict = {}
        for entry in self.stack:
            style.update(entry)
        return style

    def emit(self):
        self.out.write(sgr_for(self.effective()).encode("utf-8"))

    def handle_starttag(self, tag, attrs):
        if tag not in ("pre", "span"):
            return
        style: dict = {}
        for name, value in attrs:
            if name == "style" and value:
                style = parse_style(value)
                break
        self.stack.append(style)
        self.emit()

    def handle_endtag(self, tag):
        if tag in ("pre", "span") and self.stack:
            self.stack.pop()
            self.emit()

    def handle_data(self, data):
        self.out.write(data.encode("utf-8"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="capture.py")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    try:
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
    except FileExistsError:
        return fail("refusing to overwrite existing %s" % args.output)
    except OSError as e:
        return fail("cannot create %s: %s" % (args.output, e.strerror or e))

    env = {name: value for name, value in os.environ.items() if name not in PANE_IDENTITY}
    try:
        proc = subprocess.Popen(
            ["tern", "capture", args.origin, "--html", "--scrollback", "--surfaces"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError:
        discard(args.output)
        return fail("tern is not on PATH; install Tern 0.8.3 and its CLI on this host")

    stderr_chunks: list[bytes] = []

    def drain_stderr():
        assert proc.stderr is not None
        for line in proc.stderr:
            stderr_chunks.append(line)

    reader = threading.Thread(target=drain_stderr)
    reader.start()

    try:
        with os.fdopen(fd, "wb") as out:
            decoder = codecs.getincrementaldecoder("utf-8")("replace")
            converter = HtmlToAnsi(out)
            assert proc.stdout is not None
            while True:
                chunk = proc.stdout.read(CHUNK)
                if not chunk:
                    break
                converter.feed(decoder.decode(chunk))
            converter.feed(decoder.decode(b"", True))
            converter.close()
            out.flush()
        status = proc.wait()
    except OSError as e:
        proc.kill()
        proc.wait()
        reader.join()
        discard(args.output)
        return fail("capture failed: %s" % e)

    reader.join()
    if status != 0:
        discard(args.output)
        detail = b"".join(stderr_chunks).decode(errors="replace").strip()
        message = "tern capture exited %d" % status
        return fail(message + (": %s" % detail if detail else ""))

    print("captured pane %s: %d bytes" % (args.origin, os.path.getsize(args.output)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
