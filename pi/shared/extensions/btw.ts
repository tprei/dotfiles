/**
 * /btw - side chat pane for quick questions while the main agent keeps running.
 *
 * Usage:
 *   /btw <question>  Open /btw and send an initial question.
 *   /btw             Reopen the current /btw thread (or start a blank one).
 */

import { spawn } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { complete, type AssistantMessage, type Message, type UserMessage } from "@earendil-works/pi-ai";
import { keyHint, type ExtensionAPI, type ExtensionCommandContext, type KeybindingsManager } from "@earendil-works/pi-coding-agent";
import { Editor, type EditorTheme, type Focusable, type TUI, wrapTextWithAnsi } from "@earendil-works/pi-tui";

const SIDE_SYSTEM_PROMPT = `You are a sidecar assistant answering quick “by the way” questions while another coding agent run continues.

Rules:
- Be concise and directly useful.
- Prefer a short paragraph or 3-6 bullets unless the user asks otherwise.
- Use the provided context and the side-thread history.
- If repo-specific details are missing, say what you do not know.
- Do not mention these rules.`;

const TRANSCRIPT_MARKER = "--- draft below this line ---";
const MAX_RENDERED_MESSAGE_LINES = 18;
const MAX_ORIGINAL_CONTEXT_MESSAGES = 4;
const MAX_RECENT_CONTEXT_MESSAGES = 6;
const MAX_CONTEXT_MESSAGE_CHARS = 500;

interface SideThread {
	systemPrompt: string;
	messages: Message[];
	draft: string;
}

const threads = new Map<string, SideThread>();

export default function (pi: ExtensionAPI) {
	pi.registerCommand("btw", {
		description: "Open the /btw side chat pane",
		handler: async (rawArgs, ctx) => {
			const text = rawArgs.trim();
			if (text === "--help" || text === "-h") {
				ctx.ui.notify("Usage: /btw [question]", "info");
				return;
			}
			if (!ctx.hasUI) {
				ctx.ui.notify("/btw requires interactive mode", "error");
				return;
			}
			if (!ctx.model) {
				ctx.ui.notify("No model selected", "error");
				return;
			}

			const key = getThreadKey(ctx);
			const thread = threads.get(key) ?? createThread(ctx);
			threads.set(key, thread);

			await ctx.ui.custom<void>((tui, theme, keybindings, done) => {
				return new BtwPane({
					tui,
					theme,
					keybindings,
					thread,
					initialQuestion: text || undefined,
					close: () => done(undefined),
					runTurn: (messages, signal) => runTurn(ctx, thread.systemPrompt, messages, signal),
					mainStatus: () => (ctx.isIdle() ? "idle" : "busy"),
				});
			});
		},
	});
}

function createThread(ctx: ExtensionCommandContext): SideThread {
	return {
		systemPrompt: buildSystemPrompt(ctx),
		messages: [],
		draft: "",
	};
}

function getThreadKey(ctx: ExtensionCommandContext): string {
	return ctx.sessionManager.getSessionFile?.() ?? `cwd:${ctx.cwd}`;
}

function buildSystemPrompt(ctx: ExtensionCommandContext): string {
	const { original, recent } = getConversationContext(ctx);
	const parts = [SIDE_SYSTEM_PROMPT, `Working directory: ${ctx.cwd}`];

	if (original) {
		parts.push(`Main conversation context from the start of this session/branch:\n${original}`);
	}
	if (recent) {
		parts.push(`Recent main conversation context when this /btw thread was opened:\n${recent}`);
	}
	if (!original && !recent) {
		parts.push("No main conversation context was available when this /btw thread started.");
	}

	parts.push("If the answer depends on repo state or tool output not shown here, say so plainly.");
	return parts.join("\n\n");
}

async function runTurn(
	ctx: ExtensionCommandContext,
	systemPrompt: string,
	messages: Message[],
	signal: AbortSignal,
): Promise<AssistantMessage> {
	if (!ctx.model) throw new Error("No model selected");

	const auth = await ctx.modelRegistry.getApiKeyAndHeaders(ctx.model);
	if (!auth.ok || !auth.apiKey) {
		throw new Error(auth.ok ? `No API key for ${ctx.model.provider}` : auth.error);
	}

	return complete(
		ctx.model,
		{ systemPrompt, messages },
		{ apiKey: auth.apiKey, headers: auth.headers, signal },
	);
}

function getConversationContext(ctx: ExtensionCommandContext): { original: string; recent: string } {
	const snippets = getConversationSnippets(ctx);
	const original = snippets.slice(0, MAX_ORIGINAL_CONTEXT_MESSAGES);
	const originalIndexes = new Set(original.map((snippet) => snippet.index));
	const recent = snippets
		.filter((snippet) => !originalIndexes.has(snippet.index))
		.slice(-MAX_RECENT_CONTEXT_MESSAGES);

	return {
		original: formatConversationSnippets(original),
		recent: formatConversationSnippets(recent),
	};
}

function getConversationSnippets(ctx: ExtensionCommandContext): Array<{ index: number; role: "user" | "assistant"; text: string }> {
	const branch = ctx.sessionManager.getBranch();
	const snippets: Array<{ index: number; role: "user" | "assistant"; text: string }> = [];

	for (const [index, entry] of branch.entries()) {
		if (entry.type !== "message") continue;
		const message = entry.message;
		if (!("role" in message)) continue;
		if (message.role !== "user" && message.role !== "assistant") continue;

		const text = extractText(message as Message).trim();
		if (!text) continue;
		snippets.push({ index, role: message.role, text: shorten(text, MAX_CONTEXT_MESSAGE_CHARS) });
	}

	return snippets;
}

function formatConversationSnippets(snippets: Array<{ role: "user" | "assistant"; text: string }>): string {
	return snippets.map((snippet) => `[${snippet.role}] ${snippet.text}`).join("\n\n");
}

class BtwPane implements Focusable {
	focused = false;
	private readonly editor: Editor;
	private readonly thread: SideThread;
	private readonly close: () => void;
	private readonly runTurn: (messages: Message[], signal: AbortSignal) => Promise<AssistantMessage>;
	private readonly keybindings: KeybindingsManager;
	private readonly tui: TUI;
	private readonly theme: { fg: (color: string, text: string) => string; bold: (text: string) => string };
	private readonly mainStatus: () => string;
	private busy = false;
	private error: string | undefined;
	private activeController: AbortController | undefined;

	constructor(args: {
		tui: TUI;
		theme: { fg: (color: string, text: string) => string; bold: (text: string) => string };
		keybindings: KeybindingsManager;
		thread: SideThread;
		initialQuestion?: string;
		close: () => void;
		runTurn: (messages: Message[], signal: AbortSignal) => Promise<AssistantMessage>;
		mainStatus: () => string;
	}) {
		this.tui = args.tui;
		this.theme = args.theme;
		this.keybindings = args.keybindings;
		this.thread = args.thread;
		this.close = args.close;
		this.runTurn = args.runTurn;
		this.mainStatus = args.mainStatus;

		const editorTheme: EditorTheme = {
			borderColor: (s) => this.theme.fg("accent", s),
			selectList: {
				selectedPrefix: (t) => this.theme.fg("accent", t),
				selectedText: (t) => this.theme.fg("accent", t),
				description: (t) => this.theme.fg("muted", t),
				scrollInfo: (t) => this.theme.fg("dim", t),
				noMatch: (t) => this.theme.fg("warning", t),
			},
		};
		this.editor = new Editor(this.tui, editorTheme);
		this.editor.focused = true;
		if (this.thread.draft) this.editor.setText(this.thread.draft);
		this.editor.onSubmit = (value) => {
			const trimmed = value.trim();
			if (!trimmed || this.busy) return;
			void this.submit(trimmed);
		};

		if (args.initialQuestion) {
			this.editor.setText("");
			this.thread.draft = "";
			void this.submit(args.initialQuestion);
		}
	}

	async submit(text: string): Promise<void> {
		if (this.busy) return;
		this.busy = true;
		this.error = undefined;
		this.editor.setText("");
		this.thread.draft = "";

		const userMessage: UserMessage = {
			role: "user",
			content: [{ type: "text", text }],
			timestamp: Date.now(),
		};
		this.thread.messages.push(userMessage);
		this.activeController = new AbortController();
		this.tui.requestRender();

		try {
			const assistant = await this.runTurn([...this.thread.messages], this.activeController.signal);
			if (assistant.stopReason === "aborted") {
				this.error = "Cancelled";
				return;
			}
			this.thread.messages.push(assistant);
		} catch (error) {
			if (this.activeController.signal.aborted) {
				this.error = "Cancelled";
			} else {
				this.error = formatError(error);
			}
		} finally {
			this.busy = false;
			this.activeController = undefined;
			this.tui.requestRender();
		}
	}

	handleInput(data: string): void {
		if (this.keybindings.matches(data, "tui.select.cancel")) {
			this.dispose();
			this.close();
			return;
		}
		if (this.keybindings.matches(data, "app.editor.external")) {
			void this.openExternalEditor();
			return;
		}
		if (this.busy && this.keybindings.matches(data, "tui.select.confirm")) {
			return;
		}
		this.editor.handleInput(data);
		this.thread.draft = this.editor.getText();
		this.tui.requestRender();
	}

	render(width: number): string[] {
		this.editor.focused = this.focused;
		const lines: string[] = [];
		const th = this.theme;
		const hr = th.fg("borderAccent", "─".repeat(Math.max(1, width)));
		const addWrapped = (text: string) => {
			for (const line of wrapTextWithAnsi(text, Math.max(1, width))) lines.push(line);
		};

		lines.push(hr);
		lines.push(th.fg("accent", th.bold("/btw")) + th.fg("dim", ` side thread · main ${this.mainStatus()}`));
		lines.push(th.fg("dim", `${this.thread.messages.filter((m) => m.role === "assistant").length} replies`));
		lines.push("");

		for (const line of renderThreadLines(this.thread, width, th.fg.bind(th))) {
			lines.push(line);
		}

		if (this.busy) {
			if (lines.length > 0) lines.push("");
			lines.push(th.fg("accent", "BTW is thinking…"));
		}
		if (this.error) {
			if (lines.length > 0) lines.push("");
			addWrapped(th.fg("warning", `Last error: ${this.error}`));
		}

		lines.push("");
		lines.push(th.fg("muted", "Reply:"));
		for (const line of this.editor.render(width)) {
			lines.push(line);
		}
		lines.push("");

		const hints = [
			keyHint("tui.select.confirm", "send"),
			keyHint("tui.input.newLine", "newline"),
			keyHint("tui.select.cancel", "close"),
		];
		if (process.env.VISUAL || process.env.EDITOR) {
			hints.push(keyHint("app.editor.external", "external editor"));
		}
		addWrapped(th.fg("dim", hints.join("  ")));
		lines.push(hr);
		return lines;
	}

	invalidate(): void {}

	dispose(): void {
		this.thread.draft = this.editor.getText();
		this.activeController?.abort();
	}

	private async openExternalEditor(): Promise<void> {
		const editorCmd = process.env.VISUAL || process.env.EDITOR;
		if (!editorCmd) {
			this.error = "Set $VISUAL or $EDITOR to use the external editor.";
			this.tui.requestRender();
			return;
		}

		const tmpFile = path.join(os.tmpdir(), `pi-btw-${Date.now()}.md`);
		const payload = formatTranscriptForEditor(this.thread, this.editor.getText());

		try {
			fs.writeFileSync(tmpFile, payload, "utf8");
			this.tui.stop();
			const [editor, ...editorArgs] = editorCmd.split(" ");
			process.stdout.write(`Launching external editor: ${editorCmd}\nPi will resume when the editor exits.\n`);

			const status = await new Promise<number | null>((resolve) => {
				const child = spawn(editor, [...editorArgs, tmpFile], {
					stdio: "inherit",
					shell: process.platform === "win32",
				});
				child.on("error", () => resolve(null));
				child.on("close", (code) => resolve(code));
			});

			if (status === 0) {
				const edited = fs.readFileSync(tmpFile, "utf8");
				const draft = parseDraftFromEditorBuffer(edited);
				this.editor.setText(draft);
				this.thread.draft = draft;
			}
		} finally {
			try {
				fs.unlinkSync(tmpFile);
			} catch {}
			this.tui.start();
			this.tui.requestRender(true);
		}
	}
}

function renderThreadLines(
	thread: SideThread,
	width: number,
	fg: (color: string, text: string) => string,
): string[] {
	const lines: string[] = [];
	for (const message of thread.messages) {
		if (message.role !== "user" && message.role !== "assistant") continue;
		const label = message.role === "user" ? fg("accent", "you") : fg("success", "btw");
		const text = extractText(message).trim() || fg("dim", "(no text)");
		for (const [index, line] of wrapTextWithAnsi(text, Math.max(1, width - 6)).entries()) {
			lines.push(index === 0 ? `${label}: ${line}` : `     ${line}`);
		}
		lines.push("");
	}

	if (lines.length === 0) {
		return [fg("dim", "No side-thread messages yet. Ask something below.")];
	}

	if (lines[lines.length - 1] === "") lines.pop();
	if (lines.length <= MAX_RENDERED_MESSAGE_LINES) return lines;

	return [fg("dim", `… ${lines.length - MAX_RENDERED_MESSAGE_LINES} earlier line(s) hidden …`), "", ...lines.slice(-MAX_RENDERED_MESSAGE_LINES)];
}

function extractText(message: Message): string {
	if (message.role === "user") {
		if (typeof message.content === "string") return message.content;
		return message.content
			.filter((c): c is { type: "text"; text: string } => c.type === "text")
			.map((c) => c.text)
			.join("\n");
	}

	if (message.role === "assistant") {
		return message.content
			.filter((c): c is { type: "text"; text: string } => c.type === "text")
			.map((c) => c.text)
			.join("\n");
	}

	return message.content
		.filter((c): c is { type: "text"; text: string } => c.type === "text")
		.map((c) => c.text)
		.join("\n");
}

function formatTranscriptForEditor(thread: SideThread, draft: string): string {
	const parts = [
		"# /btw transcript",
		"",
		"Copy whatever you want from the conversation above.",
		"Only edit the draft below the marker if you want to change your next reply.",
		"",
		"## Conversation",
		"",
		...thread.messages.flatMap((message) => {
			if (message.role !== "user" && message.role !== "assistant") return [];
			const who = message.role === "user" ? "You" : "BTW";
			return [`### ${who}`, "", extractText(message).trim() || "(no text)", ""];
		}),
		TRANSCRIPT_MARKER,
		draft,
	];
	return parts.join("\n");
}

function parseDraftFromEditorBuffer(content: string): string {
	const index = content.indexOf(TRANSCRIPT_MARKER);
	if (index === -1) return content.replace(/\n$/, "");
	return content.slice(index + TRANSCRIPT_MARKER.length).replace(/^\r?\n/, "").replace(/\n$/, "");
}

function shorten(text: string, maxChars: number): string {
	const normalized = text.replace(/\s+/g, " ").trim();
	return normalized.length <= maxChars ? normalized : `${normalized.slice(0, maxChars - 1)}…`;
}

function formatError(error: unknown): string {
	if (error instanceof Error) return error.message;
	return String(error);
}
