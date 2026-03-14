---
allowed-tools: Bash(rg:*), Bash(git:*), Glob, Grep, Read, mcp__repomix__pack_codebase, mcp__repomix__attach_packed_output, mcp__repomix__read_repomix_output, mcp__repomix__grep_repomix_output, mcp__repomix__file_system_read_file, mcp__repomix__file_system_read_directory
description: Package relevant code context using two-pass repomix
---

## Purpose
Automatically package relevant code context using a two-pass repomix strategy for efficient codebase analysis.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| scope | string | No | Short description of what the bundle is for (e.g., "authentication refactor", "add payment flow") |

If no scope is provided, prompt: "Briefly describe the scope of this bundle (e.g., 'fixing login bug', 'adding user settings'):"
Store the scope description for use in LLM queries and final output.

## Execution Flow

### Pass 0: Check for existing bundle
Grep conversation history for `repomix` patterns. If a bundle has already been attached or referenced, skip with message: "Existing bundle detected, skipping prepare."

### Pass 1: Discover entry points
Run `git diff --name-only` and `git diff --cached --name-only` to find unstaged and staged changes.

If no changes found:
- Prompt user: "No changes detected. Provide entry point (file/dir) or 'abort' to cancel:"
- Accept file paths, directory paths, or 'abort'

### Pass 2: Discovery pack (compressed)
Run `mcp__repomix__pack_codebase` with `compress=true` to repository root.

Standard exclusions (ignorePatterns):
- `node_modules/**`, `dist/**`, `build/**`, `.git/**`, `vendor/**`, `target/**`, `*.test.*`, `*.spec.*`, `test_*.py`, `*_test.py`, `*_test.go`, `tests/**`, `CHANGELOG.md`, `CHANGELOG.yaml`, `CHANGELOG.yml`

Output to scratchpad directory: `/tmp/claude-1000/-home-prei-dotfiles/*/scratchpad/prepare-discovery.xml`

### Pass 3: Expand relevance

#### Static discovery via ripgrep
For each entry point:

1. **Same directory files:**
   ```bash
   rg --files $(dirname entry_point)
   ```

2. **Direct imports/exports:**
   ```bash
   rg -t js -t ts "^import.*from.*['\"](\./|\.\.)|^export (.*from )?['\"](\./|\.\.)" --glob $(dirname entry_point)/**
   rg -t py "^from \.|^import \." --glob $(dirname entry_point)/**
   rg -t go "^import \t\"" --glob $(dirname entry_point)/**
   ```

3. **Type definitions nearby:**
   ```bash
   rg --files --glob '*.d.ts' --glob 'types.ts' --glob 'types.py' --glob 'interfaces.py' $(dirname entry_point)
   ```

#### Language-specific test exclusion patterns
- JS/TS: `**/*.test.ts`, `**/*.spec.ts`, `**/*.test.js`, `**/*.spec.js`
- Python: `**/test_*.py`, `**/*_test.py`, `**/tests/**/*.py`
- Go: `**/*_test.go`
- Rust: `**/tests/**/*.rs`, `**/*_test.rs`

#### Language-specific type inclusion patterns
- TS: `**/*.d.ts`
- Python: `**/types.py`, `**/interfaces.py`
- Go: `**/*_types.go`, `**/types.go`

#### LLM-assisted discovery
Query the discovery pack with scope context:
"For these entry points, list domain neighbors and shared utilities that are relevant for: **{scope}**. Exclude test files and changelogs."

### Pass 4: Present candidates
Display findings with scope context:

```
Bundle scope: {scope}

Candidate files for context packaging:

Entry points:
  src/auth/login.ts (from git diff)

Direct imports/exports:
  src/auth/types.ts (exports AuthToken type used by login)
  src/auth/utils.ts (exports validateCredentials used by login)

Same directory:
  src/auth/middleware.ts (domain neighbor, imports login)

Type definitions:
  src/auth/types.d.ts

Shared utilities:
  src/shared/crypto.ts (used by validateCredentials)

Files to exclude? (enter filenames comma-separated, or 'none' to proceed)
```

Read user input and filter exclusions. If user enters 'none' or empty, proceed with all candidates.

### Pass 5: Final pack
Construct includePatterns from confirmed files. Run `mcp__repomix__pack_codebase` with:
- `includePatterns`: Comma-separated list of confirmed files
- `ignorePatterns`: Standard exclusions (tests, changelogs, build artifacts)

Attach output to session using `mcp__repomix__attach_packed_output`.

Report: "Bundle attached for scope: {scope} ({N} files)"

## Language Auto-Detection

Detect primary language from entry point extensions and apply corresponding test/type patterns:

| Extension | Language | Test patterns | Type patterns |
|-----------|----------|---------------|---------------|
| .ts, .tsx, .js, .jsx | JS/TS | *.test.ts, *.spec.ts, *.test.js, *.spec.js | *.d.ts |
| .py | Python | test_*.py, *_test.py, tests/**/*.py | types.py, interfaces.py |
| .go | Go | *_test.go | *_types.go, types.go |
| .rs | Rust | tests/**/*.rs, *_test.rs | (none) |

## Edge Cases

1. **No git repo:** Skip git diff, prompt user for entry point immediately
2. **Mixed languages:** Apply patterns for all detected languages
3. **Large file sets:** If candidate count > 50, prompt: "Found N candidates. Continue? (y/n)"
4. **Binary files:** Skip binary files from candidate lists

## Exit Conditions

- Success: Bundle attached, report file count, output path, and scope
- Skipped: Existing bundle detected or user aborted
- Error: Invalid entry point, repomix failure (report stderr)
