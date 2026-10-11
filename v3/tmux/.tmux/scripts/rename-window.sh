#!/usr/bin/env bash

set -u

window_id=$(tmux display-message -p -t "$TMUX_PANE" '#{window_id}')
current_name=$(tmux display-message -p -t "$window_id" '#W')

if read -er -p 'Window name: ' -i "$current_name" new_name && [[ -n $new_name ]]; then
  tmux rename-window -t "$window_id" -- "$new_name"
fi
