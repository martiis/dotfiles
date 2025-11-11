#!/usr/bin/env sh
# Ensure Hyprland config sources override-master.conf at the end of the file
# POSIX sh, safe to run multiple times

set -eu

# Allow overriding target (defaults to current user's HOME)
TARGET_DIR=${TARGET_DIR:-$HOME}

CONF_DIR="$TARGET_DIR/.config/hypr"
CONF_FILE="$CONF_DIR/hyprland.conf"
REQUIRED_LINE='source = ~/.config/hypr/override-master.conf'

# Require the Hyprland config file to already exist; fail otherwise
if [ ! -f "$CONF_FILE" ]; then
  echo "Error: required config file not found: $CONF_FILE" >&2
  exit 1
fi

# Recreate the file with the required line exactly once at the end
tmp=$(mktemp)
# Keep all lines except existing occurrences of REQUIRED_LINE
if [ -s "$CONF_FILE" ]; then
  # grep -Fv returns non-zero if no lines are selected; that's fine
  grep -Fv -- "$REQUIRED_LINE" "$CONF_FILE" >"$tmp" || true
fi
printf '%s\n' "$REQUIRED_LINE" >>"$tmp"
mv "$tmp" "$CONF_FILE"

echo "Hyprland override ensured in $CONF_FILE"
