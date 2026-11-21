#!/usr/bin/python3

# @raycast.schemaVersion 1
# @raycast.title Fork focused omp session
# @raycast.mode silent
# @raycast.packageName omp
# @raycast.description Forks the omp session running in Tern's shown focused pane into a new right-hand pane.

import json
import os
import socket
import struct
import subprocess
import sys

TERN = "/Applications/Tern.app/Contents/MacOS/tern"
DEFAULT_SOCKET = os.path.expanduser("~/Library/Application Support/Tern/daemon.sock")
SELECTION_VARS = ("TERN_PANE", "TERN_PANE_SOCKET", "TERN_WINDOW_KEY", "TERN_WINDOW_SOCKET")
CONNECT_TIMEOUT = 10.0
IO_TIMEOUT = 30.0
SUBPROCESS_TIMEOUT = 30.0
MAX_FRAME_BYTES = 256 << 20
FORK_REQUEST_ID = 1


class SelectionError(Exception):
    pass


class ProtocolError(Exception):
    pass


def _read_exact(connection: socket.socket, count: int) -> bytes:
    chunks = []
    remaining = count
    while remaining:
        chunk = connection.recv(remaining)
        if not chunk:
            raise ProtocolError(
                f"Tern closed the connection mid-frame ({count - remaining} of {count} bytes read)"
            )
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def receive_frame(connection: socket.socket) -> dict:
    (length,) = struct.unpack("<I", _read_exact(connection, 4))
    if length > MAX_FRAME_BYTES:
        raise ProtocolError(f"Tern sent a {length}-byte frame (limit {MAX_FRAME_BYTES})")
    payload = _read_exact(connection, length)
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolError(f"Tern sent a frame that is not valid UTF-8 JSON: {error}") from error
    if not isinstance(message, dict):
        raise ProtocolError("Tern sent a frame that is not a JSON object")
    return message


def send_frame(connection: socket.socket, message: dict) -> None:
    payload = json.dumps(message).encode("utf-8")
    connection.sendall(struct.pack("<I", len(payload)) + payload)


def _window_keys(snapshot: dict) -> set:
    clients = snapshot.get("clients") or []
    return {client.get("window") for client in clients if client.get("kind") == "window"}


def focused_pane(snapshot: dict) -> int:
    windows = _window_keys(snapshot)
    if len(windows) != 1:
        raise SelectionError(f"expected exactly one Tern window, found {len(windows)}")

    focused = []
    for session in snapshot.get("sessions") or []:
        if session.get("shown") is not True:
            continue
        for tab in session.get("tabs") or []:
            if tab.get("shown") is not True:
                continue
            for block in tab.get("blocks") or []:
                if block.get("focused") is True:
                    focused.append(block)
    if len(focused) != 1:
        raise SelectionError(
            f"expected exactly one focused block in the shown tab of a shown session, found {len(focused)}"
        )
    pane_id = focused[0].get("id")
    if not isinstance(pane_id, int):
        raise SelectionError(f"focused block has no pane id: {focused[0]!r}")

    panes = snapshot.get("panes") or []
    entries = [pane for pane in panes if pane.get("pane") == pane_id]
    if not entries:
        raise SelectionError(f"focused pane {pane_id} is missing from the daemon's pane list")
    session_file = entries[0].get("omp_session_file")
    if not isinstance(session_file, str) or not session_file:
        raise SelectionError(f"focused pane {pane_id} has no omp_session_file (not an omp session)")
    return pane_id


def _socket_path() -> str:
    return os.environ.get("TERN_DAEMON_SOCKET") or DEFAULT_SOCKET


def _selection_env(socket_path: str) -> dict:
    env = {name: value for name, value in os.environ.items() if name not in SELECTION_VARS}
    env["TERN_DAEMON_SOCKET"] = socket_path
    return env


def _inspect_snapshot(socket_path: str) -> dict:
    try:
        result = subprocess.run(
            [TERN, "inspect", "--json"],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            env=_selection_env(socket_path),
        )
    except subprocess.TimeoutExpired as error:
        raise SelectionError(f"`tern inspect --json` timed out after {SUBPROCESS_TIMEOUT:g}s") from error
    except OSError as error:
        raise SelectionError(f"could not run {TERN}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise SelectionError(f"`tern inspect --json` failed ({result.returncode}): {detail}")
    try:
        snapshot = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SelectionError(f"`tern inspect --json` printed invalid JSON: {error}") from error
    if not isinstance(snapshot, dict):
        raise SelectionError("`tern inspect --json` printed a JSON value that is not an object")
    return snapshot


def _connect(socket_path: str) -> socket.socket:
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.settimeout(CONNECT_TIMEOUT)
        connection.connect(socket_path)
        connection.settimeout(IO_TIMEOUT)
        return connection
    except OSError as error:
        connection.close()
        raise ProtocolError(f"could not connect to the Tern daemon socket {socket_path}: {error}") from error


def _request(connection: socket.socket, request: dict) -> dict:
    send_frame(connection, request)
    reply = receive_frame(connection)
    channel = "fork" if "fork" in reply else None
    if channel is None or reply.get("id") != request["id"]:
        raise ProtocolError(f"Tern answered a frame this script cannot correlate: {json.dumps(reply)[:200]}")
    answer = reply[channel]
    if isinstance(answer, dict) and "error" in answer:
        error = answer["error"]
        kind = error.get("kind") if isinstance(error, dict) else "failed"
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise ProtocolError(f"Tern refused the fork ({kind}): {message}")
    if not (isinstance(answer, dict) and isinstance(answer.get("ok"), dict)):
        raise ProtocolError(f"Tern sent a malformed fork answer: {json.dumps(answer)[:200]}")
    return answer["ok"]


def fork_focused() -> int:
    socket_path = _socket_path()
    pane_id = focused_pane(_inspect_snapshot(socket_path))

    connection = _connect(socket_path)
    try:
        welcome = _request_hello(connection)
        if not isinstance(welcome.get("ops"), list) or "fork" not in welcome["ops"]:
            raise ProtocolError("this Tern daemon does not answer fork requests")
        result = _request(connection, {"id": FORK_REQUEST_ID, "fork": {"block": pane_id, "dir": "right"}})
    except OSError as error:
        raise ProtocolError(f"Tern daemon connection failed: {error}") from error
    finally:
        connection.close()

    new_block = result.get("block")
    if not isinstance(new_block, int):
        raise ProtocolError(f"Tern's fork result has no block: {json.dumps(result)[:200]}")
    return new_block


def _request_hello(connection: socket.socket) -> dict:
    send_frame(connection, {"hello": {}})
    reply = receive_frame(connection)
    welcome = reply.get("welcome")
    if not isinstance(welcome, dict):
        raise ProtocolError(f"Tern did not send a welcome: {json.dumps(reply)[:200]}")
    return welcome


def main() -> int:
    try:
        new_block = fork_focused()
    except (SelectionError, ProtocolError, OSError) as error:
        print(f"omp-fork: {error}")
        return 1
    print(f"Forked the focused omp session into pane {new_block}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
