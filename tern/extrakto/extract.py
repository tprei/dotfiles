#!/usr/bin/env python3
"""Tern port of the extrakto tmux plugin.

Launched by the extrakto window plugin as `tern-extrakto` in a zoomed split under the focused pane.
"""

import base64
import json
import os
import shlex
import shutil
import subprocess
import sys
from typing import Optional

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, ROOT)

from extrakto import Extrakto, get_lines

HELP_PATH = os.path.join(ROOT, "HELP.md")

FULL_LINES = 2000
NO_MATCH = "NO MATCH - use a different filter"
NEXT_FILTER = {"word": "all", "all": "line", "line": "word"}
BOLD = "\033[1m"
YELLOW = "\033[0;33m"
OFF = "\033[0m"
FZF_ERROR = 2


def run_tern(socket: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["tern", *args], check=True, capture_output=True, text=True, timeout=20, env={**os.environ, "TERN_DAEMON_SOCKET": socket})


def find_tab(ls: dict, me: int) -> dict:
    for session in ls["sessions"]:
        for tab in session["tabs"]:
            if any(block["id"] == me for block in tab["blocks"]):
                return tab
    raise LookupError(f"pane {me} is in no tab")


def split_origin(tree: dict, me: int) -> Optional[int]:
    if "Split" not in tree:
        return None
    node = tree["Split"]
    if node["axis"] == "Column" and node["b"] == {"Leaf": me} and "Leaf" in node["a"]:
        return node["a"]["Leaf"]
    origin = split_origin(node["a"], me)
    if origin is None:
        origin = split_origin(node["b"], me)
    return origin


def find_origin(tree: dict, me: int) -> int:
    origin = split_origin(tree, me)
    if origin is None:
        raise LookupError("can't find the pane extrakto split from")
    return origin


def text_blocks(tab: dict, me: int) -> list[int]:
    return [block["id"] for block in tab["blocks"] if block["id"] != me and block["program"] != ""]


def next_grab(grab: str, single_pane: bool) -> str:
    if grab == "recent":
        return "full" if single_pane else "window recent"
    if grab == "window recent":
        return "full"
    if grab == "full":
        return "recent" if single_pane else "window full"
    return "recent"


def capture(socket: str, origin: int, blocks: list[int], grab: str) -> str:
    pane_ids = []
    if grab.startswith("window"):
        pane_ids = [pane_id for pane_id in blocks if pane_id != origin]
    pane_ids.append(origin)
    texts = []
    for pane_id in pane_ids:
        args = ["capture", str(pane_id), "--surfaces"]
        if grab in ("recent", "window recent"):
            texts.append(run_tern(socket, *args).stdout)
        else:
            args.append("--scrollback")
            text = run_tern(socket, *args).stdout
            texts.append("\n".join(text.removesuffix("\n").split("\n")[-FULL_LINES:]))
    return "\n".join(texts)


def candidates(filter_name: str, text: str) -> list[str]:
    if filter_name == "all":
        extrakto = Extrakto(alt=True, prefix_name=True)
        results: list[str] = []
        for name in extrakto.all():
            results += extrakto[name].filter(text)
    elif filter_name == "line":
        results = get_lines(text)
    else:
        extrakto = Extrakto(alt=False, prefix_name=False)
        results = extrakto[filter_name].filter(text)
    if not results:
        results = [NO_MATCH]
    results.reverse()
    return list(dict.fromkeys(results))


def selection_items(filter_name: str, selection: list[str]) -> list[str]:
    if filter_name != "all":
        return list(selection)
    items = []
    for entry in selection:
        parts = entry.split(": ", 1)
        items.append(parts[1] if len(parts) == 2 else entry)
    return items


def joined(filter_name: str, items: list[str]) -> str:
    separator = "\n" if filter_name in ("all", "line") else " "
    return separator.join(items)


def header(filter_name: str, grab: str) -> str:
    parts = [
        f"{BOLD}tab{OFF}=insert",
        f"{BOLD}enter{OFF}=copy",
        f"{BOLD}ctrl-e{OFF}=edit",
        f"{BOLD}ctrl-f{OFF}=filter [{YELLOW}{BOLD}{filter_name}{OFF}]",
        f"{BOLD}ctrl-g{OFF}=grab [{YELLOW}{BOLD}{grab}{OFF}]",
        f"{BOLD}ctrl-l{OFF}=help",
    ]
    return ", ".join(parts).replace("ctrl-", "^")


def run_fzf(query: str, header_text: str, data: str) -> tuple[str, str, list[str]]:
    env = {k: v for k, v in os.environ.items() if k not in ("FZF_DEFAULT_OPTS", "FZF_DEFAULT_OPTS_FILE")}
    command = [
        "fzf",
        "--multi",
        "--print-query",
        f"--query={query}",
        f"--header={header_text}",
        "--expect=ctrl-c,ctrl-g,esc",
        "--expect=tab,enter,ctrl-f,ctrl-e,ctrl-g,ctrl-l",
        "--tiebreak=index",
        "--layout=default",
        "--no-info",
    ]
    result = subprocess.run(command, input=data + "\n", stdout=subprocess.PIPE, text=True, env=env)
    if result.returncode == FZF_ERROR:
        raise subprocess.CalledProcessError(result.returncode, command)
    lines = result.stdout.split("\n")[:-1]
    query_out, key, *selection = lines
    return query_out, key, selection


def copy_text(text: str) -> None:
    with open("/dev/tty", "w") as tty:
        tty.write("\033]52;c;" + base64.b64encode(text.encode()).decode() + "\a")


def insert_text(socket: str, origin: int, text: str) -> None:
    run_tern(socket, "send", str(origin), "paste", text)


def edit_selection(socket: str, origin: int, items: list[str]) -> None:
    command = '"${EDITOR:-vi}" -- ' + " ".join(shlex.quote(item) for item in items)
    run_tern(socket, "run", str(origin), command)


def show_help() -> None:
    subprocess.run(["less", "-+EF", HELP_PATH])


def fail(message: str) -> int:
    print("extrakto: %s" % message, file=sys.stderr)
    return 1


def process_failure(e: subprocess.CalledProcessError) -> int:
    if e.stderr:
        return fail(f"{e}: {e.stderr.strip()}")
    return fail(str(e))


def main() -> int:
    pane = os.environ.get("TERN_PANE", "")
    socket = os.environ.get("TERN_PANE_SOCKET", "")
    if not pane:
        return fail("TERN_PANE is not set")
    if not socket:
        return fail("TERN_PANE_SOCKET is not set")
    if not shutil.which("fzf"):
        return fail("fzf is not installed")

    me = int(pane)
    try:
        ls = json.loads(run_tern(socket, "ls", "--json").stdout)
        tab = find_tab(ls, me)
        origin = find_origin(tab["splits"], me)
        blocks = text_blocks(tab, me)
    except LookupError as e:
        return fail(str(e))
    except subprocess.CalledProcessError as e:
        return process_failure(e)

    single_pane = blocks == [origin]
    filter_name = "word"
    grab = "window full"
    query = ""

    try:
        while True:
            text = capture(socket, origin, blocks, grab)
            entries = candidates(filter_name, text)
            query, key, selection = run_fzf(query, header(filter_name, grab), "\n".join(entries))
            items = selection_items(filter_name, selection)

            if key in ("ctrl-c", "esc"):
                return 0
            if key == "tab":
                insert_text(socket, origin, joined(filter_name, items))
                return 0
            if key == "enter":
                copy_text(joined(filter_name, items))
                return 0
            if key == "ctrl-e":
                edit_selection(socket, origin, items)
                return 0
            if key == "ctrl-f":
                filter_name = NEXT_FILTER[filter_name]
            elif key == "ctrl-g":
                grab = next_grab(grab, single_pane)
            elif key == "ctrl-l":
                show_help()
    except subprocess.CalledProcessError as e:
        return process_failure(e)


if __name__ == "__main__":
    sys.exit(main())
