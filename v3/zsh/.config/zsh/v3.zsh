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

# Optional private overrides; never tracked.
if [[ -r "$HOME/.zshrc.local" ]]; then
  source "$HOME/.zshrc.local"
fi
