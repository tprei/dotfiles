import { appendFile, mkdir, open, readFile, readdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";

import type { AssistantMessage } from "@earendil-works/pi-ai";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";

const CODEX_POLL_MS = 30_000;
const CODEX_TAIL_BYTES = 128 * 1024;
const CODEX_HISTORY_MAX_AGE_MS = 14 * 24 * 60 * 60 * 1000;
const CODEX_PRIMARY_LOOKBACK_MS = 90 * 60 * 1000;
const CODEX_SECONDARY_LOOKBACK_MS = 48 * 60 * 60 * 1000;
const CODEX_PRIMARY_MIN_SPAN_MS = 10 * 60 * 1000;
const CODEX_SECONDARY_MIN_SPAN_MS = 6 * 60 * 60 * 1000;
const CODEX_MIN_DELTA_PERCENT = 0.5;

type CodexLimitWindow = {
	used_percent?: number | null;
	window_minutes?: number | null;
	resets_at?: number | null;
};

type CodexRateLimits = {
	timestamp?: string;
	file?: string;
	primary?: CodexLimitWindow | null;
	secondary?: CodexLimitWindow | null;
	plan_type?: string | null;
	rate_limit_reached_type?: string | null;
};

type CodexHistorySample = {
	timestampMs: number;
	primaryUsed?: number | null;
	primaryReset?: number | null;
	secondaryUsed?: number | null;
	secondaryReset?: number | null;
};

type CodexForecast = { type: "eta"; etaMs: number } | { type: "safe" };

type CodexWindowForecast = {
	available: boolean;
	safe?: boolean;
	etaMs?: number;
};

function formatPath(cwd: string): string {
	const home = process.env.HOME;
	return home && cwd.startsWith(home) ? `~${cwd.slice(home.length)}` : cwd;
}

function formatTokens(value: number): string {
	if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}m`;
	if (value >= 10_000) return `${Math.round(value / 1_000)}k`;
	if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
	return `${Math.round(value)}`;
}

function formatCost(value: number): string {
	if (value >= 10) return value.toFixed(1);
	if (value >= 1) return value.toFixed(2);
	return value.toFixed(3);
}

function joinSegments(theme: any, segments: Array<string | undefined>): string {
	const sep = theme.fg("dim", " • ");
	return segments.filter((segment): segment is string => Boolean(segment)).join(sep);
}

function fitLine(left: string, right: string, width: number): string {
	if (width <= 0) return "";
	if (!left) return truncateToWidth(right, width, "");
	if (!right) return truncateToWidth(left, width, "");

	let leftText = left;
	let rightText = right;

	while (visibleWidth(leftText) + visibleWidth(rightText) + 1 > width && visibleWidth(leftText) > visibleWidth(rightText)) {
		leftText = truncateToWidth(leftText, Math.max(0, visibleWidth(leftText) - 1), "");
	}
	while (visibleWidth(leftText) + visibleWidth(rightText) + 1 > width && visibleWidth(rightText) > 0) {
		rightText = truncateToWidth(rightText, Math.max(0, visibleWidth(rightText) - 1), "");
	}
	while (visibleWidth(leftText) + visibleWidth(rightText) + 1 > width && visibleWidth(leftText) > 0) {
		leftText = truncateToWidth(leftText, Math.max(0, visibleWidth(leftText) - 1), "");
	}

	const gapWidth = Math.max(1, width - visibleWidth(leftText) - visibleWidth(rightText));
	return truncateToWidth(`${leftText}${" ".repeat(gapWidth)}${rightText}`, width, "");
}

function thinkingColor(level: string): string {
	switch (level) {
		case "off":
			return "thinkingOff";
		case "minimal":
			return "thinkingMinimal";
		case "low":
			return "thinkingLow";
		case "medium":
			return "thinkingMedium";
		case "high":
			return "thinkingHigh";
		default:
			return "thinkingXhigh";
	}
}

function contextColor(percent: number | null | undefined): string {
	if (percent === null || percent === undefined) return "muted";
	if (percent >= 80) return "error";
	if (percent >= 60) return "warning";
	return "success";
}

function renderBar(theme: any, percent: number | null | undefined, width = 8): string {
	if (percent === null || percent === undefined) {
		return `${theme.fg("borderMuted", "░".repeat(width))}`;
	}

	const clamped = Math.max(0, Math.min(100, percent));
	const filled = Math.round((clamped / 100) * width);
	return `${theme.fg(contextColor(clamped), "█".repeat(filled))}${theme.fg("borderMuted", "░".repeat(width - filled))}`;
}

function getUsageTotals(ctx: ExtensionContext): { input: number; output: number; cost: number } {
	let input = 0;
	let output = 0;
	let cost = 0;

	for (const entry of ctx.sessionManager.getBranch()) {
		if (entry.type !== "message" || entry.message.role !== "assistant") continue;
		const message = entry.message as AssistantMessage;
		if (!message.usage) continue;
		input += message.usage.input;
		output += message.usage.output;
		cost += message.usage.cost.total;
	}

	return { input, output, cost };
}

function codexLimitColor(percent: number | null | undefined): string {
	if (percent === null || percent === undefined) return "muted";
	if (percent >= 80) return "error";
	if (percent >= 60) return "warning";
	return "success";
}

function forecastColor(etaMs: number): string {
	if (etaMs <= 60 * 60 * 1000) return "error";
	if (etaMs <= 4 * 60 * 60 * 1000) return "warning";
	return "success";
}

function formatDurationMs(diffMs: number): string | undefined {
	if (!Number.isFinite(diffMs) || diffMs <= 0) return undefined;
	if (diffMs < 60_000) return "<1m";

	const minutes = Math.ceil(diffMs / 60_000);
	if (minutes < 60) return `${minutes}m`;

	const hours = Math.ceil(minutes / 60);
	if (hours < 24) return `${hours}h`;

	return `${Math.ceil(hours / 24)}d`;
}

function formatResetIn(epochSeconds: number | null | undefined): string | undefined {
	if (epochSeconds === null || epochSeconds === undefined || !Number.isFinite(epochSeconds)) return undefined;
	return formatDurationMs(epochSeconds * 1000 - Date.now());
}

function formatCodexSegment(theme: any, limits: CodexRateLimits | null, forecast: CodexForecast | null): string | undefined {
	if (!limits) return undefined;

	const primaryReset = formatResetIn(limits.primary?.resets_at);
	const secondaryReset = formatResetIn(limits.secondary?.resets_at);
	const primaryPercent = primaryReset ? limits.primary?.used_percent : undefined;
	const secondaryPercent = secondaryReset ? limits.secondary?.used_percent : undefined;

	if (limits.rate_limit_reached_type) {
		const reset = limits.rate_limit_reached_type === "secondary" ? secondaryReset ?? primaryReset : primaryReset ?? secondaryReset;
		return `${theme.fg("dim", "codex ")}${theme.fg("error", "limit")}${reset ? theme.fg("dim", ` ${reset}`) : ""}`;
	}

	const usageParts: string[] = [];
	if (primaryPercent !== null && primaryPercent !== undefined) {
		usageParts.push(theme.fg(codexLimitColor(primaryPercent), `${Math.round(primaryPercent)}%`));
	}
	if (secondaryPercent !== null && secondaryPercent !== undefined) {
		usageParts.push(theme.fg(codexLimitColor(secondaryPercent), `${Math.round(secondaryPercent)}%`));
	}

	const resetParts = [primaryReset, secondaryReset].filter(Boolean) as string[];
	if (usageParts.length === 0 && resetParts.length === 0) return undefined;

	const usageText = usageParts.join(theme.fg("dim", "/"));
	const resetText = resetParts.length > 0 ? theme.fg("dim", ` ${resetParts.join("/")}`) : "";
	const forecastText =
		forecast?.type === "eta"
			? theme.fg(forecastColor(forecast.etaMs), ` ~${formatDurationMs(forecast.etaMs) ?? "<1m"}`)
			: forecast?.type === "safe"
				? theme.fg("success", " ~safe")
				: "";

	return `${theme.fg("dim", "codex ")}${usageText}${resetText}${forecastText}`;
}

async function findLatestJsonlFile(dir: string): Promise<{ path: string; mtimeMs: number } | null> {
	const entries = await readdir(dir, { withFileTypes: true });
	let latest: { path: string; mtimeMs: number } | null = null;

	for (const entry of entries) {
		const path = join(dir, entry.name);
		if (entry.isDirectory()) {
			const nested = await findLatestJsonlFile(path);
			if (nested && (!latest || nested.mtimeMs > latest.mtimeMs)) latest = nested;
			continue;
		}
		if (!entry.isFile() || !entry.name.endsWith(".jsonl")) continue;
		const info = await stat(path);
		if (!latest || info.mtimeMs > latest.mtimeMs) latest = { path, mtimeMs: info.mtimeMs };
	}

	return latest;
}

async function readTail(path: string, maxBytes: number): Promise<string> {
	const handle = await open(path, "r");
	try {
		const info = await handle.stat();
		const length = Math.min(maxBytes, info.size);
		const buffer = Buffer.alloc(length);
		await handle.read(buffer, 0, length, info.size - length);
		return buffer.toString("utf8");
	} finally {
		await handle.close();
	}
}

function parseCodexSnapshot(text: string, file: string): { latest: CodexRateLimits | null; samples: CodexHistorySample[] } {
	const lines = text.split("\n");
	const samples: CodexHistorySample[] = [];
	let latest: CodexRateLimits | null = null;

	for (const rawLine of lines) {
		const line = rawLine.trim();
		if (!line || !line.includes('"rate_limits"')) continue;
		try {
			const parsed = JSON.parse(line);
			const rateLimits = parsed?.payload?.rate_limits;
			if (!rateLimits) continue;

			latest = {
				timestamp: parsed?.timestamp,
				file,
				primary: rateLimits.primary ?? null,
				secondary: rateLimits.secondary ?? null,
				plan_type: rateLimits.plan_type ?? null,
				rate_limit_reached_type: rateLimits.rate_limit_reached_type ?? null,
			};

			const timestampMs = Date.parse(String(parsed?.timestamp ?? ""));
			if (!Number.isFinite(timestampMs)) continue;

			samples.push({
				timestampMs,
				primaryUsed: rateLimits.primary?.used_percent ?? null,
				primaryReset: rateLimits.primary?.resets_at ?? null,
				secondaryUsed: rateLimits.secondary?.used_percent ?? null,
				secondaryReset: rateLimits.secondary?.resets_at ?? null,
			});
		} catch {
			continue;
		}
	}

	return { latest, samples };
}

function mergeCodexHistory(history: CodexHistorySample[], seen: Set<number>, samples: CodexHistorySample[]): CodexHistorySample[] {
	const cutoff = Date.now() - CODEX_HISTORY_MAX_AGE_MS;
	const newSamples: CodexHistorySample[] = [];

	for (const sample of samples) {
		if (!Number.isFinite(sample.timestampMs) || sample.timestampMs < cutoff) continue;
		if (seen.has(sample.timestampMs)) continue;
		seen.add(sample.timestampMs);
		history.push(sample);
		newSamples.push(sample);
	}

	if (newSamples.length > 0) {
		history.sort((a, b) => a.timestampMs - b.timestampMs);
	}

	return newSamples;
}

function pruneCodexHistory(history: CodexHistorySample[], seen: Set<number>): void {
	const cutoff = Date.now() - CODEX_HISTORY_MAX_AGE_MS;
	const kept = history.filter((sample) => sample.timestampMs >= cutoff);
	if (kept.length === history.length) return;

	history.length = 0;
	history.push(...kept);
	seen.clear();
	for (const sample of kept) seen.add(sample.timestampMs);
}

function buildWindowForecast(
	history: CodexHistorySample[],
	currentReset: number | null | undefined,
	getUsed: (sample: CodexHistorySample) => number | null | undefined,
	getReset: (sample: CodexHistorySample) => number | null | undefined,
	lookbackMs: number,
	minSpanMs: number,
): CodexWindowForecast {
	if (currentReset === null || currentReset === undefined || !Number.isFinite(currentReset)) return { available: false };

	const relevant = history.filter((sample) => getReset(sample) === currentReset && getUsed(sample) !== null && getUsed(sample) !== undefined);
	if (relevant.length < 2) return { available: false };

	const latest = relevant[relevant.length - 1]!;
	const recentCutoff = latest.timestampMs - lookbackMs;
	const recent = relevant.filter((sample) => sample.timestampMs >= recentCutoff);
	const series = recent.length >= 2 ? recent : relevant;
	const first = series[0]!;
	const last = series[series.length - 1]!;
	const firstUsed = getUsed(first)!;
	const lastUsed = getUsed(last)!;
	const spanMs = last.timestampMs - first.timestampMs;
	const deltaUsed = lastUsed - firstUsed;

	if (!Number.isFinite(firstUsed) || !Number.isFinite(lastUsed) || spanMs < minSpanMs || deltaUsed < CODEX_MIN_DELTA_PERCENT) {
		return { available: false };
	}

	if (lastUsed >= 100) return { available: true, etaMs: 0 };

	const ratePerMs = deltaUsed / spanMs;
	if (!Number.isFinite(ratePerMs) || ratePerMs <= 0) return { available: false };

	const etaMs = ((100 - lastUsed) / ratePerMs);
	if (!Number.isFinite(etaMs) || etaMs < 0) return { available: false };

	const exhaustAtMs = last.timestampMs + etaMs;
	const resetAtMs = currentReset * 1000;
	if (exhaustAtMs >= resetAtMs) return { available: true, safe: true };

	return { available: true, etaMs: Math.max(0, exhaustAtMs - Date.now()) };
}

function computeCodexForecast(history: CodexHistorySample[], limits: CodexRateLimits | null): CodexForecast | null {
	if (!limits) return null;

	const primary = buildWindowForecast(
		history,
		limits.primary?.resets_at,
		(sample) => sample.primaryUsed,
		(sample) => sample.primaryReset,
		CODEX_PRIMARY_LOOKBACK_MS,
		CODEX_PRIMARY_MIN_SPAN_MS,
	);
	const secondary = buildWindowForecast(
		history,
		limits.secondary?.resets_at,
		(sample) => sample.secondaryUsed,
		(sample) => sample.secondaryReset,
		CODEX_SECONDARY_LOOKBACK_MS,
		CODEX_SECONDARY_MIN_SPAN_MS,
	);

	const etas = [primary.etaMs, secondary.etaMs].filter((value): value is number => value !== null && value !== undefined);
	if (etas.length > 0) {
		return { type: "eta", etaMs: Math.min(...etas) };
	}

	if (primary.available && secondary.available && primary.safe && secondary.safe) {
		return { type: "safe" };
	}

	return null;
}

export default function (pi: ExtensionAPI) {
	let requestRender: (() => void) | undefined;
	let codexLimits: CodexRateLimits | null = null;
	let codexForecast: CodexForecast | null = null;
	let codexPollTimer: ReturnType<typeof setInterval> | undefined;
	let codexCacheKey: string | undefined;
	let codexHistory: CodexHistorySample[] = [];
	let codexHistorySeen = new Set<number>();
	let codexHistoryPath: string | undefined;
	let codexHistoryLoaded = false;

	async function ensureCodexHistoryLoaded(home: string): Promise<void> {
		if (codexHistoryLoaded) return;
		codexHistoryPath = join(home, ".pi/agent/codex-rate-history.jsonl");
		codexHistoryLoaded = true;

		try {
			const text = await readFile(codexHistoryPath, "utf8");
			const samples: CodexHistorySample[] = [];
			for (const rawLine of text.split("\n")) {
				const line = rawLine.trim();
				if (!line) continue;
				try {
					const parsed = JSON.parse(line);
					if (!Number.isFinite(parsed?.timestampMs)) continue;
					samples.push({
						timestampMs: parsed.timestampMs,
						primaryUsed: parsed.primaryUsed ?? null,
						primaryReset: parsed.primaryReset ?? null,
						secondaryUsed: parsed.secondaryUsed ?? null,
						secondaryReset: parsed.secondaryReset ?? null,
					});
				} catch {
					continue;
				}
			}
			mergeCodexHistory(codexHistory, codexHistorySeen, samples);
			pruneCodexHistory(codexHistory, codexHistorySeen);
		} catch {
			// no persisted history yet
		}
	}

	async function persistCodexHistory(samples: CodexHistorySample[]): Promise<void> {
		if (!codexHistoryPath || samples.length === 0) return;
		try {
			await mkdir(dirname(codexHistoryPath), { recursive: true });
			const payload = samples
				.map((sample) => JSON.stringify(sample))
				.join("\n");
			await appendFile(codexHistoryPath, `${payload}\n`, "utf8");
		} catch {
			// ignore persistence issues
		}
	}

	async function refreshCodexLimits(): Promise<void> {
		const home = process.env.HOME;
		if (!home) return;

		await ensureCodexHistoryLoaded(home);
		pruneCodexHistory(codexHistory, codexHistorySeen);

		try {
			const latest = await findLatestJsonlFile(join(home, ".codex/sessions"));
			if (!latest) {
				if (codexLimits !== null || codexForecast !== null) {
					codexLimits = null;
					codexForecast = null;
					requestRender?.();
				}
				return;
			}

			const cacheKey = `${latest.path}:${latest.mtimeMs}`;
			const tail = await readTail(latest.path, CODEX_TAIL_BYTES);
			const snapshot = parseCodexSnapshot(tail, latest.path);
			const newSamples = mergeCodexHistory(codexHistory, codexHistorySeen, snapshot.samples);
			if (newSamples.length > 0) {
				await persistCodexHistory(newSamples);
			}

			if (cacheKey !== codexCacheKey) {
				codexCacheKey = cacheKey;
				codexLimits = snapshot.latest;
			}

			codexForecast = computeCodexForecast(codexHistory, codexLimits);
			requestRender?.();
		} catch {
			// ignore missing/locked Codex state
		}
	}

	pi.on("session_start", (_event, ctx) => {
		if (!ctx.hasUI) return;

		if (codexPollTimer) clearInterval(codexPollTimer);
		void refreshCodexLimits();
		codexPollTimer = setInterval(() => {
			void refreshCodexLimits();
		}, CODEX_POLL_MS);

		ctx.ui.setFooter((tui, theme, footerData) => {
			const rerender = () => tui.requestRender();
			requestRender = rerender;
			const stopWatchingBranch = footerData.onBranchChange(rerender);

			return {
				dispose() {
					stopWatchingBranch();
					if (requestRender === rerender) requestRender = undefined;
				},
				invalidate() {},
				render(width: number): string[] {
					const branch = footerData.getGitBranch();
					const statuses = Array.from(footerData.getExtensionStatuses().values()).filter(Boolean);
					const thinkingLevel = pi.getThinkingLevel();
					const contextUsage = ctx.getContextUsage();
					const totals = getUsageTotals(ctx);
					const contextWindow = contextUsage?.contextWindow ?? ctx.model?.contextWindow;
					const contextPercent = contextUsage?.percent;
					const contextTokens = contextUsage?.tokens;
					const codexSegment = formatCodexSegment(theme, codexLimits, codexForecast);

					const leftBase = [
						theme.fg("muted", formatPath(ctx.cwd)),
						branch ? `${theme.fg("dim", "git ")}${theme.fg("accent", branch)}` : undefined,
					];
					const leftOptional = [...statuses];

					const modelSegment = ctx.model
						? `${theme.fg("dim", `${ctx.model.provider}/`)}${theme.fg("accent", ctx.model.id)}`
						: theme.fg("warning", "no model");
					const thinkingSegment = `${theme.fg("dim", "think ")}${theme.fg(thinkingColor(thinkingLevel), thinkingLevel)}`;
					const contextSegment = `${theme.fg("dim", "ctx ")}${renderBar(theme, contextPercent)} ${theme.fg(
						contextColor(contextPercent),
						contextPercent === null || contextPercent === undefined ? "?" : `${Math.round(contextPercent)}%`,
					)}${theme.fg(
						"dim",
						` ${contextTokens !== undefined ? formatTokens(contextTokens) : "?"}/${contextWindow ? formatTokens(contextWindow) : "?"}`,
					)}`;
					const ioSegment =
						totals.input > 0 || totals.output > 0
							? `${theme.fg("dim", "io ")}${theme.fg("muted", formatTokens(totals.input))}${theme.fg("dim", "/")}${theme.fg("text", formatTokens(totals.output))}`
							: undefined;
					const costSegment = totals.cost > 0 ? theme.fg("dim", `$${formatCost(totals.cost)}`) : undefined;

					const rightBase = [modelSegment, thinkingSegment, contextSegment];
					const rightOptional = [codexSegment, ioSegment, costSegment].filter(Boolean) as string[];

					let left = joinSegments(theme, [...leftBase, ...leftOptional]);
					let right = joinSegments(theme, [...rightBase, ...rightOptional]);
					const optionalRight = [...rightOptional];
					const optionalLeft = [...leftOptional];

					while (visibleWidth(left) + visibleWidth(right) + 1 > width && optionalRight.length > 0) {
						optionalRight.pop();
						right = joinSegments(theme, [...rightBase, ...optionalRight]);
					}
					while (visibleWidth(left) + visibleWidth(right) + 1 > width && optionalLeft.length > 0) {
						optionalLeft.pop();
						left = joinSegments(theme, [...leftBase, ...optionalLeft]);
					}

					return [fitLine(left, right, width)];
				},
			};
		});
	});

	for (const eventName of ["model_select", "thinking_level_select", "turn_end", "session_tree", "session_compact"] as const) {
		pi.on(eventName, () => requestRender?.());
	}

	pi.on("session_shutdown", () => {
		requestRender = undefined;
		codexCacheKey = undefined;
		codexLimits = null;
		codexForecast = null;
		codexHistory = [];
		codexHistorySeen = new Set<number>();
		codexHistoryPath = undefined;
		codexHistoryLoaded = false;
		if (codexPollTimer) {
			clearInterval(codexPollTimer);
			codexPollTimer = undefined;
		}
	});
}
