import type { ProviderModelConfig } from "@oh-my-pi/pi-coding-agent";

const EFFORTS = ["low", "medium", "high", "xhigh"] as const;
type AgyEffort = (typeof EFFORTS)[number];
type AgyReasoning = AgyEffort | "off" | "minimal" | "max";

export const AGY_PROVIDER_ID = "antigravity-cli";
export const AGY_API_ID = "antigravity-cli";

const ZERO_COST = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };

const WIRE_IDS: Record<string, Partial<Record<AgyEffort, string>>> = {
	"gemini-4-hydrogen": {
		low: "gemini-4-hydrogen-low",
		medium: "gemini-4-hydrogen-medium",
		high: "gemini-4-hydrogen-high",
		xhigh: "gemini-4-hydrogen-xhigh",
	},
	"gemini-4-neon": {
		low: "gemini-4-neon-low",
		medium: "gemini-4-neon-medium",
		high: "gemini-4-neon-high",
		xhigh: "gemini-4-neon-xhigh",
	},
	"claude-opus-5-5": {
		low: "claude-opus-5-5-low",
		medium: "claude-opus-5-5-medium",
		high: "claude-opus-5-5-high",
	},
	"claude-sonnet-5-5": {
		low: "claude-sonnet-5-5-low",
		medium: "claude-sonnet-5-5-medium",
		high: "claude-sonnet-5-5-high",
	},
};

function createModel(id: string, name: string, wire: Partial<Record<AgyEffort, string>>): ProviderModelConfig {
	const effortRouting: Partial<Record<AgyReasoning, string>> = {
		off: wire.low,
		minimal: wire.low,
		low: wire.low,
		medium: wire.medium ?? wire.high,
		high: wire.high,
		xhigh: wire.xhigh ?? wire.high,
		max: wire.xhigh ?? wire.high,
	};

	return {
		id,
		name,
		api: AGY_API_ID,
		reasoning: true,
		supportsTools: true,
		thinking: {
			mode: "effort",
			efforts: EFFORTS.filter(effort => wire[effort] !== undefined),
			defaultLevel: "high",
			effortRouting,
		} as unknown as NonNullable<ProviderModelConfig["thinking"]>,
		input: ["text"],
		cost: { ...ZERO_COST },
		contextWindow: 1_048_576,
		maxTokens: 65_536,
	};
}

export const AGY_MODELS: ProviderModelConfig[] = [
	createModel("gemini-4-hydrogen", "Gemini 4 Hydrogen (AGY CLI)", WIRE_IDS["gemini-4-hydrogen"]),
	createModel("gemini-4-neon", "Gemini 4 Neon (AGY CLI)", WIRE_IDS["gemini-4-neon"]),
	createModel("claude-opus-5-5", "Claude Opus 5.5 (AGY CLI)", WIRE_IDS["claude-opus-5-5"]),
	createModel("claude-sonnet-5-5", "Claude Sonnet 5.5 (AGY CLI)", WIRE_IDS["claude-sonnet-5-5"]),
];

export function resolveAgyModelId(
	modelId: string,
	reasoning: AgyReasoning | undefined,
	disableReasoning = false,
): string {
	const model = AGY_MODELS.find(candidate => candidate.id === modelId);
	if (!model?.thinking?.effortRouting) {
		throw new Error(`AGY CLI provider does not support model "${modelId}".`);
	}

	let effort: AgyReasoning = "high";
	if (disableReasoning) effort = "off";
	else if (reasoning === "minimal") effort = "low";
	else if (reasoning !== undefined) effort = reasoning;
	const wireModelId = model.thinking.effortRouting[effort];
	if (!wireModelId) {
		throw new Error(`AGY CLI provider has no wire model for "${modelId}" at ${effort} effort.`);
	}
	return wireModelId;
}
