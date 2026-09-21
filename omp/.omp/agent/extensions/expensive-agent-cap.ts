import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

const MAX_CONCURRENT_BY_AGENT: Record<string, number> = {
	investigator: 1,
	"ui-designer": 1,
};
// A tool_call handler that blocks or throws after this one prevents the
// tool_result that would release the slot; stranded entries expire instead.
const STALE_MS = 45 * 60_000;

// Subagent sessions re-bind this factory without re-evaluating the module,
// so every session in the process shares this one in-flight count.
const pendingByToolCall = new Map<string, { counts: Record<string, number>; at: number }>();

function cappedSpawnCounts(input: unknown): Record<string, number> {
	if (typeof input !== "object" || input === null) return {};
	const record = input as Record<string, unknown>;
	const items = Array.isArray(record.tasks) ? record.tasks : [record];
	const counts: Record<string, number> = {};
	for (const item of items) {
		if (typeof item !== "object" || item === null) continue;
		const agent = (item as Record<string, unknown>).agent;
		if (typeof agent !== "string") continue;
		const trimmed = agent.trim();
		if (trimmed in MAX_CONCURRENT_BY_AGENT) counts[trimmed] = (counts[trimmed] ?? 0) + 1;
	}
	return counts;
}

function inFlightCounts(now: number): Record<string, number> {
	const totals: Record<string, number> = {};
	for (const [toolCallId, entry] of pendingByToolCall) {
		if (now - entry.at > STALE_MS) {
			pendingByToolCall.delete(toolCallId);
			continue;
		}
		for (const [agent, count] of Object.entries(entry.counts)) {
			totals[agent] = (totals[agent] ?? 0) + count;
		}
	}
	return totals;
}

function firstOverCap(requested: Record<string, number>, inFlight: Record<string, number>): string | undefined {
	for (const agent of Object.keys(requested)) {
		if ((inFlight[agent] ?? 0) + requested[agent] > MAX_CONCURRENT_BY_AGENT[agent]) return agent;
	}
	return undefined;
}

export default function expensiveAgentCap(pi: ExtensionAPI): void {
	pi.on("tool_call", async event => {
		if (event.toolName !== "task") return;
		const requested = cappedSpawnCounts(event.input);
		if (Object.keys(requested).length === 0) return;
		const inFlight = inFlightCounts(Date.now());
		const overCap = firstOverCap(requested, inFlight);
		if (overCap !== undefined) {
			return {
				block: true,
				reason: `${overCap} runs an expensive model and is capped at ${MAX_CONCURRENT_BY_AGENT[overCap]} concurrent spawn${MAX_CONCURRENT_BY_AGENT[overCap] === 1 ? "" : "s"}; ${inFlight[overCap] ?? 0} already in flight. Spawn one, wait for its report, then continue.`,
			};
		}
		pendingByToolCall.set(event.toolCallId, { counts: requested, at: Date.now() });
	});

	pi.on("tool_result", async event => {
		if (event.toolName !== "task") return;
		// A toolCallId can repeat across sessions; only the owning call's result
		// input may release its slots.
		if (Object.keys(cappedSpawnCounts(event.input)).length > 0) {
			pendingByToolCall.delete(event.toolCallId);
		}
	});
}
