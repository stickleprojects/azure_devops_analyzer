"""
.NET/NuGet ecosystem manifest file parser.

Supports:
- *.csproj (SDK-style and old-style)
- packages.config
"""

import re
from typing import Optional
from xml.etree import ElementTree as ET

from src.extractors.base import DependencyData
from src.analyzers.parsers.base import ManifestParser, ParserRegistry


@ParserRegistry.register
class DotNetParser(ManifestParser):
    """Parser for .NET project files and packages.config."""

    ECOSYSTEM = "nuget"
    SUPPORTED_FILES = ["*.csproj", "packages.config"]

    def parse(self, content: str, file_path: str) -> list[DependencyData]:
        """Parse .NET manifest file content."""
        file_name = file_path.split("/")[-1].lower()

        if file_name == "packages.config":
            return self._parse_packages_config(content, file_path)
        elif file_name.endswith(".csproj"):
            return self._parse_csproj(content, file_path)

        return []

    def _parse_csproj(self, content: str, file_path: str) -> list[DependencyData]:
        """
        Parse .csproj file (SDK-style format).

        Handles:
        - <PackageReference Include="..." Version="..." />
        - <PackageReference Include="...">
            <Version>...</Version>
          </PackageReference>
        """
        dependencies = []

        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            # Fall back to regex parsing
            return self._parse_csproj_regex(content, file_path)

        # Find all PackageReference elements
        for pkg_ref in root.findall(".//PackageReference"):
            dep = self._parse_package_reference(pkg_ref, file_path)
            if dep:
                dependencies.append(dep)

        return dependencies

    def _parse_package_reference(
        self, elem: ET.Element, file_path: str
    ) -> Optional[DependencyData]:
        """Parse a PackageReference element."""
        package_name = elem.get("Include") or elem.get("Update")
        if not package_name:
            return None

        # Version can be an attribute or child element
        version = elem.get("Version")
        if not version:
            version_elem = elem.find("Version")
            if version_elem is not None and version_elem.text:
                version = version_elem.text.strip()

        # Check for dev packages (common test/dev packages)
        is_dev = self._is_dev_package(package_name)

        # Extract version from constraint if needed
        resolved_version = self._extract_version(version)

        return self._create_dependency(
            package_name=package_name,
            version=resolved_version,
            file_path=file_path,
            is_dev=is_dev,
            version_constraint=version,
        )

    def _parse_csproj_regex(
        self, content: str, file_path: str
    ) -> list[DependencyData]:
        """Fallback regex parser for csproj files."""
        dependencies = []

        # Match PackageReference with Include and Version attributes
        pattern = re.compile(
            r'<PackageReference\s+'
            r'Include="([^"]+)"'
            r'(?:\s+Version="([^"]*)")?',
            re.IGNORECASE,
        )

        for match in pattern.finditer(content):
            package_name = match.group(1)
            version = match.group(2)

            is_dev = self._is_dev_package(package_name)
            resolved_version = self._extract_version(version)

            dependencies.append(
                self._create_dependency(
                    package_name=package_name,
                    version=resolved_version,
                    file_path=file_path,
                    is_dev=is_dev,
                    version_constraint=version,
                )
            )

        return dependencies

    def _parse_packages_config(
        self, content: str, file_path: str
    ) -> list[DependencyData]:
        """
        Parse packages.config file (old NuGet format).

        Format:
        <packages>
          <package id="..." version="..." targetFramework="..." />
        </packages>
        """
        dependencies = []

        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return dependencies

        for pkg_elem in root.findall(".//package"):
            package_name = pkg_elem.get("id")
            version = pkg_elem.get("version")

            if not package_name:
                continue

            is_dev = (
                pkg_elem.get("developmentDependency", "false").lower() == "true"
                or self._is_dev_package(package_name)
            )

            dependencies.append(
                self._create_dependency(
                    package_name=package_name,
                    version=version,
                    file_path=file_path,
                    is_dev=is_dev,
                    version_constraint=version,
                )
            )

        return dependencies

    def _is_dev_package(self, package_name: str) -> bool:
        """Check if package is typically a dev dependency."""
        dev_indicators = [
            "test",
            "mock",
            "xunit",
            "nunit",
            "mstest",
            "moq",
            "fluentassertions",
            "shouldly",
            "coverlet",
            "benchmark",
        ]
        name_lower = package_name.lower()
        return any(indicator in name_lower for indicator in dev_indicators)

    def _extract_version(self, version_spec: Optional[str]) -> Optional[str]:
        """
        Extract version from NuGet version specifier.

        Examples:
            "1.0.0" -> "1.0.0"
            "[1.0.0]" -> "1.0.0"
            "(1.0.0,2.0.0)" -> "1.0.0"
            "[1.0.0,)" -> "1.0.0"
        """
        if not version_spec:
            return None

        # Remove brackets and get first version number
        cleaned = version_spec.strip("[]() ")
        parts = cleaned.split(",")
        if parts:
            first_version = parts[0].strip()
            if first_version and first_version[0].isdigit():
                return first_version

        # Try regex extraction
        match = re.search(r"(\d+(?:\.\d+)*(?:-[a-zA-Z0-9._-]+)?)", version_spec)
        if match:
            return match.group(1)

        return None
