import json
import pathlib
from datetime import datetime
from src.extractors.base import (
    BranchData,
    CommitData,
    FileTreeItem,
    LanguageData,
    ManifestFileData,
    Platform,
    PullRequestData,
    RepositoryExtractor,
)

class FixtureExtractor(RepositoryExtractor):
    """A fake RepositoryExtractor for testing backed by scenario JSON files."""
    
    def __init__(self, scenario: str | dict):
        if isinstance(scenario, str):
            # Try generated first
            path = pathlib.Path(__file__).parent / "scenarios" / "generated" / f"{scenario}.json"
            if not path.exists():
                path = pathlib.Path(__file__).parent / "scenarios" / f"{scenario}.json"
            if not path.exists():
                raise FileNotFoundError(f"No scenario found for {scenario}")
            
            with open(path, 'r') as file:
                self._scenario = json.load(file)
        else:
            self._scenario = scenario

    @property
    def platform(self) -> Platform:
        return Platform.GITHUB

    def get_file_tree(self, repo_id, branch=None) -> list[FileTreeItem]:
        return [FileTreeItem(path=p, is_directory=False, size=100) for p in self._scenario["file_names"]]

    def get_file_content(self, repo_id, file_path, branch=None) -> str | None:
        manifests = self._scenario.get("manifests", {})
        if isinstance(manifests, dict):
            return manifests.get(file_path)
        for manifest in manifests:
            if manifest["file_path"] == file_path:
                return manifest["content"]
        return None

    def get_languages(self, repo_id) -> list[LanguageData]:
        langs = self._scenario.get("languages", self._scenario.get("language_data", []))
        if langs and isinstance(langs[0], str):
            return [LanguageData(language=l, byte_count=0, percentage=None) for l in langs]
        return [LanguageData(language=d["language"], byte_count=d["byte_count"], percentage=d.get("percentage")) for d in langs]

    def get_branches(self, repo_id) -> list[BranchData]:
        branches = self._scenario.get("branches", [])
        if branches and isinstance(branches[0], str):
            return [BranchData(name=b, latest_commit_sha=None) for b in branches]
        return [BranchData(name=b["name"], latest_commit_sha=b.get("latest_commit_sha")) for b in branches]

    def get_commits(self, repo_id, **kwargs) -> list[CommitData]:
        return [
            CommitData(
                sha=c.get("sha") or c["commit_hash"],
                message=c["message"],
                author_email=c["author_email"],
                author_name=c.get("author_name"),
                committer_email=c["committer_email"],
                committer_name=c.get("committer_name"),
                commit_date=datetime.fromisoformat(c["commit_date"]),
                files_changed=c.get("files_changed"),
                lines_added=c.get("lines_added"),
                lines_removed=c.get("lines_removed")
            )
            for c in self._scenario.get("commits", [])
        ]

    def get_pull_requests(self, repo_id, **kwargs) -> list[PullRequestData]:
        return [
            PullRequestData(
                pr_number=pr["pr_number"],
                platform_pr_id=pr.get("platform_pr_id", str(pr.get("pr_number"))),
                title=pr["title"],
                description=pr.get("description"),
                source_branch=pr["source_branch"],
                target_branch=pr["target_branch"],
                author_email=pr["author_email"],
                author_name=pr.get("author_name"),
                status=pr["status"],
                created_at=datetime.fromisoformat(pr["created_at"]),
                merged_at=datetime.fromisoformat(pr["merged_at"]) if pr.get("merged_at") else None,
                closed_at=datetime.fromisoformat(pr["closed_at"]) if pr.get("closed_at") else None,
                files_changed=pr.get("files_changed", 0),
                lines_added=pr.get("lines_added", 0),
                lines_removed=pr.get("lines_removed", 0)
            )
            for pr in self._scenario.get("pull_requests", [])
        ]

    def get_organizations(self):
        return []

    def get_projects(self, org):
        return []

    def get_repositories(self, org, project=None):
        return []

    def get_repository(self, repo_id):
        raise NotImplementedError("FixtureExtractor does not support get_repository")