import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { readdir, readlink, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { resolve } from "node:path";

function hasCode(error: unknown, code: string): boolean {
	return error instanceof Error && "code" in error && error.code === code;
}

export async function isOpenSqlitePath(rawPath: string, cwd: string): Promise<boolean> {
	const openFiles = new Set<string>();
	for (const descriptor of await readdir("/proc/self/fd")) {
		const descriptorPath = `/proc/self/fd/${descriptor}`;
		try {
			const target = (await readlink(descriptorPath)).replace(/ \(deleted\)$/, "");
			if (!/\.(?:db|sqlite3?)(?:-wal|-shm)?$/i.test(target)) continue;
			const identity = await stat(descriptorPath, { bigint: true });
			openFiles.add(`${identity.dev}:${identity.ino}`);
		} catch (error) {
			if (!hasCode(error, "ENOENT")) throw error;
		}
	}
	const candidates = [rawPath];
	for (let index = 0; index < rawPath.length; index++) {
		if (rawPath[index] === ":" || rawPath[index] === "?") candidates.push(rawPath.slice(0, index));
	}
	candidates.sort((left, right) => left.length - right.length);
	for (const candidate of candidates) {
		let expanded = candidate;
		if (candidate === "~") expanded = homedir();
		else if (candidate.startsWith("~/")) expanded = resolve(homedir(), candidate.slice(2));
		try {
			const identity = await stat(resolve(cwd, expanded), { bigint: true });
			if (openFiles.has(`${identity.dev}:${identity.ino}`)) return true;
		} catch (error) {
			if (!hasCode(error, "ENOENT") && !hasCode(error, "ENOTDIR")) throw error;
		}
	}
	return false;
}

export default function protectLiveSqlite(pi: ExtensionAPI): void {
	if (process.platform !== "linux") return;
	pi.on("tool_call", async (event, ctx) => {
		if (event.toolName !== "read" || typeof event.input.path !== "string") return;
		if (await isOpenSqlitePath(event.input.path, ctx.cwd)) {
			return {
				block: true,
				reason: "This SQLite file is already open by OMP. Reading it through this tool can release OMP’s Linux file locks and corrupt state. Inspect it with sqlite3 in a separate bash process instead.",
			};
		}
	});
}
