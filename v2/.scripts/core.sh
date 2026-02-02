#!/usr/bin/env bash

install_core_tools() {
    info "Installing core tools (eza, bat, fzf, zoxide, alacritty)..."
    yay -S --needed --noconfirm eza bat fzf zoxide alacritty
}
