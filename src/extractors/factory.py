"""
Factory for creating platform-specific extractors.
"""

from src.extractors.base import Platform, RepositoryExtractor


def get_extractor(platform: Platform | str) -> RepositoryExtractor:
    """
    Get an extractor instance for the specified platform.

    Args:
        platform: Platform enum or string name.

    Returns:
        Configured extractor instance.

    Raises:
        ValueError: If platform is not supported.
    """
    if isinstance(platform, str):
        platform = Platform(platform)

    if platform == Platform.AZURE_DEVOPS:
        from src.extractors.azure_devops import AzureDevOpsExtractor
        return AzureDevOpsExtractor()

    elif platform == Platform.GITHUB:
        from src.extractors.github import GitHubExtractor
        return GitHubExtractor()

    else:
        raise ValueError(f"Unsupported platform: {platform}")
