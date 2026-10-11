#!/usr/bin/env bash
configure_git() {
  local args=() file
  if [[ "$APPLY" == true ]]; then args+=(--apply); fi
  if [[ -n "${BACKUP_DIR:-}" ]]; then args+=(--backup-dir "$BACKUP_DIR"); fi
  for file in gitconfig gitignore; do
    bash "$SCRIPT_DIR/.scripts/update-block.sh" --file "$HOME/.$file" \
      --block "$SCRIPT_DIR/git/$file" --position prepend "${args[@]}"
  done
}
