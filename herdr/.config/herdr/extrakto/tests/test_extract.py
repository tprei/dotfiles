import json
import os
import pathlib
import sys
import tomllib
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import extract

ROOT = pathlib.Path(os.path.dirname(os.path.realpath(extract.__file__)))


def pane(pane_id, tab_id, viewport_rows=24):
    return {
        "pane_id": pane_id,
        "tab_id": tab_id,
        "workspace_id": "w1",
        "focused": False,
        "cwd": "/tmp",
        "foreground_cwd": "/tmp",
        "scroll": {"viewport_rows": viewport_rows, "offset_from_bottom": 0, "max_offset_from_bottom": 0},
    }


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


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.panes = [
            pane("w1:p1", "w1:t1", viewport_rows=30),
            pane("w1:p2", "w1:t1"),
            pane("w1:p3", "w1:t2"),
        ]

    def run_capture(self, grab):
        with mock.patch.object(extract.subprocess, "run") as run:
            run.return_value = mock.Mock(stdout="output\n")
            text = extract.capture("w1:p1", self.panes, grab)
        return text, run

    def test_window_grab_reads_same_tab_other_pane_first_then_source(self):
        _, run = self.run_capture("window full")
        pane_args = [call.args[0][3] for call in run.call_args_list]
        self.assertEqual(pane_args, ["w1:p2", "w1:p1"])

    def test_non_window_grab_reads_only_source(self):
        _, run = self.run_capture("full")
        pane_args = [call.args[0][3] for call in run.call_args_list]
        self.assertEqual(pane_args, ["w1:p1"])

    def test_recent_grab_uses_viewport_rows_plus_ten(self):
        _, run = self.run_capture("recent")
        lines_args = [call.args[0][-1] for call in run.call_args_list]
        self.assertEqual(lines_args, ["40"])

    def test_window_recent_grab_uses_viewport_rows_plus_ten_for_every_pane(self):
        _, run = self.run_capture("window recent")
        lines_args = [call.args[0][-1] for call in run.call_args_list]
        self.assertEqual(lines_args, ["40", "40"])

    def test_full_grab_uses_2000_lines(self):
        _, run = self.run_capture("full")
        lines_args = [call.args[0][-1] for call in run.call_args_list]
        self.assertEqual(lines_args, ["2000"])

    def test_window_grab_never_reads_other_tab_pane(self):
        _, run = self.run_capture("window full")
        pane_args = [call.args[0][3] for call in run.call_args_list]
        self.assertNotIn("w1:p3", pane_args)


class CandidatesTests(unittest.TestCase):
    def test_word_filter_is_newest_first_and_deduped(self):
        result = extract.candidates("word", "hello world hello there world hello")
        self.assertEqual(result, ["hello", "world", "there"])

    def test_all_filter_yields_prefixed_url_url2_and_path(self):
        result = extract.candidates("all", "see https://example.com/a/b and ./src/main.py")
        self.assertEqual(
            result,
            ["url: https://example.com/a/b", "url2: example.com", "path: ./src/main.py"],
        )

    def test_empty_input_gives_no_match_row(self):
        self.assertEqual(extract.candidates("word", ""), [extract.NO_MATCH])

    def test_line_filter_returns_stripped_lines(self):
        result = extract.candidates("line", "  first line here  \n  second line here  \n")
        self.assertEqual(result, ["second line here", "first line here"])


class SelectionTests(unittest.TestCase):
    def test_prefix_stripped_only_for_all(self):
        self.assertEqual(
            extract.selection_items("all", ["url: https://x.com", "path: ./a.py"]),
            ["https://x.com", "./a.py"],
        )
        self.assertEqual(extract.selection_items("word", ["foo", "bar"]), ["foo", "bar"])
        self.assertEqual(extract.selection_items("line", ["a line here"]), ["a line here"])

    def test_joined_separator_by_filter(self):
        self.assertEqual(extract.joined("all", ["a", "b"]), "a\nb")
        self.assertEqual(extract.joined("line", ["a", "b"]), "a\nb")
        self.assertEqual(extract.joined("word", ["a", "b"]), "a b")


class SendTextTests(unittest.TestCase):
    def sent(self, text):
        with mock.patch.object(extract.subprocess, "run") as run:
            extract.send_text("w1:p1", text)
        return run.call_args.args[0][-1]

    def test_multiline_text_is_bracketed_paste_so_shells_do_not_run_it(self):
        self.assertEqual(self.sent("echo one\necho two"), "\033[200~echo one\necho two\033[201~")

    def test_single_line_text_is_typed_as_is(self):
        self.assertEqual(self.sent("./src/main.py"), "./src/main.py")


class MainDispatchTests(unittest.TestCase):
    def setUp(self):
        self.panes_payload = {
            "result": {
                "panes": [pane("w1:p1", "w1:t1", viewport_rows=30)],
            }
        }
        self.env = {
            "HERDR_ACTIVE_PANE_ID": "w1:p1",
            "HERDR_ACTIVE_WORKSPACE_ID": "w1",
            "HERDR_ACTIVE_PANE_CWD": "/tmp",
        }

    def test_filter_cycle_then_insert(self):
        with mock.patch.dict(os.environ, self.env, clear=False), \
                mock.patch.object(extract.shutil, "which", return_value="/usr/bin/fzf"), \
                mock.patch.object(extract, "run_fzf") as run_fzf, \
                mock.patch.object(extract, "candidates", wraps=extract.candidates) as candidates, \
                mock.patch.object(extract.subprocess, "run") as run:
            run.side_effect = [
                mock.Mock(stdout=json.dumps(self.panes_payload)),
                mock.Mock(stdout="hello world\n"),
                mock.Mock(stdout="hello world\n"),
                mock.Mock(),
            ]
            run_fzf.side_effect = [
                ("", "ctrl-f", []),
                ("", "tab", ["hello"]),
            ]
            result = extract.main()

        self.assertEqual(result, 0)
        filter_calls = [call.args[0] for call in candidates.call_args_list]
        self.assertEqual(filter_calls, ["word", "all"])
        last_call = run.call_args_list[-1].args[0]
        self.assertEqual(last_call[1:4], ["pane", "send-text", "w1:p1"])

    def test_edit_shell_quotes_path(self):
        with mock.patch.dict(os.environ, self.env, clear=False), \
                mock.patch.object(extract.shutil, "which", return_value="/usr/bin/fzf"), \
                mock.patch.object(extract, "run_fzf") as run_fzf, \
                mock.patch.object(extract.subprocess, "run") as run:
            run.side_effect = [
                mock.Mock(stdout=json.dumps(self.panes_payload)),
                mock.Mock(stdout="see ./some file.py\n"),
                mock.Mock(),
            ]
            run_fzf.side_effect = [("", "ctrl-e", ["./some file.py"])]
            result = extract.main()

        self.assertEqual(result, 0)
        last_call = run.call_args_list[-1].args[0]
        self.assertEqual(last_call[1:3], ["pane", "run"])
        self.assertIn("'./some file.py'", last_call[4])

    def test_copy_on_darwin_runs_pbcopy_with_text_as_input(self):
        with mock.patch.dict(os.environ, self.env, clear=False), \
                mock.patch.object(extract.shutil, "which", return_value="/usr/bin/fzf"), \
                mock.patch.object(extract, "run_fzf") as run_fzf, \
                mock.patch.object(extract.sys, "platform", "darwin"), \
                mock.patch.object(extract.subprocess, "run") as run:
            run.side_effect = [
                mock.Mock(stdout=json.dumps(self.panes_payload)),
                mock.Mock(stdout="hello there\n"),
                mock.Mock(),
            ]
            run_fzf.side_effect = [("", "enter", ["hello"])]
            result = extract.main()

        self.assertEqual(result, 0)
        copy_call = run.call_args_list[-1]
        self.assertEqual(copy_call.args[0], ["pbcopy"])
        self.assertEqual(copy_call.kwargs.get("input"), "hello")

    def test_missing_active_pane_id_fails_without_calling_fzf(self):
        env = dict(self.env)
        del env["HERDR_ACTIVE_PANE_ID"]
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("builtins.input", return_value=""), \
                mock.patch.object(extract, "run_fzf") as run_fzf:
            result = extract.main()
        self.assertEqual(result, 1)
        run_fzf.assert_not_called()

    def test_fzf_error_exit_fails_instead_of_crashing(self):
        with mock.patch.dict(os.environ, self.env, clear=False), \
                mock.patch.object(extract.shutil, "which", return_value="/usr/bin/fzf"), \
                mock.patch("builtins.input", return_value=""), \
                mock.patch.object(extract.subprocess, "run") as run:
            run.side_effect = [
                mock.Mock(stdout=json.dumps(self.panes_payload)),
                mock.Mock(stdout="hello there\n"),
                mock.Mock(returncode=2, stdout=""),
            ]
            result = extract.main()
        self.assertEqual(result, 1)


class ConfigWiringTests(unittest.TestCase):
    def test_config_binds_prefix_tab_to_extract_popup(self):
        config_path = ROOT.parent / "config.toml"
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        commands = [c for c in config["keys"]["command"] if c.get("key") == "prefix+tab"]
        self.assertEqual(len(commands), 1)
        command = commands[0]
        self.assertEqual(command["type"], "popup")
        self.assertTrue(command["command"].endswith("extrakto/extract.py"))
        self.assertEqual(config["keys"]["cycle_pane_next"], "")


if __name__ == "__main__":
    unittest.main()
