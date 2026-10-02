---
name: pr-screenshots-inline
description: "Embed screenshots directly in the PR body as images, never as a link to a gist gallery"
condition: ["\\bgh gist create\\b", "gist\\.github\\.com/[\\w-]+/[0-9a-f]{20,}"]
scope: "tool"
---

Screenshots belong **inside the PR body**, rendered inline. A link to a gist, an `evidence.md`, or a `gallery.html` is not enough.

- Put a Before/After markdown table in the PR body with `![alt](url)` images for each viewport and theme you captured.
- Host the PNGs as raw files, not base64 data URLs in an HTML page. For example, clone a secret gist (`git clone https://gist.github.com/<id>.git`), add the PNGs, and push. Then embed `https://gist.githubusercontent.com/<user>/<id>/raw/<file>.png`.
- Before finishing, check that the images show up in the PR body.
- Never commit screenshots to the repo.