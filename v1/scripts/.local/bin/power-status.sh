#!/usr/bin/env bash

current=$(powerprofilesctl get)

if [ "$current" = performance ]; then
    echo '{"text":"󰓅","class":"performance"}'
else
    echo '{"text":"󰾆","class":"balanced"}'
fi
