#!/usr/bin/env python3
"""Generate test fixture JSON files for the test fixture system.

No LLM needed — all scenario data is deterministic from the spec.

AI-generated fixtures are placed in tests/fixtures/scenarios/generated/ to distinguish
them from manually created scenarios.

Usage:
    python scripts/generate-fixture-scenarios.py
"""

import json
import pathlib

SCENARIOS_DIR = pathlib.Path(__file__).parent.parent / "tests" / "fixtures" / "scenarios" / "generated"

SCENARIOS = [
    {
        "name": "python-docker",
        "description": "Python service with Docker and GitHub Actions CI",
        "file_names": ["requirements.txt", "src/main.py", "Dockerfile", "docker-compose.yml", ".github/workflows/ci.yml"],
        "language_data": [{"language": "Python", "byte_count": 12000, "percentage": 85.0}],
        "manifests": [
            {
                "file_path": "requirements.txt",
                "content": "flask==3.0.0\nrequests==2.31.0\ncelery==5.2.7\n",
                "ecosystem": "pypi"
            }
        ],
        "branches": [{"name": "main", "latest_commit_sha": "abc123def456"}],
        "commits": [
            {
                "sha": "abc123def456",
                "message": "Add Docker support",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "committer_email": "developer@example.com",
                "committer_name": "Developer",
                "commit_date": "2026-01-15T10:30:00",
                "files_changed": 3,
                "lines_added": 45,
                "lines_removed": 12
            }
        ],
        "pull_requests": [
            {
                "pr_number": 1,
                "platform_pr_id": "pr-1",
                "title": "Add Docker support",
                "description": "Adds Dockerfile and docker-compose configuration",
                "source_branch": "feature/docker",
                "target_branch": "main",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "status": "merged",
                "created_at": "2026-01-12T14:00:00",
                "merged_at": "2026-01-15T10:30:00",
                "files_changed": 3,
                "lines_added": 45,
                "lines_removed": 12
            }
        ]
    },
    {
        "name": "react-spa",
        "description": "React SPA with TypeScript and GitHub Actions",
        "file_names": ["package.json", "tsconfig.json", "src/App.tsx", "src/index.tsx", ".github/workflows/ci.yml"],
        "language_data": [
            {"language": "TypeScript", "byte_count": 15000, "percentage": 90.0},
            {"language": "HTML", "byte_count": 1200, "percentage": 7.0},
            {"language": "CSS", "byte_count": 800, "percentage": 3.0}
        ],
        "manifests": [
            {
                "file_path": "package.json",
                "content": '{"name": "react-app", "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"}}',
                "ecosystem": "npm"
            }
        ],
        "branches": [{"name": "main", "latest_commit_sha": "ghi789jkl012"}],
        "commits": [
            {
                "sha": "ghi789jkl012",
                "message": "Initial React SPA setup",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "committer_email": "developer@example.com",
                "committer_name": "Developer",
                "commit_date": "2026-01-10T09:00:00",
                "files_changed": 4,
                "lines_added": 85,
                "lines_removed": 0
            }
        ],
        "pull_requests": [
            {
                "pr_number": 2,
                "platform_pr_id": "pr-2",
                "title": "Initial React SPA setup",
                "description": "Sets up initial React application with TypeScript and GitHub Actions CI",
                "source_branch": "feature/react-spa",
                "target_branch": "main",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "status": "merged",
                "created_at": "2026-01-09T13:00:00",
                "merged_at": "2026-01-10T09:00:00",
                "files_changed": 4,
                "lines_added": 85,
                "lines_removed": 0
            }
        ]
    },
    {
        "name": "java-maven-jenkins",
        "description": "Java service with Maven and Jenkins CI",
        "file_names": ["pom.xml", "Jenkinsfile", "src/main/java/com/example/App.java"],
        "language_data": [{"language": "Java", "byte_count": 18000, "percentage": 95.0}],
        "manifests": [
            {
                "file_path": "pom.xml",
                "content": """<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>example-app</artifactId>
    <version>1.0-SNAPSHOT</version>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
    </dependencies>
</project>""",
                "ecosystem": "maven"
            }
        ],
        "branches": [{"name": "main", "latest_commit_sha": "jkl012mno345"}],
        "commits": [
            {
                "sha": "jkl012mno345",
                "message": "Add Maven and Jenkins setup",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "committer_email": "developer@example.com",
                "committer_name": "Developer",
                "commit_date": "2026-01-18T14:30:00",
                "files_changed": 3,
                "lines_added": 50,
                "lines_removed": 0
            }
        ],
        "pull_requests": [
            {
                "pr_number": 3,
                "platform_pr_id": "pr-3",
                "title": "Add Maven and Jenkins setup",
                "description": "Sets up Maven project with Jenkins CI",
                "source_branch": "feature/maven-jenkins",
                "target_branch": "main",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "status": "merged",
                "created_at": "2026-01-17T09:30:00",
                "merged_at": "2026-01-18T14:30:00",
                "files_changed": 3,
                "lines_added": 50,
                "lines_removed": 0
            }
        ]
    },
    {
        "name": "fullstack-monorepo",
        "description": "Python backend + React frontend in monorepo",
        "file_names": ["requirements.txt", "frontend/package.json", "src/api/main.py", "frontend/src/App.tsx"],
        "language_data": [
            {"language": "Python", "byte_count": 10000, "percentage": 55.0},
            {"language": "TypeScript", "byte_count": 8000, "percentage": 45.0}
        ],
        "manifests": [
            {
                "file_path": "requirements.txt",
                "content": "fastapi==0.92.0\nuvicorn==0.17.6\n",
                "ecosystem": "pypi"
            },
            {
                "file_path": "frontend/package.json",
                "content": '{"name": "react-app", "dependencies": {"react": "^18.2.0", "axios": "^1.3.4"}}',
                "ecosystem": "npm"
            }
        ],
        "branches": [{"name": "main", "latest_commit_sha": "mno345opq678"}],
        "commits": [
            {
                "sha": "mno345opq678",
                "message": "Initial monorepo setup",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "committer_email": "developer@example.com",
                "committer_name": "Developer",
                "commit_date": "2026-01-25T08:45:00",
                "files_changed": 4,
                "lines_added": 75,
                "lines_removed": 0
            }
        ],
        "pull_requests": [
            {
                "pr_number": 4,
                "platform_pr_id": "pr-4",
                "title": "Initial monorepo setup",
                "description": "Sets up a monorepo with Python backend and React frontend",
                "source_branch": "feature/monorepo",
                "target_branch": "main",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "status": "merged",
                "created_at": "2026-01-24T13:45:00",
                "merged_at": "2026-01-25T08:45:00",
                "files_changed": 4,
                "lines_added": 75,
                "lines_removed": 0
            }
        ]
    },
    {
        "name": "dotnet-legacy",
        "description": ".NET with both legacy packages.config and modern .csproj, Azure Pipelines",
        "file_names": ["MyApp.csproj", "packages.config", "azure-pipelines.yml", "src/Program.cs"],
        "language_data": [{"language": "C#", "byte_count": 16000, "percentage": 98.0}],
        "manifests": [
            {
                "file_path": "MyApp.csproj",
                "content": """<Project Sdk="Microsoft.NET.Sdk.Web">
    <PropertyGroup>
        <OutputType>Exe</OutputType>
        <TargetFramework>net6.0</TargetFramework>
    </PropertyGroup>
    <ItemGroup>
        <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
    </ItemGroup>
</Project>""",
                "ecosystem": "nuget"
            },
            {
                "file_path": "packages.config",
                "content": """<?xml version="1.0" encoding="utf-8"?>
<packages>
  <package id="Newtonsoft.Json" version="12.0.3" targetFramework="net6.0" />
</packages>""",
                "ecosystem": "nuget"
            }
        ],
        "branches": [{"name": "main", "latest_commit_sha": "opq678rst901"}],
        "commits": [
            {
                "sha": "opq678rst901",
                "message": "Add .NET with legacy and modern project formats",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "committer_email": "developer@example.com",
                "committer_name": "Developer",
                "commit_date": "2026-01-30T17:15:00",
                "files_changed": 4,
                "lines_added": 80,
                "lines_removed": 0
            }
        ],
        "pull_requests": [
            {
                "pr_number": 5,
                "platform_pr_id": "pr-5",
                "title": "Add .NET with legacy and modern project formats",
                "description": "Sets up a .NET project with both packages.config and .csproj",
                "source_branch": "feature/dotnet-legacy",
                "target_branch": "main",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "status": "merged",
                "created_at": "2026-01-29T12:15:00",
                "merged_at": "2026-01-30T17:15:00",
                "files_changed": 4,
                "lines_added": 80,
                "lines_removed": 0
            }
        ]
    },
    {
        "name": "dual-ci",
        "description": "Repository with both Jenkins and GitHub Actions",
        "file_names": ["Jenkinsfile", ".github/workflows/ci.yml", "requirements.txt", "src/app.py"],
        "language_data": [{"language": "Python", "byte_count": 12000, "percentage": 100.0}],
        "manifests": [
            {
                "file_path": "requirements.txt",
                "content": "flask==3.0.0\npytest==7.4.0\n",
                "ecosystem": "pypi"
            }
        ]
    },
    {
        "name": "python-dual-deps",
        "description": "Python with both Pipfile and requirements.txt",
        "file_names": ["Pipfile", "Pipfile.lock", "requirements.txt", "app.py"],
        "language_data": [{"language": "Python", "byte_count": 12000, "percentage": 100.0}],
        "manifests": [
            {
                "file_path": "Pipfile",
                "content": '[packages]\nflask = "==3.0.0"\npytest = "==7.4.0"',
                "ecosystem": "pypi"
            },
            {
                "file_path": "requirements.txt",
                "content": "flask==3.0.0\npytest==7.4.0\n",
                "ecosystem": "pypi"
            }
        ]
    },
    {
        "name": "go-microservice",
        "description": "Go microservice with sparse file tree",
        "file_names": ["go.mod", "go.sum", "main.go", "Dockerfile"],
        "language_data": [{"language": "Go", "byte_count": 14000, "percentage": 100.0}],
        "manifests": [
            {
                "file_path": "go.mod",
                "content": """module example.com/myservice

go 1.19

require (
    github.com/gin-gonic/gin v1.7.5
)""",
                "ecosystem": "golang"
            }
        ],
        "branches": [{"name": "main", "latest_commit_sha": "rst901stu234"}],
        "commits": [
            {
                "sha": "rst901stu234",
                "message": "Initial Go microservice setup",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "committer_email": "developer@example.com",
                "committer_name": "Developer",
                "commit_date": "2026-02-05T11:45:00",
                "files_changed": 4,
                "lines_added": 70,
                "lines_removed": 0
            }
        ],
        "pull_requests": [
            {
                "pr_number": 8,
                "platform_pr_id": "pr-8",
                "title": "Initial Go microservice setup",
                "description": "Sets up a Go microservice with Docker",
                "source_branch": "feature/go-microservice",
                "target_branch": "main",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "status": "merged",
                "created_at": "2026-02-04T16:45:00",
                "merged_at": "2026-02-05T11:45:00",
                "files_changed": 4,
                "lines_added": 70,
                "lines_removed": 0
            }
        ]
    },
    {
        "name": "empty-stub",
        "description": "Repository with no code (edge case)",
        "file_names": ["README.md"],
        "language_data": [],
        "manifests": []
    },
    {
        "name": "deep-nested-manifests",
        "description": "Manifests only in subdirectories (edge case)",
        "file_names": ["services/api/requirements.txt", "services/web/package.json", "services/api/src/main.py", "services/web/src/App.tsx"],
        "language_data": [
            {"language": "Python", "byte_count": 10000, "percentage": 50.0},
            {"language": "TypeScript", "byte_count": 8000, "percentage": 50.0}
        ],
        "manifests": [
            {
                "file_path": "services/api/requirements.txt",
                "content": "fastapi==0.92.0\nuvicorn==0.17.6\n",
                "ecosystem": "pypi"
            },
            {
                "file_path": "services/web/package.json",
                "content": '{"name": "react-app", "dependencies": {"react": "^18.2.0", "axios": "^1.3.4"}}',
                "ecosystem": "npm"
            }
        ],
        "branches": [{"name": "main", "latest_commit_sha": "stu234uvw567"}],
        "commits": [
            {
                "sha": "stu234uvw567",
                "message": "Add nested manifests",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "committer_email": "developer@example.com",
                "committer_name": "Developer",
                "commit_date": "2026-02-12T14:00:00",
                "files_changed": 4,
                "lines_added": 75,
                "lines_removed": 0
            }
        ],
        "pull_requests": [
            {
                "pr_number": 9,
                "platform_pr_id": "pr-9",
                "title": "Add nested manifests",
                "description": "Adds manifests in subdirectories for edge case testing",
                "source_branch": "feature/nested-manifests",
                "target_branch": "main",
                "author_email": "developer@example.com",
                "author_name": "Developer",
                "status": "merged",
                "created_at": "2026-02-11T09:00:00",
                "merged_at": "2026-02-12T14:00:00",
                "files_changed": 4,
                "lines_added": 75,
                "lines_removed": 0
            }
        ]
    }
]

def main() -> None:
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    for scenario in SCENARIOS:
        file_path = SCENARIOS_DIR / f"{scenario['name']}.json"
        with open(file_path, "w") as f:
            json.dump(scenario, f, indent=2)
        print(f"[OK] {file_path.relative_to(SCENARIOS_DIR)}")
    print("[OK] All scenarios generated.")

if __name__ == "__main__":
    main()