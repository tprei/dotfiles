import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

const WRITE_TOOLS: Record<string, true> = {
	edit: true,
	write: true,
	apply_patch: true,
	ast_edit: true,
};

const COMMENT_SUPPRESSION =
	/(?:\/\/|\/\*|<!--)[^\n]*(?:@ts[-](?:ignore|expect[-]error)|eslint[-]disable)|#\s*type:\s*ignore|#\s*pyright:\s*ignore|#\s*pylint:\s*disable|#\s*noqa/;

const ADVISORY_GATE = /continue-on-error:\s*true|\|\|\s*true\b/;

const MARKDOWN = /\.mdx?$/i;

const CI_CONFIG = /(?:^|\/)\.github\/workflows\/|\.ya?ml$/i;

const SECTION_HEADER = /^\[([^\]\n]+)#[0-9A-Fa-f]{4}\]/gm;

const COMMAND_START = "(?:^|[\\n;|&(){}`])\\s*(?:['\"]\\s*)?";

const SHELL_MUTATION = [
	"sed\\s+(?:-{1,2}\\S+\\s+)*-(?:i|-in-place)",
	"perl\\s+(?:-\\S+\\s+)*-[0acdlnpsw]*i",
	"awk\\b[^\\n;|&]*\\s-i\\s+inplace\\b",
	"cat\\b[^\\n;|&]*?(?<![0-9&>])>{1,2}\\s*[^\\s&>|]",
].map(body => new RegExp(COMMAND_START + body));

const EVAL_SHELL = /\bsubprocess\b|\bos\.system\s*\(|Bun\.\$|\bexecSync\s*\(|\bspawnSync\s*\(|`/;

const QUOTED = /'[^']*'|"(?:[^"\\]|\\.)*"/g;

const GIT_BYPASS = [
	/\bgit\s+commit\b[^\n;|&]*--no-verify\b/,
	/\bgit\s+commit\b[^\n;|&]*\s-[^\s-]*n/,
	/\bgit\s+push\b[^\n;|&]*--force(?![-\w])/,
	/\bgit\s+push\b[^\n;|&]*\s-[^\s-]*f/,
];

const SUPPRESSION_HEAD =
	"Fix the root cause instead of silencing the checker. This write carries a banned inline suppression: ";

const SUPPRESSION_TAIL = ". Resolve the underlying error; if you genuinely cannot, stop and report the blocker.";

const ADVISORY_HEAD = "Lint and typecheck gates must be blocking. This CI config carries an advisory escape hatch: ";

const ADVISORY_TAIL =
	". Make the step fail the build instead; if a step genuinely cannot pass, stop and report the blocker.";

const SHELL_REASON =
	"Use the edit tool for text edits (read the file first to mint its snapshot anchor) or ast_edit for structural codemods across call sites. In-place shell substitution and file-clobbering redirection (sed -i, perl -i, awk -i inplace, cat > file) bypass anchor verification and diff previews. Reserve bash for real binaries and read-only fact pipelines.";

const GIT_REASON =
	"Never bypass git hooks or overwrite published history. Committing with --no-verify or -n skips the checks that gate this repo, and pushing with --force or -f can destroy a remote branch. Run the checks, fix what fails, and reach for --force-with-lease only on a branch you own.";

function collectStrings(value: unknown, out: string[], depth: number): void {
	if (typeof value === "string") {
		out.push(value);
		return;
	}
	if (depth >= 6) return;
	if (Array.isArray(value)) {
		for (const item of value) collectStrings(item, out, depth + 1);
		return;
	}
	if (typeof value === "object" && value !== null) {
		for (const item of Object.values(value)) collectStrings(item, out, depth + 1);
	}
}

function collectPaths(input: unknown, texts: readonly string[]): string[] {
	const paths: string[] = [];
	if (typeof input === "object" && input !== null) {
		if ("path" in input && typeof input.path === "string" && input.path.length > 0) paths.push(input.path);
		if ("paths" in input && Array.isArray(input.paths)) {
			for (const entry of input.paths) {
				if (typeof entry === "string" && entry.length > 0) paths.push(entry);
			}
		}
	}
	for (const text of texts) {
		for (const match of text.matchAll(SECTION_HEADER)) paths.push(match[1]);
	}
	return paths;
}

function isExemptPath(target: string): boolean {
	const path = target.replace(/^\.\//, "");
	return path.length > 0 && MARKDOWN.test(path);
}

function isCiConfigPath(target: string): boolean {
	const path = target.replace(/^\.\//, "");
	return path.length > 0 && CI_CONFIG.test(path);
}

function hasShellMutation(command: string): boolean {
	for (const pattern of SHELL_MUTATION) {
		if (pattern.test(command)) return true;
	}
	return false;
}

function hasGitBypass(command: string): boolean {
	const bare = command.replace(QUOTED, '""');
	for (const pattern of GIT_BYPASS) {
		if (pattern.test(bare)) return true;
	}
	return false;
}

export default function invariants(pi: ExtensionAPI) {
	pi.on("tool_call", event => {
		if (WRITE_TOOLS[event.toolName] === true) {
			const texts: string[] = [];
			collectStrings(event.input, texts, 0);
			const paths = collectPaths(event.input, texts);
			if (paths.length > 0 && paths.every(isExemptPath)) return undefined;
			const written = texts.join("\n");
			const marker = COMMENT_SUPPRESSION.exec(written);
			if (marker) return { block: true, reason: `${SUPPRESSION_HEAD}${marker[0]}${SUPPRESSION_TAIL}` };
			if (paths.some(isCiConfigPath)) {
				const gate = ADVISORY_GATE.exec(written);
				if (gate) return { block: true, reason: `${ADVISORY_HEAD}${gate[0]}${ADVISORY_TAIL}` };
			}
			return undefined;
		}

		if (event.toolName === "bash") {
			const command = String(event.input.command ?? "");
			if (hasShellMutation(command)) return { block: true, reason: SHELL_REASON };
			if (hasGitBypass(command)) return { block: true, reason: GIT_REASON };
			return undefined;
		}

		if (event.toolName === "eval") {
			const code = String(event.input.code ?? "");
			if (EVAL_SHELL.test(code) && hasShellMutation(code)) return { block: true, reason: SHELL_REASON };
			return undefined;
		}

		return undefined;
	});
}
