import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
CAPTURE = os.path.join(os.path.dirname(HERE), "capture.py")

BIG = "17 * 1024 * 1024 + 7"
SGR = re.compile(r"\x1b\[([0-9;]*)m")
FLAGS = {1: "bold", 2: "faint", 3: "italic", 4: "underline", 9: "strike"}


def styled(ansi):
    style = {}
    cells = []
    at = 0
    for match in SGR.finditer(ansi):
        cells.extend((ch, dict(style)) for ch in ansi[at:match.start()])
        params = [int(p) for p in match.group(1).split(";") if p != ""] or [0]
        index = 0
        while index < len(params):
            code = params[index]
            if code == 0:
                style.clear()
            elif code in (38, 48) and params[index + 1] == 2:
                style["fg" if code == 38 else "bg"] = tuple(params[index + 2:index + 5])
                index += 4
            elif code in FLAGS:
                style[FLAGS[code]] = True
            index += 1
        at = match.end()
    cells.extend((ch, dict(style)) for ch in ansi[at:])
    return cells


def style_of(cells, needle):
    text = "".join(ch for ch, _ in cells)
    start = text.index(needle)
    found = {repr(sorted(style.items())) for _, style in cells[start:start + len(needle)]}
    if len(found) != 1:
        raise AssertionError("%r has mixed styles: %s" % (needle, found))
    return cells[start][1]


class FindOriginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bin_dir = os.path.join(self.tmp.name, "bin")
        os.mkdir(self.bin_dir)

    def write_tern(self, body):
        path = os.path.join(self.bin_dir, "tern")
        with open(path, "w") as fh:
            fh.write("#!%s\nimport sys\n%s" % (sys.executable, body))
        os.chmod(path, 0o755)

    def write_ls(self, tree, blocks=(5, 9)):
        result = {"sessions": [{"tabs": [{"blocks": [{"id": pane} for pane in blocks], "splits": tree}]}]}
        self.write_tern("sys.stdout.write(%r)\n" % json.dumps(result))

    def run_origin(self, extra_env=None):
        env = dict(os.environ, PATH=self.bin_dir)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, CAPTURE, "--origin-of", "9"],
            capture_output=True,
            text=True,
            env=env,
        )

    def test_finds_column_a_leaf(self):
        self.write_ls({"Split": {"axis": "Column", "a": {"Leaf": 5}, "b": {"Leaf": 9}}})
        result = self.run_origin()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "5\n")

    def test_finds_column_a_leaf_when_copy_is_nested_under_row(self):
        self.write_ls(
            {
                "Split": {
                    "axis": "Row",
                    "a": {"Leaf": 3},
                    "b": {
                        "Split": {
                            "axis": "Column",
                            "a": {"Leaf": 5},
                            "b": {"Leaf": 9},
                        }
                    },
                }
            }
        )
        result = self.run_origin()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "5\n")

    def test_rejects_copy_on_column_a_side(self):
        self.write_ls({"Split": {"axis": "Column", "a": {"Leaf": 9}, "b": {"Leaf": 5}}})
        result = self.run_origin()
        self.assertEqual(result.returncode, 1)
        self.assertIn("can't find the pane copy mode split from", result.stderr)

    def test_reports_copy_not_in_a_tab(self):
        self.write_ls({"Split": {"axis": "Column", "a": {"Leaf": 5}, "b": {"Leaf": 6}}}, blocks=(5, 6))
        result = self.run_origin()
        self.assertEqual(result.returncode, 1)
        self.assertIn("is in no tab", result.stderr)

    def test_reports_tern_ls_failure(self):
        self.write_tern("sys.stderr.write('boom\\n')\nsys.exit(2)\n")
        result = self.run_origin()
        self.assertEqual(result.returncode, 1)
        self.assertIn("tern ls exited 2: boom", result.stderr)

    def test_sets_copy_pane_environment(self):
        output = {"sessions": [{"tabs": [{"blocks": [{"id": 5}, {"id": 9}], "splits": {"Split": {"axis": "Column", "a": {"Leaf": 5}, "b": {"Leaf": 9}}}}]}]}
        env_path = os.path.join(self.tmp.name, "environment")
        argv_path = os.path.join(self.tmp.name, "argv")
        names = ("TERN_PANE", "TERN_PANE_SOCKET", "TERN_WINDOW_KEY", "TERN_WINDOW_SOCKET")
        body = (
            "import json, os\n"
            "sys.stdout.write(%r)\n"
            "with open(os.environ['COPYMODE_ENV_FILE'], 'w') as fh:\n"
            "    fh.write('\\n'.join(name + '=' + os.environ[name] for name in %r if name in os.environ))\n"
            "with open(os.environ['COPYMODE_ARGV_FILE'], 'w') as fh:\n"
            "    fh.write(json.dumps(sys.argv[1:]))\n"
        ) % (json.dumps(output), names)
        self.write_tern(body)
        env = {name: "set" for name in names}
        env["TERN_PANE"] = "1234"
        env["COPYMODE_ENV_FILE"] = env_path
        env["COPYMODE_ARGV_FILE"] = argv_path
        result = self.run_origin(env)
        self.assertEqual(result.returncode, 0)
        with open(env_path) as fh:
            self.assertEqual(fh.read(), "TERN_PANE=9")
        with open(argv_path) as fh:
            self.assertEqual(json.load(fh), ["ls", "--json"])


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bin_dir = os.path.join(self.tmp.name, "bin")
        self.out_dir = os.path.join(self.tmp.name, "out")
        os.mkdir(self.bin_dir)
        os.mkdir(self.out_dir)
        self.output = os.path.join(self.out_dir, "snapshot.ansi")

    def write_tern(self, body):
        path = os.path.join(self.bin_dir, "tern")
        with open(path, "w") as fh:
            fh.write("#!%s\nimport sys\n%s" % (sys.executable, body))
        os.chmod(path, 0o755)

    def run_capture(self, *extra, extra_env=None):
        env = dict(os.environ, PATH=self.bin_dir)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, CAPTURE, "--origin", "17", "--output", self.output, "--copy", "9", *extra],
            capture_output=True,
            text=True,
            env=env,
        )

    def test_capture_uses_copy_pane_environment(self):
        env_path = os.path.join(self.tmp.name, "environment")
        argv_path = os.path.join(self.tmp.name, "argv")
        names = ("TERN_PANE", "TERN_PANE_SOCKET", "TERN_WINDOW_KEY", "TERN_WINDOW_SOCKET")
        body = (
            "import json, os\n"
            "sys.stdout.write('<pre>x</pre>')\n"
            "with open(os.environ['COPYMODE_ENV_FILE'], 'w') as fh:\n"
            "    fh.write('\\n'.join(name + '=' + os.environ[name] for name in %r if name in os.environ))\n"
            "with open(os.environ['COPYMODE_ARGV_FILE'], 'w') as fh:\n"
            "    fh.write(json.dumps(sys.argv[1:]))\n"
        ) % (names,)
        self.write_tern(body)
        env = {name: "set" for name in names}
        env["TERN_PANE"] = "1234"
        env["COPYMODE_ENV_FILE"] = env_path
        env["COPYMODE_ARGV_FILE"] = argv_path
        result = self.run_capture(extra_env=env)
        self.assertEqual(result.returncode, 0)
        with open(env_path) as fh:
            self.assertEqual(fh.read(), "TERN_PANE=9")
        with open(argv_path) as fh:
            self.assertEqual(json.load(fh), ["capture", "17", "--html", "--scrollback", "--surfaces"])

    def test_full_capture_streams_beyond_16mib_to_file_without_stdout(self):
        self.write_tern("sys.stdout.write('x' * (%s))\n" % BIG)
        result = self.run_capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(self.output, "rb") as fh:
            data = fh.read()
        self.assertEqual(len(data), 17 * 1024 * 1024 + 7)
        self.assertEqual(data[:64], b"x" * 64)
        self.assertLess(len(result.stdout), 200)
        self.assertIn("captured pane 17", result.stdout)

    def test_html_styles_entities_and_native_text_convert_to_ansi(self):
        html = (
            '<pre style="color:#e8ecf4;background-color:#151820">'
            "plain 17\n"
            "&lt;tag&gt; &amp; &quot;q&quot;\n"
            '<span style="color:#ff0000">red</span>'
            '<span style="font-weight:bold;font-style:italic;text-decoration:underline line-through">'
            "rich\nspan</span>\n"
            '<span style="color:#00ff00"><span style="background-color:#0000ff">nested</span></span>'
            '<span style="opacity:0.5">dim</span>\n'
            "tail omp transcript"
        )
        self.write_tern("sys.stdout.write(%r)\n" % html)
        result = self.run_capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(self.output, "rb") as fh:
            data = fh.read().decode("utf-8")
        self.assertNotIn("&lt;", data)
        self.assertNotIn("<span", data)
        cells = styled(data)
        self.assertEqual("".join(ch for ch, _ in cells), 'plain 17\n<tag> & "q"\nredrich\nspan\nnesteddim\ntail omp transcript')
        base = {"fg": (232, 236, 244), "bg": (21, 24, 32)}
        self.assertEqual(style_of(cells, "plain 17"), base)
        self.assertEqual(style_of(cells, "red"), {"fg": (255, 0, 0), "bg": (21, 24, 32)})
        self.assertEqual(style_of(cells, "rich\nspan"), dict(base, bold=True, italic=True, underline=True, strike=True))
        self.assertEqual(style_of(cells, "nested"), {"fg": (0, 255, 0), "bg": (0, 0, 255)})
        self.assertEqual(style_of(cells, "dim"), dict(base, faint=True))
        self.assertEqual(style_of(cells, "tail omp transcript"), base)

    def test_snapshot_file_is_private_even_with_permissive_umask(self):
        self.write_tern("sys.stdout.write('secret')\n")
        old = os.umask(0)
        try:
            result = self.run_capture()
        finally:
            os.umask(old)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(os.stat(self.output).st_mode), 0o600)

    def test_failed_capture_removes_file_and_reports_stderr(self):
        self.write_tern("sys.stderr.write('pane not found\\n')\nsys.exit(3)\n")
        result = self.run_capture()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(os.path.exists(self.output))
        self.assertIn("exited 3", result.stderr)
        self.assertIn("pane not found", result.stderr)

    def test_partial_output_cleaned_after_failure(self):
        self.write_tern("sys.stdout.write('partial')\nsys.exit(1)\n")
        result = self.run_capture()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(os.path.exists(self.output))

    def test_missing_tern_leaves_no_file_and_explains(self):
        result = self.run_capture()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(os.path.exists(self.output))
        self.assertIn("PATH", result.stderr)

    def test_existing_output_file_is_refused_untouched(self):
        self.write_tern("sys.stdout.write('new')\n")
        with open(self.output, "w") as fh:
            fh.write("precious")
        result = self.run_capture()
        self.assertEqual(result.returncode, 1)
        with open(self.output) as fh:
            self.assertEqual(fh.read(), "precious")
        self.assertIn("refusing", result.stderr)

    def test_symlinked_output_is_refused(self):
        self.write_tern("sys.stdout.write('x')\n")
        target = os.path.join(self.out_dir, "target")
        with open(target, "w") as fh:
            fh.write("keep")
        os.symlink(target, self.output)
        result = self.run_capture()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(os.path.islink(self.output))
        with open(target) as fh:
            self.assertEqual(fh.read(), "keep")

    def test_cleanup_failure_is_reported(self):
        self.addCleanup(os.chmod, self.out_dir, 0o755)
        path = os.path.join(self.bin_dir, "tern")
        with open(path, "w") as fh:
            fh.write(
                "#!%s\n"
                "import os, sys\n"
                "os.chmod(os.environ['CM_TEST_OUT'], 0o555)\n"
                "sys.exit(4)\n" % sys.executable
            )
        os.chmod(path, 0o755)
        result = self.run_capture(extra_env={"CM_TEST_OUT": self.out_dir})
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot remove", result.stderr)
        self.assertTrue(os.path.exists(self.output))


if __name__ == "__main__":
    unittest.main()
