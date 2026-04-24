"""
SnapshotExtractor: fixture-backed extractor sourced from recorded real-API snapshots.

Snapshots live in tests/fixtures/snapshots/<platform>/<filename>.json and follow
the same JSON schema as generated/adversarial fixture scenarios.  This allows the
same FixtureExtractor parsing path to be reused while exercising data shapes that
come from real production API responses (after anonymisation).

Usage:
    extractor = SnapshotExtractor("github")   # loads snapshots/github/fixture.json
    extractor = SnapshotExtractor("azure_devops")
"""

import json
import pathlib

from tests.fixtures.fixture_extractor import FixtureExtractor

# Root of the snapshot tree relative to this file
_SNAPSHOTS_ROOT = pathlib.Path(__file__).parent / "snapshots"


class SnapshotExtractor(FixtureExtractor):
    """FixtureExtractor variant that reads from the anonymised snapshot files.

    Each platform has a snapshot directory (``snapshots/<platform>/``) containing
    at least one ``fixture.json`` that follows the standard scenario JSON schema.
    """

    def __init__(self, platform: str, filename: str = "fixture.json"):
        """
        Args:
            platform: One of ``"github"`` or ``"azure_devops"``.
            filename: Snapshot filename within the platform directory (default
                ``"fixture.json"``).
        """
        snapshot_path = _SNAPSHOTS_ROOT / platform / filename
        if not snapshot_path.exists():
            raise FileNotFoundError(
                f"No snapshot found for platform '{platform}' at {snapshot_path}. "
                "Run scripts/capture-api-snapshot.sh to capture and "
                "scripts/anonymise-snapshot.py to anonymise snapshots."
            )

        with open(snapshot_path, "r", encoding="utf-8") as fh:
            scenario = json.load(fh)

        # Bypass FixtureExtractor.__init__'s path resolution by calling with a dict
        super().__init__(scenario)
