import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

const AGENT_NAME = "investigator";
const MAX_CONCURRENT = 1;
// A tool_call handler that blocks or throws after this one prevents the
// tool_result that would release the slot; stranded entries expire instead.
const STALE_MS = 45 * 60_000;

// Subagent sessions re-bind this factory without re-evaluating the module,
// so every session in the process shares this one in-flight count.
const pendingByToolCall = new Map<string, { count: number; at: number }>();

function isInvestigator(agent: unknown): boolean {
	return typeof agent === "string" && agent.trim() === AGENT_NAME;
}

function countInvestigatorSpawns(input: unknown): number {
	if (typeof input !== "object" || input === null) return 0;
	const record = input as Record<string, unknown>;
	if (Array.isArray(record.tasks)) {
		return record.tasks.filter(item => typeof item === "object" && item !== null && isInvestigator((item as Record<string, unknown>).agent))
			.length;
	}
	return isInvestigator(record.agent) ? 1 : 0;
}

function inFlightCount(now: number): number {
	let total = 0;
	for (const [toolCallId, entry] of pendingByToolCall) {
		if (now - entry.at > STALE_MS) {
			pendingByToolCall.delete(toolCallId);
			continue;
		}
		total += entry.count;
	}
	return total;
}

export default function investigatorCap(pi: ExtensionAPI): void {
	pi.on("tool_call", async event => {
		if (event.toolName !== "task") return;
		const count = countInvestigatorSpawns(event.input);
		if (count === 0) return;
		const inFlight = inFlightCount(Date.now());
		if (inFlight + count > MAX_CONCURRENT) {
			return {
				block: true,
				reason: `investigator runs an expensive model and is capped at ${MAX_CONCURRENT} concurrent spawn${MAX_CONCURRENT === 1 ? "" : "s"}; ${inFlight} already in flight. Spawn one, wait for its report, then continue.`,
			};
		}
		pendingByToolCall.set(event.toolCallId, { count, at: Date.now() });
	});

	pi.on("tool_result", async event => {
		if (event.toolName !== "task") return;
		// A toolCallId can repeat across sessions; only the owning call's result
		// input may release its slot.
		if (countInvestigatorSpawns(event.input) > 0) {
			pendingByToolCall.delete(event.toolCallId);
		}
	});
}
