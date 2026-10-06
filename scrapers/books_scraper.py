"""
Books to Scrape Scraper Module.
Extracts book records including title, price, availability, rating, category, and product URLs.
Traverses categories and follows pagination automatically until all records are collected.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config.settings import DEFAULT_CONFIG, Config
from scrapers.base_scraper import BaseScraper


class BooksScraper(BaseScraper):
    """Scraper for https://books.toscrape.com/ with automated category traversal and pagination."""

    def __init__(
        self,
        config: Optional[Config] = None,
        logger: Optional[logging.Logger] = None,
        fetch_details: bool = False,
    ) -> None:
        super().__init__(config=config, logger=logger)
        self.start_url = self.config.BOOKS_START_URL
        self.base_url = self.config.BOOKS_BASE_URL
        self.fetch_details = fetch_details or self.config.FETCH_BOOK_DETAILS

    def parse_page(
        self, html_content: str, current_url: str, default_category: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Parses a book listing page (catalog or category page).

        Args:
            html_content: HTML string of the page.
            current_url: URL of the current page.
            default_category: Optional known category name for category pages.

        Returns:
            Tuple of (extracted_records, next_page_url).
        """
        records: List[Dict[str, Any]] = []
        soup = BeautifulSoup(html_content, "html.parser")

        # Determine category dynamically from page context
        detected_category = default_category
        if not detected_category:
            # Check h1 tag (standard on category pages, e.g. <h1>Travel</h1>)
            h1_elem = soup.select_one(".page-header h1, h1")
            if h1_elem:
                h1_text = h1_elem.get_text(strip=True)
                # Ensure it's not a generic header like "All products"
                if h1_text and h1_text.lower() != "all products":
                    detected_category = h1_text

            # Check breadcrumb if not found in h1
            if not detected_category:
                crumbs = soup.select("ul.breadcrumb li a, ul.breadcrumb li.active")
                if len(crumbs) >= 3:
                    detected_category = crumbs[2].get_text(strip=True)

        # Find all product cards on the page
        book_pods = soup.select("article.product_pod")

        for pod in book_pods:
            try:
                # 1. Title
                title_elem = pod.select_one("h3 a")
                if not title_elem:
                    self.logger.warning("Found product_pod without h3 a element; skipping card.")
                    continue
                # The 'title' attribute holds the full untruncated title
                title = title_elem.get("title") or title_elem.get_text(strip=True)

                # 2. Product Detail URL
                rel_href = title_elem.get("href", "")
                product_url = urljoin(current_url, rel_href)

                # 3. Price
                price_elem = pod.select_one(".price_color")
                price_raw = price_elem.get_text(strip=True) if price_elem else None

                # 4. Rating (class name, e.g., 'star-rating Three')
                rating_raw = None
                rating_elem = pod.select_one("p.star-rating")
                if rating_elem and rating_elem.get("class"):
                    classes = rating_elem.get("class")
                    rating_words = [c for c in classes if c.lower() != "star-rating"]
                    if rating_words:
                        rating_raw = rating_words[0]

                # 5. Availability
                avail_elem = pod.select_one(".instock.availability")
                availability = avail_elem.get_text(strip=True) if avail_elem else "In stock"

                category = detected_category
                description = None

                # Optional detail fetching if explicitly requested
                if self.fetch_details and product_url:
                    detail_cat, detail_desc = self._fetch_book_detail(product_url)
                    if detail_cat:
                        category = detail_cat
                    description = detail_desc

                record = {
                    "source": self.config.SOURCE_BOOKS,
                    "source_url": product_url,
                    "name_or_title": title,
                    "category": category,
                    "price": price_raw,
                    "rating": rating_raw,
                    "author": None,
                    "tags": None,
                    "availability": availability,
                    "description": description or f"Available: {availability}",
                    "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                records.append(record)

            except Exception as e:
                self.logger.error(f"Error parsing product card on {current_url}: {e}", exc_info=False)
                continue

        # Extract next page link
        next_elem = soup.select_one("li.next a")
        next_url = None
        if next_elem and next_elem.get("href"):
            next_url = urljoin(current_url, next_elem.get("href"))

        return records, next_url

    def discover_categories(self) -> List[Tuple[str, str]]:
        """Discovers all category names and URLs from the homepage sidebar.

        Returns:
            List of (category_name, category_url) tuples.
        """
        html = self.fetch_page(self.base_url)
        if not html:
            self.logger.error("Could not fetch homepage to discover categories.")
            return []

        soup = BeautifulSoup(html, "html.parser")
        cat_links = soup.select(".side_categories ul li ul li a")
        categories: List[Tuple[str, str]] = []

        for a in cat_links:
            cat_name = a.get_text(strip=True)
            rel_href = a.get("href", "")
            if rel_href:
                cat_url = urljoin(self.base_url, rel_href)
                categories.append((cat_name, cat_url))

        self.logger.info(f"Discovered {len(categories)} book categories on {self.base_url}.")
        return categories

    def scrape(
        self,
        max_pages: Optional[int] = None,
        max_records: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Scrapes books across all categories with full pagination and dynamic category assignment.

        Args:
            max_pages: Optional limit on total pages scraped.
            max_records: Optional limit on total records extracted.

        Returns:
            List of raw book dictionaries.
        """
        records: List[Dict[str, Any]] = []
        limit_pages = max_pages if (max_pages and max_pages > 0) else getattr(self.config, "MAX_PAGES", 0)
        limit_records = max_records if (max_records and max_records > 0) else getattr(self.config, "MAX_RECORDS", None)

        self.logger.info(f"Starting BooksScraper crawl. Limit pages: {limit_pages or 'ALL'}, Limit records: {limit_records or 'ALL'}")

        # Discover all categories to ensure 100% accurate category extraction
        categories = self.discover_categories()

        # If categories could not be fetched, fallback to catalog pagination
        if not categories:
            self.logger.warning("Falling back to catalog-based pagination without sidebar categories.")
            return super().scrape(max_pages=max_pages, max_records=max_records)

        pages_processed = 0

        for cat_name, cat_url in categories:
            if limit_pages and pages_processed >= limit_pages:
                self.logger.info(f"Reached page limit of {limit_pages}. Stopping category traversal.")
                break
            if limit_records and len(records) >= limit_records:
                self.logger.info(f"Reached record limit of {limit_records}. Stopping crawl.")
                break

            current_cat_url: Optional[str] = cat_url

            while current_cat_url:
                if limit_pages and pages_processed >= limit_pages:
                    break
                if limit_records and len(records) >= limit_records:
                    break

                pages_processed += 1
                self.pages_scraped = pages_processed
                self.logger.info(f"[Books Page {pages_processed}] Scraping category '{cat_name}': {current_cat_url}")

                html = self.fetch_page(current_cat_url)
                if not html:
                    self.logger.error(f"Failed to fetch category page: {current_cat_url}. Moving to next.")
                    break

                page_records, next_cat_url = self.parse_page(html, current_cat_url, default_category=cat_name)
                records.extend(page_records)
                self.records_extracted = len(records)

                self.logger.debug(
                    f"Category '{cat_name}' page yielded {len(page_records)} books. Total books so far: {len(records)}"
                )

                if limit_records and len(records) >= limit_records:
                    records = records[:limit_records]
                    self.records_extracted = len(records)
                    self.logger.info(f"Reached record limit of {limit_records}. Halting.")
                    break

                current_cat_url = next_cat_url

        self.logger.info(
            f"Completed BooksScraper. Pages scraped: {pages_processed}, Total books: {len(records)}, Failed URLs: {len(self.failed_urls)}"
        )
        return records

    def _fetch_book_detail(self, product_url: str) -> Tuple[Optional[str], Optional[str]]:
        """Optionally fetches the product detail page to retrieve category and full description."""
        html = self.fetch_page(product_url)
        if not html:
            return None, None

        soup = BeautifulSoup(html, "html.parser")
        crumbs = soup.select("ul.breadcrumb li a")
        category = crumbs[2].get_text(strip=True) if len(crumbs) > 2 else None

        desc_elem = soup.select_one("#product_description + p")
        description = desc_elem.get_text(strip=True) if desc_elem else None

        return category, description
