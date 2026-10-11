import json
import os
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import extract


def leaf(pane_id):
    return {"Leaf": pane_id}


def split(axis, a, b):
    return {"Split": {"axis": axis, "ratio": 0.5, "a": a, "b": b}}


def block(block_id, program="zsh"):
    return {"id": block_id, "program": program}


def tab(tab_id, tree, blocks):
    return {"id": tab_id, "splits": tree, "blocks": blocks}


class FindOriginTests(unittest.TestCase):
    def test_direct_column_split_returns_origin(self):
        tree = split("Column", leaf(1), leaf(2))
        self.assertEqual(extract.find_origin(tree, 2), 1)

    def test_nested_tree_returns_origin(self):
        tree = split("Row", leaf(3), split("Column", leaf(1), leaf(2)))
        self.assertEqual(extract.find_origin(tree, 2), 1)

    def test_me_as_a_side_raises(self):
        tree = split("Column", leaf(2), leaf(1))
        with self.assertRaises(LookupError):
            extract.find_origin(tree, 2)

    def test_row_axis_raises(self):
        tree = split("Row", leaf(1), leaf(2))
        with self.assertRaises(LookupError):
            extract.find_origin(tree, 2)

    def test_b_side_split_raises(self):
        tree = split("Column", leaf(1), split("Column", leaf(2), leaf(3)))
        with self.assertRaises(LookupError):
            extract.find_origin(tree, 2)


class FindTabTests(unittest.TestCase):
    def test_finds_tab_across_sessions(self):
        first = tab(10, split("Column", leaf(1), leaf(2)), [block(1), block(2)])
        second = tab(20, split("Column", leaf(3), leaf(4)), [block(3), block(4)])
        ls = {"sessions": [{"tabs": [first]}, {"tabs": [second]}]}
        self.assertEqual(extract.find_tab(ls, 4), second)

    def test_unknown_id_raises(self):
        only = tab(10, split("Column", leaf(1), leaf(2)), [block(1), block(2)])
        ls = {"sessions": [{"tabs": [only]}]}
        with self.assertRaises(LookupError):
            extract.find_tab(ls, 9)


class TextBlocksTests(unittest.TestCase):
    def test_excludes_me_and_file_panes_and_keeps_pip_and_order(self):
        tree = split("Column", leaf(9), leaf(7))
        blocks = [
            block(7, "zsh"),
            block(5, ""),
            block(9, "zsh"),
            block(11, "zsh"),
            block(3, "nvim"),
        ]
        self.assertEqual(extract.text_blocks(tab(20, tree, blocks), 9), [7, 11, 3])


class CaptureTests(unittest.TestCase):
    def run_capture(self, grab, stdout):
        with mock.patch.object(extract, "run_tern") as run_tern:
            run_tern.return_value = mock.Mock(stdout=stdout)
            text = extract.capture("sock", 1, [7, 9, 1], grab)
        return text, run_tern

    def test_window_full_reads_others_then_origin_with_scrollback_and_trims(self):
        stdout = "\n".join(f"l{n}" for n in range(2001))
        text, run_tern = self.run_capture("window full", stdout)
        trimmed = "\n".join(f"l{n}" for n in range(1, 2001))
        self.assertEqual(text, "\n".join([trimmed, trimmed, trimmed]))
        self.assertEqual(
            [call.args for call in run_tern.call_args_list],
            [
                ("sock", "capture", "7", "--surfaces", "--scrollback"),
                ("sock", "capture", "9", "--surfaces", "--scrollback"),
                ("sock", "capture", "1", "--surfaces", "--scrollback"),
            ],
        )

    def test_recent_reads_origin_without_scrollback(self):
        text, run_tern = self.run_capture("recent", "screen\n")
        self.assertEqual(text, "screen\n")
        self.assertEqual(run_tern.call_args_list[0].args, ("sock", "capture", "1", "--surfaces"))
        self.assertEqual(run_tern.call_count, 1)

    def test_window_recent_reads_every_pane_without_scrollback(self):
        text, run_tern = self.run_capture("window recent", "screen")
        self.assertEqual(text, "screen\nscreen\nscreen")
        self.assertEqual(
            [call.args for call in run_tern.call_args_list],
            [
                ("sock", "capture", "7", "--surfaces"),
                ("sock", "capture", "9", "--surfaces"),
                ("sock", "capture", "1", "--surfaces"),
            ],
        )

    def test_full_reads_origin_only_with_scrollback(self):
        text, run_tern = self.run_capture("full", "a\nb\n")
        self.assertEqual(text, "a\nb")
        self.assertEqual(
            [call.args for call in run_tern.call_args_list],
            [("sock", "capture", "1", "--surfaces", "--scrollback")],
        )


class MainTests(unittest.TestCase):
    def test_fzf_failure_reports_and_exits_nonzero(self):
        ls = {"sessions": [{"tabs": [tab(1, split("Column", leaf(5), leaf(9)), [block(5), block(9)])]}]}

        def run_tern(socket, *args):
            if args[0] == "ls":
                return mock.Mock(stdout=json.dumps(ls))
            return mock.Mock(stdout="captured words here")

        env = {"TERN_PANE": "9", "TERN_PANE_SOCKET": "sock"}
        with mock.patch.dict(os.environ, env), mock.patch.object(extract.shutil, "which", return_value="/bin/fzf"), mock.patch.object(
            extract, "run_tern", side_effect=run_tern
        ), mock.patch.object(extract.subprocess, "run", return_value=mock.Mock(returncode=2, stdout="")), mock.patch("sys.stderr"):
            self.assertEqual(extract.main(), 1)


class NextGrabTests(unittest.TestCase):
    def test_cycle_single_pane(self):
        grab = "window full"
        sequence = [grab]
        for _ in range(4):
            grab = extract.next_grab(grab, True)
            sequence.append(grab)
        self.assertEqual(sequence, ["window full", "recent", "full", "recent", "full"])

    def test_cycle_multi_pane(self):
        grab = "window full"
        sequence = [grab]
        for _ in range(4):
            grab = extract.next_grab(grab, False)
            sequence.append(grab)
        self.assertEqual(
            sequence,
            ["window full", "recent", "window recent", "full", "window full"],
        )


if __name__ == "__main__":
    unittest.main()
