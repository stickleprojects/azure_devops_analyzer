#!/usr/bin/env python3
"""Generate test fixture JSON files for plan 013.

No LLM needed — all scenario data is deterministic from the plan spec.

AI-generated fixtures are placed in tests/fixtures/scenarios/generated/ to distinguish
them from manually created scenarios.

Usage:
    python scripts/generate-013-fixtures.py
"""

import json
import pathlib

SCENARIOS_DIR = pathlib.Path(__file__).parent.parent / "tests" / "fixtures" / "scenarios" / "generated"

SCENARIOS = [
    {
        "name": "python-docker",
        "description": "Python service with Docker and GitHub Actions CI",
        "file_names": [
            "requirements.txt",
            "src/main.py",
            "src/__init__.py",
            "Dockerfile",
            "docker-compose.yml",
            ".github/workflows/ci.yml",
            "README.md",
        ],
        "language_data": [
            {"language": "Python", "byte_count": 12000, "percentage": 85.0}
        ],
        "manifests": [
            {
                "file_path": "requirements.txt",
                "content": "flask==3.0.0\nrequests==2.31.0\ncelery==5.3.4\n",
                "ecosystem": "pypi",
            }
        ],
    },
    {
        "name": "react-spa",
        "description": "React SPA with TypeScript and GitHub Actions",
        "file_names": [
            "package.json",
            "tsconfig.json",
            "src/App.tsx",
            "src/index.tsx",
            "public/index.html",
            ".github/workflows/ci.yml",
            "README.md",
        ],
        "language_data": [
            {"language": "TypeScript", "byte_count": 25000, "percentage": 90.0},
            {"language": "HTML", "byte_count": 2000, "percentage": 7.0},
            {"language": "CSS", "byte_count": 1000, "percentage": 3.0},
        ],
        "manifests": [
            {
                "file_path": "package.json",
                "content": '{\n  "name": "react-spa",\n  "version": "1.0.0",\n  "dependencies": {\n    "react": "^18.2.0",\n    "react-dom": "^18.2.0"\n  },\n  "devDependencies": {\n    "typescript": "^5.0.0",\n    "@types/react": "^18.2.0"\n  }\n}\n',
                "ecosystem": "npm",
            }
        ],
    },
    {
        "name": "java-maven-jenkins",
        "description": "Java service with Maven build and Jenkins CI",
        "file_names": [
            "pom.xml",
            "Jenkinsfile",
            "src/main/java/com/example/App.java",
            "src/test/java/com/example/AppTest.java",
            "README.md",
        ],
        "language_data": [
            {"language": "Java", "byte_count": 20000, "percentage": 95.0}
        ],
        "manifests": [
            {
                "file_path": "pom.xml",
                "content": '<?xml version="1.0" encoding="UTF-8"?>\n<project>\n  <groupId>com.example</groupId>\n  <artifactId>app</artifactId>\n  <version>1.0.0</version>\n  <dependencies>\n    <dependency>\n      <groupId>org.springframework.boot</groupId>\n      <artifactId>spring-boot-starter-web</artifactId>\n      <version>3.1.0</version>\n    </dependency>\n  </dependencies>\n</project>\n',
                "ecosystem": "maven",
            }
        ],
    },
    {
        "name": "fullstack-monorepo",
        "description": "Python backend with React frontend in a monorepo",
        "file_names": [
            "requirements.txt",
            "src/api/main.py",
            "src/api/__init__.py",
            "frontend/package.json",
            "frontend/src/App.tsx",
            "Dockerfile",
            "docker-compose.yml",
            ".github/workflows/ci.yml",
            "README.md",
        ],
        "language_data": [
            {"language": "Python", "byte_count": 15000, "percentage": 55.0},
            {"language": "TypeScript", "byte_count": 12000, "percentage": 45.0},
        ],
        "manifests": [
            {
                "file_path": "requirements.txt",
                "content": "fastapi==0.104.0\nuvicorn==0.24.0\npydantic==2.4.0\n",
                "ecosystem": "pypi",
            },
            {
                "file_path": "frontend/package.json",
                "content": '{\n  "name": "frontend",\n  "dependencies": {\n    "react": "^18.2.0",\n    "axios": "^1.5.0"\n  }\n}\n',
                "ecosystem": "npm",
            },
        ],
    },
    {
        "name": "dotnet-legacy",
        "description": ".NET service with both legacy packages.config and new .csproj, Azure Pipelines CI",
        "file_names": [
            "MyApp.csproj",
            "packages.config",
            "azure-pipelines.yml",
            "src/Program.cs",
            "src/Controllers/HomeController.cs",
            "README.md",
        ],
        "language_data": [
            {"language": "C#", "byte_count": 18000, "percentage": 98.0}
        ],
        "manifests": [
            {
                "file_path": "MyApp.csproj",
                "content": '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n    <TargetFramework>net8.0</TargetFramework>\n  </PropertyGroup>\n  <ItemGroup>\n    <PackageReference Include="Microsoft.AspNetCore.App" />\n    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />\n  </ItemGroup>\n</Project>\n',
                "ecosystem": "nuget",
            },
            {
                "file_path": "packages.config",
                "content": '<?xml version="1.0" encoding="utf-8"?>\n<packages>\n  <package id="Newtonsoft.Json" version="6.0.4" targetFramework="net45" />\n</packages>\n',
                "ecosystem": "nuget",
            },
        ],
    },
    {
        "name": "dual-ci",
        "description": "Repository with both Jenkins and GitHub Actions CI configured",
        "file_names": [
            "Jenkinsfile",
            ".github/workflows/ci.yml",
            "requirements.txt",
            "src/app.py",
            "README.md",
        ],
        "language_data": [
            {"language": "Python", "byte_count": 5000, "percentage": 100.0}
        ],
        "manifests": [
            {
                "file_path": "requirements.txt",
                "content": "flask==3.0.0\npytest==7.4.0\n",
                "ecosystem": "pypi",
            }
        ],
    },
    {
        "name": "python-dual-deps",
        "description": "Python project with both Pipfile and requirements.txt present",
        "file_names": [
            "Pipfile",
            "Pipfile.lock",
            "requirements.txt",
            "app.py",
            "README.md",
        ],
        "language_data": [
            {"language": "Python", "byte_count": 3000, "percentage": 100.0}
        ],
        "manifests": [
            {
                "file_path": "Pipfile",
                "content": '[source]\nurl = "https://pypi.org/simple"\n\n[packages]\nrequests = "*"\nflask = ">=2.0"\n\n[dev-packages]\npytest = "*"\n',
                "ecosystem": "pypi",
            },
            {
                "file_path": "requirements.txt",
                "content": "requests==2.31.0\nflask==3.0.0\n",
                "ecosystem": "pypi",
            },
        ],
    },
    {
        "name": "go-microservice",
        "description": "Go microservice with Docker only, sparse file tree",
        "file_names": [
            "go.mod",
            "go.sum",
            "main.go",
            "Dockerfile",
            "README.md",
        ],
        "language_data": [
            {"language": "Go", "byte_count": 4000, "percentage": 100.0}
        ],
        "manifests": [
            {
                "file_path": "go.mod",
                "content": "module github.com/example/service\n\ngo 1.21\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.1\n)\n",
                "ecosystem": "go",
            }
        ],
    },
    {
        "name": "empty-stub",
        "description": "Repository with no code — README only",
        "file_names": ["README.md"],
        "language_data": [],
        "manifests": [],
    },
    {
        "name": "deep-nested-manifests",
        "description": "Manifests only in subdirectories, no root-level manifest files",
        "file_names": [
            "services/api/requirements.txt",
            "services/api/src/main.py",
            "services/web/package.json",
            "services/web/src/index.ts",
            "README.md",
        ],
        "language_data": [
            {"language": "Python", "byte_count": 8000, "percentage": 50.0},
            {"language": "TypeScript", "byte_count": 8000, "percentage": 50.0},
        ],
        "manifests": [
            {
                "file_path": "services/api/requirements.txt",
                "content": "fastapi==0.104.0\nuvicorn==0.24.0\n",
                "ecosystem": "pypi",
            },
            {
                "file_path": "services/web/package.json",
                "content": '{\n  "name": "web",\n  "dependencies": {\n    "react": "^18.2.0"\n  }\n}\n',
                "ecosystem": "npm",
            },
        ],
    },
]


def main() -> None:
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    for scenario in SCENARIOS:
        out_path = SCENARIOS_DIR / f"{scenario['name']}.json"
        out_path.write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")
        print(f"  [OK] {out_path.relative_to(pathlib.Path.cwd())}")
    print(f"\nCreated {len(SCENARIOS)} scenario files in {SCENARIOS_DIR.relative_to(pathlib.Path.cwd())}/")


if __name__ == "__main__":
    main()
