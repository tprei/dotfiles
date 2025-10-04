#!/usr/bin/env python3
"""Incrementally analyze Codex session history and refresh AGENTS.md guidance."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import shlex
import subprocess
import textwrap
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_ROOT = Path(__file__).resolve().parent.parent


def resolve_workspace_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (SCRIPT_ROOT / path).resolve()


DEFAULT_HISTORY_PATH = Path.home() / ".codex" / "history.jsonl"
DEFAULT_STATE_PATH = Path("automation_state.json")
DEFAULT_CODEX_PATH = Path("AGENTS.md")
DEFAULT_CLAUDE_DOC_PATH = Path("..") / ".claude" / "CLAUDE.md"
DEFAULT_CLAUDE_STATE_PATH = Path("..") / ".claude" / "automation_state.json"
DEFAULT_CLAUDE_PROJECTS_PATH = Path.home() / ".claude" / "projects"
DEFAULT_CLAUDE_TOP_HISTORY_PATH = Path.home() / ".claude" / "history.jsonl"
DEFAULT_AUTOMATION_BRANCH = "codex/autotune"
DEFAULT_BASE_BRANCH = "master"
MAX_MEMORY_TOKENS = 100_000
MAX_PATTERNS = 20
DEFAULT_LLM_PROVIDER = "claude"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"
STATIC_CALLOUTS: Sequence[str] = (
    "DO NOT IMPLEMENT FALLBACKS. If you are unsure how to do something or something isn't working, avoid quick hacks like mocked data or assuming functionality is impossible; pause and surface the blocker instead.",
    "Prefer rg (ripgrep) over grep for searching.",
    "Leverage MCP tools—including Serena and Repomix—before resorting to manual spelunking.",
)

DEFAULT_CLAUDE_MANUAL_CALLOUTS: Sequence[str] = (
    "- Use context7 for context",
    "- Always write .MD plan/todo files to separate folder. If docs already exists, write it there, otherwise create one",
    "- After you make significant changes, always engage the git commit specialist agent",
    "- DONT ADD FALLBACKS",
    "- When working on a new issue, create a new worktree and branch so that other agents do not conflict with your work in the same environment",
    "- Never add fallbacks",
    "- Never add \"🤖 Generated with Claude Code\" to PRs",
    "- Never put \"commited by agent\" or \"committed by claude code\" -- same for PRs",
    "- Don't write co-authored by Claude",
    "- Always timestamp doc names. Follow conventions of the repo under docs repo",
)

CLAUDE_MANUAL_MARKER_START = "<!-- manual-claude-guidance:start -->"
CLAUDE_MANUAL_MARKER_END = "<!-- manual-claude-guidance:end -->"

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-9;?]*[ -/]*[@-~]")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def sanitize_text(value: str) -> str:
    if not value:
        return ""
    cleaned = ANSI_ESCAPE_RE.sub("", value)
    cleaned = cleaned.replace("\r", "")
    cleaned = CONTROL_CHAR_RE.sub("", cleaned)
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii", "ignore")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    return cleaned.strip()


@dataclass
class Pattern:
    identifier: str
    title: str
    keywords: Sequence[str]
    bullets: Sequence[str]


STATIC_PATTERNS: Sequence[Pattern] = (
    Pattern(
        identifier="plan_first",
        title="Shape the work before touching files",
        keywords=(
            "don't make changes",
            "dont make changes",
            "do not make changes",
            "reason deeply",
            "think deeply",
            "plan first",
            "make a plan",
            "before making changes",
        ),
        bullets=(
            "Always produce an explicit plan and confirm scope before editing. {count} session(s) asked for more upfront reasoning.",
            "Surface unknowns early; restate assumptions and request missing context.",
            "When instructions conflict with filesystem reality, pause and clarify before acting.",
        ),
    ),
    Pattern(
        identifier="document_work",
        title="Document intent and outcomes as you go",
        keywords=(
            "document",
            "write a readme",
            "add docs",
            "update the readme",
            "documentation",
            "changelog",
            "explain what",
        ),
        bullets=(
            "Treat documentation as a first-class deliverable. {count} session(s) explicitly requested docs or READMEs.",
            "Provide contextual summaries with every change: why, what, and how to validate.",
            "When adding or modifying tooling, append usage notes or examples for the next agent.",
        ),
    ),
    Pattern(
        identifier="test_first",
        title="Build verification into the loop",
        keywords=(
            "write a test",
            "add a test",
            "tests ",
            " test",
            "make a test",
            "run the test",
            "coverage",
        ),
        bullets=(
            "Default to running or adding tests whenever behavior shifts. {count} session(s) demanded test coverage or reruns.",
            "If no automated test exists, outline a manual checklist and suggest how to automate it next.",
            "Share test commands and results; avoid saying it works without evidence.",
        ),
    ),
    Pattern(
        identifier="commit_quality",
        title="Be deliberate with commits and PRs",
        keywords=(
            "commit changes",
            "commit with",
            "good commit",
            "clear explanation",
            "changelog",
            "branch",
            "pull request",
        ),
        bullets=(
            "Keep commits scoped and narrated. {count} session(s) asked for clearer commits or change descriptions.",
            "Stage only relevant files, double-check paths, and mention side effects.",
            "Draft changelog-ready notes so follow-up agents inherit context without rereading diffs.",
        ),
    ),
    Pattern(
        identifier="approvals",
        title="Minimize approval churn",
        keywords=(
            "approval",
            "approve",
            "permission",
            "escalate",
        ),
        bullets=(
            "Bundle related commands to reduce repetitive approval requests. {count} session(s) flagged approval fatigue.",
            "Cite why elevated permissions are needed; suggest safe, sandboxed alternatives when possible.",
            "Reuse previously granted permissions if policy allows instead of re-requesting reflexively.",
        ),
    ),
    Pattern(
        identifier="workspace",
        title="Stay within the correct workspace",
        keywords=(
            "wrong file",
            "wrong directory",
            "wrong repo",
            "should be in",
            "correct folder",
            "right folder",
            "right file",
        ),
        bullets=(
            "Confirm target directories before writing—spell out the intended path in your plan. Mentioned in {count} session(s).",
            "When unsure, list candidate locations and ask for confirmation instead of guessing.",
            "After edits, echo file paths so the user can audit quickly.",
        ),
    ),
    Pattern(
        identifier="tooling",
        title="Leverage available tooling proactively",
        keywords=(
            "use docker",
            "docker logs",
            "use ffmpeg",
            "use rg",
            "use ripgrep",
            "use jq",
            "use gh",
            "use script",
            "cron",
            "automation",
            "use pydoll",
        ),
        bullets=(
            "Highlight built-in tools before the user prompts you. {count} session(s) reminded Codex to employ local tooling.",
            "Prefer existing scripts or automation hooks over ad-hoc commands; update or create helpers when they are missing.",
            "Cache learnings: when you discover an effective workflow, note it for future runs.",
        ),
    ),
    Pattern(
        identifier="communication",
        title="Communicate like a teammate",
        keywords=(
            "explain why",
            "walk me through",
            "what changed",
            "summarize",
            "next steps",
            "follow up",
        ),
        bullets=(
            "Narrate trade-offs and residual risks instead of silently choosing a path. {count} session(s) asked for clearer communication.",
            "When blocked, propose concrete next steps for the user instead of stalling.",
            "Close the loop by outlining follow-up tasks or open questions at the end of each session.",
        ),
    ),
)

if len(STATIC_PATTERNS) > MAX_PATTERNS:
    raise ValueError("Number of improvement patterns exceeds MAX_PATTERNS limit")



@dataclass
class ManualSectionSpec:
    header: str
    start_marker: str
    end_marker: str
    default_lines: Sequence[str]


@dataclass
class ManualSectionContent:
    header: str
    start_marker: str
    end_marker: str
    lines: Sequence[str]


@dataclass
class AgentConfig:
    key: str
    history_loader: str
    history_path: Path
    state_path: Path
    output_path: Path
    doc_title: str
    doc_intro: str
    callout_header: str
    static_callouts: Sequence[str]
    manual_section: Optional[ManualSectionSpec] = None
    branch: str = DEFAULT_AUTOMATION_BRANCH
    base_branch: str = DEFAULT_BASE_BRANCH


@dataclass
class AgentRunResult:
    agent: AgentConfig
    sessions: Dict[str, List[Dict[str, object]]]
    processed_sessions: List[str]
    new_sessions: List[str]
    updated_sessions: List[str]
    stats: Dict[str, Dict[str, object]]
    patterns: Sequence[Pattern]
    repo_root: Optional[Path]
    trimmed: int
    output_path: Path
    state_path: Path
    total_sessions: int
    branch: str
    base_branch: str


DEFAULT_AGENT_CONFIGS: Dict[str, AgentConfig] = {
    "codex": AgentConfig(
        key="codex",
        history_loader="codex",
        history_path=DEFAULT_HISTORY_PATH,
        state_path=DEFAULT_STATE_PATH,
        output_path=DEFAULT_CODEX_PATH,
        doc_title="Codex Improvement Guidelines",
        doc_intro=(
            "Codex acts as an autonomous coding partner. The notes below distill common "
            "issues spotted across past sessions in `~/.codex/history.jsonl` and turn "
            "them into guardrails that apply to any repo."
        ),
        callout_header="# Callouts",
        static_callouts=STATIC_CALLOUTS,
        manual_section=None,
        branch=DEFAULT_AUTOMATION_BRANCH,
        base_branch=DEFAULT_BASE_BRANCH,
    ),
    "claude": AgentConfig(
        key="claude",
        history_loader="claude",
        history_path=DEFAULT_CLAUDE_PROJECTS_PATH,
        state_path=DEFAULT_CLAUDE_STATE_PATH,
        output_path=DEFAULT_CLAUDE_DOC_PATH,
        doc_title="Claude Improvement Guidelines",
        doc_intro=(
            "Claude acts as an autonomous coding partner alongside Codex. The notes below "
            "distill recurrent themes from local Claude sessions (captured under "
            "`~/.claude/projects`) so future runs follow the same guardrails."
        ),
        callout_header="# Callouts",
        static_callouts=(),
        manual_section=ManualSectionSpec(
            header="## Manual Reminders",
            start_marker=CLAUDE_MANUAL_MARKER_START,
            end_marker=CLAUDE_MANUAL_MARKER_END,
            default_lines=DEFAULT_CLAUDE_MANUAL_CALLOUTS,
        ),
        branch=DEFAULT_AUTOMATION_BRANCH,
        base_branch=DEFAULT_BASE_BRANCH,
    ),
}


def pattern_from_dict(data: Dict[str, object]) -> Pattern:
    return Pattern(
        identifier=str(data.get("identifier", slugify(str(data.get("title", "dynamic"))))),
        title=str(data.get("title", "Dynamic Pattern")),
        keywords=tuple(data.get("keywords", [])),
        bullets=tuple(data.get("bullets", [])),
    )


def pattern_to_dict(pattern: Pattern) -> Dict[str, object]:
    return {
        "identifier": pattern.identifier,
        "title": pattern.title,
        "keywords": list(pattern.keywords),
        "bullets": list(pattern.bullets),
    }


def load_existing_manual_lines(output_path: Path, spec: ManualSectionSpec) -> Sequence[str]:
    if not output_path.exists():
        return tuple(spec.default_lines)

    try:
        text = output_path.read_text(encoding="utf-8")
    except OSError:
        return tuple(spec.default_lines)

    start_idx = text.find(spec.start_marker)
    end_idx = text.find(spec.end_marker)

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        start_idx += len(spec.start_marker)
        snippet = text[start_idx:end_idx]
        lines = [line.rstrip() for line in snippet.splitlines() if line.strip()]
        return tuple(lines) if lines else tuple(spec.default_lines)

    # First run: treat any bullet-style lines as manual callouts.
    candidate_lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    bullet_lines = [line.strip() for line in candidate_lines if line.strip().startswith("-")]
    if bullet_lines:
        return tuple(bullet_lines)

    return tuple(spec.default_lines)


def build_manual_section(
    config: AgentConfig,
    output_path_override: Optional[Path] = None,
) -> Optional[ManualSectionContent]:
    if config.manual_section is None:
        return None

    target_path = output_path_override or config.output_path
    target_path = resolve_workspace_path(target_path)
    lines = load_existing_manual_lines(target_path, config.manual_section)
    return ManualSectionContent(
        header=config.manual_section.header,
        start_marker=config.manual_section.start_marker,
        end_marker=config.manual_section.end_marker,
        lines=lines,
    )


def dynamic_patterns_from_state(state: Dict[str, object]) -> List[Pattern]:
    dynamic: List[Pattern] = []
    for entry in state.get("dynamic_patterns", []):
        try:
            pattern = pattern_from_dict(entry)
        except Exception:
            continue
        dynamic.append(pattern)
    return dynamic


def truncate_text(value: str, limit: int = 1200) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def summarize_sessions_for_prompt(
    sessions: Dict[str, List[Dict[str, object]]],
    session_ids: Sequence[str],
    char_limit: int = 1600,
) -> str:
    blocks: List[str] = []
    for sid in session_ids:
        messages = sessions.get(sid, [])
        if not messages:
            continue
        combined = " \n".join(
            str(msg.get("text", "")).replace("\n", " ") for msg in messages
        )
        blocks.append(f"Session {sid}:\n{truncate_text(combined, char_limit)}")
    return "\n\n".join(blocks)


def parse_json_array(text: str) -> Optional[List[Dict[str, object]]]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None


def discover_patterns_with_llm(
    sessions: Dict[str, List[Dict[str, object]]],
    session_ids: Sequence[str],
    existing_titles: Sequence[str],
    capacity: int,
    repo_root: Optional[Path],
) -> List[Pattern]:
    provider = os.environ.get("CODEX_PATTERN_PROVIDER", DEFAULT_LLM_PROVIDER).lower()
    if provider == "claude":
        return discover_patterns_with_claude(
            sessions,
            session_ids,
            existing_titles,
            capacity,
        )

    if capacity <= 0 or not session_ids:
        return []

    codex_bin = shutil.which("codex")
    if codex_bin is None:
        print("LLM discovery skipped: codex CLI not available.")
        return []

    excerpts = summarize_sessions_for_prompt(sessions, session_ids[:10])
    if not excerpts:
        return []

    existing_titles_text = ", ".join(existing_titles) if existing_titles else "None"
    prompt = textwrap.dedent(
        f"""
        You are maintaining a set of improvement patterns for the Codex coding agent. Existing patterns are: {existing_titles_text}.
        Review the new session excerpts below and propose up to {capacity} additional patterns that capture recurring issues not already addressed.

        Respond with a JSON array (no extra text) where each element has:
        - "title": short descriptive pattern title (max 7 words)
        - "summary": one-sentence explanation of the issue/opportunity
        - "guidance": array of 2-3 actionable best-practice bullets for Codex (present tense)
        - "keywords": array of 3-6 lowercase keywords to detect similar cases

        Session excerpts:
        {excerpts}

        Return only the JSON array.
        """
    ).strip()

    env = os.environ.copy()

    # Ensure the Codex CLI writes any session artifacts inside the workspace so it
    # stays within sandbox permissions (writing to $HOME/.codex fails here).
    workspace_root = Path(__file__).resolve().parent.parent
    if not workspace_root.exists():
        workspace_root = Path.cwd()
    codex_home = env.get("CODEX_HOME")
    if codex_home:
        codex_home_path = Path(codex_home)
    else:
        codex_home_path = workspace_root / ".codex_cli"
        try:
            codex_home_path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            print(f"Warning: could not create CODEX_HOME at {codex_home_path}: {exc}")
        env["CODEX_HOME"] = str(codex_home_path)

    rollout_dir_value = env.get("CODEX_ROLLOUT_DIR")
    if rollout_dir_value:
        rollout_dir = Path(rollout_dir_value)
    else:
        rollout_dir = Path(env.get("CODEX_HOME", workspace_root)) / "rollouts"
        try:
            rollout_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            print(f"Warning: could not create rollout directory at {rollout_dir}: {exc}")
        env["CODEX_ROLLOUT_DIR"] = str(rollout_dir)

    sandbox_mode = env.get("CODEX_PATTERN_SANDBOX", "workspace-write")
    approval_mode = env.get("CODEX_PATTERN_APPROVAL", "never")
    working_dir = str(repo_root or Path.cwd())

    command: List[str] = [
        codex_bin,
        "-a",
        approval_mode,
        "exec",
        "--sandbox",
        sandbox_mode,
        "--cd",
        working_dir,
    ]

    if (
        sandbox_mode == "workspace-write"
        and env.get("CODEX_PATTERN_DISABLE_NETWORK_CONFIG", "0").lower()
        not in {"1", "true", "yes"}
    ):
        command.extend(["-c", "sandbox_workspace_write.network_access=true"])

    command.append(prompt)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
    except Exception as exc:
        print(f"LLM discovery skipped: {exc}")
        return []

    if result.returncode != 0:
        error_text = result.stderr.strip() or result.stdout.strip()
        print("LLM discovery skipped: command failed", error_text)
        lowered = error_text.lower()
        if "permission denied" in lowered and "rollout" in lowered:
            print(
                "Hint: Codex CLI could not write rollout data. Set CODEX_HOME to a"
                " writable directory or let the updater manage it."
            )
        elif "error sending request" in lowered:
            print(
                "Hint: Codex CLI could not reach the OpenAI API. Confirm network"
                " access before rerunning."
            )
        snippet = (result.stdout or "").strip()
        if snippet:
            preview = truncate_text(snippet, 400)
            print(f"Codex CLI output (truncated): {preview}")
        return []

    combined_lower = f"{result.stdout}\n{result.stderr}".lower()
    if "error sending request" in combined_lower:
        print(
            "LLM discovery skipped: Codex CLI could not reach the OpenAI API."
            " Confirm network access before rerunning."
        )
        return []

    parsed = parse_json_array(result.stdout)
    if not parsed:
        print("LLM discovery returned no parsable JSON.")
        snippet = (result.stdout or "").strip()
        if snippet:
            preview = truncate_text(snippet, 400)
            print(f"Codex CLI output (truncated): {preview}")
        return []

    patterns: List[Pattern] = []
    existing = {title.lower() for title in existing_titles}
    seen_titles: set[str] = set()
    for entry in parsed:
        if len(patterns) >= capacity:
            break
        title = str(entry.get("title", "")).strip()
        if not title or title.lower() in existing or title.lower() in seen_titles:
            continue
        summary = str(entry.get("summary", "")).strip()
        guidance = entry.get("guidance", []) or ([summary] if summary else [])
        guidance_lines = [truncate_text(str(item).strip(), 180) for item in guidance if str(item).strip()]
        if not guidance_lines:
            continue
        keywords = [truncate_text(str(k).lower().strip(), 40) for k in entry.get("keywords", [])]
        if not keywords:
            continue

        identifier = f"dynamic-{slugify(title)}"
        bullets = tuple(guidance_lines[:3])
        pattern = Pattern(
            identifier=identifier,
            title=title,
            keywords=tuple(keywords[:6]),
            bullets=bullets,
        )
        patterns.append(pattern)
        seen_titles.add(title.lower())

    return patterns


def discover_patterns_with_claude(
    sessions: Dict[str, List[Dict[str, object]]],
    session_ids: Sequence[str],
    existing_titles: Sequence[str],
    capacity: int,
) -> List[Pattern]:
    if capacity <= 0 or not session_ids:
        return []

    env = os.environ.copy()
    api_key = env.get("ANTHROPIC_API_KEY") or env.get("CLAUDE_API_KEY")
    if not api_key:
        print(
            "LLM discovery skipped: ANTHROPIC_API_KEY (or CLAUDE_API_KEY) not set "
            "for claude provider."
        )
        return []

    excerpts = summarize_sessions_for_prompt(sessions, session_ids[:10])
    if not excerpts:
        return []

    existing_titles_text = ", ".join(existing_titles) if existing_titles else "None"
    prompt = textwrap.dedent(
        f"""
        You are maintaining a set of improvement patterns for a coding agent. Existing patterns are: {existing_titles_text}.
        Review the new session excerpts below and propose up to {capacity} additional patterns that capture recurring issues not already addressed.

        Respond with a JSON array (no extra text) where each element has:
        - "title": short descriptive pattern title (max 7 words)
        - "summary": one-sentence explanation of the issue/opportunity
        - "guidance": array of 2-3 actionable best-practice bullets for the agent (present tense)
        - "keywords": array of 3-6 lowercase keywords to detect similar cases

        Session excerpts:
        {excerpts}

        Return only the JSON array.
        """
    ).strip()

    model = env.get("CODEX_PATTERN_CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL)
    max_tokens = int(env.get("CODEX_PATTERN_CLAUDE_MAX_TOKENS", "1024"))
    temperature = float(env.get("CODEX_PATTERN_CLAUDE_TEMPERATURE", "0"))
    top_p = env.get("CODEX_PATTERN_CLAUDE_TOP_P")
    top_p_value = float(top_p) if top_p is not None else None

    request_body: Dict[str, object] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if top_p_value is not None:
        request_body["top_p"] = top_p_value

    request_json = json.dumps(request_body).encode("utf-8")
    request = urllib.request.Request(
        env.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages"),
        data=request_json,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": env.get("ANTHROPIC_API_VERSION", "2023-06-01"),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="ignore")
        message = error_text or str(exc)
        print("LLM discovery skipped: claude API error", message)
        if "insufficient" in message.lower() or "credit" in message.lower():
            print(
                "Hint: ensure your Anthropic account has sufficient credit or quota "
                "for claude-sonnet-4-20250514."
            )
        return []
    except urllib.error.URLError as exc:
        print(f"LLM discovery skipped: failed to contact Anthropic ({exc})")
        return []

    try:
        api_response = json.loads(body)
    except json.JSONDecodeError:
        snippet = truncate_text(body.strip(), 400)
        if snippet:
            print(f"Claude API response (truncated): {snippet}")
        print("LLM discovery returned no parsable JSON.")
        return []

    if api_response.get("type") == "error":
        message = truncate_text(str(api_response.get("error", "")), 400)
        print(f"LLM discovery skipped: claude API error {message}")
        return []

    content = api_response.get("content", [])
    text_chunks = [
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    combined_output = "\n".join(chunk for chunk in text_chunks if chunk).strip()

    parsed = parse_json_array(combined_output)
    if not parsed:
        snippet = truncate_text(combined_output, 400)
        if snippet:
            print(f"Claude response (truncated): {snippet}")
        print("LLM discovery returned no parsable JSON.")
        return []

    patterns: List[Pattern] = []
    existing = {title.lower() for title in existing_titles}
    seen_titles: set[str] = set()
    for entry in parsed:
        if len(patterns) >= capacity:
            break
        title = str(entry.get("title", "")).strip()
        if not title or title.lower() in existing or title.lower() in seen_titles:
            continue
        summary = str(entry.get("summary", "")).strip()
        guidance = entry.get("guidance", []) or ([summary] if summary else [])
        guidance_lines = [truncate_text(str(item).strip(), 180) for item in guidance if str(item).strip()]
        if not guidance_lines:
            continue
        keywords = [truncate_text(str(k).lower().strip(), 40) for k in entry.get("keywords", [])]
        if not keywords:
            continue

        identifier = f"dynamic-{slugify(title)}"
        bullets = tuple(guidance_lines[:3])
        pattern = Pattern(
            identifier=identifier,
            title=title,
            keywords=tuple(keywords[:6]),
            bullets=bullets,
        )
        patterns.append(pattern)
        seen_titles.add(title.lower())

    return patterns


def load_codex_history(path: Path) -> Dict[str, List[Dict[str, object]]]:
    sessions: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    if not path.exists():
        raise FileNotFoundError(f"History file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            session_id = entry["session_id"]
            sessions[session_id].append(
                {
                    "ts": entry.get("ts", 0),
                    "text": sanitize_text(entry.get("text", "")),
                }
            )
    for message_list in sessions.values():
        message_list.sort(key=lambda item: item.get("ts") or 0)
    return sessions


def _normalize_timestamp(raw: object) -> int:
    if isinstance(raw, (int, float)):
        value = int(raw)
        # Anthropics history sometimes stores milliseconds.
        if value > 10**12:
            value //= 1000
        return value

    if isinstance(raw, str) and raw:
        cleaned = raw.strip()
        if cleaned.isdigit():
            return _normalize_timestamp(int(cleaned))
        try:
            if cleaned.endswith("Z"):
                cleaned = cleaned[:-1] + "+00:00"
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            return 0

    return 0


def _extract_claude_text(entry: Dict[str, object]) -> Optional[str]:
    message = entry.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    for key in ("summary", "display", "text"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def load_claude_history(
    projects_root: Path,
    top_level_history: Optional[Path] = DEFAULT_CLAUDE_TOP_HISTORY_PATH,
) -> Dict[str, List[Dict[str, object]]]:
    sessions: Dict[str, List[Dict[str, object]]] = defaultdict(list)

    if projects_root.exists():
        jsonl_files = sorted(projects_root.glob("**/*.jsonl"))
        for file_path in jsonl_files:
            try:
                with file_path.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        session_id = (
                            data.get("sessionId")
                            or data.get("session_id")
                            or data.get("leafUuid")
                        )
                        if not session_id:
                            continue
                        text = _extract_claude_text(data)
                        if not text:
                            continue
                        ts = _normalize_timestamp(
                            data.get("timestamp")
                            or data.get("ts")
                            or data.get("createdAt")
                        )
                        sessions[str(session_id)].append({"ts": ts, "text": sanitize_text(text)})
            except OSError:
                continue

    # The flat history file stores quick command invocations; include them as context.
    if top_level_history and top_level_history.exists():
        try:
            with top_level_history.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    project = data.get("project")
                    session_id = f"{project}:{data.get('timestamp')}"
                    text = _extract_claude_text(data)
                    if not text:
                        continue
                    ts = _normalize_timestamp(data.get("timestamp"))
                    sessions[str(session_id)].append({"ts": ts, "text": sanitize_text(text)})
        except OSError:
            pass

    for message_list in sessions.values():
        message_list.sort(key=lambda item: item.get("ts") or 0)

    return sessions


def extract_text(messages: Sequence[Dict[str, object]]) -> List[str]:
    return [str(item.get("text", "")) for item in messages]


def load_state(path: Path) -> Dict[str, object]:
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            state = json.load(fh)
    else:
        state = {}

    state.setdefault("processed_sessions", [])
    state.setdefault("dynamic_patterns", [])
    state.setdefault("trimmed_sessions", 0)
    state.setdefault("session_progress", {})
    return state


def estimate_token_cost(session_id: str) -> int:
    # Rough approximation: 4 characters per token plus delimiter overhead
    return max(1, (len(session_id) // 4) + 1)


def enforce_state_limits(processed_sessions: List[str]) -> Tuple[List[str], int]:
    tokens = 0
    limited: List[str] = []
    trimmed = 0
    for session_id in reversed(processed_sessions):
        cost = estimate_token_cost(session_id)
        if tokens + cost > MAX_MEMORY_TOKENS:
            trimmed += 1
            continue
        tokens += cost
        limited.append(session_id)
    limited.reverse()
    trimmed_count = len(processed_sessions) - len(limited)
    return limited, trimmed_count


def save_state(path: Path, state: Dict[str, object]) -> None:
    processed_list = list(state.get("processed_sessions", []))
    session_progress: Dict[str, int] = {
        str(key): int(value)
        for key, value in (state.get("session_progress", {}) or {}).items()
    }

    limited, trimmed = enforce_state_limits(processed_list)

    seen: set[str] = set()
    ordered_unique: List[str] = []
    for sid in limited:
        if sid in seen:
            continue
        seen.add(sid)
        ordered_unique.append(sid)

    if session_progress:
        session_progress = {
            sid: session_progress[sid]
            for sid in ordered_unique
            if sid in session_progress
        }
        state["session_progress"] = session_progress

    state["processed_sessions"] = ordered_unique
    state["trimmed_sessions"] = trimmed
    state["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")


def build_stats(
    sessions: Dict[str, List[Dict[str, object]]],
    processed_ids: Iterable[str],
    patterns: Sequence[Pattern],
) -> Dict[str, Dict[str, object]]:
    stats: Dict[str, Dict[str, object]] = {}
    processed_set = set(processed_ids)

    for pattern in patterns:
        matched_sessions: List[str] = []
        examples: List[Dict[str, str]] = []

        for sid, messages in sessions.items():
            if processed_set and sid not in processed_set:
                continue
            text_messages = extract_text(messages)
            blob = "\n".join(text_messages).lower()
            if any(keyword in blob for keyword in pattern.keywords):
                matched_sessions.append(sid)
                if len(examples) < 3:
                    snippet = next(
                        (
                            msg.get("text", "")
                            for msg in messages
                            if any(k in str(msg.get("text", "")).lower() for k in pattern.keywords)
                        ),
                        messages[0].get("text", ""),
                    )
                    examples.append({
                        "session_id": sid,
                        "snippet": " ".join(str(snippet).strip().split())[:160],
                    })

        stats[pattern.identifier] = {
            "count": len(set(matched_sessions)),
            "examples": examples,
        }

    return stats


def render_examples(examples: Sequence[Dict[str, str]]) -> List[str]:
    lines: List[str] = []
    for item in examples:
        snippet = item["snippet"]
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        lines.append(f"Example: \"{snippet}\"")
    return lines


def render_guidance_document(
    title: str,
    intro: str,
    patterns: Sequence[Pattern],
    stats: Dict[str, Dict[str, object]],
    callouts: Sequence[str],
    callout_header: str,
    manual_section: Optional[ManualSectionContent] = None,
) -> str:
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(intro)
    lines.append("")

    for index, pattern in enumerate(patterns, start=1):
        pattern_stats = stats.get(pattern.identifier, {"count": 0, "examples": []})
        count = pattern_stats.get("count", 0)
        example_lines = render_examples(pattern_stats.get("examples", []))

        lines.append(f"## {index}. {pattern.title}")
        for bullet in pattern.bullets:
            text = bullet.format(count=count)
            lines.append(f"- {text}")
        for example in example_lines:
            wrapped = textwrap.fill(example, width=92)
            if wrapped:
                first, *rest = wrapped.splitlines()
                lines.append(f"- {first}")
                for continuation in rest:
                    lines.append(f"  {continuation}")
        lines.append("")

    lines.append(
        "Regularly revisit this document as new patterns emerge. The automation in this repository will "
        "refresh guidance when new sessions highlight fresh themes."
    )

    if callouts:
        lines.append("")
        lines.append(callout_header)
        lines.append("")
        for callout in callouts:
            lines.append(f"- {callout}")

    if manual_section:
        lines.append("")
        lines.append(manual_section.header)
        lines.append("")
        lines.append(manual_section.start_marker)
        if manual_section.lines:
            lines.append("")
            for line in manual_section.lines:
                lines.append(line)
            lines.append("")
        lines.append(manual_section.end_marker)

    return "\n".join(lines).rstrip() + "\n"


def write_document(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write(content)


def run_cmd(command: Sequence[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    if check and result.returncode != 0:
        cmd_display = " ".join(command)
        raise RuntimeError(
            f"Command failed ({cmd_display})\nSTDOUT: {result.stdout.strip()}\nSTDERR: {result.stderr.strip()}"
        )
    return result


def detect_repo_root(start: Path) -> Optional[Path]:
    current = start
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            break
        current = current.parent

    result = run_cmd(["git", "rev-parse", "--show-toplevel"], start, check=False)
    if result.returncode == 0:
        path = Path(result.stdout.strip())
        if path.exists():
            return path
    return None


def repo_has_changes(repo_root: Path) -> bool:
    status = run_cmd(["git", "status", "--porcelain"], repo_root)
    return bool(status.stdout.strip())


def ensure_branch(repo_root: Path, branch: str, base_branch: str) -> None:
    try:
        run_cmd(["git", "fetch", "origin"], repo_root)
    except RuntimeError as exc:
        print(f"Warning: could not fetch origin ({exc})")
    current = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root).stdout.strip()
    if current == branch:
        return

    exists = run_cmd(["git", "rev-parse", "--verify", branch], repo_root, check=False)
    if exists.returncode == 0:
        run_cmd(["git", "checkout", branch], repo_root)
        return

    run_cmd(["git", "checkout", base_branch], repo_root)
    result = run_cmd(["git", "pull", "--ff-only", "origin", base_branch], repo_root, check=False)
    if result.returncode != 0:
        print("Warning: could not pull latest base; continuing with local state.")
    run_cmd(["git", "checkout", "-B", branch], repo_root)


def stage_paths(repo_root: Path, paths: Sequence[Path]) -> None:
    for path in paths:
        if not path.exists():
            continue
        resolved = path.resolve()
        try:
            rel = resolved.relative_to(repo_root.resolve())
        except ValueError:
            continue
        run_cmd(["git", "add", str(rel)], repo_root)


def has_staged_changes(repo_root: Path) -> bool:
    result = run_cmd(["git", "diff", "--cached", "--quiet"], repo_root, check=False)
    return result.returncode != 0


def commit_changes(repo_root: Path, message: str) -> None:
    run_cmd(["git", "commit", "-m", message], repo_root)


def push_branch(repo_root: Path, branch: str) -> None:
    try:
        run_cmd(["git", "push", "--set-upstream", "origin", branch], repo_root)
    except RuntimeError:
        run_cmd(["git", "push", "origin", branch], repo_root)


def get_pr_info(repo_root: Path, branch: str) -> Optional[Dict[str, object]]:
    if shutil.which("gh") is None:
        return None
    result = run_cmd(
        ["gh", "pr", "view", branch, "--json", "number,state,title,url"],
        repo_root,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None




def process_agent(
    agent: AgentConfig,
    *,
    history_path: Optional[Path] = None,
    claude_top_history: Optional[Path] = None,
    state_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    dry_run: bool = False,
    branch: Optional[str] = None,
    base_branch: Optional[str] = None,
) -> AgentRunResult:
    resolved_state_path = resolve_workspace_path(state_path or agent.state_path)
    resolved_output_path = resolve_workspace_path(output_path or agent.output_path)
    branch_name = branch or agent.branch
    base_branch_name = base_branch or agent.base_branch

    if agent.history_loader == "codex":
        history_source = history_path or agent.history_path
        sessions = load_codex_history(history_source)
    elif agent.history_loader == "claude":
        projects_root = history_path or agent.history_path
        top_history_path = claude_top_history or DEFAULT_CLAUDE_TOP_HISTORY_PATH
        sessions = load_claude_history(projects_root, top_history_path)
    else:
        raise ValueError(f"Unsupported history loader: {agent.history_loader}")

    state = load_state(resolved_state_path)
    session_progress: Dict[str, int] = {
        str(key): int(value)
        for key, value in (state.get("session_progress", {}) or {}).items()
    }
    processed_sessions_snapshot: List[str] = list(state.get("processed_sessions", []))
    dynamic_patterns = dynamic_patterns_from_state(state)
    patterns: List[Pattern] = list(STATIC_PATTERNS) + dynamic_patterns

    repo_root = detect_repo_root(resolved_output_path.resolve().parent)

    migration_performed = False
    if processed_sessions_snapshot and not session_progress:
        for sid in processed_sessions_snapshot:
            messages = sessions.get(sid, [])
            if not messages:
                continue
            latest_ts = max(int(item.get("ts") or 0) for item in messages)
            session_progress[sid] = latest_ts
        migration_performed = True

    new_sessions: List[str] = []
    updated_sessions: List[str] = []

    for sid, messages in sessions.items():
        latest_ts = max(int(item.get("ts") or 0) for item in messages) if messages else 0
        last_seen = session_progress.get(sid)
        if last_seen is None:
            if messages:
                new_sessions.append(sid)
        else:
            if any(int(item.get("ts") or 0) > last_seen for item in messages):
                updated_sessions.append(sid)
        session_progress[sid] = latest_ts

    processed_sessions = list(session_progress.keys())
    state["session_progress"] = session_progress
    state["processed_sessions"] = processed_sessions

    remaining_pattern_slots = MAX_PATTERNS - len(patterns)
    llm_disabled = os.environ.get("CODEX_PATTERN_DISABLE_LLM", "0").lower() in {"1", "true", "yes"}

    touched_sessions = new_sessions + [sid for sid in updated_sessions if sid not in new_sessions]

    prefix = f"[{agent.key}]"
    if new_sessions:
        preview = ", ".join(new_sessions[:5])
        suffix = "..." if len(new_sessions) > 5 else ""
        print(f"{prefix} New sessions detected ({len(new_sessions)}): {preview}{suffix}")
    else:
        print(f"{prefix} No new sessions detected this run.")

    if updated_sessions:
        preview = ", ".join(updated_sessions[:5])
        suffix = "..." if len(updated_sessions) > 5 else ""
        print(f"{prefix} Updated sessions ({len(updated_sessions)}): {preview}{suffix}")
    else:
        print(f"{prefix} No previously processed sessions had new messages.")

    if llm_disabled:
        if touched_sessions and remaining_pattern_slots > 0:
            print(f"{prefix} LLM discovery skipped: disabled via CODEX_PATTERN_DISABLE_LLM.")
    elif touched_sessions and remaining_pattern_slots > 0:
        llm_patterns = discover_patterns_with_llm(
            sessions,
            touched_sessions,
            [pattern.title for pattern in patterns],
            remaining_pattern_slots,
            repo_root,
        )
        if llm_patterns:
            patterns.extend(llm_patterns)
            dynamic_patterns.extend(llm_patterns)
            if "dynamic_patterns" not in state:
                state["dynamic_patterns"] = []
            state["dynamic_patterns"] = [pattern_to_dict(p) for p in dynamic_patterns]
            print(
                f"{prefix} Discovered dynamic patterns: "
                + ", ".join(pattern.title for pattern in llm_patterns)
            )
        else:
            print(f"{prefix} No dynamic patterns discovered in latest sessions.")

    callouts = list(agent.static_callouts)
    manual_section = build_manual_section(agent, resolved_output_path)

    stats = build_stats(sessions, processed_sessions, patterns)
    document_content = render_guidance_document(
        title=agent.doc_title,
        intro=agent.doc_intro,
        patterns=patterns,
        stats=stats,
        callouts=callouts,
        callout_header=agent.callout_header,
        manual_section=manual_section,
    )

    trimmed_preview = enforce_state_limits(processed_sessions)[1]

    if dry_run:
        print(f"{prefix} Dry run: skipping writes.")
        trimmed = trimmed_preview
    else:
        write_document(resolved_output_path, document_content)
        if touched_sessions or trimmed_preview or migration_performed or not resolved_state_path.exists():
            if "dynamic_patterns" not in state:
                state["dynamic_patterns"] = [pattern_to_dict(p) for p in dynamic_patterns]
            save_state(resolved_state_path, state)
        trimmed = state.get("trimmed_sessions", trimmed_preview)

    print(
        f"{prefix} Analyzed {len(processed_sessions)} session(s); "
        f"{len(new_sessions)} new, {len(updated_sessions)} updated since last run."
    )
    if trimmed:
        print(f"{prefix} Trimmed {trimmed} session id(s) to stay within memory limits.")
    for pattern in patterns:
        count = stats.get(pattern.identifier, {}).get("count", 0)
        print(f"{prefix}  - {pattern.title}: {count} session(s)")

    recent_dynamic = [p for p in dynamic_patterns if p.identifier.startswith("dynamic-")]
    if recent_dynamic:
        titles = ", ".join(p.title for p in recent_dynamic[-5:])
        print(f"{prefix} Recent dynamic patterns tracked ({len(recent_dynamic)} total): {titles}")

    return AgentRunResult(
        agent=agent,
        sessions=sessions,
        processed_sessions=processed_sessions,
        new_sessions=new_sessions,
        updated_sessions=updated_sessions,
        stats=stats,
        patterns=patterns,
        repo_root=repo_root,
        trimmed=trimmed,
        output_path=resolved_output_path,
        state_path=resolved_state_path,
        total_sessions=len(processed_sessions),
        branch=branch_name,
        base_branch=base_branch_name,
    )


def build_commit_message_multi(results: Sequence[AgentRunResult]) -> str:
    labels: List[str] = []
    for result in results:
        new_count = len(result.new_sessions)
        updated_count = len(result.updated_sessions)
        parts: List[str] = []
        if new_count:
            parts.append(f"{new_count} new")
        if updated_count:
            parts.append(f"{updated_count} updated")
        if parts:
            labels.append(f"{result.agent.key}: {' / '.join(parts)}")
    if labels:
        return f"chore: refresh agent guidance ({'; '.join(labels)})"
    return "chore: refresh agent guidance"


def build_pr_title_multi(results: Sequence[AgentRunResult]) -> str:
    active_agents = [
        result.agent.key for result in results if result.new_sessions or result.updated_sessions
    ]
    if active_agents:
        return f"Update agent guidance ({', '.join(active_agents)})"
    return "Update agent guidance"


def relativize_path(repo_root: Optional[Path], path: Path) -> str:
    resolved = path.resolve()
    if repo_root is not None:
        try:
            return str(resolved.relative_to(repo_root.resolve()))
        except ValueError:
            pass
    return str(resolved)


def summarize_session_preview(session_ids: Sequence[str]) -> str:
    if not session_ids:
        return "None"
    preview = ", ".join(session_ids[:5])
    if len(session_ids) > 5:
        preview += ", ..."
    return preview


def format_example_for_pr(examples: Sequence[Dict[str, str]]) -> str:
    if not examples:
        return "no direct example stored"
    sample = examples[0]
    snippet = sample.get("snippet", "")
    if len(snippet) > 100:
        snippet = snippet[:97] + "..."
    session_id = sample.get("session_id", "unknown")
    return f"session {session_id} — \"{snippet}\""


def build_pr_body_multi(results: Sequence[AgentRunResult]) -> str:
    summary_lines: List[str] = []
    for result in results:
        output_rel = relativize_path(result.repo_root, result.output_path)
        state_rel = relativize_path(result.repo_root, result.state_path)
        summary_lines.append(
            f"- regenerate {output_rel} with updated guidance across {result.total_sessions} session(s)"
        )
        summary_lines.append(
            f"- update {state_rel} to record processed conversations"
        )
    summary_section = "\\n".join(summary_lines) if summary_lines else "- No changes detected"

    motivation_sections: List[str] = []
    for result in results:
        top_patterns = sorted(
            result.patterns,
            key=lambda pattern: result.stats.get(pattern.identifier, {}).get("count", 0),
            reverse=True,
        )[:3]
        lines: List[str] = []
        for pattern in top_patterns:
            data = result.stats.get(pattern.identifier, {"count": 0, "examples": []})
            lines.append(
                f"- {pattern.title}: {data.get('count', 0)} session(s); {format_example_for_pr(data.get('examples', []))}"
            )
        if not lines:
            lines.append("- No new insights detected")
        motivation_sections.append(
            f"### {result.agent.doc_title}\n" + "\n".join(lines)
        )
    motivation_section = (
        "\n\n".join(motivation_sections)
        if motivation_sections
        else "- No new insights detected"
    )

    new_sessions_lines = [
        f"- {result.agent.key}: {summarize_session_preview(result.new_sessions)}"
        for result in results
    ]
    updated_sessions_lines = [
        f"- {result.agent.key}: {summarize_session_preview(result.updated_sessions)}"
        for result in results
    ]

    if len(results) == len(DEFAULT_AGENT_CONFIGS):
        dry_run_flag = "--agent all"
    else:
        dry_run_flag = " ".join(f"--agent {result.agent.key}" for result in results) or "--agent codex"

    body = f"""
## Summary
{summary_section}

## Motivation
{motivation_section}

## Newly Processed Sessions
{"\\n".join(new_sessions_lines)}

## Updated Sessions
{"\\n".join(updated_sessions_lines)}

## Testing
- scripts/codex_pattern_updater.py --dry-run {dry_run_flag}
"""
    return textwrap.dedent(body).strip() + "\n"


def create_or_update_pr_multi(
    repo_root: Path,
    branch: str,
    base_branch: str,
    results: Sequence[AgentRunResult],
) -> None:
    if shutil.which("gh") is None:
        print("gh CLI not found; skipping PR automation.")
        return

    info = get_pr_info(repo_root, branch)
    title = build_pr_title_multi(results)
    body = build_pr_body_multi(results)

    if info and info.get("state") == "OPEN":
        run_cmd(["gh", "pr", "edit", branch, "--title", title, "--body", body], repo_root)
        print(f"Updated existing PR #{info.get('number')}.")
        return

    run_cmd(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base_branch,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ],
        repo_root,
    )
    print("Created new pull request.")


def handle_git_workflow_multi(
    results: Sequence[AgentRunResult],
    branch: Optional[str],
    base_branch: Optional[str],
) -> None:
    if not results:
        return

    repo_roots = {
        result.repo_root.resolve()
        for result in results
        if result.repo_root is not None
    }
    if not repo_roots:
        print("Skipping git automation; could not locate git repository root.")
        return
    if len(repo_roots) > 1:
        raise RuntimeError("Multiple repository roots detected; cannot manage git automation.")

    repo_root = next(iter(repo_roots))

    if not repo_has_changes(repo_root):
        print("No working tree changes detected; skipping git automation.")
        return

    branch_name = branch or results[0].branch
    base_branch_name = base_branch or results[0].base_branch

    ensure_branch(repo_root, branch_name, base_branch_name)

    paths_to_stage = {Path(__file__).resolve()}
    for result in results:
        paths_to_stage.add(result.output_path.resolve())
        paths_to_stage.add(result.state_path.resolve())

    stage_paths(repo_root, sorted(paths_to_stage))

    if not has_staged_changes(repo_root):
        print("No staged changes after add; skipping commit.")
        return

    commit_changes(
        repo_root,
        build_commit_message_multi(results),
    )
    push_branch(repo_root, branch_name)
    create_or_update_pr_multi(repo_root, branch_name, base_branch_name, results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent",
        action="append",
        choices=[*DEFAULT_AGENT_CONFIGS.keys(), "all"],
        help="Agent(s) to process (defaults to codex). Repeat to specify multiple or use 'all'.",
    )
    parser.add_argument("--history", type=Path, help="Override Codex history.jsonl path")
    parser.add_argument("--state", type=Path, help="Override Codex automation state path")
    parser.add_argument("--codex", type=Path, help="Override Codex guidance output path")
    parser.add_argument("--codex-history", type=Path, help="Alias for --history")
    parser.add_argument("--codex-state", type=Path, help="Alias for --state")
    parser.add_argument("--codex-output", type=Path, help="Alias for --codex")
    parser.add_argument("--claude-projects", type=Path, help="Override Claude projects directory")
    parser.add_argument(
        "--claude-history",
        type=Path,
        help="Override Claude top-level history.jsonl path",
    )
    parser.add_argument("--claude-state", type=Path, help="Override Claude automation state path")
    parser.add_argument("--claude-output", type=Path, help="Override Claude guidance output path")
    parser.add_argument("--dry-run", action="store_true", help="Run analysis without writing outputs")
    parser.add_argument("--skip-git", action="store_true", help="Skip git commit/push and PR automation")
    parser.add_argument("--branch", help="Automation branch name overriding defaults")
    parser.add_argument("--base-branch", help="Base branch for PRs overriding defaults")
    args = parser.parse_args()

    selected = args.agent or ["codex"]
    if "all" in selected:
        agent_keys = list(DEFAULT_AGENT_CONFIGS.keys())
    else:
        agent_keys: List[str] = []
        for key in selected:
            if key == "all":
                continue
            if key not in DEFAULT_AGENT_CONFIGS:
                raise ValueError(f"Unknown agent: {key}")
            if key not in agent_keys:
                agent_keys.append(key)

    overrides: Dict[str, Dict[str, Optional[Path]]] = {key: {} for key in agent_keys}
    if "codex" in overrides:
        overrides["codex"]["history_path"] = args.codex_history or args.history
        overrides["codex"]["state_path"] = args.codex_state or args.state
        overrides["codex"]["output_path"] = args.codex_output or args.codex
    if "claude" in overrides:
        overrides["claude"]["history_path"] = args.claude_projects
        overrides["claude"]["claude_top_history"] = args.claude_history
        overrides["claude"]["state_path"] = args.claude_state
        overrides["claude"]["output_path"] = args.claude_output

    results: List[AgentRunResult] = []
    for key in agent_keys:
        config = DEFAULT_AGENT_CONFIGS[key]
        override = overrides.get(key, {})
        result = process_agent(
            config,
            history_path=override.get("history_path"),
            claude_top_history=override.get("claude_top_history"),
            state_path=override.get("state_path"),
            output_path=override.get("output_path"),
            dry_run=args.dry_run,
            branch=args.branch,
            base_branch=args.base_branch,
        )
        results.append(result)

    if not args.dry_run and not args.skip_git:
        handle_git_workflow_multi(results, branch=args.branch, base_branch=args.base_branch)
    elif args.skip_git:
        print("Skipping git and PR automation (--skip-git).")
