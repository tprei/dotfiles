# Shape and new work

Includes modified guidance from Impeccable and Anthropic. See [sources](SOURCES.md).

## Shape the job before the look

`shape` returns a design brief, not code. Use one round of two or three related questions for a sparse brief; add a second only if an answer changes the work materially. Assert the likely reading rather than asking for facts already available. For a precise brief, confirm the interpretation in the plan; if you cannot ask, mark assumptions. Do not ask users to pick CSS values or canned aesthetics.

- Purpose: who arrives, in what situation and state of mind, for which job, and what outcome proves success? Name the product's distinctive mechanism in one sentence.
- Material: use real content, proof, and assets. Name minimum, typical, and maximum inputs; first use, empty, loading, error, success, permissions, and expert use where material.
- Boundaries: name the target, fidelity, supported contexts, interactivity, non-goals, untouched behavior, and what would feel wrong even if polished. Include localization, accessibility, performance, platform, and delivery limits.
- Return the chosen structure, first viewport, path, feedback, responsive changes, states, and any decision a builder must not invent. Use three to five bullets when settled. Seek confirmation for a planning-only `shape` and stop without implementation. For delegated work, return the assumptions with the brief.

## Determine visual authority

Read the product notes, design system, representative screens, source, tokens, shared controls, and assets. Preserve an established identity even when no `DESIGN.md` exists. A confirmed seed or approved direction is authority even before code exists; incidental starter CSS is not. Extend an incomplete system from its confirmed traits. For a redesign, preserve product facts, content, behavior, constraints, and named commitments; replace the old aesthetic rather than polishing it halfway. For a local addition, inherit both the surrounding composition and its identity.

## Explore without spending the user's time

- **One new surface, existing identity:** for materially open work, derive five to seven structures from the content and user path. Compare three distinct options that vary what leads, topology, density, sequencing, or interaction. Keep the same world; leave trivial additions out of this exercise.
- **New identity or redesign:** name the category default and its obvious opposite. Find seven resonant systems, objects, places, or rituals in the audience's actual culture. Span at least three material families, with no more than three from the same one. Include printed and screen traditions, historical and physical forms. Limit the literal brief metaphor to one candidate; for Operate and Read, do not dress a working screen as a tool its users operate. For Persuade and Experience, treat that as at most one candidate.
- Pair a reusable visual language with one concrete opening and interaction in every option. Compare on audience recognition and product clarity; test truth, assets, and performance before offering a direction. Include challengers unlike the first impulse. Borrow their discipline, such as a strong grid or decisive coverage, not their motifs, faces, or chrome. If a challenger wins both axes, change the recommendation; if it wins one, keep it as a real alternative; if neither, name what improved the winner and demote it.
- Recommend one coherent direction. Give an honest risk and one line per credible alternative, not a catalog. When presenting a major visual decision, keep the conventional option available without softening the distinct option. If the user chooses convention, name two or three benchmark peers and meet their craft level without adding ironic quirks. If two materially different rounds miss, ask what quality is missing instead of recycling directions.
- An explicit brief pins only the axes it names. A reference sets a quality bar unless the user adopts it as a direction. Do not present alternate visual identities for a direction pinned in full; solve remaining layout and behavior in that world.

## Record the direction before code

Write 4 to 6 named color values with roles; one or two named faces with weights, roles, and scale; an ASCII layout sketch with alignment and a narrow/wide change; the content order and one memorable move. Note the real alternative and why the chosen answer fits. Compare against a generic answer for the same category and for a neighboring brief. Revise any unpinned choice that survives unchanged without a reason. Name the changes and why. Calibrate against the common cream/serif/clay look, acid-on-black, editorial hairlines with tiny tracked mono, boxed neobrutalism, and SaaS card kit. The reflex opposite is still a reflex. A promise of calm behavior does not require a beige surface.

For substantial work, keep a development-only direction contract, about 150 words: thesis and refused default; reusable world and material logic; visitor story; exact first viewport and primary action; named form and signature interaction; finish conditions. Record approved comp or sketch and boundaries. Keep this out of page copy, source comments shipped to the browser, DOM, metadata, serialized state, and bundles. Keep durable product facts and visual rules separate from the surface brief. See [design systems](design-systems.md).

## Carry it through the build

Choose a code-led path for most working interfaces and documents. Use approved comps for expressive work or when supplied; audit a code-led build against the chosen sketch and recorded behavior, not a new imaginary comp. Translate the world into the structure it can own in [the chosen mode](modes.md), not an accent sticker on a template. Make the opening do the work the brief promises; ask what somebody would describe an hour later. Show enough of the real mechanism to earn trust. Pace the subsequent content with denser and quieter groups, end with a real close, and keep accessibility and function intact. Follow [comp and asset guidance](imagery-and-comps.md) where relevant, then the [pre-ship pass](pre-ship.md).

## Compare refinements on distinct axes

When asked for variants within an identity, note its actual surface and accent, type voice, topology, corners and depth, density and copy tone. Use three comparable designs on distinct primary axes: hierarchy, topology, type roles, which existing color role leads, density, or how content groups. A narrow request still constrains every option: three genuinely different layout arrangements beat three gap tweaks; three motion variants should express different relationships. Compare from thumbnail distance and remove near-duplicates. If redesign is explicit, derive different material families from the product instead, then compare descriptions side by side for interchangeable rationale. Keep trials disposable; ship only the selected design in its real components.
