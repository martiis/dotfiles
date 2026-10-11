#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/.scripts/common.sh"
parse_apply "$@"
command -v stow >/dev/null || die 'GNU Stow is required.'
packages=(ghostty zsh tmux)

# Resolve every conflict before linking anything. Never adopt or delete configs.
if ! stow --no-folding -d "$SCRIPT_DIR" -n -t "$HOME" "${packages[@]}" >/dev/null 2>&1; then
  die 'Stow preview failed. Inspect conflicts with the manual preview in v3/README.md; nothing linked.'
fi
if [[ "$APPLY" == false ]]; then
  info 'Stow preview passed; would link ghostty, zsh, and tmux.'
else
  stow --no-folding -d "$SCRIPT_DIR" -t "$HOME" "${packages[@]}"
  info 'Linked ghostty, zsh, and tmux.'
fi
