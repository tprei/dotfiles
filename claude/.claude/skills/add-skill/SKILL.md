---
name: add-skill
description: Scaffold a new Claude Code skill with proper directory structure, SKILL.md frontmatter, and optional reference files. Use when creating or bootstrapping a new skill.
model: sonnet
allowed-tools: Read Glob Grep Write Bash(ls:*) Bash(mkdir:*) Bash(ln:*)
argument-hint: "[skill-name]"
---

# Add skill

Create a new Claude Code skill in this dotfiles repo following established conventions.

## Parameters

| Parameter | Source | Required | Description |
|-----------|--------|----------|-------------|
| skill-name | `$ARGUMENTS` | Yes | Lowercase, hyphen-separated name for the new skill |

If `$ARGUMENTS` is empty, ask: "What should the skill be named? (lowercase, hyphen-separated, e.g. `git-reviewer`)"

## Skill location

All skills in this repo live under the Stow-managed path:

```
claude/.claude/skills/<skill-name>/
├── SKILL.md              # Required entrypoint
└── references/           # Optional supporting files
```

After `stow claude`, they symlink to `~/.claude/skills/<skill-name>/`.

**Working directory for new skills:** `/home/prei/dotfiles/claude/.claude/skills/`

## Execution flow

### Step 1: Validate name

- Reject names with spaces, uppercase letters, or special characters (allow lowercase, digits, hyphens)
- Check that `claude/.claude/skills/<skill-name>/` does not already exist
- If it exists, stop and report the conflict

### Step 2: Gather skill metadata

Ask the user for each of these, one prompt at a time. Show the default in brackets. Accept empty input as the default.

| Field | Question | Default |
|-------|----------|---------|
| description | One-line description — when should Claude invoke this skill? | *(required, no default)* |
| model | Model tier: `haiku`, `sonnet`, or `opus`? | `sonnet` |
| allowed-tools | Space-separated tool list (e.g. `Read Grep Bash(git:*)`) | `Read Glob Grep` |
| user-invocable | Should users invoke this with `/name`? | `true` |
| disable-model-invocation | Prevent Claude from auto-invoking? | `false` |
| references | Create a `references/` directory? | `no` |

### Step 3: Gather skill body content

Ask the user: "Describe what this skill does. What instructions should Claude follow when this skill is invoked?"

Use their response to draft the skill body with these sections:

```markdown
# <Skill title>

<Purpose — one sentence>

## When to use

<Bullet list of trigger conditions>

## Instructions

<Numbered steps or structured guidance>
```

If the user provided reference files info, add a **Reference files** section with a table like:

```markdown
## Reference files

| File | Contents |
|------|----------|
| `references/<name>` | Description |
```

### Step 4: Write the files

1. Create the skill directory: `claude/.claude/skills/<skill-name>/`
2. Write `SKILL.md` with the gathered frontmatter and body
3. If references requested, create `claude/.claude/skills/<skill-name>/references/` directory

### Step 5: Present the result

Show the user:
- Full path of the created `SKILL.md`
- The complete file contents for review
- Remind them to run `stow claude` from the dotfiles root if the symlink needs refreshing
- Ask if they want to add a trigger hint to `CLAUDE.md` (e.g., `- When asked about X, use the /skill-name skill`)

## SKILL.md frontmatter reference

All supported fields for the skill author's reference:

```yaml
---
name: my-skill                       # string — directory name is fallback
description: "..."                   # string — used for auto-invocation matching
argument-hint: "[arg1] [arg2]"       # string — shown in autocomplete
model: sonnet                        # haiku | sonnet | opus
allowed-tools: Read Grep Bash(git *) # space-separated or YAML list
user-invocable: true                 # bool — show in / menu
disable-model-invocation: false      # bool — prevent auto-invocation
effort: high                         # low | medium | high | max
context: fork                        # runs in isolated subagent
agent: Explore                       # agent type for context: fork
paths: "src/**/*.ts"                 # auto-activate for matching files
shell: bash                          # bash | powershell
---
```

## Body features reference

These features are available inside skill body content:

- **Argument substitution:** `$ARGUMENTS` (full string), `$ARGUMENTS[0]` (first arg), `$0` shorthand
- **Session variables:** `${CLAUDE_SESSION_ID}`, `${CLAUDE_SKILL_DIR}`
- **Shell execution:** Prefix with `!` backticks for dynamic context injection:
  ```
  Current branch: !`git branch --show-current`
  ```
- **Extended thinking:** Include the word `ultrathink` anywhere in the body

## Conventions

- Skill names: lowercase, hyphen-separated
- Entry file: always `SKILL.md` (uppercase)
- Reference files: lowercase, hyphen-separated
- Keep the SKILL.md body focused — delegate detail to reference files
- Do not add comments to generated code unless the user requests them
