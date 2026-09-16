set shell := ["bash", "-euo", "pipefail", "-c"]

home := env_var("HOME")
omp_src := env_var_or_default("OMP_SRC", home / "src/oh-my-pi")
omp_worktree := env_var_or_default("OMP_WORKTREE", home / ".worktrees/oh-my-pi-main-driver-no-agy")
omp_launcher := home / ".bun/bin/omp"
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

# Rebuild the patched omp runtime from the worktree and relink the launcher.
omp-rebuild:
    #!/usr/bin/env bash
    set -euo pipefail
    git -C "{{ omp_worktree }}" log --oneline -1
    bun --cwd="{{ omp_worktree }}" install --frozen-lockfile
    bun --cwd="{{ omp_worktree }}" run build:native
    bun --cwd="{{ omp_worktree }}/packages/coding-agent" link
    sh "{{ omp_worktree }}/scripts/link-omp.sh"
    realpath "{{ omp_launcher }}"
    "{{ omp_launcher }}" --version
    echo "restart open omp sessions to load the rebuilt runtime"

# Regenerate omp-runtime/*.patch from the worktree commits above the pinned baseline.
omp-runtime-export:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}"
    baseline=$(awk '/^Baseline SHA: /{print $3}' omp-runtime/PIN)
    rm -f omp-runtime/[0-9][0-9][0-9][0-9]-*.patch
    git -C "{{ omp_worktree }}" format-patch --filename-max-length=100 "$baseline"..HEAD \
        -o "{{ justfile_directory() }}/omp-runtime"
    {{ just_executable() }} omp-runtime-check

# Fail when the versioned patches drift from the worktree or from PIN.
omp-runtime-check:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}"
    baseline=$(awk '/^Baseline SHA: /{print $3}' omp-runtime/PIN)
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    git -C "{{ omp_worktree }}" format-patch --filename-max-length=100 "$baseline"..HEAD -o "$tmp" >/dev/null
    for generated in "$tmp"/*.patch; do
        name=$(basename "$generated")
        diff -u "omp-runtime/$name" "$generated"
    done
    for patch in omp-runtime/[0-9][0-9][0-9][0-9]-*.patch; do
        name=$(basename "$patch")
        test -f "$tmp/$name" || { echo "stale patch file: $name" >&2; exit 1; }
        grep -qF "Patch file: $name" omp-runtime/PIN || { echo "PIN does not list $name" >&2; exit 1; }
    done
    while read -r name; do
        test -f "omp-runtime/$name" || { echo "PIN lists missing patch: $name" >&2; exit 1; }
    done < <(awk '/^Patch file: /{print $3}' omp-runtime/PIN)
    echo "patches match worktree and PIN"

# Provider usage report across every authenticated backend.
usage:
    tools/.local/bin/codex-usage-check

# Claude Code OAuth window utilization.
usage-claude:
    tools/.local/bin/claude-usage-check
