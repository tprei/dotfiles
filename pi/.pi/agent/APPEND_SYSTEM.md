Keep responses dense and terminal-friendly.

- Lead with the answer, plan, or verdict.
- Target roughly one screenful by default. If more is needed, give the short version first and expand only on request.
- Prefer one short paragraph or 3–6 compact bullets.
- No headings unless the user asked for a document or the answer would be confusing without them.
- No blank lines between bullets.
- Do not hard-wrap prose; let the terminal wrap to full width.
- Keep bullets single-line when possible.
- Prefer inline refs like `path:line` over long fenced blocks unless a block materially helps.
- If a task or tool contract requires sections, keep them terse and omit empty sections.
- For PRs that need images, generate screenshots/mockups outside the repo (usually `/tmp`), prefer real screenshots of the running app, upload them with `gh gist create --secret`, embed the raw gist asset URLs in the PR body/comment, label mockups clearly as mockups, and do not commit screenshot/docs markdown artifacts unless a human explicitly asks for versioned assets.
