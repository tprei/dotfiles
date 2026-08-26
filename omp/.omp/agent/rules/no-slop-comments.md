---
name: no-slop-comments
description: "Delete the comment this edit just added — it matches a comment shape that is slop by definition (banner, TODO, step narration, chain-of-thought, restatement, column-padded trailing note)"
condition:
  - "(?im)^(?:[ \\t]*|[^\"'`\\n]*\\S[ \\t]{2,})(?:#|//|--|/\\*|\\*)[ \\t]*[=*_~+#\\-\\u2500\\u2501\\u2014\\u2013]{3,}"
  - "(?im)^(?:[ \\t]*|[^\"'`\\n]*\\S[ \\t]{2,})(?:#(?!(?:include|define|if|ifdef|ifndef|else|elif|endif|pragma|error|warning|line|undef|!)\\b)|//|--)[ \\t]*(?:todo|fixme|xxx|hack\\b|placeholder|for now|temporar|stub\\b)"
  - "(?im)^(?:[ \\t]*|[^\"'`\\n]*\\S[ \\t]{2,})(?:#(?!(?:include|define|if|ifdef|ifndef|else|elif|endif|pragma|error|warning|line|undef|!)\\b)|//|--)[ \\t]*step[ \\t]*\\d\\b"
  - "(?im)(?<!\\n[ \\t]{0,64}(?:#|//|--)[^\\n]{0,512}\\n)^[ \\t]*(?:#(?!(?:include|define|if|ifdef|ifndef|else|elif|endif|pragma|error|warning|line|undef|!)\\b)|//|--)[ \\t]*\\d+[.)][ \\t]+(?![^\\n]*\\.[ \\t])\\w[^\\n]*(?:\\r?\\n[ \\t]*(?!#|//|--)\\S|[ \\t]*\\r?\\n?(?![\\s\\S]))"
  - "(?im)(?<!\\n[ \\t]{0,64}(?:#|//|--)[^\\n]{0,512}\\n)^(?:[ \\t]*|[^\"'`\\n]*\\S[ \\t]{2,})(?:#(?!(?:include|define|if|ifdef|ifndef|else|elif|endif|pragma|error|warning|line|undef|!)\\b)|//|--)[ \\t]*(?:we[ \\t]|we'\\w|let'?s[ \\t]|now[ \\t]|then[ \\t]|first[ ,]|next[ ,]|finally[ ,]|after that|note that|here we|this (?:is|will|does|function|method|block|section|file|module|script|means)|as (?:mentioned|noted|described|above)|basically|essentially|actually[ \\t]|in (?:this|our) case|at this point)"
  - "(?im)(?<!\\n[ \\t]{0,64}(?:#|//|--)[^\\n]{0,512}\\n)^(?:[ \\t]*|[^\"'`\\n]*\\S[ \\t]{2,})(?:#(?!(?:include|define|if|ifdef|ifndef|else|elif|endif|pragma|error|warning|line|undef|!)\\b)|//|--)[ \\t]*(?![^\\n]*(?:because|so that|[ \\t]so[ \\t]|otherwise|since |prevents?|requires?|needs?|without|never|must|\\())(?![A-Za-z]\\w*[ \\t]+(?:is|are|was|returns?|reports?|makes?|creates?|defines?|holds?|wraps?|implements?|provides?|contains?|represents?|specifies?|describes?|indicates?|denotes?|maps?|converts?|compares?|panics|must|may|should|can)\\b)(?:fetch|get|set|create|update|delete|initiali[sz]e|loop|iterate|check|validate|return|call|add|remove|handle|process|parse|build|render|start|stop|store|save|load|print|log|convert|ensure|apply|execute|compute|configure|define|import|export|read|write|send|receive|open|close|connect|install|deploy|run|test|init|setup|encode|decode|extract|copy|move|register|generate|prepare|refresh|verify|reorder|bump|wire)[ \\t]+\\w"
  - "(?m)(?<!\\n[ \\t]{0,64}(?:#|//|--)[^\\n]{0,512}\\n)^[ \\t]*(?:#(?!(?:include|define|if|ifdef|ifndef|else|elif|endif|pragma|error|warning|line|undef|!)\\b)|//|--)[ \\t]*(?![^\\n]*(?:because|so that|[ \\t]so[ \\t]|otherwise|since |prevents?|requires?|needs?|without|never|must|\\())[a-z]+(?:[ \\t]+[a-z]+){1,5}[ \\t]*(?:\\r?\\n[ \\t]*(?!#|//|--)\\S|[ \\t]*\\r?\\n?(?![\\s\\S]))"
  - "(?im)(?<!\\n[ \\t]{0,64}(?:#|//|--)[^\\n]{0,512}\\n)^[ \\t]*(?:#(?!(?:include|define|if|ifdef|ifndef|else|elif|endif|pragma|error|warning|line|undef|!)\\b)|//|--)[ \\t]*(?![A-Za-z]\\w*[ \\t]+(?:is|are|was|returns?|reports?|makes?|creates?|defines?|holds?|wraps?|implements?|provides?|contains?|represents?|specifies?|describes?|indicates?|denotes?|maps?|converts?|compares?|panics|must|may|should|can)\\b)(?:the[ \\t]+)?(\\w{4,})(?:[ \\t]+[\\w'()\\-]+){0,3}[ \\t]*\\r?\\n[ \\t]*(?!#|//|--)\\S[^\\n]*\\b\\1"
  - "(?m)^[^\"'`\\n]*\\S[ \\t]{4,}(?:#|//)[ \\t]*[A-Za-z][\\w']*(?:[ \\t]+\\S+)+"
scope: "tool:edit(*.{py,pyi,ts,tsx,js,jsx,mjs,cjs,mts,cts,sh,bash,zsh,go,rs,lua,sql,tf,tfvars,hcl,nix,rb,php,java,kt,swift,scala,dart,c,cc,cpp,h,hpp,cs,ex,exs,clj,r,ps1,zig,vue,svelte,mk,toml,yaml,yml,jsonc}), tool:write(*.{py,pyi,ts,tsx,js,jsx,mjs,cjs,mts,cts,sh,bash,zsh,go,rs,lua,sql,tf,tfvars,hcl,nix,rb,php,java,kt,swift,scala,dart,c,cc,cpp,h,hpp,cs,ex,exs,clj,r,ps1,zig,vue,svelte,mk,toml,yaml,yml,jsonc})"
---

A comment in this edit matches a shape that is slop by definition. Default verdict: **DELETE it**, then re-issue the edit.

Judge only the comments this edit writes. Hashline and patch edits re-type untouched lines, so a pre-existing comment inside a replaced range can trip this rule: if you did not author the matched comment, keep it verbatim and move on.

## Shapes matched here (all slop)

- **Divider art and section banners** — `# === config ===`, `// --- helpers ---`, `// ─── fallback ───`. Express structure with functions and modules.
- **TODO / FIXME / XXX / HACK / placeholder / "for now" / stub chatter** — do the work now or leave the code honest.
- **Step narration** — `# Step 2: ...`, or a numbered comment sitting directly above the code it numbers.
- **Chain-of-thought openers** — `we`, `let's`, `now`, `then`, `first`, `note that`, `here we`, `this is`, `basically`. That belongs in your reply, not in the file.
- **Restatement of the line below** — `# fetch the articles` above `fetch_articles()`; a terse all-lowercase phrase above the statement it describes; a comment word echoed straight into the identifier beneath it.
- **Trailing comments padded to a comment column** — `MAX_ARXIV = 1        # cap on arXiv items`. Rename the symbol; a plain 2-space note is tolerable, alignment padding is not.

## Bar for keeping a comment

Keep only a concrete fact the code cannot state: a footgun that will bite the next reader, an external spec/protocol/API constraint, a workaround for a named bug (`# Workaround for jj-vcs/jj#53: jj ignores .gitattributes eol`), or a non-local invariant the code silently relies on. "It adds context" is not enough. Otherwise put it in a name, a type, or the structure — or delete it.

## Deliberately not matched

Causal comments carrying a real why (`because`, `so that`, `otherwise`, `without`, `never`, a parenthetical), doc comments stating an exported contract (`// Get returns the values for key`), shebangs, license/SPDX headers, preprocessor lines, directives (`# noqa`, `//go:build`, `# shellcheck disable=...`), and continuation lines of an existing comment block. Markers inside strings, URLs, and regexes are excluded by anchoring, so a match means a real comment.

Where the substrate comment gate runs, it independently scores comment volume and prose blocks at checkpoint time from the real AST. This rule only intercepts the shapes above, mid-edit.
