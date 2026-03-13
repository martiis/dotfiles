#!/usr/bin/env bash

IFACE="${WG_IFACE:?WG_IFACE not set}"

if ip link show "$IFACE" &>/dev/null; then
    echo '{"text":"󰌘","class":"running"}'
else
    echo '{"text":"󰌙","class":"disconnected"}'
fi
