# Motion and animate

Includes modified guidance from Impeccable and Anthropic. See [sources](SOURCES.md).

Inspect existing transitions, real input paths, devices, and budgets. Before coding name the focal moment, if any, continuity to preserve, feedback needed, and cost of expensive effects. Animate a meaningful change: causality, state, spatial continuity, or a narrative beat. Product and reading tasks should not wait for choreography. On expressive work OpenAI asks for two to three intentional motions such as entry, scroll-linked depth, and interaction feedback; Impeccable asks for one authored focal moment. Use one lead sequence and add only quieter state cues that earn their place. Do not make the number of animations a target.

| Duration | Job |
|---|---|
| 100–150 ms | Immediate press or confirmation feedback |
| 150–300 ms | Routine state change; usually 150–250 ms for product UI |
| 300–500 ms | Overlay, layout, or view continuity |
| 500–800 ms | Deliberately authored focal entrance on an expressive surface |

Use duration proportional to distance and consequence. Exit faster than entrance. Use natural deceleration, such as `cubic-bezier(0.16, 1, 0.3, 1)`, ease-out quart/quint/exponential. Avoid bounce, elastic, marquee and fake cursor effects as decorative defaults; literal physical behavior can warrant appropriate physics. If staggering siblings helps people see a list as a unit, cap total delay. Keep content visible at rest; never make entrance failure blank a section.

## Choose a technique by meaning

- For a relationship, use shared elements, FLIP, or View Transitions; for feedback, use the smallest tone, opacity, or position change that reads. For directed reveal use a crop, mask or clip. A bounded blur, backdrop, or neutral shadow can show focus or depth; relevant colors, texture, or shader changes can express material. Do not stack properties for spectacle.
- Use CSS for routine state, Web Animations API or the existing motion library for cancellation and sequencing, and support-gated scroll-linked motion only when the scroll relationship matters. Keep expensive paint small and isolated. Avoid routine animation of layout-driving `width`, `height`, offsets, and margins. Apply `will-change` only for observed need during animation; measure before assuming compositing helps.
- Keep hover hit areas still; animate an inner child, never something that moves its neighbors or escapes the pointer. For preview, delay entry until dwell and dismiss immediately. Touch and keyboard users need equivalent actions and feedback. Avoid autoplay sound; pause nonessential loops offscreen or when hidden and provide controls where applicable.
- Honor `prefers-reduced-motion` and native preferences. Remove or shrink travel, zoom and parallax; preserve outcome with color, opacity, or an instant state that remains legible. A globally shortened animation is not a meaningful alternative, and the same long travel in fewer milliseconds is worse. Do not flash more than three times in a second unless below the applicable WCAG flash thresholds.

## Look at the transition, not just the end

Drive entry and exit independently with keyboard, pointer, and touch where shipped. Capture before, first, middle, last animated, and settled frames of the same interaction in normal and reduced motion. Inspect filmstrip or recording and measured timing; prove view, target, and state are correct. Check first-frame jumps, content swaps, occlusion, clipping, interruption and reversals, rapid repeat, focus order, and neighbors moving. Try mid-range devices and narrow viewports. The reduced path must carry the same meaning with materially less movement. Use fresh eyes when available; bad captures require recapture, real findings a grouped fix and same-evidence comparison. Report remaining limits, not a claim of smoothness based on a still. See [overdrive](overdrive.md) for advanced techniques and [optimize](optimize.md) for frame budgets.

For shared transitions, compare the actual painted layers, not the underlying new DOM. Look for entrance replay on already-present content, a dark or bright dip where old and new overlap, orphaned content lingering beyond the surrounding motion, a z-order swap when transition layers retire, and shadows jumping at the start or end. If opacity values are measured, repeated samples whose sum falls outside 0.95–1.05 warrant inspection. Complementary opacities still do not establish correct compositing; judge brightness and legibility from the frames.
