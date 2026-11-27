/**
 * Subagent load balancer (`before_subagent_spawn`).
 *
 * A pool is one model served by several providers. A spawn whose first pattern
 * belongs to a pool starts on the pool's next member that offers the requested
 * effort, rotating across spawns. When auto-retry abandons a model, its quota
 * bucket (provider plus model family) cools down, longer for a usage-limit
 * failure, so pool members rotate past a spent quota instead of paying a failed
 * request per spawn. Until `DRAIN_UNTIL`, a fresh `DRAIN_PROVIDER` member wins
 * every spawn so its plan is used up before cancellation; after it, that
 * provider leaves every pool.
 */
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import type { Api, Model } from "@oh-my-pi/pi-ai";

const POOLS: readonly (readonly string[])[] = [
	["anthropic/claude-opus-5-5", "antigravity-cli/claude-opus-5-5"],
	["anthropic/claude-sonnet-5-5", "antigravity-cli/claude-sonnet-5-5"],
	["zai/glm-5.3:max", "opencode-go/glm-5.3"],
	["zai/glm-5.3-flash:max", "opencode-go/glm-5.3-flash"],
];

const COOLDOWN_MS = 10 * 60_000;
const QUOTA_COOLDOWN_MS = 60 * 60_000;
const QUOTA_REASON = /usage.?limit|quota|rate.?limit|429/i;
const DRAIN_PROVIDER = "opencode-go/";
const DRAIN_UNTIL = Date.parse("2026-12-08T00:00:00");
const SUFFIXES = ["off", "auto", "minimal", "low", "medium", "high", "xhigh", "max"] as const;
const LEVELS = ["minimal", "low", "medium", "high", "xhigh", "max"] as const;
type Level = (typeof LEVELS)[number];
type Suffix = (typeof SUFFIXES)[number];

interface Selector {
	base: string;
	level?: Suffix;
}

const cursors = new Map<string, number>();
const cooledUntil = new Map<string, number>();

function isSuffix(value: unknown): value is Suffix {
	return (SUFFIXES as readonly unknown[]).includes(value);
}

function isLevel(value: unknown): value is Level {
	return (LEVELS as readonly unknown[]).includes(value);
}

function parse(pattern: string): Selector {
	const index = pattern.lastIndexOf(":");
	const level = index < 0 ? undefined : pattern.slice(index + 1);
	return isSuffix(level) ? { base: pattern.slice(0, index), level } : { base: pattern };
}

function format(selector: Selector): string {
	return selector.level ? `${selector.base}:${selector.level}` : selector.base;
}

function bucket(base: string): string {
	const slash = base.indexOf("/");
	if (slash < 0) return base;
	return `${base.slice(0, slash)}/${base.slice(slash + 1).split("-")[0]}`;
}

function serves(level: Suffix | undefined, model: Model<Api> | undefined): boolean {
	if (level === undefined || level === "off" || level === "auto") return true;
	const efforts = model?.thinking?.efforts?.filter(isLevel) ?? [];
	return efforts.length === 0 || efforts.includes(level);
}

export default function modelBalancer(pi: ExtensionAPI) {
	pi.on("retry_fallback_applied", event => {
		const span = QUOTA_REASON.test(event.reason ?? "") ? QUOTA_COOLDOWN_MS : COOLDOWN_MS;
		cooledUntil.set(bucket(parse(event.from).base), Date.now() + span);
	});

	pi.on("before_subagent_spawn", async (event, ctx) => {
		const [primary, ...rest] = event.patterns;
		if (!primary) return undefined;
		const source = parse(primary);
		const pool = POOLS.find(members => members.some(member => parse(member).base === source.base));
		if (!pool) return undefined;

		const now = Date.now();
		const members = pool
			.map(member => parse(member))
			.filter(selector => now < DRAIN_UNTIL || !selector.base.startsWith(DRAIN_PROVIDER))
			.filter(selector => ctx.models.resolve(selector.base) !== undefined);
		const starts = members.filter(
			selector => selector.level !== undefined || serves(source.level, ctx.models.resolve(selector.base)),
		);
		if (starts.length < 2) return undefined;
		const fresh = starts.filter(selector => now >= (cooledUntil.get(bucket(selector.base)) ?? 0));
		const choices = fresh.length > 0 ? fresh : starts;

		const drain = now < DRAIN_UNTIL ? fresh.find(selector => selector.base.startsWith(DRAIN_PROVIDER)) : undefined;
		const index = (cursors.get(source.base) ?? 0) % choices.length;
		cursors.set(source.base, index + 1);
		const picked = drain ?? choices[index];
		const routed = (selector: Selector): Selector =>
			selector.level ? selector : { base: selector.base, level: source.level };
		const siblings = members.filter(selector => selector !== picked).map(selector => format(routed(selector)));

		return {
			model: [format(routed(picked)), ...siblings, ...rest],
			note: `pool rotation: ${format(routed(picked))}`,
		};
	});
}
