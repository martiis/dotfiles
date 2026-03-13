#!/bin/bash

choice=$(printf "  Lock\n󰍃  Logout\n  Suspend\n  Restart\n  Shutdown" | wofi --dmenu --prompt "Power")

case "$choice" in
    *Lock) hyprlock ;;
    *Logout) hyprctl dispatch exit ;;
    *Suspend) systemctl suspend ;;
    *Restart) systemctl reboot ;;
    *Shutdown) systemctl poweroff ;;
esac
