"""
Unit tests for shared env loader helpers with .env file loading and indirect variable resolution.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.config.env_loader import (
    load_env_file,
    find_project_root,
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


class TestFindProjectRoot:
    """Test suite for find_project_root function."""

    def test_find_root_with_env_file(self):
        """Test finding project root when .env exists."""
        # This test assumes we're running from within the project
        root = find_project_root()
        assert root.is_dir()
        # Should find either .env or pyproject.toml
        assert (root / ".env").exists() or (root / "pyproject.toml").exists()
