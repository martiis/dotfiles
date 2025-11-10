#!/usr/bin/env sh
# Minimal GNU Stow runner for v2 dotfiles with safe backups (POSIX sh)
# - No arguments
# - Always targets $HOME
# - Packages: waybar, starship, alacritty, omarchy

set -eu

# Ensure stow is available
if ! command -v stow >/dev/null 2>&1; then
  echo "Error: GNU Stow is not installed. Please install it and re-run." >&2
  echo "Examples: apt install stow | yay -S stow | dnf install stow" >&2
  exit 1
fi

# Resolve script directory (v2 root)
SCRIPT_DIR=$(cd "$(dirname "$0")" 2>/dev/null && pwd)
TARGET_DIR="$HOME"

# Fixed package list (space-separated for POSIX sh)
packages="waybar starship alacritty omarchy"

# Backup a path if it exists and is not already a symlink
backup_if_needed() {
  abs_path="$1"
  if [ -L "$abs_path" ]; then
    :
  elif [ -d "$abs_path" ] || [ -f "$abs_path" ]; then
    ts=$(date +%F-%H%M%S)
    backup_path="${abs_path}.bak-${ts}"
    echo "Backing up: $abs_path -> $backup_path"
    # Ensure parent directory exists for backup_path (usually does)
    mkdir -p "$(dirname "$backup_path")"
    if [ -d "$abs_path" ]; then
      cp -R "$abs_path" "$backup_path"
      rm -rf "$abs_path"
    else
      cp -p "$abs_path" "$backup_path" 2>/dev/null || cp "$abs_path" "$backup_path"
      rm -f "$abs_path"
    fi
  fi
}

# Parse stow dry-run output to find conflicting targets and back them up
handle_conflicts_for_pkg() {
  pkg="$1"
  tmp=$(mktemp)
  # Capture both stdout and stderr because stow may write warnings to stderr
  if ! stow -n -t "$TARGET_DIR" -d "$SCRIPT_DIR" "$pkg" >"$tmp" 2>&1; then
    : # non-zero is fine; we will parse the output
  fi

  while IFS= read -r line; do
    # Look for lines containing "over existing target <REL> since"
    case "$line" in
      *"over existing target "*)
        rel=${line#*over existing target }
        rel=${rel%% since*}
        # Normalize leading ./ if present
        case "$rel" in
          ./*) rel=${rel#./} ;;
        esac
        # Build absolute path and back it up if needed
        target="$TARGET_DIR/$rel"
        backup_if_needed "$target"
        ;;
    esac
  done <"$tmp"

  rm -f "$tmp"
}

echo "Stowing selected packages into $TARGET_DIR"
for pkg in $packages; do
  if [ -d "$SCRIPT_DIR/$pkg" ]; then
    echo "==> Checking conflicts for '$pkg'"
    handle_conflicts_for_pkg "$pkg"
    echo "==> stow -t \"$TARGET_DIR\" -d \"$SCRIPT_DIR\" \"$pkg\""
    stow -t "$TARGET_DIR" -d "$SCRIPT_DIR" "$pkg"
  else
    echo "Skipping '$pkg' — directory not found under $SCRIPT_DIR" >&2
  fi
done

echo "Done." 
