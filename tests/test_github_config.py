"""
Unit tests for GitHub configuration with .env file loading and indirect variable resolution.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.config.github import (
    GitHubExtractorConfig,
    load_env_file,
    _find_project_root,
)


class TestLoadEnvFile:
    """Test suite for load_env_file function."""

    def test_load_simple_variables(self):
        """Test loading simple key=value pairs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("VAR1=value1\n")
            f.write("VAR2=value2\n")
            f.write("VAR3=value3\n")
            env_file = f.name

        try:
            # Clear any existing values
            for key in ['VAR1', 'VAR2', 'VAR3']:
                os.environ.pop(key, None)

            result = load_env_file(env_file, override=True)

            assert result == {
                'VAR1': 'value1',
                'VAR2': 'value2',
                'VAR3': 'value3',
            }
            assert os.environ.get('VAR1') == 'value1'
            assert os.environ.get('VAR2') == 'value2'
            assert os.environ.get('VAR3') == 'value3'
        finally:
            Path(env_file).unlink()
            for key in ['VAR1', 'VAR2', 'VAR3']:
                os.environ.pop(key, None)

    def test_load_quoted_values(self):
        """Test loading values with quotes."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('VAR1="value with spaces"\n')
            f.write("VAR2='single quoted'\n")
            f.write("VAR3=unquoted\n")
            env_file = f.name

        try:
            for key in ['VAR1', 'VAR2', 'VAR3']:
                os.environ.pop(key, None)

            result = load_env_file(env_file, override=True)

            assert result['VAR1'] == 'value with spaces'
            assert result['VAR2'] == 'single quoted'
            assert result['VAR3'] == 'unquoted'
        finally:
            Path(env_file).unlink()
            for key in ['VAR1', 'VAR2', 'VAR3']:
                os.environ.pop(key, None)

    def test_skip_comments_and_empty_lines(self):
        """Test that comments and empty lines are ignored."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("\n")
            f.write("VAR1=value1\n")
            f.write("  # Another comment\n")
            f.write("VAR2=value2\n")
            f.write("\n\n")
            env_file = f.name

        try:
            for key in ['VAR1', 'VAR2']:
                os.environ.pop(key, None)

            result = load_env_file(env_file, override=True)

            assert len(result) == 2
            assert result['VAR1'] == 'value1'
            assert result['VAR2'] == 'value2'
        finally:
            Path(env_file).unlink()
            for key in ['VAR1', 'VAR2']:
                os.environ.pop(key, None)

    def test_resolve_indirect_variables(self):
        """Test resolving indirect variable references."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("SECRET_TOKEN=ghp_abc123xyz\n")
            f.write("GITHUB_TOKEN=$SECRET_TOKEN\n")
            f.write("API_KEY=direct_value\n")
            env_file = f.name

        try:
            for key in ['SECRET_TOKEN', 'GITHUB_TOKEN', 'API_KEY']:
                os.environ.pop(key, None)

            result = load_env_file(env_file, override=True)

            assert result['SECRET_TOKEN'] == 'ghp_abc123xyz'
            assert result['GITHUB_TOKEN'] == 'ghp_abc123xyz'
            assert result['API_KEY'] == 'direct_value'
            assert os.environ.get('GITHUB_TOKEN') == 'ghp_abc123xyz'
        finally:
            Path(env_file).unlink()
            for key in ['SECRET_TOKEN', 'GITHUB_TOKEN', 'API_KEY']:
                os.environ.pop(key, None)

    def test_resolve_indirect_from_environment(self):
        """Test resolving indirect references from existing environment."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("GITHUB_TOKEN=$ENV_SECRET\n")
            env_file = f.name

        try:
            # Set a variable in the environment before loading
            os.environ['ENV_SECRET'] = 'from_environment'
            os.environ.pop('GITHUB_TOKEN', None)

            result = load_env_file(env_file, override=True)

            assert result['GITHUB_TOKEN'] == 'from_environment'
            assert os.environ.get('GITHUB_TOKEN') == 'from_environment'
        finally:
            Path(env_file).unlink()
            os.environ.pop('ENV_SECRET', None)
            os.environ.pop('GITHUB_TOKEN', None)

    def test_resolve_chained_indirect_variables(self):
        """Test resolving chained indirect references (A->B->C)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("LEVEL1=actual_value\n")
            f.write("LEVEL2=$LEVEL1\n")
            f.write("LEVEL3=$LEVEL2\n")
            env_file = f.name

        try:
            for key in ['LEVEL1', 'LEVEL2', 'LEVEL3']:
                os.environ.pop(key, None)

            result = load_env_file(env_file, override=True)

            assert result['LEVEL1'] == 'actual_value'
            assert result['LEVEL2'] == 'actual_value'
            assert result['LEVEL3'] == 'actual_value'
        finally:
            Path(env_file).unlink()
            for key in ['LEVEL1', 'LEVEL2', 'LEVEL3']:
                os.environ.pop(key, None)

    def test_no_override_existing_env_vars(self):
        """Test that existing environment variables are not overridden by default."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("VAR1=from_file\n")
            env_file = f.name

        try:
            os.environ['VAR1'] = 'existing_value'

            result = load_env_file(env_file, override=False)

            # File value is returned in result
            assert result['VAR1'] == 'from_file'
            # But environment is not changed
            assert os.environ.get('VAR1') == 'existing_value'
        finally:
            Path(env_file).unlink()
            os.environ.pop('VAR1', None)

    def test_override_existing_env_vars(self):
        """Test that override=True replaces existing environment variables."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("VAR1=from_file\n")
            env_file = f.name

        try:
            os.environ['VAR1'] = 'existing_value'

            result = load_env_file(env_file, override=True)

            assert result['VAR1'] == 'from_file'
            assert os.environ.get('VAR1') == 'from_file'
        finally:
            Path(env_file).unlink()
            os.environ.pop('VAR1', None)

    def test_nonexistent_file_returns_empty_dict(self):
        """Test that loading a nonexistent file returns empty dict."""
        result = load_env_file("/nonexistent/path/.env")
        assert result == {}

    def test_unresolvable_indirect_keeps_original(self):
        """Test that unresolvable indirect references are kept as-is."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("VAR1=$NONEXISTENT_VAR\n")
            env_file = f.name

        try:
            os.environ.pop('VAR1', None)
            os.environ.pop('NONEXISTENT_VAR', None)

            result = load_env_file(env_file, override=True)

            # Should keep the original reference
            assert result['VAR1'] == '$NONEXISTENT_VAR'
        finally:
            Path(env_file).unlink()
            os.environ.pop('VAR1', None)


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


class TestFindProjectRoot:
    """Test suite for _find_project_root function."""

    def test_find_root_with_env_file(self):
        """Test finding project root when .env exists."""
        # This test assumes we're running from within the project
        root = _find_project_root()
        assert root.is_dir()
        # Should find either .env or pyproject.toml
        assert (root / ".env").exists() or (root / "pyproject.toml").exists()
