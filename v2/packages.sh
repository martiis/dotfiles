#!/usr/bin/env bash

set -eu

# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source libraries
source "$SCRIPT_DIR/.scripts/common.sh"
source "$SCRIPT_DIR/.scripts/core.sh"
source "$SCRIPT_DIR/.scripts/tmux.sh"
source "$SCRIPT_DIR/.scripts/zsh.sh"

# Installation steps
install_core_tools
install_tmux
install_zsh
install_zsh_plugins
configure_zshrc
