# Portable additions only. The existing ~/.zshrc remains authoritative.
# Do not reload Oh My Zsh or reinitialize fzf/zoxide here.
[[ -o interactive ]] || return 0

if (( $+commands[eza] )); then
  (( ! $+aliases[ls] && ! $+functions[ls] )) && alias ls='eza -lh --group-directories-first --icons=auto'
  (( ! $+aliases[lt] && ! $+functions[lt] )) && alias lt='eza --tree --level=2 --long --icons --git'
fi
(( $+commands[bat] && ! $+aliases[cat] && ! $+functions[cat] )) && alias cat='bat'
(( ! $+aliases[..] && ! $+functions[..] )) && alias ..='cd ..'
(( ! $+aliases[...] && ! $+functions[...] )) && alias ...='cd ../..'
(( ! $+aliases[....] && ! $+functions[....] )) && alias ....='cd ../../..'

# Yazi shell integration: keep an existing alias/function authoritative.
if (( $+commands[yazi] && ! $+aliases[y] && ! $+functions[y] )); then
  function y() {
    local tmp cwd
    tmp="$(mktemp -t "yazi-cwd.XXXXXX")" || return
    command yazi "$@" --cwd-file="$tmp"
    IFS= read -r -d '' cwd < "$tmp"
    [[ -n "$cwd" && "$cwd" != "$PWD" ]] && builtin cd -- "$cwd"
    command rm -f -- "$tmp"
  }
fi

# Optional private overrides; never tracked.
if [[ -r "$HOME/.zshrc.local" ]]; then
  source "$HOME/.zshrc.local"
fi
