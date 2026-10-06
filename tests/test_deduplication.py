"""
Unit tests for duplicate detection module.
"""
import pytest

from processing.deduplication import (
    deduplicate_records,
    generate_record_key,
    generate_text_fingerprint,
)
from processing.models import StandardRecord


class TestTextFingerprint:
    def test_case_and_whitespace_insensitivity(self):
        fp1 = generate_text_fingerprint("Example Book Title")
        fp2 = generate_text_fingerprint("  EXAMPLE   BOOK TITLE  ")
        assert fp1 == fp2 == "example book title"

    def test_punctuation_and_quotes(self):
        fp1 = generate_text_fingerprint("“Example Book Title!”")
        fp2 = generate_text_fingerprint("Example Book Title")
        assert fp1 == fp2

    def test_unicode_accents(self):
        fp1 = generate_text_fingerprint("Café au Lait")
        fp2 = generate_text_fingerprint("Cafe au Lait")
        assert fp1 == fp2


class TestDeduplication:
    def test_dedup_remove_exact_and_fuzzy(self):
        rec1 = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/book-1/index.html",
            name_or_title="Example Book Title",
            price=25.0,
        )
        rec2 = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/book-1-alt/index.html",
            name_or_title="  EXAMPLE   BOOK TITLE!  ",
            price=25.0,
        )
        rec3 = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/book-2/index.html",
            name_or_title="Completely Different Book",
            price=30.0,
        )

        deduped, report = deduplicate_records([rec1, rec2, rec3], action="remove")
        assert len(deduped) == 2
        assert report.duplicates_count == 1
        assert report.unique_count == 2
        assert deduped[0].name_or_title == "Example Book Title"
        assert deduped[1].name_or_title == "Completely Different Book"

    def test_dedup_flag_mode(self):
        rec1 = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/book-1/index.html",
            name_or_title="Example Book Title",
            price=25.0,
        )
        rec2 = StandardRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/book-1-dup/index.html",
            name_or_title="EXAMPLE BOOK TITLE",
            price=25.0,
        )

        flagged, report = deduplicate_records([rec1, rec2], action="flag")
        assert len(flagged) == 2
        assert report.duplicates_count == 1
        assert flagged[0].is_duplicate is False
        assert flagged[1].is_duplicate is True
