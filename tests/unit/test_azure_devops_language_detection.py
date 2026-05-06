"""Unit tests for Azure DevOps language detection heuristics."""

import pytest
from unittest.mock import Mock, patch
from src.config.azure_devops import AzureDevOpsExtractorConfig
from src.extractors.azure_devops.extractor import AzureDevOpsExtractor
from src.extractors.base import FileTreeItem


@pytest.fixture
def azure_config():
    """Create a test Azure DevOps configuration."""
    return AzureDevOpsExtractorConfig(
        pat="test-pat",
        org_url="https://dev.azure.com/test-org",
        organization="test-org",
    )


@pytest.fixture
def extractor(azure_config):
    """Create an Azure DevOps extractor with mocked clients."""
    with patch.object(AzureDevOpsExtractor, '__abstractmethods__', set()):
        extractor = AzureDevOpsExtractor(config=azure_config)
        extractor._git_client = Mock()
        extractor._core_client = Mock()
        return extractor


class TestAzureDevOpsLanguageDetection:
    """Test language detection based on file patterns."""
    
    def test_detects_csharp_from_csproj(self, extractor, mocker):
        """Detect C# from .csproj files."""
        # Mock get_file_tree to return C# project files
        mock_files = [
            FileTreeItem(path="/MyProject.csproj", is_directory=False, size=1000),
            FileTreeItem(path="/Program.cs", is_directory=False, size=500),
            FileTreeItem(path="/Services/DataService.cs", is_directory=False, size=800),
        ]
        mocker.patch.object(extractor, "get_file_tree", return_value=mock_files)
        
        languages = extractor.get_languages("test-repo-id")
        
        assert len(languages) == 1
        assert languages[0].language == "C#"
        assert languages[0].percentage == 100.0
    
    def test_detects_python_from_requirements(self, extractor, mocker):
        """Detect Python from requirements.txt."""
        mock_files = [
            FileTreeItem(path="/requirements.txt", is_directory=False, size=500),
            FileTreeItem(path="/main.py", is_directory=False, size=1000),
            FileTreeItem(path="/utils/helper.py", is_directory=False, size=600),
        ]
        mocker.patch.object(extractor, "get_file_tree", return_value=mock_files)
        
        languages = extractor.get_languages("test-repo-id")
        
        assert len(languages) == 1
        assert languages[0].language == "Python"
        assert languages[0].percentage == 100.0
    
    def test_detects_multiple_languages(self, extractor, mocker):
        """Detect multiple languages with percentage distribution."""
        mock_files = [
            # Python files (3 total, 1 config = 10 points + 2 code = 2 points = 12)
            FileTreeItem(path="/requirements.txt", is_directory=False, size=500),
            FileTreeItem(path="/app.py", is_directory=False, size=1000),
            FileTreeItem(path="/models.py", is_directory=False, size=800),
            
            # JavaScript files (2 total = 2 points)
            FileTreeItem(path="/index.js", is_directory=False, size=600),
            FileTreeItem(path="/utils.js", is_directory=False, size=400),
            
            # HTML (1 file = 1 point)
            FileTreeItem(path="/index.html", is_directory=False, size=300),
        ]
        mocker.patch.object(extractor, "get_file_tree", return_value=mock_files)
        
        languages = extractor.get_languages("test-repo-id")
        
        # Total points: 12 + 2 + 1 = 15
        # Python: 12/15 = 80%, JS: 2/15 = 13.33%, HTML: 1/15 = 6.67%
        assert len(languages) == 3
        
        # Should be sorted by byte_count (points) descending
        assert languages[0].language == "Python"
        assert languages[0].percentage == 80.0
        
        assert languages[1].language == "JavaScript"
        assert languages[1].percentage == 13.33
        
        assert languages[2].language == "HTML"
        assert languages[2].percentage == 6.67
    
    def test_handles_empty_repository(self, extractor, mocker):
        """Handle repositories with no files."""
        mocker.patch.object(extractor, "get_file_tree", return_value=[])
        
        languages = extractor.get_languages("test-repo-id")
        
        assert languages == []
    
    def test_ignores_directories(self, extractor, mocker):
        """Ignore directory entries when detecting languages."""
        mock_files = [
            FileTreeItem(path="/src", is_directory=True, size=None),
            FileTreeItem(path="/src/app.py", is_directory=False, size=1000),
            FileTreeItem(path="/tests", is_directory=True, size=None),
        ]
        mocker.patch.object(extractor, "get_file_tree", return_value=mock_files)
        
        languages = extractor.get_languages("test-repo-id")
        
        assert len(languages) == 1
        assert languages[0].language == "Python"
    
    def test_detects_typescript_from_tsconfig(self, extractor, mocker):
        """Detect TypeScript from tsconfig.json."""
        mock_files = [
            FileTreeItem(path="/tsconfig.json", is_directory=False, size=300),
            FileTreeItem(path="/src/index.ts", is_directory=False, size=1000),
            FileTreeItem(path="/src/types.ts", is_directory=False, size=500),
        ]
        mocker.patch.object(extractor, "get_file_tree", return_value=mock_files)
        
        languages = extractor.get_languages("test-repo-id")
        
        assert len(languages) == 1
        assert languages[0].language == "TypeScript"
        
    def test_project_files_weighted_higher(self, extractor, mocker):
        """Project config files should be weighted higher than code files."""
        mock_files = [
            # Single project file (10 points)
            FileTreeItem(path="/pom.xml", is_directory=False, size=500),
            
            # Multiple Python files (5 files = 5 points)
            FileTreeItem(path="/script1.py", is_directory=False, size=100),
            FileTreeItem(path="/script2.py", is_directory=False, size=100),
            FileTreeItem(path="/script3.py", is_directory=False, size=100),
            FileTreeItem(path="/script4.py", is_directory=False, size=100),
            FileTreeItem(path="/script5.py", is_directory=False, size=100),
        ]
        mocker.patch.object(extractor, "get_file_tree", return_value=mock_files)
        
        languages = extractor.get_languages("test-repo-id")
        
        # Java: 10 points (66.67%), Python: 5 points (33.33%)
        assert len(languages) == 2
        assert languages[0].language == "Java"
        assert languages[0].percentage == 66.67
        assert languages[1].language == "Python"

