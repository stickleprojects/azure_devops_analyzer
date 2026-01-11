# Data Extraction Layer

## Overview

The Data Extraction Layer interfaces with Azure DevOps REST API to fetch all repository-related data needed for analysis. It handles authentication, rate limiting, pagination, and error recovery.

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

## Core Data Collection Modules

### 1. Repository Scanner

**Purpose**: Discover all repositories across projects

The scanner iterates through all projects in the organization (or a specific project if filtered) and retrieves the list of repositories using the Git client.

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

A rate limiter ensures the application respects Azure DevOps API limits by enforcing a maximum number of calls per second.

### Retry Logic with Exponential Backoff

API calls are wrapped with retry logic that uses exponential backoff to handle transient failures gracefully.

## Incremental Data Collection

### Change Detection

The system detects changes by comparing the current state with the last scan timestamp. It identifies new commits, new PRs, updated PRs, and new branches.

## Data Validation

Extracted data is validated to ensure required fields (like IDs and timestamps) are present before processing.

## Example Complete Extraction Workflow

The complete workflow initializes the connection, fetches the repository, and then sequentially extracts branches, commits, PRs, file trees, and contributor data.

## Next Steps

- See [03-analysis-engine.md](03-analysis-engine.md) for processing this extracted data
- Review [05-orchestration.md](05-orchestration.md) for scheduling extraction jobs
