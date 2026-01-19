"""
Python ecosystem manifest file parsers.

Supports:
- requirements.txt
- pyproject.toml (PEP 621 and Poetry formats)
- Pipfile
"""

import re
from typing import Optional

from src.extractors.base import DependencyData
from src.analyzers.parsers.base import ManifestParser, ParserRegistry


@ParserRegistry.register
class PythonParser(ManifestParser):
    """Parser for Python dependency manifest files."""

    ECOSYSTEM = "pypi"
    SUPPORTED_FILES = [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-test.txt",
        "requirements_dev.txt",
        "requirements_test.txt",
        "dev-requirements.txt",
        "test-requirements.txt",
        "pyproject.toml",
        "Pipfile",
    ]

    # Regex for parsing requirements.txt lines
    # Matches: package_name, optional extras, optional version specifier
    REQUIREMENTS_PATTERN = re.compile(
        r"^"
        r"(?P<package>[a-zA-Z0-9][-a-zA-Z0-9._]*)"  # Package name
        r"(?:\[(?P<extras>[^\]]+)\])?"  # Optional extras [extra1,extra2]
        r"(?P<constraint>(?:[<>=!~]+[^;#\s]+)?)"  # Version constraint
        r"(?:;[^#]*)?"  # Optional environment markers
        r"(?:\s*#.*)?"  # Optional comment
        r"$"
    )

    def parse(self, content: str, file_path: str) -> list[DependencyData]:
        """Parse Python manifest file content."""
        file_name = file_path.split("/")[-1].lower()

        if file_name.endswith(".toml") or file_name == "pyproject.toml":
            return self._parse_pyproject_toml(content, file_path)
        elif file_name == "pipfile":
            return self._parse_pipfile(content, file_path)
        else:
            return self._parse_requirements_txt(content, file_path)

    def _parse_requirements_txt(
        self, content: str, file_path: str
    ) -> list[DependencyData]:
        """
        Parse requirements.txt format.

        Handles:
        - Simple package names: requests
        - Version specs: requests==2.28.0, requests>=2.0
        - Extras: requests[security]
        - Comments and blank lines
        - -r includes (noted but not followed)
        """
        dependencies = []
        file_name = file_path.split("/")[-1].lower()

        # Determine if this is a dev requirements file
        is_dev_file = any(
            marker in file_name
            for marker in ["dev", "test", "development", "testing"]
        )

        for line in content.split("\n"):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Skip options and includes
            if line.startswith("-"):
                continue

            # Skip editable installs
            if line.startswith("git+") or line.startswith("http"):
                continue

            match = self.REQUIREMENTS_PATTERN.match(line)
            if match:
                package_name = match.group("package")
                constraint = match.group("constraint") or ""

                # Extract version from constraint
                version = self._extract_version_from_constraint(constraint)

                dependencies.append(
                    self._create_dependency(
                        package_name=package_name,
                        version=version,
                        file_path=file_path,
                        is_dev=is_dev_file,
                        version_constraint=constraint if constraint else None,
                    )
                )

        return dependencies

    def _parse_pyproject_toml(
        self, content: str, file_path: str
    ) -> list[DependencyData]:
        """
        Parse pyproject.toml format (PEP 621 and Poetry).

        Handles:
        - [project.dependencies] (PEP 621)
        - [project.optional-dependencies] (PEP 621)
        - [tool.poetry.dependencies] (Poetry)
        - [tool.poetry.dev-dependencies] (Poetry)
        - [tool.poetry.group.*.dependencies] (Poetry 1.2+)
        """
        dependencies = []

        try:
            import tomllib
        except ImportError:
            # Python < 3.11, try tomli
            try:
                import tomli as tomllib
            except ImportError:
                # No TOML parser available, fall back to regex parsing
                return self._parse_pyproject_toml_regex(content, file_path)

        try:
            data = tomllib.loads(content)
        except Exception:
            # Parse error, fall back to regex
            return self._parse_pyproject_toml_regex(content, file_path)

        # PEP 621 format: [project]
        project = data.get("project", {})

        # Main dependencies
        for dep_spec in project.get("dependencies", []):
            dep = self._parse_pep508_spec(dep_spec, file_path, is_dev=False)
            if dep:
                dependencies.append(dep)

        # Optional dependencies (treat as dev)
        for group_name, deps in project.get("optional-dependencies", {}).items():
            is_dev = group_name.lower() in ["dev", "test", "testing", "development"]
            for dep_spec in deps:
                dep = self._parse_pep508_spec(dep_spec, file_path, is_dev=is_dev)
                if dep:
                    dependencies.append(dep)

        # Poetry format: [tool.poetry]
        poetry = data.get("tool", {}).get("poetry", {})

        # Main dependencies
        for pkg_name, spec in poetry.get("dependencies", {}).items():
            if pkg_name.lower() == "python":
                continue
            dep = self._parse_poetry_spec(pkg_name, spec, file_path, is_dev=False)
            if dep:
                dependencies.append(dep)

        # Dev dependencies (old format)
        for pkg_name, spec in poetry.get("dev-dependencies", {}).items():
            dep = self._parse_poetry_spec(pkg_name, spec, file_path, is_dev=True)
            if dep:
                dependencies.append(dep)

        # Group dependencies (Poetry 1.2+)
        for group_name, group_data in poetry.get("group", {}).items():
            is_dev = group_name.lower() in ["dev", "test", "testing", "development"]
            for pkg_name, spec in group_data.get("dependencies", {}).items():
                dep = self._parse_poetry_spec(pkg_name, spec, file_path, is_dev=is_dev)
                if dep:
                    dependencies.append(dep)

        return dependencies

    def _parse_pyproject_toml_regex(
        self, content: str, file_path: str
    ) -> list[DependencyData]:
        """Fallback regex-based pyproject.toml parser."""
        dependencies = []

        # Find dependencies lists
        deps_pattern = re.compile(
            r'dependencies\s*=\s*\[(.*?)\]',
            re.DOTALL
        )

        for match in deps_pattern.finditer(content):
            deps_block = match.group(1)
            # Extract quoted strings
            for dep_match in re.finditer(r'"([^"]+)"', deps_block):
                dep = self._parse_pep508_spec(dep_match.group(1), file_path, is_dev=False)
                if dep:
                    dependencies.append(dep)

        return dependencies

    def _parse_pep508_spec(
        self, spec: str, file_path: str, is_dev: bool
    ) -> Optional[DependencyData]:
        """Parse a PEP 508 dependency specification."""
        match = self.REQUIREMENTS_PATTERN.match(spec.strip())
        if match:
            package_name = match.group("package")
            constraint = match.group("constraint") or ""
            version = self._extract_version_from_constraint(constraint)

            return self._create_dependency(
                package_name=package_name,
                version=version,
                file_path=file_path,
                is_dev=is_dev,
                version_constraint=constraint if constraint else None,
            )
        return None

    def _parse_poetry_spec(
        self, pkg_name: str, spec, file_path: str, is_dev: bool
    ) -> Optional[DependencyData]:
        """Parse a Poetry dependency specification."""
        if isinstance(spec, str):
            # Simple version string: "^1.0.0"
            version = self._extract_version_from_constraint(spec)
            return self._create_dependency(
                package_name=pkg_name,
                version=version,
                file_path=file_path,
                is_dev=is_dev,
                version_constraint=spec,
            )
        elif isinstance(spec, dict):
            # Complex spec: {version = "^1.0", optional = true}
            version_constraint = spec.get("version", "")
            version = self._extract_version_from_constraint(version_constraint)
            return self._create_dependency(
                package_name=pkg_name,
                version=version,
                file_path=file_path,
                is_dev=is_dev,
                version_constraint=version_constraint if version_constraint else None,
            )
        return None

    def _parse_pipfile(self, content: str, file_path: str) -> list[DependencyData]:
        """
        Parse Pipfile format.

        Handles:
        - [packages] section
        - [dev-packages] section
        """
        dependencies = []
        current_section = None
        is_dev = False

        for line in content.split("\n"):
            line = line.strip()

            # Section headers
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].lower()
                if section == "packages":
                    current_section = "packages"
                    is_dev = False
                elif section == "dev-packages":
                    current_section = "dev-packages"
                    is_dev = True
                else:
                    current_section = None
                continue

            # Skip if not in a packages section
            if current_section is None:
                continue

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse package = version_spec
            if "=" in line:
                parts = line.split("=", 1)
                pkg_name = parts[0].strip().strip('"').strip("'")
                version_spec = parts[1].strip().strip('"').strip("'")

                # Skip python_version and other non-package entries
                if pkg_name.lower() in ["python_version", "python_full_version"]:
                    continue

                version = None
                constraint = None

                if version_spec != "*":
                    constraint = version_spec
                    version = self._extract_version_from_constraint(version_spec)

                dependencies.append(
                    self._create_dependency(
                        package_name=pkg_name,
                        version=version,
                        file_path=file_path,
                        is_dev=is_dev,
                        version_constraint=constraint,
                    )
                )

        return dependencies

    def _extract_version_from_constraint(self, constraint: str) -> Optional[str]:
        """
        Extract a version number from a version constraint.

        Examples:
            "==2.28.0" -> "2.28.0"
            ">=1.0,<2.0" -> "1.0"
            "^1.0.0" -> "1.0.0"
            "~=1.0" -> "1.0"
        """
        if not constraint:
            return None

        # Common version patterns
        patterns = [
            r"==\s*([0-9][0-9a-zA-Z._-]*)",  # ==1.0.0
            r"^\^([0-9][0-9a-zA-Z._-]*)",  # ^1.0.0 (Poetry caret)
            r"^~([0-9][0-9a-zA-Z._-]*)",  # ~1.0.0 (Poetry tilde)
            r"~=\s*([0-9][0-9a-zA-Z._-]*)",  # ~=1.0 (compatible release)
            r">=\s*([0-9][0-9a-zA-Z._-]*)",  # >=1.0
        ]

        for pattern in patterns:
            match = re.search(pattern, constraint)
            if match:
                return match.group(1)

        return None
