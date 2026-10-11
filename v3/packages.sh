#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/.scripts/common.sh"
source "$SCRIPT_DIR/.scripts/core.sh"
source "$SCRIPT_DIR/.scripts/tmux.sh"
source "$SCRIPT_DIR/.scripts/zsh.sh"
parse_apply "$@"

# Package/bootstrap stage only: no linking or modification of .zshrc.
install_core_tools
install_tmux
install_zsh
install_zsh_plugins
info 'Oh My Zsh/plugin loading and the default login shell remain under your control.'
