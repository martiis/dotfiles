#!/usr/bin/env sh

set -eu

sh ./packages.sh
sh ./stow.sh
sh ./override.sh
