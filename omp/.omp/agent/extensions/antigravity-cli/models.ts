import type { ProviderModelConfig } from "@oh-my-pi/pi-coding-agent";

const EFFORT_LEVELS = ["minimal", "low", "medium", "high", "xhigh", "max"] as const;
type Effort = (typeof EFFORT_LEVELS)[number];

export const AGY_PROVIDER_ID = "antigravity-cli";
export const AGY_API_ID = "antigravity-cli";

const ZERO_COST = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };
const FLASH_EFFORTS: Effort[] = ["minimal", "low", "medium", "high"];
const PRO_EFFORTS: Effort[] = ["low", "high"];

type WireModelIds = {
	low: string;
	medium?: string;
	high: string;
};

function createModel(id: string, name: string, efforts: Effort[], wire: WireModelIds): ProviderModelConfig {
	const effortRouting: Partial<Record<Effort | "off", string>> = {
		minimal: wire.low,
		low: wire.low,
		medium: wire.medium ?? wire.high,
		high: wire.high,
		xhigh: wire.high,
		max: wire.high,
		off: wire.low,
	};

	return {
		id,
		name,
		api: AGY_API_ID,
		reasoning: true,
		thinking: {
			mode: "effort",
			efforts,
			defaultLevel: "high",
			effortRouting,
		},
		input: ["text"],
		cost: { ...ZERO_COST },
		contextWindow: 1_048_576,
		maxTokens: 65_536,
	};
}

export const AGY_MODELS: ProviderModelConfig[] = [
	createModel("gemini-3.8-flash", "Gemini 3.8 Flash (AGY CLI)", FLASH_EFFORTS, {
		low: "gemini-3.8-flash-low",
		medium: "gemini-3.8-flash-medium",
		high: "gemini-3.8-flash-high",
	}),
	createModel("gemini-3.7-flash", "Gemini 3.7 Flash (AGY CLI)", FLASH_EFFORTS, {
		low: "gemini-3.7-flash-low",
		medium: "gemini-3.7-flash-medium",
		high: "gemini-3.7-flash-high",
	}),
	createModel("gemini-3.6-flash", "Gemini 3.6 Flash (AGY CLI)", FLASH_EFFORTS, {
		low: "gemini-3.6-flash-low",
		medium: "gemini-3.6-flash-medium",
		high: "gemini-3.6-flash-high",
	}),
	createModel("gemini-3.1-pro", "Gemini 3.1 Pro (AGY CLI)", PRO_EFFORTS, {
		low: "gemini-3.1-pro-low",
		high: "gemini-3.1-pro-high",
	}),
];

export function resolveAgyModelId(
	modelId: string,
	reasoning: Effort | undefined,
	disableReasoning = false,
): string {
	const model = AGY_MODELS.find(candidate => candidate.id === modelId);
	if (!model?.thinking?.effortRouting) {
		throw new Error(`AGY CLI provider does not support model "${modelId}".`);
	}

	let effort: Effort | "off" = "high";
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
