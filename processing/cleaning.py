"""
Data Cleaning and Standardization Module.
Transforms raw scraped data into clean, typed, and normalized records.
"""
import html
import re
import unicodedata
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urljoin

from processing.models import StandardRecord


# Mapping word-based ratings to numeric values
RATING_MAP: Dict[str, float] = {
    "zero": 0.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
}

NULL_REPRESENTATIONS = {
    "",
    "none",
    "null",
    "n/a",
    "na",
    "undefined",
    "-",
    "unknown",
}


def normalize_whitespace(text: Optional[str]) -> Optional[str]:
    """Strips leading/trailing whitespace and collapses consecutive internal whitespace.

    Args:
        text: Raw input string.

    Returns:
        Cleaned string or None if input is empty.
    """
    if text is None:
        return None
    # Replace non-breaking spaces and other unicode spaces
    cleaned = re.sub(r"[\s\u00a0\u200b]+", " ", str(text)).strip()
    return cleaned if cleaned else None


def clean_text(text: Optional[str], strip_quotes: bool = False) -> Optional[str]:
    """Cleans and standardizes text by unescaping HTML entities, normalizing unicode,
    and trimming surrounding whitespace or curly quotation marks.

    Args:
        text: Raw text string.
        strip_quotes: Whether to strip outer quotation marks (e.g., for quotes).

    Returns:
        Normalized text or None.
    """
    if text is None:
        return None

    # Unescape HTML entities (e.g. &amp; -> &, &#39; -> ')
    unescaped = html.unescape(str(text))

    # Normalize unicode to NFKC (standardizes ligatures, symbols)
    normalized = unicodedata.normalize("NFKC", unescaped)

    # Normalize whitespace
    cleaned = normalize_whitespace(normalized)
    if not cleaned:
        return None

    # Check for sentinel null representations
    if cleaned.lower() in NULL_REPRESENTATIONS:
        return None

    if strip_quotes:
        # Strip common outer quote marks including smart/curly quotes
        cleaned = re.sub(r'^["\'“”«»]+|["\'“”«»]+$', '', cleaned).strip()

    return cleaned if cleaned else None


def clean_price(raw_price: Any) -> Optional[float]:
    """Extracts numeric price from strings containing currency symbols or formats.

    Handles edge cases such as '£51.77', 'Â£51.77', '$19.99', '51.77', etc.

    Args:
        raw_price: Price representation (str, int, float).

    Returns:
        Float rounded to 2 decimal places, or None if price is absent or invalid.
    """
    if raw_price is None:
        return None

    if isinstance(raw_price, (int, float)):
        val = float(raw_price)
        return round(val, 2) if val >= 0 else None

    price_str = str(raw_price).strip()
    if not price_str or price_str.lower() in NULL_REPRESENTATIONS:
        return None

    # Extract numeric part (e.g. from '£51.77' or 'Â£51.77')
    match = re.search(r"[-+]?\d+(?:\.\d+)?", price_str)
    if match:
        try:
            val = float(match.group())
            return round(val, 2) if val >= 0 else None
        except ValueError:
            return None
    return None


def clean_rating(raw_rating: Any) -> Optional[float]:
    """Standardizes ratings into a numeric float between 0.0 and 5.0.

    Converts textual ratings like 'Three' or string numbers like '3' to 3.0.

    Args:
        raw_rating: Rating representation (str, int, float, or list of classes).

    Returns:
        Float between 0.0 and 5.0, or None if invalid or absent.
    """
    if raw_rating is None:
        return None

    # If list of classes provided (e.g. ['star-rating', 'Three'])
    if isinstance(raw_rating, (list, tuple)):
        for item in raw_rating:
            cleaned_sub = clean_rating(item)
            if cleaned_sub is not None:
                return cleaned_sub
        return None

    if isinstance(raw_rating, (int, float)):
        val = float(raw_rating)
        return val if 0.0 <= val <= 5.0 else None

    rating_str = str(raw_rating).strip().lower()
    if not rating_str or rating_str in NULL_REPRESENTATIONS:
        return None

    # Check direct word map
    if rating_str in RATING_MAP:
        return RATING_MAP[rating_str]

    # Check if a word rating is embedded within string (e.g. 'star-rating three')
    for word, num in RATING_MAP.items():
        if re.search(rf"\b{word}\b", rating_str):
            return num

    # Check numeric digit in string
    match = re.search(r"\b([0-5](?:\.\d+)?)\b", rating_str)
    if match:
        try:
            val = float(match.group(1))
            if 0.0 <= val <= 5.0:
                return val
        except ValueError:
            return None

    return None


def clean_url(raw_url: Optional[str], base_url: Optional[str] = None) -> Optional[str]:
    """Normalizes and validates a URL, resolving relative paths when base_url is provided.

    Args:
        raw_url: Relative or absolute URL.
        base_url: Base URL to resolve against.

    Returns:
        Cleaned absolute URL or None if invalid.
    """
    if not raw_url:
        return None

    url_str = str(raw_url).strip()
    if not url_str or url_str.lower() in NULL_REPRESENTATIONS:
        return None

    # Resolve against base URL if relative
    if base_url:
        url_str = urljoin(base_url, url_str)

    parsed = urlparse(url_str)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return url_str

    return None


def clean_tags(raw_tags: Any) -> Optional[str]:
    """Standardizes tags into a sorted, comma-separated string of unique tags.

    Args:
        raw_tags: List of strings or a comma-separated string.

    Returns:
        Comma-separated string of tags or None.
    """
    if raw_tags is None:
        return None

    tag_list: List[str] = []
    if isinstance(raw_tags, (list, tuple, set)):
        for t in raw_tags:
            c = clean_text(str(t))
            if c:
                tag_list.append(c.lower())
    elif isinstance(raw_tags, str):
        parts = raw_tags.split(",")
        for p in parts:
            c = clean_text(p)
            if c:
                tag_list.append(c.lower())

    if not tag_list:
        return None

    # Deduplicate while preserving or sorting order
    unique_tags = sorted(list(set(tag_list)))
    return ", ".join(unique_tags)


def clean_raw_record(raw: Dict[str, Any]) -> StandardRecord:
    """Takes a dictionary of raw scraped fields and produces a cleaned StandardRecord.

    Args:
        raw: Dictionary containing raw fields from scrapers.

    Returns:
        StandardRecord with cleaned and typed values.
    """
    source = clean_text(raw.get("source")) or "Unknown Source"
    source_url = clean_url(raw.get("source_url")) or ""
    
    # Strip quotes from name_or_title if it's from Quotes to Scrape
    strip_q = "quote" in source.lower()
    name_or_title = clean_text(raw.get("name_or_title"), strip_quotes=strip_q) or ""

    category = clean_text(raw.get("category"))
    price = clean_price(raw.get("price"))
    rating = clean_rating(raw.get("rating"))
    author = clean_text(raw.get("author"))
    tags = clean_tags(raw.get("tags"))
    description = clean_text(raw.get("description"))
    availability = clean_text(raw.get("availability"))

    scraped_at = clean_text(raw.get("scraped_at"))
    
    return StandardRecord(
        source=source,
        source_url=source_url,
        name_or_title=name_or_title,
        category=category,
        price=price,
        rating=rating,
        author=author,
        tags=tags,
        description=description,
        availability=availability,
        scraped_at=scraped_at if scraped_at else StandardRecord(source="", source_url="", name_or_title="").scraped_at,
        is_duplicate=bool(raw.get("is_duplicate", False)),
    )
