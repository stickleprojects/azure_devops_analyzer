"""
Standalone test for GitHubExtractor.get_repositories method.

This test verifies that private repositories are correctly retrieved
for user accounts.

Setup:
    1. Create and activate venv:
       python -m venv .venv
       .venv\\Scripts\\activate  (Windows)
       source .venv/bin/activate  (Linux/Mac)

    2. Install dependencies:
       pip install PyGithub python-dotenv pytest

    3. Ensure .env file has GITHUB_TOKEN and GITHUB_USER set

    4. Run the test:
       pytest tests/test_github_extractor_standalone.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load .env at module level
load_dotenv()


class TestGetRepositoriesPrivateRepos:
    """Test cases for get_repositories with private repos."""

    def test_get_repositories_includes_private_repos_for_user(self):
        """
        Test that private repositories are included when fetching for a user.

        The current implementation has a bug where it calls:
            user = self.client.get_user()  # Gets authenticated user
            gh_repos = user.get_repos(visibility="all")

        But when organization param is a username (not an org), it should call:
            user = self.client.get_user(organization)
            gh_repos = user.get_repos(type="all")  # or affiliation param

        Additionally, visibility="all" only works for the authenticated user's
        own repos, not when fetching another user's repos.
        """
        from src.extractors.github.extractor import GitHubExtractor
        from src.extractors.base import Platform
        from github import GithubException

        # Create mock repos - one public, one private
        mock_public_repo = Mock()
        mock_public_repo.owner.login = "testuser"
        mock_public_repo.name = "public-repo"
        mock_public_repo.html_url = "https://github.com/testuser/public-repo"
        mock_public_repo.default_branch = "main"
        mock_public_repo.id = 12345
        mock_public_repo.created_at = None
        mock_public_repo.private = False

        mock_private_repo = Mock()
        mock_private_repo.owner.login = "testuser"
        mock_private_repo.name = "private-repo"
        mock_private_repo.html_url = "https://github.com/testuser/private-repo"
        mock_private_repo.default_branch = "main"
        mock_private_repo.id = 12346
        mock_private_repo.created_at = None
        mock_private_repo.private = True

        mock_repos = [mock_public_repo, mock_private_repo]

        # Mock the client
        mock_client = Mock()

        # Make get_organization raise an exception (user is not an org)
        mock_client.get_organization.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )

        # Mock get_user to return a user with repos
        mock_user = Mock()
        mock_user.get_repos.return_value = mock_repos
        mock_client.get_user.return_value = mock_user

        # Create extractor and inject mock client
        extractor = GitHubExtractor()
        extractor._client = mock_client

        # Call get_repositories for a user (not an org)
        repos = extractor.get_repositories("testuser")

        # Verify we got both repos
        assert len(repos) == 2
        repo_names = [r.name for r in repos]
        assert "public-repo" in repo_names
        assert "private-repo" in repo_names

        # Verify get_repos was called with visibility="all"
        mock_user.get_repos.assert_called_once_with(visibility="all")

    def test_get_repositories_org_does_not_use_visibility_param(self):
        """
        Test that organization repos don't use visibility param.

        Organizations use get_repos() without visibility - the token's
        permissions determine what repos are visible.
        """
        from src.extractors.github.extractor import GitHubExtractor
        from src.extractors.base import Platform

        # Create mock repo
        mock_repo = Mock()
        mock_repo.owner.login = "testorg"
        mock_repo.name = "org-repo"
        mock_repo.html_url = "https://github.com/testorg/org-repo"
        mock_repo.default_branch = "main"
        mock_repo.id = 12347
        mock_repo.created_at = None

        # Mock the client
        mock_client = Mock()
        mock_org = Mock()
        mock_org.get_repos.return_value = [mock_repo]
        mock_client.get_organization.return_value = mock_org

        # Create extractor and inject mock client
        extractor = GitHubExtractor()
        extractor._client = mock_client

        # Call get_repositories for an org
        repos = extractor.get_repositories("testorg")

        # Verify org.get_repos was called (not user.get_repos)
        mock_org.get_repos.assert_called_once()
        assert len(repos) == 1
        assert repos[0].name == "org-repo"


class TestGetRepositoriesLive:
    """
    Live integration tests against real GitHub API.

    These tests require valid credentials in .env file.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load environment variables."""
        self.github_token = os.environ.get("GITHUB_TOKEN")
        self.github_user = os.environ.get("GITHUB_USER")

    def test_extractor_returns_azure_devops_analyzer_repo(self):
        """
        Verify that the extractor returns the 'azure_devops_analyzer' repository.

        This is a specific regression test for a known missing private repo.
        """
        from src.extractors.github.extractor import GitHubExtractor

        extractor = GitHubExtractor()

        print(f"\n{'='*60}")
        print(f"Testing get_repositories for user: {self.github_user}")
        print(f"{'='*60}")

        repos = extractor.get_repositories(self.github_user)
        repo_names = [r.name for r in repos]

        print(f"\nExtractor returned {len(repos)} repositories:")
        for name in sorted(repo_names):
            print(f"  - {name}")

        # Check for the specific missing repo
        assert "azure_devops_analyzer" in repo_names, (
            f"Repository 'azure_devops_analyzer' not found in extractor results.\n"
            f"Returned repos: {sorted(repo_names)}"
        )
        print(f"\n✓ 'azure_devops_analyzer' found in results")

    def test_direct_api_finds_azure_devops_analyzer(self):
        """
        Verify that direct GitHub API calls can find 'azure_devops_analyzer'.

        This test bypasses the extractor to confirm the repo exists and is accessible.
        """
        from github import Github, Auth

        auth = Auth.Token(self.github_token)
        client = Github(auth=auth)

        print(f"\n{'='*60}")
        print("Direct API: Finding 'azure_devops_analyzer'")
        print(f"{'='*60}")

        # Method 1: Authenticated user's repos
        print("\n1. client.get_user().get_repos(visibility='all'):")
        auth_user = client.get_user()
        all_repos = list(auth_user.get_repos(visibility="all"))
        repo_names = [r.name for r in all_repos]
        found = "azure_devops_analyzer" in repo_names

        print(f"   Total repos: {len(all_repos)}")
        print(f"   'azure_devops_analyzer' found: {found}")

        if found:
            repo = next(r for r in all_repos if r.name == "azure_devops_analyzer")
            print(f"   Private: {repo.private}")
            print(f"   Owner: {repo.owner.login}")

        # Method 2: Try to get repo directly
        print(f"\n2. client.get_repo('{self.github_user}/azure_devops_analyzer'):")
        try:
            repo = client.get_repo(f"{self.github_user}/azure_devops_analyzer")
            print(f"   Found! Private: {repo.private}, Owner: {repo.owner.login}")
        except Exception as e:
            print(f"   Error: {e}")

        assert found, "azure_devops_analyzer not found via direct API call"

    def test_debug_extractor_code_path(self):
        """
        Debug which code path the extractor takes for the configured user.

        This helps identify if get_organization or get_user fallback is used.
        """
        from github import Github, Auth, GithubException

        auth = Auth.Token(self.github_token)
        client = Github(auth=auth)

        print(f"\n{'='*60}")
        print(f"Debugging extractor code path for: {self.github_user}")
        print(f"{'='*60}")

        # Check if user is treated as org or user
        print(f"\n1. Is '{self.github_user}' an organization?")
        try:
            org = client.get_organization(self.github_user)
            print(f"   YES - get_organization succeeded")
            print(f"   Org repos count: {org.get_repos().totalCount}")
        except GithubException as e:
            print(f"   NO - get_organization failed: {e.status}")
            print(f"   Extractor will fall back to get_user()")

        # What does get_user() return?
        print(f"\n2. client.get_user() (no args - authenticated user):")
        auth_user = client.get_user()
        print(f"   Login: {auth_user.login}")
        print(f"   Same as GITHUB_USER? {auth_user.login == self.github_user}")

        # Compare repo counts
        print(f"\n3. Comparing repo retrieval methods:")

        repos_visibility_all = list(auth_user.get_repos(visibility="all"))
        repos_no_args = list(auth_user.get_repos())

        print(f"   get_repos(visibility='all'): {len(repos_visibility_all)} repos")
        print(f"   get_repos() [no args]:       {len(repos_no_args)} repos")

        # Check for azure_devops_analyzer in each
        names_visibility = {r.name for r in repos_visibility_all}
        names_no_args = {r.name for r in repos_no_args}

        print(f"\n4. 'azure_devops_analyzer' presence:")
        print(f"   In visibility='all': {'azure_devops_analyzer' in names_visibility}")
        print(f"   In no args:          {'azure_devops_analyzer' in names_no_args}")

        # Show what's different
        only_in_visibility = names_visibility - names_no_args
        only_in_no_args = names_no_args - names_visibility

        if only_in_visibility:
            print(f"\n   Only in visibility='all': {only_in_visibility}")
        if only_in_no_args:
            print(f"\n   Only in no args: {only_in_no_args}")


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
