const REPLACEMENTS: [RegExp, string][] = [
	[/<(\/?)system[-_]conventions>/gi, "<$1conventions>"],
	[/<(\/?)system[-_]directive>/gi, "<$1instructions>"],
	[/<(\/?)critical>/gi, "<$1important>"],
	[/Oh My Pi coding harness/gi, "AI coding assistant"],
	[/Oh My Pi/gi, "coding assistant"],
	[/omp Live/gi, "coding assistant live"],
];

export function sanitizeAgyText(raw: string): string {
	let text = raw;
	for (const [pattern, replacement] of REPLACEMENTS) {
		text = text.replace(pattern, replacement);
	}
	return text;
}
