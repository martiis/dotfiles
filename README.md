# Dotfiles

Personal dotfiles split into three generations:
- v1 — Arch Linux + Hyprland setup.
- v2 — the Omarchy setup.
- v3 — Arch Linux + GNOME.

Use GNU Stow to symlink selected packages from the chosen version into your $HOME.
For **v3, `--no-folding` is mandatory** for manual Stow commands, or use the
v3 installer, which supplies it. Otherwise plugin/private state can end up inside
the checkout. See [v3 instructions](v3/README.md) before applying anything.

## Usage
- Review the repository contents first. Only apply what you need.
- Back up your existing configuration before making changes.
- Decide which version you want (v1, v2, or v3) and stow packages from that directory.

## v3 preview-first setup

Stow must already be installed. From the repository root:

```sh
bash v3/install.sh                     # preview only
bash v3/install.sh --apply             # link packages and update private Zsh/Git files
bash v3/install.sh --apply --packages  # also opt into packages and TPM/OMZ/Zsh plugin clones
# Manual linking alternative (does not update Zsh/Git managed blocks):
stow --no-folding -d v3 -n -t "$HOME" ghostty zsh tmux
stow --no-folding -d v3 -t "$HOME" ghostty zsh tmux
```

Git files are **not Stow-linked** in v3: shared preferences/ignores are managed
blocks inside private `~/.gitconfig` and `~/.gitignore`. `git config --global`
writes stay private. Put identity, signing keys, and private preferences outside
the block, after it: Git may edit shared sections inside the block, which the
next `--apply` rewrites (keeping a private backup). `install.sh --backup-dir DIR`
places all updater backups in an existing real, non-symlink directory outside the
repo on the same filesystem; by default they are beside each target.

Nothing is installed automatically; plugin code is not vendored. GNOME settings
are a separate opt-in step. Review the [v3 requirements and safety notes](v3/README.md)
first, including the updater's GNU mv/flock requirements and recovery limits.

## Quick start (GNU Stow, v1/v2)
The examples below assume you cloned the repo and are in its root. They are for
v1/v2 only; do not substitute v3 without adding `--no-folding`, including restow
and unstow commands.

1) Clone the repo
- git clone https://github.com/martiis/dotfiles.git
- cd dotfiles

2) Install stow
- sudo pacman -S stow

3) Choose a version and preview what will be linked (dry-run)
- From inside the version directory:
  - cd v1 && stow -nt ~ <package>
  - Example: stow -nt ~ hypr kitty waybar
- Or from repo root using -d to point to the version directory:
  - stow -d v2 -nt ~ <package>
  - Example: stow -d v2 -nt ~ omarchy starship

4) Apply symlinks
- From inside the version directory:
  - cd v1 && stow -t ~ <package>
  - Example: stow -t ~ hypr kitty waybar
- Or from repo root with -d:
  - stow -d v2 -t ~ <package>
  - Example: stow -d v2 -t ~ omarchy starship

5) Update/restow after changes
- If you changed files and want to restow:
  - stow -d v1 -Rt ~ <package>
  - or: cd v2 && stow -Rt ~ <package>

6) Unstow (remove symlinks)
- stow -d v1 -Dt ~ <package>
- or: cd v2 && stow -Dt ~ <package>

## v2 helper script (auto‑backup + stow)
- v2 includes a convenience script: `v2/stow.sh`.
- What it does:
  - Checks for conflicts via a dry‑run, backs up existing non‑symlink targets as `*.bak-YYYY-MM-DD-HHMMSS`, removes them, then runs Stow.
  - Always targets your `$HOME` and handles the fixed packages: `waybar`, `starship`, `omarchy`, `alacritty`.
- Usage:
  ```bash
  ./v2/stow.sh
  ```
- Requirement: GNU Stow must be installed and on your `PATH`.

### Notes
- Replace <package> with package directories inside the chosen version. For v3, only `ghostty`, `zsh`, and `tmux` are Stow packages; GNOME settings are applied separately.
- If you see conflicts, Stow will abort. Move or back up the existing files first, then retry — or use `v2/stow.sh` in v2, which will back up conflicting targets automatically and then stow.
- You can target a different home with -t /path/to/home if needed.
- You can mix packages across versions, but never link overlapping configurations from multiple versions.

## Requirements
- v1: Arch Linux (or Arch-based) + Hyprland on Wayland
- v2: Omarchy environment (plus any tools referenced by packages, e.g., starship)
- v3: Arch Linux + GNOME on Wayland; see [v3 requirements](v3/README.md#dependencies)
- Additional tools used by specific configs may include common Wayland/CLI apps (launchers, bars, terminals, shells). Install according to your needs.
