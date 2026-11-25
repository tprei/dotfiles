# UX copy and clarify

Includes modified guidance from Impeccable and Anthropic. See [sources](SOURCES.md).

Read the entire path before editing strings. For each state decide the needed fact, next action, context that changes the decision, and tone appropriate to risk. Use the user's words rather than implementation terms. Write active verbs and sentence case. Establish one glossary and keep names stable across buttons, navigation, states, and announcements. Keep facts, price, legal meaning, and domain terms intact unless their owner changes them.

| Situation | What to write |
|---|---|
| Command | Name the result, such as **Save changes**, not the gesture or **Submit**. Keep the same verb in the result, such as **Published** after **Publish**. |
| Destructive action | Name the affected object and consequence. Prefer undo when reliable. If confirmation is necessary, name the action instead of using **Yes** or **OK**. |
| Form | Keep a visible persistent label and show real requirements before submit. Place an example in a placeholder, not the label. Explain why only if needed. Keep optional and required conventions consistent. |
| Error | Say what failed, why if known and useful, and what the person can do now. Name the correction near its field; preserve entries, announce the error, and keep unrelated work available. Do not guess a cause or expose code as the primary message. |
| Permission | Describe what is unavailable and who or what grants access, if known. Distinguish inability to see from inability to edit; do not label every immutable row. |
| Loading | Name a meaningful operation or delay; use measured progress and honest estimates only. Keep the rest of the interface useful. |
| Empty | Distinguish first-use, no results, filtered, cleared, no access, and failure. Offer the relevant next action, not the same **Get started** everywhere. |
| Success | Confirm the actual result. Mention the next consequence only when it changes what the user should do. |
| Help | Answer a real question at its point of need. Disclose uncommon detail on request; give links meaningful names out of context. |

Use utility headings in tools: **Last sync**, **Filter orders**, or **Plan status**. Lead with the table or working task, not a greeting, feature tour, build tooling, or campaign text. One short supporting sentence only if it adds scope, behavior, freshness, or decision value. In Persuade one section explains, proves, deepens, or converts; remove repeats until more cuts would remove meaning. Avoid filler, vague buzzwords, rebuttal cadence more than once per page, and technical slash labels. Separate independent metadata with layout; reserve punctuation for language, supplied names, and real relationships. See the [catalog](slop-catalog.md) for checks.

OpenAI's prompt guide discourages in-app explanations of features, keyboard shortcuts, styling, and operation; onboarding guidance allows contextual teaching. Keep routine chrome free of instructional commentary, but supply necessary labels, help at unusual decision points, discoverable shortcut reference, and [first-use guidance](onboard.md). Be plain and calm about payment, consent, deletion, blocked access, and data loss. Do not joke or add ritual apologies in place of recovery.

Localize whole messages, not concatenated fragments; keep variables re-orderable and plurals locale-aware. Check widths with long names and 200% zoom, number and date formatting, and the voice under stress. Use visible labels as the accessible name's basis; alt conveys the image's role, decorative images get empty alt, and status changes need usable announcements. No punctuation, icon, or color alone should carry essential meaning. Then [polish](polish.md).
