# Prompt: Generate Fixture Repository Seeds

You are a Python code generation expert. Your task is to write a complete, runnable Python script that generates fixture repository seed JSON files.

## Context

The fixture system uses a two-layer generation approach:

1. **Layer 1 (this prompt)**: Generate structural seeds (no commits/PRs)
2. **Layer 2**: Per-repo enrichment adds commits/PRs

You have access to `tests/fixtures/scenarios/config.json` which defines:

- `patterns`: 6 reusable repo type templates
- `repo_templates`: dict keyed by template name (e.g. `"python-docker"`). Each value has `pattern`, `languages`, `commit_message_themes`, `pr_title_themes`, `overrides`. **There is no `"name"` field inside the value** — the key IS the name.
- `repo_sets`: generation rules that expand templates into concrete repos. Each entry has `template` (key into `repo_templates`), and either `names` (list) or `name_template`+`services`. Optionally has `description_template`. These fields are on `repo_sets` entries, NOT on `repo_templates` values.

## Task

Generate a complete Python script: `scripts/generated/generate-repo-seeds.py`

**Input**: Reads `tests/fixtures/scenarios/config.json`

**Logic**:

1. Load config.json
2. Expand concrete repos from `repo_sets` using `repo_templates`
   - Look up `repo_set["template"]` in `repo_templates` to get the template dict
   - If `repo_set` has `names`, use those exact names
   - If `repo_set` has `name_template` + `services`, expand names: `name_template.format(service=s)` for each service
   - Resolved `name` comes from the loop above — **never from the template dict**
   - If `repo_set` has `description_template`, compute description: `description_template.format(service=service)`; otherwise fall back to `template.get("description")`
3. For each expanded repo:
   - Create seed JSON with: `name`, `description`, `languages`, `file_names`, `manifests`, `branches`
   - Write to `tests/fixtures/scenarios/generated/{name}.json`
   - Print `[OK] Created {name}.json`

**Output files**: 10 seed JSONs, one per repo

## Seed Schema

Each seed JSON must have this structure:

```json
{
  "name": "python-docker",
  "description": "Python project with Docker support and Flask API",
  "languages": ["Python"],
  "file_names": [
    "README.md",
    "Dockerfile",
    "requirements.txt",
    "app.py",
    "tests/test_app.py",
    "config.yaml"
  ],
  "manifests": {
    "requirements.txt": "# Python dependencies\nFlask==2.3.0\nrequests==2.31.0\npython-dotenv==1.0.0"
  },
  "branches": ["main", "develop", "feature/docker"]
}
```

## Repository Definitions

Based on `config.json`, generate seeds by expanding these templates and sets:

### Single-Stack Templates (simple, focused)

1. **python-docker** (template)
   - Description: Python project with Docker support
   - Languages: Python
   - Key manifests: requirements.txt, Dockerfile
   - Typical files: app.py, pytest.ini, .dockerignore, src/_, tests/_

2. **go-microservice** (template)
   - Description: Go microservice with HTTP handlers
   - Languages: Go
   - Key manifests: go.mod, go.sum
   - Typical files: main.go, cmd/_, internal/_, Makefile

### Frontend SPA Template

3. **react-spa** (template)
   - Description: React single-page application
   - Languages: TypeScript, JavaScript
   - Key manifests: package.json, tsconfig.json
   - Typical files: src/, public/, index.html, vite.config.ts, .eslintrc

### Fullstack Monorepo Template

4. **fullstack-monorepo** (template)
   - Description: Monorepo with backend (Python) + frontend (TypeScript) services
   - Languages: Python, TypeScript
   - Key manifests: backend/requirements.txt, frontend/package.json, pyproject.toml
   - Typical files: backend/app.py, frontend/src/_, services/_, shared/\*, docker-compose.yml

### Complex/Edge Case Templates

5. **java-maven-jenkins** (template)
   - Description: Java project using Maven and Jenkins CI
   - Languages: Java
   - Key manifests: pom.xml, Jenkinsfile
   - Typical files: src/main/java/_, src/test/java/_, .mvn/\*, settings.xml

6. **legacy-migration** (template)
   - Description: .NET legacy project with mixed package formats
   - Languages: C#
   - Key manifests: packages.config, .csproj, app.config
   - Typical files: src/_.cs, tests/_.cs, bin/, obj/

7. **dual-ci** (template)
   - Description: Dual CI (Jenkins + GitHub Actions)
   - Languages: Python
   - Key manifests: requirements.txt, Jenkinsfile, .github/workflows/\*.yml
   - Typical files: app.py, tests/\*, scripts/

8. **python-dual-deps** (template)
   - Description: Python project with dual dependency systems (Pipenv + pip)
   - Languages: Python
   - Key manifests: Pipfile, Pipfile.lock, requirements.txt
   - Typical files: main.py, src/_, tests/_, setup.py

9. **edge-case-empty** (template)
   - Description: Empty repository (edge case)
   - Languages: (none)
   - Key manifests: (none)
   - Typical files: README.md only

10. **deep-nested-manifests** (template)
    - Description: Complex monorepo with services in deeply-nested subdirectories
    - Languages: Python, TypeScript
    - Key manifests: services/backend/requirements.txt, services/frontend/package.json, shared/pyproject.toml
    - Typical files: services/_/src/_, shared/_, scripts/_, terraform/

## Guidelines

- **File lists**: 8–15 files per repo (more for monorepos). **Do not use a hardcoded `DEFAULT_FILES` dict keyed by template name** — derive `file_names` and `manifests` dynamically from the template's `languages` list.
- **Manifests format**: `manifests` MUST be a flat `{"filename": "content"}` dict — keys are filenames (e.g. `"requirements.txt"`, `"go.mod"`), values are string content. **Never** use a language-keyed list format like `{"python": [{"type": "...", "content": "..."}]}`.
- **Manifests**: Include realistic content snippets (no placeholders like `...`)
- **Branches**: Include `main`, `develop`, 1–2 feature branches
- **Language awareness**: Match file types to declared languages
- **Empty stub**: Return repo object but with empty or minimal file/manifest lists
- **Variable scoping**: All variables used in fallbacks or conditionals must be pre-defined. No undefined variable references (e.g., don't use `default_value` unless it's defined earlier in scope)
- **Error handling**: Print to stderr if config.json not found, but don't crash—use fallback 10-repo list
- **Output format**: Print progress `[OK] Created {name}.json` for each repo; final line should be `[OK] Generated N seed files`

## Code Quality

- Use `pathlib.Path` for file operations (not `os.path`)
- Create `tests/fixtures/scenarios/generated/` directory if missing
- Pretty-print JSON with 2-space indentation: `json.dump(obj, f, indent=2)` (NOT `open(..., indent=2)`)
- All file I/O must be inside `with` blocks
- Add comments explaining each repo type
- No TODOs or incomplete code—fully runnable

## Output

Write the complete Python script source code, ready to execute:

```python
#!/usr/bin/env python3
"""Generate fixture repository seed JSON files from config.json."""
...
```

That's it. Write the full script now, no explanations.
