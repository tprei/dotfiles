import type { ProviderModelConfig } from "@oh-my-pi/pi-coding-agent";

const EFFORTS = ["minimal", "low", "medium", "high", "xhigh", "max"] as const;
type AgyEffort = (typeof EFFORTS)[number];
type AgyReasoning = AgyEffort | "off";

export const AGY_PROVIDER_ID = "antigravity-cli";
export const AGY_API_ID = "antigravity-cli";

const ZERO_COST = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };
const GEN4_EFFORTS: AgyEffort[] = ["low", "medium", "high", "xhigh"];

type WireModelIds = {
	low: string;
	medium?: string;
	high: string;
	xhigh: string;
};

function createModel(id: string, name: string, efforts: AgyEffort[], wire: WireModelIds): ProviderModelConfig {
	const effortRouting: Partial<Record<AgyReasoning, string>> = {
		minimal: wire.low,
		low: wire.low,
		medium: wire.medium ?? wire.high,
		high: wire.high,
		xhigh: wire.xhigh,
		max: wire.high,
		off: wire.low,
	};

	return {
		id,
		name,
		api: AGY_API_ID,
		reasoning: true,
		supportsTools: true,
		thinking: {
			mode: "effort",
			efforts,
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
	createModel("gemini-4-hydrogen", "Gemini 4 Hydrogen (AGY CLI)", GEN4_EFFORTS, {
		low: "gemini-4-hydrogen-low",
		medium: "gemini-4-hydrogen-medium",
		high: "gemini-4-hydrogen-high",
		xhigh: "gemini-4-hydrogen-xhigh",
	}),
	createModel("gemini-4-neon", "Gemini 4 Neon (AGY CLI)", GEN4_EFFORTS, {
		low: "gemini-4-neon-low",
		medium: "gemini-4-neon-medium",
		high: "gemini-4-neon-high",
		xhigh: "gemini-4-neon-xhigh",
	}),
];

export function resolveAgyModelId(
	modelId: string,
	reasoning: AgyEffort | undefined,
	disableReasoning = false,
): string {
	const model = AGY_MODELS.find(candidate => candidate.id === modelId);
	if (!model?.thinking?.effortRouting) {
		throw new Error(`AGY CLI provider does not support model "${modelId}".`);
	}

	let effort: AgyReasoning = "high";
	if (disableReasoning) {
		effort = "off";
	} else if (reasoning === "minimal" || reasoning === "low") {
		effort = "low";
	} else if (reasoning === "medium") {
		effort = "medium";
	}
	const wireModelId = model.thinking.effortRouting[effort];
	if (!wireModelId) {
		throw new Error(`AGY CLI provider has no wire model for "${modelId}" at ${effort} effort.`);
	}
	return wireModelId;
}
