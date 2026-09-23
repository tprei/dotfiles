---
name: add-skill
description: Scaffold a new shared skill in this dotfiles repo. Use when creating or bootstrapping a reusable skill that should work across Codex, Claude, and Pi.
---

# Add skill

Canonical skills live in `shared/skills/<skill-name>/` (`SKILL.md`, optional `references/`, `scripts/`, `assets/`). These already symlink to it: `.agents/skills`, `.claude/skills`, `codex/.agents/skills`, `claude/.claude/skills`, `pi/.pi/agent/skills`, `omp/.omp/agent/skills`. Never write into a consumer path.

1. Name: ask if missing ("lowercase, hyphen-separated, e.g. `git-reviewer`"). Allow only lowercase letters, digits, and hyphens. Stop if the directory exists.
2. Ask, one at a time: the description (when should it trigger; required), then whether to create `references/`, `scripts/`, `assets/` (default no).
3. Ask what the skill does and what the agent should follow. Draft a body: title, one-line purpose, trigger conditions, and numbered instructions. Add a reference-file table if `references/` exists. Keep the body lean; push detail into `references/`.
4. Write `SKILL.md` with portable frontmatter only, unless the user asks for tool-specific fields:
   ```yaml
   ---
   name: my-skill
   description: What it does and when to use it.
   ---
   ```
5. Show the path and contents, note that no symlink step is needed, and ask whether to add a trigger line to `shared/context/agent-guidance.md`.

Conventions: `SKILL.md` uppercase, portable wording, no comments in generated code unless asked.
