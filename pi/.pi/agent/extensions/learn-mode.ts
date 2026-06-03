/**
 * Learn Mode Extension for pi
 *
 * Tutors the user through a topic without giving direct answers, copyable
 * implementations, or complete command sequences. Removes useless friction
 * but does not replace the user's thinking.
 *
 * Usage:
 *   /learn              Enter learn mode
 *   /learn-off          Exit learn mode
 *   /learn-status       Check if learn mode is active
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";

const LEARN_MODE_PROMPT = `
# Learn Mode (ACTIVE)

You are tutoring the user. Preserve the learning process — remove useless friction, but do not replace the user's thinking.

## Instructions

1. Announce: "Learn mode is active."
2. Restate the learning target in one sentence.
3. Ask a focused diagnostic question or propose the smallest experiment.
4. Wait for the user's attempt, prediction, or observation.
5. Give feedback and the next hint.
6. If the user is stuck twice at the same point, reveal one narrow concept or line shape, not the whole solution.

## Provide

- Mental models, vocabulary, and relevant APIs.
- The next file, command, doc, or search term to inspect.
- Hints in increasing specificity.
- Review of the user's attempt with the smallest correction.
- Error interpretation that asks the user to predict the fix.
- Tiny non-copyable pseudocode only when words are too vague.

## Withhold

- Final answers.
- Drop-in snippets.
- End-to-end implementation plans.
- Exact finished command sequences.
- Large examples that can be copied with minor edits.

## Exit hatch

The user can exit learn mode by typing /learn-off. Until then, keep withholding.
`;

const ALLOWED_BASH_PREFIXES = [
  "rg ", "fd ", "bat ", "ls ", "head ", "tail ", "wc ", "file ", "stat ",
  "which ", "where ", "type ", "echo ", "pwd ", "tree ", "cat ",
  "find ", "git log ", "git diff ", "git show ", "git branch ", "git status ",
  "git stash list", "node -e ", "python3 -c ", "python -c ",
];

function isAllowedBash(command: string): boolean {
  const trimmed = command.trimStart();
  return ALLOWED_BASH_PREFIXES.some((prefix) => trimmed.startsWith(prefix));
}

export default function learnMode(pi: ExtensionAPI) {
  let active = false;

  // Restore state from session on reload
  pi.on("session_start", async (_event, ctx) => {
    for (const entry of ctx.sessionManager.getEntries()) {
      if (entry.type === "custom" && entry.customType === "learn-mode-state") {
        active = entry.data?.active === true;
        if (active) {
          ctx.ui.setStatus("learn-mode", "LEARN MODE");
        }
        return;
      }
    }
  });

  // Save state
  function persistState() {
    pi.appendEntry("learn-mode-state", { active });
  }

  // Toggle learn mode on
  pi.registerCommand("learn", {
    description: "Enter learn mode — tutoring without direct answers",
    handler: async (_args, ctx) => {
      if (active) {
        ctx.ui.notify("Learn mode is already active.", "info");
        return;
      }
      active = true;
      persistState();
      ctx.ui.setStatus("learn-mode", "LEARN MODE");
      ctx.ui.notify("Learn mode activated. I'll tutor, not spoon-feed.", "info");
      pi.sendUserMessage("I want to learn. Guide me, don't give me the answer.");
    },
  });

  // Toggle learn mode off
  pi.registerCommand("learn-off", {
    description: "Exit learn mode — answer normally again",
    handler: async (_args, ctx) => {
      if (!active) {
        ctx.ui.notify("Learn mode is not active.", "info");
        return;
      }
      active = false;
      persistState();
      ctx.ui.setStatus("learn-mode", "");
      ctx.ui.notify("Learn mode deactivated. Back to normal mode.", "info");
    },
  });

  // Check status
  pi.registerCommand("learn-status", {
    description: "Check if learn mode is active",
    handler: async (_args, ctx) => {
      ctx.ui.notify(`Learn mode: ${active ? "ACTIVE" : "inactive"}`, active ? "info" : "warning");
    },
  });

  // Inject learn-mode system prompt when active
  pi.on("before_agent_start", async (event) => {
    if (!active) return;

    return {
      systemPrompt: event.systemPrompt + "\n" + LEARN_MODE_PROMPT,
    };
  });

  // Block write operations in learn mode
  pi.on("tool_call", async (event) => {
    if (!active) return;

    if (event.toolName === "write" || event.toolName === "edit") {
      return {
        block: true,
        reason: "Learn mode is active. Guide the user to make this change themselves.",
      };
    }

    if (isToolCallEventType("bash", event)) {
      if (!isAllowedBash(event.input.command)) {
        return {
          block: true,
          reason: "Learn mode is active. Only read-only commands allowed — guide the user instead.",
        };
      }
    }
  });

  // Clean up on shutdown
  pi.on("session_shutdown", async (_event, ctx) => {
    ctx.ui.setStatus("learn-mode", "");
  });
}
