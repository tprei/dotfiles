---
name: add-skill
description: Scaffold a new shared skill in this dotfiles repo. Use when creating or bootstrapping a reusable skill that should work across Codex, Claude, and Pi.
---

# Add skill

Create a new shared skill in this dotfiles repo following established conventions.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| skill-name | Yes | Lowercase, hyphen-separated name for the new skill. |

If no skill name is supplied, ask: "What should the skill be named? (lowercase, hyphen-separated, e.g. `git-reviewer`)"

## Skill location

All canonical skills in this repo live under:

```
/Users/thiago/repos/dotfiles/shared/skills/<skill-name>/
├── SKILL.md
├── references/           # Optional
├── scripts/              # Optional
└── assets/               # Optional
```

These consumer paths are already symlinked to the shared library:

- `.agents/skills`
- `.claude/skills`
- `codex/.agents/skills`
- `claude/.claude/skills`
- `pi/.pi/agent/skills`

Do not create or edit skills inside the consumer paths directly. Write only to `shared/skills/`.

## Execution flow

### Step 1: Validate name

- Reject names with spaces, uppercase letters, or special characters. Allow lowercase letters, digits, and hyphens only.
- Check that `shared/skills/<skill-name>/` does not already exist.
- If it exists, stop and report the conflict.

### Step 2: Gather skill metadata

Ask the user for each of these, one prompt at a time.

| Field | Question | Default |
|-------|----------|---------|
| description | One-line description — when should this skill trigger? | *(required, no default)* |
| references | Create a `references/` directory? | `no` |
| scripts | Create a `scripts/` directory? | `no` |
| assets | Create an `assets/` directory? | `no` |

Prefer portable frontmatter with only `name` and `description`. Add tool-specific fields only if the user explicitly asks for them and they are compatible with the tools that should consume the skill.

### Step 3: Gather skill body content

Ask the user: "Describe what this skill does. What instructions should the agent follow when this skill is invoked?"

Use their response to draft the skill body with these sections:

```markdown
# <Skill title>

<Purpose — one sentence>

## When to use

<Bullet list of trigger conditions>

## Instructions

<Numbered steps or structured guidance>
```

If the user asked for reference files, add a **Reference files** section with a table like:

```markdown
## Reference files

| File | Contents |
|------|----------|
| `references/<name>` | Description |
```

### Step 4: Write the files

1. Create the skill directory: `shared/skills/<skill-name>/`.
2. Write `SKILL.md` with the gathered frontmatter and body.
3. If requested, create `references/`, `scripts/`, and `assets/` under that directory.

### Step 5: Present the result

Show the user:
- Full path of the created `SKILL.md`.
- The complete file contents for review.
- A reminder that no extra symlink step is needed because the consumer directories already point at `shared/skills/`.
- Ask whether they want a trigger hint added to the shared agent guidance file.

## SKILL.md frontmatter reference

Use the smallest portable frontmatter that does the job:

```yaml
---
name: my-skill
description: Clear explanation of what the skill does and when to use it.
---
```

## Conventions

- Skill names: lowercase, hyphen-separated.
- Entry file: always `SKILL.md` (uppercase).
- Keep the SKILL.md body focused — move detail into `references/` when needed.
- Prefer portable wording over product-specific wording.
- Do not add comments to generated code unless the user requests them.
