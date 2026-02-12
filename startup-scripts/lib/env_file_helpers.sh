#!/bin/bash

# .env file generation and loading.

new_env_file() {
    local force="$1"
    local env_file="$2"
    local env_example_file="$3"

    if [ ! -f "$env_example_file" ]; then
        write_error ".env.example not found at $env_example_file"
        return 1
    fi

    if [ -f "$env_file" ] && [ "$force" != "true" ]; then
        write_info "Existing .env found. Skipping generation (use --regenerate-env to overwrite)."
        return 0
    fi

    declare -A values
    local line
    local prompt_source="/dev/tty"

    if [ ! -r "$prompt_source" ]; then
        write_error "No TTY available for interactive prompts."
        write_error "Run this script in an interactive terminal or provide a prefilled .env file."
        return 1
    fi

    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^[[:space:]]*[^#=[:space:]]+[[:space:]]*= ]]; then
            local key
            local raw_default
            key="${line%%=*}"
            raw_default="${line#*=}"
            raw_default="${raw_default%$'\r'}"
            key="$(echo "$key" | xargs)"

            local default="$raw_default"
            if [ "$key" = "POSTGRES_PASSWORD" ] && [[ "$raw_default" == changeme* ]]; then
                default="$(random_password "$PASSWORD_LENGTH")"
            fi
            if [ "$key" = "RABBITMQ_DEFAULT_PASS" ] && [[ "$raw_default" == changeme* ]]; then
                default="$(random_password "$PASSWORD_LENGTH")"
            fi

            if [ "$key" = "CELERY_BROKER_URL" ]; then
                values["$key"]="$raw_default"
                continue
            fi

            local display_default="$default"
            if [ -z "$display_default" ]; then
                display_default="<empty>"
            fi

            printf "Enter %s [default: %s] (type 'env' to search existing environment variables): " "$key" "$display_default" > "$prompt_source"
            IFS= read -r input_raw < "$prompt_source"

            local final=""
            if [ -z "$input_raw" ]; then
                final="$default"
            elif [ "$input_raw" = "env" ]; then
                printf "Search term for environment variables [default: %s]: " "$key" > "$prompt_source"
                IFS= read -r search_term < "$prompt_source"
                if [ -z "$search_term" ]; then
                    search_term="$key"
                fi
                local selected
                selected=$(select_env_variable "$search_term")
                if [ -n "$selected" ]; then
                    final="\$${selected}"
                    write_info "Using value from environment variable '$selected'"
                else
                    final="$default"
                fi
            elif [[ "$input_raw" =~ ^\$env:([A-Za-z0-9_]+)$ ]]; then
                local env_name="${BASH_REMATCH[1]}"
                if [ -n "${!env_name}" ]; then
                    final="\$${env_name}"
                    write_info "Using value from environment variable '$env_name'"
                else
                    write_warning "Environment variable '$env_name' not found. Using typed value."
                    final="$input_raw"
                fi
            else
                if [[ "$input_raw" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] && [ -n "${!input_raw}" ]; then
                    final="\$${input_raw}"
                    write_info "Using value from environment variable '$input_raw'"
                else
                    final="$input_raw"
                fi
            fi

            values["$key"]="$final"
        fi
    done < "$env_example_file"

    if [ -n "${values[RABBITMQ_DEFAULT_USER]}" ] && [ -n "${values[RABBITMQ_DEFAULT_PASS]}" ] && [ -n "${values[RABBITMQ_HOST]}" ] && [ -n "${values[RABBITMQ_PORT]}" ]; then
        local user_resolved
        local pass_resolved
        local host_resolved
        local port_resolved

        user_resolved=$(resolve_env_value "${values[RABBITMQ_DEFAULT_USER]}")
        pass_resolved=$(resolve_env_value "${values[RABBITMQ_DEFAULT_PASS]}")
        host_resolved=$(resolve_env_value "${values[RABBITMQ_HOST]}")
        port_resolved=$(resolve_env_value "${values[RABBITMQ_PORT]}")

        values["CELERY_BROKER_URL"]="amqp://${user_resolved}:${pass_resolved}@${host_resolved}:${port_resolved}//"
    fi

    local output_lines=()
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^[[:space:]]*[^#=[:space:]]+[[:space:]]*= ]]; then
            local key
            key="${line%%=*}"
            key="$(echo "$key" | xargs)"
            if [[ "${values[$key]+isset}" ]]; then
                output_lines+=("$key=${values[$key]}")
            else
                output_lines+=("$line")
            fi
        else
            output_lines+=("$line")
        fi
    done < "$env_example_file"

    printf "%s\n" "${output_lines[@]}" > "$env_file"
    write_success "Environment file created: $env_file"
    return 0
}

read_env_file() {
    local env_file="$1"
    local line

    if [ ! -f "$env_file" ]; then
        return 1
    fi

    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^[[:space:]]*[^#=[:space:]]+[[:space:]]*= ]]; then
            local key="${line%%=*}"
            local value="${line#*=}"
            key="$(echo "$key" | xargs)"
            value="$(echo "$value" | xargs)"
            local resolved
            resolved=$(resolve_env_value "$value")
            echo "$key=$resolved"
        fi
    done < "$env_file"
}

export_resolved_env_vars() {
    local env_file="$1"

    if [ ! -f "$env_file" ]; then
        write_warning "Env file not found: $env_file"
        return 1
    fi

    local missing=()
    local exported=0
    local line

    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^[[:space:]]*[^#=[:space:]]+[[:space:]]*= ]]; then
            local key="${line%%=*}"
            local value="${line#*=}"
            key="$(echo "$key" | xargs)"
            value="$(echo "$value" | xargs)"

            if [[ "$value" =~ ^\$\{?([A-Za-z0-9_]+)\}?$ ]]; then
                local referenced="${BASH_REMATCH[1]}"
                if [ -n "${!referenced}" ]; then
                    export "$referenced"="${!referenced}"
                else
                    missing+=("$key references \$$referenced which is not set in the environment")
                fi
            elif [[ "$value" =~ ^\$env:([A-Za-z0-9_]+)$ ]]; then
                local referenced="${BASH_REMATCH[1]}"
                if [ -n "${!referenced}" ]; then
                    export "$referenced"="${!referenced}"
                else
                    missing+=("$key references \$$referenced which is not set in the environment")
                fi
            fi

            local resolved
            resolved=$(resolve_env_value "$value")
            export "$key"="$resolved"
            exported=$((exported + 1))
        fi
    done < "$env_file"

    if [ ${#missing[@]} -gt 0 ]; then
        write_warning "Some environment variable references could not be resolved:"
        local msg
        for msg in "${missing[@]}"; do
            write_warning "  - $msg"
        done
        write_info ""
        write_info "To fix this, either:"
        write_info "  1. Set the environment variable in your shell"
        write_info "  2. Or update .env to use the actual value instead of a variable reference"
        return 1
    fi

    return 0
}

test_required_env_vars() {
    local env_file="$1"

    if [ ! -f "$env_file" ]; then
        write_error "Env file not found: $env_file"
        return 1
    fi

    local required_vars=(POSTGRES_PASSWORD RABBITMQ_DEFAULT_PASS)
    local optional_auth_vars=(GITHUB_TOKEN AZURE_DEVOPS_PAT)

    local has_errors="false"
    local has_auth="false"

    local env_entries
    env_entries=$(read_env_file "$env_file")

    local key
    for key in "${required_vars[@]}"; do
        local value
        value=$(echo "$env_entries" | grep -m1 "^${key}=" | cut -d= -f2-)
        if [ -z "$value" ]; then
            write_error "$key is blank or not set"
            has_errors="true"
        fi
    done

    for key in "${optional_auth_vars[@]}"; do
        local value
        value=$(echo "$env_entries" | grep -m1 "^${key}=" | cut -d= -f2-)
        if [ -n "$value" ] && [[ "$value" != your_* ]] && [[ "$value" != changeme* ]]; then
            has_auth="true"
            break
        fi
    done

    if [ "$has_auth" != "true" ]; then
        write_error "No authentication token configured. At least one of GITHUB_TOKEN or AZURE_DEVOPS_PAT must be set."
        write_error "Current values:"
        for key in "${optional_auth_vars[@]}"; do
            local value
            value=$(echo "$env_entries" | grep -m1 "^${key}=" | cut -d= -f2-)
            if [ -z "$value" ]; then
                value="<not set>"
            fi
            write_error "  $key = $value"
        done
        has_errors="true"
    fi

    if [ "$has_errors" = "true" ]; then
        write_error ""
        write_error "Please update your .env file with valid credentials and try again."
        return 1
    fi

    return 0
}
