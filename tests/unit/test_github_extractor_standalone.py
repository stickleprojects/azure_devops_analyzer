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
from src.config.github import GitHubExtractorConfig

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Note: Environment variables are loaded by tests/conftest.py
# which runs before test collection, ensuring .env.resolved is loaded


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
        mock_user.login = "testuser"
        mock_user.get_repos.return_value = mock_repos
        mock_client.get_user.return_value = mock_user

        # Create extractor and inject mock client
        extractor = GitHubExtractor()
        extractor._client = mock_client

        # Call get_repositories for a user (authenticated user scenario)
        repos = extractor.get_repositories("testuser")

        # Verify we got both repos
        assert len(repos) == 2
        repo_names = [r.name for r in repos]
        assert "public-repo" in repo_names
        assert "private-repo" in repo_names

        # Verify get_repos was called with visibility="all" (authenticated user)
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
        config = GitHubExtractorConfig.from_env()
        self.github_token = config.token
        self.github_user = config.user
        self.github_org = config.organization
        self.private_repo = config.private_repo
        
        # Skip tests if credentials are not configured
        if not self.github_token:
            pytest.skip("GITHUB_TOKEN must be set in .env for live tests")
        
        if not self.github_user and not self.github_org:
            pytest.skip("Either GITHUB_USER or GITHUB_ORG must be set in .env for live tests")
        
        if not self.private_repo:
            pytest.skip("GITHUB_PRIVATE_REPO must be set in .env for live tests")
        
        # Use whichever is set
        self.target_account = self.github_user or self.github_org

    def test_extractor_returns_private_repo(self):
        """
        Verify that the extractor returns the configured private repository.

        This is a regression test for a previously missing private repo.
        """
        from src.extractors.github.extractor import GitHubExtractor

        extractor = GitHubExtractor()

        print(f"\n{'='*70}")
        print(f"PRIVATE REPO TEST - Extractor.get_repositories()")
        print(f"{'='*70}")
        print(f"Target Account: {self.target_account}")
        print(f"Account Type:   {'User' if self.github_user else 'Organization'}")
        print(f"Looking for:    {self.private_repo}")

        repos = extractor.get_repositories(self.target_account)
        repo_ids = sorted([r.repo_id for r in repos])
        repo_names = [r.name for r in repos]

        print(f"\nExtractor returned {len(repos)} repositories:")
        for repo_id in repo_ids:
            marker = " <-- TARGET" if repo_id == self.private_repo else ""
            print(f"  - {repo_id}{marker}")

        # Check for the configured private repo
        if self.private_repo not in repo_ids:
            print(f"\n✗ ERROR: Repository '{self.private_repo}' NOT found")
            print(f"\nDEBUG: Checking by name instead...")
            print(f"  Looking for name: {self.private_repo.split('/')[-1]}")
            print(f"  Available names: {sorted(repo_names)}")
        
        assert self.private_repo in repo_ids, (
            f"Repository '{self.private_repo}' not found in extractor results.\n"
            f"Returned repos: {repo_ids}"
        )
        print(f"\n✓ SUCCESS: '{self.private_repo}' found in results")
        print(f"{'='*70}\n")

    def test_direct_api_finds_private_repo(self):
        """
        Verify that direct GitHub API calls can find the configured private repo.
        This bypasses the extractor to confirm the repo exists and is accessible.
        """
        from github import Github, Auth

        auth = Auth.Token(self.github_token)
        client = Github(auth=auth)

        print(f"\n{'='*70}")
        print(f"PRIVATE REPO TEST - Direct GitHub API Calls")
        print(f"{'='*70}")
        print(f"Target Account: {self.target_account}")
        print(f"Looking for:    {self.private_repo}")

        # Method 1: Authenticated user's repos
        print(f"\n1. get_user().get_repos(visibility='all'):")
        auth_user = client.get_user()
        all_repos = list(auth_user.get_repos(visibility="all"))
        repo_items = [(r.full_name, r.private) for r in all_repos]
        repo_items.sort()
        
        print(f"   Found {len(all_repos)} repositories:")
        for full_name, is_private in repo_items:
            marker = " <-- TARGET" if full_name == self.private_repo else ""
            private_flag = "🔒 PRIVATE" if is_private else "🌐 PUBLIC"
            print(f"     - {full_name} ({private_flag}){marker}")
        
        found = self.private_repo in [r[0] for r in repo_items]
        print(f"\n   Result: '{self.private_repo}' {'✓ FOUND' if found else '✗ NOT FOUND'}")

        if found:
            repo = next(r for r in all_repos if r.full_name == self.private_repo)
            print(f"   Details: Private={repo.private}, Owner={repo.owner.login}")

        # Method 2: Try to get repo directly
        print(f"\n2. get_repo('{self.private_repo}'):")
        try:
            repo = client.get_repo(self.private_repo)
            print(f"   ✓ Found! Private={repo.private}, Owner={repo.owner.login}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        print(f"{'='*70}\n")
        assert found, (
            f"'{self.private_repo}' not found via direct API.\n"
            f"Available repos listed above - check if credentials have access."
        )

    def test_debug_extractor_code_path(self):
        """
        Debug which code path the extractor takes for the configured user.

        This helps identify if get_organization or get_user fallback is used.
        """
        from github import Github, Auth, GithubException

        auth = Auth.Token(self.github_token)
        client = Github(auth=auth)

        print(f"\n{'='*60}")
        print(f"Debugging extractor code path for: {self.target_account}")
        print(f"{'='*60}")

        # Check if user is treated as org or user
        print(f"\n1. Is '{self.target_account}' an organization?")
        try:
            org = client.get_organization(self.target_account)
            print(f"   YES - get_organization succeeded")
            print(f"   Org repos count: {org.get_repos().totalCount}")
        except GithubException as e:
            print(f"   NO - get_organization failed: {e.status}")
            print(f"   Extractor will fall back to get_user()")

        # What does get_user() return?
        print(f"\n2. client.get_user() (no args - authenticated user):")
        auth_user = client.get_user()
        print(f"   Login: {auth_user.login}")
        print(f"   Same as target account? {auth_user.login == self.target_account}")

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
