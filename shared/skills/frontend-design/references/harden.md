# Harden

Includes modified guidance from Impeccable. See [sources](SOURCES.md).

Treat unusual data, interrupted gestures, localization, and network failure as real use. Inventory limits and recovery per flow. Run representative extremes before editing rather than defensively wrapping every in-process value.

## Content and language

- Test empty, one character, 100+ character names, unbroken URLs, pasted lists, duplicates, millions/billions, 50+ options, and 1,000+ records. Prefer wrapping, flexible tracks and `min-inline-size: 0` to clipping. Use `overflow-wrap` and correct-language hyphenation when helpful. Reserve one-line ellipsis or a three-line clamp for a deliberate summary with reachable full content; keep disambiguation visible. Test 200% zoom and the 16px mobile body/input floor.
- Budget 30–40% extra space for translations; German often needs around 30% more. Let boxes grow and verify long locale, CJK, Arabic/Hebrew, Cyrillic, emoji/grapheme clusters and UTF-8. Translate whole messages using locale-aware plural rules, dates, times, numbers, money, and timezone. Use `Intl` or the project's equivalent. `fa-IR` can use Persian digits and Solar Hijri dates; use the appropriate Arabic locale/calendar such as `ar-SA-u-ca-islamic` where required, not an assumed universal date form.
- Mark interface direction with `dir`; use logical properties where direction changes the intent and isolate user-entered bidi text. Mirror navigational arrows only when semantics require it. Preserve U+200C (ZWNJ) in scripts that need it. Preserve original Arabic/Persian Yeh and Kaf in storage; where the locale expects it, compare equivalent forms in search or validation rather than rejecting input from another keyboard.

## Fail and recover without losing work

| Situation | Behavior |
|---|---|
| Initial, pagination or refresh loading | Preserve layout with a useful stable placeholder, keep prior usable content for refresh, and give measured progress only when known. |
| Empty, filtered, partial, stale | Distinguish the cases and show the relevant action. Keep partial errors local and label missing data rather than showing zero. |
| Offline, slow or timed out | Keep working content, explain the failed operation, allow explicit recovery or offline work when supported, and never fake success. |
| Request and permission errors | Map validation, authentication (401), forbidden (403), missing (404), rate limit (429), and server failure (5xx) to distinct useful states. Do not surface raw infrastructure errors as copy. |
| Forms | State constraints before submit. Use appropriate semantic input, hints, and inline validation; keep values and focus or restore them. Client checks are UX, not a substitute for server validation at the process boundary. |
| Concurrent actions | Prevent duplicate submission, define which response is current, handle races and conflicts, and roll back optimistic treatment with an honest status if needed. |
| Interrupted work | Preserve drafts and meaningful position across back, close, refresh, or tab switch, or warn when loss is possible. Allow undo for reversible destructive actions. |

## Interaction and runtime resilience

Use native controls, semantic HTML, focus restoration on dismissal, logical tab order, skip links for long paths, labels and usable live updates. Test forced colors, screen reader, and operation without hover. Keep menus outside clipping ancestors and keep the point of focus visible with any on-screen keyboard. Make critical rendered content readable without optional scripts. Feature-detect enhancements and keep the functional baseline coherent on supported browsers.

For drag surfaces, set a deliberate `touch-action` that preserves perpendicular scrolling. Track the originating pointer; a second finger does not take it over. Clear state on cancel, lost capture, release outside, and blur. Confirm the next swipe works. For long lists, use search, pagination or measured virtualization, not 10,000 rows in the DOM. Clean up subscriptions, listeners, timers, and pending work when removed. Use measured debounce or throttle when it makes input and scroll responsive, not as a shortcut around slow rendering.

## Verify a stress matrix

Exercise translations and long inputs, first use and empty, all material error codes, refresh mid-flow and tab switch, offline and slow 3G, dataset volume, and ten rapid attempts at the same action. Try touch drag and scrolling, cancellation, another pointer and the next fresh attempt. Record viewport, engine, pointer synthesis or actual device; screenshots only prove layout. Use scoped unit, integration, E2E, gesture regression, visual and accessibility checks when supported. Fix a reusable cause instead of widening local guards. End with [polish](polish.md).
