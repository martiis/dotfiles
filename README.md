# Dotfiles (Arch + Hyprland)

Personal dotfiles tailored for an Arch Linux + Hyprland setup.

## Usage
- Review the repository contents first. Only apply what you need.
- Back up your existing configuration before making changes.
- Use GNU Stow to symlink the configs into your $HOME.


### Quick start (GNU Stow)
Use GNU Stow from the repo root to symlink packages into your $HOME. The commands below assume you are in the repo root.

1) Clone the repo:
- git clone https://github.com/martiis/dotfiles.git
- cd dotfiles

2) Install stow:
- sudo pacman -S stow

3) Preview what will be linked (dry-run):
- stow -nt ~ <package>
- Example: stow -nt ~ hypr kitty waybar

4) Apply symlinks:
- stow -t ~ <package>
- Example (multiple at once): stow -t ~ hypr kitty waybar

5) Update/restow after changes:
- stow -Rt ~ <package>

6) Unstow (remove symlinks):
- stow -Dt ~ <package>

Notes:
- Replace <package> with the directory names in this repo (each is a Stow "package").
- If you see conflicts, Stow will abort. Move or back up the existing files first, then retry.
- You can target a different home with -t /path/to/home if needed.

## Requirements
- Arch Linux (or an Arch-based distro)
- Hyprland on Wayland
- Additional tools used by specific configs may include common Wayland apps (e.g., a bar/launcher/terminal). Install according to your needs.
