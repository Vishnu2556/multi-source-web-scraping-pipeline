"""
Quotes to Scrape Scraper Module.
Extracts quote records including quote text, author, tags, and source URLs.
Supports pagination across all quote pages.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config.settings import DEFAULT_CONFIG, Config
from scrapers.base_scraper import BaseScraper


class QuotesScraper(BaseScraper):
    """Scraper for https://quotes.toscrape.com/."""

    def __init__(
        self,
        config: Optional[Config] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        super().__init__(config=config, logger=logger)
        self.start_url = self.config.QUOTES_START_URL

    def parse_page(
        self, html_content: str, current_url: str
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Parses a quotes page from Quotes to Scrape.

        Args:
            html_content: HTML string of the quotes page.
            current_url: URL of the current page.

        Returns:
            Tuple of (extracted_records, next_page_url).
        """
        records: List[Dict[str, Any]] = []
        soup = BeautifulSoup(html_content, "html.parser")

        quote_divs = soup.select("div.quote")

        for idx, div in enumerate(quote_divs):
            try:
                # 1. Quote text
                text_elem = div.select_one("span.text")
                quote_text = text_elem.get_text(strip=True) if text_elem else ""

                # 2. Author
                author_elem = div.select_one("small.author")
                author = author_elem.get_text(strip=True) if author_elem else None

                # 3. Author details URL
                author_link_elem = div.select_one("span a")
                rel_url = author_link_elem.get("href", "") if author_link_elem else ""
                author_bio_url = urljoin(current_url, rel_url) if rel_url else ""
                
                # Source URL is the page URL containing the quote (with anchor)
                source_url = f"{current_url}#quote-{idx + 1}"

                # 4. Tags
                tag_elems = div.select("div.tags a.tag")
                tags = [t.get_text(strip=True) for t in tag_elems if t.get_text(strip=True)]
                
                # Primary tag acts as natural category
                category = tags[0] if tags else "General"

                desc_parts = [f"Quote by {author}"] if author else ["Quote"]
                if author_bio_url:
                    desc_parts.append(f"Author bio: {author_bio_url}")
                description = " | ".join(desc_parts)

                record = {
                    "source": self.config.SOURCE_QUOTES,
                    "source_url": source_url,
                    "name_or_title": quote_text,
                    "category": None,
                    "price": None,
                    "rating": None,
                    "author": author,
                    "tags": tags,
                    "availability": None,
                    "description": description,
                    "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                records.append(record)

            except Exception as e:
                self.logger.error(f"Error parsing quote block on page {current_url}: {e}", exc_info=False)
                continue

        # Extract next page link
        next_elem = soup.select_one("li.next a")
        next_url = None
        if next_elem and next_elem.get("href"):
            next_url = urljoin(current_url, next_elem.get("href"))

        return records, next_url
