import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { isRecord } from "@oh-my-pi/pi-utils/type-guards";

const MAX_STDERR_LENGTH = 16_384;

interface AgyUsageFields {
	inputTokens?: number;
	outputTokens?: number;
	thinkingTokens?: number;
	cacheReadTokens?: number;
	totalTokens?: number;
}

export interface AgyTurnRequest {
	prompt: string;
	modelId: string;
	conversationId?: string;
	cwd: string;
	signal?: AbortSignal;
	dangerouslySkipPermissions: boolean;
	onTextDelta?: (delta: string) => void;
}

export interface AgyTurnResult extends AgyUsageFields {
	conversationId: string;
	response: string;
	durationMs?: number;
}

class AgyProcessError extends Error {
	readonly status?: number;

	constructor(message: string, status?: number) {
		super(message);
		this.name = "AgyProcessError";
		this.status = status;
	}
}

class AgyAbortError extends AgyProcessError {
	constructor() {
		super("AGY CLI request aborted");
		this.name = "AbortError";
	}
}

function readString(record: Record<string, unknown>, key: string): string | undefined {
	const value = record[key];
	return typeof value === "string" ? value : undefined;
}

function readNumber(record: Record<string, unknown>, key: string): number | undefined {
	const value = record[key];
	return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function parseEvent(line: string): Record<string, unknown> {
	let value: unknown;
	try {
		value = JSON.parse(line);
	} catch (error) {
		const detail = error instanceof Error ? error.message : String(error);
		throw new AgyProcessError(`AGY CLI emitted malformed JSON: ${detail}`);
	}
	if (!isRecord(value)) {
		throw new AgyProcessError("AGY CLI emitted a non-object stream event.");
	}
	return value;
}

function parseUsage(value: unknown): AgyUsageFields | undefined {
	if (!isRecord(value)) return undefined;
	const usage: AgyUsageFields = {
		inputTokens: readNumber(value, "input_tokens"),
		outputTokens: readNumber(value, "output_tokens"),
		thinkingTokens: readNumber(value, "thinking_tokens"),
		cacheReadTokens: readNumber(value, "cache_read_tokens"),
		totalTokens: readNumber(value, "total_tokens"),
	};
	if (Object.values(usage).every(entry => entry === undefined)) return undefined;
	return usage;
}

function errorWithStderr(message: string, stderr: string): AgyProcessError {
	const detail = stderr.trim();
	return detail ? new AgyProcessError(`${message}\nAGY stderr:\n${detail}`) : new AgyProcessError(message);
}

export async function runAgyTurn(request: AgyTurnRequest): Promise<AgyTurnResult> {
	if (request.signal?.aborted) throw new AgyAbortError();

	const executable = process.env.AGY_BIN?.trim() || "agy";
	const args = [
		"--print=",
		"--input-format",
		"stream-json",
		"--output-format",
		"stream-json",
		"--model",
		request.modelId,
		"--disable-slash-commands",
	];
	if (request.conversationId) args.push("--conversation", request.conversationId);
	if (request.dangerouslySkipPermissions) args.push("--dangerously-skip-permissions");

	const child = spawn(executable, args, {
		cwd: request.cwd,
		shell: false,
		stdio: ["pipe", "pipe", "pipe"],
	});
	if (!child.stdin || !child.stdout || !child.stderr) {
		child.kill("SIGTERM");
		throw new AgyProcessError("AGY CLI process did not expose piped stdio.");
	}

	return await new Promise<AgyTurnResult>((resolve, reject) => {
		let settled = false;
		let childClosed = false;
		let forceKillTimer: ReturnType<typeof setTimeout> | undefined;
		let conversationId: string | undefined;
		let responseFromResult: string | undefined;
		let responseFromDeltas = "";
		let resultUsage: AgyUsageFields | undefined;
		let durationMs: number | undefined;
		let resultSeen = false;
		let stderr = "";

		const lines = createInterface({ input: child.stdout });

		const clearForceKillTimer = (): void => {
			if (forceKillTimer === undefined) return;
			clearTimeout(forceKillTimer);
			forceKillTimer = undefined;
		};

		const cleanup = (): void => {
			request.signal?.removeEventListener("abort", onAbort);
			lines.close();
			if (childClosed) clearForceKillTimer();
		};

		const settleReject = (error: unknown): void => {
			if (settled) return;
			settled = true;
			cleanup();
			reject(error);
		};

		const settleResolve = (result: AgyTurnResult): void => {
			if (settled) return;
			settled = true;
			cleanup();
			resolve(result);
		};

		const terminate = (): void => {
			if (childClosed || child.exitCode !== null || child.signalCode !== null) return;
			child.kill("SIGTERM");
			forceKillTimer = setTimeout(() => {
				if (!childClosed && child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
			}, 1_000);
			forceKillTimer.unref?.();
		};

		const fail = (error: unknown): void => {
			terminate();
			settleReject(error instanceof Error ? error : new AgyProcessError(String(error)));
		};

		const onAbort = (): void => {
			fail(new AgyAbortError());
		};

		lines.on("line", line => {
			if (settled || line.trim().length === 0) return;
			try {
				const event = parseEvent(line);
				switch (event.event) {
					case "init": {
						const value = readString(event, "conversation_id")?.trim();
						if (value) conversationId = value;
						break;
					}
					case "step_update": {
						if (!isRecord(event.step_update) || event.step_update.step_type !== "agent_response") break;
						const delta = readString(event.step_update, "text_delta");
						if (!delta) break;
						responseFromDeltas += delta;
						request.onTextDelta?.(delta);
						break;
					}
					case "result": {
						if (!isRecord(event.result)) throw new AgyProcessError("AGY CLI emitted an invalid result event.");
						resultSeen = true;
						const status = readString(event.result, "status");
						if (status !== "SUCCESS") {
							const statusCode = readNumber(event.result, "status_code") ?? readNumber(event.result, "http_status");
							const detail = JSON.stringify(event.result) ?? "";
							throw new AgyProcessError(
								errorWithStderr(
									`AGY CLI returned status ${status ?? "unknown"}${detail ? `: ${detail.slice(0, 2_000)}` : "."}`,
									stderr,
								).message,
								statusCode,
							);
						}
						const resultConversationId = readString(event.result, "conversation_id")?.trim();
						if (resultConversationId) conversationId = resultConversationId;
						responseFromResult = readString(event.result, "response");
						resultUsage = parseUsage(event.result.usage);
						const seconds = readNumber(event.result, "duration_seconds");
						if (seconds !== undefined) durationMs = Math.max(0, Math.round(seconds * 1_000));
						break;
					}
				}
			} catch (error) {
				fail(error);
			}
		});

		child.stderr.on("data", chunk => {
			stderr += String(chunk);
			if (stderr.length > MAX_STDERR_LENGTH) stderr = stderr.slice(-MAX_STDERR_LENGTH);
		});
		child.stdout.on("error", fail);
		child.stderr.on("error", fail);
		child.once("error", fail);
		child.once("close", (code, signal) => {
			childClosed = true;
			clearForceKillTimer();
			lines.close();
			if (settled) return;
			if (code !== 0) {
				settleReject(errorWithStderr(`AGY CLI exited with ${signal ? `signal ${signal}` : `code ${code}`}.`, stderr));
				return;
			}
			if (!resultSeen) {
				settleReject(errorWithStderr("AGY CLI exited without a result event.", stderr));
				return;
			}
			if (!conversationId) {
				settleReject(errorWithStderr("AGY CLI completed without a conversation id.", stderr));
				return;
			}
			settleResolve({
				conversationId,
				response: responseFromResult ?? responseFromDeltas,
				...resultUsage,
				durationMs,
			});
		});

		request.signal?.addEventListener("abort", onAbort, { once: true });
		if (request.signal?.aborted) {
			onAbort();
			return;
		}
		try {
			const input = JSON.stringify({
				event: "user",
				message: { role: "user", content: request.prompt },
			});
			child.stdin.end(`${input}\n`);
		} catch (error) {
			fail(error);
		}
	});
}
