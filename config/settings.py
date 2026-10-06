"""
Centralized Configuration Settings for Multi-Source Web Scraping Pipeline.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class Config:
    """Application configuration parameters with safe defaults and CLI overridability."""

    # Target Web Sources
    BOOKS_BASE_URL: str = "https://books.toscrape.com/"
    BOOKS_START_URL: str = "https://books.toscrape.com/catalogue/page-1.html"
    QUOTES_BASE_URL: str = "https://quotes.toscrape.com/"
    QUOTES_START_URL: str = "https://quotes.toscrape.com/page/1/"

    # Source identifiers
    SOURCE_BOOKS: str = "Books to Scrape"
    SOURCE_QUOTES: str = "Quotes to Scrape"

    # HTTP Network Policies
    REQUEST_TIMEOUT: int = 15
    MAX_RETRIES: int = 3
    BACKOFF_FACTOR: float = 0.5
    RETRY_STATUS_CODES: Tuple[int, ...] = (429, 500, 502, 503, 504)
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 (Educational Scraping Assessment)"
    )

    # Politeness & Throttling
    RATE_LIMIT_DELAY: float = 0.05  # seconds between page requests

    # Scraper Runtime Flags
    MAX_PAGES: int = 0  # 0 or None indicates scrape until pagination ends
    MAX_RECORDS: Optional[int] = None  # None indicates scrape all available records
    FETCH_BOOK_DETAILS: bool = False  # Deep crawl for description/category on detail page

    # Deduplication
    DEDUP_ACTION: str = "remove"  # "remove" or "flag"

    # File System Locations
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    OUTPUT_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "output")
    LOGS_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "logs")

    FINAL_CSV_FILENAME: str = "final_dataset.csv"
    SUMMARY_JSON_FILENAME: str = "summary_report.json"
    LOG_FILENAME: str = "scraper.log"

    def ensure_directories(self) -> None:
        """Create output and logs directories if they do not already exist."""
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)


DEFAULT_CONFIG = Config()
