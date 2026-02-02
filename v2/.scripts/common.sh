#!/usr/bin/env bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    printf "${BLUE}==>${NC} ${GREEN}%s${NC}\n" "$1"
}

warn() {
    printf "${YELLOW}==>${NC} %s\n" "$1"
}
