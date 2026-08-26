/**
 * Direct picker for the session's thinking effort.
 *
 * omp ships only `app.thinking.cycle` (Shift+Tab), which steps blindly along the
 * ladder. This surfaces the levels as a list instead: Alt+J, or `/effort [level]`.
 *
 * Alt+J because tmux leaves lowercase M-j free (it is bound only inside the M-n
 * `create_mode` table), and it sits beside the Alt+K / Alt+L model pickers.
 *
 * Note: the session-level `auto` selector is not reachable here — `setThinkingLevel`
 * accepts a concrete `ThinkingLevel`, while `auto` is a `ConfiguredThinkingLevel`
 * that only the `defaultThinkingLevel` setting understands.
 */
import type { ExtensionAPI, ExtensionCommandContext, ExtensionContext } from "@oh-my-pi/pi-coding-agent";
import type { ThinkingLevel } from "@oh-my-pi/pi-agent-core";

/** Every `Effort` the catalog defines, plus explicit reasoning disablement. */
const LEVELS = ["off", "minimal", "low", "medium", "high", "xhigh", "max"] as const;
type Level = (typeof LEVELS)[number];

const BLURB: Record<Level, string> = {
	off: "reasoning disabled",
	minimal: "fastest, shallowest",
	low: "quick checks",
	medium: "balanced",
	high: "default depth",
	xhigh: "deep analysis",
	max: "maximum reasoning",
};

function isLevel(value: string): value is Level {
	return (LEVELS as readonly string[]).includes(value);
}

export default function thinkingPicker(pi: ExtensionAPI) {
	/**
	 * Reasoning models with no controllable effort surface carry no `thinking`
	 * metadata at all, so fall back to the full ladder and let omp clamp rather
	 * than rendering an empty picker.
	 */
	function levelsFor(ctx: ExtensionContext): Level[] {
		const efforts = ctx.model?.thinking?.efforts;
		if (!efforts?.length) return [...LEVELS];
		return ["off", ...efforts.filter(isLevel)];
	}

	/**
	 * `Effort` is a nominal const enum, so its members are not interchangeable with
	 * the equivalent string literals even though they are identical at runtime
	 * (`Effort.High === "high"`). Assert once here instead of importing the enum:
	 * a value import would add a runtime dependency that a bare extension
	 * directory cannot resolve.
	 */
	function apply(ctx: ExtensionContext, level: Level): void {
		pi.setThinkingLevel(level as unknown as ThinkingLevel);
		ctx.ui.notify(`Thinking effort: ${level}`);
	}

	async function pick(ctx: ExtensionContext): Promise<void> {
		if (!ctx.hasUI) {
			ctx.ui.notify("Thinking picker requires interactive mode.", "warning");
			return;
		}

		const current = pi.getThinkingLevel();
		const options = levelsFor(ctx).map(level => ({
			label: level,
			description: level === current ? `${BLURB[level]} \u00b7 current` : BLURB[level],
		}));

		// select() resolves to the chosen label, which is the level id verbatim.
		const chosen = await ctx.ui.select("Thinking effort", options);
		if (chosen === undefined || !isLevel(chosen) || chosen === current) return;
		apply(ctx, chosen);
	}

	pi.registerShortcut("alt+j", { description: "Pick thinking effort", handler: pick });

	pi.registerCommand("effort", {
		description: "Pick the session's thinking effort level",
		getArgumentCompletions: prefix => {
			const matches = LEVELS.filter(level => level.startsWith(prefix.trim().toLowerCase()));
			return matches.length === 0
				? null
				: matches.map(level => ({ value: level, label: level, description: BLURB[level] }));
		},
		handler: async (args, ctx: ExtensionCommandContext) => {
			const requested = args.trim().toLowerCase();
			if (requested.length === 0) {
				await pick(ctx);
				return;
			}
			if (!isLevel(requested)) {
				ctx.ui.notify(`Unknown effort "${requested}". Expected one of: ${LEVELS.join(", ")}`, "warning");
				return;
			}
			apply(ctx, requested);
		},
	});
}
