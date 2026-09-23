set shell := ["bash", "-euo", "pipefail", "-c"]

home := env_var("HOME")
omp_src := env_var_or_default("OMP_SRC", home / ".worktrees/oh-my-pi-main-driver-no-agy")
packages := "aerospace alacritty borders claude codex ghostty herdr karabiner nvim omp pi starship tmux tools vim zsh"

_default:
    @{{ just_executable() }} --list --unsorted

# Dry-run stow for one package, or every package when PKG is omitted.
stow-check pkg="":
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}"
    for pkg in {{ if pkg == "" { packages } else { pkg } }}; do
        echo "== $pkg"
        stow -n -v -t ~ "$pkg"
    done

# Link one package, or every package when PKG is omitted. stow refuses to link over a real file.
stow pkg="":
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}"
    for pkg in {{ if pkg == "" { packages } else { pkg } }}; do
        echo "== $pkg"
        stow -n -t ~ "$pkg"
        stow -v -t ~ "$pkg"
    done

unstow pkg:
    cd "{{ justfile_directory() }}" && stow -D -v -t ~ "{{ pkg }}"

# Prove the omp package is linked into $HOME and not shadowed by real files.
omp-verify:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}"
    stow -n -v -t ~ omp
    target=$(readlink -f ~/.omp/agent/config.yml)
    case "$target" in
        "{{ justfile_directory() }}"/omp/*) echo "config.yml -> $target" ;;
        *) echo "drift: ~/.omp/agent/config.yml resolves to $target" >&2; exit 1 ;;
    esac
    find ~/.omp -maxdepth 4 -type l | sort

# Parse every managed omp config, compile the extensions, and fail on GLM thinking-level drift.
omp-config-check:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}"
    mapfile -t configs < <(find omp/.omp -name '*.yml' -not -path '*/node_modules/*' | sort)
    python3 -c 'import sys, yaml; [yaml.safe_load(open(p)) for p in sys.argv[1:]]' "${configs[@]}"
    printf 'parsed %d yaml files\n' "${#configs[@]}"
    for ext in omp/.omp/agent/extensions/*.ts; do
        bun build "$ext" --no-bundle --outdir /tmp/omp-ext-check >/dev/null
    done
    rm -rf /tmp/omp-ext-check
    echo "extensions compile"
    # Level-less `zai/glm-5.3:` keys under retry.fallbackChains name a failing
    # route, so only a populated non-max level is drift.
    drift=0
    grep -rPn 'zai/glm-5\.3(-flash)?:(low|medium|high)' omp/ && drift=1
    for agent in shared/agents/*/*.md; do
        grep -q '^model: zai/glm-5\.3' "$agent" || continue
        grep -qx 'thinking: max' "$agent" || { grep -Hn '^thinking:' "$agent"; drift=1; }
    done
    if [ "$drift" -ne 0 ]; then
        echo "GLM thinking level drifted off max" >&2
        exit 1
    fi
    echo "GLM thinking levels pinned to max"

# Bootstrap the pinned omp source when missing, apply the patches, rebuild, and relink every omp launcher.
omp-rebuild:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}"
    src="{{ omp_src }}"
    if [ -d "$src" ] && [ -n "$(ls -A "$src")" ] && [ ! -e "$src/.git" ]; then
        echo "refusing to bootstrap into nonempty $src without a .git dir" >&2
        exit 1
    fi
    if [ ! -e "$src/.git" ]; then
        tarball=$(sed -n 's/^Tarball: //p' omp-runtime/PIN)
        message=$(sed -n 's/^Baseline commit message: //p' omp-runtime/PIN)
        mkdir -p "$src"
        curl --fail --location "$tarball" | tar -xz -C "$src" --strip-components=1
        git -C "$src" init -b main-driver-no-agy >/dev/null
        git -C "$src" add -A
        git -C "$src" commit -q -m "$message"
        git -C "$src" tag omp-baseline
        echo "bootstrapped $src from $(sed -n 's/^Release: //p' omp-runtime/PIN)"
    fi
    if [ "$(git -C "$src" rev-parse omp-baseline)" = "$(git -C "$src" rev-parse HEAD)" ]; then
        git -C "$src" am "$PWD"/omp-runtime/[0-9][0-9][0-9][0-9]-*.patch
    fi
    git -C "$src" log --oneline -1
    bun --cwd="$src" install --frozen-lockfile
    bun --cwd="$src" run build:native
    bun --cwd="$src/packages/coding-agent" link
    sh "$src/scripts/link-omp.sh"
    wrapper=$(readlink -f "$src/packages/coding-agent/scripts/omp")
    for bin in "$HOME/.bun/bin" "$HOME/.local/bin"; do
        if [ -e "$bin/omp" ] && [ "$(readlink -f "$bin/omp")" != "$wrapper" ]; then
            ln -sfn "$wrapper" "$bin/omp"
            echo "linked $bin/omp -> $wrapper"
        fi
    done
    live=$(command -v omp)
    resolved=$(readlink -f "$live")
    case "$resolved" in
        "$src"/*) echo "omp ($live) -> $resolved" ;;
        *) echo "drift: $live resolves to $resolved, expected under $src" >&2; exit 1 ;;
    esac
    "$live" --version
    echo "restart open omp sessions to load the rebuilt runtime"

# Regenerate omp-runtime/*.patch from the source commits above the omp-baseline tag.
omp-runtime-export:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}"
    rm -f omp-runtime/[0-9][0-9][0-9][0-9]-*.patch
    git -C "{{ omp_src }}" format-patch --no-signature --filename-max-length=100 omp-baseline..HEAD \
        -o "{{ justfile_directory() }}/omp-runtime"
    {{ just_executable() }} omp-runtime-check

# Fail when the versioned patches drift from the source checkout or from PIN.
omp-runtime-check:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}"
    [ -e "{{ omp_src }}/.git" ] || { echo "no omp source at {{ omp_src }}; run: just omp-rebuild" >&2; exit 1; }
    git -C "{{ omp_src }}" rev-parse omp-baseline >/dev/null 2>&1 || {
        echo "no omp-baseline tag in {{ omp_src }}; run: just omp-rebuild" >&2
        exit 1
    }
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    git -C "{{ omp_src }}" format-patch --no-signature --filename-max-length=100 omp-baseline..HEAD -o "$tmp" >/dev/null
    strip_sha() { sed 's/^From [0-9a-f]\{40\} Mon Sep 17 00:00:00 2001$/From <commit>/' "$1"; }
    for generated in "$tmp"/*.patch; do
        name=$(basename "$generated")
        test -f "omp-runtime/$name" || { echo "untracked patch file: $name" >&2; exit 1; }
        diff -u <(strip_sha "omp-runtime/$name") <(strip_sha "$generated")
    done
    for patch in omp-runtime/[0-9][0-9][0-9][0-9]-*.patch; do
        name=$(basename "$patch")
        test -f "$tmp/$name" || { echo "stale patch file: $name" >&2; exit 1; }
        grep -qF "Patch file: $name" omp-runtime/PIN || { echo "PIN does not list $name" >&2; exit 1; }
    done
    while read -r name; do
        test -f "omp-runtime/$name" || { echo "PIN lists missing patch: $name" >&2; exit 1; }
    done < <(awk '/^Patch file: /{print $3}' omp-runtime/PIN)
    echo "patches match source and PIN"

# Provider usage report across every authenticated backend.
usage:
    tools/.local/bin/codex-usage-check

# Claude Code OAuth window utilization.
usage-claude:
    tools/.local/bin/claude-usage-check
