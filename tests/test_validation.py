"""
Unit tests for data validation module.
"""
import pytest

from processing.models import StandardRecord
from processing.validation import validate_record, validate_records


class TestValidation:
    def test_valid_book_record(self):
        rec = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/book_1/index.html",
            name_or_title="A Light in the Attic",
            category="Poetry",
            price=51.77,
            rating=3.0,
            availability="In stock",
        )
        res = validate_record(rec)
        assert res.is_valid is True
        assert len(res.errors) == 0

    def test_missing_book_category(self):
        rec = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/book_1/index.html",
            name_or_title="A Light in the Attic",
            category="",
            price=51.77,
            rating=3.0,
        )
        res = validate_record(rec)
        assert res.is_valid is False
        assert any("Books must have a valid category" in e for e in res.errors)

    def test_valid_quote_record(self):
        rec = StandardRecord(
            source="Quotes to Scrape",
            source_url="https://quotes.toscrape.com/page/1/#quote-1",
            name_or_title="The world as we have created it...",
            author="Albert Einstein",
            tags="change, thinking",
        )
        res = validate_record(rec)
        assert res.is_valid is True
        assert len(res.errors) == 0

    def test_missing_source(self):
        rec = StandardRecord(
            source="",
            source_url="https://example.com",
            name_or_title="Something",
        )
        res = validate_record(rec)
        assert res.is_valid is False
        assert any("source is empty" in e for e in res.errors)

    def test_unrecognized_source(self):
        rec = StandardRecord(
            source="Random Unknown Site",
            source_url="https://example.com",
            name_or_title="Something",
        )
        res = validate_record(rec)
        assert res.is_valid is False
        assert any("UNRECOGNIZED_SOURCE" in e for e in res.errors)

    def test_missing_title(self):
        rec = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/book_1/index.html",
            name_or_title="",
            price=20.0,
        )
        res = validate_record(rec)
        assert res.is_valid is False
        assert any("name_or_title is empty" in e for e in res.errors)

    def test_invalid_url(self):
        rec = StandardRecord(
            source="Books to Scrape",
            source_url="invalid_url",
            name_or_title="Test Book",
            price=10.0,
        )
        res = validate_record(rec)
        assert res.is_valid is False
        assert any("INVALID_URL" in e for e in res.errors)

    def test_invalid_rating_range(self):
        rec = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/book_1/index.html",
            name_or_title="Test Book",
            price=15.0,
            rating=6.5,  # Out of range
        )
        res = validate_record(rec)
        assert res.is_valid is False
        assert any("INVALID_RATING_RANGE" in e for e in res.errors)

    def test_batch_validation_reporting(self):
        valid_rec = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/b1/index.html",
            name_or_title="Book 1",
            category="Fiction",
            price=20.0,
        )
        invalid_rec = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/b2/index.html",
            name_or_title="",  # Invalid missing title
            category="Fiction",
            price=20.0,
        )
        valid_list, report = validate_records([valid_rec, invalid_rec])
        assert len(valid_list) == 1
        assert report.total_inspected == 2
        assert report.total_valid == 1
        assert report.total_rejected == 1
        assert "MISSING_REQUIRED_FIELD: name_or_title is empty or missing" in report.rejection_reasons
