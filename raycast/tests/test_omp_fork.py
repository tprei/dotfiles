import importlib.util
import json
import os
import struct
import sys
import unittest

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.realpath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "omp-fork.py")
spec = importlib.util.spec_from_file_location("omp_fork", SCRIPT)
omp_fork = importlib.util.module_from_spec(spec)
spec.loader.exec_module(omp_fork)


def block(block_id, focused=False):
    return {"id": block_id, "program": "/bin/zsh", "focused": focused, "live": True}


def tab(tab_id, blocks, shown=True):
    return {"id": tab_id, "number": 1, "shown": shown, "blocks": blocks, "splits": {"Leaf": blocks[0]["id"]}}


def session(session_id, tabs, shown=True):
    return {"id": session_id, "name": "Default", "shown": shown, "tabs": tabs}


def pane_entry(pane_id, omp_session_file="/tmp/session.jsonl"):
    entry = {"pane": pane_id, "program": "omp", "cwd": "/tmp"}
    if omp_session_file is not None:
        entry["omp_session_file"] = omp_session_file
    return entry


def client(kind, window="", conn=1):
    return {"conn": conn, "window": window, "kind": kind, "since": 0}


def snapshot(sessions=(), panes=(), clients=()):
    return {"sessions": list(sessions), "detached": [], "panes": list(panes), "clients": list(clients)}


def happy_snapshot(pane_id=101):
    sessions = [
        session(
            1,
            [
                tab(11, [block(pane_id, focused=True)], shown=True),
                tab(12, [block(202, focused=True)], shown=False),
            ],
            shown=True,
        ),
        session(2, [tab(21, [block(303, focused=True)], shown=True)], shown=False),
    ]
    return snapshot(sessions, [pane_entry(pane_id), pane_entry(202), pane_entry(303)], [client("window")])


def frame_bytes(message):
    payload = json.dumps(message).encode("utf-8")
    return struct.pack("<I", len(payload)) + payload


class ChunkedConnection:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def recv(self, size):
        if not self.chunks:
            return b""
        chunk = self.chunks[0][:size]
        self.chunks[0] = self.chunks[0][size:]
        if not self.chunks[0]:
            self.chunks.pop(0)
        return chunk


class FocusedPaneTests(unittest.TestCase):
    def test_returns_shown_tab_block_ignoring_hidden_tabs_and_sessions(self):
        self.assertEqual(omp_fork.focused_pane(happy_snapshot()), 101)

    def test_hidden_tab_focused_block_never_wins(self):
        sessions = [session(1, [tab(11, [block(202, focused=True)], shown=False)], shown=True)]
        with self.assertRaises(omp_fork.SelectionError) as raised:
            omp_fork.focused_pane(snapshot(sessions, [pane_entry(202)], [client("window")]))
        self.assertIn("found 0", str(raised.exception))

    def test_hidden_session_focused_block_never_wins(self):
        sessions = [
            session(1, [tab(11, [block(202)], shown=True)], shown=True),
            session(2, [tab(21, [block(303, focused=True)], shown=True)], shown=False),
        ]
        with self.assertRaises(omp_fork.SelectionError) as raised:
            omp_fork.focused_pane(snapshot(sessions, [pane_entry(202), pane_entry(303)], [client("window")]))
        self.assertIn("found 0", str(raised.exception))

    def test_two_shown_sessions_are_ambiguous(self):
        sessions = [
            session(1, [tab(11, [block(101, focused=True)], shown=True)], shown=True),
            session(2, [tab(21, [block(303, focused=True)], shown=True)], shown=True),
        ]
        state = snapshot(sessions, [pane_entry(101), pane_entry(303)], [client("window")])
        with self.assertRaises(omp_fork.SelectionError) as raised:
            omp_fork.focused_pane(state)
        self.assertIn("found 2", str(raised.exception))

    def test_two_focused_blocks_in_one_shown_tab_are_ambiguous(self):
        sessions = [session(1, [tab(11, [block(101, focused=True), block(202, focused=True)], shown=True)])]
        state = snapshot(sessions, [pane_entry(101), pane_entry(202)], [client("window")])
        with self.assertRaises(omp_fork.SelectionError):
            omp_fork.focused_pane(state)

    def test_two_windows_are_ambiguous(self):
        clients = [client("window", "w1", conn=1), client("window", "w2", conn=2)]
        state = snapshot([session(1, [tab(11, [block(101, focused=True)])])], [pane_entry(101)], clients)
        with self.assertRaises(omp_fork.SelectionError) as raised:
            omp_fork.focused_pane(state)
        self.assertIn("found 2", str(raised.exception))

    def test_no_window_client_fails(self):
        state = snapshot([session(1, [tab(11, [block(101, focused=True)])])], [pane_entry(101)], [])
        with self.assertRaises(omp_fork.SelectionError) as raised:
            omp_fork.focused_pane(state)
        self.assertIn("found 0", str(raised.exception))

    def test_cli_clients_do_not_count_as_windows(self):
        clients = [client("cli", conn=1), client("cli", conn=2)]
        state = snapshot([session(1, [tab(11, [block(101, focused=True)])])], [pane_entry(101)], clients)
        with self.assertRaises(omp_fork.SelectionError):
            omp_fork.focused_pane(state)

    def test_duplicate_entries_of_one_window_count_once(self):
        clients = [client("window", "", conn=1), client("window", "", conn=2)]
        state = snapshot([session(1, [tab(11, [block(101, focused=True)])])], [pane_entry(101)], clients)
        self.assertEqual(omp_fork.focused_pane(state), 101)

    def test_missing_pane_entry_fails(self):
        sessions = [session(1, [tab(11, [block(999, focused=True)], shown=True)])]
        state = snapshot(sessions, [pane_entry(101)], [client("window")])
        with self.assertRaises(omp_fork.SelectionError) as raised:
            omp_fork.focused_pane(state)
        self.assertIn("missing from the daemon's pane list", str(raised.exception))

    def test_pane_without_omp_session_file_fails(self):
        sessions = [session(1, [tab(11, [block(101, focused=True)], shown=True)])]
        state = snapshot(sessions, [pane_entry(101, omp_session_file=None)], [client("window")])
        with self.assertRaises(omp_fork.SelectionError) as raised:
            omp_fork.focused_pane(state)
        self.assertIn("omp_session_file", str(raised.exception))

    def test_omp_session_file_fails(self):
        sessions = [session(1, [tab(11, [block(101, focused=True)], shown=True)])]
        state = snapshot(sessions, [pane_entry(101, omp_session_file="")], [client("window")])
        with self.assertRaises(omp_fork.SelectionError):
            omp_fork.focused_pane(state)


class FrameTests(unittest.TestCase):
    def test_receive_reassembles_fragmented_frame(self):
        data = frame_bytes({"welcome": {"ops": ["fork"]}})
        chunks = [data[:2], data[2:5], data[5:9], data[9:]]
        self.assertEqual(omp_fork.receive_frame(ChunkedConnection(chunks)), {"welcome": {"ops": ["fork"]}})

    def test_eof_before_header_raises(self):
        with self.assertRaises(omp_fork.ProtocolError) as raised:
            omp_fork.receive_frame(ChunkedConnection([]))
        self.assertIn("closed the connection", str(raised.exception))

    def test_eof_mid_payload_raises(self):
        data = frame_bytes({"a": 1})
        with self.assertRaises(omp_fork.ProtocolError) as raised:
            omp_fork.receive_frame(ChunkedConnection([data[:4], data[4:6]]))
        self.assertIn("closed the connection", str(raised.exception))

    def test_oversized_frame_raises_without_reading_payload(self):
        header = struct.pack("<I", omp_fork.MAX_FRAME_BYTES + 1)
        with self.assertRaises(omp_fork.ProtocolError) as raised:
            omp_fork.receive_frame(ChunkedConnection([header]))
        self.assertIn("byte frame", str(raised.exception))

    def test_non_object_frame_raises(self):
        payload = b"[]"
        data = struct.pack("<I", len(payload)) + payload
        with self.assertRaises(omp_fork.ProtocolError) as raised:
            omp_fork.receive_frame(ChunkedConnection([data]))
        self.assertIn("not a JSON object", str(raised.exception))

    def test_non_utf8_frame_raises(self):
        payload = b"\xff\xfe{}"
        data = struct.pack("<I", len(payload)) + payload
        with self.assertRaises(omp_fork.ProtocolError):
            omp_fork.receive_frame(ChunkedConnection([data]))


if __name__ == "__main__":
    unittest.main()
