#!/usr/bin/env bash

CONFIG="${WG_CONFIG:?WG_CONFIG not set}"
IFACE="${WG_IFACE:?WG_IFACE not set}"

if ip link show "$IFACE" &>/dev/null; then
    if pkexec wg-quick down "$CONFIG"; then
        notify-send "VPN" "Disconnected" --icon=network-offline
    else
        notify-send "VPN" "Failed to disconnect" --icon=dialog-error
    fi
else
    if pkexec wg-quick up "$CONFIG"; then
        notify-send "VPN" "Connected" --icon=network-vpn
    else
        notify-send "VPN" "Failed to connect" --icon=dialog-error
    fi
fi
