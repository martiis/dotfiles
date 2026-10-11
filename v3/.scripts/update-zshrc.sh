#!/usr/bin/env bash
set +x
set -euo pipefail
exec 3>&2
exec 2>/dev/null
args=()
while (( $# )); do
  case "$1" in
    --apply) args+=(--apply); shift ;;
    --file|--backup-dir)
      if (( $# < 2 )) || [[ -z "$2" ]]; then
        printf '%s\n' 'Expected a value after the option.' >&3
        exit 1
      fi
      args+=("$1" "$2"); shift 2 ;;
    --help|-h)
      printf '%s\n' 'Usage: update-zshrc.sh [--file FILE] [--backup-dir DIR] [--apply]' \
        'Default: preview only. --apply writes changes with a private backup.'
      exit 0 ;;
    *) printf '%s\n' 'Unknown argument. Use --help.' >&3; exit 1 ;;
  esac
done
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec bash "$SCRIPT_DIR/update-block.sh" --file "$HOME/.zshrc" \
  --block "$SCRIPT_DIR/blocks/zshrc" --position append "${args[@]}" 2>&3
