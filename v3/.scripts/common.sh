#!/usr/bin/env bash
# Shared helpers for v3's opt-in setup scripts.
info() { printf '==> %s\n' "$1"; }
warn() { printf 'Warning: %s\n' "$1" >&2; }
die() { warn "$1"; exit 1; }

parse_apply() {
  APPLY=false
  case "${1:-}" in
    "") ;;
    --apply) APPLY=true; shift ;;
    *) die 'Expected --apply or no arguments (preview).' ;;
  esac
  (( $# == 0 )) || die 'Unexpected arguments.'
}

install_packages() {
  if [[ "$APPLY" == false ]]; then
    info "Would install Arch packages: $*"
    return
  fi
  command -v pacman >/dev/null || die 'Package installation requires Arch Linux.'
  # Keep pacman interactive: the user reviews its transaction.
  sudo pacman -S --needed "$@"
}

clone_if_missing() {
  local description=$1 url=$2 target=$3 repository resolved
  repository=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)
  resolved=$(realpath -m -- "$target")
  case "$resolved" in
    "$repository"|"$repository"/*)
      die 'Refusing to bootstrap plugins inside the dotfiles checkout.' ;;
  esac
  if [[ -d "$target/.git" ]]; then
    info "$description is already installed; leaving it unchanged."
  elif [[ -e "$target" || -L "$target" ]]; then
    die "$description target already exists but is not a Git checkout; leaving it unchanged."
  elif [[ "$APPLY" == false ]]; then
    info "Would clone $description."
  else
    info "Installing $description."
    # Git diagnostics can expose private destination paths, even on success.
    if ! git clone --quiet --depth 1 -- "$url" "$target" >/dev/null 2>&1; then
      die "Could not clone $description; inspect the destination and network locally."
    fi
  fi
}
