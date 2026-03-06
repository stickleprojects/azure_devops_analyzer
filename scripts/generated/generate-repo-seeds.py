#!/usr/bin/env python3
"""Generate fixture repository seed JSON files from config.json."""

import json
from pathlib import Path

# Define default values and constants
DEFAULT_BRANCHES = ["main", "develop"]

def load_config(config_path):
    """Load the configuration JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found. Using fallback configuration.", file=sys.stderr)
        return {
            "patterns": {},
            "repo_templates": {},
            "repo_sets": []
        }

def generate_file_names(languages):
    """Generate typical file names based on languages."""
    files = ["README.md"]
    if "Python" in languages:
        files.extend([
            "requirements.txt",
            "app.py",
            "tests/test_app.py",
            "config.yaml"
        ])
    if "Go" in languages:
        files.extend([
            "main.go",
            "cmd/main.go",
            "internal/handlers.go",
            "Makefile"
        ])
    if "TypeScript" in languages or "JavaScript" in languages:
        files.extend([
            "src/index.tsx",
            "public/index.html",
            "vite.config.ts",
            ".eslintrc.json"
        ])
    if "Java" in languages:
        files.extend([
            "pom.xml",
            "Jenkinsfile",
            "src/main/java/com/example/Main.java",
            "src/test/java/com/example/MainTest.java"
        ])
    if "C#" in languages:
        files.extend([
            "packages.config",
            ".csproj",
            "app.config",
            "src/Program.cs",
            "tests/ProgramTests.cs"
        ])
    return files

def generate_manifests(languages):
    """Generate key manifests based on languages."""
    manifests = {}
    if "Python" in languages:
        manifests["python"] = [
            {
                "type": "requirements.txt",
                "content": "# Python dependencies\nFlask==2.3.0\nrequests==2.31.0\npython-dotenv==1.0.0"
            }
        ]
    if "Go" in languages:
        manifests["go"] = [
            {
                "type": "go.mod",
                "content": "module example.com/myservice\n\ngo 1.18"
            },
            {
                "type": "go.sum",
                "content": "# go.sum content\n# (this is a placeholder)"
            }
        ]
    if "TypeScript" in languages:
        manifests["typescript"] = [
            {
                "type": "package.json",
                "content": '{"name": "my-app", "version": "1.0.0", "dependencies": {"react": "^18.2.0"}}'
            },
            {
                "type": "tsconfig.json",
                "content": '{"compilerOptions": {"target": "es5", "module": "commonjs", "strict": true}}'
            }
        ]
    if "Java" in languages:
        manifests["java"] = [
            {
                "type": "pom.xml",
                "content": "<project><modelVersion>4.0.0</modelVersion><groupId>com.example</groupId><artifactId>myservice</artifactId><version>1.0-SNAPSHOT</version></project>"
            },
            {
                "type": "Jenkinsfile",
                "content": "pipeline {\n    agent any\n    stages {\n        stage('Build') {\n            steps {\n                echo 'Building..'\n            }\n        }\n    }\n}"
            }
        ]
    if "C#" in languages:
        manifests["csharp"] = [
            {
                "type": "packages.config",
                "content": "<packages><package id=\"Newtonsoft.Json\" version=\"13.0.1\" /></packages>"
            },
            {
                "type": ".csproj",
                "content": '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n    <OutputType>Exe</OutputType>\n    <TargetFramework>net5.0</TargetFramework>\n  </PropertyGroup>\n</Project>'
            }
        ]
    return manifests

def generate_repo(repo_set, repo_template):
    """Generate a repository seed based on the given set and template."""
    if "names" in repo_set:
        names = repo_set["names"]
    else:
        names = [repo_set["name_template"].format(service=s) for s in repo_set.get("services", [])]
    
    repos = []
    for name in names:
        description = (repo_set.get("description_template") or
                        repo_template.get("description")).format(service=name)
        languages = repo_template["languages"]
        file_names = generate_file_names(languages)
        manifests = generate_manifests(languages)
        branches = DEFAULT_BRANCHES + [f"feature/{service}" for service in name.split('-') if len(name.split('-')) > 1]
        
        repo = {
            "name": name,
            "description": description,
            "languages": languages,
            "file_names": file_names,
            "manifests": manifests,
            "branches": branches
        }
        repos.append(repo)
    return repos

def main():
    config_path = Path("tests/fixtures/scenarios/config.json")
    config = load_config(config_path)
    
    repo_sets = config.get("repo_sets", [])
    repo_templates = config.get("repo_templates", {})
    
    generated_repos = []
    for repo_set in repo_sets:
        template_name = repo_set["template"]
        repo_template = repo_templates.get(template_name, {})
        repos = generate_repo(repo_set, repo_template)
        generated_repos.extend(repos)
    
    output_dir = Path("tests/fixtures/scenarios/generated/")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for repo in generated_repos:
        file_path = output_dir / f"{repo['name']}.json"
        with open(file_path, 'w') as f:
            json.dump(repo, f, indent=2)
        print(f"[OK] Created {file_path.name}")
    
    print(f"[OK] Generated {len(generated_repos)} seed files")

if __name__ == "__main__":
    main()