#!/usr/bin/env python3
"""Incrementally analyze Codex session history and refresh CODEX.md guidance."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_HISTORY_PATH = Path.home() / ".codex" / "history.jsonl"
DEFAULT_STATE_PATH = Path("automation_state.json")
DEFAULT_CODEX_PATH = Path("CODEX.md")
DEFAULT_AUTOMATION_BRANCH = "codex/autotune"
DEFAULT_BASE_BRANCH = "master"
MAX_MEMORY_TOKENS = 100_000
MAX_PATTERNS = 20


@dataclass
class Pattern:
    identifier: str
    title: str
    keywords: Sequence[str]
    bullets: Sequence[str]


PATTERNS: Sequence[Pattern] = (
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

if len(PATTERNS) > MAX_PATTERNS:
    raise ValueError("Number of improvement patterns exceeds MAX_PATTERNS limit")


def load_history(path: Path) -> Dict[str, List[str]]:
    sessions: Dict[str, List[str]] = defaultdict(list)
    if not path.exists():
        raise FileNotFoundError(f"History file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            sessions[entry["session_id"]].append(entry["text"])
    return sessions


def load_state(path: Path) -> Dict[str, object]:
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"processed_sessions": []}


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


def save_state(path: Path, processed_sessions: Iterable[str]) -> None:
    processed_list = list(processed_sessions)
    limited, trimmed = enforce_state_limits(processed_list)
    payload = {
        "processed_sessions": sorted(set(limited)),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trimmed_sessions": trimmed,
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def collect_new_sessions(all_sessions: Dict[str, List[str]], processed: Iterable[str]) -> List[str]:
    seen = set(processed)
    return [sid for sid in all_sessions.keys() if sid not in seen]


def build_stats(
    sessions: Dict[str, List[str]],
    processed_ids: Iterable[str],
) -> Dict[str, Dict[str, object]]:
    stats: Dict[str, Dict[str, object]] = {}
    processed_set = set(processed_ids)

    for pattern in PATTERNS:
        matched_sessions: List[str] = []
        examples: List[Dict[str, str]] = []

        for sid, messages in sessions.items():
            if processed_set and sid not in processed_set:
                continue
            blob = "\n".join(messages).lower()
            if any(keyword in blob for keyword in pattern.keywords):
                matched_sessions.append(sid)
                if len(examples) < 3:
                    snippet = next((m for m in messages if any(k in m.lower() for k in pattern.keywords)), messages[0])
                    examples.append({
                        "session_id": sid,
                        "snippet": " ".join(snippet.strip().split())[:160],
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


def render_codex(stats: Dict[str, Dict[str, object]]) -> str:
    lines: List[str] = []
    lines.append("# Codex Improvement Guidelines")
    lines.append("")
    lines.append(
        "Codex acts as an autonomous coding partner. The notes below distill common issues spotted across "
        "past sessions in `~/.codex/history.jsonl` and turn them into guardrails that apply to any repo."
    )
    lines.append("")

    for index, pattern in enumerate(PATTERNS, start=1):
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

    return "\n".join(lines).rstrip() + "\n"


def write_codex(path: Path, content: str) -> None:
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


def build_commit_message(new_sessions: int) -> str:
    if new_sessions:
        return f"chore: refresh codex guidance ({new_sessions} new session{'s' if new_sessions != 1 else ''})"
    return "chore: refresh codex guidance"


def build_pr_title(new_sessions: int) -> str:
    if new_sessions:
        return f"Update CODEX guidance from {new_sessions} new session{'s' if new_sessions != 1 else ''}"
    return "Update CODEX guidance"


def format_example_for_pr(examples: Sequence[Dict[str, str]]) -> str:
    if not examples:
        return "no direct example stored"
    sample = examples[0]
    snippet = sample["snippet"]
    if len(snippet) > 100:
        snippet = snippet[:97] + "..."
    return f"session {sample['session_id']} — \"{snippet}\""


def build_pr_body(
    total_sessions: int,
    new_sessions: Sequence[str],
    stats: Dict[str, Dict[str, object]],
) -> str:
    top_patterns = sorted(
        PATTERNS,
        key=lambda pattern: stats.get(pattern.identifier, {}).get("count", 0),
        reverse=True,
    )[:3]

    motivation_lines = []
    for pattern in top_patterns:
        data = stats.get(pattern.identifier, {"count": 0, "examples": []})
        motivation_lines.append(
            f"- {pattern.title}: {data.get('count', 0)} session(s); {format_example_for_pr(data.get('examples', []))}"
        )

    motivation_section = "\n".join(motivation_lines) if motivation_lines else "- No new insights detected"

    new_sessions_list = ", ".join(new_sessions[:5]) if new_sessions else "None"

    body = f"""
## Summary
- regenerate CODEX.md with updated guidance across {total_sessions} session(s)
- update automation_state.json to record processed conversations

## Motivation
{motivation_section}

## Newly Processed Sessions
- {new_sessions_list}

## Testing
- scripts/codex_pattern_updater.py --dry-run
"""
    return textwrap.dedent(body).strip() + "\n"


def create_or_update_pr(
    repo_root: Path,
    branch: str,
    base_branch: str,
    new_sessions: Sequence[str],
    stats: Dict[str, Dict[str, object]],
    total_sessions: int,
) -> None:
    if shutil.which("gh") is None:
        print("gh CLI not found; skipping PR automation.")
        return

    info = get_pr_info(repo_root, branch)
    title = build_pr_title(len(new_sessions))
    body = build_pr_body(total_sessions=total_sessions, new_sessions=new_sessions, stats=stats)

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


def handle_git_workflow(
    repo_root: Path,
    codex_path: Path,
    state_path: Path,
    branch: str,
    base_branch: str,
    new_sessions: Sequence[str],
    stats: Dict[str, Dict[str, object]],
    total_sessions: int,
) -> None:
    if not repo_has_changes(repo_root):
        print("No working tree changes detected; skipping git automation.")
        return

    ensure_branch(repo_root, branch, base_branch)

    paths_to_stage = [codex_path, state_path, Path(__file__).resolve()]
    stage_paths(repo_root, paths_to_stage)

    if not has_staged_changes(repo_root):
        print("No staged changes after add; skipping commit.")
        return

    commit_changes(repo_root, build_commit_message(len(new_sessions)))
    push_branch(repo_root, branch)
    create_or_update_pr(
        repo_root,
        branch,
        base_branch,
        new_sessions,
        stats,
        total_sessions=total_sessions,
    )

def run(
    history_path: Path,
    state_path: Path,
    codex_path: Path,
    dry_run: bool = False,
    skip_git: bool = False,
    branch: str = DEFAULT_AUTOMATION_BRANCH,
    base_branch: str = DEFAULT_BASE_BRANCH,
) -> None:
    sessions = load_history(history_path)
    state = load_state(state_path)
    processed_sessions: List[str] = list(state.get("processed_sessions", []))

    new_sessions = collect_new_sessions(sessions, processed_sessions)
    if new_sessions:
        processed_sessions.extend(new_sessions)

    processed_sessions, trimmed = enforce_state_limits(processed_sessions)

    stats = build_stats(sessions, processed_sessions)
    codex_content = render_codex(stats)

    if dry_run:
        print("Dry run: skipping writes.")
    else:
        write_codex(codex_path, codex_content)
        if new_sessions or trimmed or not state_path.exists():
            save_state(state_path, processed_sessions)

    print(
        f"Analyzed {len(processed_sessions)} session(s); {len(new_sessions)} new since last run."
    )
    if trimmed:
        print(f"Trimmed {trimmed} session id(s) to stay within memory limits.")
    for pattern in PATTERNS:
        count = stats.get(pattern.identifier, {}).get("count", 0)
        print(f" - {pattern.title}: {count} session(s)")

    if dry_run or skip_git:
        if skip_git:
            print("Skipping git and PR automation (--skip-git).")
        return

    repo_root = detect_repo_root(codex_path.resolve().parent)
    if repo_root is None:
        print("Skipping git automation; could not locate git repository root.")
        return
    try:
        handle_git_workflow(
            repo_root,
            codex_path.resolve(),
            state_path.resolve(),
            branch,
            base_branch,
            new_sessions,
            stats,
            total_sessions=len(processed_sessions),
        )
    except RuntimeError as exc:
        print(f"Git automation failed: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY_PATH, help="Path to history.jsonl")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH, help="Path to incremental state file")
    parser.add_argument("--codex", type=Path, default=DEFAULT_CODEX_PATH, help="Path to CODEX.md output")
    parser.add_argument("--dry-run", action="store_true", help="Run analysis without writing outputs")
    parser.add_argument("--skip-git", action="store_true", help="Skip git commit/push and PR automation")
    parser.add_argument("--branch", default=DEFAULT_AUTOMATION_BRANCH, help="Automation branch name")
    parser.add_argument("--base-branch", default=DEFAULT_BASE_BRANCH, help="Base branch for PRs")
    args = parser.parse_args()

    run(
        args.history,
        args.state,
        args.codex,
        dry_run=args.dry_run,
        skip_git=args.skip_git,
        branch=args.branch,
        base_branch=args.base_branch,
    )
