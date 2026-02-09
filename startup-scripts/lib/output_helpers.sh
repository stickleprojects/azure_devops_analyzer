#!/bin/bash

# Output and formatting utilities.

COLOR_CYAN='\033[0;36m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
COLOR_BLUE='\033[0;34m'
COLOR_GRAY='\033[0;37m'
COLOR_RESET='\033[0m'

write_step() {
    echo -e "\n${COLOR_CYAN}==>${COLOR_RESET} $1"
}

write_success() {
    echo -e "${COLOR_GREEN}[OK]${COLOR_RESET} $1"
}

write_warning() {
    echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1"
}

write_error() {
    echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1"
}

write_info() {
    echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $1"
}

show_banner() {
    cat << 'EOF'

 ____                        _
|  _ \ ___ _ __   ___       / \   _ __   __ _ _ __ _   _
| |_) / _ \ '_ \ / _ \     / _ \ | '_ \ / _' | '__| | | |
|  _ <  __/ |_) | (_) |   / ___ \| | | | (_| | |  | |_| |
|_| \_\___| .__/ \___/   /_/   \_\_| |_|\__,_|_|   \__, |
          |_|            GitHub Repository Analyzer|___/

EOF
}
