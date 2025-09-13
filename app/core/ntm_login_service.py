"""
NTM Login Service for automating login processes for NTM-owned news sites.
This service handles automated login for different NTM news sites using
the shared NTM login system with dynamic URLs.
"""

import logging
from typing import Dict

from playwright.async_api import Page
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class NTMLoginConfig(BaseModel):
    """Configuration for NTM site authentication."""

    site_name: str
    domain: str
    username_env_key: str
    password_env_key: str
    username_selector: str = "#Input_Username"
    password_selector: str = "#passwordField"
    submit_selector: str = "button[type='submit']"
    success_url_pattern: str | None = None


class NTMLoginService:
    """Service for automating login processes for NTM news sites."""

    def __init__(self) -> None:
        """Initialize the NTM login service."""
        self.login_configs: Dict[str, NTMLoginConfig] = {}
        self._register_ntm_sites()

    def _register_ntm_sites(self) -> None:
        """Register NTM site login configurations."""
        try:
            # Define NTM site configurations
            ntm_sites = [
                NTMLoginConfig(
                    site_name="nt",
                    domain="www.nt.se",
                    username_env_key="NT_USERNAME",
                    password_env_key="NT_PASSWORD",
                    success_url_pattern="nt.se",
                ),
                NTMLoginConfig(
                    site_name="nsd",
                    domain="www.nsd.se",
                    username_env_key="NSD_USERNAME",
                    password_env_key="NSD_PASSWORD",
                    success_url_pattern="nsd.se",
                ),
                NTMLoginConfig(
                    site_name="kuriren",
                    domain="www.kuriren.se",
                    username_env_key="NSD_USERNAME",
                    password_env_key="NSD_PASSWORD",
                    success_url_pattern="kuriren.se",
                ),
                NTMLoginConfig(
                    site_name="norran",
                    domain="www.norran.se",
                    username_env_key="NORRAN_USERNAME",
                    password_env_key="NORRAN_PASSWORD",
                    success_url_pattern="norran.se",
                ),
                NTMLoginConfig(
                    site_name="corren",
                    domain="www.corren.se",
                    username_env_key="CORREN_USERNAME",
                    password_env_key="CORREN_PASSWORD",
                    success_url_pattern="corren.se",
                ),
            ]

            # Register all site configurations
            for site_config in ntm_sites:
                # Get credentials dynamically from settings if they exist
                username = getattr(settings, site_config.username_env_key, None)
                password = getattr(settings, site_config.password_env_key, None)

                # If credentials are empty, log a warning
                if not username or not password:
                    logger.warning(
                        f"Missing credentials for {site_config.site_name}, login may fail"
                    )
                    logger.warning(
                        f"Ensure {site_config.username_env_key} and {site_config.password_env_key} are set in .env"
                    )

                # Register the site login config
                self.login_configs[site_config.site_name] = site_config
                logger.info(f"Registered NTM login configuration for {site_config.site_name}")

        except Exception as e:
            logger.error(f"Error loading NTM site configurations: {str(e)}")
            logger.warning("Automatic login configurations for NTM sites might not be available")

    def has_login_config(self, site_name: str) -> bool:
        """
        Check if login configuration exists for a site.

        Args:
            site_name: Name of the site to check

        Returns:
            True if login configuration exists, False otherwise
        """
        return site_name in self.login_configs

    async def auto_login(self, page: Page, site_name: str) -> bool:
        """
        Attempt automated login for an NTM site.

        Args:
            page: Playwright page object
            site_name: Name of the site to login to

        Returns:
            True if login was successful, False otherwise
        """
        if not self.has_login_config(site_name):
            logger.warning(f"No NTM login configuration found for {site_name}")
            return False

        config = self.login_configs[site_name]

        # Get credentials dynamically
        username = getattr(settings, config.username_env_key, "")
        password = getattr(settings, config.password_env_key, "")

        try:
            # Instead of directly navigating to the login URL, we use the site-specific login entry point
            # This will redirect to the NTM login page
            login_entry_url = f"https://{config.domain}/logga-in"
            logger.info(f"Navigating to login entry point for {site_name}: {login_entry_url}")
            await page.goto(login_entry_url)  # Fixed: using login_entry_url instead of login_url

            # Check for missing credentials
            if not username or not password:
                logger.warning(f"Missing credentials for {site_name}")
                logger.warning(
                    f"Please set {config.username_env_key} and {config.password_env_key} in your .env file"
                )
                return False

            # Wait for the redirect to complete and ensure we're on the NTM login page
            logger.info("Waiting for navigation to complete after redirect...")
            await page.wait_for_load_state("networkidle")

            # Step 1: Fill email field and click 'Fortsätt'
            logger.info(f"Filling email field: {config.username_selector}")
            await page.fill(config.username_selector, username)

            # Click the 'Fortsätt' (Continue) button
            continue_button = "button:has-text('Fortsätt')"
            logger.info("Clicking 'Fortsätt' button to continue to password step")
            await page.click(continue_button)

            # Wait for the second step to load
            logger.info("Waiting for password form to load...")
            await page.wait_for_load_state("networkidle")

            # Step 2: Fill password field and click 'Logga in'
            logger.info(f"Filling password field: {config.password_selector}")
            await page.fill(config.password_selector, password)

            # Click the 'Logga in' button
            login_button = "button:has-text('Logga in')"
            logger.info("Clicking 'Logga in' button to complete login")
            await page.click(login_button)

            # Wait for the login process to complete and page to load fully
            logger.info("Waiting for login to complete and page to fully load...")
            # Wait for the page to be fully loaded with all resources
            await page.wait_for_load_state("networkidle")

            # Wait for navigation or success indicator
            if config.success_url_pattern:
                logger.info(f"Waiting for URL pattern: {config.success_url_pattern}")

                # Wait for redirects to complete (NTM login involves multiple redirects)
                logger.info("Waiting for all redirects to complete...")
                try:
                    # Wait for the page to become stable
                    await page.wait_for_timeout(2000)
                    await page.wait_for_load_state("networkidle")
                except Exception as e:
                    # Something went wrong with the waiting
                    logger.warning(f"Waiting issue: {str(e)}")

                # Check if we've reached the destination site
                current_url = page.url
                logger.info(f"URL after login process: {current_url}")

                if config.success_url_pattern in current_url:
                    logger.info(f"URL pattern match found in {current_url}")
                    logger.info(f"Successfully logged in to {site_name}")

                    # Make sure the authentication cookies and storage are properly set
                    logger.info("Ensuring authentication is complete...")
                    await page.wait_for_load_state("load")

                    return True
                else:
                    logger.warning(
                        f"Expected URL pattern '{config.success_url_pattern}' not found in '{current_url}'"
                    )
                    return False

            # If we don't have a success pattern, assume success
            logger.info(f"Successfully logged in to {site_name}")
            return True

        except Exception as e:
            logger.error(f"Automated NTM login failed for {site_name}: {str(e)}")
            return False
