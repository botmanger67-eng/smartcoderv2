import logging
from typing import Optional, List, Dict, Any
from github import Github, GithubException
from github.Repository import Repository
from config import GITHUB_TOKEN, GITHUB_USERNAME
from database import save_repo, get_repo_by_name
from utils import validate_repo_name, sanitize_repo_description

logger = logging.getLogger(__name__)

def create_github_repo(
    repo_name: str,
    description: str = "",
    private: bool = False,
    auto_init: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Create a new GitHub repository for the authenticated user.

    Args:
        repo_name: Name of the repository (will be validated).
        description: Short description of the repository.
        private: Whether the repository should be private.
        auto_init: Initialize with a README.md.

    Returns:
        Dictionary with repo info (name, full_name, html_url, clone_url, id)
        or None if creation fails.

    Raises:
        ValueError: If repo_name is invalid or missing.
    """
    try:
        if not GITHUB_TOKEN:
            logger.error("GitHub token is not configured")
            return None

        validated_name = validate_repo_name(repo_name)
        if validated_name is None:
            logger.error("Invalid repository name: %s", repo_name)
            return None

        # Check if repo already exists locally (optional)
        existing = get_repo_by_name(validated_name)
        if existing:
            logger.warning("Repository %s already exists in local database", validated_name)

        gh = Github(GITHUB_TOKEN)
        user = gh.get_user()
        try:
            repo = user.create_repo(
                name=validated_name,
                description=sanitize_repo_description(description),
                private=private,
                auto_init=auto_init
            )
        except GithubException as e:
            logger.error("GitHub API error creating repo %s: %s", validated_name, e.data)
            return None

        # Save to local database
        save_repo(
            repo_id=repo.id,
            name=repo.name,
            full_name=repo.full_name,
            html_url=repo.html_url,
            clone_url=repo.clone_url,
            private=repo.private
        )

        return {
            "id": repo.id,
            "name": repo.name,
            "full_name": repo.full_name,
            "html_url": repo.html_url,
            "clone_url": repo.clone_url,
            "private": repo.private
        }

    except Exception as e:
        logger.exception("Unexpected error creating GitHub repo '%s': %s", repo_name, e)
        return None

def list_user_repos(visibility: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """
    List all repositories for the authenticated user.

    Args:
        visibility: Filter by visibility ('all', 'public', 'private', or None for all).

    Returns:
        List of repo dictionaries or None on failure.
    """
    try:
        if not GITHUB_TOKEN:
            logger.error("GitHub token is not configured")
            return None

        gh = Github(GITHUB_TOKEN)
        user = gh.get_user()
        repos = user.get_repos(type=visibility or "all")

        repo_list = []
        for repo in repos:
            repo_list.append({
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "html_url": repo.html_url,
                "private": repo.private,
                "description": repo.description,
                "fork": repo.fork
            })
        return repo_list

    except GithubException as e:
        logger.error("GitHub API error listing repos: %s", e.data)
        return None
    except Exception as e:
        logger.exception("Unexpected error listing GitHub repos: %s", e)
        return None

def delete_github_repo(repo_name: str) -> bool:
    """
    Delete a GitHub repository by its name.

    Args:
        repo_name: Name of the repository to delete.

    Returns:
        True if successful, False otherwise.
    """
    try:
        if not GITHUB_TOKEN:
            logger.error("GitHub token is not configured")
            return False

        validated_name = validate_repo_name(repo_name)
        if validated_name is None:
            logger.error("Invalid repository name: %s", repo_name)
            return False

        gh = Github(GITHUB_TOKEN)
        user = gh.get_user()
        try:
            repo = user.get_repo(validated_name)
            repo.delete()
            logger.info("Deleted repository %s", validated_name)
            # Remove from local database
            from database import delete_repo_by_name
            delete_repo_by_name(validated_name)
            return True
        except GithubException as e:
            logger.error("GitHub API error deleting repo %s: %s", validated_name, e.data)
            return False

    except Exception as e:
        logger.exception("Unexpected error deleting GitHub repo '%s': %s", repo_name, e)
        return False

def get_github_user_info() -> Optional[Dict[str, Any]]:
    """
    Retrieve authenticated user's GitHub profile information.

    Returns:
        Dictionary with login, name, email, avatar_url, public_repos, etc.
    """
    try:
        if not GITHUB_TOKEN:
            logger.error("GitHub token is not configured")
            return None

        gh = Github(GITHUB_TOKEN)
        user = gh.get_user()
        return {
            "login": user.login,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "public_repos": user.public_repos,
            "private_repos": user.owned_private_repos,
            "total_private_repos": user.total_private_repos,
            "bio": user.bio,
            "blog": user.blog,
            "location": user.location,
            "html_url": user.html_url
        }
    except GithubException as e:
        logger.error("GitHub API error getting user info: %s", e.data)
        return None
    except Exception as e:
        logger.exception("Unexpected error getting GitHub user info: %s", e)
        return None