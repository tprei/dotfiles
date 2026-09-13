import type { AssistantMessage, Context, Message } from "@oh-my-pi/pi-ai";
import { sanitizeAgySystemText } from "./sanitize.ts";

type ContentBlock = AssistantMessage["content"][number];

function stringify(value: unknown): string {
	return JSON.stringify(value) ?? "";
}

function renderBlock(block: ContentBlock): string {
	switch (block.type) {
		case "text":
			return block.text;
		case "image":
			throw new Error("AGY CLI provider does not support image content.");
		case "toolCall":
			return `Tool call ${block.name} (${block.id}): ${stringify(block.arguments)}`;
		case "fallback":
			return `Provider fallback from ${stringify(block.from)} to ${stringify(block.to)}.`;
		case "anthropicServerTool":
			return `Server tool event: ${stringify(block.block)}`;
		case "thinking":
		case "redactedThinking":
			return "";
		default:
			throw new Error("AGY CLI provider does not support this content block.");
	}
}

function renderMessage(message: Message, index: number): string {
	let content: string;
	if (typeof message.content === "string") {
		content = message.content;
	} else {
		content = message.content.map(renderBlock).filter(Boolean).join("\n");
	}
	if (message.role === "toolResult") {
		const status = message.isError ? "error" : "success";
		return `TOOL RESULT ${index + 1} ${message.toolName} (${status}):\n${content}`;
	}

	return `${message.role.toUpperCase()} MESSAGE ${index + 1}:\n${content}`;
}
export function buildAgyPrompt(context: Context, previousMessageCount: number | undefined, toolPrompt?: string): string {
	const sections: string[] = [];
	let start = 0;
	if (previousMessageCount !== undefined) {
		start = Math.max(0, Math.min(previousMessageCount, context.messages.length));
	}

	if (previousMessageCount === undefined) {
		const systemSections = context.systemPrompt?.filter(Boolean) ?? [];
		if (toolPrompt) systemSections.push(toolPrompt);
		const system = sanitizeAgySystemText(systemSections.join("\n\n"));
		if (system) sections.push(`SYSTEM INSTRUCTIONS:\n${system}`);
	}

	for (let index = start; index < context.messages.length; index += 1) {
		sections.push(renderMessage(context.messages[index]!, index));
	}

	sections.push(
		"Respond to the latest request. This prompt is handled by OMP through the AGY CLI. Follow the XML tool-call format in the system instructions, emit the complete tool call and stop when a tool is needed, and do not invoke AGY-native tools because OMP executes tools.",
	);
	return sections.join("\n\n");
}
