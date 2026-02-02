#!/usr/bin/env sh

set -eu

echo "Installing tmux..."
yay -S --needed --noconfirm tmux

if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
    echo "Installing TPM (Tmux Package Manager)..."
    git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
else
    echo "TPM is already installed."
fi
