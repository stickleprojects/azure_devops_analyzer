# GitHub Copilot Instructions for azure_devops_analyzer

## Project-Specific Conventions

### Docker
- **ALWAYS use `docker compose`** (Docker Compose V2), NOT `docker-compose` (V1)
- Docker Compose V1 is deprecated and not installed on this system

### Environment Variables
- The `.env` file supports **indirect variable references** like `$VARIABLE_NAME`
- PowerShell helpers (`EnvironmentHelpers.ps1`, `EnvFileHelpers.ps1`) resolve these references
- Docker Compose reads `.env` directly and does NOT resolve indirect references
- Use `./scripts/resolve_env.sh` to create `.env.resolved` with resolved values
- When starting Docker services, use: `docker compose --env-file .env.resolved up -d`

### Python Environment
- Python 3.12.4 managed via pyenv
- Always use `configure_python_environment` tool before running Python commands
- Use `mcp_pylance_mcp_s_pylanceRunCodeSnippet` for running Python snippets (preferred over terminal)

### Code Style
- Follow existing patterns in the codebase
- Use type hints in Python code
- Keep database operations in `src/database/storage.py`
- Extractors go in `src/extractors/{platform}/`

### Testing
- Run tests with `runTests` tool, not manual terminal commands
- Test files in `tests/` directory

### Common Issues
1. **Placeholder data in database**: Environment variables not properly resolved - check `.env.resolved`
2. **Celery workers failing**: Ensure `.env.resolved` is up to date and services restarted with correct env file
3. **Import errors**: Verify Python environment is configured correctly

## Workflow
1. When making environment changes, regenerate resolved env: `./scripts/resolve_env.sh`
2. Restart services with resolved env: `docker compose --env-file .env.resolved restart {service}`
3. Check logs: `docker compose logs -f {service}`
