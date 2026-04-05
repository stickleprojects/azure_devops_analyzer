#!/usr/bin/env python3
"""Generate fixture repository seed JSON files from config.json.

This is a single-stage generator: it produces complete fixtures including
commits and pull requests in one pass, making re-generation safe and
idempotent.  Commit/PR data is produced deterministically by seeding the
PRNG with a hash of the repository name, so the output is stable across
runs without depending on a separate enrichment step.
"""

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Synthetic vulnerability data per template — deterministic, no external API calls.
# Each entry maps directly to store_package_metadata() + store_repo_dependencies().
#
# Severity distribution across templates:
#   python-docker    → CRITICAL (urllib3) + HIGH (requests) + EOL (certifi)
#   dual-ci          → HIGH (Flask) + MEDIUM (Werkzeug)
#   fullstack-monorepo → MEDIUM (fastapi) + LOW (starlette)
#   go-microservice  → MEDIUM (gin-gonic)
#   react-spa        → LOW (axios, npm)
#   java-maven-jenkins → LOW (spring-web, maven)
#   legacy-migration → MEDIUM (Newtonsoft.Json, nuget)
#   others           → [] (clean repos)
VULNERABILITY_DATA_BY_TEMPLATE = {
    "python-docker": [
        {
            "package_name": "urllib3",
            "ecosystem": "pypi",
            "pinned_version": "1.22",
            "latest_version": "2.2.1",
            "is_eol": False,
            "eol_date": None,
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2021-33503",
                    "osv_id": "GHSA-q2q7-5pp4-w6pg",
                    "severity": "CRITICAL",
                    "summary": "urllib3 ReDoS via catastrophic backtracking",
                    "details": "Catastrophic backtracking in URL regular expression leads to denial of service",
                    "fixed_in_versions": ["1.26.5", "2.0.2"],
                    "references": [],
                }
            ],
        },
        {
            "package_name": "requests",
            "ecosystem": "pypi",
            "pinned_version": "2.18.0",
            "latest_version": "2.31.0",
            "is_eol": False,
            "eol_date": None,
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2018-18074",
                    "osv_id": "GHSA-x84v-xcm2-53pg",
                    "severity": "HIGH",
                    "summary": "Requests sends HTTP Authorization header to redirect targets",
                    "details": "Requests library forwards auth headers to redirect destinations, enabling SSRF",
                    "fixed_in_versions": ["2.20.0"],
                    "references": [],
                }
            ],
        },
        {
            "package_name": "certifi",
            "ecosystem": "pypi",
            "pinned_version": "2017.4.17",
            "latest_version": "2024.2.2",
            "is_eol": True,
            "eol_date": "2022-05-01",
            "vulnerabilities": [],
        },
    ],
    "dual-ci": [
        {
            "package_name": "Flask",
            "ecosystem": "pypi",
            "pinned_version": "2.2.0",
            "latest_version": "3.0.2",
            "is_eol": False,
            "eol_date": None,
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2023-30861",
                    "osv_id": "GHSA-m2qf-hxjv-5gpq",
                    "severity": "HIGH",
                    "summary": "Flask vulnerable to possible disclosure of permanent session cookie",
                    "details": "Flask does not set Vary: Cookie header, allowing proxy caches to serve cached sessions",
                    "fixed_in_versions": ["2.3.2"],
                    "references": [],
                }
            ],
        },
        {
            "package_name": "Werkzeug",
            "ecosystem": "pypi",
            "pinned_version": "2.2.0",
            "latest_version": "3.0.1",
            "is_eol": False,
            "eol_date": None,
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2023-25577",
                    "osv_id": "GHSA-px8h-6qxv-m22q",
                    "severity": "MEDIUM",
                    "summary": "Werkzeug multipart data parser resource exhaustion",
                    "details": "Parsing multipart/form-data with many fields triggers quadratic complexity",
                    "fixed_in_versions": ["2.2.3"],
                    "references": [],
                }
            ],
        },
    ],
    "fullstack-monorepo": [
        {
            "package_name": "fastapi",
            "ecosystem": "pypi",
            "pinned_version": "0.92.0",
            "latest_version": "0.110.0",
            "is_eol": False,
            "eol_date": None,
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2024-24762",
                    "osv_id": "GHSA-2jv5-9r88-3w3p",
                    "severity": "MEDIUM",
                    "summary": "FastAPI denial of service via ReDoS in form data parsing",
                    "details": "python-multipart used by FastAPI has a ReDoS vulnerability in content-type header parsing",
                    "fixed_in_versions": ["0.109.1"],
                    "references": [],
                }
            ],
        },
        {
            "package_name": "starlette",
            "ecosystem": "pypi",
            "pinned_version": "0.25.0",
            "latest_version": "0.37.2",
            "is_eol": False,
            "eol_date": None,
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2023-29159",
                    "osv_id": "GHSA-v5gw-mw7f-84px",
                    "severity": "LOW",
                    "summary": "Starlette directory traversal via static file path",
                    "details": "Improper path normalisation in static file handler allows reading files outside root",
                    "fixed_in_versions": ["0.27.0"],
                    "references": [],
                }
            ],
        },
    ],
    "go-microservice": [
        {
            "package_name": "github.com/gin-gonic/gin",
            "ecosystem": "go",
            "pinned_version": "v1.7.5",
            "latest_version": "v1.9.1",
            "is_eol": False,
            "eol_date": None,
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2023-26125",
                    "osv_id": "GHSA-h395-qcrr-msq3",
                    "severity": "MEDIUM",
                    "summary": "Gin lacks protection against request smuggling via improper header parsing",
                    "details": "Missing validation of Content-Length header allows HTTP request smuggling",
                    "fixed_in_versions": ["v1.9.0"],
                    "references": [],
                }
            ],
        },
    ],
    "react-spa": [
        {
            "package_name": "axios",
            "ecosystem": "npm",
            "pinned_version": "0.21.1",
            "latest_version": "1.6.7",
            "is_eol": False,
            "eol_date": None,
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2021-3749",
                    "osv_id": "GHSA-cph5-m8f7-6c5x",
                    "severity": "LOW",
                    "summary": "axios ReDoS via inefficient regular expression",
                    "details": "Inefficient regular expression in trim() function leads to denial of service",
                    "fixed_in_versions": ["0.21.2"],
                    "references": [],
                }
            ],
        },
    ],
    "java-maven-jenkins": [
        {
            "package_name": "spring-web",
            "ecosystem": "maven",
            "pinned_version": "5.3.0",
            "latest_version": "6.1.4",
            "is_eol": False,
            "eol_date": None,
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2021-22096",
                    "osv_id": "GHSA-562r-vg33-8x8h",
                    "severity": "LOW",
                    "summary": "Spring Framework log injection vulnerability",
                    "details": "Log injection is possible via crafted user input without proper sanitisation",
                    "fixed_in_versions": ["5.3.12"],
                    "references": [],
                }
            ],
        },
    ],
    "legacy-migration": [
        {
            "package_name": "Newtonsoft.Json",
            "ecosystem": "nuget",
            "pinned_version": "12.0.1",
            "latest_version": "13.0.3",
            "is_eol": False,
            "eol_date": None,
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2024-21907",
                    "osv_id": "GHSA-5crp-9r3c-p9vx",
                    "severity": "MEDIUM",
                    "summary": "Newtonsoft.Json vulnerable to ReDoS",
                    "details": "Improper handling of exceptional conditions in JSON parsing enables ReDoS",
                    "fixed_in_versions": ["13.0.1"],
                    "references": [],
                }
            ],
        },
    ],
}

# Define default file names and content for different languages
DEFAULT_FILE_NAMES = {
    "Python": [
        "README.md",
        "requirements.txt",
        "app.py",
        "tests/test_app.py",
        "config.yaml"
    ],
    "TypeScript": [
        "src/index.ts",
        "public/index.html",
        "vite.config.ts",
        ".eslintrc"
    ],
    "JavaScript": [],
    "Java": [
        "README.md",
        "pom.xml",
        "Jenkinsfile",
        "src/main/java/App.java",
        "src/test/java/AppTest.java"
    ],
    "C#": [
        "README.md",
        "packages.config",
        ".csproj",
        "app.config",
        "src/Program.cs",
        "tests/ProgramTests.cs"
    ],
    "Go": [
        "README.md",
        "go.mod",
        "go.sum",
        "main.go",
        "Makefile"
    ]
}

DEFAULT_MANIFESTS = {
    "Python": {
        "requirements.txt": "# Python dependencies\nFlask==2.3.0\nrequests==2.31.0\npython-dotenv==1.0.0"
    },
    "TypeScript": {
        "package.json": '{"name": "react-spa", "version": "1.0.0", "dependencies": {"react": "^18.2.0"}}',
        "tsconfig.json": '{"compilerOptions": {"target": "ES6", "module": "commonjs", "strict": true}}'
    },
    "JavaScript": {},
    "Java": {
        "pom.xml": '<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">\n  <modelVersion>4.0.0</modelVersion>\n  <groupId>com.example</groupId>\n  <artifactId>java-maven-jenkins</artifactId>\n  <version>1.0-SNAPSHOT</version>\n</project>',
        "Jenkinsfile": 'pipeline {\n    agent any\n    stages {\n        stage(\'Build\') {\n            steps {\n                echo \'Building..\'\n            }\n        }\n        stage(\'Test\') {\n            steps {\n                echo \'Testing..\'\n            }\n        }\n        stage(\'Deploy\') {\n            steps {\n                echo \'Deploying....\'\n            }\n        }\n    }\n}'
    },
    "C#": {
        "packages.config": '<packages>\n  <package id="NUnit" version="3.12.0" targetFramework="net5.0" />\n</packages>',
        ".csproj": '<Project Sdk="Microsoft.NET.Sdk">\n\n  <PropertyGroup>\n    <OutputType>Exe</OutputType>\n    <TargetFramework>net5.0</TargetFramework>\n  </PropertyGroup>\n\n</Project>',
        "app.config": '<?xml version="1.0" encoding="utf-8" ?>\n<configuration>\n  <startup>\n    <supportedRuntime version="v4.0" sku=".NETFramework,Version=v5.0" />\n  </startup>\n</configuration>'
    },
    "Go": {
        "go.mod": 'module go-microservice\n\ngo 1.18',
        "go.sum": '',
        "Makefile": 'build:\n\tgo build -o app .\nrun:\n\t./app'
    }
}

# Define branch names for each repo
DEFAULT_BRANCHES = {
    "Python": ["main", "develop", "feature/docker"],
    "TypeScript": ["main", "develop", "feature/react-component"],
    "JavaScript": [],
    "Java": ["main", "develop", "feature/maven-plugin"],
    "C#": ["main", "develop", "feature/nuget-update"],
    "Go": ["main", "develop", "feature/gin-router"]
}

# ---------------------------------------------------------------------------
# Enrichment helpers (deterministic, no external dependencies)
# ---------------------------------------------------------------------------

_FIRST_NAMES = ["Alice", "Bob", "Charlie", "David", "Eve"]
_LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
_DOMAINS = ["example.com", "test.org", "sample.net"]


def _realistic_name() -> str:
    return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"


def _realistic_email(name: str) -> str:
    first, last = name.split()
    return f"{first.lower()}.{last.lower()}@{random.choice(_DOMAINS)}"


def _commit_hash() -> str:
    return "".join(random.choices("0123456789abcdef", k=40))


def _random_date(start: datetime, end: datetime) -> datetime:
    delta_days = int((end - start).total_seconds() / 86400)
    return start + timedelta(days=random.randint(0, max(delta_days, 0)))


def _load_pattern(config: dict, template_name: str) -> dict:
    """Return the merged pattern config for a template."""
    tmpl = config["repo_templates"][template_name]
    pat = config["patterns"][tmpl["pattern"]]
    return {
        "commit_message_themes": tmpl["commit_message_themes"],
        "pr_title_themes": tmpl["pr_title_themes"],
        "commit_min": pat["commits"]["min"],
        "commit_max": pat["commits"]["max"],
        "pr_min": pat["pull_requests"]["min"],
        "pr_max": pat["pull_requests"]["max"],
        "commit_meta": pat["commit_metadata"],
        "pr_meta": pat["pr_metadata"],
        "pr_status": pat["pr_status"],
    }


def _generate_commits(cfg: dict, end_date: datetime) -> list[dict]:
    start_date = end_date - timedelta(days=90)
    num = random.randint(cfg["commit_min"], cfg["commit_max"])
    dates = sorted(_random_date(start_date, end_date) for _ in range(num))
    cm = cfg["commit_meta"]
    commits = []
    for dt in dates:
        author = _realistic_name()
        committer = random.choice([author, _realistic_name()])
        commits.append({
            "commit_hash": _commit_hash(),
            "author_name": author,
            "author_email": _realistic_email(author),
            "committer_name": committer,
            "committer_email": _realistic_email(committer),
            "message": random.choice(cfg["commit_message_themes"]),
            "commit_date": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "files_changed": random.randint(cm["files_changed"]["min"], cm["files_changed"]["max"]),
            "lines_added": random.randint(cm["lines_added"]["min"], cm["lines_added"]["max"]),
            "lines_removed": random.randint(cm["lines_removed"]["min"], cm["lines_removed"]["max"]),
        })
    return commits


def _generate_pull_requests(cfg: dict, branch_names: list[str], end_date: datetime) -> list[dict]:
    start_date = end_date - timedelta(days=90)
    num = random.randint(cfg["pr_min"], cfg["pr_max"])
    status_keys = list(cfg["pr_status"].keys())
    status_weights = [cfg["pr_status"][k] for k in status_keys]
    pm = cfg["pr_meta"]
    default_branch = branch_names[0] if branch_names else "main"
    feature_branches = branch_names[1:] if len(branch_names) > 1 else ["feature/update"]
    prs = []
    for pr_number in range(1, num + 1):
        created_at = _random_date(start_date, end_date)
        status = random.choices(status_keys, weights=status_weights, k=1)[0]
        author = _realistic_name()
        pr: dict = {
            "pr_number": pr_number,
            "title": random.choice(cfg["pr_title_themes"]),
            "description": f"Added {random.choice(cfg['pr_title_themes'])}",
            "source_branch": random.choice(feature_branches),
            "target_branch": default_branch,
            "status": status,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author_name": author,
            "author_email": _realistic_email(author),
            "review_comments": random.randint(0, 5),
            "commits_count": random.randint(1, 5),
            "files_changed": random.randint(pm["files_changed"]["min"], pm["files_changed"]["max"]),
            "lines_added": random.randint(pm["lines_added"]["min"], pm["lines_added"]["max"]),
            "lines_removed": random.randint(pm["lines_removed"]["min"], pm["lines_removed"]["max"]),
        }
        if status == "merged":
            pr["merged_at"] = _random_date(created_at, end_date).strftime("%Y-%m-%dT%H:%M:%SZ")
        elif status == "closed":
            pr["closed_at"] = _random_date(created_at, end_date).strftime("%Y-%m-%dT%H:%M:%SZ")
        prs.append(pr)
    return prs


def _repo_rng_seed(name: str) -> int:
    """Return a stable 32-bit integer seed derived from the repo name."""
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


# ---------------------------------------------------------------------------
# Seed generation (complete fixtures in a single pass)
# ---------------------------------------------------------------------------

def generate_repo_seed(config, repo_set):
    template_name = repo_set["template"]
    template = config["repo_templates"][template_name]

    if "names" in repo_set:
        names = repo_set["names"]
    else:
        name_template = repo_set.get("name_template", "{service}")
        services = repo_set["services"]
        names = [name_template.format(service=s) for s in services]

    # Fixed reference date so the generator is fully deterministic across runs.
    # Update this date when you want to advance the fixture timeline.
    end_date = datetime(2026, 4, 1, tzinfo=timezone.utc)

    # Load the pattern config for commits/PRs.
    pat = _load_pattern(config, template_name)
    is_empty = pat["commit_max"] == 0

    seeds = []
    for name in names:
        description_template = repo_set.get("description_template", template.get("description"))
        description = description_template if not description_template else description_template.format(service=name.split('-')[-1])

        languages = template["languages"]

        file_names = []
        manifests = {}
        for lang in languages:
            if lang in DEFAULT_FILE_NAMES:
                file_names.extend(DEFAULT_FILE_NAMES[lang])
            if lang in DEFAULT_MANIFESTS:
                manifests.update(DEFAULT_MANIFESTS[lang])

        branches = DEFAULT_BRANCHES.get(template_name, ["main", "develop"])

        # Vulnerability data is fully deterministic — no RNG needed.
        vulnerability_data = VULNERABILITY_DATA_BY_TEMPLATE.get(template_name, [])

        # Seed the PRNG from the repo name so commit/PR data is stable across
        # re-runs while still varying between repos.
        random.seed(_repo_rng_seed(name))

        if is_empty:
            commits: list[dict] = []
            pull_requests: list[dict] = []
        else:
            commits = _generate_commits(pat, end_date)
            pull_requests = _generate_pull_requests(pat, branches, end_date)

        seed = {
            "name": name,
            "description": description,
            "languages": languages,
            "file_names": sorted(set(file_names)),
            "manifests": manifests,
            "branches": branches,
            "vulnerability_data": vulnerability_data,
            "commits": commits,
            "pull_requests": pull_requests,
        }

        seeds.append(seed)

    return seeds


def main():
    config_path = Path("tests/fixtures/scenarios/config.json")
    output_dir = Path("tests/fixtures/scenarios/generated/")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(config_path) as f:
        config = json.load(f)

    seeds = []
    for repo_set in config["repo_sets"]:
        seeds.extend(generate_repo_seed(config, repo_set))

    for seed in seeds:
        output_file = output_dir / f"{seed['name']}.json"
        with open(output_file, "w") as f:
            json.dump(seed, f, indent=2)
        print(f"[OK] Created {seed['name']}.json")

    print(f"[OK] Generated {len(seeds)} seed files")


if __name__ == "__main__":
    main()