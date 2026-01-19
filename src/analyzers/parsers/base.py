"""
Base classes for manifest file parsers.

Provides the abstract base class and registry for all ecosystem-specific parsers.
"""

from abc import ABC, abstractmethod
from fnmatch import fnmatch
from typing import Optional

from src.extractors.base import DependencyData


class ParserRegistry:
    """Registry for manifest file parsers."""

    _parsers: list[type["ManifestParser"]] = []

    @classmethod
    def register(cls, parser_class: type["ManifestParser"]) -> type["ManifestParser"]:
        """
        Register a parser class.

        Use as a decorator:
            @ParserRegistry.register
            class MyParser(ManifestParser):
                ...

        Args:
            parser_class: Parser class to register.

        Returns:
            The parser class (unchanged).
        """
        cls._parsers.append(parser_class)
        return parser_class

    @classmethod
    def get_parsers(cls) -> list[type["ManifestParser"]]:
        """
        Get all registered parsers.

        Returns:
            List of registered parser classes.
        """
        return cls._parsers.copy()

    @classmethod
    def get_parser_for_file(cls, file_path: str) -> Optional["ManifestParser"]:
        """
        Find a parser that can handle the given file.

        Args:
            file_path: Path to the manifest file.

        Returns:
            Parser instance if found, None otherwise.
        """
        for parser_class in cls._parsers:
            if parser_class.can_parse(file_path):
                return parser_class()
        return None

    @classmethod
    def get_supported_patterns(cls) -> list[str]:
        """
        Get all file patterns supported by registered parsers.

        Returns:
            List of glob patterns (e.g., ['requirements.txt', 'package.json']).
        """
        patterns = []
        for parser_class in cls._parsers:
            patterns.extend(parser_class.SUPPORTED_FILES)
        return patterns

    @classmethod
    def clear(cls) -> None:
        """Clear the registry. Useful for testing."""
        cls._parsers = []


class ManifestParser(ABC):
    """
    Abstract base class for manifest file parsers.

    Each parser handles one ecosystem and knows how to parse
    its manifest file formats to extract dependency information.
    """

    # Ecosystem identifier (pypi, npm, maven, nuget, go, rubygems, cargo)
    ECOSYSTEM: str = ""

    # File patterns this parser can handle (e.g., ['requirements.txt', 'Pipfile'])
    SUPPORTED_FILES: list[str] = []

    @abstractmethod
    def parse(self, content: str, file_path: str) -> list[DependencyData]:
        """
        Parse manifest file content and extract dependencies.

        Args:
            content: Raw content of the manifest file.
            file_path: Path to the file (for context and source tracking).

        Returns:
            List of extracted dependencies.
        """
        pass

    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        """
        Check if this parser can handle the given file.

        Args:
            file_path: Path to the file.

        Returns:
            True if this parser can handle the file.
        """
        file_name = file_path.split("/")[-1]
        for pattern in cls.SUPPORTED_FILES:
            if fnmatch(file_name, pattern):
                return True
        return False

    def _create_dependency(
        self,
        package_name: str,
        version: Optional[str],
        file_path: str,
        is_dev: bool = False,
        version_constraint: Optional[str] = None,
    ) -> DependencyData:
        """
        Helper to create a DependencyData instance.

        Args:
            package_name: Name of the package.
            version: Resolved version (if any).
            file_path: Source manifest file.
            is_dev: Whether this is a development dependency.
            version_constraint: Original version constraint string.

        Returns:
            DependencyData instance.
        """
        return DependencyData(
            package_name=package_name,
            version=version,
            ecosystem=self.ECOSYSTEM,
            is_dev_dependency=is_dev,
            source_file=file_path,
            version_constraint=version_constraint,
        )
