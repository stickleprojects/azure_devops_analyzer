"""Unit tests for Azure DevOps extractor configuration loading."""

import os
import tempfile
from pathlib import Path

from src.config.azure_devops import AzureDevOpsExtractorConfig


class TestAzureDevOpsExtractorConfig:
    """Test suite for AzureDevOpsExtractorConfig."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = AzureDevOpsExtractorConfig()

        assert config.page_size == 100
        assert config.max_items_per_list == 5000
        assert config.max_retries == 3
        assert config.backoff_seconds == 2.0
        assert config.max_backoff_seconds == 60.0
        assert config.fetch_pr_file_metrics is True
        assert config.pat is None
        assert config.org_url is None
        assert config.organization is None
        assert config.project is None

    def test_from_env_with_overrides(self):
        """Test loading config with environment variable overrides."""
        original_vars = {
            'AZURE_PAGE_SIZE': os.environ.get('AZURE_PAGE_SIZE'),
            'AZURE_MAX_RETRIES': os.environ.get('AZURE_MAX_RETRIES'),
        }

        try:
            os.environ['AZURE_PAGE_SIZE'] = '50'
            os.environ['AZURE_MAX_RETRIES'] = '5'

            config = AzureDevOpsExtractorConfig.from_env()

            assert config.page_size == 50
            assert config.max_retries == 5
            assert config.max_items_per_list == 5000  # Default
        finally:
            for key, value in original_vars.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_from_env_with_custom_file(self):
        """Test loading config from a custom .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("AZURE_PAGE_SIZE=25\n")
            f.write("AZURE_MAX_RETRIES=7\n")
            f.write("AZURE_BACKOFF_SECONDS=5.5\n")
            env_file = f.name

        try:
            for key in ['AZURE_PAGE_SIZE', 'AZURE_MAX_RETRIES', 'AZURE_BACKOFF_SECONDS']:
                os.environ.pop(key, None)

            config = AzureDevOpsExtractorConfig.from_env(env_file=env_file)

            assert config.page_size == 25
            assert config.max_retries == 7
            assert config.backoff_seconds == 5.5
        finally:
            Path(env_file).unlink()
            for key in ['AZURE_PAGE_SIZE', 'AZURE_MAX_RETRIES', 'AZURE_BACKOFF_SECONDS']:
                os.environ.pop(key, None)

    def test_from_env_with_indirect_variables(self):
        """Test loading config with indirect variable resolution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("ACTUAL_PAGE_SIZE=75\n")
            f.write("AZURE_PAGE_SIZE=$ACTUAL_PAGE_SIZE\n")
            env_file = f.name

        try:
            for key in ['ACTUAL_PAGE_SIZE', 'AZURE_PAGE_SIZE']:
                os.environ.pop(key, None)

            config = AzureDevOpsExtractorConfig.from_env(env_file=env_file)

            assert config.page_size == 75
        finally:
            Path(env_file).unlink()
            for key in ['ACTUAL_PAGE_SIZE', 'AZURE_PAGE_SIZE']:
                os.environ.pop(key, None)

    def test_from_env_invalid_values_use_defaults(self):
        """Test that invalid values fall back to defaults."""
        original = os.environ.get('AZURE_PAGE_SIZE')

        try:
            os.environ['AZURE_PAGE_SIZE'] = 'not_a_number'

            config = AzureDevOpsExtractorConfig.from_env()

            assert config.page_size == 100
        finally:
            if original is None:
                os.environ.pop('AZURE_PAGE_SIZE', None)
            else:
                os.environ['AZURE_PAGE_SIZE'] = original

    def test_from_env_loads_credentials(self):
        """Test that Azure credentials are loaded from environment."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("AZURE_DEVOPS_PAT=pat_test123\n")
            f.write("AZURE_DEVOPS_ORG_URL=https://dev.azure.com/my-org\n")
            f.write("AZURE_DEVOPS_ORG=my-org\n")
            f.write("AZURE_DEVOPS_PROJECT=my-project\n")
            env_file = f.name

        try:
            for key in ['AZURE_DEVOPS_PAT', 'AZURE_DEVOPS_ORG_URL', 'AZURE_DEVOPS_ORG', 'AZURE_DEVOPS_PROJECT']:
                os.environ.pop(key, None)

            config = AzureDevOpsExtractorConfig.from_env(env_file=env_file)

            assert config.pat == 'pat_test123'
            assert config.org_url == 'https://dev.azure.com/my-org'
            assert config.organization == 'my-org'
            assert config.project == 'my-project'
        finally:
            Path(env_file).unlink()
            for key in ['AZURE_DEVOPS_PAT', 'AZURE_DEVOPS_ORG_URL', 'AZURE_DEVOPS_ORG', 'AZURE_DEVOPS_PROJECT']:
                os.environ.pop(key, None)

    def test_from_env_resolves_indirect_credentials(self):
        """Test that indirect Azure credential references are resolved."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("AZURE_VAULT_PAT=pat_secret456\n")
            f.write("AZURE_DEVOPS_PAT=$AZURE_VAULT_PAT\n")
            f.write("AZURE_DEVOPS_ORG_URL=https://dev.azure.com/my-org\n")
            f.write("AZURE_DEVOPS_ORG=my-org\n")
            f.write("AZURE_DEVOPS_PROJECT=my-project\n")
            env_file = f.name

        try:
            for key in ['AZURE_VAULT_PAT', 'AZURE_DEVOPS_PAT', 'AZURE_DEVOPS_ORG_URL', 'AZURE_DEVOPS_ORG', 'AZURE_DEVOPS_PROJECT']:
                os.environ.pop(key, None)

            config = AzureDevOpsExtractorConfig.from_env(env_file=env_file)

            assert config.pat == 'pat_secret456'
            assert config.org_url == 'https://dev.azure.com/my-org'
            assert config.organization == 'my-org'
            assert config.project == 'my-project'
        finally:
            Path(env_file).unlink()
            for key in ['AZURE_VAULT_PAT', 'AZURE_DEVOPS_PAT', 'AZURE_DEVOPS_ORG_URL', 'AZURE_DEVOPS_ORG', 'AZURE_DEVOPS_PROJECT']:
                os.environ.pop(key, None)

    def test_from_env_overrides_stale_env_values_from_default_env_file(self, tmp_path, monkeypatch):
        """Test .env values override stale env when loading default project .env."""
        env_file = tmp_path / ".env"
        env_file.write_text("AZURE_VAULT_PAT=pat_fresh\nAZURE_DEVOPS_PAT=$AZURE_VAULT_PAT\n", encoding="utf-8")

        os.environ["AZURE_DEVOPS_PAT"] = "pat_stale"
        os.environ.pop("AZURE_VAULT_PAT", None)

        monkeypatch.chdir(tmp_path)
        config = AzureDevOpsExtractorConfig.from_env()

        assert config.pat == "pat_fresh"
        assert os.environ.get("AZURE_DEVOPS_PAT") == "pat_fresh"
