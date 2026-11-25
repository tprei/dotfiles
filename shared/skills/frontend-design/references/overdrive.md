# Overdrive

Includes modified guidance from Impeccable. See [sources](SOURCES.md).

Take one existing capability past its usual craft limit. Identify whether the payoff is sensory composition, interaction continuity, scale, responsiveness, or data fluidity. A virtualized 100,000-row table that stays responsive or a form that validates without interrupting focus may be more ambitious than a shader. An overdrive request is not permission for new backend behavior.

## Propose before implementation

Offer two or three meaningfully different directions with the payoff and the cost in support, complexity and runtime. Ask for the pick when the direction is materially open and the user is available. If scope, technique and payoff are already pinned, honor them. Fix fundamentals before adding spectacle.

| Job | Consider |
|---|---|
| Spatial continuity | View Transitions, shared layout, or FLIP. For CSS entry transitions use `@starting-style` where supported. For material physics use a bounded spring with appropriate damping, not a gratuitous bounce. |
| Scroll narrative | Scroll-driven timelines or sticky progression, only if the scroll relationship carries meaning. Keep a complete static experience for unsupported browsers and reduced motion. |
| 2D, 3D, material | SVG filters for intentional distortion, Canvas 2D for too many drawable elements, Three.js or another existing WebGL renderer for real 3D, WebGPU only where adapter acquisition and runtime support are verified. Keep an accessible baseline and a WebGL2 alternative if WebGPU is optional. |
| Massive data | Virtual rows, Canvas/WebGL plots, stable keys and transitions that maintain orientation. Show meaningful frame-to-frame changes and keep exact values accessible. |
| Intensive computation | Move heavy calculations to Workers where justified; move rendering to OffscreenCanvas when supported; consider WASM for computational kernels, not ordinary rendering. |
| Sequencing | Use registered `@property` for custom interpolated values, Web Animations API for cancellation/reversal, or the existing library. Verify actual browser support for the intended operation, not a general support claim. |
| Device input | Use audio, orientation or sensor input only with permission and a clear purpose. Sound must have explicit opt-in and a user gesture; features remain usable without it. |

## Verify the payoff

Progressively enhance: feature detection alone cannot prove a GPU adapter is available. Initialize heavyweight modules/contexts near use, pause rendering offscreen or hidden, and measure mid-range hardware. Aim for 60 fps and roughly 16 ms/frame; simplify if sustained performance drops under 50 fps. Give games usable controls first; use a proven existing library for well-understood engines unless from-scratch is required. For an immersive scene, keep the canvas unframed, inspect its actual pixels at desktop and mobile, exercise interaction and movement, and verify loading, framing, asset presence and non-overlap. A blank or static screenshot cannot establish an interactive result.

Use the wow test with someone new, the removal test, the hardware test (phone/tablet/low-powered laptop), and the specific-context test. One extraordinary moment is enough. Use [motion](motion.md) and [optimize](optimize.md) for measured checks, then [polish](polish.md).
