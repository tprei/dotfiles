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
            [sys.executable, CAPTURE, "--origin", "17", "--output", self.output, *extra],
            capture_output=True,
            text=True,
            env=env,
        )

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
