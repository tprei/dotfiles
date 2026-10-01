#!/usr/bin/env python3
"""Ctrl+h/j/k/l for Herdr: forward the key to vim, fzf, ssh, or a nested multiplexer, else move pane focus."""

import json
import os
import re
import subprocess
import sys

PASSTHROUGH = re.compile(r"^(view|l?n?vim?x?|fzf|ssh|mosh-client|tmux|herdr)$")
KEYS = {"left": "ctrl+h", "down": "ctrl+j", "up": "ctrl+k", "right": "ctrl+l"}


def foreground_command(herdr: str, pane: str) -> str:
    output = subprocess.run([herdr, "pane", "process-info", "--pane", pane],
                            capture_output=True, text=True, check=True).stdout
    info = json.loads(output)["result"]["process_info"]
    leader = info["foreground_process_group_id"]
    names = [process["name"] for process in info["foreground_processes"] if process["pid"] == leader]
    return names[0] if names else ""


def navigate(herdr: str, pane: str, direction: str) -> None:
    if PASSTHROUGH.match(foreground_command(herdr, pane)):
        subprocess.run([herdr, "pane", "send-keys", pane, KEYS[direction]], check=True)
    else:
        subprocess.run([herdr, "pane", "focus", "--direction", direction, "--pane", pane],
                       capture_output=True, check=True)


if __name__ == "__main__":
    navigate(os.environ["HERDR_BIN_PATH"], os.environ["HERDR_ACTIVE_PANE_ID"], sys.argv[1])
