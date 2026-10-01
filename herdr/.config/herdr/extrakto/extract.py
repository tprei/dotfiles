"""Herdr port of the extrakto tmux plugin.

Launched as a Herdr popup command bound to `prefix+tab`: `python3 extract.py`.
"""

import base64
import json
import os
import shlex
import shutil
import subprocess
import sys

from extrakto import Extrakto, get_lines

ROOT = os.path.dirname(os.path.realpath(__file__))
HELP_PATH = os.path.join(ROOT, "HELP.md")

NO_MATCH = "NO MATCH - use a different filter"
NEXT_FILTER = {"word": "all", "all": "line", "line": "word"}
BOLD = "\033[1m"
YELLOW = "\033[0;33m"
OFF = "\033[0m"
FZF_ERROR = 2
PASTE_START = "\033[200~"
PASTE_END = "\033[201~"


def herdr_bin() -> str:
    return os.environ.get("HERDR_BIN_PATH") or "herdr"


def run_herdr(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([herdr_bin(), *args], check=True, capture_output=True, text=True, timeout=20)


def pane_list(workspace_id: str) -> list[dict]:
    result = run_herdr("pane", "list", "--workspace", workspace_id)
    return json.loads(result.stdout)["result"]["panes"]


def pane_read(pane_id: str, lines: int) -> str:
    result = run_herdr("pane", "read", pane_id, "--source", "recent-unwrapped", "--lines", str(lines))
    return result.stdout


def next_grab(grab: str, single_pane: bool) -> str:
    if grab == "recent":
        return "full" if single_pane else "window recent"
    if grab == "window recent":
        return "full"
    if grab == "full":
        return "recent" if single_pane else "window full"
    return "recent"


def capture(source: str, panes: list[dict], grab: str) -> str:
    by_id = {pane["pane_id"]: pane for pane in panes}
    tab_id = by_id[source]["tab_id"]
    if grab in ("recent", "window recent"):
        lines = by_id[source]["scroll"]["viewport_rows"] + 10
    else:
        lines = 2000
    pane_ids = []
    if grab.startswith("window"):
        pane_ids = [pane["pane_id"] for pane in panes if pane["tab_id"] == tab_id and pane["pane_id"] != source]
    pane_ids.append(source)
    return "\n".join(pane_read(pane_id, lines) for pane_id in pane_ids)


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
        f"{BOLD}ctrl-o{OFF}=open",
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
        "--expect=tab,enter,ctrl-f,ctrl-e,ctrl-o,ctrl-g,ctrl-l",
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
    if sys.platform == "darwin":
        subprocess.run(["pbcopy"], input=text, text=True, check=True)
    else:
        with open("/dev/tty", "w") as tty:
            tty.write("\033]52;c;" + base64.b64encode(text.encode()).decode() + "\a")


def send_text(pane_id: str, text: str) -> None:
    if "\n" in text:
        text = PASTE_START + text + PASTE_END
    run_herdr("pane", "send-text", pane_id, text)


def open_selection(items: list[str], cwd: str) -> None:
    tool = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen(
        [tool, *items],
        cwd=cwd,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def edit_selection(pane_id: str, items: list[str]) -> None:
    editor = os.environ.get("EDITOR") or "vi"
    command = f"{editor} -- {' '.join(shlex.quote(item) for item in items)}"
    run_herdr("pane", "run", pane_id, command)


def show_help() -> None:
    subprocess.run(["less", "-+EF", HELP_PATH])


def fail(message: str) -> int:
    print("extrakto: %s" % message, file=sys.stderr)
    input("press enter to close... ")
    return 1


def main() -> int:
    pane_id = os.environ.get("HERDR_ACTIVE_PANE_ID", "")
    workspace_id = os.environ.get("HERDR_ACTIVE_WORKSPACE_ID", "")
    if not pane_id:
        return fail("HERDR_ACTIVE_PANE_ID is not set")
    if not workspace_id:
        return fail("HERDR_ACTIVE_WORKSPACE_ID is not set")
    if not shutil.which("fzf"):
        return fail("fzf is not installed")

    try:
        panes = pane_list(workspace_id)
    except subprocess.CalledProcessError as e:
        return fail(str(e))

    sources = [pane for pane in panes if pane["pane_id"] == pane_id]
    if not sources:
        return fail("pane %s not found in workspace %s" % (pane_id, workspace_id))

    single_pane = sum(1 for pane in panes if pane["tab_id"] == sources[0]["tab_id"]) == 1
    filter_name = "word"
    grab = "window full"
    query = ""

    try:
        while True:
            text = capture(pane_id, panes, grab)
            entries = candidates(filter_name, text)
            query, key, selection = run_fzf(query, header(filter_name, grab), "\n".join(entries))
            items = selection_items(filter_name, selection)

            if key in ("ctrl-c", "esc"):
                return 0
            if key == "tab":
                send_text(pane_id, joined(filter_name, items))
                return 0
            if key == "enter":
                copy_text(joined(filter_name, items))
                return 0
            if key == "ctrl-o":
                open_selection(items, os.environ.get("HERDR_ACTIVE_PANE_CWD", ""))
                return 0
            if key == "ctrl-e":
                edit_selection(pane_id, items)
                return 0
            if key == "ctrl-f":
                filter_name = NEXT_FILTER[filter_name]
            elif key == "ctrl-g":
                grab = next_grab(grab, single_pane)
            elif key == "ctrl-l":
                show_help()
    except subprocess.CalledProcessError as e:
        return fail(str(e))


if __name__ == "__main__":
    sys.exit(main())
