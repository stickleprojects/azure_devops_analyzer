"""
Ruby ecosystem manifest file parser.

Supports:
- Gemfile
"""

import re
from typing import Optional

from src.extractors.base import DependencyData
from src.analyzers.parsers.base import ManifestParser, ParserRegistry


@ParserRegistry.register
class RubyParser(ManifestParser):
    """Parser for Ruby Gemfile files."""

    ECOSYSTEM = "rubygems"
    SUPPORTED_FILES = ["Gemfile"]

    def parse(self, content: str, file_path: str) -> list[DependencyData]:
        """Parse Gemfile content."""
        dependencies = []
        current_group = None
        in_group = False

        for line in content.split("\n"):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Track group blocks
            group_match = re.match(r"group\s+(.+?)\s+do", line)
            if group_match:
                groups_str = group_match.group(1)
                # Parse groups like :development, :test or [:development, :test]
                groups = re.findall(r":(\w+)", groups_str)
                current_group = groups
                in_group = True
                continue

            if line == "end" and in_group:
                current_group = None
                in_group = False
                continue

            # Parse gem declarations
            dep = self._parse_gem_line(line, file_path, current_group)
            if dep:
                dependencies.append(dep)

        return dependencies

    def _parse_gem_line(
        self,
        line: str,
        file_path: str,
        current_group: Optional[list[str]],
    ) -> Optional[DependencyData]:
        """
        Parse a gem declaration line.

        Formats:
        - gem 'rails'
        - gem 'rails', '~> 6.0'
        - gem 'rails', '>= 5.0', '< 6.0'
        - gem 'rails', git: 'https://github.com/rails/rails.git'
        - gem 'rails', group: :development
        """
        # Match gem declarations
        pattern = re.compile(
            r"^gem\s+['\"]([^'\"]+)['\"]"
            r"(?:,\s*['\"]([^'\"]+)['\"])?"  # Optional version
            r"(.*)$"  # Rest of line (options)
        )

        match = pattern.match(line)
        if not match:
            return None

        gem_name = match.group(1)
        version_spec = match.group(2)
        options_str = match.group(3) or ""

        # Skip git/github/path sources (no version)
        if any(src in options_str for src in ["git:", "github:", "path:"]):
            return None

        # Check for inline group specification
        inline_group = self._extract_inline_group(options_str)
        groups = inline_group if inline_group else current_group

        # Determine if dev dependency
        is_dev = self._is_dev_group(groups)

        # Extract version
        version = self._extract_version(version_spec)

        return self._create_dependency(
            package_name=gem_name,
            version=version,
            file_path=file_path,
            is_dev=is_dev,
            version_constraint=version_spec,
        )

    def _extract_inline_group(self, options_str: str) -> Optional[list[str]]:
        """Extract group from inline options."""
        # Match group: :development or group: [:development, :test]
        group_match = re.search(r"group:\s*\[?([^\],]+(?:,\s*[^\],]+)*)\]?", options_str)
        if group_match:
            groups_str = group_match.group(1)
            return re.findall(r":(\w+)", groups_str)
        return None

    def _is_dev_group(self, groups: Optional[list[str]]) -> bool:
        """Check if groups indicate a dev dependency."""
        if not groups:
            return False

        dev_groups = {"development", "test", "testing", "dev"}
        return any(g.lower() in dev_groups for g in groups)

    def _extract_version(self, version_spec: Optional[str]) -> Optional[str]:
        """
        Extract version from Ruby version specifier.

        Examples:
            "~> 6.0" -> "6.0"
            ">= 5.0" -> "5.0"
            "= 1.0.0" -> "1.0.0"
            "1.0.0" -> "1.0.0"
        """
        if not version_spec:
            return None

        # Remove operators and extract version number
        match = re.search(r"(\d+(?:\.\d+)*(?:\.\d+)?(?:\.[a-zA-Z0-9._-]+)?)", version_spec)
        if match:
            return match.group(1)

        return None
