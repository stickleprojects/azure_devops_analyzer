#!/usr/bin/env python3
"""Generate fixture repository seed JSON files from config.json."""

import json
from pathlib import Path

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

def generate_repo_seed(config, repo_set):
    template_name = repo_set["template"]
    template = config["repo_templates"][template_name]

    if "names" in repo_set:
        names = repo_set["names"]
    else:
        name_template = repo_set.get("name_template", "{service}")
        services = repo_set["services"]
        names = [name_template.format(service=s) for s in services]

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

        seed = {
            "name": name,
            "description": description,
            "languages": languages,
            "file_names": list(set(file_names)),
            "manifests": manifests,
            "branches": branches
        }

        seeds.append(seed)

    return seeds

def main():
    config_path = Path("tests/fixtures/scenarios/config.json")
    output_dir = Path("tests/fixtures/scenarios/generated/")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found. Using fallback 10-repo list.", file=sys.stderr)
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
                {"template": "edge-case-empty", "names": ["empty-repo"]},
                {"template": "deep-nested-manifests", "names": ["deep-nested-manifests"]}
            ]
        }

    seeds = []
    for repo_set in config["repo_sets"]:
        seeds.extend(generate_repo_seed(config, repo_set))

    for seed in seeds:
        output_file = output_dir / f"{seed['name']}.json"
        with open(output_file, 'w') as f:
            json.dump(seed, f, indent=2)
        print(f"[OK] Created {seed['name']}.json")

    print(f"[OK] Generated {len(seeds)} seed files")

if __name__ == "__main__":
    main()