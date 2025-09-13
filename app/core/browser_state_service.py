"""
Storage State Service for managing browser authentication states.
This service handles saving, loading, and checking browser authentication states
for Playwright-based web scraping.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)


class BrowserStateService:
    """Service for handling browser authentication states."""

    def __init__(self, base_directory: str | Path | None = None):
        """
        Args:
            base_directory: Directory to store authentication states. Defaults to './browser_data'
        """

        self.base_directory = Path(base_directory) if base_directory else Path("./browser_data")
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the storage directory exists."""
        self.base_directory.mkdir(exist_ok=True, parents=True)

    def get_state_path(self, site_name: str = "default") -> Path:
        """
        Get the path for a specific site's authentication state.

        Args:
            site_name: Name of the site to get the state for

        Returns:
            Path object for the storage state file
        """
        return self.base_directory / f"{site_name}_auth_state.json"

    async def save_storage_state(self, context: BrowserContext, site_name: str = "default") -> Path:
        """
        Save the authentication state from a browser context.

        Args:
            context: The Playwright browser context to save state from
            site_name: Name of the site for the state

        Returns:
            Path where the state was saved
        """
        state_path = self.get_state_path(site_name)
        await context.storage_state(path=str(state_path))
        logger.info(f"Authentication state for {site_name} saved to {state_path}")
        return state_path

    def load_storage_state(self, site_name: str = "default") -> str | None:
        """
        Get the path to a saved authentication state if it exists.

        Args:
            site_name: Name of the site to load state for

        Returns:
            String path to the storage state file or None if it doesn't exist
        """
        state_path = self.get_state_path(site_name)
        if state_path.exists():
            logger.info(f"Found authentication state for {site_name} at {state_path}")
            return str(state_path)
        logger.warning(f"No authentication state found for {site_name}")
        return None

    def state_exists(self, site_name: str = "default") -> bool:
        """
        Check if an authentication state exists for a site.

        Args:
            site_name: Name of the site to check

        Returns:
            True if state exists, False otherwise
        """
        state_path = self.get_state_path(site_name)
        return state_path.exists()

    def get_storage_content(self, site_name: str = "default") -> dict | None:
        """
        Get the content of a storage state file.

        Args:
            site_name: Name of the site to get state for

        Returns:
            dict containing the storage state or None if it doesn't exist
        """
        state_path = self.get_state_path(site_name)
        if not state_path.exists():
            return None

        try:
            with open(state_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading storage state for {site_name}: {str(e)}")
            return None

    def list_available_states(self) -> list[dict]:
        """
        List all available authentication states.

        Returns:
            List of dicts with information about each available state
        """
        self._ensure_directory()
        state_files = list(self.base_directory.glob("*_auth_state.json"))
        result = []

        for state_file in state_files:
            site_name = state_file.stem.replace("_auth_state", "")
            mod_time = datetime.fromtimestamp(state_file.stat().st_mtime)
            size = state_file.stat().st_size

            result.append(
                {
                    "site_name": site_name,
                    "path": str(state_file),
                    "modified": mod_time.isoformat(),
                    "size_bytes": size,
                }
            )

        return result

    def delete_state(self, site_name: str) -> bool:
        """
        Delete an authentication state file.
        """
        state_path = self.get_state_path(site_name)
        if not state_path.exists():
            logger.warning(f"No state found to delete for {site_name}")
            return False

        try:
            state_path.unlink()
            logger.info(f"Deleted authentication state for {site_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting state for {site_name}: {str(e)}")
            return False

    def backup_state(self, site_name: str = "default") -> Path | None:
        """
        Create a backup of an authentication state.
        """
        state_path = self.get_state_path(site_name)
        if not state_path.exists():
            logger.warning(f"No state found to backup for {site_name}")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.base_directory / f"{site_name}_auth_state_backup_{timestamp}.json"

        try:
            with open(state_path, "r") as src, open(backup_path, "w") as dest:
                content = src.read()
                dest.write(content)
            logger.info(f"Backed up {site_name} state to {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Error backing up state for {site_name}: {str(e)}")
            return None
