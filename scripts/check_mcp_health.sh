#!/usr/bin/env bash
set -u

# Minimal MCP startup health check for VS Code folder-open tasks.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_CONFIG="$ROOT_DIR/.vscode/mcp.json"
WAIT_SECONDS=20

log_info() {
  echo "[INFO] $1"
}

log_warn() {
  echo "[WARN] $1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

extract_server_blocks() {
  tr -d '\r\n' < "$MCP_CONFIG" | sed -E 's/^[[:space:]]+//g' | grep -oE '"[^"]+"[[:space:]]*:[[:space:]]*\{([^{}]|\{[^{}]*\})*\}' || true
}

extract_server_name() {
  echo "$1" | sed -E 's/^"([^"]+)"[[:space:]]*:.*/\1/'
}

extract_command() {
  echo "$1" | sed -nE 's/.*"command"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/p'
}

extract_env_value() {
  local block="$1"
  local key="$2"
  echo "$block" | sed -nE "s/.*\"$key\"[[:space:]]*:[[:space:]]*\"([^\"]+)\".*/\1/p"
}

ollama_is_ready() {
  local host="$1"
  if command_exists curl; then
    curl -sS --max-time 2 "$host/api/tags" >/dev/null 2>&1
    return $?
  fi

  if command_exists wget; then
    wget -q -T 2 -O - "$host/api/tags" >/dev/null 2>&1
    return $?
  fi

  log_warn "Neither curl nor wget is available for Ollama health checks"
  return 1
}

start_ollama() {
  if ! command_exists ollama; then
    log_warn "Cannot auto-start Ollama: 'ollama' is not in PATH"
    return 1
  fi

  if [ "${OSTYPE:-}" = "msys" ] || [ "${OSTYPE:-}" = "cygwin" ] || [ "${OSTYPE:-}" = "win32" ]; then
    nohup ollama serve >/dev/null 2>&1 &
  else
    nohup ollama serve >/dev/null 2>&1 &
  fi

  return 0
}

wait_for_ollama() {
  local host="$1"
  local i=0
  while [ "$i" -lt "$WAIT_SECONDS" ]; do
    if ollama_is_ready "$host"; then
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}

main() {
  if [ ! -f "$MCP_CONFIG" ]; then
    log_warn "MCP config not found: $MCP_CONFIG"
    exit 0
  fi

  local server_blocks
  server_blocks="$(extract_server_blocks)"

  if [ -z "$server_blocks" ]; then
    log_info "No MCP servers configured."
    exit 0
  fi

  log_info "Checking MCP server configuration from $MCP_CONFIG"

  local issues=0
  while IFS= read -r block; do
    [ -z "$block" ] && continue

    local name
    name="$(extract_server_name "$block")"

    local command
    command="$(extract_command "$block")"

    if [ -z "$command" ]; then
      log_warn "MCP '$name' has no 'command' configured"
      issues=$((issues + 1))
      continue
    fi

    if ! command_exists "$command"; then
      log_warn "MCP '$name' command not found: $command"
      issues=$((issues + 1))
      continue
    fi

    log_info "MCP '$name' command available: $command"

    if [ "$name" != "ollama" ]; then
      continue
    fi

    local host
    host="$(extract_env_value "$block" "OLLAMA_HOST")"
    [ -z "$host" ] && host="$(extract_env_value "$block" "OLLAMA_URL")"
    [ -z "$host" ] && host="http://127.0.0.1:11434"
    host="${host%/}"

    if ollama_is_ready "$host"; then
      log_info "MCP 'ollama' reachable at $host"
      continue
    fi

    log_warn "MCP 'ollama' configured but not reachable at $host"
    issues=$((issues + 1))

    log_info "Attempting to auto-start Ollama with 'ollama serve'..."
    if ! start_ollama; then
      continue
    fi

    if wait_for_ollama "$host"; then
      log_info "Ollama is now reachable at $host"
      issues=$((issues - 1))
    else
      log_warn "Ollama still unreachable after ${WAIT_SECONDS}s"
    fi
  done <<EOF
$server_blocks
EOF

  if [ "$issues" -eq 0 ]; then
    log_info "MCP health check passed."
  else
    log_warn "MCP health check found $issues issue(s)."
  fi

  exit 0
}

main "$@"
