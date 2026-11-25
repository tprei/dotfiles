# Optimize

Includes modified guidance from Impeccable. See [sources](SOURCES.md).

Name the slow path and affected device/connection. Capture a scoped before-and-after measure of the actual bottleneck: waterfall and bytes, first contentful paint (FCP), total blocking time (TBT), interaction latency, layouts and paint, CPU, memory, render counts, or frame time. Do not optimize a guessed bottleneck. Prefer real-user 75th percentile data when available; lab profiles help diagnose causes, not replace field evidence. Compare like for like.

| Signal | Target | Common causes and corrections |
|---|---|---|
| Largest Contentful Paint (LCP) | ~2.5 s or faster | Keep the hero asset discoverable and correctly sized, only preload true critical resources, reduce blocking styles or scripts, and render initial content on the server where the project supports it. Never lazy-load the focal above-fold image. |
| Interaction to Next Paint (INP) | ~200 ms or faster | Break up long tasks, reduce work in interaction paths, profile unnecessary renders, and move heavy computations off the main thread where justified. |
| Cumulative Layout Shift (CLS) | ~0.1 or lower | Reserve media and embed space (`width`/`height` or `aspect-ratio`), match font metrics, and avoid injecting late content above a reader or changing tracks when controls load. |
| Smooth motion | ~16 ms/frame at 60 Hz, ~8.3 ms at 120 Hz | Batch layout reads then writes, isolate and bound expensive paint, prefer transform and opacity, use the runtime's frame scheduler, and avoid broad permanent `will-change`. |

## Reduce what the interface has to do

- **Media:** use right-size variants and crops, WebP/AVIF where appropriate, and lazy-load below the fold. Approximate 80–85% quality is a compression starting point; inspect subject detail, color and texture before accepting. Do not send a 3000px image for a 300px role unless pixel density warrants it. Use CDN/cache only where the project already supports the architecture.
- **Assets:** subset only unused scripts/glyphs, keep fallbacks metrics-compatible, use WOFF2, load necessary weights only, and preload only the face needed immediately. Split heavy noncritical code by actual use, eliminate dead dependencies, tree-shake, and defer non-blocking work. Remove unused CSS rather than duplicating it into a critical chunk.
- **Runtime:** reduce DOM depth and independent work; profile containment and `content-visibility: auto` before adoption; preserve focus, search, and landmarks. Virtualize genuinely large lists with tested keyboard, scroll, and selection. Do not do synchronous aggregation during typing and gestures; consider Workers and appropriate thresholds for expensive work. Use frame pacing and stop animations offscreen. Observer-based visibility work helps avoid continuous scroll reads.
- **Framework:** follow repository/compiler conventions. Impeccable suggests memoization for expensive React components; OpenAI cautions against blanket `memo`, `useMemo`, and `useCallback`. Profile first; use them only where they change measured work and the compiler does not already handle it. Consider `startTransition`, `useDeferredValue`, or `useEffectEvent` only when the current stack uses and benefits from the corresponding scheduling/effect semantics.
- **Network:** prioritize critical requests, avoid extra origins and unused third-party scripts, compress responses, cache versioned assets, and request only the data needed. Page large results; avoid prefetch that competes with primary load. Where supported, use service worker caching/offline behavior and truthful optimistic UI rather than fake loading or optimistic completion without recovery.

## Confirm improvements

Measure the same target on a low or mid-range phone, constrained network such as 3G where appropriate, and the real browser/refresh rates. Use performance tracks, Web Vitals, a bundle analyzer or product monitoring as available. Include request count and bytes where they explain the result. Verify functional, accessibility and content parity, loading and interruption, and whether it visibly feels faster. Avoid device- or browser-wide changes to fix one local issue. End with [polish](polish.md).
