# v3 — Arch Linux + GNOME

Starting point for GNOME on Wayland with Alacritty, Zsh, tmux, and Git.
Based on the current GNOME 51 setup; v1 and v2 remain unchanged.
Nothing here is applied automatically.

## Contents

| Directory | Purpose |
| --- | --- |
| `alacritty/` | Stow package: Gruvbox Dark, Meslo font, audio bell, XDG terminal preferences |
| `zsh/` | Stow package: portable additions in `~/.config/zsh/v3.zsh`; **no copy of .zshrc** |
| `tmux/` | Stow package: current layout, bindings, plugin declarations, RAM/rename helpers |
| `git/` | Non-stowed templates for managed blocks in private `~/.gitconfig` and `~/.gitignore` |
| `gnome/` | Selected dconf preferences and shortcuts; **not a Stow package** |
| `install.sh` | Preview-first entry point for linking and Zsh/Git managed blocks |
| `packages.sh`, `stow.sh` | Separate package/bootstrap and linking stages |
| `.scripts/` | Shared Bash helpers for core tools, Zsh, and tmux; generic managed-block updater and compatible .zshrc wrapper |
| `examples/` | Private-override templates; **not Stow packages** |
| `tests/` | Tests using temporary files and an isolated tmux server |

Machine-specific worktree locations, Git identity/signing-key values, API tokens,
VPN/cloud settings, and extension credentials are not captured.
No wallpaper, avatar, application history, or full dconf dump is included.

## Dependencies

Install only what you use. Nothing installs automatically: linking alone does
not install applications or plugins. Explicit `--apply --packages` (or
`packages.sh --apply`) opts into Arch package installation and plugin bootstrap.

- Core: Bash, GNU coreutils/grep, GNU Stow, Zsh, Alacritty, tmux (baseline tested with 3.8), Git.
- Managed-block updater apply mode: util-linux `flock` and GNU `mv` supporting
  `--exchange`, `--no-copy`, and `--update=none-fail` (tested with coreutils 9.12).
  Older utilities are refused before updater writes; preview does not need these flags.
- Tests only: Python 3.9+ (3.11+ for TOML validation); setup and the managed-block updater do not need Python.
- Alacritty: MesloLGS Nerd Font Mono, `libpulse` (`paplay`), and the freedesktop sound theme.
  The bell uses external `paplay`, not GTK/GStreamer. The config imports its bundled
  Gruvbox Dark theme relative to the config file and preserves the current 11pt font,
  10px padding, 95% opacity, blur, and `xterm-256color` compatibility.
- Git 2.38+ (for `merge.conflictstyle=zdiff3` and `rebase.updateRefs`): `nano`,
  `git-delta`, GnuPG and a configured signing key. The installer
  refuses to write the Git block while `delta` or `nano` is missing (see below).
- Optional Zsh additions: `eza`, `bat`. Existing Oh My Zsh/fzf/zoxide setup is left alone.
- tmux plugins: TPM; its declared plugins require tools such as `fzf`,
  `zoxide`, `lazygit`, `wl-clipboard`, and Rust/Cargo for tmux-thumbs.
  Plugin code is not vendored. The opt-in package stage clones TPM, Oh My Zsh,
  zsh-autosuggestions, and zsh-syntax-highlighting from public GitHub repositories;
  it does not install the plugins declared in the tmux config.
- GNOME: `dconf` and Alacritty; the default terminal and terminal shortcut use Alacritty.
- GNOME schema validation tests: Arch's `python-gobject`.

## Bash setup scripts

Inspired by v2's entry point and shared helpers, but preview-first and without
config deletion, plugin-list replacement, downloaded installer execution, or
an automatic login-shell change. All scripts resolve their own directory.

```sh
bash v3/packages.sh                    # preview Arch packages and plugin clones
bash v3/install.sh                     # preflight linking and all Zsh/Git blocks
bash v3/install.sh --packages          # also preview package/bootstrap steps
```

After the manual backup/conflict resolution and review of private Git settings below:

```sh
bash v3/install.sh --apply             # link packages and update the Zsh/Git blocks
bash v3/install.sh --apply --packages  # also install Arch packages/clone plugins
```

The runner previews Stow (Alacritty, Zsh, tmux), the Zsh block, the Git config
block, and the Git ignore block, in that order. When `--packages` is selected it also runs
`packages.sh` in preview mode before any package/bootstrap or config writes.
Apply then runs the optional package stage, Stow, the Zsh block, and the Git
blocks, in that order. Preview-only mode runs that package preview once.

The shared Git block sets `delta` as pager and `git add -p` diff filter and
`nano` as editor; without delta, `git add -p` fails in a colour terminal. So the
preflight refuses, in preview and apply, when `delta` or `nano` is not on `PATH`,
before any package, link, or config write. With `--packages` the preflight
accepts them as pending, and the runner re-checks after the package stage,
stopping before linking if they are still missing. If you override the pager and
editor in the private part of `~/.gitconfig`, pass `--allow-missing-deps` to
write the block anyway with a warning.
Stow must already be installed; on a fresh Arch machine, install Stow first (for example, `sudo pacman -S stow`).
Package installation uses interactive `sudo pacman -S --needed`, not `--noconfirm`
or AUR helpers. Existing plugin Git checkouts are left untouched; non-checkout
file/directory collisions and bootstrap destinations inside this checkout stop
the runner before package installation. Clone diagnostics are suppressed on both
success and failure to avoid exposing private destination paths; failures report
only a generic description. Oh My Zsh is cloned, not auto-configured: its loading,
plugin list, and the login shell stay under your control. The standalone
`packages.sh --apply` stage is not the runner's all-stage preflight.
GNOME preferences remain a separate manual step; package bootstrap never applies them.

The selected enabled-extension IDs are:
- `focus-changer@heartmire`
- `clipboard-history@alexsaveau.dev`
- `appindicatorsupport@rgcjonas.gmail.com`

Install compatible versions separately before restoring extension enablement.
Extension settings/credentials are intentionally not exported.

## Preview and link packages

Run from the repository root. GNOME settings and the Zsh/Git updaters are separate steps.

```sh
stow --no-folding -d v3 -n -v -t "$HOME" alacritty zsh tmux
```

Existing Alacritty, XDG terminal preference, and tmux files may conflict. Back them up outside the
checkout, inspect the differences, and move only the specific conflicting files
before applying. Never use `--adopt`: it could copy private host files into Git.
Do not delete entire configuration directories or stow every directory in v3.
Always use `--no-folding`: directories such as `~/.tmux` must remain local so
plugins and private session state cannot end up inside the checkout.

Git files are **not linked**; keep the existing private files in place and review
the managed-block model below. If an older setup linked them, first migrate them
to real private files outside the checkout; the updater refuses symlinks.

Optional private Zsh/tmux overrides can be created from the templates in
`v3/examples/`. Keep them outside the repository.

After reviewing and resolving conflicts yourself:

```sh
stow --no-folding -d v3 -v -t "$HOME" alacritty zsh tmux
```

If you did not opt into `--packages`, optionally install TPM separately at
`~/.tmux/plugins/tpm`; the opt-in package stage installs it there for you.
Then use prefix + I to install the declared tmux plugins (the prefix here is
Ctrl+s). Those plugins are not installed by the package stage. Without them the
full tmux theme/status modules are unavailable. TPM loading is skipped when absent.

## Private Git files with shared managed blocks

`git/gitconfig` and `git/gitignore` are templates, **not Stow packages**.
The installer prepends one marked block to each real private file:
`~/.gitconfig` and `~/.gitignore`. Existing bytes remain after the block, so
private preferences override shared settings (Git last-value-wins), and later
private ignore rules override shared patterns. A missing file is created with
mode 0600. There is no `.gitconfig.local` include or separate identity file.

Keep identity, signing keys, credentials, and private preferences **outside**
`# >>> dotfiles v3 >>>` / `# <<< dotfiles v3 <<<` in `~/.gitconfig`, after the
block. For example, edit the private file locally and replace these placeholders:

```gitconfig
[user]
    name = YOUR_NAME
    email = YOUR_EMAIL
    signingkey = YOUR_GPG_KEY_ID
```

The baseline enables commit signing; configure your key before committing or
put `[commit]` with `gpgsign = false` after the block on a machine without one.

`git config --global ...` and credential-helper writes now go to the private
`~/.gitconfig`, never the checkout. **Caveat:** Git may edit or insert keys inside
the managed block when it shares a section with that block. The next `--apply`
rewrites that block and keeps a private backup, so move private settings outside
the markers rather than relying on edits within them.

To update only Git, from the repository root:

```sh
bash v3/.scripts/update-block.sh --file "$HOME/.gitconfig" --block v3/git/gitconfig --position prepend
bash v3/.scripts/update-block.sh --file "$HOME/.gitignore" --block v3/git/gitignore --position prepend
# Add --apply to each command after reviewing the previews.
```

These manual commands skip the installer's `delta`/`nano` check; install
`git-delta` and `nano` first or override the pager/editor privately.

## Update the existing Zsh startup file

This does **not** replace or copy `~/.zshrc`. It adds one marked source block at
the end, pointing to the portable fragment linked by the `zsh` package.
All bytes outside an existing managed block are preserved, including private settings.

```sh
bash v3/.scripts/update-zshrc.sh          # preview; no writes
bash v3/.scripts/update-zshrc.sh --apply  # explicit opt-in
```

The updater never prints config contents or target paths. On a real change it
makes a uniquely named `.zshrc.v3-backup-*` file (mode 0600), then atomically
replaces the file while preserving its permission mode. Backups default to beside
the original; the same rules apply to the Git files.
Repeated runs are no-ops. Symlinks, malformed/duplicate markers, and targets
inside this checkout are refused. Backups contain private data: never commit them.

### Generic updater and backup placement

`update-zshrc.sh` remains a compatible wrapper with `--file`, `--apply`, and
`--backup-dir`. It uses the unchanged Zsh source block with append positioning.
The Bash-only generic interface is:

```sh
bash v3/.scripts/update-block.sh --file TARGET --block BODYFILE \
  --position append --backup-dir BACKUP_DIR   # preview; add --apply to write
```

`--file` and `--block` are required; `--position` defaults to `append`.
`prepend` inserts the block before all original bytes when no markers exist;
`append` adds a separating newline if necessary. A single existing marker pair
is replaced in place regardless of position. CRLF markers are accepted; body
files must not contain marker lines. Every unmanaged byte is preserved.

`--backup-dir DIR` on `install.sh`, either updater, or the manual Git commands
puts backups in an existing real directory outside the repository instead of
beside each target. It cannot be a symlink and must be on the same filesystem
as the target. For example, after creating and securing your private directory:

```sh
bash v3/install.sh --backup-dir "$HOME/private-backups"          # preview
bash v3/install.sh --backup-dir "$HOME/private-backups" --apply
```

The installer forwards this option to all three updates. No backup is left beside
a target when a separate backup directory is selected. Backups contain private
data; protect the directory and never commit them. Filesystem checks and the
`mv --no-copy` staging move happen before publication, so a cross-device backup
destination cannot cause a partially published update.

Apply runs take a nonblocking `flock` on the parent directory, serializing
cooperating updater runs for that directory without a persistent lock file. A
private snapshot is used to construct the update and preserve unmanaged bytes;
concurrent edits detected before publication are refused. Existing files are
published with GNU `mv --exchange --no-copy`; missing files use
`--update=none-fail --no-copy` so a newly appeared target is not overwritten.

This is not a lock on editors or a transaction for the entire installer. An edit
in the final comparison/publication window can be detected **after publication**:
the displaced regular file is retained in a 0600 backup, and the updater returns
nonzero with a recovery warning. It never automatically restores over the target,
which might have been edited again. Inspect the target and backups locally before
retrying or recovering; prior package/linking changes are not rolled back.
SIGKILL or power loss cannot run cleanup: the displaced file remains recoverable,
but may retain its original permissions. Review and tighten recovery-file permissions
locally before retaining it.

Remove the marked block or restore a reviewed backup to undo the Zsh update.
Open a new shell to load changes; no running shell is modified by the updater.

### Shared aliases

The fragment preserves existing aliases **and functions**. Defaults are added
only for missing names: `ls` (`eza -lh --group-directories-first --icons=auto`),
`lt` (`eza --tree --level=2 --long --icons --git`), `cat` (`bat`), `..` (`cd ..`),
`...` (`cd ../..`), and `....` (`cd ../../..`). The `ls`/`lt` defaults require
`eza`; `cat` requires `bat`. No Oh My Zsh, fzf, or zoxide reinitialization occurs.

## GNOME preferences (separate, opt-in)

`gnome/settings.ini` contains selected appearance, input, window/workspace,
keyboard shortcut, default-terminal, and extension-enable settings. Super+Enter
and GNOME's default-terminal command launch Alacritty. The Alacritty Stow package
also supplies `xdg-terminals.list` and `gnome-xdg-terminals.list`; these preferences
are used by `xdg-terminal-exec` if installed.

**Loading it replaces the custom-shortcut and enabled-extension lists**, including
existing entries on another machine. Review first. It does not install extensions.
Wallpaper, monitors, credentials, and unrelated settings are not modified.

Back up GNOME settings **outside the repository** before loading:

```sh
(umask 077; dconf dump /org/gnome/ > "$HOME/gnome-before-v3.ini")
dconf load / < v3/gnome/settings.ini
```

To restore the previous saved values:

```sh
dconf load /org/gnome/ < "$HOME/gnome-before-v3.ini"
```

This restores keys in that backup, but does not remove keys absent from it.
Keep backups private: a full dump can contain machine-specific data.

## Checks (no live configuration writes)

```sh
python3 -m unittest discover -s v3/tests -v
for script in v3/*.sh v3/.scripts/*.sh; do bash -n "$script"; done
zsh -n v3/zsh/.config/zsh/v3.zsh
bash -n v3/tmux/.tmux/scripts/rename-window.sh
bash -n v3/tmux/.tmux/scripts/ram_progress.sh
alacritty migrate --dry-run --config-file="$PWD/v3/alacritty/.config/alacritty/alacritty.toml"
git diff --check
```

Tests cover generic/Zsh updater privacy, append/prepend/in-place replacement,
backup placement and permissions, cross-device refusal, idempotency, concurrent
edits and refusal cases; Git rendering with synthetic private identity/overrides;
preview-only setup, bootstrap/config conflict preflights, missing Git-block
command refusal/override/package-stage re-check with a filtered `PATH`,
existing-checkout preservation and mock clone diagnostic privacy in a temporary
home; package linking, bundled Alacritty theme/TOML validation; isolated tmux config loading; and GNOME schema/value checks
when PyGObject is available. No test installs system packages or clones plugins.
