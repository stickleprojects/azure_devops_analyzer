#!/bin/bash
# Resolve indirect environment variable references in .env file
# This script reads .env, resolves $VARIABLE references, and writes a resolved version

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
RESOLVED_ENV_FILE="${PROJECT_ROOT}/.env.resolved"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

echo "Resolving environment variables from $ENV_FILE..."

# Create temporary file
TEMP_FILE=$(mktemp)

# Process each line in .env file
while IFS= read -r line; do
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
            # Resolve the reference
            resolved_value="${!ref_var}"
            
            if [ -z "$resolved_value" ]; then
                echo "Warning: $key references \$$ref_var which is not set in the environment"
                echo "$line" >> "$TEMP_FILE"
            else
                echo "$key=$resolved_value" >> "$TEMP_FILE"
                echo "  Resolved: $key=\$$ref_var"
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

echo ""
echo "Resolved environment file created at: $RESOLVED_ENV_FILE"
echo ""
echo "To use the resolved environment with Docker Compose:"
echo "  docker compose --env-file .env.resolved up -d"
echo ""
echo "Or to replace your .env file (backup recommended):"
echo "  cp .env .env.backup"
echo "  mv .env.resolved .env"
