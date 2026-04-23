---
name: add-skill
description: Scaffold a new Codex skill with proper directory structure and SKILL.md frontmatter. Use when creating or bootstrapping a new skill.
---

# Add skill

Create a new Codex skill in this dotfiles repo following established conventions.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| skill-name | Yes | Lowercase, hyphen-separated name for the new skill. |

If no skill name is supplied, ask: "What should the skill be named? (lowercase, hyphen-separated, e.g. `git-reviewer`)"

## Skill location

All skills in this repo live under the stow-managed path:

```
codex/.agents/skills/<skill-name>/
├── SKILL.md      # Required entrypoint
└── references/   # Optional supporting files
```

After `stow codex`, they are linked into `~/.agents/skills/<skill-name>/`, which Codex discovers as user-level skills.

**Working directory for new skills:** `/home/prei/dotfiles/codex/.agents/skills/`

## Execution flow

### Step 1: Validate name

- Reject names with spaces, uppercase letters, or special characters (allow lowercase, digits, hyphens).
- Check that `codex/.agents/skills/<skill-name>/` does not already exist.
- If it exists, stop and report the conflict.

### Step 2: Gather skill metadata

Ask the user for each of these, one prompt at a time. Show the default in brackets. Accept empty input as the default.

| Field | Question | Default |
|-------|----------|---------|
| description | One-line description — when should Codex invoke this skill? | *(required, no default)* |
| references | Create a `references/` directory? | `no` |

### Step 3: Gather skill body content

Ask the user: "Describe what this skill does. What instructions should Codex follow when this skill is invoked?"

Use the response to draft the skill body with these sections:

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

1. Create the skill directory: `codex/.agents/skills/<skill-name>/`.
2. Write `SKILL.md` with the gathered frontmatter and body.
3. If references were requested, create `codex/.agents/skills/<skill-name>/references/`.

### Step 5: Present the result

Show the user:

- Full path of the created `SKILL.md`.
- The complete file contents for review.
- Remind them to run `stow codex` from the dotfiles root (or re-run the symlinking step) if needed.
- Ask if they want to add a trigger hint to `AGENTS.md` (e.g., `- When asked about X, invoke the X skill.`).

## SKILL.md frontmatter reference

Codex only requires `name` and `description`:

```yaml
---
name: my-skill
description: "Clear explanation of when this skill triggers and its boundaries."
---
```

## Conventions

- Skill names: lowercase, hyphen-separated.
- Entry file: always `SKILL.md` (uppercase).
- Reference files: lowercase, hyphen-separated.
- Keep the SKILL.md body focused — delegate detail to reference files.
- Do not add comments to generated code unless the user requests them.
