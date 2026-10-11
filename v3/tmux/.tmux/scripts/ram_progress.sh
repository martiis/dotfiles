#!/usr/bin/env bash

free | awk '/^Mem:/ {
  percentage = $3 / $2 * 100
  filled = int(percentage / 10)

  printf "["
  for (i = 0; i < 10; i++) {
    printf "%s", (i < filled ? "=" : "-")
  }
  printf "] %.0f%%", percentage
}'
