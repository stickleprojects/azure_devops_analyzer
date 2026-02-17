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

    local tty_source="/dev/tty"
    if [ ! -r "$tty_source" ]; then
        write_warning "No TTY available for environment variable selection."
        echo ""
        return 0
    fi

    if [ ${#matches[@]} -eq 0 ]; then
        printf "No environment variables matched '%s'\n" "$search_term" > "$tty_source"
        echo ""
        return 0
    fi

    printf "Select an environment variable value:\n" > "$tty_source"
    local i
    for i in "${!matches[@]}"; do
        printf "  [%d] %s\n" "$((i + 1))" "${matches[$i]}" > "$tty_source"
    done

    printf "Enter number (or press Enter to cancel): " > "$tty_source"
    IFS= read -r choice < "$tty_source"
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
