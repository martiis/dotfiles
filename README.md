# Dotfiles

Personal dotfiles split into two generations:
- v1 — Arch Linux + Hyprland setup.
- v2 — the newer setup for Omarchy.

Use GNU Stow to symlink any package from the chosen version into your $HOME.

## Usage
- Review the repository contents first. Only apply what you need.
- Back up your existing configuration before making changes.
- Decide which version you want (v1 or v2) and stow packages from that directory.

## Quick start (GNU Stow)
The examples below assume you cloned the repo and are in its root.

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
- Replace <package> with the directory names inside v1/ or v2/ (each is a Stow "package").
- If you see conflicts, Stow will abort. Move or back up the existing files first, then retry — or use `v2/stow.sh` in v2, which will back up conflicting targets automatically and then stow.
- You can target a different home with -t /path/to/home if needed.
- You can mix and match packages across v1 and v2 if that suits your setup, but prefer staying within one version for consistency.

## Requirements
- v1: Arch Linux (or Arch-based) + Hyprland on Wayland
- v2: Omarchy environment (plus any tools referenced by packages, e.g., starship)
- Additional tools used by specific configs may include common Wayland/CLI apps (launchers, bars, terminals, shells). Install according to your needs.
