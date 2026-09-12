# Antigravity and OMP usage repair

## Scope

Repair the Antigravity CLI provider so OMP can load it from the bare extension directory, document the exact visibility limit of AGY's stream protocol, expose truthful progress where the protocol permits, and make the systemd OMP usage report use the installed binary and represent a successful empty usage payload without reporting an execution failure.

## Extension changes

### `omp/.omp/agent/extensions/antigravity-cli/models.ts`

Remove the runtime import of `Effort` from `@oh-my-pi/pi-catalog/effort`. Follow the existing bare-extension pattern in `thinking-picker.ts`: declare the supported string literals locally, derive a local effort union, and use a single narrow assertion where `ProviderModelConfig` requires OMP's nominal effort type. Keep the current model IDs, effort routes, costs, context window, and token limit unchanged. `resolveAgyModelId` must continue accepting the reasoning value passed by `SimpleStreamOptions` and map `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max` to the existing AGY wire IDs without importing a runtime-only package.

### `omp/.omp/agent/extensions/antigravity-cli/process.ts`

Extend the AGY event parser only for protocol data observed from `agy --output-format stream-json`. Preserve `agent_response` text streaming. Add a typed activity callback to `AgyTurnRequest` if OMP can display truthful progress without presenting hidden chain-of-thought as if it were available. Tool activity may identify the observed `tool_name`, and completed silent agent-response steps may report their observed `thinking_tokens`. Never invent reasoning text, expose tool arguments or output, or label progress metadata as chain-of-thought. If OMP's assistant stream cannot represent progress without polluting the final answer, leave runtime output unchanged and state that AGY exposes only token counts, not reasoning content.

### `omp/.omp/agent/extensions/antigravity-cli.ts`

Wire any supported progress callback into OMP's native thinking stream events and `ThinkingContent` blocks, while preserving text blocks and final response content. Honor `options.disableReasoning`: do not emit progress blocks when reasoning is disabled. Keep conversation reuse, abort handling, usage accounting, and provider registration unchanged. Do not add dependencies, fallbacks, compatibility shims, or suppressions.

## Usage report changes

### `tools/.config/systemd/user/codex-usage-report.service`

Set `OMP_BIN` to `/home/prei/.local/bin/omp`, the installed executable reported by `which omp`. Keep an explicit non-interactive `PATH` containing that directory. Do not point at the removed `/home/prei/.bun/bin/omp`.

### `tools/.local/bin/codex-usage-check`

Treat an OMP process that exits zero and returns an object with a `reports` list as a successful command even when the list is empty. Keep malformed JSON, non-object payloads, missing `reports`, process failures, and timeouts as errors. Render a concise no-reports state for an empty list instead of the misleading `OMP usage unavailable` warning, and return zero so systemd does not mark a valid empty response failed. Preserve provider formatting and Telegram behavior for non-empty reports. Do not query providers directly or add another usage source.

## Verification

Run these checks from the issue worktree:

1. `omp --no-extensions -e ./omp/.omp/agent/extensions/antigravity-cli.ts --model antigravity-cli/gemini-3.8-flash:minimal -p "Reply with exactly: ok"` exits zero and prints `ok` without a catalog-load warning.
2. A direct AGY stream probe confirms the protocol exposes `thinking_tokens` and tool lifecycle metadata but no reasoning text. If progress blocks are implemented, run OMP with `--print-thoughts` and a prompt that invokes a terminal tool, then confirm only truthful metadata appears.
3. `OMP_BIN=/home/prei/.local/bin/omp tools/.local/bin/codex-usage-check` accepts the installed command's current empty `reports` payload and exits zero.
4. `python3 -m py_compile tools/.local/bin/codex-usage-check` exits zero.
5. `systemd-analyze --user verify tools/.config/systemd/user/codex-usage-report.service tools/.config/systemd/user/codex-usage-report.timer` exits zero.
6. After merging, reload the user manager and run `systemctl --user start codex-usage-report.service`; service status must be successful and the generated image must show the no-reports state rather than an OMP execution error.

## Constraints

Do not change unrelated `codex/.codex/config.toml` or `zsh/.zshrc` work. Do not expose fabricated chain-of-thought. Do not add a fallback binary path or provider endpoint. Do not add lint or type suppressions. Do not change model routing beyond eliminating the unavailable runtime dependency.
