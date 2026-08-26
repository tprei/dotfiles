/**
 * Model-role profile switcher (`/use`, Alt+U).
 *
 * Switches the entire model-role lineup between five provider profiles in one
 * shot. /use or Alt+U lists the profiles (current one marked); `/use <key>` (or
 * a unique prefix) applies it directly; Tab completes keys.
 *
 * A profile assigns the `plan` role one model and every other built-in role the
 * same "all others" model. The live session model flips to the all-others model.
 */
import type { ExtensionAPI, ExtensionCommandContext, ExtensionContext } from "@oh-my-pi/pi-coding-agent";

const REST_ROLES = ["default", "smol", "slow", "vision", "designer", "commit", "tiny", "task", "advisor"] as const;

interface Profile {
	name: string;
	plan: string;
	rest: string;
}

const PROFILES: Record<string, Profile> = {
	cld: { name: "Claude (Anthropic)", plan: "anthropic/claude-opus-5:high", rest: "anthropic/claude-sonnet-5:high" },
	glm: { name: "GLM (Z.AI)",        plan: "zai/glm-5.3:max",          rest: "zai/glm-5.3:high"            },
	oc:  { name: "OpenCode",          plan: "opencode-go/glm-5.3:high", rest: "opencode-go/deepseek-v4-pro:high" },
	gpt: { name: "Codex (OpenAI)",    plan: "openai-codex/gpt-5.6-sol:high", rest: "openai-codex/gpt-5.6-luna:medium" },
};

/** One-line model summary — provider prefix stripped so it fits the picker column. */
function summary(p: Profile): string {
	const planId = p.plan.includes("/") ? p.plan.slice(p.plan.indexOf("/") + 1) : p.plan;
	const restId = p.rest.includes("/") ? p.rest.slice(p.rest.indexOf("/") + 1) : p.rest;
	return `plan ${planId} \u00b7 rest ${restId}`;
}

function currentKey(pi: ExtensionAPI): string | undefined {
	const s = pi.pi.settings;
	const planSel = s.getModelRole("plan");
	if (!planSel) return undefined;
	for (const [key, p] of Object.entries(PROFILES)) {
		if (planSel !== p.plan) continue;
		if (REST_ROLES.some(role => s.getModelRole(role) !== p.rest)) continue;
		return key;
	}
	return undefined;
}

async function apply(pi: ExtensionAPI, ctx: ExtensionContext, key: string): Promise<void> {
	const p = PROFILES[key];
	if (!p) return;

	const planModel = ctx.models.resolve(p.plan);
	const restModel = ctx.models.resolve(p.rest);
	if (!planModel || !restModel) {
		ctx.ui.notify(`Profile "${key}" not available — run /setup providers.`, "warning");
		return;
	}

	const s = pi.pi.settings;
	const roles: Record<string, string> = { plan: p.plan };
	for (const role of REST_ROLES) {
		roles[role] = p.rest;
	}
	s.overrideModelRoles(roles);

	const ok = await pi.setModel(restModel);
	if (!ok) {
		ctx.ui.notify(`Switched ${p.name}, but no API key for live default ${p.rest}.`, "warning");
		return;
	}
	ctx.ui.notify(`Profile: ${key} \u00b7 ${p.name}`);
}

async function pick(pi: ExtensionAPI, ctx: ExtensionContext): Promise<void> {
	if (!ctx.hasUI) {
		ctx.ui.notify("Profile picker requires interactive mode.", "warning");
		return;
	}

	const cur = currentKey(pi);
	const options = Object.entries(PROFILES).map(([k, p]) => ({
		label: `${k} \u00b7 ${p.name}`,
		description: k === cur ? `${summary(p)} \u00b7 current` : summary(p),
	}));

	const curIdx = cur ? Object.keys(PROFILES).indexOf(cur) : -1;
	const initialIndex = Math.max(0, curIdx);
	const chosen = await ctx.ui.select("Switch profile", options, { initialIndex });
	if (chosen === undefined) return;
	const key = chosen.slice(0, chosen.indexOf(" "));
	if (!PROFILES[key]) return;
	await apply(pi, ctx, key);
}

export default function profilePicker(pi: ExtensionAPI) {
	pi.registerShortcut("alt+u", { description: "Pick model-role profile", handler: ctx => pick(pi, ctx) });

	pi.registerCommand("use", {
		description: "Switch model-role profile (cld, glm, oc, gpt)",
		getArgumentCompletions: prefix => {
			const q = prefix.trim().toLowerCase();
			const keys = Object.keys(PROFILES).filter(k => k.startsWith(q));
			if (keys.length === 0) return null;
			return keys.map(k => ({
				value: k,
				label: `${k} \u00b7 ${PROFILES[k].name}`,
				description: summary(PROFILES[k]),
			}));
		},
		handler: async (args, ctx: ExtensionCommandContext) => {
			const q = args.trim().toLowerCase();
			if (q.length === 0) {
				await pick(pi, ctx);
				return;
			}
			if (PROFILES[q]) {
				await apply(pi, ctx, q);
				return;
			}
			const matches = Object.keys(PROFILES).filter(k => k.startsWith(q));
			if (matches.length === 1) {
				await apply(pi, ctx, matches[0]);
				return;
			}
			if (matches.length > 1) {
				await pick(pi, ctx);
				return;
			}
			ctx.ui.notify(`Unknown profile "${args}". Profiles: ${Object.keys(PROFILES).join(", ")}`, "warning");
		},
	});
}
