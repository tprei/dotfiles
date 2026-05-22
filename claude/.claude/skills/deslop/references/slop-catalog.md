# Slop catalog

The pattern set for the deslop scan. Run each with the Grep tool (it uses ripgrep). Patterns are
case-sensitive regexes unless noted. Scope the scan to source dirs; exclude `node_modules`, `dist`,
`build`, `.venv`, and vendored trees.

A hit is slop until proven otherwise. The default action is to fix the root cause and delete the
construct — never to widen or relocate a suppression.

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

When a gate is found advisory (`continue-on-error: true`, `|| true`) the checker has been passing
without checking anything. Make it blocking, then fix whatever it surfaces.

## Cross-language

| What | How to find |
|------|-------------|
| commented-out code | scan for contiguous comment blocks that parse as code (`//`, `#`, `/* */`) — distinguish from prose comments |
| untracked TODO/FIXME | `(TODO\|FIXME\|XXX)` then drop any line that references an issue id (e.g. `#1234`, `JIRA-1`, an issue URL); the remainder is slop |
| dead code | unused exports, unreachable branches, functions with no callers — confirm with the language's own unused-symbol check before deleting |
| unused imports/vars | rely on the linter/typechecker with warnings-as-errors; do not eyeball |

## Notes

- `cast()` and `Any` are not always slop — flag them, then judge each: an `Any` at a genuine dynamic
  boundary with a narrowing check is fine; an `Any` used to dodge a fixable type error is slop.
- `print`/`console.log` inside a CLI's actual output path is not debug slop — judge by intent.
- A `# noqa`/`@ts-expect-error` that survives must carry a specific rule code, an inline reason, and a
  linked issue — bare blanket suppressions never survive.
