#!/usr/bin/env bash
# Commands invoked by the shared Git block, as command:Arch-package pairs.
# Every package listed here must also be installed by install_core_tools.
GIT_BLOCK_COMMANDS=(delta:git-delta nano:nano)

missing_git_packages() {
  local entry missing=()
  for entry in "${GIT_BLOCK_COMMANDS[@]}"; do
    command -v "${entry%%:*}" >/dev/null || missing+=("${entry#*:}")
  done
  printf '%s' "${missing[*]}"
}

# Refuse to write a Git block whose pager/editor would be missing, unless the
# package stage will install them or the user explicitly overrides.
# Pass "installed" after the package stage has run to require them strictly.
check_git_dependencies() {
  local stage=${1:-preflight} missing
  missing=$(missing_git_packages)
  [[ -z "$missing" ]] && return 0
  if [[ "${ALLOW_MISSING_DEPS:-false}" == true ]]; then
    warn "Git block commands are missing (packages: $missing); continuing because of --allow-missing-deps."
  elif [[ "$stage" == preflight && "${PACKAGES:-false}" == true ]]; then
    info "Git block packages missing now; the package stage installs them: $missing"
  else
    die "The Git block needs missing packages: $missing. Install them (sudo pacman -S --needed $missing), add --packages, or pass --allow-missing-deps."
  fi
}

configure_git() {
  local args=() file
  if [[ "$APPLY" == true ]]; then args+=(--apply); fi
  if [[ -n "${BACKUP_DIR:-}" ]]; then args+=(--backup-dir "$BACKUP_DIR"); fi
  for file in gitconfig gitignore; do
    bash "$SCRIPT_DIR/.scripts/update-block.sh" --file "$HOME/.$file" \
      --block "$SCRIPT_DIR/git/$file" --position prepend "${args[@]}"
  done
}
