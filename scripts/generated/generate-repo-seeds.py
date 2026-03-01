#!/usr/bin/env python3
"""Generate fixture repository seed JSON files from config.json."""

import json
from pathlib import Path
import sys

# Define default templates for file and manifest generation
def generate_file_names(template_name, service=None):
    """Generate typical file names based on template."""
    if template_name == "python-docker":
        return [
            "README.md",
            "Dockerfile",
            "requirements.txt",
            "app.py",
            "tests/test_app.py",
            "config.yaml"
        ]
    elif template_name == "go-microservice":
        return [
            "main.go",
            "cmd/main.go",
            "internal/handlers.go",
            "Makefile"
        ]
    elif template_name == "react-spa":
        return [
            "src/index.tsx",
            "public/index.html",
            "vite.config.ts",
            ".eslintrc"
        ]
    elif template_name == "fullstack-monorepo":
        return [
            "backend/app.py",
            "frontend/src/App.js",
            "services/auth/auth.js",
            "shared/utils.js",
            "docker-compose.yml"
        ]
    elif template_name == "java-maven-jenkins":
        return [
            "src/main/java/com/example/Main.java",
            "src/test/java/com/example/TestClass.java",
            ".mvn/wrapper/maven-wrapper.properties",
            "settings.xml"
        ]
    elif template_name == "legacy-migration":
        return [
            "src/BillingService.cs",
            "tests/BillingServiceTests.cs",
            "bin/",
            "obj/"
        ]
    elif template_name == "dual-ci":
        return [
            "app.py",
            "tests/test_app.py",
            "scripts/CI_script.sh"
        ]
    elif template_name == "python-dual-deps":
        return [
            "main.py",
            "src/module.py",
            "tests/test_module.py",
            "setup.py"
        ]
    elif template_name == "edge-case-empty":
        return [
            "README.md"
        ]
    elif template_name == "deep-nested-manifests":
        return [
            "services/backend/app.py",
            "services/frontend/src/App.js",
            "shared/config.yaml",
            "scripts/deploy.sh",
            "terraform/main.tf"
        ]
    else:
        return []

def generate_manifests(template_name, service=None):
    """Generate typical manifests based on template."""
    if template_name == "python-docker":
        return {
            "python": [
                {
                    "type": "requirements.txt",
                    "content": "# Python dependencies\nFlask==2.3.0\nrequests==2.31.0\npython-dotenv==1.0.0"
                }
            ]
        }
    elif template_name == "go-microservice":
        return {
            "go": [
                {
                    "type": "go.mod",
                    "content": "module example.com/microservice\n\ngo 1.18\nrequire github.com/gin-gonic/gin v1.7.4"
                },
                {
                    "type": "go.sum",
                    "content": "# go.sum contents omitted for brevity"
                }
            ]
        }
    elif template_name == "react-spa":
        return {
            "javascript": [
                {
                    "type": "package.json",
                    "content": '{"name": "react-app", "version": "1.0.0", "dependencies": {"react": "^17.0.2"}}'
                },
                {
                    "type": "tsconfig.json",
                    "content": '{"compilerOptions": {"target": "ES6", "module": "commonjs"}, "include": ["src"]}'
                }
            ]
        }
    elif template_name == "fullstack-monorepo":
        return {
            "python": [
                {
                    "type": "requirements.txt",
                    "content": "# Python dependencies\nFlask==2.3.0\nrequests==2.31.0"
                }
            ],
            "typescript": [
                {
                    "type": "package.json",
                    "content": '{"name": "frontend-app", "version": "1.0.0", "dependencies": {"react": "^17.0.2"}}'
                }
            ]
        }
    elif template_name == "java-maven-jenkins":
        return {
            "maven": [
                {
                    "type": "pom.xml",
                    "content": '<project><modelVersion>4.0.0</modelVersion><groupId>com.example</groupId><artifactId>app</artifactId><version>1.0-SNAPSHOT</version></project>'
                },
                {
                    "type": "Jenkinsfile",
                    "content": "pipeline { agent any; stages { stage('Build') { steps { echo 'Building..' } } } }"
                }
            ]
        }
    elif template_name == "legacy-migration":
        return {
            "csharp": [
                {
                    "type": "packages.config",
                    "content": "<packages><package id=\"Newtonsoft.Json\" version=\"13.0.1\" targetFramework=\"net472\" /></packages>"
                },
                {
                    "type": ".csproj",
                    "content": '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType></PropertyGroup></Project>'
                }
            ]
        }
    elif template_name == "dual-ci":
        return {
            "python": [
                {
                    "type": "requirements.txt",
                    "content": "# Python dependencies\nFlask==2.3.0\nrequests==2.31.0"
                },
                {
                    "type": "Jenkinsfile",
                    "content": "pipeline { agent any; stages { stage('Build') { steps { echo 'Building..' } } } }"
                }
            ]
        }
    elif template_name == "python-dual-deps":
        return {
            "pipenv": [
                {
                    "type": "Pipfile",
                    "content": "[packages]\nflask = \"^2.3.0\"\nrequests = \"^2.31.0\""
                },
                {
                    "type": "Pipfile.lock",
                    "content": "{\"_meta\": {\"sources\": [{\"url\": \"https://pypi.org/simple\", \"verify_ssl\": true}]}\"default\": {\"flask\": {\"version\": \"==2.3.0\"}, \"requests\": {\"version\": \"==2.31.0\"}}}"
                }
            ],
            "pip": [
                {
                    "type": "requirements.txt",
                    "content": "# Python dependencies\nFlask==2.3.0\nrequests==2.31.0"
                }
            ]
        }
    elif template_name == "edge-case-empty":
        return {}
    elif template_name == "deep-nested-manifests":
        return {
            "python": [
                {
                    "type": "requirements.txt",
                    "content": "# Python dependencies\nFlask==2.3.0"
                }
            ],
            "typescript": [
                {
                    "type": "package.json",
                    "content": '{"name": "frontend-app", "version": "1.0.0", "dependencies": {"react": "^17.0.2"}}'
                }
            ]
        }
    else:
        return {}

def main():
    # Define paths
    config_path = Path("tests/fixtures/scenarios/config.json")
    output_dir = Path("tests/fixtures/scenarios/generated/")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load configuration
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found. Using fallback configuration.", file=sys.stderr)
        config = {
            "repo_sets": [
                {"template": "python-docker", "names": ["python-docker"]},
                {"template": "go-microservice", "names": ["go-microservice"]},
                {"template": "react-spa", "names": ["react-spa"]},
                {"template": "fullstack-monorepo", "names": ["fullstack-monorepo"]},
                {"template": "java-maven-jenkins", "names": ["java-maven-jenkins"]},
                {"template": "legacy-migration", "names": ["legacy-migration"]},
                {"template": "dual-ci", "names": ["dual-ci"]},
                {"template": "python-dual-deps", "names": ["python-dual-deps"]},
                {"template": "edge-case-empty", "names": ["edge-case-empty"]},
                {"template": "deep-nested-manifests", "names": ["deep-nested-manifests"]}
            ]
        }

    # Process each repo set
    for repo_set in config["repo_sets"]:
        if "name_template" in repo_set:
            names = [repo_set["name_template"].format(service=service) for service in repo_set.get("services", [])]
            descriptions = [repo_set["description_template"].format(service=service) for service in repo_set.get("services", [])]
        elif "names" in repo_set:
            names = repo_set["names"]
            descriptions = [f"{repo_set['template']} repository"] * len(names)
        else:
            continue

        # Generate seed JSONs
        for name, description in zip(names, descriptions):
            template_name = repo_set.get("template", "unknown")
            if template_name not in config["repo_templates"]:
                print(f"Warning: Template '{template_name}' not found. Skipping {name}.", file=sys.stderr)
                continue

            template = config["repo_templates"][template_name]
            languages = template.get("languages", [])
            files = generate_file_names(template_name)
            manifests = generate_manifests(template_name)

            # Define branches
            branches = ["main", "develop"]
            if template_name != "edge-case-empty":
                branches.append(f"feature/{template_name.split('-')[-1]}")

            # Create seed JSON
            seed = {
                "name": name,
                "description": description,
                "languages": languages,
                "file_names": files,
                "manifests": manifests,
                "branches": branches
            }

            # Write to output file
            output_file = output_dir / f"{name}.json"
            with open(output_file, 'w') as f:
                json.dump(seed, f, indent=2)
            
            print(f"[OK] Created {output_file.name}")

    print(f"[OK] Generated {len(names)} seed files")

if __name__ == "__main__":
    main()