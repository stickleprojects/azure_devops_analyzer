#!/bin/bash
# Resolve indirect environment variable references in .env file
# This script reads .env, resolves $VARIABLE references, and writes a resolved version
#
# Usage: resolve_env.sh [--quiet]
#   --quiet: Suppress informational messages (errors still displayed)

set -e

QUIET_MODE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quiet)
            QUIET_MODE=true
            shift
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
RESOLVED_ENV_FILE="${PROJECT_ROOT}/.env.resolved"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE" >&2
    exit 1
fi

if [ "$QUIET_MODE" = false ]; then
    echo "Resolving environment variables from $ENV_FILE..."
fi

# Create temporary file
TEMP_FILE=$(mktemp)

# Load raw key/value pairs from .env for reference resolution
declare -A ENV_MAP
while IFS= read -r line; do
    line="${line//$'\r'/}"
    if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        ENV_MAP["$key"]="$value"
    fi
done < "$ENV_FILE"

resolve_reference() {
    local ref_var="$1"
    local seen="$2"

    if [[ "$seen" == *"|$ref_var|"* ]]; then
        echo ""
        return 0
    fi

    local env_value="${!ref_var}"
    if [ -n "$env_value" ]; then
        echo "$env_value"
        return 0
    fi

    local map_value="${ENV_MAP[$ref_var]}"
    if [[ -z "$map_value" ]]; then
        echo ""
        return 0
    fi

    if [[ "$map_value" =~ ^\$\{?([A-Za-z0-9_]+)\}?$ ]]; then
        local next_ref="${BASH_REMATCH[1]}"
        resolve_reference "$next_ref" "${seen}|${ref_var}|"
        return 0
    fi

    echo "$map_value"
}

# Process each line in .env file
while IFS= read -r line; do
    # Strip Windows carriage returns
    line="${line//$'\r'/}"

    # Skip comments and empty lines
    if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
        echo "$line" >> "$TEMP_FILE"
        continue
    fi
    
    # Parse KEY=VALUE
    if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        
        # Check if value is an indirect reference like $VARIABLE or ${VARIABLE}
        if [[ "$value" =~ ^\$\{?([A-Za-z0-9_]+)\}?$ ]]; then
            ref_var="${BASH_REMATCH[1]}"
            # Resolve the reference from env or .env contents
            resolved_value="$(resolve_reference "$ref_var" "")"
            
            if [ -z "$resolved_value" ]; then
                echo "Warning: $key references \$$ref_var which is not set" >&2
                echo "$line" >> "$TEMP_FILE"
            else
                echo "$key=$resolved_value" >> "$TEMP_FILE"
                if [ "$QUIET_MODE" = false ]; then
                    echo "  Resolved: $key=\$$ref_var"
                fi
            fi
        else
            # Not a reference, keep as-is
            echo "$line" >> "$TEMP_FILE"
        fi
    else
        # Malformed line, keep as-is
        echo "$line" >> "$TEMP_FILE"
    fi
done < "$ENV_FILE"

# Move resolved file to final location
mv "$TEMP_FILE" "$RESOLVED_ENV_FILE"
chmod 600 "$RESOLVED_ENV_FILE"

if [ "$QUIET_MODE" = false ]; then
    echo ""
    echo "Resolved environment file created at: $RESOLVED_ENV_FILE"
    echo ""
    echo "To use the resolved environment with Docker Compose:"
    echo "  docker compose --env-file .env.resolved up -d"
    echo ""
    echo "Or to replace your .env file (backup recommended):"
    echo "  cp .env .env.backup"
    echo "  mv .env.resolved .env"
fi
