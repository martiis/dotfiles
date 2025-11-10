#!/usr/bin/env bash
# Minimal GNU Stow runner for v2 dotfiles with safe backups
# - No arguments
# - Always targets $HOME
# - Packages: waybar, starship, alacritty, omarchy

set -euo pipefail

# Ensure stow is available
if ! command -v stow >/dev/null 2>&1; then
  echo "Error: GNU Stow is not installed. Please install it and re-run." >&2
  echo "Examples: apt install stow | yay -S stow | dnf install stow" >&2
  exit 1
fi

# Resolve script directory (v2 root)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME"

# Fixed package list
packages=(waybar starship alacritty omarchy)

# Backup a path if it exists and is not already a symlink
backup_if_needed() {
  local abs_path="$1"
  if [[ -e "$abs_path" && ! -L "$abs_path" ]]; then
    local ts
    ts=$(date +%F-%H%M%S)
    local backup_path="${abs_path}.bak-${ts}"
    echo "Backing up: $abs_path -> $backup_path"
    # Ensure parent directory exists for backup_path (usually does)
    mkdir -p -- "$(dirname -- "$backup_path")"
    cp -a -- "$abs_path" "$backup_path"
    # Remove the original so stow can create the symlink
    if [[ -d "$abs_path" ]]; then
      rm -rf -- "$abs_path"
    else
      rm -f -- "$abs_path"
    fi
  fi
}

# Parse stow dry-run output to find conflicting targets and back them up
handle_conflicts_for_pkg() {
  local pkg="$1"
  local tmp
  tmp=$(mktemp)
  # Capture both stdout and stderr because stow may write warnings to stderr
  if ! stow -n -t "$TARGET_DIR" -d "$SCRIPT_DIR" "$pkg" >"$tmp" 2>&1; then
    : # non-zero is fine; we will parse the output
  fi

  local had_conflicts=0
  while IFS= read -r line; do
    # Look for lines containing "over existing target <REL> since"
    case "$line" in
      *"over existing target "*)
        had_conflicts=1
        local rel target
        rel="${line#*over existing target }"
        rel="${rel%% since*}"
        # Normalize leading ./ if present
        rel="${rel#./}"
        # Build absolute path and back it up if needed
        target="$TARGET_DIR/$rel"
        backup_if_needed "$target"
        ;;
    esac
  done <"$tmp"

  rm -f -- "$tmp"
}

echo "Stowing selected packages into $TARGET_DIR"
for pkg in "${packages[@]}"; do
  if [[ -d "$SCRIPT_DIR/$pkg" ]]; then
    echo "==> Checking conflicts for '$pkg'"
    handle_conflicts_for_pkg "$pkg"
    echo "==> stow -t \"$TARGET_DIR\" -d \"$SCRIPT_DIR\" \"$pkg\""
    stow -t "$TARGET_DIR" -d "$SCRIPT_DIR" "$pkg"
  else
    echo "Skipping '$pkg' — directory not found under $SCRIPT_DIR" >&2
  fi
done

echo "Done." 
