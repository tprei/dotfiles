from __future__ import annotations

import re
import shlex
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Final

_SEPARATORS: Final = frozenset({"&&", "||", ";", "&"})
_PIPES: Final = frozenset({"|", "|&"})
_GROUPING: Final = frozenset({"(", ")"})
_SUBSTITUTIONS: Final = ("$(", "`", "<(", ">(")
_QUERY_FLAGS: Final = frozenset({"--version", "--help", "--list"})
_LONE_QUERY_FLAGS: Final = frozenset({"-v", "-V", "-h", "-l"})
_QUERY_WORDS: Final = frozenset({"version", "help"})
_ASSIGNMENT: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_PYTHON: Final = re.compile(r"python3?(\.\d+)?")
_OUTPUT_FILTERS: Final = frozenset({"tail", "head", "tee", "grep", "rg", "sed", "awk", "cut", "sort", "uniq", "wc"})
_SCRIPT_RUNNERS: Final = frozenset({"npm", "pnpm", "yarn", "bun"})
_PACKAGE_CHORES: Final = frozenset(
    """
    install i add remove rm update up upgrade link unlink x info view list ls outdated why config store cache root
    bin audit publish env npm pm pack prune dedupe import licenses patch setup create init login logout whoami help
    """.split()
)
_RUNNER_PREFIXES: Final = frozenset({"exec", "dlx"})
_NPX_LIKE: Final = frozenset({"npx", "bunx"})
_HEAVY_TOOLS: Final = frozenset(
    """
    tsc vue-tsc vitest jest mocha ava eslint biome playwright cypress webpack rollup turbo nx svelte-check pytest
    mypy pyright tox nox make just gradle gradlew mvn bazel ctest
    """.split()
)
_TOOL_SUBCOMMANDS: Final = {
    "vite": frozenset({"build", "optimize"}),
    "next": frozenset({"build", "lint"}),
    "astro": frozenset({"build", "check"}),
    "go": frozenset({"test", "build", "vet", "generate"}),
    "cargo": frozenset({"test", "build", "check", "clippy", "bench", "nextest"}),
    "dotnet": frozenset({"build", "test"}),
    "deno": frozenset({"test", "check", "lint", "bench", "compile"}),
}
_MAKE_CHORES: Final = frozenset({"clean", "distclean", "install", "help"})
_PYTHON_MODULES: Final = frozenset({"pytest", "mypy", "unittest"})
_NPM_VALUE_OPTIONS: Final = frozenset({"--prefix", "-w", "--workspace", "-C"})
_PNPM_VALUE_OPTIONS: Final = frozenset({"--filter", "-F", "-C", "--dir", "--cwd", "-w", "--workspace"})
_UV_RUN_VALUE_OPTIONS: Final = frozenset(
    {
        "--with",
        "--with-editable",
        "--with-requirements",
        "--group",
        "--only-group",
        "--extra",
        "--package",
        "--python",
        "-p",
        "--env-file",
        "--project",
        "--directory",
    }
)
_LIGHT: Final = "not a test, build, lint or typecheck runner"


@dataclass(frozen=True)
class _Segment:
    words: list[str]
    after_pipe: bool


def refusal(command: str) -> str | None:
    """Why `command` is too light to offload, or None when it runs a test, build, lint or typecheck tool."""
    if any(marker in command for marker in _SUBSTITUTIONS):
        return "it runs a command substitution, which could hide anything"
    try:
        tokens = _tokens(command)
    except ValueError as error:
        return f"it is not valid shell syntax ({error})"
    segments = _segments(tokens)
    if any(token in _QUERY_FLAGS for token in tokens) or any(_is_query(segment.words) for segment in segments):
        return "a version or help query"
    heavy = [_is_heavy(segment.words) for segment in segments]
    if not any(heavy):
        return _LIGHT
    for segment, is_heavy in zip(segments, heavy, strict=True):
        if is_heavy or _is_cd(segment.words) or (segment.after_pipe and _is_output_filter(segment.words)):
            continue
        return _LIGHT
    return None


def _tokens(command: str) -> list[str]:
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    # Bash starts a comment only at a word's start; shlex's default also cuts mid-word, hiding what follows.
    lexer.commenters = ""
    return [token for token in lexer if token not in _GROUPING]


def _segments(tokens: list[str]) -> list[_Segment]:
    segments = [_Segment(words=[], after_pipe=False)]
    for token in tokens:
        if token in _SEPARATORS or token in _PIPES:
            segments.append(_Segment(words=[], after_pipe=token in _PIPES))
        else:
            segments[-1].words.append(token)
    return [_Segment(words=_command_words(segment.words), after_pipe=segment.after_pipe) for segment in segments]


def _command_words(words: list[str]) -> list[str]:
    start = 1 if words[:1] == ["env"] else 0
    while start < len(words) and _ASSIGNMENT.match(words[start]):
        start += 1
    return words[start:]


def _is_query(words: list[str]) -> bool:
    return len(words) == 2 and (words[1] in _QUERY_WORDS or words[1] in _LONE_QUERY_FLAGS)


def _is_cd(words: list[str]) -> bool:
    return len(words) == 2 and words[0] == "cd"


def _is_output_filter(words: list[str]) -> bool:
    return bool(words) and _name(words[0]) in _OUTPUT_FILTERS


def _is_heavy(words: list[str]) -> bool:
    if not words:
        return False
    program = _name(words[0])
    args = words[1:]
    if program in _SCRIPT_RUNNERS:
        return _is_package_script(program, args)
    if program in _NPX_LIKE:
        return _is_tool(_positionals(args, frozenset()))
    if program == "uv":
        return _is_uv_run(args)
    if _PYTHON.fullmatch(program):
        return _is_python_module(args)
    if program == "node":
        return args[:1] == ["--test"]
    return _is_tool(words)


def _is_package_script(program: str, args: list[str]) -> bool:
    value_options = _NPM_VALUE_OPTIONS if program == "npm" else _PNPM_VALUE_OPTIONS
    positionals = _positionals(args, value_options)
    if not positionals:
        return False
    if program != "npm" and positionals[0] in _RUNNER_PREFIXES:
        return _is_tool(_positionals(positionals[1:], frozenset()))
    if positionals[0] in _PACKAGE_CHORES:
        return False
    if positionals[0] in {"test", "t"}:
        return True
    if positionals[0] in {"run", "run-script"}:
        name = _positionals(positionals[1:], value_options)
        return bool(name) and name[0] != "env"
    return program != "npm"


def _is_tool(words: list[str]) -> bool:
    if not words:
        return False
    if _is_query(words):
        return False
    tool = _name(words[0])
    rest = words[1:]
    if tool in {"tsc", "vue-tsc", "eslint"} and {"-v", "-V"}.intersection(rest):
        return False
    if tool == "pytest" and "-V" in rest:
        return False
    subcommands = _TOOL_SUBCOMMANDS.get(tool)
    if subcommands is not None:
        named = _positionals(rest, frozenset())
        return bool(named) and named[0] in subcommands
    if tool == "make" and _MAKE_CHORES.intersection(rest):
        return False
    return tool in _HEAVY_TOOLS


def _is_uv_run(args: list[str]) -> bool:
    if args[:1] != ["run"]:
        return False
    command = _positionals(args[1:], _UV_RUN_VALUE_OPTIONS)
    if command and _PYTHON.fullmatch(_name(command[0])):
        return _is_python_module(command[1:])
    return _is_tool(command)


def _is_python_module(args: list[str]) -> bool:
    return len(args) > 1 and args[0] == "-m" and args[1] in _PYTHON_MODULES


def _positionals(args: list[str], value_options: Collection[str]) -> list[str]:
    """`args` from the first word that isn't an option (or an option's value) on."""
    index = 0
    while index < len(args) and args[index].startswith(("-", "+")):
        index += 2 if args[index] in value_options else 1
    return args[index:]


def _name(word: str) -> str:
    return PurePosixPath(word).name
