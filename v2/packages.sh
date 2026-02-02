#!/usr/bin/env sh

set -eu

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    printf "${BLUE}==>${NC} ${GREEN}%s${NC}\n" "$1"
}

warn() {
    printf "${YELLOW}==>${NC} %s\n" "$1"
}

info "Installing tmux..."
yay -S --needed --noconfirm tmux

if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
    info "Installing TPM (Tmux Package Manager)..."
    git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
else
    warn "TPM is already installed."
fi

info "Installing zsh..."
yay -S --needed --noconfirm zsh

if [ ! -d "$HOME/.oh-my-zsh" ]; then
    info "Installing oh-my-zsh..."
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
else
    warn "oh-my-zsh is already installed."
fi

if [ "$SHELL" != "$(which zsh)" ]; then
    info "Changing default shell to zsh..."
    chsh -s "$(which zsh)"
else
    warn "zsh is already the default shell."
fi
