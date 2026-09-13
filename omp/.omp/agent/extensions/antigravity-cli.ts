import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { createAssistantMessageEventStream } from "@oh-my-pi/pi-ai/utils/event-stream";
import type {
	Api,
	AssistantMessage,
	AssistantMessageEventStream,
	Context,
	Message,
	Model,
	SimpleStreamOptions,
	TextContent,
	Usage,
} from "@oh-my-pi/pi-ai";
import { renderInbandToolPrompt, wrapInbandToolStream } from "@oh-my-pi/pi-ai/dialect/index";
import { buildAgyPrompt } from "./antigravity-cli/context.ts";
import { AGY_API_ID, AGY_MODELS, AGY_PROVIDER_ID, resolveAgyModelId } from "./antigravity-cli/models.ts";
import { runAgyTurn, type AgyTurnResult } from "./antigravity-cli/process.ts";

type ConversationBinding = {
	conversationId: string;
	messageCount: number;
	prefixMessageCount: number;
	prefixFingerprint: string;
};

const AGY_API_KEY_MARKER = "AGY_CLI_MANAGED";
const bindings = new Map<string, ConversationBinding>();

function assistantFingerprint(message: AssistantMessage): object {
	return {
		role: message.role,
		content: message.content.map(block =>
			block.type === "toolCall"
				? {
						type: block.type,
						id: block.id,
						name: block.name,
						arguments: block.arguments,
						rawBlock: block.rawBlock,
					}
				: block,
		),
		provider: message.provider,
		model: message.model,
		responseId: message.responseId,
		stopReason: message.stopReason,
	};
}

function contextPrefixFingerprint(context: Context, messageCount: number, assistantMessage?: AssistantMessage): string {
	const messages = assistantMessage
		? [...context.messages.slice(0, messageCount), assistantFingerprint(assistantMessage)]
		: context.messages.slice(0, messageCount);
	const fingerprint = JSON.stringify(messages);
	if (fingerprint === undefined) throw new Error("OMP context could not be serialized for AGY conversation reuse.");
	return fingerprint;
}

function bindingMatches(context: Context, binding: ConversationBinding): boolean {
	if (context.messages.length < binding.messageCount) return false;
	const assistantMessage = context.messages[binding.prefixMessageCount];
	if (assistantMessage?.role !== "assistant") return false;
	return contextPrefixFingerprint(context, binding.prefixMessageCount, assistantMessage) === binding.prefixFingerprint;
}

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

function streamAgy(
	model: Model<Api>,
	context: Context,
	options: SimpleStreamOptions | undefined,
): AssistantMessageEventStream {
	const initialMessageCount = context.messages.length;
	const stream = createAssistantMessageEventStream();
	const key = bindingKey(options);
	const currentBinding = key ? bindings.get(key) : undefined;
	const canResume = currentBinding !== undefined && bindingMatches(context, currentBinding);
	const previousMessageCount = canResume ? currentBinding.messageCount : undefined;
	const conversationId = canResume ? currentBinding.conversationId : undefined;
	const partial = createAssistantMessage(model);
	const tools = context.tools ?? [];
	let textBlock: TextContent | undefined;
	let streamedText = "";

	const emitTextDelta = (delta: string): void => {
		if (!textBlock) {
			textBlock = { type: "text", text: "" };
			partial.content = [textBlock];
			partial.ttft = Date.now() - partial.timestamp;
			stream.push({ type: "text_start", contentIndex: 0, partial });
		}
		streamedText += delta;
		textBlock.text = streamedText;
		stream.push({ type: "text_delta", contentIndex: 0, delta, partial });
	};

	stream.push({ type: "start", partial });
	void (async () => {
		try {
			const prompt = buildAgyPrompt(
				context,
				previousMessageCount,
				tools.length > 0 ? renderInbandToolPrompt(tools, "xml") : undefined,
			);
			const result = await stream.trackLocalWork(
				runAgyTurn({
					prompt,
					modelId: resolveAgyModelId(model.id, options?.reasoning, options?.disableReasoning),
					conversationId,
					cwd: options?.cwd ?? process.cwd(),
					signal: options?.signal,
					onTextDelta: emitTextDelta,
				}),
			);
			const response = result.response;
			if (!textBlock && response.length > 0) emitTextDelta(response);
			if (textBlock) textBlock.text = response;
			partial.content = textBlock ? [textBlock] : [];
			partial.usage = usageFromResult(result);
			partial.responseId = result.conversationId;
			if (result.durationMs !== undefined) partial.duration = result.durationMs;
			partial.stopReason = "stop";
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
			stream.push({ type: "error", reason, error: partial });
		}
	})();
	const wrapped = wrapInbandToolStream(stream, tools, "xml");
	wrapped.forwardLocalWorkFrom(stream);
	const output = createAssistantMessageEventStream();
	output.forwardLocalWorkFrom(wrapped);
	void (async () => {
		try {
			for await (const event of wrapped) {
				if (event.type === "done") {
					if (key && event.message.responseId) {
						bindings.set(key, {
							conversationId: event.message.responseId,
							messageCount: initialMessageCount + 1,
							prefixMessageCount: initialMessageCount,
							prefixFingerprint: contextPrefixFingerprint(context, initialMessageCount, event.message),
						});
					}
					output.forwardLocalWorkFrom(undefined);
				} else if (event.type === "error") {
					if (key) bindings.delete(key);
					output.forwardLocalWorkFrom(undefined);
				}
				output.push(event);
			}
		} catch (error) {
			if (key) bindings.delete(key);
			output.forwardLocalWorkFrom(undefined);
			output.fail(error);
		}
	})();
	return output;
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
