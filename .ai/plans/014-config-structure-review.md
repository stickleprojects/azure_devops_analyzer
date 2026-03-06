# Plan 014: Config Structure Review

## Proposed Fixture Config Design

The config should be stored at `tests/fixtures/scenarios/config.json` and define:

1. **Repo type patterns** (reusable templates for sizing/metadata)
2. **Repository templates** (base repo definitions: description, languages, themes)
3. **Repository sets** (expand templates into concrete repos with unique names)
4. **Commit/PR sizing per pattern**

### Structure

```json
{
  "patterns": {
    "single-language": {
      "description": "Single-stack service with one primary language (Python, Java, Go, C#)",
      "commits": { "min": 15, "max": 25, "median": 20 },
      "commit_metadata": {
        "files_changed": { "min": 2, "max": 8, "median": 4 },
        "lines_added": { "min": 10, "max": 100, "median": 40 },
        "lines_removed": { "min": 0, "max": 50, "median": 10 }
      },
      "pull_requests": { "min": 5, "max": 10, "median": 7 },
      "pr_metadata": {
        "files_changed": { "min": 3, "max": 12, "median": 6 },
        "lines_added": { "min": 30, "max": 200, "median": 100 },
        "lines_removed": { "min": 5, "max": 80, "median": 30 }
      },
      "pr_status": {
        "merged": 0.70,
        "open": 0.20,
        "closed": 0.10
      }
    },
    "frontend-spa": {
      "description": "Frontend SPA (TypeScript + JavaScript)",
      "commits": { "min": 15, "max": 25, "median": 20 },
      "commit_metadata": {
        "files_changed": { "min": 2, "max": 8, "median": 4 },
        "lines_added": { "min": 10, "max": 100, "median": 40 },
        "lines_removed": { "min": 0, "max": 50, "median": 10 }
      },
      "pull_requests": { "min": 5, "max": 10, "median": 7 },
      "pr_metadata": {
        "files_changed": { "min": 3, "max": 12, "median": 6 },
        "lines_added": { "min": 30, "max": 200, "median": 100 },
        "lines_removed": { "min": 5, "max": 80, "median": 30 }
      },
      "pr_status": {
        "merged": 0.70,
        "open": 0.20,
        "closed": 0.10
      }
    },
    "fullstack-monorepo": {
      "description": "Multiple languages in monorepo (Python + TypeScript, etc)",
      "commits": { "min": 20, "max": 30, "median": 25 },
      "commit_metadata": {
        "files_changed": { "min": 3, "max": 10, "median": 6 },
        "lines_added": { "min": 20, "max": 150, "median": 60 },
        "lines_removed": { "min": 5, "max": 80, "median": 20 }
      },
      "pull_requests": { "min": 8, "max": 15, "median": 11 },
      "pr_metadata": {
        "files_changed": { "min": 4, "max": 15, "median": 8 },
        "lines_added": { "min": 50, "max": 300, "median": 150 },
        "lines_removed": { "min": 10, "max": 120, "median": 40 }
      },
      "pr_status": {
        "merged": 0.70,
        "open": 0.20,
        "closed": 0.10
      }
    },
    "legacy-migration": {
      "description": ".NET with mixed legacy + modern packages",
      "commits": { "min": 18, "max": 28, "median": 23 },
      "commit_metadata": {
        "files_changed": { "min": 2, "max": 8, "median": 4 },
        "lines_added": { "min": 10, "max": 100, "median": 35 },
        "lines_removed": { "min": 5, "max": 60, "median": 20 }
      },
      "pull_requests": { "min": 6, "max": 12, "median": 9 },
      "pr_metadata": {
        "files_changed": { "min": 3, "max": 10, "median": 6 },
        "lines_added": { "min": 30, "max": 180, "median": 90 },
        "lines_removed": { "min": 10, "max": 100, "median": 40 }
      },
      "pr_status": {
        "merged": 0.65,
        "open": 0.25,
        "closed": 0.10
      }
    },
    "dual-ci": {
      "description": "Dual CI configuration (Jenkins + GitHub Actions)",
      "commits": { "min": 12, "max": 20, "median": 16 },
      "commit_metadata": {
        "files_changed": { "min": 1, "max": 5, "median": 2 },
        "lines_added": { "min": 5, "max": 50, "median": 20 },
        "lines_removed": { "min": 0, "max": 30, "median": 8 }
      },
      "pull_requests": { "min": 4, "max": 8, "median": 6 },
      "pr_metadata": {
        "files_changed": { "min": 2, "max": 8, "median": 4 },
        "lines_added": { "min": 20, "max": 100, "median": 50 },
        "lines_removed": { "min": 0, "max": 40, "median": 15 }
      },
      "pr_status": {
        "merged": 0.80,
        "open": 0.20,
        "closed": 0.00
      }
    },
    "edge-case-empty": {
      "description": "Empty repository (no code, no commits)",
      "commits": { "min": 0, "max": 0, "median": 0 },
      "pull_requests": { "min": 0, "max": 0, "median": 0 },
      "pr_status": {}
    }
  },
```

        "merged": 0.8,
        "open": 0.2,
        "closed": 0.0
      }
    },
    "edge-case-empty": {
      "description": "Empty repository (no code, no commits)",
      "commits": { "min": 0, "max": 0, "median": 0 },
      "pull_requests": { "min": 0, "max": 0, "median": 0 },
      "pr_status": {}
    }

},
"repos": [
{
"name": "python-docker",
"description": "Python service with Docker and GitHub Actions CI",
"pattern": "single-language",
"languages": ["Python"],
"commit_message_themes": [
"Docker setup",
"Flask endpoint",
"pytest configuration",
"requirements.txt update",
"docker-compose enhancement"
],
"pr_title_themes": [
"Add Docker support",
"Improve Flask API",
"Add unit tests",
"Fix requirements issue",
"Update CI/CD pipeline"
],
"overrides": {}
},
{
"name": "react-spa",
"description": "React SPA with TypeScript and GitHub Actions",
"pattern": "frontend-spa",
"languages": ["TypeScript", "JavaScript"],
"commit_message_themes": [
"React component",
"async/await refactor",
"TypeScript type definition",
"component state management",
"styling update"
],
"pr_title_themes": [
"Add new component",
"Improve component performance",
"Fix TypeScript errors",
"Refactor state management",
"Update dependencies"
],
"overrides": {}
},
{
"name": "java-maven-jenkins",
"description": "Java service with Maven and Jenkins CI",
"pattern": "single-language",
"languages": ["Java"],
"commit_message_themes": [
"Spring component",
"Maven plugin configuration",
"dependency version update",
"Jenkins pipeline stage",
"unit test addition"
],
"pr_title_themes": [
"Add Spring service",
"Improve Maven build",
"Update dependencies",
"Enhance Jenkins pipeline",
"Add integration tests"
],
"overrides": {}
},
{
"name": "fullstack-monorepo",
"description": "Python backend + React frontend in monorepo",
"pattern": "fullstack-monorepo",
"languages": ["Python", "TypeScript"],
"commit_message_themes": [
"Backend API endpoint",
"Frontend component",
"shared type definition",
"database migration",
"API contract update",
"monorepo structure improvement"
],
"pr_title_themes": [
"Add backend API",
"Add frontend feature",
"Align API contracts",
"Improve monorepo structure",
"Cross-service integration"
],
"overrides": {}
},
{
"name": "dotnet-legacy",
"description": ".NET with legacy packages.config and modern .csproj",
"pattern": "legacy-migration",
"languages": ["C#"],
"commit_message_themes": [
"Nuget package update",
".csproj migration",
"packages.config cleanup",
"legacy reference removal",
"modern API usage"
],
"pr_title_themes": [
"Migrate to modern .csproj",
"Update Nuget packages",
"Remove legacy references",
"Upgrade to new API",
"Fix compatibility issues"
],
"overrides": {}
},
{
"name": "dual-ci",
"description": "Dual CI: both Jenkins and GitHub Actions",
"pattern": "dual-ci",
"languages": ["Python"],
"commit_message_themes": [
"Jenkinsfile stage",
"GitHub Actions workflow",
"CI/CD improvement",
"build optimization",
"pipeline trigger fix"
],
"pr_title_themes": [
"Add Jenkins stage",
"Add GitHub Actions workflow",
"Improve build speed",
"Fix CI trigger",
"Standardize CI configuration"
],
"overrides": {}
},
{
"name": "python-dual-deps",
"description": "Python with both Pipfile and requirements.txt",
"pattern": "dual-ci",
"languages": ["Python"],
"commit_message_themes": [
"Pipfile lock update",
"requirements.txt sync",
"dependency specification",
"environment configuration"
],
"pr_title_themes": [
"Sync Pipfile and requirements.txt",
"Update dependencies",
"Fix environment mismatch",
"Pin versions"
],
"overrides": {}
},
{
"name": "go-microservice",
"description": "Go microservice with Docker",
"pattern": "single-language",
"languages": ["Go"],
"commit_message_themes": [
"Gin router implementation",
"HTTP handler",
"go.mod dependency",
"package refactor",
"error handling improvement"
],
"pr_title_themes": [
"Add HTTP endpoint",
"Refactor package structure",
"Update go.mod",
"Improve error handling",
"Add middleware"
],
"overrides": {}
},
{
"name": "empty-stub",
"description": "Empty repository - edge case",
"pattern": "edge-case-empty",
"languages": [],
"commit_message_themes": [],
"pr_title_themes": [],
"overrides": {}
},
{
"name": "deep-nested-manifests",
"description": "Manifests only in subdirectories",
"pattern": "fullstack-monorepo",
"languages": ["Python", "TypeScript"],
"commit_message_themes": [
"Service API implementation",
"service structure",
"monorepo layout",
"package isolation",
"cross-service communication"
],
"pr_title_themes": [
"Add service implementation",
"Improve service isolation",
"Restructure services directory",
"Add cross-service integration",
"Enhance package organization"
],
"overrides": {}
}
]
}

```

---

## How This Works

### Step A1: Seed Generation

- **Input**: `config.json`
- **Output**: Expand `repo_sets` + `repo_templates` into N concrete repos; generate one seed JSON per repo
- **Uses**: `name`, `description`, `languages`, plus file/manifest templates
- **Example**:
```

For python-docker:

- Create tests/fixtures/scenarios/generated/python-docker.json
- Seed contains: name, description, languages, file_names, manifests, branches
- NO commits or PRs yet

```

### Step A2: Per-Repo Enrichment

- **Input**: Each seed JSON + corresponding config entry
- **Output**: Enriched seed with commits/PRs added
- **Process**:
1. Enrichment script receives seed file path as `sys.argv[1]`
2. Reads seed JSON
3. Looks up repo in expanded set via `seed["name"]`
4. Gets template info: `repo_templates[template_name]`
5. Gets pattern info: `patterns[pattern_name]`
6. Gets sizing: `min/max commits`, `pr_status` distribution
7. Gets themes: `commit_message_themes` list
8. Generates commits/PRs using this data
9. Writes back to same seed file
- **Example**:
```

For python-docker:

- Pattern: "single-language" → 15-25 commits (median 20)
- Themes: ["Docker setup", "Flask endpoint", "pytest configuration", ...]
- Generates ~20 commits with these themes
- Generates ~7 PRs with 70% merged, 20% open, 10% closed

```

---

## Benefits

✅ **Scalable**: Add repos by adding to `repo_sets` or new `repo_templates`
✅ **DRY**: Patterns defined once, reused many times
✅ **Extensible**: New patterns just add to `patterns{}` dict
✅ **Per-repo customization**: `commit_message_themes` tailored per repo
✅ **Override capability**: `overrides` field allows one-off tweaks (e.g., one repo wants 30 commits)
✅ **Easy to document**: Config is the source of truth, not scattered tables
✅ **LLM-friendly**: Enrichment prompt can receive the whole repo config object via `--context`

---

## Design Decisions ✅ FINALIZED

**All decisions locked in** (user approved all recommendations):

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Q1: Context window** | Full repo config + pattern | Simpler prompt logic; enrichment already per-repo |
| **Q2: Overrides** | Merge with pattern | Only override what's specified; pattern values preserved |
| **Q3: Themes format** | Simple strings | Uniform distribution fine for tests; minimal config |
| **Q4: Median field** | Keep it | Useful for determinism + documentation |
| **Q5: PR status** | Per-pattern only | Consistent "health" per pattern type |

**Implementation impact**:
- Enrichment prompt receives: `repos[i]` object merged with `patterns[pattern]` object
- Overrides applied as shallow merge: `{...pattern_dict, ...repo_overrides}`
- Theme selection: random.choice() from string list (equal probability)
- Median used as generation target: pick random value in [median-2, median+2] for determinism
- PR status distribution (merged/open/closed %) determined by pattern, not per-repo

These decisions ensure the system is **scalable, predictable, and easy to customize** while keeping config complexity manageable.

---

## Update: PR Metadata Now Included ✅

**Latest additions** (addressed user feedback: "you forgot to model pull requests"):

1. **`commit_metadata` per pattern** — Specifies realistic diffstat ranges:
   - `files_changed`: min/max/median (2–8 for single-language, 4–15 for fullstack-monorepo)
   - `lines_added`: min/max/median (10–100 for single-language, 50–500 for fullstack)
   - `lines_removed`: min/max/median (0–50 for single-language, 20–200 for fullstack)

2. **`pr_metadata` per pattern** — Equivalent diffstat ranges for pull requests:
   - `files_changed`: 3–12 for single-language, 6–20 for fullstack
   - `lines_added`: 30–200 for single-language, 100–800 for fullstack
   - `lines_removed`: 5–80 for single-language, 50–300 for fullstack

3. **`pr_title_themes` per repo** — Curated PR title suggestions matching tech stack:
   - python-docker: "Add Docker support", "Improve Flask API", "Add unit tests", ...
   - go-microservice: "Add Gin router", "Implement middleware", "Optimize concurrency", ...
   - legacy-.net-migration: "Migrate to modern .csproj", "Update Nuget packages", ...
   - And so on for all 10 repos

**Why this matters**:

- **Before**: Only had PR count (e.g., 5–10 PRs). Enrichment script had no guidance on realistic diffstat values or messaging.
- **After**: Enrichment script can now generate realistic PRs with appropriate file/line changes per pattern, and select from themed title suggestions tailored to each repo's tech stack. Result: deterministic, stack-appropriate test data.

**Next step**: User feedback on the 5 config design questions above will finalize the structure for main plan migration and implementation.

---

## Next Steps (If Approved)

1. Update `.ai/ollama-prompts/fixture-repo-seeds.md` to read config JSON and generate seeds
2. Update `.ai/ollama-prompts/fixture-repo-enrichment.md` to receive repo config via context
3. Update Step A1/A2 in plan to reference config file
4. Update verification section to show config-based workflow
```
