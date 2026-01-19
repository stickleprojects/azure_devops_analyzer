"""
Java/Maven ecosystem manifest file parser.

Supports:
- pom.xml (Maven)
"""

import re
from typing import Optional
from xml.etree import ElementTree as ET

from src.extractors.base import DependencyData
from src.analyzers.parsers.base import ManifestParser, ParserRegistry


@ParserRegistry.register
class JavaParser(ManifestParser):
    """Parser for Maven pom.xml files."""

    ECOSYSTEM = "maven"
    SUPPORTED_FILES = ["pom.xml"]

    # Maven XML namespace
    MAVEN_NS = {"m": "http://maven.apache.org/POM/4.0.0"}

    def parse(self, content: str, file_path: str) -> list[DependencyData]:
        """Parse pom.xml content."""
        dependencies = []

        try:
            # Handle namespace in pom.xml
            root = self._parse_xml(content)
        except ET.ParseError:
            return dependencies

        # Extract properties for variable substitution
        properties = self._extract_properties(root)

        # Find all dependency elements
        dep_elements = self._find_dependencies(root)

        for dep_elem in dep_elements:
            dep = self._parse_dependency_element(dep_elem, properties, file_path)
            if dep:
                dependencies.append(dep)

        return dependencies

    def _parse_xml(self, content: str) -> ET.Element:
        """Parse XML content, handling namespaces."""
        # Try with namespace first
        try:
            return ET.fromstring(content)
        except ET.ParseError:
            pass

        # Try stripping namespace
        content_no_ns = re.sub(r'\sxmlns="[^"]+"', "", content, count=1)
        return ET.fromstring(content_no_ns)

    def _extract_properties(self, root: ET.Element) -> dict[str, str]:
        """Extract Maven properties for variable substitution."""
        properties = {}

        # Try both with and without namespace
        for props_elem in root.findall(".//properties"):
            for prop in props_elem:
                tag = prop.tag.split("}")[-1] if "}" in prop.tag else prop.tag
                if prop.text:
                    properties[tag] = prop.text

        for props_elem in root.findall(".//m:properties", self.MAVEN_NS):
            for prop in props_elem:
                tag = prop.tag.split("}")[-1] if "}" in prop.tag else prop.tag
                if prop.text:
                    properties[tag] = prop.text

        return properties

    def _find_dependencies(self, root: ET.Element) -> list[ET.Element]:
        """Find all dependency elements in the POM."""
        deps = []

        # Try both with and without namespace
        deps.extend(root.findall(".//dependency"))
        deps.extend(root.findall(".//m:dependency", self.MAVEN_NS))

        return deps

    def _parse_dependency_element(
        self,
        elem: ET.Element,
        properties: dict[str, str],
        file_path: str,
    ) -> Optional[DependencyData]:
        """Parse a single dependency element."""
        # Get child elements (handle namespace)
        group_id = self._get_child_text(elem, "groupId")
        artifact_id = self._get_child_text(elem, "artifactId")
        version = self._get_child_text(elem, "version")
        scope = self._get_child_text(elem, "scope")

        if not group_id or not artifact_id:
            return None

        # Substitute properties
        if version:
            version = self._substitute_properties(version, properties)

        # Determine if dev dependency
        is_dev = scope in ("test", "provided")

        # Maven package name format: groupId:artifactId
        package_name = f"{group_id}:{artifact_id}"

        return self._create_dependency(
            package_name=package_name,
            version=version,
            file_path=file_path,
            is_dev=is_dev,
            version_constraint=version,
        )

    def _get_child_text(self, elem: ET.Element, tag: str) -> Optional[str]:
        """Get text content of a child element."""
        # Try without namespace
        child = elem.find(tag)
        if child is not None and child.text:
            return child.text.strip()

        # Try with namespace
        child = elem.find(f"m:{tag}", self.MAVEN_NS)
        if child is not None and child.text:
            return child.text.strip()

        return None

    def _substitute_properties(self, value: str, properties: dict[str, str]) -> str:
        """Substitute Maven property references."""
        pattern = r"\$\{([^}]+)\}"

        def replace(match):
            prop_name = match.group(1)
            return properties.get(prop_name, match.group(0))

        result = re.sub(pattern, replace, value)

        # Return None if still contains unresolved properties
        if "${" in result:
            return None

        return result
