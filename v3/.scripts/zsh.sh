#!/usr/bin/env bash
install_zsh() {
  install_packages zsh
  # Clone only: no downloaded installer, generated .zshrc, or automatic chsh.
  clone_if_missing 'Oh My Zsh' 'https://github.com/ohmyzsh/ohmyzsh.git' "$HOME/.oh-my-zsh"
}

install_zsh_plugins() {
  local custom=${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}
  clone_if_missing 'zsh-autosuggestions' \
    'https://github.com/zsh-users/zsh-autosuggestions.git' "$custom/plugins/zsh-autosuggestions"
  clone_if_missing 'zsh-syntax-highlighting' \
    'https://github.com/zsh-users/zsh-syntax-highlighting.git' "$custom/plugins/zsh-syntax-highlighting"
}

configure_zshrc() {
  local args=()
  if [[ "$APPLY" == true ]]; then args+=(--apply); fi
  if [[ -n "${BACKUP_DIR:-}" ]]; then args+=(--backup-dir "$BACKUP_DIR"); fi
  bash "$SCRIPT_DIR/.scripts/update-zshrc.sh" "${args[@]}"
}
