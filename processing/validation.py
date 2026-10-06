"""
Data Validation Module.
Validates cleaned StandardRecord instances against schema constraints and business rules.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from processing.models import StandardRecord


VALID_SOURCES: Set[str] = {
    "Books to Scrape",
    "Quotes to Scrape",
}


@dataclass
class ValidationResult:
    """Encapsulates the validation outcome of a single record."""
    is_valid: bool
    record: StandardRecord
    errors: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Aggregated validation statistics across a batch of records."""
    total_inspected: int = 0
    total_valid: int = 0
    total_rejected: int = 0
    rejection_reasons: Dict[str, int] = field(default_factory=dict)
    rejected_records: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def validation_rate(self) -> float:
        if self.total_inspected == 0:
            return 100.0
        return round((self.total_valid / self.total_inspected) * 100, 2)

    def add_result(self, result: ValidationResult) -> None:
        self.total_inspected += 1
        if result.is_valid:
            self.total_valid += 1
        else:
            self.total_rejected += 1
            for err in result.errors:
                self.rejection_reasons[err] = self.rejection_reasons.get(err, 0) + 1
            self.rejected_records.append({
                "record": result.record.to_dict(),
                "errors": result.errors,
            })


def validate_record(record: StandardRecord) -> ValidationResult:
    """Validates a single StandardRecord against required criteria.

    Rules checked:
    1. Source is recognized and non-empty.
    2. name_or_title is present and non-empty.
    3. source_url is a well-formed HTTP/HTTPS URL.
    4. If price is present, must be non-negative numeric float.
    5. If rating is present, must be between 1.0 and 5.0 inclusive.
    6. Source-specific checks: Books must have price & category; Quotes must have author.

    Args:
        record: StandardRecord to validate.

    Returns:
        ValidationResult indicating validity and any error messages.
    """
    errors: List[str] = []

    # 1. Source check
    if not record.source:
        errors.append("MISSING_REQUIRED_FIELD: source is empty")
    elif record.source not in VALID_SOURCES:
        errors.append(f"UNRECOGNIZED_SOURCE: '{record.source}' is not a recognized source")

    # 2. Name or Title check
    if not record.name_or_title or not record.name_or_title.strip():
        errors.append("MISSING_REQUIRED_FIELD: name_or_title is empty or missing")

    # 3. Source URL check
    if not record.source_url:
        errors.append("MISSING_REQUIRED_FIELD: source_url is empty")
    else:
        parsed_url = urlparse(record.source_url)
        if parsed_url.scheme not in ("http", "https"):
            errors.append(f"INVALID_URL_SCHEME: scheme '{parsed_url.scheme}' is not http/https")
        if not parsed_url.netloc:
            errors.append(f"INVALID_URL_HOST: URL '{record.source_url}' lacks host/netloc")

    # 4. Price check (if present)
    if record.price is not None:
        if not isinstance(record.price, (int, float)):
            errors.append(f"INVALID_PRICE_TYPE: price '{record.price}' is not numeric")
        elif record.price < 0.0:
            errors.append(f"INVALID_PRICE_VALUE: price '{record.price}' is negative")

    # 5. Rating check (if present)
    if record.rating is not None:
        if not isinstance(record.rating, (int, float)):
            errors.append(f"INVALID_RATING_TYPE: rating '{record.rating}' is not numeric")
        elif not (1.0 <= record.rating <= 5.0):
            errors.append(f"INVALID_RATING_RANGE: rating '{record.rating}' outside [1.0, 5.0]")

    # 6. Source-specific consistency checks
    if record.source == "Books to Scrape":
        if record.price is None:
            errors.append("MISSING_FIELD_FOR_SOURCE: Books must have a valid price")
        if not record.category or not record.category.strip():
            errors.append("MISSING_FIELD_FOR_SOURCE: Books must have a valid category")
    elif record.source == "Quotes to Scrape":
        if not record.author or not record.author.strip():
            errors.append("MISSING_FIELD_FOR_SOURCE: Quotes must have an author")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, record=record, errors=errors)


def validate_records(
    records: List[StandardRecord],
) -> Tuple[List[StandardRecord], ValidationReport]:
    """Validates a collection of records, segregating valid records from rejected ones.

    Args:
        records: List of StandardRecord instances.

    Returns:
        Tuple of (list_of_valid_records, ValidationReport).
    """
    valid_records: List[StandardRecord] = []
    report = ValidationReport()

    for rec in records:
        result = validate_record(rec)
        report.add_result(result)
        if result.is_valid:
            valid_records.append(rec)

    return valid_records, report
