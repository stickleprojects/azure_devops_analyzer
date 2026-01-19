"""
Rust ecosystem manifest file parser.

Supports:
- Cargo.toml
"""

import re
from typing import Optional

from src.extractors.base import DependencyData
from src.analyzers.parsers.base import ManifestParser, ParserRegistry


@ParserRegistry.register
class RustParser(ManifestParser):
    """Parser for Rust Cargo.toml files."""

    ECOSYSTEM = "cargo"
    SUPPORTED_FILES = ["Cargo.toml"]

    def parse(self, content: str, file_path: str) -> list[DependencyData]:
        """Parse Cargo.toml content."""
        dependencies = []

        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                # Fall back to regex parsing
                return self._parse_cargo_toml_regex(content, file_path)

        try:
            data = tomllib.loads(content)
        except Exception:
            return self._parse_cargo_toml_regex(content, file_path)

        # Regular dependencies
        for name, spec in data.get("dependencies", {}).items():
            dep = self._parse_cargo_dependency(name, spec, file_path, is_dev=False)
            if dep:
                dependencies.append(dep)

        # Dev dependencies
        for name, spec in data.get("dev-dependencies", {}).items():
            dep = self._parse_cargo_dependency(name, spec, file_path, is_dev=True)
            if dep:
                dependencies.append(dep)

        # Build dependencies (treat as dev)
        for name, spec in data.get("build-dependencies", {}).items():
            dep = self._parse_cargo_dependency(name, spec, file_path, is_dev=True)
            if dep:
                dependencies.append(dep)

        # Target-specific dependencies
        for target, target_data in data.get("target", {}).items():
            if isinstance(target_data, dict):
                for name, spec in target_data.get("dependencies", {}).items():
                    dep = self._parse_cargo_dependency(name, spec, file_path, is_dev=False)
                    if dep:
                        dependencies.append(dep)
                for name, spec in target_data.get("dev-dependencies", {}).items():
                    dep = self._parse_cargo_dependency(name, spec, file_path, is_dev=True)
                    if dep:
                        dependencies.append(dep)

        return dependencies

    def _parse_cargo_dependency(
        self,
        name: str,
        spec,
        file_path: str,
        is_dev: bool,
    ) -> Optional[DependencyData]:
        """Parse a single Cargo dependency specification."""
        if isinstance(spec, str):
            # Simple version string: "1.0"
            version = self._extract_version(spec)
            return self._create_dependency(
                package_name=name,
                version=version,
                file_path=file_path,
                is_dev=is_dev,
                version_constraint=spec,
            )
        elif isinstance(spec, dict):
            # Complex spec: { version = "1.0", features = [...] }
            # Skip git/path dependencies
            if "git" in spec or "path" in spec:
                return None

            version_spec = spec.get("version")
            if version_spec:
                version = self._extract_version(version_spec)
                return self._create_dependency(
                    package_name=name,
                    version=version,
                    file_path=file_path,
                    is_dev=is_dev,
                    version_constraint=version_spec,
                )

        return None

    def _parse_cargo_toml_regex(
        self, content: str, file_path: str
    ) -> list[DependencyData]:
        """Fallback regex-based Cargo.toml parser."""
        dependencies = []
        current_section = None

        for line in content.split("\n"):
            line = line.strip()

            # Section headers
            section_match = re.match(r"\[([^\]]+)\]", line)
            if section_match:
                current_section = section_match.group(1).lower()
                continue

            # Skip if not in a dependencies section
            if not current_section or "dependencies" not in current_section:
                continue

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse name = "version" or name = { version = "..." }
            simple_match = re.match(r'([a-zA-Z0-9_-]+)\s*=\s*"([^"]+)"', line)
            if simple_match:
                name = simple_match.group(1)
                version_spec = simple_match.group(2)
                is_dev = "dev" in current_section or "build" in current_section

                dependencies.append(
                    self._create_dependency(
                        package_name=name,
                        version=self._extract_version(version_spec),
                        file_path=file_path,
                        is_dev=is_dev,
                        version_constraint=version_spec,
                    )
                )
                continue

            # Parse inline table: name = { version = "1.0", ... }
            table_match = re.match(
                r'([a-zA-Z0-9_-]+)\s*=\s*\{.*version\s*=\s*"([^"]+)"', line
            )
            if table_match:
                name = table_match.group(1)
                version_spec = table_match.group(2)
                is_dev = "dev" in current_section or "build" in current_section

                dependencies.append(
                    self._create_dependency(
                        package_name=name,
                        version=self._extract_version(version_spec),
                        file_path=file_path,
                        is_dev=is_dev,
                        version_constraint=version_spec,
                    )
                )

        return dependencies

    def _extract_version(self, version_spec: Optional[str]) -> Optional[str]:
        """
        Extract version from Cargo version specifier.

        Examples:
            "1.0" -> "1.0"
            "^1.0" -> "1.0"
            "~1.0" -> "1.0"
            ">=1.0, <2.0" -> "1.0"
            "=1.0.0" -> "1.0.0"
            "*" -> None
        """
        if not version_spec or version_spec == "*":
            return None

        # Remove operators and extract version
        match = re.search(r"(\d+(?:\.\d+)*(?:-[a-zA-Z0-9._-]+)?)", version_spec)
        if match:
            return match.group(1)

        return None
