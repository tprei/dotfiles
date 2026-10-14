--!strict

export type Line = { text: string, ansi: string }

export type Position = { line: number, column: number }

export type Model = {
	lines: { Line },
	cursor: Position,
	anchor: Position?,
	linewise: boolean,
	top: number,
	left: number,
	cols: number,
	rows: number,
	preferred: number,
	query: string,
	searching: boolean,
	searchDirection: number,
	searchOrigin: Position?,
	searchDraft: string,
	count: string,
	status: "loading" | "ready" | "error",
	message: string,
}

export type Result = "changed" | "copy" | "quit" | "ignored"

return {}
