# Analysis Engine

## Overview

The Analysis Engine processes raw data from Azure DevOps to generate actionable insights. It consists of multiple specialized analyzers that can run independently and in parallel.

## Analysis Modules

### 1. Language Detection

**Purpose**: Identify programming languages used in the repository

#### Implementation Options

- **GitHub Linguist**: Uses the `github-linguist` Ruby gem for accurate detection.
- **File Extension Analysis**: A fallback method that maps file extensions to languages and estimates usage based on file size.

### 2. Dependency Analysis

**Purpose**: Identify libraries, versions, and security vulnerabilities

#### Package File Parsers

Parsers extract dependency information from standard manifest files:

- **Python**: `requirements.txt`, `Pipfile`
- **Node.js**: `package.json`
- **Java**: `pom.xml`
- **.NET**: `.csproj`

#### Vulnerability Scanning

Queries the **OSV.dev API** to check identified packages and versions against known vulnerability databases. It normalizes severity scores (CVSS) to a standard scale (CRITICAL, HIGH, MEDIUM, LOW).

#### End-of-Life Detection

Checks the **endoflife.date API** to determine if the package version is no longer supported.

### 3. Repository Summarization

**Purpose**: Generate intelligent summaries of repository purpose and contents

Uses an LLM (Claude or OpenAI) to analyze the README content and file structure. It generates a concise summary, identifies key technologies, and describes the primary functionality.

### 4. Code Quality Analysis

**Purpose**: Identify code quality issues, security vulnerabilities, and best practice violations

#### SonarQube Integration

Runs the `sonar-scanner` CLI to analyze the repository and fetches results (bugs, vulnerabilities, code smells) from the SonarQube API.

#### Language-Specific Linters

Executes tools like `pylint` (Python) and `eslint` (JS/TS) on individual files. Results are aggregated and mapped to standard severity levels.

### 5. Contributor Analytics

**Purpose**: Calculate metrics about developer activity and patterns

Aggregates data from commits and PRs to track:

- **Activity**: Commit counts, lines added/removed, active days.
- **Collaboration**: PRs created, reviews given, approval rates.
- **Quality**: Commit message scoring based on best practices (length, structure, imperative mood).

### 6. Pull Request Analytics

**Purpose**: Evaluate PR quality, size, and review patterns

Evaluates PRs to identify:

- **Size**: Categorizes as Small, Medium, Large, or Extra Large based on files and lines changed.
- **Efficiency**: Calculates average time-to-merge.
- **Issues**: Flags PRs that are too large, have excessive comments, or were merged without approval.

### 7. Branch Analysis

**Purpose**: Analyze metrics at the branch level

Calculates branch-specific metrics including age, staleness (days since last commit), unique contributors, and divergence from the main branch.

## Analysis Orchestration

The orchestration layer coordinates the execution of all analysis modules, ensuring that dependencies (like extracting data before analyzing it) are met and that results are aggregated for storage.

## Checklist

- [ ] Language detection configured (Linguist or file extension fallback)
- [ ] Dependency parsers implemented for target ecosystems
- [ ] OSV.dev API integration for vulnerability scanning
- [ ] endoflife.date API integration for EOL detection
- [ ] SonarQube or linter integration for code quality
- [ ] LLM API configured for repository summarization
- [ ] Parallel execution configured via ThreadPoolExecutor

## Further Reading

- [OSV.dev API Documentation](https://osv.dev/docs/)
- [endoflife.date API](https://endoflife.date/docs/api)
- [SonarQube Documentation](https://docs.sonarsource.com/sonarqube/latest/)
- [GitHub Linguist](https://github.com/github-linguist/linguist)

## Next Steps

- See [04-data-storage.md](04-data-storage.md) for storing these analysis results
- Review [05-orchestration.md](05-orchestration.md) for scheduling analysis jobs
