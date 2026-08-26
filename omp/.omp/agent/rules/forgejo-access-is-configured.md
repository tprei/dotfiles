---
name: forgejo-access-is-configured
description: "forgejo.yfrit.com Access is already wired: git routes are Bypass, /api/v1 uses a CF service token; a bare 302 is not a blocker"
condition: ["cloudflareaccess.com", "behind Cloudflare Access", "Access is blocking", "mint a service token", "bypass policy", "302 to", "HTTP 307"]
scope: "text"
---

Stop -- you are treating `forgejo.yfrit.com` as unreachable and are about to build around Cloudflare Access. It is already configured, per route. The workaround is the mistake, not the fix.

What is true on this machine:

- The git smart-HTTP routes (`info/refs`, `git-upload-pack`, `git-receive-pack`, in both the `.git`-suffixed and bare forms) and the Git-LFS routes (`*/*.git/info/lfs`) are Cloudflare **Bypass** applications. `git`, `jj` and `git-lfs` clone, fetch, pull and push with no flags, no manual headers, and no Cloudflare credential of any kind. `~/.gitconfig` no longer carries `extraheader` values for this host; they were removed because nothing read them.
- Forgejo's own token auth is the only gate on those git routes, and `ENABLE_BASIC_AUTHENTICATION` is `false` instance-wide: they accept OAuth2 access tokens, personal access tokens and Actions task tokens, and reject username-and-password. A credential helper supplies the token.
- `/api/v1` is still behind the Yfrit Forgejo API application, admitting a CF service token via a `non_identity` policy. Nothing needs creating in the Cloudflare dashboard.
- `fj` on PATH is a shim that injects those service-token headers, which is why `fj` subcommands work against the instance directly. That shim is load-bearing for the API, not for git.

A `302` to `yfrit.cloudflareaccess.com` from a bare `curl` against a browser route or `/api/v1` is the correct answer to a request carrying no CF headers. It is not evidence that Access is shut, and it is not a reason to mint a token, add a policy, start a tunnel, or move to SSH.

A `401` on a git route is likewise not Access -- it is Forgejo asking for a token, identifiable by `WWW-Authenticate: Basic realm="Gitea"` and the absence of a `cf-access-aud` header. It is identical for a repository that does not exist.

The two git Bypass applications are deliberate and load-bearing; do not convert them back. Equally, do not widen the bypass to `/api/v1` or any other route on your own initiative -- that is an explicit decision.

A `307` on a git remote is a different thing, and also not Access: Forgejo returns it for a repository that changed owner, and git does not follow it for smart HTTP. Repos live under the `fairfruit` owner, so an older `mpp/...` or `matheusp/...` remote is stale -- repoint it with `git remote set-url origin https://forgejo.yfrit.com/fairfruit/<repo>.git`.

Before concluding anything is broken, issue the request the way the tooling issues it: `git ls-remote https://forgejo.yfrit.com/<owner>/<repo>`, or `fj repo view`. If those fail, report that real error -- do not route around the front door.
