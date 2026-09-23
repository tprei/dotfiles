---
name: forgejo-access-is-configured
description: "forgejo.yfrit.com Access is already wired: git routes are Bypass, /api/v1 uses a CF service token; a bare 302 is not a blocker"
condition: ["cloudflareaccess.com", "behind Cloudflare Access", "Access is blocking", "mint a service token", "bypass policy", "302 to", "HTTP 307"]
scope: "text"
---

Stop. `forgejo.yfrit.com` is reachable and Cloudflare Access is already configured per route. Building around it is the mistake.

- Git smart-HTTP routes (`info/refs`, `git-upload-pack`, `git-receive-pack`, with or without `.git`) and Git-LFS (`*/*.git/info/lfs`) are Cloudflare **Bypass** apps. `git`, `jj`, and `git-lfs` clone, fetch, and push with no flags, headers, or CF credentials. `~/.gitconfig` has no `extraheader` for this host on purpose.
- On git routes, Forgejo token auth is the only gate. `ENABLE_BASIC_AUTHENTICATION=false`: OAuth2, personal access, and Actions tokens work; username and password don't. A credential helper supplies the token.
- `/api/v1` sits behind the Yfrit Forgejo API app, which admits a CF service token via a `non_identity` policy. Nothing needs creating in the dashboard.
- `fj` on PATH is a shim that injects the service-token headers. It's required for the API, not for git.

Status codes:
- `302` to `yfrit.cloudflareaccess.com` from bare `curl` on a browser route or `/api/v1` is correct for a request without CF headers. Don't mint tokens, add policies, start tunnels, or switch to SSH.
- `401` on a git route is Forgejo asking for a token (`WWW-Authenticate: Basic realm="Gitea"`, no `cf-access-aud`). Missing repos return the same.
- `307` on a git remote means the repo changed owner; git won't follow it. Repos live under `fairfruit`, so `mpp/...` or `matheusp/...` remotes are stale: `git remote set-url origin https://forgejo.yfrit.com/fairfruit/<repo>.git`.

Keep both git Bypass apps. Don't widen bypass to `/api/v1` or other routes; that's the owner's call.

Test the way the tooling does: `git ls-remote https://forgejo.yfrit.com/<owner>/<repo>` or `fj repo view`. If those fail, report that error.
