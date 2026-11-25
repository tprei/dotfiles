# Adapt to context

Includes modified guidance from Impeccable. See [sources](SOURCES.md).

Name the old and new screen, posture, task, input, connection, orientation and platform expectations. Note what scales, what needs restructuring, and what must stay recognizable. Width is not input mode; detect pointer/hover support without removing functions from people with either input. Read [native](native.md) for native navigation, units, insets and device classes.

| Context | Restructure |
|---|---|
| Phone | Stack meaningful regions, prioritize one working action within thumb reach, expose back/context, use progressive disclosure for secondary detail. Prefer a clear inline control; use a sheet only when context or focus warrants it. Keep full capability, useful touch feedback and 44×44 CSS px hit areas. |
| Tablet | Try workspace plus context or list plus detail. Adapt portrait and landscape, with touch spacing and pointer/keyboard support. A tablet window may be as narrow as a phone. |
| Desktop | Use width for comparison, visible navigation, stable side panels and expert actions like shortcuts, batch selection or context menus where useful. Cap reading width on 4K; keep keyboard and touch paths. |
| Print or static export | Remove interactive chrome, page-break between meaningful groups, leave binding margins, show otherwise hidden required content and meaningful URLs. Provide titles, numbering, creation dates, units and print-friendly charts. Inspect printed size and monochrome. |
| Email | Use a single column up to about 600px, inline CSS, compatible table-based presentation when needed, clear buttons without hover and durable links to the working app. |
| Terminal | Test minimum columns and rows, sensible wrapping or horizontal movement for required comparison, monochrome and actual terminal color palettes, keyboard paths and selectable plain output. Use width-aware grapheme measurement for CJK and emoji content. Do not emit decorative sparkle, motion or arbitrary glyphs. |

Start with narrow styles and add structure as content needs room. Treat 320–767px, 768–1023px and 1024px+ as sample ranges, not device taxonomy. Common starting test widths include 320, 390, 640, 768 and 1024px, intermediate widths, desktop and 4K. Choose breakpoints when content actually breaks. Use grid/flex reflow, container queries, intrinsic sizes and bounded fluid spacing. Do not use hidden downloaded duplicates or a separate mobile architecture. Use `srcset` width descriptors and accurate `sizes` for resolution, `<picture>` for art-directed crops. Keep the same information architecture as layout changes.

For mobile web with edge-to-edge rendering, include `viewport-fit=cover` and account for every `env(safe-area-inset-*)` without removing base padding, for example `max(1rem, env(safe-area-inset-bottom))`. Use `svh` for a stable initial view, `dvh` for layout that follows dynamic chrome, and observe the visual viewport where the OS keyboard requires scroll/position correction. Test that fields and focused actions remain visible when the keyboard opens; browser chrome and IME size are not implied by `dvh`. Never disable zoom. Verify fixed/sticky UI cannot obscure content, including height-starved landscape.

## Exercise input, not only viewport sizes

Check the actual supported mobile browsers and engines, including Safari on a real iPhone and Chromium on Android where shipped. Check touch and keyboard, landscape and split windows, a relevant tablet, and throttled network. Do not rely on hover or gestures alone. Drag each custom slider to completion, swipe across it on the page's scroll axis without activating it, interrupt it, and try again. Follow [harden](harden.md) for gesture cancellation. For evidence specify resize, synthesized touch and engine, or physical device. These establish different things. Report unsupported or untested contexts, then [polish](polish.md).
