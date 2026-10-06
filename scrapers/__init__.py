"""
Web scrapers package.
"""
from scrapers.base_scraper import BaseScraper
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper

__all__ = ["BaseScraper", "BooksScraper", "QuotesScraper"]
