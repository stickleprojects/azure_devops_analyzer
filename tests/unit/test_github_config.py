"""Unit tests for GitHub extractor configuration loading."""

import os
import tempfile
from pathlib import Path

from src.config.github import GitHubExtractorConfig


class TestGitHubExtractorConfig:
    """Test suite for GitHubExtractorConfig."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = GitHubExtractorConfig()

        assert config.page_size == 100
        assert config.max_items_per_list == 5000
        assert config.max_retries == 3
        assert config.backoff_seconds == 2.0
        assert config.max_backoff_seconds == 60.0
        assert config.token is None
        assert config.organization is None
        assert config.user is None

    def test_from_env_with_overrides(self):
        """Test loading config with environment variable overrides."""
        # Save original values
        original_vars = {
            'GITHUB_PAGE_SIZE': os.environ.get('GITHUB_PAGE_SIZE'),
            'GITHUB_MAX_RETRIES': os.environ.get('GITHUB_MAX_RETRIES'),
        }

        try:
            os.environ['GITHUB_PAGE_SIZE'] = '50'
            os.environ['GITHUB_MAX_RETRIES'] = '5'

            config = GitHubExtractorConfig.from_env()

            assert config.page_size == 50
            assert config.max_retries == 5
            assert config.max_items_per_list == 5000  # Default
        finally:
            # Restore original values
            for key, value in original_vars.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_from_env_with_custom_file(self):
        """Test loading config from a custom .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("GITHUB_PAGE_SIZE=25\n")
            f.write("GITHUB_MAX_RETRIES=7\n")
            f.write("GITHUB_BACKOFF_SECONDS=5.5\n")
            env_file = f.name

        try:
            # Clear environment
            for key in ['GITHUB_PAGE_SIZE', 'GITHUB_MAX_RETRIES', 'GITHUB_BACKOFF_SECONDS']:
                os.environ.pop(key, None)

            config = GitHubExtractorConfig.from_env(env_file=env_file)

            assert config.page_size == 25
            assert config.max_retries == 7
            assert config.backoff_seconds == 5.5
        finally:
            Path(env_file).unlink()
            for key in ['GITHUB_PAGE_SIZE', 'GITHUB_MAX_RETRIES', 'GITHUB_BACKOFF_SECONDS']:
                os.environ.pop(key, None)

    def test_from_env_with_indirect_variables(self):
        """Test loading config with indirect variable resolution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("ACTUAL_PAGE_SIZE=75\n")
            f.write("GITHUB_PAGE_SIZE=$ACTUAL_PAGE_SIZE\n")
            env_file = f.name

        try:
            for key in ['ACTUAL_PAGE_SIZE', 'GITHUB_PAGE_SIZE']:
                os.environ.pop(key, None)

            config = GitHubExtractorConfig.from_env(env_file=env_file)

            assert config.page_size == 75
        finally:
            Path(env_file).unlink()
            for key in ['ACTUAL_PAGE_SIZE', 'GITHUB_PAGE_SIZE']:
                os.environ.pop(key, None)

    def test_from_env_invalid_values_use_defaults(self):
        """Test that invalid values fall back to defaults."""
        original = os.environ.get('GITHUB_PAGE_SIZE')

        try:
            os.environ['GITHUB_PAGE_SIZE'] = 'not_a_number'

            config = GitHubExtractorConfig.from_env()

            # Should use default when conversion fails
            assert config.page_size == 100
        finally:
            if original is None:
                os.environ.pop('GITHUB_PAGE_SIZE', None)
            else:
                os.environ['GITHUB_PAGE_SIZE'] = original

    def test_from_env_loads_credentials(self):
        """Test that credentials are loaded from environment."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("GITHUB_TOKEN=ghp_test123\n")
            f.write("GITHUB_ORG=my-org\n")
            f.write("GITHUB_USER=testuser\n")
            env_file = f.name

        try:
            for key in ['GITHUB_TOKEN', 'GITHUB_ORG', 'GITHUB_USER']:
                os.environ.pop(key, None)

            config = GitHubExtractorConfig.from_env(env_file=env_file)

            assert config.token == 'ghp_test123'
            assert config.organization == 'my-org'
            assert config.user == 'testuser'
        finally:
            Path(env_file).unlink()
            for key in ['GITHUB_TOKEN', 'GITHUB_ORG', 'GITHUB_USER']:
                os.environ.pop(key, None)

    def test_from_env_resolves_indirect_credentials(self):
        """Test that indirect credential references are resolved."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("AZURE_VAULT_TOKEN=ghp_secret456\n")
            f.write("GITHUB_TOKEN=$AZURE_VAULT_TOKEN\n")
            f.write("GITHUB_USER=myuser\n")
            env_file = f.name

        try:
            for key in ['AZURE_VAULT_TOKEN', 'GITHUB_TOKEN', 'GITHUB_USER']:
                os.environ.pop(key, None)

            config = GitHubExtractorConfig.from_env(env_file=env_file)

            assert config.token == 'ghp_secret456'
            assert config.user == 'myuser'
        finally:
            Path(env_file).unlink()
            for key in ['AZURE_VAULT_TOKEN', 'GITHUB_TOKEN', 'GITHUB_USER']:
                os.environ.pop(key, None)

    def test_from_env_overrides_stale_env_values_from_default_env_file(self, tmp_path, monkeypatch):
        """Test .env values override stale env when loading default project .env."""
        env_file = tmp_path / ".env"
        env_file.write_text("VAULT_SECRET=ghp_fresh_token\nGITHUB_TOKEN=$VAULT_SECRET\n", encoding="utf-8")

        os.environ["GITHUB_TOKEN"] = "ghp_stale_token"
        os.environ.pop("VAULT_SECRET", None)

        monkeypatch.chdir(tmp_path)
        config = GitHubExtractorConfig.from_env()

        assert config.token == "ghp_fresh_token"
        assert os.environ.get("GITHUB_TOKEN") == "ghp_fresh_token"
