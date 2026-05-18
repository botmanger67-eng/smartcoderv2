"""
GitHub Manager module for SmartBot.
Handles repository operations using PyGithub.
Fixed: Removed unused GITHUB_USERNAME, better error handling, more features.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from github import Github, GithubException
from github.Repository import Repository

logger = logging.getLogger(__name__)


class GitHubManager:
    """Manages GitHub repository operations."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub manager.
        
        Args:
            token: GitHub personal access token. If None, reads from config.
        """
        from config import GITHUB_TOKEN
        
        self.token = token or GITHUB_TOKEN
        self.github: Optional[Github] = None
        self.user = None
        
        if self.token:
            try:
                self.github = Github(self.token)
                self.user = self.github.get_user()
                logger.info(f"GitHub manager initialized for: {self.user.login}")
            except GithubException as e:
                logger.error(f"GitHub auth failed: {e}")
                self.github = None
        else:
            logger.warning("No GitHub token provided. GitHub features disabled.")

    def is_available(self) -> bool:
        """Check if GitHub integration is available."""
        return self.github is not None

    async def create_repository(
        self, 
        repo_name: str, 
        description: str = "", 
        private: bool = False,
        auto_init: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new GitHub repository.

        Args:
            repo_name: Repository name (validated)
            description: Short description
            private: Make it private?
            auto_init: Initialize with README?

        Returns:
            Repo info dict or None on failure
        """
        if not self.is_available():
            logger.error("GitHub not available")
            return None

        try:
            # Validate repo name
            import re
            if not re.match(r'^[a-zA-Z0-9._-]+$', repo_name):
                logger.error(f"Invalid repo name: {repo_name}")
                return None

            # Create repo
            repo = await asyncio.to_thread(
                self.user.create_repo,
                name=repo_name,
                description=description[:200] if description else "",
                private=private,
                auto_init=auto_init
            )

            logger.info(f"Created repo: {repo.full_name}")

            # Save to database
            try:
                from database import save_repo
                save_repo(
                    repo_id=repo.id,
                    name=repo.name,
                    full_name=repo.full_name,
                    html_url=repo.html_url,
                    clone_url=repo.clone_url,
                    private=repo.private
                )
            except Exception as e:
                logger.warning(f"Failed to save repo to DB: {e}")

            return {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "private": repo.private
            }

        except GithubException as e:
            logger.error(f"GitHub API error: {e}")
            if e.status == 422:
                logger.error("Repo already exists or name taken")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    async def list_repos(self, visibility: str = "all") -> List[Dict[str, Any]]:
        """
        List user's repositories.

        Args:
            visibility: 'all', 'public', or 'private'

        Returns:
            List of repo dictionaries
        """
        if not self.is_available():
            return []

        try:
            repos = await asyncio.to_thread(
                self.user.get_repos,
                type=visibility
            )

            repo_list = []
            for repo in repos:
                repo_list.append({
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "html_url": repo.html_url,
                    "private": repo.private,
                    "description": repo.description or "",
                    "language": repo.language or "",
                    "stars": repo.stargazers_count,
                    "updated": repo.updated_at.isoformat() if repo.updated_at else ""
                })
            
            return repo_list

        except GithubException as e:
            logger.error(f"Error listing repos: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []

    async def get_repo(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific repo by name."""
        if not self.is_available():
            return None

        try:
            full_name = f"{self.user.login}/{repo_name}"
            repo = await asyncio.to_thread(self.github.get_repo, full_name)
            
            return {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "private": repo.private,
                "description": repo.description or "",
                "language": repo.language or "",
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count
            }

        except GithubException as e:
            if e.status == 404:
                logger.warning(f"Repo not found: {repo_name}")
            else:
                logger.error(f"Error getting repo: {e}")
            return None

    async def delete_repo(self, repo_name: str) -> bool:
        """Delete a repository."""
        if not self.is_available():
            return False

        try:
            full_name = f"{self.user.login}/{repo_name}"
            repo = await asyncio.to_thread(self.github.get_repo, full_name)
            await asyncio.to_thread(repo.delete)
            
            logger.info(f"Deleted repo: {repo_name}")
            
            try:
                from database import delete_repo_by_name
                delete_repo_by_name(repo_name)
            except:
                pass
                
            return True

        except GithubException as e:
            logger.error(f"Error deleting repo: {e}")
            return False

    async def push_files(
        self, 
        repo_name: str, 
        files: Dict[str, str], 
        commit_message: str = "Initial commit"
    ) -> bool:
        """
        Push multiple files to a repository.

        Args:
            repo_name: Repository name
            files: Dict of {filepath: content}
            commit_message: Commit message

        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            full_name = f"{self.user.login}/{repo_name}"
            repo = await asyncio.to_thread(self.github.get_repo, full_name)
            
            for file_path, content in files.items():
                try:
                    await asyncio.to_thread(
                        repo.create_file,
                        path=file_path,
                        message=f"Create {file_path}",
                        content=content,
                        branch="main"
                    )
                    logger.info(f"Created: {file_path}")
                    await asyncio.sleep(0.3)
                except GithubException as e:
                    if e.status == 422:
                        logger.warning(f"File already exists: {file_path}")
                    else:
                        logger.error(f"Failed to push {file_path}: {e}")

            return True

        except Exception as e:
            logger.error(f"Error pushing files: {e}")
            return False

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get authenticated user's info."""
        if not self.is_available():
            return None

        try:
            return {
                "login": self.user.login,
                "name": self.user.name or self.user.login,
                "avatar_url": self.user.avatar_url,
                "html_url": self.user.html_url,
                "public_repos": self.user.public_repos,
                "bio": self.user.bio or ""
            }
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
