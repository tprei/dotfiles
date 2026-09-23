# Slop catalog

Case-sensitive `rg` regexes. Scan source dirs; exclude `node_modules`, `dist`, `build`, `.venv`, and vendored trees. A hit is slop until proven otherwise.

## Python

| What | Pattern |
|------|---------|
| mypy ignore | `#\s*type:\s*ignore` |
| pyright ignore | `#\s*pyright:\s*ignore` |
| pylint disable | `#\s*pylint:\s*disable` |
| flake8/ruff noqa | `#\s*noqa` |
| escape-hatch cast | `\bcast\s*\(` |
| `Any` annotations | `:\s*Any\b\|->\s*Any\b` |
| bare except | `except\s*:` |
| broad except | `except\s+(Exception\|BaseException)\s*:` |
| swallowed error | `except[^\n]*:\s*$\s*pass` (also check `except ...: pass` one-liners) |
| debug print | `^\s*print\s*\(` |
| debugger | `pdb\.set_trace\|breakpoint\s*\(` |

## TypeScript / JavaScript

| What | Pattern |
|------|---------|
| ts-ignore | `@ts-ignore` |
| ts-expect-error | `@ts-expect-error` |
| eslint disable | `eslint-disable` |
| any cast | `\bas\s+any\b` |
| any annotation | `:\s*any\b` |
| console debug | `console\.(log\|debug\|trace)\s*\(` |
| debugger | `^\s*debugger\b` |

## CI / config gates

| What | Pattern |
|------|---------|
| advisory step | `continue-on-error:\s*true` |
| swallowed command | `\|\|\s*true` |
| mypy per-module override | `\[mypy-.*\]` |
| mypy ignore block | `ignore_errors\s*=\s*true` |
| mypy/ruff exclude | `^\s*exclude\s*=` |
| warning slack | `--max-warnings` |
| suppression baselines | files named `.mypy_baseline`, `*.baseline`, `.eslint-baseline*`, `tsc-baseline*` |

An advisory gate has been passing without checking anything. Make it blocking, then fix what it surfaces.

## Cross-language

| What | How to find |
|------|-------------|
| commented-out code | contiguous comment blocks that parse as code, not prose |
| untracked TODO/FIXME | `(TODO\|FIXME\|XXX)` minus lines referencing an issue (`#1234`, `JIRA-1`, a URL) |
| dead code | unused exports, unreachable branches, uncalled functions; confirm with the language's unused-symbol check |
| unused imports/vars | linter or typechecker with warnings-as-errors, not eyeballing |

## Notes

- `cast()` and `Any` at a real dynamic boundary with a narrowing check are fine; used to dodge a fixable type error, they're slop.
- `print`/`console.log` in a CLI's real output path isn't debug slop.
- A surviving `# noqa`/`@ts-expect-error` needs a specific rule code, inline reason, and linked issue. Blanket suppressions never survive.
