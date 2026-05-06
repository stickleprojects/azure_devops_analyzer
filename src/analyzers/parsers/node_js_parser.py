"""
Node.js ecosystem manifest file parser.

Supports:
- package.json
"""

import json
from typing import Optional

from src.extractors.base import DependencyData
from src.analyzers.parsers.base import ManifestParser, ParserRegistry


@ParserRegistry.register
class NodeJsParser(ManifestParser):
    """Parser for Node.js package.json files."""

    ECOSYSTEM = "npm"
    SUPPORTED_FILES = ["package.json"]

    def parse(self, content: str, file_path: str) -> list[DependencyData]:
        """Parse package.json content."""
        dependencies = []

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return dependencies

        # Regular dependencies
        for pkg_name, version_spec in data.get("dependencies", {}).items():
            dep = self._parse_npm_dependency(
                pkg_name, version_spec, file_path, is_dev=False
            )
            if dep:
                dependencies.append(dep)

        # Dev dependencies
        for pkg_name, version_spec in data.get("devDependencies", {}).items():
            dep = self._parse_npm_dependency(
                pkg_name, version_spec, file_path, is_dev=True
            )
            if dep:
                dependencies.append(dep)

        # Peer dependencies (treat as regular deps)
        for pkg_name, version_spec in data.get("peerDependencies", {}).items():
            dep = self._parse_npm_dependency(
                pkg_name, version_spec, file_path, is_dev=False
            )
            if dep:
                dependencies.append(dep)

        # Optional dependencies (treat as regular deps)
        for pkg_name, version_spec in data.get("optionalDependencies", {}).items():
            dep = self._parse_npm_dependency(
                pkg_name, version_spec, file_path, is_dev=False
            )
            if dep:
                dependencies.append(dep)

        return dependencies

    def _parse_npm_dependency(
        self,
        pkg_name: str,
        version_spec: str,
        file_path: str,
        is_dev: bool,
    ) -> Optional[DependencyData]:
        """Parse a single npm dependency specification."""
        # Skip non-version specs (git URLs, file paths, etc.)
        if not isinstance(version_spec, str):
            return None

        if version_spec.startswith(("git", "http", "file:", "link:", "/")):
            return None

        version = self._extract_version_from_spec(version_spec)

        return self._create_dependency(
            package_name=pkg_name,
            version=version,
            file_path=file_path,
            is_dev=is_dev,
            version_constraint=version_spec,
        )

    def _extract_version_from_spec(self, spec: str) -> Optional[str]:
        """
        Extract version from npm version specifier.

        Examples:
            "1.0.0" -> "1.0.0"
            "^1.0.0" -> "1.0.0"
            "~1.0.0" -> "1.0.0"
            ">=1.0.0" -> "1.0.0"
            "1.0.0 - 2.0.0" -> "1.0.0"
            "*" -> None
            "latest" -> None
        """
        if not spec or spec in ("*", "latest", "next"):
            return None

        # Remove leading operators and extract version
        import re

        # Patterns to match version numbers
        patterns = [
            r"^[~^<>=]*\s*(\d+\.\d+\.\d+(?:-[a-zA-Z0-9._-]+)?)",  # semver
            r"^[~^<>=]*\s*(\d+\.\d+)(?:\.\d+)?",  # major.minor
            r"^[~^<>=]*\s*(\d+)(?:\.\d+)?(?:\.\d+)?",  # major only
        ]

        for pattern in patterns:
            match = re.search(pattern, spec)
            if match:
                return match.group(1)

        return None
