"""Unit tests for manifest file extraction."""

import pytest
from unittest.mock import Mock, patch
from src.config.github import GitHubExtractorConfig
from src.config.azure_devops import AzureDevOpsExtractorConfig
from src.extractors.github.extractor import GitHubExtractor
from src.extractors.azure_devops.extractor import AzureDevOpsExtractor
from src.extractors.base import FileTreeItem, ManifestFileData


@pytest.fixture
def github_extractor():
    """Create a GitHub extractor with mocked client."""
    with patch('src.extractors.github.client.get_github_client') as mock_client:
        mock_client.return_value = Mock()
        config = GitHubExtractorConfig(token="fake-token", user="test-user")
        extractor = GitHubExtractor(config=config)
        return extractor


@pytest.fixture
def azure_config():
    """Create a test Azure DevOps configuration."""
    return AzureDevOpsExtractorConfig(
        pat="test-pat",
        org_url="https://dev.azure.com/test-org",
        organization="test-org",
    )


@pytest.fixture
def azure_extractor(azure_config):
    """Create an Azure DevOps extractor with mocked clients."""
    with patch.object(AzureDevOpsExtractor, '__abstractmethods__', set()):
        extractor = AzureDevOpsExtractor(config=azure_config)
        extractor._git_client = Mock()
        extractor._core_client = Mock()
        return extractor


class TestManifestExtractionGitHub:
    """Test manifest extraction for GitHub repositories."""
    
    def test_extracts_python_requirements(self, github_extractor, mocker):
        """Extract Python requirements.txt file."""
        # Mock file tree
        mock_tree = [
            FileTreeItem(path="requirements.txt", is_directory=False, size=100),
            FileTreeItem(path="README.md", is_directory=False, size=50),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        # Mock file content
        requirements_content = "flask==2.0.1\nrequests>=2.28.0\npytest==7.1.0"
        mocker.patch.object(
            github_extractor,
            "get_file_content",
            return_value=requirements_content
        )
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 1
        assert manifests[0].file_path == "requirements.txt"
        assert manifests[0].content == requirements_content
        assert manifests[0].ecosystem == "pypi"
    
    def test_extracts_package_json(self, github_extractor, mocker):
        """Extract Node.js package.json file."""
        mock_tree = [
            FileTreeItem(path="package.json", is_directory=False, size=200),
            FileTreeItem(path="src/index.js", is_directory=False, size=500),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        package_json = '{"name": "test", "dependencies": {"express": "^4.17.1"}}'
        mocker.patch.object(
            github_extractor,
            "get_file_content",
            return_value=package_json
        )
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 1
        assert manifests[0].file_path == "package.json"
        assert manifests[0].ecosystem == "npm"
    
    def test_extracts_multiple_manifests(self, github_extractor, mocker):
        """Extract multiple manifest files from polyglot repository."""
        mock_tree = [
            FileTreeItem(path="requirements.txt", is_directory=False, size=100),
            FileTreeItem(path="package.json", is_directory=False, size=200),
            FileTreeItem(path="pom.xml", is_directory=False, size=300),
            FileTreeItem(path="README.md", is_directory=False, size=50),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        # Mock file content - return different content based on path
        def mock_get_file(repo_id, path, branch=None):
            if path == "requirements.txt":
                return "flask==2.0.1"
            elif path == "package.json":
                return '{"name": "test"}'
            elif path == "pom.xml":
                return '<project></project>'
            return None
        
        mocker.patch.object(
            github_extractor,
            "get_file_content",
            side_effect=mock_get_file
        )
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 3
        paths = {m.file_path for m in manifests}
        assert paths == {"requirements.txt", "package.json", "pom.xml"}
        
        ecosystems = {m.ecosystem for m in manifests}
        assert ecosystems == {"pypi", "npm", "maven"}
    
    def test_extracts_csproj_files(self, github_extractor, mocker):
        """Extract .NET .csproj files."""
        mock_tree = [
            FileTreeItem(path="MyProject.csproj", is_directory=False, size=400),
            FileTreeItem(path="tests/Tests.csproj", is_directory=False, size=200),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        csproj_content = '<Project><ItemGroup><PackageReference Include="Newtonsoft.Json" /></ItemGroup></Project>'
        mocker.patch.object(
            github_extractor,
            "get_file_content",
            return_value=csproj_content
        )
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 2
        assert all(m.ecosystem == "nuget" for m in manifests)
    
    def test_ignores_directories(self, github_extractor, mocker):
        """Ignore directory entries when scanning for manifests."""
        mock_tree = [
            FileTreeItem(path="src", is_directory=True, size=None),
            FileTreeItem(path="src/requirements.txt", is_directory=False, size=100),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        mocker.patch.object(
            github_extractor,
            "get_file_content",
            return_value="flask==2.0.1"
        )
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        # Should only extract the file, not the directory
        assert len(manifests) == 1
        assert manifests[0].file_path == "src/requirements.txt"
    
    def test_handles_empty_repository(self, github_extractor, mocker):
        """Handle repositories with no manifest files."""
        mock_tree = [
            FileTreeItem(path="README.md", is_directory=False, size=50),
            FileTreeItem(path="LICENSE", is_directory=False, size=100),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert manifests == []
    
    def test_handles_file_read_failure(self, github_extractor, mocker):
        """Handle cases where file content cannot be retrieved."""
        mock_tree = [
            FileTreeItem(path="requirements.txt", is_directory=False, size=100),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        # Mock get_file_content to return None (file not found)
        mocker.patch.object(
            github_extractor,
            "get_file_content",
            return_value=None
        )
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        # Should not include files that couldn't be read
        assert manifests == []


class TestLineEndingNormalization:
    """Test line ending normalization across platforms."""
    
    def test_normalizes_crlf_to_lf(self, github_extractor, mocker):
        """Windows-style line endings (CRLF) are normalized to Unix (LF)."""
        mock_tree = [
            FileTreeItem(path="requirements.txt", is_directory=False, size=100),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        # Windows-style line endings
        windows_content = "flask==2.0.1\r\nrequests>=2.28.0\r\npytest==7.1.0"
        mocker.patch.object(
            github_extractor,
            "get_file_content",
            return_value=windows_content
        )
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 1
        # Should be normalized to LF
        assert manifests[0].content == "flask==2.0.1\nrequests>=2.28.0\npytest==7.1.0"
        assert "\r" not in manifests[0].content
    
    def test_normalizes_cr_to_lf(self, github_extractor, mocker):
        """Old Mac-style line endings (CR) are normalized to Unix (LF)."""
        mock_tree = [
            FileTreeItem(path="requirements.txt", is_directory=False, size=100),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        # Old Mac-style line endings (CR only)
        mac_content = "flask==2.0.1\rrequests>=2.28.0\rpytest==7.1.0"
        mocker.patch.object(
            github_extractor,
            "get_file_content",
            return_value=mac_content
        )
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 1
        # Should be normalized to LF
        assert manifests[0].content == "flask==2.0.1\nrequests>=2.28.0\npytest==7.1.0"
    
    def test_preserves_lf_line_endings(self, github_extractor, mocker):
        """Unix-style line endings (LF) are preserved unchanged."""
        mock_tree = [
            FileTreeItem(path="requirements.txt", is_directory=False, size=100),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        # Unix-style line endings
        unix_content = "flask==2.0.1\nrequests>=2.28.0\npytest==7.1.0"
        mocker.patch.object(
            github_extractor,
            "get_file_content",
            return_value=unix_content
        )
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 1
        # Should remain unchanged
        assert manifests[0].content == unix_content
    
    def test_handles_mixed_line_endings(self, github_extractor, mocker):
        """Mixed line endings are all normalized to LF."""
        mock_tree = [
            FileTreeItem(path="requirements.txt", is_directory=False, size=100),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        
        # Mixed line endings (CRLF, CR, LF)
        mixed_content = "flask==2.0.1\r\nrequests>=2.28.0\rpytest==7.1.0\ndjango==3.2.0"
        mocker.patch.object(
            github_extractor,
            "get_file_content",
            return_value=mixed_content
        )
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 1
        # All line endings should be LF
        expected = "flask==2.0.1\nrequests>=2.28.0\npytest==7.1.0\ndjango==3.2.0"
        assert manifests[0].content == expected
        assert "\r" not in manifests[0].content


class TestManifestExtractionAzureDevOps:
    """Test manifest extraction for Azure DevOps repositories."""
    
    def test_extracts_manifests_from_azure_devops(self, azure_extractor, mocker):
        """Extract manifests from Azure DevOps repository."""
        mock_tree = [
            FileTreeItem(path="/requirements.txt", is_directory=False, size=100),
            FileTreeItem(path="/src/package.json", is_directory=False, size=200),
        ]
        mocker.patch.object(azure_extractor, "get_file_tree", return_value=mock_tree)
        
        def mock_get_file(repo_id, path, branch=None):
            if path == "/requirements.txt":
                return "flask==2.0.1"
            elif path == "/src/package.json":
                return '{"name": "test"}'
            return None
        
        mocker.patch.object(
            azure_extractor,
            "get_file_content",
            side_effect=mock_get_file
        )
        
        manifests = azure_extractor.extract_manifests("test-repo-id")
        
        assert len(manifests) == 2
        ecosystems = {m.ecosystem for m in manifests}
        assert ecosystems == {"pypi", "npm"}


class TestEcosystemInference:
    """Test ecosystem inference from file names."""
    
    def test_infers_python_ecosystems(self, github_extractor, mocker):
        """Infer Python ecosystem from various requirements files."""
        mock_tree = [
            FileTreeItem(path="requirements.txt", is_directory=False, size=100),
            FileTreeItem(path="requirements-dev.txt", is_directory=False, size=50),
            FileTreeItem(path="test-requirements.txt", is_directory=False, size=30),
            FileTreeItem(path="pyproject.toml", is_directory=False, size=200),
            FileTreeItem(path="Pipfile", is_directory=False, size=150),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        mocker.patch.object(github_extractor, "get_file_content", return_value="content")
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        # All should be identified as pypi
        assert all(m.ecosystem == "pypi" for m in manifests)
        assert len(manifests) == 5
    
    def test_infers_java_maven(self, github_extractor, mocker):
        """Infer Maven ecosystem from pom.xml."""
        mock_tree = [
            FileTreeItem(path="pom.xml", is_directory=False, size=100),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        mocker.patch.object(github_extractor, "get_file_content", return_value="<project></project>")
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 1
        assert manifests[0].ecosystem == "maven"
    
    def test_infers_go_ecosystem(self, github_extractor, mocker):
        """Infer Go ecosystem from go.mod."""
        mock_tree = [
            FileTreeItem(path="go.mod", is_directory=False, size=100),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        mocker.patch.object(github_extractor, "get_file_content", return_value="module test")
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 1
        assert manifests[0].ecosystem == "go"
    
    def test_infers_rust_ecosystem(self, github_extractor, mocker):
        """Infer Rust ecosystem from Cargo.toml."""
        mock_tree = [
            FileTreeItem(path="Cargo.toml", is_directory=False, size=100),
        ]
        mocker.patch.object(github_extractor, "get_file_tree", return_value=mock_tree)
        mocker.patch.object(github_extractor, "get_file_content", return_value="[package]")
        
        manifests = github_extractor.extract_manifests("test/repo")
        
        assert len(manifests) == 1
        assert manifests[0].ecosystem == "cargo"
