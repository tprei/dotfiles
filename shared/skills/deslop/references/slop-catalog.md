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
| double cast | `\bas\s+unknown\s+as\b` |
| never cast | `\bas\s+never\b` |
| empty catch block | `catch\s*(\([^)]*\))?\s*\{\s*\}` (add `-U` for blocks split across lines) |
| swallowed promise | `\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*(\{\s*\}\|undefined\|null\|void 0)\s*\)` |
| every type assertion | `npx -y -p @ast-grep/cli ast-grep run -p '$E as $T' -l ts <absolute root>`, again with `-l tsx`; catches `x as string` on nullables and `data as T`, which no regex above does |
| non-null assertion | `npx -y -p @ast-grep/cli ast-grep scan --inline-rules '{id: non-null, language: ts, rule: {kind: non_null_expression}}' <absolute root>`, again with `language: tsx` (`npx -p` resolves a relative path from the nearest `package.json`) |

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
| unrun tsconfig project | every `tsconfig*.json` that no CI step runs with `tsc -p` and the root config excludes; dividimos `e2e/` hid 55 type errors this way |
| lint rule off for a glob | `["']off["']\|:\s*0\s*[,}]` inside eslint config `rules` blocks |

An advisory gate has been passing without checking anything. Make it blocking, then fix what it surfaces.

## SQL

| What | Pattern |
|------|---------|
| swallow-all handler | `(?i)when\s+others\s+then`; slop when it turns any fault into a normal result (`not_found`, `null`), fine around one statement with a known failure mode |

## Cross-language

| What | How to find |
|------|-------------|
| commented-out code | contiguous comment blocks that parse as code, not prose |
| untracked TODO/FIXME | `(TODO\|FIXME\|XXX)` minus lines referencing an issue (`#1234`, `JIRA-1`, a URL) |
| dead code | unused exports, unreachable branches, uncalled functions; confirm with the language's unused-symbol check (knip for TypeScript). knip misses entry points loaded by Playwright configs, `node --test` scripts, and service workers, so confirm each finding with a repo-wide `rg -w` before deleting |
| unused imports/vars | linter or typechecker with warnings-as-errors, not eyeballing |

## Over-engineering

Code that defends against states the types already rule out, tests that can't fail, and error or metric machinery nothing consumes. Each is slop even when lint and typecheck pass.

| What | How to find |
|------|-------------|
| redundant runtime guard | TypeScript: turn on typescript-eslint's type-aware `no-unnecessary-condition` (with `checkTypePredicates: true` so it also checks `isRecord`-style predicates and `Array.isArray`) and `no-unnecessary-type-assertion`, both needing `parserOptions.projectService`; they flag `?.`, `?? default`, and conditions on values that can't be nullish or falsy. They don't flag `typeof` checks, so also `rg` for `\bisRecord\(\|typeof [\w.]+ [!=]== ["']object["']\|Array\.isArray\(` and keep only guards on data crossing a wire or process edge (`JSON.parse`, HTTP or RPC results, storage, `postMessage`); check each argument's origin with LSP. Python: pyright `reportUnnecessaryIsInstance`, `reportUnnecessaryComparison`, `reportUnnecessaryCast`, or mypy `warn_unreachable` and `warn_redundant_casts` |
| hand-rolled decoder | an `isRecord`/`typeof` narrowing function for an in-process value the types already cover (an internal call's return, a validated object passed along). Data crossing a wire or process edge still gets decoded, whatever its generated static type, but through the existing production decoder rather than a new local one |
| tautological test | literal subject `expect\((true\|false\|null\|undefined\|-?\d+\|"[^"]*")\)\.`; tests whose only assertions are `\.(toBeDefined\|toBeTruthy\|not\.toThrow)\(\)`; a mock's configured return value asserted back unchanged; snapshots of static copy; Python `assert True`, bare `assert_called()`. The test is slop if it would still pass with the unit under test returning a wrong value or doing nothing |
| unconsumed error type or code | list `class \w+(Error\|Exception)\b` and error-code constants, then count discriminating uses (`instanceof X`, `except X`, `.code === "x"`, `case "x"`) outside the defining file and tests. Zero means the type adds nothing over the base error |
| rethrow wrapper | `catch\s*\((\w+)\)\s*\{\s*throw new \w+\(\s*\1\s*\);?\s*\}`; Python `except \w+ as (\w+):\s*raise \w+\(\1\)`. Both need `rg -U --pcre2` (backreferences, line breaks). Slop unless the new error adds context a caller uses |
| unread metric or telemetry | emit calls (`counter(`, `histogram(`, `gauge(`, `.increment(`, `track(`, statsd, Prometheus clients). Slop when no dashboard, alert, SLO, test, or consumer references the metric name; `rg` the name across the repo and infra config |

## Notes

- `cast()` and `Any` at a real dynamic boundary with a narrowing check are fine; used to dodge a fixable type error, they're slop.
- `print`/`console.log` in a CLI's real output path isn't debug slop.
- A surviving `# noqa`/`@ts-expect-error` needs a specific rule code, inline reason, and linked issue. Blanket suppressions never survive.
- An empty catch or `.catch(() => {})` is fine when the callee already records the failure (store state, log, retry) and the caller only silences the rethrow. Read the callee before calling it slop.
- `as unknown as` on a partial fake of a large third-party interface in a test can stay. Typed globals (`declare global`), production decoders, and narrowed parameter types remove the rest.
- A runtime guard replacing a cast is a fix only where data crosses a wire or process edge, and there the existing decoder does the job. For an in-process value, fix the static type; a new `isRecord` check on it trades one slop for another.
