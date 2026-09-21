import { afterEach, expect, test } from "bun:test";
import expensiveAgentCap from "../../omp/.omp/agent/extensions/expensive-agent-cap";

type Event = {
	toolName: string;
	toolCallId: string;
	input: unknown;
};
type Handler = (event: Event) => unknown | Promise<unknown>;

const handlers: Record<string, Handler[]> = { tool_call: [], tool_result: [] };
const registered = { on(event: string, handler: Handler) { handlers[event]?.push(handler); } };
expensiveAgentCap(registered);

let nextId = 0;
const calls = new Set<string>();

type BlockResult = { block?: boolean; reason?: string };
function isBlockResult(value: unknown): value is BlockResult {
	return typeof value === "object" && value !== null && ("block" in value || "reason" in value);
}

async function call(input: unknown): Promise<{ id: string; results: BlockResult[] }> {
	const id = `test-call-${nextId++}`;
	calls.add(id);
	const results: BlockResult[] = [];
	for (const handler of handlers.tool_call) {
		const result = await handler({ toolName: "task", toolCallId: id, input });
		if (isBlockResult(result)) results.push(result);
	}
	return { id, results };
}

async function finish(id: string, input: unknown): Promise<void> {
	for (const handler of handlers.tool_result) await handler({ toolName: "task", toolCallId: id, input });
	calls.delete(id);
}

function isBlocked(results: Array<{ block?: boolean }>): boolean {
	return results.some(result => result.block === true);
}

afterEach(async () => {
	for (const id of calls) await finish(id, { agent: "ui-designer", task: "cleanup" });
});

test("caps each expensive agent independently and leaves implementers uncapped", async () => {
	const designer = await call({ agent: "ui-designer", task: "design" });
	expect(isBlocked(designer.results)).toBe(false);
	const investigator = await call({ agent: "investigator", task: "investigate" });
	expect(isBlocked(investigator.results)).toBe(false);
	const secondDesigner = await call({ agent: "ui-designer", task: "design again" });
	expect(isBlocked(secondDesigner.results)).toBe(true);
	const implementers = await call({ tasks: [{ agent: "ui-implementer", task: "wire one" }, { agent: "ui-implementer", task: "wire two" }] });
	expect(isBlocked(implementers.results)).toBe(false);
	await finish(designer.id, { agent: "ui-designer", task: "design" });
	await finish(investigator.id, { agent: "investigator", task: "investigate" });
	await finish(implementers.id, { tasks: [{ agent: "ui-implementer", task: "wire one" }, { agent: "ui-implementer", task: "wire two" }] });
});

test("counts trimmed names and protects slots from foreign tool-call IDs", async () => {
	const live = await call({ agent: " ui-designer ", task: "design" });
	expect(isBlocked(live.results)).toBe(false);
	await finish("foreign-call-id", { agent: "scout", task: "unrelated" });
	const blocked = await call({ agent: "ui-designer", task: "design again" });
	expect(isBlocked(blocked.results)).toBe(true);
	await finish(live.id, { agent: "ui-designer", task: "design" });
});

test("expires stranded slots", async () => {
	const stranded = await call({ agent: "ui-designer", task: "design" });
	expect(isBlocked(stranded.results)).toBe(false);
	const blocked = await call({ agent: "ui-designer", task: "design again" });
	expect(isBlocked(blocked.results)).toBe(true);
	const originalNow = Date.now;
	Date.now = () => originalNow() + 46 * 60_000;
	try {
		const recovered = await call({ agent: "ui-designer", task: "design after expiry" });
		expect(isBlocked(recovered.results)).toBe(false);
		await finish(recovered.id, { agent: "ui-designer", task: "design after expiry" });
	} finally {
		Date.now = originalNow;
	}
});
