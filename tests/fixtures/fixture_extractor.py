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
    PRReviewData,
    PullRequestData,
    RepositoryExtractor,
)

class FixtureExtractor(RepositoryExtractor):
    """A fake RepositoryExtractor for testing backed by scenario JSON files."""
    
    def __init__(self, scenario: str | dict):
        if isinstance(scenario, str):
            # Try generated first, then adversarial, then legacy root
            _scenarios_root = pathlib.Path(__file__).parent / "scenarios"
            path = _scenarios_root / "generated" / f"{scenario}.json"
            if not path.exists():
                path = _scenarios_root / "adversarial" / f"{scenario}.json"
            if not path.exists():
                path = _scenarios_root / f"{scenario}.json"
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
        result = []
        for pr in self._scenario.get("pull_requests", []):
            reviews = [
                PRReviewData(
                    reviewer_email=r["reviewer_email"],
                    reviewer_name=r.get("reviewer_name"),
                    review_date=datetime.fromisoformat(r["review_date"]) if r.get("review_date") else datetime.fromisoformat(pr["created_at"]),
                    state=r.get("state", "approved"),
                    is_required=r.get("is_required", False),
                )
                for r in pr.get("reviews", [])
            ]
            result.append(PullRequestData(
                pr_number=pr["pr_number"],
                # Namespace fixture IDs by repo to avoid collisions across scenarios.
                platform_pr_id=f"{repo_id}:{pr.get('platform_pr_id', pr.get('pr_number'))}",
                title=pr["title"],
                description=pr.get("description"),
                source_branch=pr["source_branch"],
                target_branch=pr["target_branch"],
                author_email=pr.get("author_email"),
                author_name=pr.get("author_name"),
                status=pr["status"],
                created_at=datetime.fromisoformat(pr["created_at"]),
                merged_at=datetime.fromisoformat(pr["merged_at"]) if pr.get("merged_at") else None,
                closed_at=datetime.fromisoformat(pr["closed_at"]) if pr.get("closed_at") else None,
                files_changed=pr.get("files_changed", 0),
                lines_added=pr.get("lines_added", 0),
                lines_removed=pr.get("lines_removed", 0),
                reviews=reviews,
            ))
        return result

    def get_vulnerability_data(self) -> list[dict]:
        """Return synthetic vulnerability/enrichment data stored in the fixture.

        Each entry is a dict with keys:
            package_name, ecosystem, pinned_version, latest_version,
            is_eol, eol_date (ISO string or None), vulnerabilities (list[dict])

        Returns an empty list if the fixture has no vulnerability_data.
        """
        return self._scenario.get("vulnerability_data", [])

    def get_technology_stack(self) -> dict:
        """Return deterministic technology stack (heuristic detections) for the fixture.

        Returns a dict with keys:
            frameworks, databases, deployment_platforms, build_tools,
            testing_frameworks, ci_cd_platforms, documentation_tools  (each a list[str])
            confidence  (float, 0–1)
            eol_technologies  (list[dict] with name, category, is_eol, eol_date,
                               latest_supported_version — for store_technology_eol())

        Returns an empty dict if the fixture has no technology_stack.
        """
        return self._scenario.get("technology_stack", {})

    def get_organizations(self):
        return []

    def get_projects(self, org):
        return []

    def get_repositories(self, org, project=None):
        return []

    def get_repository(self, repo_id):
        raise NotImplementedError("FixtureExtractor does not support get_repository")