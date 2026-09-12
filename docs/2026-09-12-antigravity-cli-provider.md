# Antigravity CLI provider

## Goal

Add an OMP extension provider that invokes the installed `agy` CLI in headless `stream-json` mode. This uses the CLI's own Antigravity authentication, model routing, and agent tools instead of OMP's native Cloud Code Assist transport.

This is a CLI-backed OMP provider, not an ACP client. OMP's `acp` command remains an ACP server and is not part of this change.

## Files

- `omp/.omp/agent/extensions/antigravity-cli.ts`: OMP extension entry point and provider registration.
- `omp/.omp/agent/extensions/antigravity-cli/models.ts`: static Gemini model catalog and effort-to-CLI model mapping.
- `omp/.omp/agent/extensions/antigravity-cli/context.ts`: conversion of OMP text context into a single AGY prompt.
- `omp/.omp/agent/extensions/antigravity-cli/process.ts`: `agy` child-process lifecycle, NDJSON parsing, response assembly, and usage conversion.
- `omp/.omp/agent/config.yml`: root role and fallback selections for the CLI provider.
- `omp/.omp/profiles/mix/agent/config.yml`: `mix` role and fallback selections for the CLI provider.
- `README.md`: deployment, profile, authentication, and permission setup.

The provider is available after the extension is deployed through the existing stow-managed extension directory. Users can select `antigravity-cli/gemini-3.8-flash` for text-only prompts, and the root and `mix` profiles assign it to their `tiny` role. AGY owns authentication under its existing CLI state.

## Provider contract

Register provider `antigravity-cli` with API id `antigravity-cli`, static text-only Gemini models, `apiKey: "AGY_CLI_MANAGED"`, and a custom `streamSimple` handler. The marker only satisfies OMP's credential-aware model availability check. It is never sent to AGY or used as a Google credential.

Models:

- `gemini-3.8-flash`: minimal, low, medium, and high effort routing to `gemini-3.8-flash-{low,medium,high}`.
- `gemini-3.7-flash`: minimal, low, medium, and high effort routing to the corresponding CLI ids.
- `gemini-3.6-flash`: minimal, low, medium, and high effort routing to the corresponding CLI ids.
- `gemini-3.1-pro`: low and high effort routing to `gemini-3.1-pro-{low,high}`.

`resolveAgyModelId(modelId, reasoning, disableReasoning)` maps disabled requests to each model's `off` route, maps minimal and low to the low wire model, preserves medium when available, and uses high for higher requests.

Use text-only input because this bridge does not invent an image transport. Set zero token costs because AGY subscription usage is not represented as OMP per-token billing.

## Process contract

`runAgyTurn(request)` accepts:

```ts
interface AgyTurnRequest {
  prompt: string;
  modelId: string;
  conversationId?: string;
  cwd: string;
  signal?: AbortSignal;
  dangerouslySkipPermissions: boolean;
  onTextDelta?: (delta: string) => void;
}
```

It returns:

```ts
interface AgyTurnResult {
  conversationId: string;
  response: string;
  inputTokens?: number;
  outputTokens?: number;
  thinkingTokens?: number;
  cacheReadTokens?: number;
  totalTokens?: number;
  durationMs?: number;
}
```

Launch `${AGY_BIN ?? "agy"}` without a shell using:

```text
--print= --input-format stream-json --output-format stream-json --model <cli model id> --disable-slash-commands
```

Add `--conversation <id>` when resuming an in-process binding. Add `--dangerously-skip-permissions` only when `AGY_OMP_DANGEROUSLY_SKIP_PERMISSIONS=1`; never enable it by default.

Write one `{"event":"user","message":{"role":"user","content":"<prompt>"}}` NDJSON record to stdin and close stdin. Read stdout as NDJSON. Accept `init`, `step_update`, and `result` events. Capture `step_update.text_delta` from `agent_response`, pass each delta to `onTextDelta`, and use `result.response` as the completed response. Reject malformed stdout, a failed result, a missing conversation id, or a non-zero child exit with an explicit error. On abort, terminate the child and reject the turn. Do not swallow stderr or protocol errors.

`agy` writes diagnostics to stderr. Include a bounded stderr tail in process errors without exposing environment values or credentials.

## Context contract

On a new AGY conversation, serialize the OMP system prompt and all text content from OMP messages as labeled transcript sections, ending with an instruction to answer the latest request. On an existing binding, send only newly appended text messages. Reject image content explicitly rather than silently dropping it.

Track bindings by `SimpleStreamOptions.sessionId`. Capture the provider context's message count before the AGY turn. OMP records one assistant message in session history after the provider starts, so store the first message index after that assistant, along with an exact serialized fingerprint of the provider-context prefix that AGY has seen. Resume only when the incoming provider context still contains that prefix at the stored boundary. If the prefix changed, the context was compacted, or the boundary is unavailable, discard the binding and send the full serialized context in a new AGY conversation. Do not share a conversation when OMP supplies no session id. Clear a binding after a failed turn so a later retry starts from the OMP context instead of reusing uncertain AGY state.

## Stream contract

Create an `AssistantMessageEventStream`, push `start`, stream `text_start`/`text_delta`/`text_end`, then push `done` with `stopReason: "stop"`. Populate `AssistantMessage` with API `antigravity-cli`, provider `antigravity-cli`, the logical model id, zero-cost usage, duration, and AGY conversation id as `responseId`.

On any process/protocol failure, push `error` with `stopReason: "error"` and an explicit `errorMessage`; this terminal event ends the stream. Let OMP classify the error; do not route to another model inside the extension.

## Extension lifecycle

Register the provider once at extension load. Clear all in-memory conversation bindings on `session_shutdown`. No login flow is added because AGY owns OAuth. A failed AGY authentication produces the CLI's error and tells the user to authenticate with `agy` first.

## Verification

- Load the helper modules with Bun's TypeScript loader.
- Run pure context/model assertions in a throwaway script.
- Run a real `agy --output-format stream-json` smoke turn and verify the extension's parser returns the response and conversation id.
- Launch OMP with the extension explicitly, list the custom provider model, and run a one-word prompt.
- Confirm only the provider modules, root and `mix` config files, README, and this plan changed.

## Non-goals

- Do not modify OMP's native `google-antigravity` provider or its rate-limit classifier.
- Do not implement an ACP client or vendor the third-party managed ACP runtime.
- Do not pass Google OAuth tokens through OMP.
- Do not enable yolo permissions implicitly.
- Do not add fallback routing inside the provider.
