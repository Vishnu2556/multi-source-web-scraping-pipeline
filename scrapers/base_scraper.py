"""
Base Scraper Architecture.
Provides resilient HTTP networking, automated retry with exponential backoff,
polite rate-limiting, and error-safe lifecycle management.
"""
from abc import ABC, abstractmethod
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import DEFAULT_CONFIG, Config


class BaseScraper(ABC):
    """Abstract Base Class for web scrapers with resilient networking and pagination."""

    def __init__(
        self,
        config: Optional[Config] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config or DEFAULT_CONFIG
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.session = self._create_resilient_session()
        
        # Performance and audit metrics
        self.pages_scraped: int = 0
        self.records_extracted: int = 0
        self.failed_urls: List[str] = []

    def _create_resilient_session(self) -> requests.Session:
        """Configures a requests.Session with connection pooling and automated exponential retries."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

        retry_strategy = Retry(
            total=self.config.MAX_RETRIES,
            backoff_factor=self.config.BACKOFF_FACTOR,
            status_forcelist=self.config.RETRY_STATUS_CODES,
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetches the HTML content of a given URL with timeout and error handling.

        Args:
            url: The HTTP/HTTPS URL to request.

        Returns:
            The HTML text if successful, or None on failure.
        """
        # Apply polite rate-limiting delay between requests
        if self.config.RATE_LIMIT_DELAY > 0:
            time.sleep(self.config.RATE_LIMIT_DELAY)

        try:
            self.logger.debug(f"Fetching URL: {url}")
            response = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT)

            if response.status_code == 200:
                return response.text

            self.logger.warning(
                f"Non-200 status code received: {response.status_code} for URL: {url}"
            )
            self.failed_urls.append(url)
            return None

        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout occurred fetching URL: {url} (> {self.config.REQUEST_TIMEOUT}s)")
            self.failed_urls.append(url)
            return None
        except requests.exceptions.ConnectionError as ce:
            self.logger.error(f"Network connection failed for URL: {url} - {ce}")
            self.failed_urls.append(url)
            return None
        except requests.exceptions.RequestException as re:
            self.logger.error(f"Unexpected request exception for URL: {url} - {re}")
            self.failed_urls.append(url)
            return None

    @abstractmethod
    def parse_page(self, html_content: str, current_url: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Parses an HTML page into records and extracts the next page URL.

        Args:
            html_content: Raw HTML text of the page.
            current_url: URL of the current page (for relative resolution).

        Returns:
            Tuple of (list_of_extracted_raw_records, next_page_url_or_None).
        """
        pass

    def scrape(
        self,
        max_pages: Optional[int] = None,
        max_records: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Orchestrates pagination and scraping across multiple pages.

        Args:
            max_pages: Optional cap on the number of pages to scrape (None or 0 for all).
            max_records: Optional cap on total records collected (None or 0 for all).

        Returns:
            List of raw dictionaries extracted from the target website.
        """
        records: List[Dict[str, Any]] = []
        next_url = getattr(self, "start_url", None)
        pages_processed = 0
        limit_pages = max_pages if (max_pages and max_pages > 0) else getattr(self.config, "MAX_PAGES", 0)
        limit_records = max_records if (max_records and max_records > 0) else getattr(self.config, "MAX_RECORDS", None)

        self.logger.info(f"Starting crawl for {self.__class__.__name__} from: {next_url}")

        while next_url:
            if limit_pages and pages_processed >= limit_pages:
                self.logger.info(f"Reached page limit of {limit_pages}. Stopping pagination.")
                break
            if limit_records and len(records) >= limit_records:
                self.logger.info(f"Reached record limit of {limit_records}. Stopping pagination.")
                records = records[:limit_records]
                break

            self.logger.info(f"Scraping page {pages_processed + 1}: {next_url}")
            html_text = self.fetch_page(next_url)

            if not html_text:
                self.logger.error(f"Failed to retrieve page content at: {next_url}. Halting pagination chain.")
                break

            page_records, next_url = self.parse_page(html_text, next_url)
            records.extend(page_records)
            pages_processed += 1
            self.pages_scraped = pages_processed
            self.records_extracted = len(records)

            if limit_records and len(records) >= limit_records:
                records = records[:limit_records]
                self.records_extracted = len(records)
                self.logger.info(f"Reached record limit of {limit_records}. Stopping crawl.")
                break

            self.logger.debug(
                f"Extracted {len(page_records)} records from page {pages_processed}. Next URL: {next_url}"
            )

        self.logger.info(
            f"Completed scraping for {self.__class__.__name__}. "
            f"Pages scraped: {pages_processed}, Total records: {len(records)}, "
            f"Failed URLs: {len(self.failed_urls)}"
        )
        return records

    def close(self) -> None:
        """Closes the underlying requests session."""
        self.session.close()
