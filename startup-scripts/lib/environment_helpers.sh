#!/bin/bash

# Environment variable utilities.

random_password() {
    local length="${1:-24}"
    if command -v tr >/dev/null 2>&1 && [ -r /dev/urandom ]; then
        tr -dc 'A-Za-z0-9' </dev/urandom | head -c "$length"
        return 0
    fi

    # Fallback if /dev/urandom is not available.
    local chars="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    local pass=""
    local i
    for ((i=0; i<length; i++)); do
        pass+="${chars:RANDOM%${#chars}:1}"
    done
    echo "$pass"
}

select_env_variable() {
    local search_term="$1"
    local matches=()
    local name

    while IFS= read -r name; do
        if [[ "$name" == *"${search_term}"* ]]; then
            matches+=("$name")
        fi
    done < <(env | cut -d= -f1 | sort)

    if [ ${#matches[@]} -eq 0 ]; then
        write_warning "No environment variables matched '$search_term'"
        echo ""
        return 0
    fi

    write_info "Select an environment variable value:"
    local i
    for i in "${!matches[@]}"; do
        printf "  [%d] %s\n" "$((i + 1))" "${matches[$i]}"
    done

    read -r -p "Enter number (or press Enter to cancel): " choice
    if [ -z "$choice" ]; then
        echo ""
        return 0
    fi

    if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
        write_warning "Invalid selection. Skipping env selection."
        echo ""
        return 0
    fi

    local index=$((choice - 1))
    if [ $index -lt 0 ] || [ $index -ge ${#matches[@]} ]; then
        write_warning "Selection out of range. Skipping env selection."
        echo ""
        return 0
    fi

    echo "${matches[$index]}"
}

resolve_env_value() {
    local value="$1"

    if [[ "$value" =~ ^\$\{?([A-Za-z0-9_]+)\}?$ ]]; then
        local name="${BASH_REMATCH[1]}"
        local resolved="${!name}"
        if [ -n "$resolved" ]; then
            echo "$resolved"
            return 0
        fi
    fi

    if [[ "$value" =~ ^\$env:([A-Za-z0-9_]+)$ ]]; then
        local name="${BASH_REMATCH[1]}"
        local resolved="${!name}"
        if [ -n "$resolved" ]; then
            echo "$resolved"
            return 0
        fi
    fi

    echo "$value"
}
