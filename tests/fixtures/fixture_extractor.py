import json
import pathlib
from src.extractors.base import (
    FileTreeItem,
    LanguageData,
    ManifestFileData,
    Platform,
    RepositoryExtractor,
)


class FixtureExtractor(RepositoryExtractor):
    """A fake RepositoryExtractor for testing backed by scenario JSON files."""

    def __init__(self, scenario: str | dict):
        if isinstance(scenario, str):
            scenario_path = pathlib.Path(__file__).parent / "scenarios" / f"{scenario}.json"
            with open(scenario_path, "r") as f:
                self._scenario = json.load(f)
        else:
            self._scenario = scenario

    @property
    def platform(self):
        return Platform.GITHUB

    def get_file_tree(self, repo_id, branch=None):
        return [FileTreeItem(path=p, is_directory=False, size=100) for p in self._scenario["file_names"]]

    def get_file_content(self, repo_id, file_path, branch=None):
        for manifest in self._scenario["manifests"]:
            if manifest["file_path"] == file_path:
                return manifest["content"]
        return None

    def get_languages(self, repo_id):
        return [LanguageData(language=d["language"], byte_count=d["byte_count"], percentage=d.get("percentage")) for d in self._scenario["language_data"]]

    def get_organizations(self):
        return []

    def get_projects(self, org):
        return []

    def get_repositories(self, org, project=None):
        return []

    def get_repository(self, repo_id):
        raise NotImplementedError("FixtureExtractor does not support get_repository")

    def get_branches(self, repo_id):
        return []

    def get_commits(self, repo_id, **kwargs):
        return []

    def get_pull_requests(self, repo_id, **kwargs):
        return []