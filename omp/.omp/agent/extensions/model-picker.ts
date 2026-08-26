/**
 * Fast model switcher (`/m`).
 *
 * omp's built-in `/model` (alt+l) opens the full ModelBrowser and, on its text
 * path, accepts only an exact `id` or `provider/id` — so `/model opus-5` fails
 * (the id is `claude-opus-5`) and there is no argument autocomplete. Worse,
 * `/model` is a reserved builtin name: an extension registering it is filtered
 * out of the palette and completions (`PT0 = new Set(F40.keys())`) even though
 * dispatch would still fire. Rather than fight the reserved name, this exposes a
 * short, unencumbered alias with fuzzy resolve + tab-completion.
 *
 * `/m`          → arrow-key picker over authenticated models (current marked)
 * `/m opus-5`   → smart resolve: role alias (`@slow`), exact `provider/id` or
 *                 canonical id, then token / substring / subsequence fuzzy match,
 *                 newest model first (version-aware, flagship over cheap tiers).
 *                 The newest top match switches directly; weak ties open a picker.
 *
 * The live model list is captured on session start and refreshed each call —
 * `getArgumentCompletions` receives only the prefix (no context), so it reads
 * the last-captured snapshot.
 */
import type { ExtensionAPI, ExtensionCommandContext, ExtensionContext } from "@oh-my-pi/pi-coding-agent";
import type { Model } from "@oh-my-pi/pi-ai";

let models: Model[] = [];

function selector(m: Model): string {
	return `${m.provider}/${m.id}`;
}

function isSubsequence(needle: string, hay: string): boolean {
	let i = 0;
	for (const ch of hay) {
		if (ch === needle[i]) i++;
		if (i === needle.length) return true;
	}
	return false;
}

function fmtContext(n: number | null | undefined): string | undefined {
	if (!n || n <= 0) return undefined;
	if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}M`;
	return `${Math.round(n / 1000)}K`;
}

interface Ranked {
	m: Model;
	s: number;
}

/** Version tuple from an id's first numeric run: "glm-5.2" → [5,2], "claude-opus-4-8" → [4,8]. */
function versionOf(id: string): number[] {
	const m = id.toLowerCase().match(/\d+(?:[.-]\d+)*/);
	if (!m) return [];
	const out: number[] = [];
	for (const p of m[0].split(/[.-]/).map(Number)) {
		if (out.length > 0 && p >= 1000) break; // dated snapshot suffix, e.g. -20250514
		out.push(p);
	}
	return out;
}

const CHEAP_TIER = /[-._](mini|flash|haiku|nano|small|lite|turbo|cheap)([-._]|$)/i;
const isCheapVariant = (id: string): boolean => CHEAP_TIER.test(id);

function compareRecency(a: Model, b: Model): number {
	const va = versionOf(a.id);
	const vb = versionOf(b.id);
	const n = Math.max(va.length, vb.length);
	for (let i = 0; i < n; i++) {
		const x = i < va.length ? va[i] : -1;
		const y = i < vb.length ? vb[i] : -1;
		if (x !== y) return y - x;
	}
	const ca = isCheapVariant(a.id) ? 1 : 0;
	const cb = isCheapVariant(b.id) ? 1 : 0;
	if (ca !== cb) return ca - cb;
	if (!!a.reasoning !== !!b.reasoning) return a.reasoning ? -1 : 1;
	return selector(a).localeCompare(selector(b));
}

const CONFIDENT_MATCH = 800;

/** Fuzzy rank, higher is better. */
function rankModels(list: Model[], raw: string): Ranked[] {
	const q = raw.trim().toLowerCase();
	const out: Ranked[] = [];
	for (const m of list) {
		const id = m.id.toLowerCase();
		const name = m.name.toLowerCase();
		const prov = m.provider.toLowerCase();
		let s: number;
		if (!q) s = 1;
		else if (id === q || `${prov}/${id}` === q) s = 1000;
		else if (id.startsWith(q)) s = 850;
		else {
			const tokens = id.split(/[-._/]/);
			if (tokens.some(t => t === q)) s = 800;
			else if (tokens.some(t => t.startsWith(q))) s = 700;
			else if (id.includes(q)) s = 600;
			else if (name.includes(q)) s = 500;
			else if (prov.includes(q)) s = 300;
			else if (isSubsequence(q, id)) s = 250;
			else if (isSubsequence(q, name)) s = 200;
			else continue;
		}
		out.push({ m, s });
	}
	out.sort((a, b) => b.s - a.s || compareRecency(a.m, b.m));
	return out;
}

function describe(m: Model, currentSelector?: string): string {
	const parts = [m.provider];
	const ctx = fmtContext(m.contextWindow);
	if (ctx) parts.push(`${ctx} ctx`);
	if (currentSelector && selector(m) === currentSelector) parts.push("current");
	return parts.join(" · ");
}

async function apply(pi: ExtensionAPI, ctx: ExtensionContext, m: Model): Promise<void> {
	const ok = await pi.setModel(m);
	if (!ok) {
		ctx.ui.notify(`No API key for ${selector(m)} — run /setup providers.`, "warning");
		return;
	}
	ctx.ui.notify(`Model: ${selector(m)}`);
}

async function pick(pi: ExtensionAPI, ctx: ExtensionContext, items: Model[], focusSelector?: string): Promise<void> {
	if (!ctx.hasUI) {
		ctx.ui.notify("Model picker requires interactive mode.", "warning");
		return;
	}
	if (items.length === 0) {
		ctx.ui.notify("No models available — run /setup providers to authenticate.", "warning");
		return;
	}
	const currentSelector = ctx.models.current() ? selector(ctx.models.current() as Model) : undefined;

	// Fall back to the full selector as the label only when an id collides across providers.
	const dupes = new Set<string>();
	const seen = new Set<string>();
	for (const m of items) (seen.has(m.id) ? dupes : seen).add(m.id);

	const labelOf = new Map<string, Model>();
	const options = items.map(m => {
		const label = dupes.has(m.id) ? selector(m) : m.id;
		labelOf.set(label, m);
		return { label, description: describe(m, currentSelector) };
	});

	const initialIndex = Math.max(0, items.findIndex(m => selector(m) === (focusSelector ?? currentSelector)));
	const chosen = await ctx.ui.select("Switch model", options, { initialIndex });
	if (chosen === undefined) return;
	const model = labelOf.get(chosen);
	if (model) await apply(pi, ctx, model);
}

export default function modelPicker(pi: ExtensionAPI) {
	pi.on("session_start", (_event, ctx) => {
		models = ctx.models.list();
	});

	pi.registerCommand("m", {
		description: "Switch session model — fuzzy match or picker (e.g. /m opus-5, /m @slow)",
		getArgumentCompletions: prefix => {
			if (models.length === 0) return null;
			const ranked = rankModels(models, prefix);
			if (ranked.length === 0) return null;
			return ranked.slice(0, 15).map(({ m }) => ({
				value: selector(m),
				label: m.id,
				description: describe(m),
				hint: m.name && m.name !== m.id ? m.name : undefined,
			}));
		},
		handler: async (args, ctx: ExtensionCommandContext) => {
			models = ctx.models.list();
			const q = args.trim();
			if (!q) {
				await pick(pi, ctx, models.slice().sort((a, b) => selector(a).localeCompare(selector(b))));
				return;
			}
			// Role alias (`@slow`), exact `provider/id`, canonical bare id, or thinking suffix.
			const direct = ctx.models.resolve(q);
			if (direct) {
				await apply(pi, ctx, direct);
				return;
			}
			const ranked = rankModels(models, q);
			if (ranked.length === 0) {
				ctx.ui.notify(`No model matches "${q}". Run /m with no args for the picker.`, "warning");
				return;
			}
			const top = ranked[0];
			const next = ranked[1];
			if (!next || top.s >= CONFIDENT_MATCH || top.s > next.s) {
				await apply(pi, ctx, top.m);
				return;
			}
			await pick(pi, ctx, ranked.map(r => r.m), selector(top.m));
		},
	});
}
