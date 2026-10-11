#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/.scripts/common.sh"
source "$SCRIPT_DIR/.scripts/zsh.sh"
source "$SCRIPT_DIR/.scripts/git.sh"

APPLY=false
PACKAGES=false
BACKUP_DIR=''
while (( $# )); do
  case "$1" in
    --apply) APPLY=true ;;
    --packages) PACKAGES=true ;;
    --backup-dir)
      (( $# >= 2 )) && [[ -n "$2" ]] || die 'Expected a directory after --backup-dir.'
      BACKUP_DIR=$2; shift ;;
    --help|-h)
      printf '%s\n' 'Usage: install.sh [--apply] [--packages] [--backup-dir DIR]' \
        'Default: preview linking and the Zsh/Git managed blocks.' \
        '--apply writes changes; --packages also enables package/bootstrap steps.'
      exit 0 ;;
    *) die 'Unknown argument. Use --help.' ;;
  esac
  shift
done

# All preflights happen before optional installation or config writes.
bash "$SCRIPT_DIR/stow.sh"
requested_apply=$APPLY
APPLY=false
configure_zshrc
configure_git
APPLY=$requested_apply
if [[ "$PACKAGES" == true ]]; then
  bash "$SCRIPT_DIR/packages.sh"
fi
if [[ "$APPLY" == true ]]; then
  if [[ "$PACKAGES" == true ]]; then
    bash "$SCRIPT_DIR/packages.sh" --apply
  fi
  bash "$SCRIPT_DIR/stow.sh" --apply
  configure_zshrc
  configure_git
fi
info 'GNOME settings are separate and were not applied.'
