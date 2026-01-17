# Data Extraction Layer

## Overview

The Data Extraction Layer interfaces with repository hosting platforms (Azure DevOps and GitHub) to fetch all repository-related data needed for analysis. It uses a unified extractor interface to handle both platforms consistently, while managing platform-specific authentication, rate limiting, pagination, and error recovery.

## Platform Architecture

The extraction system uses an abstract `RepositoryExtractor` interface that both platform-specific extractors implement:

```
src/extractors/
├── base.py                    # Abstract interface + data classes
├── factory.py                 # Extractor factory
├── azure_devops/
│   ├── client.py              # Azure DevOps connection
│   └── extractor.py           # AzureDevOpsExtractor implementation
└── github/
    ├── client.py              # GitHub connection
    └── extractor.py           # GitHubExtractor implementation
```

Both extractors output identical data models (`RepositoryData`, `CommitData`, `PullRequestData`, etc.) ensuring the analysis and storage layers remain platform-agnostic.

## Azure DevOps API Authentication

### Personal Access Token (PAT)

**Creating a PAT**:

1. Navigate to Azure DevOps → User Settings → Personal Access Tokens
2. Click "New Token"
3. Set appropriate scopes:
   - **Code**: Read (for repository access)
   - **Code**: Status (for PR information)
   - **Graph**: Read (for user information)
   - **Project and Team**: Read (for project metadata)
4. Set expiration date (recommend 90-180 days with rotation)
5. Store securely in Azure Key Vault

**Using the PAT**:
The PAT is retrieved from a secure vault and used to authenticate the `azure.devops.connection.Connection` object.

## GitHub API Authentication

### Personal Access Token (PAT)

**Creating a GitHub PAT**:

1. Navigate to GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Set appropriate scopes:
   - **repo**: Full repository access (read for private repos)
   - **read:org**: Read organization membership (for org repos)
   - **read:user**: Read user profile data
4. Set expiration date (recommend 90 days with rotation)
5. Store securely in Azure Key Vault or environment variable

**Using the PAT**:
The token is passed to PyGithub's `Github` client for authentication.

### GitHub App (Alternative)

For organization-wide access with better rate limits:

1. Create a GitHub App in your organization settings
2. Generate a private key
3. Install the app on target repositories
4. Use app authentication for API calls

## Core Data Collection Modules

### 1. Repository Scanner

**Purpose**: Discover all repositories across projects

The scanner iterates through all projects in the organization (or a specific project if filtered) and retrieves the list of repositories using the Git client.
If there is a file `repository.json` in the repository then this should be used to identify further metadata about the repository. The repository.json file format is similar to this:

```
{
    "teamname":"myteam",
    "servicename":"myservice"
}
```

**Data Extracted**:

- Repository ID
- Repository name
- Project name
- Default branch
- Repository URL
- Size
- Creation date
- Last update date

### 2. Git Data Collector

**Purpose**: Fetch branches, commits, and file trees

#### Branch Collection

Fetches all branches for a repository, capturing the branch name, latest commit SHA, creator, and creation date.

#### Commit History Collection

Retrieves commit history with support for pagination and filtering by branch or date. It handles rate limiting by pausing between paged requests.

**Commit Data Extracted**:

- Commit SHA
- Author name and email
- Committer name and email
- Commit date
- Message
- Parent commit SHAs
- Change counts (additions, deletions, edits)

#### File Tree Collection

Recursively fetches the file structure for a specific branch, separating files and directories.

#### File Content Retrieval

Downloads the content of specific files (e.g., `requirements.txt`, `README.md`) for analysis.

### 3. Pull Request Collector

**Purpose**: Gather PR metadata, reviews, and comments

#### PR Metadata Collection

Fetches pull requests filtered by status (active, completed, abandoned). Captures metadata like title, description, branches, dates, and merge status.

#### PR Review and Comment Collection

Retrieves all comment threads and reviewer votes for a PR to analyze review depth and collaboration patterns.

#### PR File Changes

Identifies files changed in the latest iteration of a pull request.

### 4. Contributor Metadata Collector

**Purpose**: Gather information about repository contributors

Analyzes commit history to build a profile for each contributor, including commit counts, activity dates, and total changes.

## Rate Limiting and Error Handling

### Rate Limiting Strategy

Each platform has different rate limits:

**Azure DevOps**:

- Approximately 800 requests per 5 minutes per PAT
- A rate limiter ensures compliance by tracking calls per second

**GitHub**:

- 5,000 requests per hour for authenticated requests
- Secondary rate limits for specific endpoints (search, GraphQL)
- PyGithub automatically handles rate limit headers

### Retry Logic with Exponential Backoff

API calls are wrapped with retry logic that uses exponential backoff to handle transient failures gracefully.

## Incremental Data Collection

### Change Detection

The system detects changes by comparing the current state with the last scan timestamp. It identifies new commits, new PRs, updated PRs, and new branches.

## Data Validation

Extracted data is validated to ensure required fields (like IDs and timestamps) are present before processing.

## Example Complete Extraction Workflow

The complete workflow initializes the connection, fetches the repository, and then sequentially extracts branches, commits, PRs, file trees, and contributor data.

## Checklist

**Azure DevOps**:

- [ ] Personal Access Token (PAT) created with correct scopes
- [ ] PAT stored securely in Azure Key Vault
- [ ] `AZURE_DEVOPS_ORG_URL` and `AZURE_DEVOPS_PAT` environment variables set

**GitHub**:

- [ ] GitHub PAT created with correct scopes (or GitHub App configured)
- [ ] Token stored securely
- [ ] `GITHUB_TOKEN` environment variable set
- [ ] `GITHUB_ORG` or `GITHUB_USER` configured for repository discovery

**Both Platforms**:

- [ ] Rate limiter configured for API calls
- [ ] Retry logic implemented with exponential backoff
- [ ] Data validation enabled for extracted records
- [ ] Incremental extraction supported via timestamp filtering

## Further Reading

- [Azure DevOps REST API Documentation](https://learn.microsoft.com/en-us/rest/api/azure/devops/)
- [Azure DevOps Python SDK](https://github.com/microsoft/azure-devops-python-api)
- [Azure Key Vault Secrets Client](https://learn.microsoft.com/en-us/python/api/overview/azure/keyvault-secrets-readme)
- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [PyGithub Documentation](https://pygithub.readthedocs.io/)
- [GitHub API Rate Limiting](https://docs.github.com/en/rest/rate-limit)

## Next Steps

- See [03-analysis-engine.md](03-analysis-engine.md) for processing this extracted data
- Review [05-orchestration.md](05-orchestration.md) for scheduling extraction jobs
