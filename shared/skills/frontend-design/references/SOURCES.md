# Sources and notices

This skill rewrites and combines the upstream material below. The design guidance is modified, not a verbatim mirror. New material includes chart choice and table/freshness guidance, generated reports, terminal interfaces, and synthesis across sources.

| Source | License | Adaptation |
|---|---|---|
| Paul Bakaus, [Impeccable skill and complete reference tree](https://github.com/pbakaus/impeccable/tree/9e460a87ef338ee9d12c7beed8fedc597a5af5f7/.agent/skills/impeccable) | [Apache License 2.0](https://github.com/pbakaus/impeccable/blob/9e460a87ef338ee9d12c7beed8fedc597a5af5f7/LICENSE), Copyright 2025 Paul Bakaus | Modified craft floor, mode distinctions, new-work and comp process, design-system guidance, native and web audits, complete critique method, and refine/enhance/fix playbooks. |
| Paul Bakaus, [Impeccable slop catalog](https://impeccable.style/slop) | Impeccable rules: [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) | Paraphrased 62 detector rules plus the six named design-review patterns. No website artwork or example screenshots are redistributed. |
| Anthropic, [Frontend Design skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) and [official Claude plugin copy](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md) | [Apache License 2.0](https://github.com/anthropics/skills/blob/main/skills/frontend-design/LICENSE.txt) | Both files and their license texts matched. Adapted subject-grounded choices, 4–6 named colors, ASCII sketch, review against generic defaults, single focal move, and practical UX writing. |
| OpenAI, [Designing delightful frontends with GPT-5.4](https://developers.openai.com/blog/designing-delightful-frontends-with-gpt-5-4) | No separate open license stated on the article; see [OpenAI terms](https://openai.com/policies/terms-of-use/) | Paraphrased design principles and embedded skill hard rules, including first-viewport budget, full bleed, brand hierarchy, visual anchor, utility copy, motion, and browser verification. |
| OpenAI, [Frontend prompt guide](https://developers.openai.com/api/docs/guides/frontend-prompt) | No separate open license stated on the guide; see [OpenAI terms](https://openai.com/policies/terms-of-use/) | Paraphrased task-specific UI, domain and system awareness, native control choices, type guidance, stable dimensions, media, and verifying interactive/canvas surfaces. |
| Howon Lee, [frontend-slop-guard](https://github.com/airtaxi/frontend-slop-guard/tree/7bbcd0a6402e063d0aaf18a496a871c23aa28cdd) | [MIT](https://github.com/airtaxi/frontend-slop-guard/blob/7bbcd0a6402e063d0aaf18a496a871c23aa28cdd/LICENSE) | Adapted 19 tells, self-checks, review mode and pre-ship checks. Read its [annotated examples](https://github.com/airtaxi/frontend-slop-guard/blob/7bbcd0a6402e063d0aaf18a496a871c23aa28cdd/references/examples.md) and [source mappings](https://github.com/airtaxi/frontend-slop-guard/blob/7bbcd0a6402e063d0aaf18a496a871c23aa28cdd/references/source-impeccable.md); original article: Pranav Desai (hereticpleb), [10 tells of a slop ui](https://hereticpleb.vercel.app/blog/10-tells-of-slop), no separate license stated in the cited copy. No article prose or screenshots reproduced. |

## Apache 2.0 redistribution notice

The adapted Impeccable material is modified. Keep its attribution and a copy of [Apache License 2.0](LICENSE-Apache-2.0.txt) with redistribution. Section 4 requires a prominent modification notice in changed files, retention of relevant source notices, and a readable copy of applicable attribution from the upstream [NOTICE](https://github.com/pbakaus/impeccable/blob/9e460a87ef338ee9d12c7beed8fedc597a5af5f7/NOTICE.md). The relevant notice is the platform material: Impeccable's iOS and Android references were distilled from [ehmo's platform-design-skills](https://github.com/ehmo/platform-design-skills), MIT, author ehmo, covering the Apple Human Interface Guidelines and Material Design 3. The font notices and DuckDuckGo consent notice do not apply; this skill includes none of those assets or code.

## MIT notice for frontend-slop-guard

Copyright (c) 2026 Howon Lee

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## How differences are resolved

| Question | Source positions and choice here |
|---|---|
| Atmosphere | The OpenAI blog favors image, pattern, or gradient over flat branded hero backgrounds. Its prompt guide rejects gradient/SVG hero substitutes and decorative orbs. Slop guard recommends one gradient but its checklist flags more than three. Use a relevant visual, a maximum of one justified focal gradient, and no decorative glow or gradient text. See [color](color.md). |
| First viewport | OpenAI defaults to an image-led full-bleed landing hero. Impeccable and Anthropic let the best subject-specific proof take the lead. Use full bleed for an image-led brief, but a working task, real artifact, or interactive scene can be a stronger anchor. Preserve an incumbent system. See [modes](modes.md). |
| Fonts and sizing | OpenAI and Anthropic advise against reflexive default stacks; Slop Guard and Impeccable also recognize deliberate platform and workhorse faces. OpenAI's prompt guide says no viewport-scaled type or negative tracking; Impeccable permits measured display exceptions. Use stable routine roles, native text sizing, and justified brand display exceptions only. See [typography](typography.md). |
| Motion | OpenAI suggests two to three intentional motions for visual work; Impeccable concentrates expression in one authored moment. Build one focal sequence, quiet supporting feedback only when useful, and a meaningful reduced-motion path. See [motion](motion.md). |
| Copy and help | OpenAI's prompt guide excludes routine in-app feature and shortcut exposition; Impeccable promotes contextual help and first value. Omit explanatory filler, retain useful point-of-need help. See [UX copy](ux-copy.md) and [onboarding](onboard.md). |
| Imagery acquisition | OpenAI's blog favors supplied or generated assets, not linking to web images unless requested. Its guide and Impeccable allow finding relevant actual imagery. Prefer supplied, approved, and licensed sources; do not substitute generic media or falsify evidence. See [imagery](imagery-and-comps.md). |

## Deliberate omissions

Omit upstream-specific launcher, installation, account and telemetry behavior, concept-roll software, screenshot/build-phase commands and thresholds specific to those engines, browser overlays, detector hooks and waivers, pins, doctor, image-generation plumbing, live-mode event and preview machinery, and report/sidecar storage protocols. Retain the underlying creative decisions, composition and asset review, evidence isolation, and finish criteria without requiring upstream tooling. Do not import general repo-maintenance tasks such as migration checks and CI setup into a visual design skill. Link visual examples instead of vendoring them, and do not prescribe the OpenAI article's model, reasoning setting, or sample stack.
