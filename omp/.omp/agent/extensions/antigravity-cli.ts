import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { createAssistantMessageEventStream } from "@oh-my-pi/pi-ai/utils/event-stream";
import type {
	Api,
	AssistantMessage,
	AssistantMessageEventStream,
	Context,
	Model,
	SimpleStreamOptions,
	TextContent,
	Usage,
} from "@oh-my-pi/pi-ai";
import { buildAgyPrompt } from "./antigravity-cli/context.ts";
import { AGY_API_ID, AGY_MODELS, AGY_PROVIDER_ID, resolveAgyModelId } from "./antigravity-cli/models.ts";
import { runAgyTurn, type AgyTurnResult } from "./antigravity-cli/process.ts";

type ConversationBinding = {
	conversationId: string;
	messageCount: number;
};

const AGY_API_KEY_MARKER = "AGY_CLI_MANAGED";
const bindings = new Map<string, ConversationBinding>();

function bindingKey(options: SimpleStreamOptions | undefined): string | undefined {
	const sessionId = options?.sessionId;
	if (!sessionId) return undefined;
	const isTitleRequest =
		options.disableReasoning === true &&
		options.temperature === 0 &&
		options.maxTokens !== undefined &&
		options.maxTokens <= 1_024;
	if (isTitleRequest) return undefined;
	return sessionId;
}

function usageFromResult(result: AgyTurnResult): Usage {
	const input = result.inputTokens ?? 0;
	const output = result.outputTokens ?? 0;
	const cacheRead = result.cacheReadTokens ?? 0;
	const totalTokens = result.totalTokens ?? input + output + cacheRead;
	const usage: Usage = {
		input,
		output,
		cacheRead,
		cacheWrite: 0,
		totalTokens,
		cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
	};
	if (result.thinkingTokens !== undefined) usage.reasoningTokens = result.thinkingTokens;
	return usage;
}

function createAssistantMessage(model: Model<Api>): AssistantMessage {
	return {
		role: "assistant",
		content: [],
		api: AGY_API_ID,
		provider: AGY_PROVIDER_ID,
		model: model.id,
		usage: {
			input: 0,
			output: 0,
			cacheRead: 0,
			cacheWrite: 0,
			totalTokens: 0,
			cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
		},
		stopReason: "stop",
		timestamp: Date.now(),
	};
}

function errorStatus(error: unknown): number | undefined {
	if (typeof error !== "object" || error === null || !("status" in error)) return undefined;
	const status = error.status;
	return typeof status === "number" && Number.isFinite(status) ? status : undefined;
}

function streamAgy(
	model: Model<Api>,
	context: Context,
	options: SimpleStreamOptions | undefined,
): AssistantMessageEventStream {
	const stream = createAssistantMessageEventStream();
	const key = bindingKey(options);
	const currentBinding = key ? bindings.get(key) : undefined;
	const canResume = currentBinding !== undefined && context.messages.length >= currentBinding.messageCount;
	const previousMessageCount = canResume ? currentBinding.messageCount : undefined;
	const conversationId = canResume ? currentBinding.conversationId : undefined;
	const partial = createAssistantMessage(model);
	let textBlock: TextContent | undefined;
	let streamedText = "";

	const emitTextDelta = (delta: string): void => {
		if (!textBlock) {
			textBlock = { type: "text", text: "" };
			partial.content = [textBlock];
			stream.push({ type: "text_start", contentIndex: 0, partial });
		}
		streamedText += delta;
		textBlock.text = streamedText;
		stream.push({ type: "text_delta", contentIndex: 0, delta, partial });
	};

	stream.push({ type: "start", partial });
	void (async () => {
		try {
			const prompt = buildAgyPrompt(context, previousMessageCount);
			const result = await runAgyTurn({
				prompt,
				modelId: resolveAgyModelId(model.id, options?.reasoning, options?.disableReasoning),
				cwd: options?.cwd ?? process.cwd(),
				signal: options?.signal,
				dangerouslySkipPermissions: process.env.AGY_OMP_DANGEROUSLY_SKIP_PERMISSIONS === "1",
				onTextDelta: emitTextDelta,
			});
			let response = result.response;
			if (response.length === 0 && streamedText.length > 0) response = streamedText;
			if (!textBlock && response.length > 0) emitTextDelta(response);
			if (textBlock) textBlock.text = response;
			partial.content = textBlock ? [textBlock] : [];
			partial.usage = usageFromResult(result);
			partial.responseId = result.conversationId;
			if (result.durationMs !== undefined) partial.duration = result.durationMs;
			partial.stopReason = "stop";
			if (key) {
				bindings.set(key, {
					conversationId: result.conversationId,
					messageCount: context.messages.length + 1,
				});
			}
			if (textBlock) stream.push({ type: "text_end", contentIndex: 0, content: response, partial });
			stream.push({ type: "done", reason: "stop", message: partial });
		} catch (error) {
			if (key) bindings.delete(key);
			const reason: "aborted" | "error" =
				options?.signal?.aborted === true || (error instanceof Error && error.name === "AbortError")
					? "aborted"
					: "error";
			partial.stopReason = reason;
			partial.errorMessage = error instanceof Error ? error.message : String(error);
			const status = errorStatus(error);
			if (status !== undefined) partial.errorStatus = status;
			stream.push({ type: "error", reason, error: partial });
		}
	})();
	return stream;
}

export default function antigravityCli(pi: ExtensionAPI): void {
	pi.registerProvider(AGY_PROVIDER_ID, {
		baseUrl: "agy://cli",
		api: AGY_API_ID,
		apiKey: AGY_API_KEY_MARKER,
		models: AGY_MODELS,
		streamSimple: streamAgy,
	});
	pi.on("session_shutdown", () => {
		bindings.clear();
	});
}
