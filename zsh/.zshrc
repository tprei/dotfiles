# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
ZSH_THEME="spaceship"

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME=random will cause zsh to load
# a theme from this variable instead of looking in $ZSH/themes/
# If set to an empty array, this variable will have no effect.
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment one of the following lines to change the auto-update behavior
# zstyle ':omz:update' mode disabled  # disable automatic updates
# zstyle ':omz:update' mode auto      # update automatically without asking
# zstyle ':omz:update' mode reminder  # just remind me to update when it's time

# Uncomment the following line to change how often to auto-update (in days).
# zstyle ':omz:update' frequency 13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS="true"

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
# You can also set it to another string to have that shown instead of the default red dots.
# e.g. COMPLETION_WAITING_DOTS="%F{yellow}waiting...%f"
# Caution: this setting can cause issues with multiline prompts in zsh < 5.7.1 (see #5765)
# COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# You can set one of the optional three formats:
# "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# or set a custom format using the strftime function format specifications,
# see 'man strftime' for details.
# HIST_STAMPS="mm/dd/yyyy"

# Would you like to use another custom folder than $ZSH/custom?
# ZSH_CUSTOM=/path/to/new-custom-folder

# Which plugins would you like to load?
# Standard plugins can be found in $ZSH/plugins/
# Custom plugins may be added to $ZSH_CUSTOM/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(git z zsh-autosuggestions fzf)

source $ZSH/oh-my-zsh.sh

# User configuration

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# Set personal aliases, overriding those provided by oh-my-zsh libs,
# plugins, and themes. Aliases can be placed here, though oh-my-zsh
# users are encouraged to define aliases within the ZSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

export DISPLAY=:0

. "$HOME/.local/bin/env"
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"
export PATH=$HOME/chrome-linux64:$PATH

eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"


# bun completions
[ -s "/home/prei/.bun/_bun" ] && source "/home/prei/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

alias claude-mem='/home/prei/.bun/bin/bun "/home/prei/.claude/plugins/marketplaces/thedotmack/plugin/scripts/worker-service.cjs"'

# Added by flyctl installer
export FLYCTL_INSTALL="/home/prei/.fly"
export PATH="$FLYCTL_INSTALL/bin:$PATH"


# Load secrets (not tracked in git)
if [[ -f "$HOME/.zsh_secrets" ]]; then
    source "$HOME/.zsh_secrets"
else
    echo "[warn] ~/.zsh_secrets not found — z-claude will not work without MY_ZAI_AUTH_TOKEN"
fi

# 1. Standard Anthropic Claude (Pro Plan)
claude() {
    (
        unset ANTHROPIC_BASE_URL
        unset ANTHROPIC_AUTH_TOKEN
        command claude "$@"
    )
}

# 2. Z.AI Claude (Your current GLM setup)
z-claude() {
    ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic" \
    ANTHROPIC_AUTH_TOKEN="$MY_ZAI_AUTH_TOKEN" \
    ANTHROPIC_DEFAULT_OPUS_MODEL="glm-5" \
    ANTHROPIC_DEFAULT_SONNET_MODEL="glm-5" \
    ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-5" \
    command claude --model GLM-5 "$@"
}

claude-update() {
  local message="Update CLAUDE.md (or settings.json if necessary) within $HOME/dotfiles/.claude with this guidance: $1"
  z-claude -p "$message" --dangerously-skip-permissions | cat
  commit && git push
}

tmux-help() {
  local message="How to do this in tmux: $1. Keep it super short, only answer this question specifically"
  claude --model haiku --effort low -p "$message" --dangerously-skip-permissions | cat
}

claude-commit() {
  z-claude -p "commit changes"
}

export PULSE_SERVER=/mnt/wslg/PulseServer
export SDL_AUDIODRIVER=pulseaudio


alias mini='ssh minions@mini'

export PATH=$PATH:/usr/local/go/bin
export PATH="$HOME/.luarocks/bin:$PATH"
export PATH="$PATH:/mnt/c/Users/srtp-/AppData/Local/Android/Sdk/platform-tools"

alias cb="xclip -sel clipboard"
