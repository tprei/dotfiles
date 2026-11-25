# Critique rubric

Includes modified guidance from Impeccable. See [sources](SOURCES.md).

Critique is a read-only design and usability judgment. [Audit](audit.md) is technical evidence, not a substitute. Resolve one stable target: prefer the source entry and name the render/state it serves. Work the primary path in a real or representative render, not only from source. Inspect actual wide and narrow views; sample three to five views only when the scope calls for multiple views.

## Keep judgment and signals independent

1. **Assessment A, design:** judge whether the same composition, behavior, and values could serve another product unchanged. Assess visual hierarchy, navigation, language, emotion, task path, accessible experience, states, and craft. Identify what the person sees first, where stress rises, what reassures them at consequential moments, and whether the strongest moment and ending leave the intended impression. Use the rubric and persona walks below.
2. **Assessment B, evidence:** independently inspect implementation and browser behavior; capture findings with locations, reproduction and false positives. Source cannot prove a layout or gesture; report which views were actually rendered. Use applicable project tools rather than inventing results. A native surface uses A and platform evidence, not a web detector.
3. When independent reviewers are available, keep A and B isolated until A has formed its verdict. For a shared desktop window, take turns and restore the original state. If working alone, do A first, lock its conclusions, then run B. Declare the method, any unavailable evidence, and why. Synthesize agreement, disagreements and blind spots rather than concatenating both lists. Do not rerun reliable collected evidence.

## Cognitive load

**Intrinsic** complexity belongs to the problem. Divide it into steps, group decisions, and provide examples or useful defaults. **Extraneous** load comes from jargon, hidden navigation, clutter, inconsistency, extra steps and context switching; remove it. **Germane** effort builds mastery; support it with consistent patterns, feedback and teaching by doing.

Score one failure for each question answered no:

1. Can the primary task proceed without a competing focus?
2. Are chunks typically at most four items?
3. Do visually grouped items share a genuine relationship?
4. Does the hierarchy put what matters first?
5. Can a user make one decision at a time?
6. Are there at most four visible choices at a decision point where practical?
7. Can users act without remembering data from earlier views?
8. Is complexity disclosed when needed instead of all up front?

**0–1** failures: low; **2–3**: moderate; **4+**: high. Use four simultaneous items as a working-memory design heuristic, not a biological limit. Group five to seven items; restructure eight or more. Ten ungrouped options is a clear red flag. Aim for one primary and one or two secondary actions, around five top-level nav items, four documentation siblings before grouping, and one decision at a time in a gallery. Show location, colocate evidence, keep relevant context on screen, and leave one primary element, two or three secondary, and the rest quiet.

## Nielsen heuristic scores

Score each applicable row from 0 to 4 with observed evidence. A 4 is excellent, not merely usable. Check the entire path, including failure and recovery.

| Heuristic | Inspect | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|---|
| 1. Status visibility | Feedback, loading, progress, location, validation | Guessing | Most actions silent | Key states missing | Minor feedback gaps | Timely confirmation and honest state throughout |
| 2. Match the real world | Familiar terms, mental model, meaningful icons, reading order | System jargon | Requires domain translation | Some plain language | Rare terms need context | Speaks the user's language and order throughout |
| 3. Control and freedom | Undo, cancel, back, escape, clear selections | Traps | Obscure exits | Main exits, bad edge cases | Most actions safely reversible | Clear exits, undo and recovery wherever appropriate |
| 4. Consistency and standards | Terms, visuals, gestures, control behavior and platform patterns | Disjoint | Similar actions diverge often | Main paths consistent | Small deviations | One predictable system |
| 5. Error prevention | Constraints, defaults, drafts, destructive safeguards | Easy mistakes | Few safeguards | Common mistakes caught | Proactively prevents most | Correct path is natural, mistakes hard to make |
| 6. Recognition over recall | Visible options, recent data, completion, cues and contextual help | Memorization required | Buried options | Main actions visible | Mostly discoverable | Information and actions discoverable when needed |
| 7. Flexibility and efficiency | Discoverable shortcuts, saved preferences, batch actions, expert paths | Rigid | Few alternatives | Basic accelerators | Useful accelerator paths | Multiple efficient paths without novice friction |
| 8. Aesthetic and minimalist | Relevance, hierarchy, purposeful color, focused composition | All competes | Clutter masks task | Clear core, noisy rim | Minor noise | All visible detail earns its place |
| 9. Error diagnosis and recovery | Plain, specific, nearby error, next action, preserved input | No or cryptic error | Generic text | Named problem but no next step | Clear fix for most failures | Precise, constructive and non-destructive recovery |
| 10. Help and documentation | Search, task focus, contextual entry, brevity | No help | Hidden or irrelevant | Basic reference | Searchable, task-oriented | Right help at the decision without losing context |

Maximum is four times the scored heuristics. Mark genuinely inapplicable rows with a reason, often #7 and #10 on Persuade/Experience; report the actual denominator (for example 24/32). For /40, bands are 36–40 excellent, 28–35 good, 20–27 acceptable, 12–19 poor, 0–11 critical. For other maxima, use ≥90%, ≥70%, ≥50%, ≥30%, then below 30%. Compare historical scores only with the denominator and method visible.

## Personas

Walk the primary job as two or three relevant personas. Add one or two from confirmed audiences if they expose different failures; never invent a customer's demographic. Report actual stumbling points.

| Persona | Try | Look for |
|---|---|---|
| Impatient expert | Finish the core job within about 60 seconds, skip teaching, batch edit, use shortcuts, escape dialogs. | Slow effects, forced tutorials, no batch path, repeated low-risk confirmations. |
| First-timer | Find the first action in five seconds, interpret labels literally, recover or get help. | Icon-only nav, unexplained terms, no obvious way back/forward, action silently succeeds. |
| Accessibility-dependent user | Walk keyboard only and with a screen reader, use 200% zoom, check 4.5:1 text and announced updates. | Traps, missing labels or focus, color-only state, hover-only or time-limited behavior. |
| Deliberate stress tester | Try 0 and 1,000 records, long/RTL/emoji input, paste, refresh, back and another tab. | Silent failure, lost input, broken promises, raw technical errors, blank empty states. |
| Distracted mobile user | Use one hand, a slow 3G test, realistic touch targets, tab switch and return. Use minimum typing. | Unreachable controls, lost progress, no autocomplete, small targets, unnecessarily heavy assets. |

Use expert and access on dashboards; first-timer and mobile on onboarding; first-timer, mobile and stress on landing/checkout; first-timer, access and mobile on multi-step forms. Adapt to the actual audience.

## Rank and report

| Severity | Meaning | Action |
|---|---|---|
| P0 | Blocks the task or loses critical work | Fix immediately |
| P1 | Serious difficulty, misleading state, or material accessibility/platform violation | Fix before release |
| P2 | Friction with a reasonable workaround | Fix in the next pass |
| P3 | Subtle polish without material user impact | Keep few and separate |

If a normal user would need to contact support because of the issue, it is usually at least P1. Lead with method and design-specificity verdict, then score, cognitive-load findings and emotional journey, two or three specific strengths and three to five priority issues. Give each severity, affected element and location, impact, concrete fix and relevant playbook. Add persona red flags, mechanical findings and false positives, minor notes, and evidence gaps. Deliver the report before archiving it. If interactive and three or more priorities remain, finish with two to four focused questions and two or three options each, tied to actual findings and scope. With fewer findings or a read-only/delegated run, state why questions were skipped. Recommend only needed, in-scope actions in priority order and end a fix plan with [polish](polish.md). Do not make the changes in a critique.
