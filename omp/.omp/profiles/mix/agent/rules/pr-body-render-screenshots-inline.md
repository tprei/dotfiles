---
name: pr-body-render-screenshots-inline
description: "Embed screenshots as inline markdown images in the PR body; never link a gist as the evidence"
condition: ["gist\\.github\\.com", "gh\\s+gist\\s+create"]
scope: ["tool:write(*.md)", "tool:bash", "tool:edit(*.md)"]
---

Visual evidence belongs **rendered inside the PR body**, not behind a link.

- Push the PNGs to an evidence branch (e.g. `dividimos/pr-evidence`) or otherwise obtain stable image URLs, then embed them with `![before](...)` / `![after](...)` markdown image syntax directly in the PR description.
- Lay before/after pairs out inline (an HTML `<table>` with one column per side works in a PR body) so a reviewer sees them without clicking anything.
- Never substitute a `gh gist create` link, a `gallery.html` attachment, or "open the raw view" instructions for rendered images.
- Still keep screenshots out of the product repo's tracked source tree; the evidence branch is not `main`.

If image hosting fails, say so explicitly instead of silently degrading to a link.