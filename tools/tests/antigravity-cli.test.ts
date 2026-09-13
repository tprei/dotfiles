import { afterAll, afterEach, beforeAll, expect, test } from "bun:test";
import { chmod, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { buildAgyPrompt } from "../../omp/.omp/agent/extensions/antigravity-cli/context";
import { AGY_MODELS } from "../../omp/.omp/agent/extensions/antigravity-cli/models";
import { runAgyTurn } from "../../omp/.omp/agent/extensions/antigravity-cli/process";

const FAKE_AGY = `#!/usr/bin/env bun
import { writeFileSync } from "node:fs";
writeFileSync(process.env.AGY_TEST_ARGV ?? "", JSON.stringify(process.argv.slice(2)));
writeFileSync(process.env.AGY_TEST_CWD ?? "", process.cwd());
const scenario = process.env.AGY_TEST_SCENARIO ?? "";
if (scenario === "early-close") {
	process.exit(0);
}
let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => {
	input += chunk;
});
process.stdin.on("end", () => {
	writeFileSync(process.env.AGY_TEST_STDIN ?? "", input);
	const scenarios = {
		success: [
			{ event: "init", conversation_id: "conv-init" },
			{ event: "step_update", step_update: { step_type: "agent_response", text_delta: "streamed " } },
			{ event: "step_update", step_update: { step_type: "agent_response", text_delta: "delta" } },
			{ event: "result", result: { status: "SUCCESS", conversation_id: "conv-final", response: "final answer", usage: { input_tokens: 11, output_tokens: 7, thinking_tokens: 3, cache_read_tokens: 2, total_tokens: 23 }, duration_seconds: 1.25 } },
		],
		streamed: [
			{ event: "init", conversation_id: "conv-stream" },
			{ event: "step_update", step_update: { step_type: "agent_response", text_delta: "alpha " } },
			{ event: "step_update", step_update: { step_type: "agent_response", text_delta: "beta" } },
			{ event: "result", result: { status: "SUCCESS", response: "" } },
		],
		denied: [
			{ event: "result", result: { status: "SUCCESS", response: "done", denied_actions: [{ action: "run_command", reason: "not approved" }] } },
		],
		"error-event": [
			{ event: "error", error: { message: "gemini quota exceeded" } },
		],
	};
	for (const event of scenarios[scenario] ?? []) {
		process.stdout.write(JSON.stringify(event) + "\\n");
	}
	process.exit(0);
});
`;

const originalAgyBin = process.env.AGY_BIN;
let directory = "";
let argvPath = "";
let stdinPath = "";
let cwdPath = "";

beforeAll(async () => {
	directory = await mkdtemp("/tmp/agy-cli-test-");
	const executable = join(directory, "agy-fake.mjs");
	await writeFile(executable, FAKE_AGY);
	await chmod(executable, 0o755);
	argvPath = join(directory, "argv.json");
	stdinPath = join(directory, "stdin.json");
	cwdPath = join(directory, "cwd.txt");
	process.env.AGY_BIN = executable;
	process.env.AGY_TEST_ARGV = argvPath;
	process.env.AGY_TEST_STDIN = stdinPath;
	process.env.AGY_TEST_CWD = cwdPath;
});

afterEach(() => {
	delete process.env.AGY_TEST_SCENARIO;
});

afterAll(async () => {
	if (originalAgyBin === undefined) delete process.env.AGY_BIN;
	else process.env.AGY_BIN = originalAgyBin;
	delete process.env.AGY_TEST_ARGV;
	delete process.env.AGY_TEST_STDIN;
	delete process.env.AGY_TEST_CWD;
	delete process.env.AGY_TEST_SCENARIO;
	await rm(directory, { recursive: true, force: true });
});

test("advertises native tool support and real AGY effort levels", () => {
	expect(AGY_MODELS.map(model => model.id)).toEqual([
		"gemini-3.8-flash",
		"gemini-3.7-flash",
		"gemini-3.6-flash",
		"gemini-3.1-pro",
	]);
	for (const model of AGY_MODELS) {
		expect(model.supportsTools).toBe(true);
		expect(model.thinking?.mode).toBe("effort");
		expect(model.thinking?.defaultLevel).toBe("high");
	}
	for (const model of AGY_MODELS.filter(candidate => candidate.id.endsWith("flash"))) {
		expect(model.thinking?.efforts).toEqual(["low", "medium", "high"]);
	}
	expect(AGY_MODELS.find(model => model.id === "gemini-3.1-pro")?.thinking?.efforts).toEqual(["low", "high"]);
});

test("sanitizes system text but preserves identical text in user and tool-result messages", () => {
	const prompt = buildAgyPrompt(
		{
			systemPrompt: ["<system-conventions>Oh My Pi coding harness rules</system-conventions> <critical>stay strict</critical>"],
			messages: [
				{ role: "user", content: "Oh My Pi sent <system-directive> and <critical> text" },
				{ role: "toolResult", content: "Oh My Pi sent <system-directive> and <critical> text", toolCallId: "call-1", toolName: "read", isError: false },
			],
		},
		undefined,
	);
	const sections = prompt.split("\n\n");
	expect(sections[0]).toBe("SYSTEM INSTRUCTIONS:\n<conventions>AI coding assistant rules</conventions> <important>stay strict</important>");
	expect(sections[1]).toBe("USER MESSAGE 1:\nOh My Pi sent <system-directive> and <critical> text");
	expect(sections[2]).toBe("TOOL RESULT 2 read (success):\nOh My Pi sent <system-directive> and <critical> text");
});

test("renders OMP tools with the XML transport dialect", () => {
	const prompt = buildAgyPrompt({
		messages: [{ role: "user", content: "review this" }],
		tools: [{
			name: "read",
			description: "Read a file.",
			parameters: {
				type: "object",
				properties: {
					path: { type: "string" },
				},
				required: ["path"],
				additionalProperties: false,
			},
		}],
	}, undefined, '## Format guide\n<invoke name="fn"><parameter name="arg">value</parameter></invoke>\n## read');
	const instruction = prompt.split("\n\n").at(-1) ?? "";
	expect(prompt).toContain('<invoke name="fn"><parameter name="arg">value</parameter></invoke>');
	expect(prompt).toContain("## read");
	expect(instruction).toContain("Follow the XML tool-call format in the system instructions");
	expect(instruction).toContain("do not invoke AGY-native tools because OMP executes tools");
	expect(prompt).not.toContain("```tool_code");
});

test("parses a successful turn from the fake executable", async () => {
	process.env.AGY_TEST_SCENARIO = "success";
	const deltas: string[] = [];
	const result = await runAgyTurn({
		prompt: "Report Oh My Pi verbatim",
		modelId: "gemini-3.8-flash",
		conversationId: "conv-request",
		cwd: directory,
		onTextDelta: delta => deltas.push(delta),
	});
	expect(result.conversationId).toBe("conv-final");
	expect(result.response).toBe("final answer");
	expect(result.inputTokens).toBe(11);
	expect(result.outputTokens).toBe(7);
	expect(result.thinkingTokens).toBe(3);
	expect(result.cacheReadTokens).toBe(2);
	expect(result.totalTokens).toBe(23);
	expect(result.durationMs).toBe(1250);
	expect(deltas.join("")).toBe("streamed delta");
	const args: string[] = JSON.parse(await readFile(argvPath, "utf8"));
	expect(args[0]).toBe("--print=");
	expect(args[args.indexOf("--input-format") + 1]).toBe("stream-json");
	expect(args[args.indexOf("--output-format") + 1]).toBe("stream-json");
	expect(args[args.indexOf("--print-timeout") + 1]).toBe("10m");
	expect(args[args.indexOf("--model") + 1]).toBe("gemini-3.8-flash");
	expect(args).not.toContain("--agent");
	expect(args).toContain("--disable-slash-commands");
	expect(args[args.indexOf("--conversation") + 1]).toBe("conv-request");
	expect(args).not.toContain("--dangerously-skip-permissions");
	const stdinEvent: { event: string; message: { role: string; content: string } } = JSON.parse(await readFile(stdinPath, "utf8"));
	expect(stdinEvent.message.content).toBe("Report Oh My Pi verbatim");
	expect(await readFile(cwdPath, "utf8")).toBe(directory);
});

test("falls back to streamed deltas when the result response is empty", async () => {
	process.env.AGY_TEST_SCENARIO = "streamed";
	const result = await runAgyTurn({ prompt: "stream fallback", modelId: "gemini-3.6-flash", cwd: directory });
	expect(result.response).toBe("alpha beta");
	expect(result.conversationId).toBe("conv-stream");
	const args: string[] = JSON.parse(await readFile(argvPath, "utf8"));
	expect(args).not.toContain("--conversation");
	expect(args[args.indexOf("--agent") + 1]).toBe("omp-provider");
});

test("rejects a successful result with denied actions", async () => {
	process.env.AGY_TEST_SCENARIO = "denied";
	const failure = await runAgyTurn({ prompt: "denied", modelId: "gemini-3.8-flash", cwd: directory }).then(
		() => {
			throw new Error("AGY turn unexpectedly succeeded");
		},
		(error: unknown) => error,
	);
	expect(failure).toBeInstanceOf(Error);
	expect(String(failure)).toContain("denied 1 action");
	expect(String(failure)).toContain("run_command");
});

test("rejects an error stream event", async () => {
	process.env.AGY_TEST_SCENARIO = "error-event";
	const failure = await runAgyTurn({ prompt: "failing", modelId: "gemini-3.8-flash", cwd: directory }).then(
		() => {
			throw new Error("AGY turn unexpectedly succeeded");
		},
		(error: unknown) => error,
	);
	expect(failure).toBeInstanceOf(Error);
	expect(String(failure)).toContain("error event");
	expect(String(failure)).toContain("gemini quota exceeded");
});

test("rejects when the CLI closes stdin early without an uncaught pipe error", async () => {
	process.env.AGY_TEST_SCENARIO = "early-close";
	await expect(runAgyTurn({ prompt: "bye", modelId: "gemini-3.8-flash", cwd: directory })).rejects.toThrow();
});
