# Onboard

Includes modified guidance from Impeccable. See [sources](SOURCES.md).

Design only enough first use to reach first value. Name the user's motivation, prior skill, available time, where they drop out, the first real success, and how it is measured. Teach the roughly 20% that yields 80% of value in context; design for action, not a presentation of features.

- Start in meaningful work. Ask for minimal account information, explain unusual requirements, and use truthful defaults, examples or templates. If setup needs an intro, say what will be accomplished and the honest time cost. Introduce one to three concepts and show actual progress such as **Step 1 of 3** when steps are real.
- Prefer a working example and first success over a mandatory tour. Give experienced users a visible skip, allow exploration, and do not gate the product unless a necessary prerequisite demands it. Celebrate effort proportionately and offer a useful next action.
- Put a contextual hint on a real element at the first useful moment. Dismiss it, remember dismissal, and make help recoverable. Announce newly released features only when they matter and lead directly to trying them. Introduce advanced features after need, not on entry.
- Use a tour for unusually complex workflows, major changes, or specialized skills. Keep it to about three to seven steps; spotlight the actual control, support forward/back, allow skip, make it replayable and keep focus coherent. Prefer using the real feature. Use a safe labeled practice space when the task is high stakes; provide objective, sample data, feedback and a clear end.
- Keep scoped task help and shortcuts discoverable without covering the workspace with instructions. Use an accessible tooltip/popover implementation when needed. Track seen, dismissal and progress by account and relevant onboarding version in the existing persistence layer; respect returning and shared-device users.

## Distinguish empty states

For first use, explain what will appear and why it matters, show a working next action or template, add a relevant visual and a route to contextual help when each earns its place. Keep a user-cleared view light and recreatable. A no-results state needs an editable query or clear filter action. A permissions state needs a path to request access if possible. Failed loading needs recovery, not onboarding.

Test with people new to the workflow and those who skip. Measure time to completion, comprehension, next real action, skip and drop-off, and time to first value. Use the result to cut rather than add ceremony. End with [polish](polish.md).
