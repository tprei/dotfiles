--!strict

export type Filter = "word" | "all" | "line"

export type Scope = "tab" | "pane" | "screen"

export type Pane = {
	id: number,
	title: string,
	program: string,
	origin: boolean,
	lines: { string },
}

export type Candidate = {
	id: string,
	text: string,
	kind: string,
	pane: number,
	screen: boolean,
	line: number,
	source: string,
}

export type Match = {
	candidate: Candidate,
	hits: { { number } },
}

export type Model = {
	status: "loading" | "ready" | "error",
	searching: boolean,
	message: string?,
	panes: { Pane },
	filter: Filter,
	scope: Scope,
	query: string,
	cursor: number,
	matches: { Match },
	total: number,
	selected: string?,
	marked: { [string]: boolean },
}

export type Intent =
	{ kind: "query", query: string, cursor: number }
	| { kind: "move", by: number }
	| { kind: "first" }
	| { kind: "last" }
	| { kind: "mark" }
	| { kind: "filter" }
	| { kind: "scope" }
	| { kind: "paste" }
	| { kind: "copy" }
	| { kind: "edit" }
	| { kind: "close" }
	| { kind: "none" }

return {}
