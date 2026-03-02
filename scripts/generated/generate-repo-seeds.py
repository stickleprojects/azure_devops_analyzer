#!/usr/bin/env python3
"""Generate fixture repository seed JSON files from config.json."""

import json
from pathlib import Path

# Define a default list of repositories if config.json is not found
default_repos = [
    {"name": "repo1", "languages": ["Python"]},
    {"name": "repo2", "languages": ["JavaScript"]},
    # Add more default repos as needed
]

def load_config(config_path):
    """Load the configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: {config_path} not found. Using default repository list.", file=sys.stderr)
        return {"repo_sets": [{"names": [repo["name"] for repo in default_repos]}]}

def generate_file_names(languages):
    """Generate a list of typical file names based on languages."""
    files = ["README.md"]
    if "Python" in languages:
        files.extend([
            "Dockerfile",
            "requirements.txt",
            "app.py",
            "tests/test_app.py",
            "config.yaml"
        ])
    if "Go" in languages:
        files.extend([
            "main.go",
            "cmd/main.go",
            "internal/endpoint.go",
            "Makefile"
        ])
    if "TypeScript" in languages or "JavaScript" in languages:
        files.extend([
            "src/index.js",
            "public/index.html",
            "vite.config.ts",
            ".eslintrc.json"
        ])
    if "Java" in languages:
        files.extend([
            "pom.xml",
            "Jenkinsfile",
            "settings.xml",
            "src/main/java/Main.java",
            "src/test/java/Tests.java"
        ])
    if "C#" in languages:
        files.extend([
            "packages.config",
            ".csproj",
            "app.config",
            "src/Program.cs",
            "tests/Tests.cs"
        ])
    return files

def generate_manifests(languages):
    """Generate a list of typical manifests based on languages."""
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
                "content": """module example.com/microservice

go 1.19

require (
\tgithub.com/gin-gonic/gin v1.8.4
)"""
            }
        ]
    if "TypeScript" in languages or "JavaScript" in languages:
        manifests["javascript"] = [
            {
                "type": "package.json",
                "content": """{
  "name": "react-app",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^3.0.0",
    "vite": "^4.0.0"
  }
}"""
            }
        ]
    if "Java" in languages:
        manifests["java"] = [
            {
                "type": "pom.xml",
                "content": """<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>app</artifactId>
    <version>1.0-SNAPSHOT</version>
</project>"""
            }
        ]
    if "C#" in languages:
        manifests["csharp"] = [
            {
                "type": "packages.config",
                "content": """<?xml version="1.0" encoding="utf-8"?>
<packages>
  <package id="Newtonsoft.Json" version="13.0.1" targetFramework="net472" />
</packages>"""
            }
        ]
    return manifests

def generate_branches():
    """Generate a list of typical branches."""
    return ["main", "develop", "feature/docker"]

def expand_repos(config):
    """Expand concrete repos from repo_sets using repo_templates."""
    expanded_repos = []
    for repo_set in config.get("repo_sets", []):
        template_name = repo_set["template"]
        template = config["repo_templates"][template_name]
        
        if "names" in repo_set:
            names = repo_set["names"]
        elif "name_template" in repo_set and "services" in repo_set:
            names = [repo_set["name_template"].format(service=service) for service in repo_set["services"]]
        else:
            names = [template_name]
        
        for name in names:
            description = template.get("description")
            if "description_template" in repo_set:
                description = repo_set["description_template"].format(service=name)
            
            repo = {
                "name": name,
                "description": description,
                "languages": template["languages"],
                "file_names": generate_file_names(template["languages"]),
                "manifests": generate_manifests(template["languages"]),
                "branches": generate_branches()
            }
            expanded_repos.append(repo)
    
    return expanded_repos

def write_repo_seeds(expanded_repos, output_dir):
    """Write each expanded repo to a JSON file."""
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    
    for repo in expanded_repos:
        repo_file = output_dir / f"{repo['name']}.json"
        with open(repo_file, 'w') as f:
            json.dump(repo, f, indent=2)
        print(f"[OK] Created {repo_file.name}")

def main():
    config_path = Path("tests/fixtures/scenarios/config.json")
    config = load_config(config_path)
    
    expanded_repos = expand_repos(config)
    write_repo_seeds(expanded_repos, Path("tests/fixtures/scenarios/generated"))
    
    print(f"[OK] Generated {len(expanded_repos)} seed files")

if __name__ == "__main__":
    main()