export ZSH="$HOME/.oh-my-zsh"
export ZSH_CUSTOM="${ZSH_CUSTOM:-$ZSH/custom}"

if [[ -f "$ZSH_CUSTOM/themes/spaceship.zsh-theme" ]] || [[ -f "$ZSH_CUSTOM/themes/spaceship/spaceship.zsh-theme" ]] || [[ -f "$ZSH/themes/spaceship.zsh-theme" ]]; then
  ZSH_THEME="spaceship"
else
  ZSH_THEME="robbyrussell"
fi

plugins=(git z fzf)
if [[ -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ]] || [[ -d "$ZSH/plugins/zsh-autosuggestions" ]]; then
  plugins+=(zsh-autosuggestions)
fi

if [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /usr/local/bin/brew ]]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi

source "$ZSH/oh-my-zsh.sh"

if command -v nvim >/dev/null 2>&1; then
  export EDITOR='nvim'
  export VISUAL='nvim'
  alias vim='nvim'
else
  export EDITOR='vim'
  export VISUAL='vim'
fi

[[ -f "$HOME/.local/bin/env" ]] && source "$HOME/.local/bin/env"
[[ -d "$HOME/.local/bin" ]] && export PATH="$HOME/.local/bin:$PATH"
[[ -d "/usr/local/go/bin" ]] && export PATH="$PATH:/usr/local/go/bin"
[[ -d "$HOME/.luarocks/bin" ]] && export PATH="$HOME/.luarocks/bin:$PATH"

export NVM_DIR="$HOME/.nvm"
[[ -s "$NVM_DIR/nvm.sh" ]] && source "$NVM_DIR/nvm.sh"
[[ -s "$NVM_DIR/bash_completion" ]] && source "$NVM_DIR/bash_completion"

export BUN_INSTALL="$HOME/.bun"
[[ -s "$BUN_INSTALL/_bun" ]] && source "$BUN_INSTALL/_bun"
[[ -d "$BUN_INSTALL/bin" ]] && export PATH="$BUN_INSTALL/bin:$PATH"

export FLYCTL_INSTALL="$HOME/.fly"
[[ -d "$FLYCTL_INSTALL/bin" ]] && export PATH="$FLYCTL_INSTALL/bin:$PATH"

export PNPM_HOME="$HOME/.local/share/pnpm"
[[ -d "$PNPM_HOME" ]] && export PATH="$PNPM_HOME:$PATH"

[[ -f "$HOME/.zsh_secrets" ]] && source "$HOME/.zsh_secrets"

claude() {
  (
    unset ANTHROPIC_BASE_URL
    unset ANTHROPIC_AUTH_TOKEN
    command claude "$@"
  )
}

z-claude() {
  if [[ -z "${MY_ZAI_AUTH_TOKEN:-}" ]]; then
    echo "[warn] MY_ZAI_AUTH_TOKEN is not set" >&2
    return 1
  fi

  ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic" \
  ANTHROPIC_AUTH_TOKEN="$MY_ZAI_AUTH_TOKEN" \
  ANTHROPIC_DEFAULT_OPUS_MODEL="glm-5.1" \
  ANTHROPIC_DEFAULT_SONNET_MODEL="glm-5.1" \
  ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-5.1" \
  command claude --model GLM-5.1 "$@"
}

claude-update() {
  local dotfiles_dir="$HOME/repos/dotfiles"
  local message="Update CLAUDE.md (or settings.json if necessary) within ${dotfiles_dir}/.claude with this guidance: $1"
  z-claude -p "$message" --dangerously-skip-permissions | cat
  commit && git push
}

tmux-help() {
  local message="How to do this in tmux: $1. Keep it super short, only answer this question specifically"
  claude --model haiku --effort low -p "$message" --dangerously-skip-permissions | cat
}

clearn() {
  local prompt
  if [ -t 0 ]; then
    prompt="$*"
  else
    prompt=$(</dev/stdin)
  fi

  if [[ -z "$prompt" ]]; then
    prompt="Use learn-mode. Ask me what I want to learn, then tutor me without giving direct answers or copyable solutions."
  else
    prompt="Use learn-mode. Tutor me through this without giving direct answers or copyable solutions: ${prompt}"
  fi

  codex --sandbox read-only --ask-for-approval never -- "$prompt"
}

claude-commit() {
  z-claude -p "commit changes"
}

if [[ -x "$HOME/.bun/bin/bun" && -f "$HOME/.claude/plugins/marketplaces/thedotmack/plugin/scripts/worker-service.cjs" ]]; then
  claude-mem() {
    "$HOME/.bun/bin/bun" "$HOME/.claude/plugins/marketplaces/thedotmack/plugin/scripts/worker-service.cjs" "$@"
  }
fi

alias mini='ssh minions@mini'

if command -v pbcopy >/dev/null 2>&1; then
  alias cb='pbcopy'
elif command -v xclip >/dev/null 2>&1; then
  alias cb='xclip -sel clipboard'
fi

if command -v starship >/dev/null 2>&1; then
  eval "$(starship init zsh)"
fi
link_agent_definitions() {
  local dotfiles_dir="${DOTFILES_DIR:-${${(%):-%N}:A:h:h}}"
  local source_dir="$dotfiles_dir/shared/agents/pi-codex"
  local agent_name
  local agent_dir
  local -a agent_names=(enemy explorer git-commit-specialist planner technical-architect)
  local -a agent_dirs=(
    "$HOME/.omp/agent/agents"
    "$HOME/.pi/agent/agents"
  )

  for agent_dir in "${agent_dirs[@]}"; do
    [[ -d "$source_dir" ]] || return 0
    mkdir -p "$agent_dir"
    for agent_name in "${agent_names[@]}"; do
      [[ -e "$agent_dir/$agent_name.md" || -L "$agent_dir/$agent_name.md" ]] && continue
      ln -s "$source_dir/$agent_name.md" "$agent_dir/$agent_name.md"
    done
  done
}

link_agent_definitions
