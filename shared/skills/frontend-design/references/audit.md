# Technical audit

Includes modified guidance from Impeccable. See [sources](SOURCES.md).

Read-only. Review the specific surface's implementation, computed values, render and behavior. Separate confirmed defects from untested checks. Do not let a heuristic scan or resized screenshot stand in for an actual task path. Use [critique](critique-rubric.md) instead for design judgment. Score five appropriate dimensions from 0 to 4, giving one key finding per row.

## Web evidence

| Dimension | Checks |
|---|---|
| Accessibility | Correct DOM order, landmark and heading hierarchy, native role/label/state before ARIA, visible focus and full keyboard path, modal focus restoration, labeled fields, required indications and announced errors, illustrative alt and decorative empty alt, contrast through themes and interactions. Use [AA ratios](color.md#check-perception-and-contrast), test 200% zoom, reduced motion, flashing, forced colors, and a screen reader. |
| Performance | Profile startup, load waterfall, bottleneck frames, wasteful paints or effects, size and caching of media, dependencies, re-rendering and layout thrash. Confirm whether a measure represents real phones and networks. See [optimize](optimize.md). |
| Theming | Look for semantic token misuse, hard-coded values, inaccessible themes, incorrect remapping and live theme switches. Test the actual computed colors on overlays, charts, placeholders, and states. |
| Responsive design | Width, overflow, text wrapping/scaling and keyboard at real widths; structural reflow at content-driven thresholds. Test focus visibility under sticky UI, long or localized inputs, narrow and landscape mobile, and touch transitions. See [adapt](adapt.md). |
| Implementation integrity | Start the report here: pass or fail a coherent product-specific system. Verify drift, reused placeholders, misleading data, fake interactions, missing assets, and recurrent shortcuts against source and the rendered whole. Use the [catalog](slop-catalog.md) as signals, record false positives and confirm context. |

**Web touch targets:** design for 44×44 CSS px, stronger than WCAG 2.2 AA SC 2.5.8 (24×24 CSS px or a valid exception: spacing, equivalent control, inline, user-agent styling, or essential size). For the spacing exception, a 24 CSS px circle centered on the bounds must not intersect another target or another undersized target's circle. Report the guideline missed, not a WCAG failure where an exception applies. Test tap plus start-to-finish drag, scrolling across the control, new pointer, pointer cancel/lost capture and focus loss. Give the browser engine, physical device or synthesized method. Chromium mobile emulation does not test Safari.

**RTL:** check rendered direction before flagging physical CSS. On `dir="rtl"` pages, inspect wrong spacing, arrows or positioning and compare logical properties; a `lang` such as `ar`, `fa`, `ur`, `ps`, `ckb`, `he`, `yi`, `ug`, `sd`, or `dv` does not set direction. An RTL override must clear conflicting base properties. Preserve direction-agnostic physical centering such as `left:50%; transform:translateX(-50%)`; mixing logical and physical axes there breaks it. Flip only directional icons that need it. Reduce the responsive score by one for pervasive verified RTL problems.

**Desktop renderer:** check the real window at relevant resized sizes, zoom, and keyboard states. Use a test profile with the app's available renderer inspection and capture tools. A hidden/minimized window cannot establish pixel contrast. Say when native or embedded renderer behavior is not exposed.

## Native evidence

Use [native guidance](native.md) and device captures, not a browser detector. Judge each OS separately for adaptive products.

| Dimension | Checks |
|---|---|
| Accessibility | VoiceOver/TalkBack names, traits, announcements, focus/traversal, scales, Reduce Motion/Remove animations, theme contrast, 44 pt iOS or 48 dp Android targets and separation. |
| Performance | First frame and launch weight, 60/120 Hz scroll and gestures, main thread, unnecessary React Native renders or Compose recompositions, stable keys/recycling, full-size thumbnail decodes, caching and binary/JS size. |
| Appearance/theming | Semantic system colors or Material roles, dark and high contrast, native blur/materials or tonal elevation, Android Dynamic Color and its static scheme where relevant. |
| Platform conformance | Start with native vs ported verdict backed by specifics: real back gestures, insets, expected navigation/controls, system icons, and reuse of product primitives. |
| Adaptivity | Phone and tablets by size class, landscape/portrait, keyboard/IME, split views/multi-window, hinge and posture where shipped; do not accept a scaled-up phone UI. |

## Score and deliver

Use **0** for absent or functionally broken, **1** for pervasive major gaps, **2** for partial coverage with material failures, **3** for sound coverage with isolated defects, **4** for comprehensive verified behavior. For example, unusable keyboard or screen reader = 0, labels but broken focus/scaling = 2, fully working applicable AA = 4; native conformance at 1 has three or four types of violations, at 2 one or two prominent types. Mark unavailable evidence rather than awarding 4. Total /20: **18–20** excellent, **14–17** good, **10–13** acceptable, **6–9** poor, **0–5** critical.

Give the integrity/conformance verdict, five dimension rows, score/band, counts by [P0–P3](critique-rubric.md#rank-and-report), top three to five issues, systemic patterns, and practices to keep. For each issue state location and reproduction, affected users and consequence, applicable standard or guideline, proposed fix and matching playbook. Make the recommended order impact-first, end with [polish](polish.md) if fixes are needed, and label anything not corroborated. Do not inflate minor issues or claim absence of defects from unavailable tools.
