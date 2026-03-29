"""Unit tests for Azure DevOps extractor improvements."""

import time
from datetime import datetime
from unittest.mock import Mock, patch, PropertyMock

import pytest
from azure.devops.exceptions import AzureDevOpsServiceError

from src.config.azure_devops import AzureDevOpsExtractorConfig
from src.extractors.azure_devops.extractor import AzureDevOpsExtractor
from src.extractors.base import LanguageData


def _make_service_error(status_code=None, inner_status_code=None):
    """Create an AzureDevOpsServiceError with the given status code."""
    # Build a mock wrapped_exception matching the SDK's expected structure
    wrapped = Mock()
    wrapped.message = "API error"
    wrapped.inner_exception = None
    wrapped.exception_id = None
    wrapped.type_name = None
    wrapped.type_key = None
    wrapped.error_code = 0
    wrapped.event_id = 0
    wrapped.custom_properties = {}

    if inner_status_code is not None:
        inner_wrapped = Mock()
        inner_wrapped.message = "Inner error"
        inner_wrapped.inner_exception = None
        inner_wrapped.exception_id = None
        inner_wrapped.type_name = None
        inner_wrapped.type_key = None
        inner_wrapped.error_code = 0
        inner_wrapped.event_id = 0
        inner_wrapped.custom_properties = {}
        wrapped.inner_exception = inner_wrapped

    exc = AzureDevOpsServiceError(wrapped)
    if status_code is not None:
        exc.status_code = status_code
    if inner_status_code is not None and exc.inner_exception is not None:
        exc.inner_exception.status_code = inner_status_code
    return exc


@pytest.fixture
def azure_config():
    """Create a test Azure DevOps configuration."""
    return AzureDevOpsExtractorConfig(
        pat="test-pat",
        org_url="https://dev.azure.com/test-org",
        organization="test-org",
        max_retries=3,
        backoff_seconds=0.01,  # Fast backoff for tests
        max_backoff_seconds=0.1,
        fetch_pr_file_metrics=True,
    )


@pytest.fixture
def extractor(azure_config):
    """Create an Azure DevOps extractor with mocked clients."""
    ext = AzureDevOpsExtractor(config=azure_config)
    ext._git_client = Mock()
    ext._core_client = Mock()
    return ext


class TestApiCallWithRetry:
    """Test rate limiting and retry logic."""

    def test_succeeds_first_try(self, extractor):
        """Successful API calls are returned immediately."""
        mock_fn = Mock(return_value=["result"])
        result = extractor._api_call_with_retry(mock_fn, "arg1", key="val")

        assert result == ["result"]
        mock_fn.assert_called_once_with("arg1", key="val")

    def test_retries_on_429(self, extractor):
        """Retries on HTTP 429 throttled responses."""
        exc = _make_service_error(status_code=429)

        mock_fn = Mock(side_effect=[exc, exc, "success"])
        result = extractor._api_call_with_retry(mock_fn)

        assert result == "success"
        assert mock_fn.call_count == 3

    def test_gives_up_after_max_retries(self, extractor):
        """Raises after exhausting retries."""
        exc = _make_service_error(status_code=429)

        mock_fn = Mock(side_effect=exc)

        with pytest.raises(AzureDevOpsServiceError):
            extractor._api_call_with_retry(mock_fn)

        # max_retries=3 means 4 total attempts (initial + 3 retries)
        assert mock_fn.call_count == 4

    def test_does_not_retry_non_throttle_errors(self, extractor):
        """Non-429 errors are raised immediately."""
        exc = _make_service_error(status_code=404)

        mock_fn = Mock(side_effect=exc)

        with pytest.raises(AzureDevOpsServiceError):
            extractor._api_call_with_retry(mock_fn)

        assert mock_fn.call_count == 1

    def test_exponential_backoff(self, extractor):
        """Backoff increases exponentially between retries."""
        exc = _make_service_error(status_code=429)

        mock_fn = Mock(side_effect=[exc, exc, "success"])

        with patch("src.extractors.azure_devops.extractor.time.sleep") as mock_sleep:
            extractor._api_call_with_retry(mock_fn)

        # backoff_seconds=0.01, so: 0.01*2^0=0.01, 0.01*2^1=0.02
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(0.01)
        mock_sleep.assert_any_call(0.02)

    def test_detects_throttle_via_inner_exception(self, extractor):
        """Detects throttling from inner_exception status_code."""
        exc = _make_service_error(inner_status_code=429)

        mock_fn = Mock(side_effect=[exc, "success"])
        result = extractor._api_call_with_retry(mock_fn)

        assert result == "success"
        assert mock_fn.call_count == 2


class TestRepositoryMetadata:
    """Test repository metadata population."""

    def test_populates_visibility_from_project(self, extractor):
        """is_private inferred from project visibility."""
        repo = Mock()
        repo.id = "repo-123"
        repo.name = "my-repo"
        repo.web_url = "https://dev.azure.com/org/proj/_git/my-repo"
        repo.remote_url = None
        repo.default_branch = "refs/heads/main"
        repo.project = Mock()
        repo.project.name = "MyProject"
        repo.project.visibility = 0  # private
        repo.is_disabled = False
        repo.size = 52428800  # 50MB

        extractor._git_client.get_repositories.return_value = [repo]

        repos = extractor.get_repositories("test-org", project="MyProject")

        assert len(repos) == 1
        assert repos[0].is_private is True
        assert repos[0].is_archived is False
        assert repos[0].repository_size == 52428800

    def test_public_project_visibility(self, extractor):
        """Public projects result in is_private=False."""
        repo = Mock()
        repo.id = "repo-456"
        repo.name = "public-repo"
        repo.web_url = "https://dev.azure.com/org/proj/_git/public-repo"
        repo.remote_url = None
        repo.default_branch = "refs/heads/main"
        repo.project = Mock()
        repo.project.name = "PublicProject"
        repo.project.visibility = 2  # public
        repo.is_disabled = None
        repo.size = None

        extractor._git_client.get_repositories.return_value = [repo]

        repos = extractor.get_repositories("test-org", project="PublicProject")

        assert repos[0].is_private is False
        assert repos[0].is_archived is None
        assert repos[0].repository_size is None

    def test_github_specific_fields_are_none(self, extractor):
        """GitHub-specific fields are set to None."""
        repo = Mock()
        repo.id = "repo-789"
        repo.name = "test-repo"
        repo.web_url = "https://dev.azure.com/org/proj/_git/test-repo"
        repo.remote_url = None
        repo.default_branch = "refs/heads/main"
        repo.project = Mock()
        repo.project.name = "Proj"
        repo.project.visibility = 0
        repo.is_disabled = False
        repo.size = 1000

        extractor._git_client.get_repository.return_value = repo

        result = extractor.get_repository("repo-789")

        assert result.has_vulnerability_alerts is None
        assert result.has_secret_scanning is None
        assert result.has_dependabot_alerts is None
        assert result.license_name is None
        assert result.license_key is None
        assert result.open_issues_count is None
        assert result.pushed_at is None
        assert result.updated_at is None


class TestCommitsFilesChanged:
    """Test commit file count calculation."""

    def test_sums_all_change_types(self, extractor):
        """files_changed sums all change types (Edit, Add, Delete, Rename)."""
        commit = Mock()
        commit.commit_id = "abc123"
        commit.comment = "Fix bug"
        commit.author = Mock(email="dev@example.com", name="Dev", date=datetime(2024, 1, 15))
        commit.committer = Mock(email="dev@example.com", name="Dev")
        commit.parents = []
        commit.change_counts = {"Edit": 3, "Add": 2, "Delete": 1, "Rename": 1}

        extractor._git_client.get_commits.return_value = [commit]

        commits = extractor.get_commits("repo-id")

        assert len(commits) == 1
        assert commits[0].files_changed == 7  # 3+2+1+1

    def test_none_when_no_change_counts(self, extractor):
        """files_changed is None when change_counts not available."""
        commit = Mock()
        commit.commit_id = "def456"
        commit.comment = "Initial commit"
        commit.author = Mock(email="dev@example.com", name="Dev", date=datetime(2024, 1, 15))
        commit.committer = Mock(email="dev@example.com", name="Dev")
        commit.parents = []
        commit.change_counts = None

        extractor._git_client.get_commits.return_value = [commit]

        commits = extractor.get_commits("repo-id")

        assert commits[0].files_changed is None

    def test_lines_added_removed_are_none(self, extractor):
        """lines_added and lines_removed are always None (API limitation)."""
        commit = Mock()
        commit.commit_id = "ghi789"
        commit.comment = "Update"
        commit.author = Mock(email="dev@example.com", name="Dev", date=datetime(2024, 1, 15))
        commit.committer = Mock(email="dev@example.com", name="Dev")
        commit.parents = []
        commit.change_counts = {"Edit": 5}

        extractor._git_client.get_commits.return_value = [commit]

        commits = extractor.get_commits("repo-id")

        assert commits[0].lines_added is None
        assert commits[0].lines_removed is None


class TestPRTimestamps:
    """Test pull request timestamp handling."""

    def test_merged_pr_timestamps(self, extractor):
        """Merged PRs populate merged_at and closed_at."""
        pr = Mock()
        pr.pull_request_id = 1
        pr.title = "Feature PR"
        pr.description = "Description"
        pr.source_ref_name = "refs/heads/feature"
        pr.target_ref_name = "refs/heads/main"
        pr.created_by = Mock(unique_name="dev@example.com", display_name="Dev")
        pr.status = "completed"
        pr.creation_date = datetime(2024, 1, 10)
        pr.closed_date = datetime(2024, 1, 15)
        pr.completion_queue_time = datetime(2024, 1, 15, 10, 30)

        extractor._git_client.get_pull_requests.return_value = [pr]
        extractor._git_client.get_threads.return_value = []
        extractor._git_client.get_pull_request_reviewers.return_value = []
        extractor._git_client.get_pull_request_iterations.return_value = []

        prs = extractor.get_pull_requests("repo-id")

        assert prs[0].status == "merged"
        assert prs[0].merged_at == datetime(2024, 1, 15, 10, 30)
        assert prs[0].closed_at == datetime(2024, 1, 15)
        assert prs[0].updated_at == datetime(2024, 1, 15)

    def test_abandoned_pr_timestamps(self, extractor):
        """Abandoned PRs have closed_at but no merged_at."""
        pr = Mock()
        pr.pull_request_id = 2
        pr.title = "Abandoned PR"
        pr.description = None
        pr.source_ref_name = "refs/heads/old-branch"
        pr.target_ref_name = "refs/heads/main"
        pr.created_by = Mock(unique_name="dev@example.com", display_name="Dev")
        pr.status = "abandoned"
        pr.creation_date = datetime(2024, 2, 1)
        pr.closed_date = datetime(2024, 2, 10)
        pr.completion_queue_time = None

        extractor._git_client.get_pull_requests.return_value = [pr]
        extractor._git_client.get_threads.return_value = []
        extractor._git_client.get_pull_request_reviewers.return_value = []
        extractor._git_client.get_pull_request_iterations.return_value = []

        prs = extractor.get_pull_requests("repo-id")

        assert prs[0].status == "closed"
        assert prs[0].merged_at is None
        assert prs[0].closed_at == datetime(2024, 2, 10)

    def test_open_pr_timestamps(self, extractor):
        """Open PRs have no closed_at or merged_at."""
        pr = Mock()
        pr.pull_request_id = 3
        pr.title = "Open PR"
        pr.description = None
        pr.source_ref_name = "refs/heads/wip"
        pr.target_ref_name = "refs/heads/main"
        pr.created_by = Mock(unique_name="dev@example.com", display_name="Dev")
        pr.status = "active"
        pr.creation_date = datetime(2024, 3, 1)
        pr.closed_date = None
        pr.completion_queue_time = None

        extractor._git_client.get_pull_requests.return_value = [pr]
        extractor._git_client.get_threads.return_value = []
        extractor._git_client.get_pull_request_reviewers.return_value = []
        extractor._git_client.get_pull_request_iterations.return_value = []

        prs = extractor.get_pull_requests("repo-id")

        assert prs[0].status == "open"
        assert prs[0].merged_at is None
        assert prs[0].closed_at is None
        assert prs[0].updated_at == datetime(2024, 3, 1)


class TestPRFileMetrics:
    """Test PR file metrics from iterations API."""

    def test_counts_files_from_iterations(self, extractor):
        """Files changed is counted from iteration change entries."""
        iteration = Mock()
        iteration.id = 1

        change_entry_1 = Mock()
        change_entry_2 = Mock()
        change_entry_3 = Mock()
        changes = Mock()
        changes.change_entries = [change_entry_1, change_entry_2, change_entry_3]

        extractor._git_client.get_pull_request_iterations.return_value = [iteration]
        extractor._git_client.get_pull_request_iteration_changes.return_value = changes

        files, added, removed = extractor._get_pr_file_metrics("repo-id", 1)

        assert files == 3
        assert added == 0  # API limitation
        assert removed == 0  # API limitation

    def test_disabled_by_config(self, extractor):
        """Returns zeros when fetch_pr_file_metrics is disabled."""
        extractor.config = AzureDevOpsExtractorConfig(
            pat="test-pat",
            org_url="https://dev.azure.com/test-org",
            fetch_pr_file_metrics=False,
        )

        files, added, removed = extractor._get_pr_file_metrics("repo-id", 1)

        assert files == 0
        assert added == 0
        assert removed == 0
        extractor._git_client.get_pull_request_iterations.assert_not_called()

    def test_handles_empty_iterations(self, extractor):
        """Returns zeros when no iterations exist."""
        extractor._git_client.get_pull_request_iterations.return_value = []

        files, added, removed = extractor._get_pr_file_metrics("repo-id", 1)

        assert files == 0

    def test_handles_api_error_gracefully(self, extractor):
        """Returns zeros on API failure instead of crashing."""
        extractor._git_client.get_pull_request_iterations.side_effect = Exception("API Error")

        files, added, removed = extractor._get_pr_file_metrics("repo-id", 1)

        assert files == 0
        assert added == 0
        assert removed == 0


class TestReviewsAndComments:
    """Test combined review/comment fetching with comment counts."""

    def test_combined_fetch_avoids_duplicate_threads_call(self, extractor):
        """Threads are fetched once for both comments and review counts."""
        thread = Mock()
        thread.id = 1
        thread.thread_context = None
        comment = Mock()
        comment.comment_type = "text"
        comment.author = Mock(unique_name="reviewer@example.com", display_name="Reviewer")
        comment.content = "Looks good"
        comment.published_date = datetime(2024, 1, 12)
        thread.comments = [comment]

        reviewer = Mock()
        reviewer.vote = 10
        reviewer.unique_name = "reviewer@example.com"
        reviewer.display_name = "Reviewer"
        reviewer.is_required = True

        extractor._git_client.get_threads.return_value = [thread]
        extractor._git_client.get_pull_request_reviewers.return_value = [reviewer]

        reviews, comments = extractor._get_pr_reviews_and_comments("repo-id", 1)

        # Threads called only once
        extractor._git_client.get_threads.assert_called_once()

        assert len(comments) == 1
        assert comments[0].content == "Looks good"
        assert len(reviews) == 1
        assert reviews[0].state == "approved"
        assert reviews[0].comment_count == 1

    def test_comment_count_per_reviewer(self, extractor):
        """Each reviewer gets their own comment count."""
        thread = Mock()
        thread.id = 1
        thread.thread_context = None

        comment_a1 = Mock(comment_type="text", content="Comment 1",
                          published_date=datetime(2024, 1, 10))
        comment_a1.author = Mock(unique_name="alice@example.com", display_name="Alice")

        comment_a2 = Mock(comment_type="text", content="Comment 2",
                          published_date=datetime(2024, 1, 11))
        comment_a2.author = Mock(unique_name="alice@example.com", display_name="Alice")

        comment_b1 = Mock(comment_type="text", content="Comment 3",
                          published_date=datetime(2024, 1, 12))
        comment_b1.author = Mock(unique_name="bob@example.com", display_name="Bob")

        thread.comments = [comment_a1, comment_a2, comment_b1]

        reviewer_alice = Mock(vote=10, unique_name="alice@example.com",
                              display_name="Alice", is_required=False)
        reviewer_bob = Mock(vote=5, unique_name="bob@example.com",
                            display_name="Bob", is_required=False)

        extractor._git_client.get_threads.return_value = [thread]
        extractor._git_client.get_pull_request_reviewers.return_value = [
            reviewer_alice, reviewer_bob
        ]

        reviews, comments = extractor._get_pr_reviews_and_comments("repo-id", 1)

        assert len(comments) == 3
        assert len(reviews) == 2

        alice_review = next(r for r in reviews if r.reviewer_email == "alice@example.com")
        bob_review = next(r for r in reviews if r.reviewer_email == "bob@example.com")

        assert alice_review.comment_count == 2
        assert bob_review.comment_count == 1

    def test_system_comments_excluded(self, extractor):
        """System comments are not counted or returned."""
        thread = Mock()
        thread.id = 1
        thread.thread_context = None

        system_comment = Mock(comment_type="system", content="PR updated")
        system_comment.author = Mock(unique_name="system@azure.com", display_name="System")

        user_comment = Mock(comment_type="text", content="Approved")
        user_comment.author = Mock(unique_name="dev@example.com", display_name="Dev")
        user_comment.published_date = datetime(2024, 1, 10)

        thread.comments = [system_comment, user_comment]

        extractor._git_client.get_threads.return_value = [thread]
        extractor._git_client.get_pull_request_reviewers.return_value = []

        reviews, comments = extractor._get_pr_reviews_and_comments("repo-id", 1)

        assert len(comments) == 1
        assert comments[0].content == "Approved"

    def test_threads_api_error_returns_empty(self, extractor):
        """API errors on threads return empty lists gracefully."""
        extractor._git_client.get_threads.side_effect = Exception("Network error")
        extractor._git_client.get_pull_request_reviewers.return_value = []

        reviews, comments = extractor._get_pr_reviews_and_comments("repo-id", 1)

        assert reviews == []
        assert comments == []

    def test_review_date_uses_fallback_when_provided(self, extractor):
        """review_date is set to the provided fallback, not utcnow().

        Regression guard for DASH-REVIEW-003: synthetic 'now' timestamps on
        Azure DevOps reviews caused stale PRs to appear as recent activity.
        """
        extractor._git_client.get_threads.return_value = []

        reviewer = Mock()
        reviewer.vote = 10
        reviewer.unique_name = "dev@example.com"
        reviewer.display_name = "Dev"
        reviewer.is_required = False
        extractor._git_client.get_pull_request_reviewers.return_value = [reviewer]

        fallback = datetime(2023, 6, 15, 12, 0, 0)
        reviews, _ = extractor._get_pr_reviews_and_comments(
            "repo-id", 1, review_date_fallback=fallback
        )

        assert len(reviews) == 1
        assert reviews[0].review_date == fallback

    def test_review_date_falls_back_to_utcnow_when_not_provided(self, extractor):
        """review_date defaults to utcnow() when no fallback is given (e.g. open PRs)."""
        extractor._git_client.get_threads.return_value = []

        reviewer = Mock()
        reviewer.vote = 10
        reviewer.unique_name = "dev@example.com"
        reviewer.display_name = "Dev"
        reviewer.is_required = False
        extractor._git_client.get_pull_request_reviewers.return_value = [reviewer]

        before = datetime.utcnow()
        reviews, _ = extractor._get_pr_reviews_and_comments("repo-id", 1)
        after = datetime.utcnow()

        assert len(reviews) == 1
        assert before <= reviews[0].review_date <= after
