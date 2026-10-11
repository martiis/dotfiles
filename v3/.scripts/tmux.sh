#!/usr/bin/env bash
install_tmux() {
  install_packages tmux
  clone_if_missing 'TPM' 'https://github.com/tmux-plugins/tpm.git' "$HOME/.tmux/plugins/tpm"
}
