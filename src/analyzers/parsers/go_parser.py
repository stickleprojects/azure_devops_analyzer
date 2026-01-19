"""
Go ecosystem manifest file parser.

Supports:
- go.mod
"""

import re
from typing import Optional

from src.extractors.base import DependencyData
from src.analyzers.parsers.base import ManifestParser, ParserRegistry


@ParserRegistry.register
class GoParser(ManifestParser):
    """Parser for Go go.mod files."""

    ECOSYSTEM = "go"
    SUPPORTED_FILES = ["go.mod"]

    def parse(self, content: str, file_path: str) -> list[DependencyData]:
        """Parse go.mod content."""
        dependencies = []

        # Parse require blocks and single require statements
        dependencies.extend(self._parse_require_block(content, file_path))
        dependencies.extend(self._parse_single_requires(content, file_path))

        # Remove duplicates (prefer block-style entries)
        seen = set()
        unique_deps = []
        for dep in dependencies:
            if dep.package_name not in seen:
                seen.add(dep.package_name)
                unique_deps.append(dep)

        return unique_deps

    def _parse_require_block(
        self, content: str, file_path: str
    ) -> list[DependencyData]:
        """
        Parse require blocks.

        Format:
        require (
            github.com/pkg/errors v0.9.1
            golang.org/x/sys v0.0.0-20210615035016-665e8c7367d1 // indirect
        )
        """
        dependencies = []

        # Find require blocks
        block_pattern = re.compile(
            r"require\s*\(\s*(.*?)\s*\)",
            re.DOTALL,
        )

        for block_match in block_pattern.finditer(content):
            block_content = block_match.group(1)

            for line in block_content.split("\n"):
                dep = self._parse_require_line(line, file_path)
                if dep:
                    dependencies.append(dep)

        return dependencies

    def _parse_single_requires(
        self, content: str, file_path: str
    ) -> list[DependencyData]:
        """
        Parse single-line require statements.

        Format:
        require github.com/pkg/errors v0.9.1
        """
        dependencies = []

        # Match single require statements (not in blocks)
        pattern = re.compile(
            r"^require\s+([^\s(]+)\s+([^\s]+)(?:\s+//.*)?$",
            re.MULTILINE,
        )

        for match in pattern.finditer(content):
            module_path = match.group(1)
            version = match.group(2)

            dependencies.append(
                self._create_dependency(
                    package_name=module_path,
                    version=self._clean_version(version),
                    file_path=file_path,
                    is_dev=False,
                    version_constraint=version,
                )
            )

        return dependencies

    def _parse_require_line(
        self, line: str, file_path: str
    ) -> Optional[DependencyData]:
        """Parse a single line from a require block."""
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("//"):
            return None

        # Parse: module_path version [// indirect]
        pattern = re.compile(
            r"^([^\s]+)\s+([^\s]+)(?:\s+//\s*(.*))?$"
        )

        match = pattern.match(line)
        if not match:
            return None

        module_path = match.group(1)
        version = match.group(2)
        comment = match.group(3) or ""

        # Check if indirect (typically dev/transitive dependency)
        is_dev = "indirect" in comment.lower()

        return self._create_dependency(
            package_name=module_path,
            version=self._clean_version(version),
            file_path=file_path,
            is_dev=is_dev,
            version_constraint=version,
        )

    def _clean_version(self, version: str) -> Optional[str]:
        """
        Clean and normalize Go version string.

        Examples:
            "v1.0.0" -> "1.0.0"
            "v0.0.0-20210615035016-665e8c7367d1" -> "0.0.0-20210615035016-665e8c7367d1"
        """
        if not version:
            return None

        # Remove leading 'v'
        if version.startswith("v"):
            version = version[1:]

        return version
