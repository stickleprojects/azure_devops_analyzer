"""
README file analysis module.

Analyzes README files to extract meaningful insights about repositories
including technology stack, purpose, installation instructions, and documentation quality.
"""

import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class ReadmeAnalysis:
    """Results from README file analysis."""

    # Basic metrics
    word_count: int
    line_count: int
    character_count: int

    # Content sections detected
    has_description: bool
    has_installation: bool
    has_usage: bool
    has_contributing: bool
    has_license: bool
    has_badges: bool
    has_table_of_contents: bool

    # Technology detection
    technologies: List[str]
    programming_languages: List[str]
    frameworks: List[str]
    databases: List[str]
    deployment_platforms: List[str]

    # Documentation quality
    documentation_score: float  # 0.0 - 10.0
    readability_score: float    # 0.0 - 10.0

    # Extracted metadata
    project_purpose: Optional[str]
    key_features: List[str]

    # Scope context
    scope_type: Optional[str]  # repository, module, package, component
    scope_coverage: float      # 0.0 - 10.0 (how well README covers its scope)

    # Analysis metadata
    analyzed_at: datetime
    analysis_version: str = "1.1"


class ReadmeAnalyzer:
    """Analyzer for README file content."""

    # Technology patterns for detection
    TECHNOLOGY_PATTERNS = {
        'languages': {
            'Python': r'\b(?:python|py|pip|pypi|pipenv|poetry|conda)\b',
            'JavaScript': r'\b(?:javascript|js|node|npm|yarn|webpack)\b',
            'TypeScript': r'\b(?:typescript|ts|tsc)\b',
            'Java': r'\b(?:java|maven|gradle|spring)\b',
            'C#': r'\b(?:c#|csharp|dotnet|nuget|visual studio)\b',
            'Go': r'\b(?:golang|go mod|go get)\b',
            'Rust': r'\b(?:rust|cargo|rustc)\b',
            'Ruby': r'\b(?:ruby|gem|bundler|rails)\b',
            'PHP': r'\b(?:php|composer|laravel|symfony)\b',
            'Swift': r'\b(?:swift|xcode|ios)\b',
            'Kotlin': r'\b(?:kotlin|gradle)\b'
        },
        'frameworks': {
            'React': r'\b(?:react|jsx|create-react-app)\b',
            'Vue': r'\b(?:vue|vuejs|nuxt)\b',
            'Angular': r'\b(?:angular|ng)\b',
            'Express': r'\b(?:express|expressjs)\b',
            'Django': r'\b(?:django|django-admin)\b',
            'Flask': r'\b(?:flask|wsgi)\b',
            'FastAPI': r'\b(?:fastapi|uvicorn)\b',
            'Spring': r'\b(?:spring|springboot)\b',
            'Laravel': r'\b(?:laravel|artisan)\b',
            'Rails': r'\b(?:rails|ruby on rails)\b'
        },
        'databases': {
            'PostgreSQL': r'\b(?:postgresql|postgres|psql)\b',
            'MySQL': r'\b(?:mysql|mariadb)\b',
            'MongoDB': r'\b(?:mongodb|mongo|mongoose)\b',
            'Redis': r'\b(?:redis)\b',
            'SQLite': r'\b(?:sqlite)\b',
            'ElasticSearch': r'\b(?:elasticsearch|elastic)\b'
        },
        'platforms': {
            'Docker': r'\b(?:docker|dockerfile|docker-compose)\b',
            'Kubernetes': r'\b(?:kubernetes|k8s|kubectl|helm)\b',
            'AWS': r'\b(?:aws|amazon web services|ec2|s3|lambda)\b',
            'Azure': r'\b(?:azure|microsoft azure)\b',
            'GCP': r'\b(?:gcp|google cloud|google cloud platform)\b',
            'Heroku': r'\b(?:heroku)\b',
            'Vercel': r'\b(?:vercel|zeit)\b',
            'Netlify': r'\b(?:netlify)\b'
        }
    }

    # Section header patterns
    SECTION_PATTERNS = {
        'description': r'(?:^|\n)##+\s*(?:about|description|overview|what is|intro)',
        'installation': r'(?:^|\n)##+\s*(?:install|installation|setup|getting started|quick start)',
        'usage': r'(?:^|\n)##+\s*(?:usage|how to use|examples|getting started)',
        'contributing': r'(?:^|\n)##+\s*(?:contribut|development|developers)',
        'license': r'(?:^|\n)##+\s*(?:license|licensing)',
    }

    def analyze(
        self,
        content: str,
        file_path: str = "",
        scope_type: Optional[str] = None,
        scope_path: Optional[str] = None
    ) -> ReadmeAnalysis:
        """
        Analyze README file content with scope awareness.

        Args:
            content: The README file content.
            file_path: Path to the README file (for context).
            scope_type: Type of scope (repository, module, package, component).
            scope_path: Directory path this README covers.

        Returns:
            ReadmeAnalysis with extracted insights.
        """
        if not content:
            return self._empty_analysis(scope_type)

        content_lower = content.lower()

        # Basic metrics
        word_count = len(content.split())
        line_count = len(content.split('\n'))
        character_count = len(content)

        # Section detection
        sections = self._detect_sections(content_lower)

        # Technology detection (scope-aware)
        tech_stack = self._detect_technologies(content_lower, scope_type)

        # Badge detection
        has_badges = self._has_badges(content)

        # Table of contents detection
        has_toc = self._has_table_of_contents(content_lower)

        # Quality scoring (scope-aware)
        doc_score = self._calculate_documentation_score(
            sections, tech_stack, word_count, has_badges, has_toc, scope_type
        )
        readability_score = self._calculate_readability_score(content, word_count)

        # Scope coverage scoring
        scope_coverage = self._calculate_scope_coverage(content, scope_type, sections)

        # Extract project purpose and features (scope-aware)
        purpose = self._extract_purpose(content, scope_type)
        features = self._extract_features(content, scope_type)

        return ReadmeAnalysis(
            word_count=word_count,
            line_count=line_count,
            character_count=character_count,
            has_description=sections['description'],
            has_installation=sections['installation'],
            has_usage=sections['usage'],
            has_contributing=sections['contributing'],
            has_license=sections['license'],
            has_badges=has_badges,
            has_table_of_contents=has_toc,
            technologies=tech_stack['all'],
            programming_languages=tech_stack['languages'],
            frameworks=tech_stack['frameworks'],
            databases=tech_stack['databases'],
            deployment_platforms=tech_stack['platforms'],
            documentation_score=doc_score,
            readability_score=readability_score,
            project_purpose=purpose,
            key_features=features,
            scope_type=scope_type,
            scope_coverage=scope_coverage,
            analyzed_at=datetime.utcnow()
        )

    def _empty_analysis(self, scope_type: Optional[str] = None) -> ReadmeAnalysis:
        """Return empty analysis for missing or empty README."""
        return ReadmeAnalysis(
            word_count=0,
            line_count=0,
            character_count=0,
            has_description=False,
            has_installation=False,
            has_usage=False,
            has_contributing=False,
            has_license=False,
            has_badges=False,
            has_table_of_contents=False,
            technologies=[],
            programming_languages=[],
            frameworks=[],
            databases=[],
            deployment_platforms=[],
            documentation_score=0.0,
            readability_score=0.0,
            project_purpose=None,
            key_features=[],
            scope_type=scope_type,
            scope_coverage=0.0,
            analyzed_at=datetime.utcnow()
        )

    def _detect_sections(self, content_lower: str) -> Dict[str, bool]:
        """Detect common README sections."""
        sections = {}
        for section_name, pattern in self.SECTION_PATTERNS.items():
            sections[section_name] = bool(re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE))
        return sections

    def _detect_technologies(self, content_lower: str, scope_type: Optional[str] = None) -> Dict[str, List[str]]:
        """Detect technologies mentioned in README."""
        tech_stack = {
            'languages': [],
            'frameworks': [],
            'databases': [],
            'platforms': [],
            'all': []
        }

        for category, tech_dict in self.TECHNOLOGY_PATTERNS.items():
            for tech_name, pattern in tech_dict.items():
                if re.search(pattern, content_lower, re.IGNORECASE):
                    tech_stack[category].append(tech_name)
                    tech_stack['all'].append(tech_name)

        return tech_stack

    def _has_badges(self, content: str) -> bool:
        """Check if README contains badges (shields.io, etc.)."""
        badge_patterns = [
            r'!\[.*\]\(https://img\.shields\.io',
            r'!\[.*\]\(https://badge',
            r'!\[.*\]\(https://github\.com/.*/workflows/.*/badge\.svg\)',
            r'!\[.*\]\(https://codecov\.io',
            r'!\[.*\]\(https://travis-ci',
            r'!\[.*\]\(https://circleci'
        ]

        for pattern in badge_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False

    def _has_table_of_contents(self, content_lower: str) -> bool:
        """Check if README has a table of contents."""
        toc_patterns = [
            r'table of contents',
            r'- \[.*\]\(#.*\)',  # Markdown links to sections
            r'\* \[.*\]\(#.*\)'
        ]

        for pattern in toc_patterns:
            if re.search(pattern, content_lower):
                return True
        return False

    def _calculate_documentation_score(
        self,
        sections: Dict[str, bool],
        tech_stack: Dict[str, List[str]],
        word_count: int,
        has_badges: bool,
        has_toc: bool
    ) -> float:
        """Calculate documentation quality score (0-10)."""
        score = 0.0

        # Section completeness (4 points)
        section_score = sum(sections.values()) / len(sections) * 4
        score += section_score

        # Content length (2 points)
        if word_count >= 200:
            score += 2
        elif word_count >= 50:
            score += 1

        # Technology information (2 points)
        if tech_stack['all']:
            score += min(len(tech_stack['all']) * 0.5, 2)

        # Professional touches (2 points)
        if has_badges:
            score += 1
        if has_toc:
            score += 1

        return min(score, 10.0)

    def _calculate_readability_score(self, content: str, word_count: int) -> float:
        """Calculate readability score (0-10) based on structure and clarity."""
        if word_count == 0:
            return 0.0

        score = 5.0  # Base score

        # Header structure
        headers = len(re.findall(r'^#+\s', content, re.MULTILINE))
        if headers >= 3:
            score += 1
        elif headers >= 1:
            score += 0.5

        # Paragraph breaks (good structure)
        paragraphs = len(re.split(r'\n\s*\n', content.strip()))
        if paragraphs >= 3:
            score += 1

        # Code blocks (clear examples)
        code_blocks = len(re.findall(r'```|`[^`]+`', content))
        if code_blocks >= 3:
            score += 1
        elif code_blocks >= 1:
            score += 0.5

        # Lists (organized information)
        lists = len(re.findall(r'^[\-\*\+]|\d+\.', content, re.MULTILINE))
        if lists >= 5:
            score += 1
        elif lists >= 2:
            score += 0.5

        # Penalty for very short or very long content
        if word_count < 20:
            score -= 2
        elif word_count > 2000:
            score -= 1

        return max(0.0, min(score, 10.0))

    def _extract_purpose(self, content: str) -> Optional[str]:
        """Extract project purpose from the first paragraph or description."""
        lines = content.strip().split('\n')

        # Skip title and empty lines
        description_start = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#'):
                description_start = i
                break

        # Get first substantial paragraph
        purpose_lines = []
        for line in lines[description_start:]:
            line = line.strip()
            if not line:
                if purpose_lines:
                    break
                continue
            if line.startswith('#'):
                break
            purpose_lines.append(line)
            if len(' '.join(purpose_lines)) > 300:  # Limit length
                break

        purpose = ' '.join(purpose_lines).strip()
        return purpose if len(purpose) > 10 else None

    def _extract_features(self, content: str) -> List[str]:
        """Extract key features from README content."""
        features = []

        # Look for feature lists
        feature_patterns = [
            r'(?:^|\n)(?:##?\s*)?(?:features?|highlights?|benefits?).*?(?=\n(?:#|$))',
            r'(?:^|\n)[\-\*\+]\s*(.+?)(?=\n(?:[\-\*\+]|\n|$))'
        ]

        for pattern in feature_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]

                # Extract list items
                list_items = re.findall(r'[\-\*\+]\s*(.+)', match)
                for item in list_items:
                    item = item.strip()
                    if 10 <= len(item) <= 100:  # Reasonable feature length
                        features.append(item)

        return features[:10]  # Limit to 10 features

    def _calculate_scope_coverage(
        self,
        content: str,
        scope_type: Optional[str],
        sections: Dict[str, bool]
    ) -> float:
        """
        Calculate how well the README covers its intended scope.

        Args:
            content: README content.
            scope_type: Type of scope (repository, module, package, component).
            sections: Detected sections.

        Returns:
            Score from 0.0 to 10.0.
        """
        if not scope_type:
            return 5.0

        score = 0.0
        content_lower = content.lower()

        if scope_type == "repository":
            # Repository READMEs should have comprehensive information
            if sections.get('description', False):
                score += 2.0
            if sections.get('installation', False):
                score += 2.0
            if sections.get('usage', False):
                score += 2.0
            if sections.get('contributing', False):
                score += 1.5
            if sections.get('license', False):
                score += 1.0
            # Check for project structure or architecture mentions
            if any(word in content_lower for word in ['architecture', 'structure', 'overview']):
                score += 1.5

        elif scope_type == "module":
            # Module READMEs should focus on functionality and usage
            if sections.get('description', False):
                score += 3.0
            if sections.get('usage', False):
                score += 3.0
            if sections.get('installation', False):
                score += 2.0
            # Check for API documentation
            if any(word in content_lower for word in ['api', 'functions', 'methods', 'interface']):
                score += 2.0

        elif scope_type == "package":
            # Package READMEs should explain the package purpose and usage
            if sections.get('description', False):
                score += 3.0
            if sections.get('installation', False):
                score += 3.0
            if sections.get('usage', False):
                score += 2.0
            # Check for package-specific information
            if any(word in content_lower for word in ['import', 'require', 'package']):
                score += 2.0

        elif scope_type == "component":
            # Component READMEs can be smaller but should explain purpose
            if sections.get('description', False):
                score += 5.0
            if sections.get('usage', False):
                score += 3.0
            # Check for examples
            if any(word in content_lower for word in ['example', 'demo', 'sample']):
                score += 2.0

        return min(score, 10.0)

    def _calculate_documentation_score(
        self,
        sections: Dict[str, bool],
        tech_stack: Dict[str, List[str]],
        word_count: int,
        has_badges: bool,
        has_toc: bool,
        scope_type: Optional[str] = None
    ) -> float:
        """Calculate documentation quality score (0-10) with scope awareness."""
        score = 0.0

        # Base section scoring (adjusted by scope)
        if scope_type == "repository":
            # Repository READMEs need more comprehensive sections
            section_weights = {
                'description': 1.0,
                'installation': 1.0,
                'usage': 1.0,
                'contributing': 0.5,
                'license': 0.5
            }
        elif scope_type in ["module", "package"]:
            # Module/Package READMEs prioritize usage and description
            section_weights = {
                'description': 1.5,
                'installation': 1.0,
                'usage': 1.5,
                'contributing': 0.0,
                'license': 0.0
            }
        else:  # component or unknown
            # Component READMEs can be simpler
            section_weights = {
                'description': 2.0,
                'installation': 0.5,
                'usage': 1.5,
                'contributing': 0.0,
                'license': 0.0
            }

        for section, has_section in sections.items():
            weight = section_weights.get(section, 0.0)
            if has_section:
                score += weight

        # Content length scoring (scope-adjusted)
        min_words = {
            "repository": 200,
            "module": 100,
            "package": 100,
            "component": 50
        }
        min_word_count = min_words.get(scope_type, 100)

        if word_count >= min_word_count:
            score += 2
        elif word_count >= min_word_count // 2:
            score += 1

        # Technology information (2 points)
        if tech_stack['all']:
            score += min(len(tech_stack['all']) * 0.5, 2)

        # Professional touches (scope-adjusted)
        if has_badges:
            score += 1.0 if scope_type == "repository" else 0.5
        if has_toc:
            score += 1.0 if scope_type == "repository" else 0.5

        return min(score, 10.0)

    def _extract_purpose(self, content: str, scope_type: Optional[str] = None) -> Optional[str]:
        """Extract project/module purpose with scope awareness."""
        lines = content.strip().split('\n')

        # Skip title and empty lines
        description_start = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#'):
                description_start = i
                break

        # Get first substantial paragraph
        purpose_lines = []
        for line in lines[description_start:]:
            line = line.strip()
            if not line:
                if purpose_lines:
                    break
                continue
            if line.startswith('#'):
                break
            purpose_lines.append(line)

            # Adjust length based on scope
            max_length = {
                "repository": 400,
                "module": 300,
                "package": 250,
                "component": 200
            }.get(scope_type, 300)

            if len(' '.join(purpose_lines)) > max_length:
                break

        purpose = ' '.join(purpose_lines).strip()
        return purpose if len(purpose) > 10 else None

    def _extract_features(self, content: str, scope_type: Optional[str] = None) -> List[str]:
        """Extract features with scope awareness."""
        features = []

        # Adjust feature detection based on scope
        if scope_type == "repository":
            feature_patterns = [
                r'(?:^|\n)(?:##?\s*)?(?:features?|highlights?|benefits?|capabilities?).*?(?=\n(?:#|$))',
                r'(?:^|\n)[\-\*\+]\s*(.+?)(?=\n(?:[\-\*\+]|\n|$))'
            ]
        elif scope_type in ["module", "package"]:
            feature_patterns = [
                r'(?:^|\n)(?:##?\s*)?(?:features?|functions?|methods?|api?).*?(?=\n(?:#|$))',
                r'(?:^|\n)[\-\*\+]\s*(.+?)(?=\n(?:[\-\*\+]|\n|$))'
            ]
        else:  # component
            feature_patterns = [
                r'(?:^|\n)(?:##?\s*)?(?:features?|capabilities?|what it does?).*?(?=\n(?:#|$))',
                r'(?:^|\n)[\-\*\+]\s*(.+?)(?=\n(?:[\-\*\+]|\n|$))'
            ]

        for pattern in feature_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]

                # Extract list items
                list_items = re.findall(r'[\-\*\+]\s*(.+)', match)
                for item in list_items:
                    item = item.strip()
                    if 10 <= len(item) <= 100:
                        features.append(item)

        return features[:10]