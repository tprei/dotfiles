import type { ExtensionAPI, ExtensionContext } from "@oh-my-pi/pi-coding-agent";

// Fires once per `gh pr create` bash call, across every omp session/thread.
// Deliberately bounded: a single non-agentic OpenRouter chat-completion call
// (low reasoning effort, hard output cap) — never a full reviewer subagent
// or omp session — so this can't run up usage just because a lot of PRs get
// opened concurrently across threads. For a full, on-demand review use the
// `review` skill (delegates to the `reviewer` task agent, pinned to
// openrouter/openai/gpt-5.6-luna:max in config.yml).

const PR_CREATE_RE = /\bgh\s+pr\s+create\b/;
const PR_URL_RE = /https:\/\/github\.com\/[^\s"'<>]+\/pull\/\d+/;

const MODEL = "openai/gpt-5.6-luna";
const REASONING_EFFORT = "low";
const MAX_OUTPUT_TOKENS = 900;
const MAX_DIFF_CHARS = 20_000;

async function run(cmd: string[]): Promise<{ stdout: string; stderr: string; code: number }> {
  const proc = Bun.spawn(cmd, { stdout: "pipe", stderr: "pipe" });
  const [stdout, stderr] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
  ]);
  const code = await proc.exited;
  return { stdout, stderr, code };
}

async function reviewAndComment(prUrl: string, ctx: ExtensionContext): Promise<void> {
  const [diffRes, viewRes, keyRes] = await Promise.all([
    run(["gh", "pr", "diff", prUrl]),
    run(["gh", "pr", "view", prUrl, "--json", "title,body"]),
    run(["omp", "token", "openrouter"]),
  ]);

  if (diffRes.code !== 0) throw new Error(`gh pr diff failed: ${diffRes.stderr.trim()}`);
  if (viewRes.code !== 0) throw new Error(`gh pr view failed: ${viewRes.stderr.trim()}`);

  const apiKey = keyRes.stdout.trim();
  if (!apiKey) throw new Error("no OpenRouter credentials resolved (omp token openrouter)");

  const meta = JSON.parse(viewRes.stdout) as { title?: string; body?: string };
  const diff = diffRes.stdout.slice(0, MAX_DIFF_CHARS);
  const truncated = diffRes.stdout.length > MAX_DIFF_CHARS;

  const prompt = [
    "Review this pull request diff. Be concise: a one-line verdict (APPROVE / REQUEST_CHANGES / COMMENT),",
    "then up to 5 findings max, each as `file:line — issue`. No praise, no preamble, no restating the diff.",
    "",
    `Title: ${meta.title ?? "(none)"}`,
    "",
    `Description:\n${meta.body ?? "(none)"}`,
    "",
    `Diff${truncated ? " (truncated)" : ""}:`,
    diff,
  ].join("\n");

  const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: MAX_OUTPUT_TOKENS,
      reasoning: { effort: REASONING_EFFORT },
      messages: [{ role: "user", content: prompt }],
    }),
  });
  if (!res.ok) throw new Error(`openrouter ${res.status}: ${(await res.text()).slice(0, 500)}`);

  const data = (await res.json()) as { choices?: { message?: { content?: string } }[] };
  const review = data.choices?.[0]?.message?.content?.trim();
  if (!review) throw new Error("empty response from gpt-5.6-luna");

  const body = `**Automated review — ${MODEL} via OpenRouter (reasoning: ${REASONING_EFFORT})**\n\n${review}`;
  const commentRes = await run(["gh", "pr", "comment", prUrl, "--body", body]);
  if (commentRes.code !== 0) throw new Error(`gh pr comment failed: ${commentRes.stderr.trim()}`);

  ctx.ui.notify(`Posted automated ${MODEL} review on ${prUrl}`, "info");
}

export default function prAutoReview(pi: ExtensionAPI): void {
  pi.on("tool_result", async (event, ctx) => {
    if (event.toolName !== "bash" || event.isError) return;

    const command = String((event.input as { command?: string } | undefined)?.command ?? "");
    if (!PR_CREATE_RE.test(command)) return;

    const outputText = event.content
      .filter((chunk): chunk is { type: "text"; text: string } => chunk.type === "text")
      .map((chunk) => chunk.text)
      .join("\n");
    const prUrl = outputText.match(PR_URL_RE)?.[0];
    if (!prUrl) return;

    try {
      await reviewAndComment(prUrl, ctx);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      ctx.ui.notify(`Automated PR review failed: ${message}`, "error");
    }
  });
}
