"""
Technology stack detection analyzer.

Identifies programming languages, frameworks, and technologies used in a repository
by analyzing file extensions, configuration files, and dependencies.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Set, Any
from datetime import datetime, UTC


@dataclass
class TechnologyDetection:
    """Results from technology detection analysis."""

    # Detected components
    programming_languages: List[str]  # Primary languages detected
    frameworks: List[str]  # Frameworks identified
    databases: List[str]  # Database technologies
    deployment_platforms: List[str]  # Cloud/deployment platforms
    build_tools: List[str]  # Build systems and tools
    testing_frameworks: List[str]  # Test runners and frameworks
    ci_cd_platforms: List[str]  # Continuous integration platforms
    documentation_tools: List[str]  # Documentation generators
    
    # Confidence scores
    language_confidence: float  # 0.0 - 1.0
    framework_confidence: float  # 0.0 - 1.0
    overall_confidence: float  # 0.0 - 1.0
    
    # Summary
    all_technologies: List[str]  # All detected technologies
    primary_language: Optional[str]  # Most likely primary language
    
    # Metadata
    analyzed_at: datetime


class TechnologyDetector:
    """Detector for technologies used in repositories."""

    # Mapping of file extensions to languages
    EXTENSION_TO_LANGUAGE = {
        # Statically typed languages
        'py': 'Python',
        'js': 'JavaScript',
        'ts': 'TypeScript',
        'jsx': 'JavaScript',
        'tsx': 'TypeScript',
        'java': 'Java',
        'cs': 'C#',
        'cpp': 'C++',
        'cc': 'C++',
        'cxx': 'C++',
        'c': 'C',
        'h': 'C',
        'hpp': 'C++',
        'go': 'Go',
        'rs': 'Rust',
        'rb': 'Ruby',
        'php': 'PHP',
        'swift': 'Swift',
        'kt': 'Kotlin',
        'scala': 'Scala',
        'clj': 'Clojure',
        'ex': 'Elixir',
        'erl': 'Erlang',
        'hs': 'Haskell',
        'lua': 'Lua',
        'pl': 'Perl',
        'r': 'R',
        'dart': 'Dart',
        'vb': 'Visual Basic',
        'fs': 'F#',
        'groovy': 'Groovy',
        'm': 'Objective-C',
        'mm': 'Objective-C++',
        
        # Web/Markup
        'html': 'HTML',
        'htm': 'HTML',
        'css': 'CSS',
        'scss': 'SCSS',
        'sass': 'Sass',
        'less': 'Less',
        'vue': 'Vue',
        
        # Shell
        'sh': 'Shell',
        'bash': 'Shell',
        'zsh': 'Shell',
        'ps1': 'PowerShell',
        'psm1': 'PowerShell',
        'cmd': 'Batch',
        'bat': 'Batch',
        
        # Data/Config
        'sql': 'SQL',
        'json': 'JSON',
        'xml': 'XML',
        'yaml': 'YAML',
        'yml': 'YAML',
        'toml': 'TOML',
        'ini': 'INI',
        'conf': 'Config',
    }

    # Mapping of project/config files to technologies
    PROJECT_FILE_PATTERNS = {
        # Python
        'requirements.txt': 'Python',
        'setup.py': 'Python',
        'setup.cfg': 'Python',
        'pyproject.toml': 'Python',
        'pipfile': 'Python',
        'poetry.lock': 'Python',
        'tox.ini': 'Python',
        'Pipfile.lock': 'Python',
        
        # JavaScript/Node
        'package.json': 'JavaScript',
        'package-lock.json': 'JavaScript',
        'yarn.lock': 'JavaScript',
        'pnpm-lock.yaml': 'JavaScript',
        'tsconfig.json': 'TypeScript',
        '.eslintrc.json': 'JavaScript',
        'jest.config.js': 'JavaScript',
        'webpack.config.js': 'JavaScript',
        'vite.config.ts': 'TypeScript',
        'next.config.js': 'JavaScript',
        
        # Java/JVM
        'pom.xml': 'Java',
        'build.gradle': 'Java',
        'build.gradle.kts': 'Kotlin',
        'settings.gradle': 'Java',
        'gradlew': 'Java',
        
        # .NET
        '.csproj': 'C#',
        '.vbproj': 'Visual Basic',
        '.fsproj': 'F#',
        'packages.config': 'C#',
        '.sln': 'C#',
        
        # Ruby
        'gemfile': 'Ruby',
        'gemfile.lock': 'Ruby',
        'Rakefile': 'Ruby',
        
        # Go
        'go.mod': 'Go',
        'go.sum': 'Go',
        
        # Rust
        'Cargo.toml': 'Rust',
        'cargo.lock': 'Rust',
        
        # PHP
        'composer.json': 'PHP',
        'composer.lock': 'PHP',
        
        # Other
        'Makefile': 'Make',
        'makefile': 'Make',
        'Dockerfile': 'Docker',
        'dockerfile': 'Docker',
        'docker-compose.yml': 'Docker',
        'docker-compose.yaml': 'Docker',
        'Vagrantfile': 'Vagrant',
        'Gemfile': 'Ruby',
    }

    # Framework patterns (file extensions or file names)
    FRAMEWORK_PATTERNS = {
        'React': r'(?:react|jsx|create-react-app|next\.js|gatsby)',
        'Vue': r'(?:vue|vuejs|nuxt)',
        'Angular': r'(?:angular|ng-)',
        'Django': r'(?:django|manage\.py)',
        'Flask': r'(?:flask|app\.py)',
        'FastAPI': r'(?:fastapi|main\.py)',
        'Express': r'(?:express|expressjs)',
        'Spring': r'(?:spring|springboot)',
        'Rails': r'(?:rails|ruby on rails|Rakefile)',
        'Laravel': r'(?:laravel|artisan)',
        'ASP.NET': r'(?:aspnet|asp\.net)',
        'Blazor': r'(?:blazor)',
    }

    # Database patterns
    DATABASE_PATTERNS = {
        'PostgreSQL': r'(?:postgresql|postgres|psql)',
        'MySQL': r'(?:mysql|mariadb)',
        'MongoDB': r'(?:mongodb|mongo|mongoose)',
        'Redis': r'(?:redis)',
        'SQLite': r'(?:sqlite)',
        'ElasticSearch': r'(?:elasticsearch|elastic)',
        'Cassandra': r'(?:cassandra)',
        'DynamoDB': r'(?:dynamodb)',
        'Oracle': r'(?:oracle)',
        'SQL Server': r'(?:sql server|sqlserver)',
    }

    # Deployment platforms
    PLATFORM_PATTERNS = {
        'Docker': r'(?:docker|dockerfile|docker-compose)',
        'Kubernetes': r'(?:kubernetes|k8s|kubectl|helm)',
        'AWS': r'(?:aws|amazon web services|ec2|s3|lambda)',
        'Azure': r'(?:azure|microsoft azure)',
        'GCP': r'(?:gcp|google cloud)',
        'Heroku': r'(?:heroku)',
        'Vercel': r'(?:vercel|zeit)',
        'Netlify': r'(?:netlify)',
        'DigitalOcean': r'(?:digitalocean)',
        'Cloudflare': r'(?:cloudflare)',
    }

    # Build tools
    BUILD_TOOL_PATTERNS = {
        'Maven': r'(?:maven|mvn)',
        'Gradle': r'(?:gradle|gradlew)',
        'Make': r'(?:make|Makefile)',
        'npm': r'(?:npm)',
        'Yarn': r'(?:yarn)',
        'pnpm': r'(?:pnpm)',
        'Cargo': r'(?:cargo)',
        'Cmake': r'(?:cmake)',
        'Ant': r'(?:ant)',
    }

    # Testing frameworks
    TEST_FRAMEWORK_PATTERNS = {
        'pytest': r'(?:pytest)',
        'unittest': r'(?:unittest)',
        'Jest': r'(?:jest)',
        'Mocha': r'(?:mocha)',
        'Jasmine': r'(?:jasmine)',
        'RSpec': r'(?:rspec)',
        'JUnit': r'(?:junit)',
        'TestNG': r'(?:testng)',
        'XUnit': r'(?:xunit)',
    }

    # CI/CD platforms
    CICD_PATTERNS = {
        'GitHub Actions': r'(?:github actions|\.github/workflows)',
        'GitLab CI': r'(?:gitlab ci|\.gitlab-ci\.yml)',
        'Jenkins': r'(?:jenkins|Jenkinsfile)',
        'CircleCI': r'(?:circleci|\.circleci)',
        'Travis CI': r'(?:travis|\.travis\.yml)',
        'Azure Pipelines': r'(?:azure pipelines|azure-pipelines\.yml)',
        'AWS CodePipeline': r'(?:codepipeline)',
    }

    def detect(
        self,
        file_names: List[str],
        file_tree: Optional[List[Dict[str, Any]]] = None,
        language_data: Optional[List[Dict[str, Any]]] = None,
    ) -> TechnologyDetection:
        """
        Detect technologies used in a repository.

        Args:
            file_names: List of file names/paths in the repository.
            file_tree: Optional detailed file tree with extensions.
            language_data: Optional language statistics from API (e.g., GitHub).

        Returns:
            TechnologyDetection with identified technologies.
        """
        file_names_lower = [f.lower() for f in file_names]
        
        # Detect languages from files and language_data
        languages = self._detect_languages(file_names_lower, language_data)
        
        # Detect frameworks
        frameworks = self._detect_frameworks(file_names_lower)
        
        # Detect databases
        databases = self._detect_pattern_matches(file_names_lower, self.DATABASE_PATTERNS)
        
        # Detect deployment platforms
        platforms = self._detect_pattern_matches(file_names_lower, self.PLATFORM_PATTERNS)
        
        # Detect build tools
        build_tools = self._detect_pattern_matches(file_names_lower, self.BUILD_TOOL_PATTERNS)
        
        # Detect testing frameworks
        test_frameworks = self._detect_pattern_matches(file_names_lower, self.TEST_FRAMEWORK_PATTERNS)
        
        # Detect CI/CD platforms
        cicd = self._detect_pattern_matches(file_names_lower, self.CICD_PATTERNS)
        
        # Collect all technologies
        all_tech = languages + frameworks + databases + platforms + build_tools + test_frameworks + cicd
        all_tech = list(set(all_tech))  # Remove duplicates
        all_tech.sort()
        
        # Determine primary language
        primary_lang = languages[0] if languages else None
        
        # Calculate confidence scores
        lang_conf = min(len(languages) * 0.25, 1.0)  # More languages = higher confidence
        frame_conf = min(len(frameworks) * 0.3, 1.0)
        overall_conf = (lang_conf + frame_conf) / 2 if (languages or frameworks) else 0.0
        
        return TechnologyDetection(
            programming_languages=languages,
            frameworks=frameworks,
            databases=databases,
            deployment_platforms=platforms,
            build_tools=build_tools,
            testing_frameworks=test_frameworks,
            ci_cd_platforms=cicd,
            documentation_tools=[],  # Not detected in this version
            language_confidence=lang_conf,
            framework_confidence=frame_conf,
            overall_confidence=overall_conf,
            all_technologies=all_tech,
            primary_language=primary_lang,
            analyzed_at=datetime.now(UTC)
        )

    def _detect_languages(
        self,
        file_names: List[str],
        language_data: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """Detect programming languages."""
        languages: Set[str] = set()
        
        # From GitHub language API data (most reliable)
        if language_data:
            for lang_info in language_data:
                if isinstance(lang_info, dict) and 'language' in lang_info:
                    languages.add(lang_info['language'])
        
        # From file extensions
        for file_name in file_names:
            if '.' in file_name:
                ext = file_name.rsplit('.', 1)[-1].lower()
                if ext in self.EXTENSION_TO_LANGUAGE:
                    languages.add(self.EXTENSION_TO_LANGUAGE[ext])
        
        # From project files
        for file_name in file_names:
            base_name = file_name.split('/')[-1].lower()
            if base_name in self.PROJECT_FILE_PATTERNS:
                languages.add(self.PROJECT_FILE_PATTERNS[base_name])
        
        return sorted(list(languages))

    def _detect_frameworks(self, file_names: List[str]) -> List[str]:
        """Detect frameworks."""
        return self._detect_pattern_matches(file_names, self.FRAMEWORK_PATTERNS)

    def _detect_pattern_matches(
        self,
        file_names: List[str],
        patterns: Dict[str, str]
    ) -> List[str]:
        """Detect technologies matching regex patterns."""
        import re
        
        detected: Set[str] = set()
        combined_text = ' '.join(file_names)
        
        for tech_name, pattern in patterns.items():
            if re.search(pattern, combined_text, re.IGNORECASE):
                detected.add(tech_name)
        
        return sorted(list(detected))
