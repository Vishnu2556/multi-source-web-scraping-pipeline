"""
Duplicate Detection and Resolution Module.
Implements fuzzy/normalized fingerprint matching to identify identical records
differing in whitespace, capitalization, punctuation, or formatting.
"""
from dataclasses import dataclass, field
import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

from processing.models import StandardRecord


def generate_text_fingerprint(text: Optional[str]) -> str:
    """Creates a normalized fingerprint for matching text irrespective of casing,
    punctuation, accents, and spacing discrepancies.

    Example transformations:
        'Example Book Title'  -> 'example book title'
        '  Example   Book Title! ' -> 'example book title'
        '“EXAMPLE BOOK TITLE”' -> 'example book title'

    Args:
        text: Input string.

    Returns:
        Canonical alphanumeric fingerprint string.
    """
    if not text:
        return ""

    # NFKD normalization to separate base characters and diacritics
    nfkd = unicodedata.normalize("NFKD", str(text))
    ascii_text = nfkd.encode("ASCII", "ignore").decode("utf-8")

    # Lowercase
    lowered = ascii_text.casefold()

    # Remove all punctuation, quotes, and symbols
    no_punct = re.sub(r"[^\w\s]", "", lowered)

    # Collapse multiple whitespace characters into single space
    collapsed = re.sub(r"\s+", " ", no_punct).strip()
    return collapsed


def generate_record_key(record: StandardRecord) -> str:
    """Generates a composite deduplication key based on source and distinguishing attributes.

    For Books:
        source + fingerprint(name_or_title)
    For Quotes:
        source + fingerprint(author) + fingerprint(name_or_title)

    Args:
        record: StandardRecord instance.

    Returns:
        Deterministic fingerprint string.
    """
    source_fp = generate_text_fingerprint(record.source)
    title_fp = generate_text_fingerprint(record.name_or_title)

    if record.source == "Quotes to Scrape":
        author_fp = generate_text_fingerprint(record.author)
        # Use full fingerprint for quote text and author
        return f"{source_fp}::quotes::{author_fp}::{title_fp}"
    
    # Default for Books: source + normalized title
    return f"{source_fp}::books::{title_fp}"


@dataclass
class DeduplicationReport:
    """Tracks metrics and audit information for duplicate detection."""
    total_input: int = 0
    unique_count: int = 0
    duplicates_count: int = 0
    duplicates_by_source: Dict[str, int] = field(default_factory=dict)
    duplicate_records: List[Dict[str, str]] = field(default_factory=list)
    action_taken: str = "remove"


def deduplicate_records(
    records: List[StandardRecord],
    action: str = "remove",
) -> Tuple[List[StandardRecord], DeduplicationReport]:
    """Detects duplicate records using normalized fingerprint keys and either
    removes them or flags them.

    Args:
        records: List of cleaned StandardRecord instances.
        action: 'remove' (discard subsequent duplicates) or 'flag' (keep all, mark is_duplicate=True).

    Returns:
        Tuple of (processed_records, DeduplicationReport).
    """
    report = DeduplicationReport(total_input=len(records), action_taken=action)
    seen_keys: Dict[str, StandardRecord] = {}
    output_records: List[StandardRecord] = []

    for rec in records:
        key = generate_record_key(rec)
        
        # Product-level URL canonicalization check for books
        is_book = rec.source == "Books to Scrape"
        url_key = f"url::{rec.source_url.strip().lower()}" if (is_book and rec.source_url) else None

        is_dup = (key in seen_keys) or (url_key is not None and url_key in seen_keys)

        if is_dup:
            report.duplicates_count += 1
            src = rec.source or "Unknown"
            report.duplicates_by_source[src] = report.duplicates_by_source.get(src, 0) + 1
            
            primary_rec = seen_keys.get(key) or (seen_keys.get(url_key) if url_key else None)
            report.duplicate_records.append({
                "duplicate_title": rec.name_or_title,
                "duplicate_url": rec.source_url,
                "source": rec.source,
                "duplicate_of": primary_rec.name_or_title if primary_rec else "",
            })

            if action == "flag":
                rec.is_duplicate = True
                output_records.append(rec)
            # If action == 'remove', do not add to output_records
        else:
            rec.is_duplicate = False
            seen_keys[key] = rec
            if url_key:
                seen_keys[url_key] = rec
            output_records.append(rec)
            report.unique_count += 1

    return output_records, report
