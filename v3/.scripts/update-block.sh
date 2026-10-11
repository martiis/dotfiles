#!/usr/bin/env bash
# Maintain one managed block without copying private settings into the checkout.
set +x
set -Eeuo pipefail
export LC_ALL=C
umask 077

# Keep OS diagnostics (which can contain private paths) out of the output.
exec 3>&2
exec 2>/dev/null
pending=''
snapshot=''
recovery=''
fail() { printf '%s\n' "$1" >&3; exit 1; }
cleanup() {
  local status=$?
  if [[ -n "$recovery" ]]; then
    if [[ ! -L "$recovery" && -f "$recovery" ]]; then
      chmod 600 -- "$recovery" || status=1
    fi
    if (( status != 0 )); then
      printf '%s\n' 'Recovery warning: publication may have occurred; a recovery backup is retained. Inspect locally before retrying.' >&3
    fi
  fi
  if [[ -n "$pending" ]]; then rm -f -- "$pending"; fi
  if [[ -n "$snapshot" ]]; then rm -f -- "$snapshot"; fi
  exit "$status"
}
trap cleanup EXIT
trap 'fail "Cannot update: check the target and permissions. No config contents logged."' ERR
trap 'exit 130' INT
trap 'exit 143' TERM

usage() {
  printf '%s\n' 'Usage: update-block.sh --file FILE --block BODYFILE [--position append|prepend] [--backup-dir DIR] [--apply]' \
    'Default: preview only. --apply writes changes with a private local backup.'
}

apply=false
target=''
body_file=''
position=append
backup_dir=''
while (( $# )); do
  case "$1" in
    --apply) apply=true; shift ;;
    --file)
      (( $# >= 2 )) && [[ -n "$2" ]] || fail 'Expected a file after --file.'
      target=$2; shift 2 ;;
    --block)
      (( $# >= 2 )) && [[ -n "$2" ]] || fail 'Expected a body file after --block.'
      body_file=$2; shift 2 ;;
    --position)
      (( $# >= 2 )) && [[ "$2" == append || "$2" == prepend ]] || fail 'Expected append or prepend after --position.'
      position=$2; shift 2 ;;
    --backup-dir)
      (( $# >= 2 )) && [[ -n "$2" ]] || fail 'Expected a directory after --backup-dir.'
      backup_dir=$2; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) fail 'Unknown argument. Use --help.' ;;
  esac
done

[[ -n "$target" && -n "$body_file" ]] || fail 'Both --file and --block are required.'
[[ -f "$body_file" && -r "$body_file" ]] || fail 'Block body must be a readable regular file.'

script=$(realpath -- "${BASH_SOURCE[0]}")
repository=$(CDPATH= cd -- "$(dirname -- "$script")/../.." && pwd -P)
resolved=$(realpath -m -- "$target")
case "$resolved" in
  "$repository"|"$repository"/*) fail 'Refusing a target inside the dotfiles repository.' ;;
esac
[[ ! -L "$target" ]] || fail 'Refusing a symlink; choose the real local config explicitly.'
[[ ! -e "$target" || -f "$target" ]] || fail 'Target must be a regular file.'
parent=$(dirname -- "$target")
[[ -d "$parent" ]] || fail 'Target directory does not exist.'
if [[ -z "$backup_dir" ]]; then
  backup_dir=$parent
else
  while [[ "$backup_dir" != / && "$backup_dir" == */ ]]; do backup_dir=${backup_dir%/}; done
  [[ ! -L "$backup_dir" && -d "$backup_dir" ]] || fail 'Backup directory must be an existing real directory, not a symlink.'
  resolved_backup=$(realpath -- "$backup_dir")
  case "$resolved_backup" in
    "$repository"|"$repository"/*) fail 'Refusing a backup directory inside the dotfiles repository.' ;;
  esac
  [[ $(stat -c %d -- "$parent") == $(stat -c %d -- "$backup_dir") ]] ||
    fail 'Backup directory must be on the same filesystem as the target.'
fi

if [[ "$apply" == true ]]; then
  command -v flock >/dev/null || fail 'Cannot update: GNU mv with atomic publication and flock are required.'
  mv_version=$(mv --version) || fail 'Cannot update: GNU mv with atomic publication and flock are required.'
  mv_help=$(mv --help) || fail 'Cannot update: GNU mv with atomic publication and flock are required.'
  [[ "$mv_version" == *'GNU coreutils'* && "$mv_help" == *'--exchange'* &&
     "$mv_help" == *'--no-copy'* && "$mv_help" == *'none-fail'* ]] ||
    fail 'Cannot update: GNU mv with atomic publication and flock are required.'
  # Lock the directory inode, without creating a persistent lock file.
  exec {lock_fd}< "$parent"
  flock -n "$lock_fd" || fail 'Another updater is applying changes; no files changed.'
fi

block() {
  printf '%s\n' '# >>> dotfiles v3 >>>'
  cat -- "$body_file"
  if [[ "$body_needs_newline" == true ]]; then printf '\n'; fi
  printf '%s\n' '# <<< dotfiles v3 <<<'
}

# For an apply run, inspect an immutable private snapshot, not the live file.
# Compare both before publication and against the atomically displaced file.
name=$(basename -- "$target")
source_file=$target
mode=600
if [[ "$apply" == true && -f "$target" ]]; then
  mode=$(stat -c %a -- "$target")
  snapshot=$(mktemp -- "$parent/$name.v3-update-XXXXXXXX")
  cat -- "$target" > "$snapshot"
  source_file=$snapshot
fi

# A body cannot introduce another managed marker pair.
if grep -Eq -- $'^# (>>> dotfiles v3 >>>|<<< dotfiles v3 <<<)\r?$' "$body_file"; then
  fail 'Block body contains a managed marker; no changes made.'
else
  status=$?; (( status == 1 )) || fail 'Cannot inspect the block body.'
fi
body_needs_newline=false
if [[ -s "$body_file" ]]; then
  last_byte=$(tail -c 1 -- "$body_file" | od -An -tu1)
  last_byte=${last_byte//[[:space:]]/}
  if [[ "$last_byte" != 10 ]]; then body_needs_newline=true; fi
fi

starts=()
ends=()
size=0
start=0
end=0
needs_newline=false
if [[ -f "$source_file" ]]; then
  [[ -r "$source_file" ]] || fail 'Target is not readable.'
  size=$(stat -c %s -- "$source_file")
  # Output only marker offsets, never arbitrary config lines. GNU grep's byte
  # offsets let head/tail preserve every byte outside the managed block.
  matches=$(grep -Eabo -- $'^# >>> dotfiles v3 >>>\r?$' "$source_file") || {
    status=$?; (( status == 1 )) || fail 'Cannot inspect the v3 markers.'
  }
  if [[ -n "$matches" ]]; then mapfile -t starts <<< "$matches"; fi
  matches=$(grep -Eabo -- $'^# <<< dotfiles v3 <<<\r?$' "$source_file") || {
    status=$?; (( status == 1 )) || fail 'Cannot inspect the v3 markers.'
  }
  if [[ -n "$matches" ]]; then mapfile -t ends <<< "$matches"; fi
fi

if (( ${#starts[@]} == 0 && ${#ends[@]} == 0 )); then
  if [[ "$position" == prepend ]]; then
    start=0
    end=0
  else
    start=$size
    end=$size
  fi
  if [[ "$position" == append ]] && (( size > 0 )); then
    last_byte=$(tail -c 1 -- "$source_file" | od -An -tu1)
    last_byte=${last_byte//[[:space:]]/}
    if [[ "$last_byte" != 10 ]]; then needs_newline=true; fi
  fi
elif (( ${#starts[@]} == 1 && ${#ends[@]} == 1 )); then
  start=${starts[0]%%:*}
  end=${ends[0]%%:*}
  (( start < end )) || fail 'Invalid v3 markers; no changes made.'
  marker=${ends[0]#*:}
  end=$((end + ${#marker}))
  # grep excludes the newline after the end marker, if one exists.
  if (( end < size )); then end=$((end + 1)); fi
  if cmp -s <(dd if="$source_file" bs=1 skip="$start" count="$((end - start))" status=none) <(block); then
    printf '%s\n' 'Already up to date.'
    exit 0
  fi
else
  fail 'Invalid or duplicate v3 markers; no changes made.'
fi

if [[ "$apply" == false ]]; then
  printf '%s\n' 'Would add/update the v3 managed block. No files changed; use --apply.'
  exit 0
fi

backup=''
if [[ -n "$snapshot" ]]; then
  backup=$(mktemp -- "$backup_dir/$name.v3-backup-XXXXXXXX")
  cat -- "$snapshot" > "$backup"
fi
pending=$(mktemp -- "$parent/$name.v3-update-XXXXXXXX")
{
  if [[ -n "$snapshot" ]]; then head -c "$start" -- "$snapshot"; fi
  if [[ "$needs_newline" == true ]]; then printf '\n'; fi
  block
  if [[ -n "$snapshot" ]]; then tail -c "+$((end + 1))" -- "$snapshot"; fi
} > "$pending"
chmod "$mode" -- "$pending"

# Refuse edits observed before publication; exchange closes the remaining gap.
if [[ -n "$backup" ]]; then
  [[ ! -L "$target" && -f "$target" ]] && cmp -s -- "$target" "$snapshot" ||
    fail 'Target changed during the update; refusing to replace it.'
  # Stage on the backup filesystem before publication: --no-copy must fail
  # here, never after replacing the target, if the directory crosses devices.
  mv --no-copy -T -- "$pending" "$backup"
  pending=''
  # This path may contain displaced user data even if mv fails or is interrupted.
  # Keep it unconditionally from BEFORE the exchange, including in EXIT cleanup.
  recovery=$backup
  mv --exchange --no-copy -T -- "$backup" "$target"
  [[ ! -L "$backup" && -f "$backup" ]] || fail 'Target type changed during publication; recovery is required.'
  chmod 600 -- "$backup"
  # A late edit has already been displaced into the backup. Do not restore it
  # over the target: a further edit could have happened after the exchange.
  cmp -s -- "$backup" "$snapshot" || fail 'Target changed during publication; recovery is required.'
else
  [[ ! -e "$target" && ! -L "$target" ]] || fail 'Target appeared during the update; refusing to replace it.'
  mv --update=none-fail --no-copy -T -- "$pending" "$target"
  pending=''
fi
printf '%s\n' 'Updated the v3 managed block; existing settings preserved.'
if [[ -n "$backup" ]]; then
  printf '%s\n' 'A private backup (0600) is retained in the backup directory.'
fi
