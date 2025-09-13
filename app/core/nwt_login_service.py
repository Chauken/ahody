"""
NWT Login Service for automating login processes.
This service handles automated login for NWT websites with
fallback to manual login when automated login fails.
"""

import logging
from typing import Any, Dict

from playwright.async_api import Page
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class LoginFormField(BaseModel):
    """Model representing a login form field."""

    selector: str
    value: str
    field_type: str = "text"  # text, email, password, etc.


class SiteAuthConfig(BaseModel):
    """Configuration for a site's authentication."""

    site_name: str
    login_url: str
    username_env_key: str
    password_env_key: str
    username_selector: str = "#email"
    password_selector: str = "#password"
    submit_selector: str = "button[type='submit']"
    success_url_pattern: str | None = None
    success_element_selector: str | None = None
    field_types: Dict[str, str] = {"username": "email", "password": "password"}


class LoginFormConfig(BaseModel):
    """Model for login form configuration."""

    url: str
    fields: list[LoginFormField]
    submit_selector: str
    success_url_pattern: str | None = None
    success_element_selector: str | None = None


class NWTLoginService:
    """Service for automating login processes for NWT sites."""

    def __init__(self) -> None:
        """Initialize the NWT login service."""
        self.login_configs: Dict[str, LoginFormConfig] = {}
        self._register_known_sites()

    def _register_known_sites(self) -> None:
        """Register known NWT site login configurations using a dynamic approach."""
        try:
            # Define NWT site configurations
            site_configs = [
                SiteAuthConfig(
                    site_name="nwt",
                    login_url="https://www.nwt.se/login/?returnUrl=%252F",
                    username_env_key="NWT_USERNAME",
                    password_env_key="NWT_PASSWORD",
                    username_selector="#email",
                    password_selector="#password",
                    submit_selector="button[type='submit']",
                    success_url_pattern="nwt.se",
                )
            ]

            # Register all site configurations
            for site_config in site_configs:
                # Get credentials dynamically from settings
                username = getattr(settings, site_config.username_env_key, "")
                password = getattr(settings, site_config.password_env_key, "")

                # If credentials are empty, log a warning
                if not username or not password:
                    logger.warning(
                        f"Missing credentials for {site_config.site_name}, login may fail"
                    )

                # Create login form configuration
                login_config = LoginFormConfig(
                    url=site_config.login_url,
                    fields=[
                        LoginFormField(
                            selector=site_config.username_selector,
                            value=username,
                            field_type=site_config.field_types.get("username", "email"),
                        ),
                        LoginFormField(
                            selector=site_config.password_selector,
                            value=password,
                            field_type=site_config.field_types.get("password", "password"),
                        ),
                    ],
                    submit_selector=site_config.submit_selector,
                    success_url_pattern=site_config.success_url_pattern,
                    success_element_selector=site_config.success_element_selector,
                )

                # Register the site login
                self.register_site_login(site_config.site_name, login_config)

        except Exception as e:
            logger.error(f"Error loading site configurations: {str(e)}")
            logger.warning("Automatic login configurations might not be available")

    def register_site_login(self, site_name: str, login_config: LoginFormConfig) -> None:
        """
        Register a login configuration for a site.

        Args:
            site_name: Name of the site
            login_config: Login form configuration for the site
        """
        self.login_configs[site_name] = login_config
        logger.info(f"Registered login configuration for {site_name}")

    def register_site_auth_config(self, config: SiteAuthConfig) -> None:
        """Register a site authentication configuration.

        Args:
            config: Site authentication configuration
        """
        username = getattr(settings, config.username_env_key, "")
        password = getattr(settings, config.password_env_key, "")

        # Create login form configuration
        login_config = LoginFormConfig(
            url=config.login_url,
            fields=[
                LoginFormField(
                    selector=config.username_selector,
                    value=username,
                    field_type=config.field_types.get("username", "email"),
                ),
                LoginFormField(
                    selector=config.password_selector,
                    value=password,
                    field_type=config.field_types.get("password", "password"),
                ),
            ],
            submit_selector=config.submit_selector,
            success_url_pattern=config.success_url_pattern,
            success_element_selector=config.success_element_selector,
        )

        # Register the site login
        self.register_site_login(config.site_name, login_config)

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
        Attempt automated login for a site.

        Args:
            page: Playwright page object
            site_name: Name of the site to login to

        Returns:
            True if login was successful, False otherwise
        """
        if not self.has_login_config(site_name):
            logger.warning(f"No login configuration found for {site_name}")
            return False

        config = self.login_configs[site_name]

        try:
            # Navigate to login page
            logger.info(f"Navigating to login page: {config.url}")
            await page.goto(config.url)

            # Check and prompt for missing credentials if needed
            missing_fields = []
            for field in config.fields:
                if not field.value:
                    missing_fields.append(field)

            if missing_fields:
                # Log detailed information about missing credentials
                for field in missing_fields:
                    field_name = field.selector.replace("#", "")
                    if field.field_type == "email":
                        logger.warning(
                            f"Missing email credential. Please check NWT_USERNAME in your .env file"
                        )
                    elif field.field_type == "password":
                        logger.warning(
                            f"Missing password credential. Please check NWT_PASSWORD in your .env file"
                        )
                    else:
                        logger.warning(f"Missing value for {field_name} field")

                logger.warning(
                    "For automated login to work, please ensure all required credentials are in your .env file"
                )
                return False

            # Fill login form fields
            for field in config.fields:
                logger.info(f"Filling {field.field_type} field: {field.selector}")
                await page.fill(field.selector, field.value)

            # Submit form
            logger.info("Submitting login form")
            await page.click(config.submit_selector)

            # Wait for navigation or success indicator
            if config.success_url_pattern:
                logger.info(f"Waiting for URL pattern: {config.success_url_pattern}")
                # Check current URL instead of waiting for navigation
                current_url = page.url
                logger.info(f"Current URL after login: {current_url}")

                if config.success_url_pattern in current_url:
                    logger.info(f"URL pattern match found in {current_url}")
                else:
                    # Wait a bit for any redirects to complete
                    try:
                        await page.wait_for_timeout(3000)  # Wait 3 seconds for any redirects
                        current_url = page.url
                        logger.info(f"URL after waiting: {current_url}")

                        if config.success_url_pattern not in current_url:
                            logger.warning(
                                f"Expected URL pattern '{config.success_url_pattern}' not found in '{current_url}'"
                            )
                            return False
                    except Exception as e:
                        logger.error(f"Error while waiting for redirect: {str(e)}")
                        return False

            # Only check for success element if configured and needed
            if config.success_element_selector:
                logger.info(f"Checking for success element: {config.success_element_selector}")
                try:
                    # Use shorter timeout and handle absence gracefully
                    element = await page.wait_for_selector(
                        config.success_element_selector, timeout=5000, state="visible"
                    )
                    if element:
                        logger.info(f"Success element found: {config.success_element_selector}")
                except Exception as e:
                    # Just log this but don't fail - URL check is our primary success indicator
                    logger.info(f"Element check skipped: {str(e)}")

            logger.info(f"Successfully logged in to {site_name}")
            return True

        except Exception as e:
            logger.error(f"Automated login failed for {site_name}: {str(e)}")
            return False

    async def extract_session_storage(self, page: Page) -> Dict[str, Any]:
        """
        Extract session storage from page.

        Args:
            page: Playwright page

        Returns:
            Dictionary of session storage items
        """
        try:
            return await page.evaluate("() => Object.assign({}, sessionStorage)")
        except Exception as e:
            logger.error(f"Failed to extract session storage: {str(e)}")
            return {}

    async def inject_session_storage(self, page: Page, storage_data: Dict[str, Any]) -> bool:
        """
        Inject session storage data into page.

        Args:
            page: Playwright page
            storage_data: Session storage data to inject

        Returns:
            True if injection was successful, False otherwise
        """
        try:
            await page.evaluate(
                "(storageData) => { Object.entries(storageData).forEach(([key, value]) => sessionStorage.setItem(key, value)); }",
                storage_data,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to inject session storage: {str(e)}")
            return False
