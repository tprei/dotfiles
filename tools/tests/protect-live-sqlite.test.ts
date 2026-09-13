import { afterEach, expect, test } from "bun:test";
import { Database } from "bun:sqlite";
import { link, mkdtemp, rm, symlink, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { isOpenSqlitePath } from "../../omp/.omp/agent/extensions/protect-live-sqlite";

const databases: Database[] = [];
const directories: string[] = [];

afterEach(async () => {
	for (const database of databases.splice(0)) database.close();
	for (const directory of directories.splice(0)) await rm(directory, { recursive: true });
});

async function fixture(): Promise<{ directory: string; path: string }> {
	const directory = await mkdtemp("/tmp/omp-sqlite-protection-test-");
	directories.push(directory);
	const path = join(directory, "agent.db");
	const database = new Database(path);
	databases.push(database);
	database.exec("PRAGMA journal_mode=WAL; CREATE TABLE sample(value TEXT); INSERT INTO sample VALUES ('test');");
	return { directory, path };
}

test("protects open databases, selectors, relative paths, and sidecars", async () => {
	const { directory, path } = await fixture();
	for (const target of [path, `${path}:sample`, `${path}:sample?limit=2`, `${path}?query=${"x".repeat(300)}`, "agent.db", `${path}-wal`, `${path}-shm`]) {
		expect(await isOpenSqlitePath(target, directory)).toBe(true);
	}
});

test("recognizes symbolic and hard-link aliases without opening their contents", async () => {
	const { directory, path } = await fixture();
	const symbolic = join(directory, "alias");
	const hard = join(directory, "hard-alias");
	await symlink(path, symbolic);
	await link(path, hard);
	expect(await isOpenSqlitePath(`${symbolic}:sample`, directory)).toBe(true);
	expect(await isOpenSqlitePath(hard, directory)).toBe(true);
});

test("allows closed databases, unrelated files, and absent paths", async () => {
	const { directory, path } = await fixture();
	for (const database of databases.splice(0)) database.close();
	const text = join(directory, "notes.txt");
	await writeFile(text, "ordinary text");
	for (const target of [path, text, join(directory, "absent.db")]) {
		expect(await isOpenSqlitePath(target, directory)).toBe(false);
	}
});
