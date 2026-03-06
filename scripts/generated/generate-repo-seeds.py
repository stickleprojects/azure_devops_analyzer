#!/usr/bin/env python3
"""Generate fixture repository seed JSON files from config.json."""

import json
from pathlib import Path

# Define default file lists and manifests based on language patterns
DEFAULT_FILES = {
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
        "tsconfig.json"
    ],
    "JavaScript": [
        "src/index.js",
        "public/index.html",
        "package.json"
    ],
    "Java": [
        "pom.xml",
        "Jenkinsfile",
        "README.md"
    ],
    "C#": [
        "packages.config",
        ".csproj",
        "app.config",
        "README.md"
    ],
    "Go": [
        "main.go",
        "Makefile",
        "go.mod",
        "go.sum"
    ]
}

DEFAULT_MANIFESTS = {
    "Python": {
        "requirements.txt": "# Python dependencies\nFlask==2.3.0\nrequests==2.31.0\npython-dotenv==1.0.0"
    },
    "TypeScript": {
        "package.json": '{"name": "react-spa", "version": "1.0.0", "dependencies": {"react": "^18.0.0"}}',
        "tsconfig.json": '{"compilerOptions": {"target": "es6", "module": "commonjs"}}'
    },
    "JavaScript": {
        "package.json": '{"name": "react-spa", "version": "1.0.0", "dependencies": {"react": "^18.0.0"}}'
    },
    "Java": {
        "pom.xml": "<project><modelVersion>4.0.0</modelVersion><groupId>com.example</groupId><artifactId>java-project</artifactId><version>1.0-SNAPSHOT</version></project>",
        "Jenkinsfile": "pipeline {\n  agent any\n  stages {\n    stage('Build') {\n      steps {\n        sh 'mvn clean package'\n      }\n    }\n  }\n}"
    },
    "C#": {
        "packages.config": "<packages><package id=\"Newtonsoft.Json\" version=\"13.0.1\" /></packages>",
        ".csproj": "<Project Sdk=\"Microsoft.NET.Sdk.Web\"><PropertyGroup><TargetFramework>net5.0</TargetFramework></PropertyGroup></Project>"
    },
    "Go": {
        "go.mod": "module go-microservice\n\ngo 1.18",
        "go.sum": ""
    }
}

# Define branches for each repository type
DEFAULT_BRANCHES = {
    "Python": ["main", "develop"],
    "TypeScript": ["main", "develop"],
    "JavaScript": ["main", "develop"],
    "Java": ["main", "develop"],
    "C#": ["main", "develop"],
    "Go": ["main", "develop"]
}

def generate_file_names(languages):
    file_names = []
    for language in languages:
        if language in DEFAULT_FILES:
            file_names.extend(DEFAULT_FILES[language])
    return list(set(file_names))

def generate_manifests(languages):
    manifests = {}
    for language in languages:
        if language in DEFAULT_MANIFESTS:
            manifests.update(DEFAULT_MANIFESTS[language])
    return manifests

def generate_branches(languages):
    branches = []
    for language in languages:
        if language in DEFAULT_BRANCHES:
            branches.extend(DEFAULT_BRANCHES[language])
    return list(set(branches))

def generate_repo_seed(name, description, languages):
    file_names = generate_file_names(languages)
    manifests = generate_manifests(languages)
    branches = generate_branches(languages)
    
    repo_seed = {
        "name": name,
        "description": description,
        "languages": languages,
        "file_names": file_names,
        "manifests": manifests,
        "branches": branches
    }
    return repo_seed

def load_config(config_path):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("Error: config.json not found. Using default 10-repo list.", file=sys.stderr)
        return {
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

def generate_repo_seeds(config):
    repo_sets = config["repo_sets"]
    repo_templates = config["repo_templates"]
    
    generated_repos = 0
    
    for repo_set in repo_sets:
        template_name = repo_set["template"]
        template = repo_templates[template_name]
        
        if "names" in repo_set:
            names = repo_set["names"]
        elif "name_template" in repo_set and "services" in repo_set:
            names = [repo_set["name_template"].format(service=s) for s in repo_set["services"]]
        else:
            continue
        
        description_template = repo_set.get("description_template", template.get("description"))
        
        for name in names:
            if description_template:
                description = description_template.format(service=name.split('-')[-1])
            else:
                description = template.get("description")
            
            languages = template["languages"]
            repo_seed = generate_repo_seed(name, description, languages)
            
            output_path = Path("tests/fixtures/scenarios/generated") / f"{name}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(repo_seed, f, indent=2)
            
            print(f"[OK] Created {name}.json")
            generated_repos += 1
    
    print(f"[OK] Generated {generated_repos} seed files")

if __name__ == "__main__":
    config_path = Path("tests/fixtures/scenarios/config.json")
    config = load_config(config_path)
    generate_repo_seeds(config)