#!/usr/bin/env bash

install_tmux() {
    info "Installing tmux..."
    yay -S --needed --noconfirm tmux

    if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
        info "Installing TPM (Tmux Package Manager)..."
        git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
    else
        warn "TPM is already installed."
    fi
}
