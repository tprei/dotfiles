# Antigravity ACP integration

## Goal

Make the existing `antigravity-cli` OMP provider load from the bare extension directory, keep its `agy` stream-json bridge usable, deploy the repository's Herdr stow package through the existing home configuration, and prevent Antigravity from occupying interactive OMP driver roles.

## Files and exact changes

- `omp/.omp/agent/extensions/antigravity-cli/models.ts`
  - Remove the runtime import of `@oh-my-pi/pi-catalog/effort`.
  - Define the six effort values locally as string literals and use them for model effort lists, routing keys, and `resolveAgyModelId`.
  - Keep the exported provider ids, four model ids, wire model ids, zero-cost metadata, text-only input, context limits, and error behavior unchanged.
- `omp/.omp/agent/config.yml`
  - Keep `antigravity-cli/*` fallback entries as retry-source rules only.
  - Change `modelRoles.tiny` to `zai/glm-5.3:low`.
  - Assign `modelRoles.advisor` to `antigravity-cli/gemini-3.8-flash:high`; leave default, slow, plan, task, vision, commit, and smol on non-Antigravity providers.
- `omp/.omp/profiles/mix/agent/config.yml`
  - Apply the same advisor-only Antigravity role policy and replace the `tiny` role with `zai/glm-5.3:low`.
- `zsh/.zshrc`
  - Replace the `mix` alias's `google-antigravity` plan target with the profile's existing native Anthropic high-effort model.
- `README.md`
  - Describe the provider as an `agy` stream-json bridge, document that Antigravity is advisor-only in root and `mix`, and remove stale claims that `tiny` selects it.
- Home deployment, after the repository change is committed and merged into the canonical checkout:
  - Keep the existing `~/.config/herdr` directory and runtime state.
  - Link `~/.config/herdr/config.toml` and `~/.config/herdr/scripts/open-pane-dir.sh` to the matching files in `herdr/.config/herdr`, preserving any existing non-repository Herdr state.
  - Do not create generated Herdr-managed agent hooks or invent an `@herdr` package namespace.

## Interfaces and constraints

The provider continues to launch `agy` with `--print= --input-format stream-json --output-format stream-json`, preserves conversation reuse, and exposes the existing OMP `ProviderModelConfig` records. No new package dependency, ACP client, fallback implementation, compatibility alias, permission change, or linter/typechecker suppression is allowed.

## Verification

1. Load the explicit extension with `omp --no-extensions -e <extension> models antigravity-cli` and verify all four models list without a package-load warning.
2. Run an explicit-extension OMP one-word prompt through `antigravity-cli/gemini-3.8-flash` and verify a successful response.
3. Inspect both YAML files and verify no interactive driver role except `advisor` references `antigravity-cli`; verify `tiny` and the `mix` alias use non-Antigravity models.
4. Verify the Herdr links resolve to the tracked repository files without replacing the existing configuration directory or session state.
