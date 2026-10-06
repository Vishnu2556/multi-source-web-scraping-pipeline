"""
Unit tests for data cleaning and normalization functions.
"""
import pytest

from processing.cleaning import (
    clean_price,
    clean_rating,
    clean_tags,
    clean_text,
    clean_url,
    clean_raw_record,
    normalize_whitespace,
)
from processing.models import StandardRecord


class TestNormalizeWhitespace:
    def test_strip_and_collapse_spaces(self):
        assert normalize_whitespace("   hello   world   ") == "hello world"

    def test_tabs_and_newlines(self):
        assert normalize_whitespace("line1\n\t  line2\r\n") == "line1 line2"

    def test_empty_and_none(self):
        assert normalize_whitespace(None) is None
        assert normalize_whitespace("   ") is None
        assert normalize_whitespace("") is None


class TestCleanText:
    def test_html_entities(self):
        raw = "Tom &amp; Jerry &quot;Show&quot;"
        assert clean_text(raw) == 'Tom & Jerry "Show"'

    def test_null_sentinels(self):
        for val in ["N/A", "n/a", "NONE", "null", "undefined", "-", ""]:
            assert clean_text(val) is None

    def test_strip_smart_quotes(self):
        raw = "“Life is like a box of chocolates.”"
        assert clean_text(raw, strip_quotes=True) == "Life is like a box of chocolates."


class TestCleanPrice:
    def test_gbp_symbol(self):
        assert clean_price("£51.77") == 51.77

    def test_encoding_artifact(self):
        # Common artifact from latin1 vs utf-8 encoding on books.toscrape.com
        assert clean_price("Â£51.77") == 51.77

    def test_usd_symbol(self):
        assert clean_price("$19.99") == 19.99

    def test_plain_number_and_float(self):
        assert clean_price("42.50") == 42.50
        assert clean_price(15.95) == 15.95
        assert clean_price(10) == 10.0

    def test_invalid_and_empty_price(self):
        assert clean_price(None) is None
        assert clean_price("") is None
        assert clean_price("Free") is None
        assert clean_price("-5.00") is None


class TestCleanRating:
    def test_word_ratings(self):
        assert clean_rating("One") == 1.0
        assert clean_rating("Two") == 2.0
        assert clean_rating("Three") == 3.0
        assert clean_rating("Four") == 4.0
        assert clean_rating("Five") == 5.0

    def test_class_list_from_bs4(self):
        assert clean_rating(["star-rating", "Four"]) == 4.0
        assert clean_rating(["star-rating", "One"]) == 1.0

    def test_numeric_rating(self):
        assert clean_rating(3.5) == 3.5
        assert clean_rating("4") == 4.0

    def test_invalid_ratings(self):
        assert clean_rating("Ten") is None
        assert clean_rating(9.0) is None
        assert clean_rating(None) is None
        assert clean_rating("") is None


class TestCleanUrl:
    def test_valid_absolute_url(self):
        url = "https://books.toscrape.com/catalogue/book_1/index.html"
        assert clean_url(url) == url

    def test_relative_url_with_base(self):
        base = "https://books.toscrape.com/catalogue/page-2.html"
        rel = "book_1/index.html"
        expected = "https://books.toscrape.com/catalogue/book_1/index.html"
        assert clean_url(rel, base_url=base) == expected

    def test_invalid_urls(self):
        assert clean_url(None) is None
        assert clean_url("") is None
        assert clean_url("not_a_valid_url") is None
        assert clean_url("ftp://example.com/file") is None


class TestCleanTags:
    def test_list_of_tags(self):
        raw = ["Inspirational", "  life  ", "INSPIRATIONAL", "change"]
        expected = "change, inspirational, life"
        assert clean_tags(raw) == expected

    def test_comma_separated_string(self):
        raw = "books, reading, Books"
        expected = "books, reading"
        assert clean_tags(raw) == expected

    def test_empty_tags(self):
        assert clean_tags(None) is None
        assert clean_tags([]) is None


class TestCleanRawRecord:
    def test_full_record_transformation(self):
        raw = {
            "source": "  Books to Scrape  ",
            "source_url": "https://books.toscrape.com/catalogue/book_1/index.html",
            "name_or_title": "  A Light in the Attic  ",
            "category": "Poetry",
            "price": "£51.77",
            "rating": ["star-rating", "Three"],
            "author": None,
            "tags": None,
            "description": "  A nice book.  ",
        }
        record = clean_raw_record(raw)
        assert isinstance(record, StandardRecord)
        assert record.source == "Books to Scrape"
        assert record.name_or_title == "A Light in the Attic"
        assert record.price == 51.77
        assert record.rating == 3.0
        assert record.category == "Poetry"
        assert record.description == "A nice book."
