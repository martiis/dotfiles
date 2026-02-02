#!/usr/bin/env bash

install_zsh() {
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
}

install_zsh_plugins() {
    ZSH_CUSTOM=${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}
    if [ ! -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ]; then
        info "Installing zsh-autosuggestions..."
        git clone https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
    fi

    if [ ! -d "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" ]; then
        info "Installing zsh-syntax-highlighting..."
        git clone https://github.com/zsh-users/zsh-syntax-highlighting.git "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"
    fi
}

configure_zshrc() {
    ZSHRC="$HOME/.zshrc"
    if [ ! -f "$ZSHRC" ]; then
        touch "$ZSHRC"
    fi
    
    info "Updating plugins in .zshrc..."
    if grep -q '^plugins=(' "$ZSHRC"; then
        sed -i 's/^plugins=(.*/plugins=(git docker docker-compose zsh-autosuggestions zsh-syntax-highlighting)/' "$ZSHRC"
    else
        echo 'plugins=(git docker docker-compose zsh-autosuggestions zsh-syntax-highlighting)' >> "$ZSHRC"
    fi

    info "Adding aliases to .zshrc..."
    local ALIASES=(
        "alias ls='eza -lh --group-directories-first --icons=auto'"
        "alias lt='eza --tree --level=2 --long --icons --git'"
        "alias cat='bat'"
        "alias ..='cd ..'"
        "alias ...='cd ../..'"
        "alias ....='cd ../../..'"
    )

    for alias_line in "${ALIASES[@]}"; do
        if ! grep -Fq "$alias_line" "$ZSHRC"; then
            echo "$alias_line" >> "$ZSHRC"
        fi
    done

    info "Configuring .zshrc for fzf and zoxide..."
    if ! grep -Fxq "source <(fzf --zsh)" "$ZSHRC"; then
        echo "source <(fzf --zsh)" >> "$ZSHRC"
    fi

    if ! grep -Fxq 'eval "$(zoxide init --cmd cd zsh)"' "$ZSHRC"; then
        echo 'eval "$(zoxide init --cmd cd zsh)"' >> "$ZSHRC"
    fi
}
