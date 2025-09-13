"""
Browser Service for managing Playwright browser instances with authentication.
Handles automated login, state management, and authenticated browsing.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse
from venv import logger

from fastapi import Depends
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from app.core.browser_state_service import BrowserStateService
from app.core.ntm_login_service import NTMLoginService
from app.core.nwt_login_service import NWTLoginService

logger = logging.getLogger(__name__)


class BrowserService:
    """Service for browsing websites with authentication support."""

    def __init__(
        self,
        state_service: BrowserStateService = Depends(BrowserStateService),
        nwt_login_service: NWTLoginService = Depends(NWTLoginService),
        ntm_login_service: NTMLoginService = Depends(NTMLoginService),
        headless: bool = True,
        timeout: int = 30000,
        screenshot_dir: str | Path | None = None,
    ):
        self.headless = headless
        self.timeout = timeout
        self.state_service = state_service
        self.nwt_login_service = nwt_login_service
        self.ntm_login_service = ntm_login_service

        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else Path("./browser_data")
        self.screenshot_dir.mkdir(exist_ok=True, parents=True)

    def extract_site_name(self, url: str) -> str:
        """
        Extract a site name from a URL.
        For example, 'https://www.nwt.se/article' would return 'nwt'.

        Args:
            url: The URL to extract a name from

        Returns:
            A site name for the URL
        """
        parsed = urlparse(url)
        hostname = parsed.netloc

        # Remove www. prefix if present
        if hostname.startswith("www."):
            hostname = hostname[4:]

        # Extract the domain name without TLD
        parts = hostname.split(".")
        if len(parts) >= 2:
            return parts[0]

        return hostname

    async def _request_login(self, url: str, site_name: str) -> bool:
        """
        Attempt to log in to a site using automated login.

        Args:
            url: The URL to navigate to for login
            site_name: Name to use for the saved state

        Returns:
            True if login was successful, False otherwise
        """
        logger.info(f"Authentication state for {site_name} not found. Attempting login.")

        # Determine which login service to use based on the site name
        ntm_sites = ["nt", "nsd", "kuriren", "norran", "corren"]
        use_ntm_service = site_name.lower() in ntm_sites

        # Determine if we should use the NWT service for non-NTM sites
        use_nwt_service = site_name.lower() == "nwt"

        # Check if we have a login configuration for this site in any service
        has_login_config = (
            use_ntm_service and self.ntm_login_service.has_login_config(site_name)
        ) or (use_nwt_service and self.nwt_login_service.has_login_config(site_name))

        if has_login_config:
            if use_ntm_service:
                login_service_name = "NTM login service"
            elif use_nwt_service:
                login_service_name = "NWT login service"
            else:
                login_service_name = "No appropriate login service found"
            logger.info(f"Attempting automated login for {site_name} using {login_service_name}...")

            try:
                # Start Playwright for automated login
                async with async_playwright() as playwright:
                    # Launch browser for automated login
                    browser = await playwright.chromium.launch(
                        headless=True  # Headless for automated login
                    )

                    # Create context with reasonable viewport
                    context = await browser.new_context(viewport={"width": 1280, "height": 800})

                    # Create page
                    page = await context.new_page()

                    # Attempt automated login using the appropriate service
                    if use_ntm_service:
                        login_success = await self.ntm_login_service.auto_login(page, site_name)
                    elif use_nwt_service:
                        login_success = await self.nwt_login_service.auto_login(page, site_name)
                    else:
                        login_success = False
                        logger.warning(f"No login service available for {site_name}")

                    if login_success:
                        # Save authentication state
                        state_path = await self.state_service.save_storage_state(context, site_name)
                        logger.info(f"Automated login successful. State saved to {state_path}")

                        # Close browser
                        await browser.close()
                        return True
                    else:
                        logger.error("Automated login failed.")
                        await browser.close()
                        return False

            except Exception as e:
                logger.error(f"Automated login error: {str(e)}")
                return False
        else:
            logger.error(
                f"No automated login configuration for {site_name} in any login service. Login cannot be performed."
            )
            return False

    async def _browse_without_auth(self, url: str) -> Tuple[Playwright, Browser, BrowserContext, Page]:
        """
        Browse a URL without authentication.

        Args:
            url: The URL to browse

        Returns:
            Tuple of (playwright, browser, context, page) if successful, (None, None, None, None) otherwise
        """
        try:
            # Start Playwright
            logger.info(f"Starting browser session for {url} without authentication")
            playwright = await async_playwright().start()

            # Launch browser
            browser = await playwright.chromium.launch(headless=self.headless)

            # Create context with reasonable viewport
            context = await browser.new_context(viewport={"width": 1280, "height": 800})

            # Create page and navigate to site
            page = await context.new_page()
            logger.info(f"Navigating to {url}")

            # Navigate to the URL
            await page.goto(url, timeout=self.timeout)
            logger.info("Successfully loaded page without authentication state")

            # Take screenshot as verification
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.screenshot_dir / f"no_auth_screenshot_{timestamp}.png"
            await page.screenshot(path=str(screenshot_path))
            logger.info(f"Saved screenshot to {screenshot_path}")

            return playwright, browser, context, page

        except Exception as e:
            raise Exception(f"Error browsing {url}: {str(e)}")

    async def browse_url(
        self, url: str, force_login: bool = False
    ) -> Tuple[Playwright, Browser, BrowserContext, Page]:
        """
        Browse a URL with authentication if required.

        Args:
            url: The URL to browse
            force_login: Whether to force re-authentication even if a state exists

        Returns:
            Tuple of (playwright, browser, context, page) if successful, (None, None, None, None) otherwise
        """
        # Extract site name from URL
        site_name = self.extract_site_name(url)
        logger.info(f"Using extracted site name: {site_name}")

        # Check if authentication state exists
        if force_login or not self.state_service.state_exists(site_name):
            # Request login if needed
            login_success = await self._request_login(url, site_name)
            if not login_success:
                # Check if we have login config for this site
                ntm_sites = ["nt", "nsd", "kuriren", "norran", "corren"]
                use_ntm_service = site_name.lower() in ntm_sites
                use_nwt_service = site_name.lower() == "nwt"
                
                has_login_config = (
                    use_ntm_service and self.ntm_login_service.has_login_config(site_name)
                ) or (use_nwt_service and self.nwt_login_service.has_login_config(site_name))
                
                if has_login_config:
                    # We have config but login failed - this is an error
                    raise Exception(f"Failed to authenticate for {site_name}")
                else:
                    # No login config - proceed without authentication
                    logger.info(f"No login configuration for {site_name}, proceeding without authentication")
                    return await self._browse_without_auth(url)

        # Load the auth state
        state_path = self.state_service.load_storage_state(site_name)
        if not state_path:
            # Fallback to no auth if state loading fails
            logger.warning(f"Failed to load authentication state for {site_name}, proceeding without authentication")
            return await self._browse_without_auth(url)

        try:
            # Start Playwright
            logger.info(f"Starting browser session for {url} using {site_name} authentication")
            playwright = await async_playwright().start()

            # Launch browser
            browser = await playwright.chromium.launch(headless=self.headless)

            # Create context with authentication state
            context = await browser.new_context(
                storage_state=state_path, viewport={"width": 1280, "height": 800}
            )

            # Create page and navigate to site
            page = await context.new_page()
            logger.info(f"Navigating to {url}")

            # Navigate to the URL
            await page.goto(url, timeout=self.timeout)
            logger.info("Successfully loaded page with authentication state")

            # Take screenshot as verification
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.screenshot_dir / f"{site_name}_screenshot_{timestamp}.png"
            await page.screenshot(path=str(screenshot_path))
            logger.info(f"Saved screenshot to {screenshot_path}")

            return playwright, browser, context, page

        except Exception as e:
            raise Exception(f"Error browsing {url}: {str(e)}")

    async def close_browser_session(
        self, playwright: Playwright, browser: Browser, context: BrowserContext, page: Page
    ) -> None:
        """
        Close all browser resources.

        Args:
            playwright: Playwright instance
            browser: Browser instance
            context: Browser context
            page: Page instance
        """
        logger.info("Closing browser session...")
        try:
            # Add proper type checking before trying to close each component
            if hasattr(page, "close") and callable(page.close):
                await page.close()

            if hasattr(context, "close") and callable(context.close):
                await context.close()

            if hasattr(browser, "close") and callable(browser.close):
                await browser.close()

            if hasattr(playwright, "stop") and callable(playwright.stop):
                await playwright.stop()

            logger.info("Browser session closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser session: {str(e)}")

    async def fetch_html(self, url: str) -> str | None:
        """
        Fetch HTML content from a URL using an authenticated browser session.

        Args:
            url: The URL to fetch HTML from

        Returns:
            HTML content as string, or None if fetching failed
        """
        logger.info(f"Fetching HTML from {url}")

        # Browse to the URL
        try:
            playwright, browser, context, page = await self.browse_url(url)
        except Exception as e:
            logger.error(f"Error during browsing: {str(e)}")
            return None

        try:
            # Wait for page to be fully loaded
            await page.wait_for_load_state("load")

            # Extract HTML content - get entire page HTML
            html_content = await page.content()

            logger.info(f"Successfully fetched HTML content ({len(html_content)} bytes)")
            return html_content

        except Exception as e:
            logger.error(f"Error fetching HTML content: {str(e)}")
            return None

        finally:
            # Close browser session
            await self.close_browser_session(playwright, browser, context, page)
