import { Effort } from "@oh-my-pi/pi-catalog/effort";
import type { ProviderModelConfig } from "@oh-my-pi/pi-coding-agent";

export const AGY_PROVIDER_ID = "antigravity-cli";
export const AGY_API_ID = "antigravity-cli";

const ZERO_COST = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };
const FLASH_EFFORTS: Effort[] = [Effort.Minimal, Effort.Low, Effort.Medium, Effort.High];
const PRO_EFFORTS: Effort[] = [Effort.Low, Effort.High];

type WireModelIds = {
	low: string;
	medium?: string;
	high: string;
};

function createModel(id: string, name: string, efforts: Effort[], wire: WireModelIds): ProviderModelConfig {
	const effortRouting: Partial<Record<Effort | "off", string>> = {
		[Effort.Minimal]: wire.low,
		[Effort.Low]: wire.low,
		[Effort.Medium]: wire.medium ?? wire.high,
		[Effort.High]: wire.high,
		[Effort.XHigh]: wire.high,
		[Effort.Max]: wire.high,
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
			defaultLevel: Effort.High,
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

	let effort: Effort | "off" = Effort.High;
	if (disableReasoning) {
		effort = "off";
	} else if (reasoning === Effort.Minimal || reasoning === Effort.Low) {
		effort = Effort.Low;
	} else if (reasoning === Effort.Medium) {
		effort = Effort.Medium;
	}
	const wireModelId = model.thinking.effortRouting[effort];
	if (!wireModelId) {
		throw new Error(`AGY CLI provider has no wire model for "${modelId}" at ${effort} effort.`);
	}
	return wireModelId;
}
