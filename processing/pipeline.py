"""
Pipeline Orchestration Module.
Coordinates the end-to-end execution:
Scraping -> Cleaning -> Validation -> Deduplication -> Consolidation -> Reports.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from config.settings import DEFAULT_CONFIG, Config
from processing.cleaning import clean_raw_record
from processing.deduplication import deduplicate_records, DeduplicationReport
from processing.models import StandardRecord
from processing.validation import validate_records, ValidationReport
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper


class ScrapingPipeline:
    """Manages the full lifecycle of data collection, processing, and export."""

    def __init__(
        self,
        config: Optional[Config] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config or DEFAULT_CONFIG
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.config.ensure_directories()

    def run(
        self,
        sources: Optional[List[str]] = None,
        max_pages: Optional[int] = None,
        max_records: Optional[int] = None,
        dedup_action: Optional[str] = None,
        use_concurrency: bool = True,
    ) -> Dict[str, Any]:
        """Executes the end-to-end pipeline.

        Args:
            sources: List of sources to scrape ('books', 'quotes', or both).
            max_pages: Optional maximum page limit per source.
            max_records: Optional maximum records limit per source.
            dedup_action: 'remove' or 'flag' for duplicate handling.
            use_concurrency: Whether to scrape sources in parallel threads.

        Returns:
            Dictionary containing the summary report metrics.
        """
        start_time = time.time()
        self.logger.info("=" * 60)
        self.logger.info("STARTING MULTI-SOURCE WEB SCRAPING & DATA CONSOLIDATION PIPELINE")
        self.logger.info("=" * 60)

        # Normalize sources
        if not sources or "all" in [s.lower() for s in sources]:
            selected_sources = ["books", "quotes"]
        else:
            selected_sources = [s.lower() for s in sources]

        action = dedup_action or self.config.DEDUP_ACTION
        rec_limit = max_records if max_records is not None else self.config.MAX_RECORDS

        # -------------------------------------------------------------
        # STEP 1: SCRAPING
        # -------------------------------------------------------------
        self.logger.info("[Step 1/5] Initiating Scraping Phase...")
        raw_records: List[Dict[str, Any]] = []
        source_scrape_stats: Dict[str, Dict[str, Any]] = {}

        scrapers = {}
        if "books" in selected_sources:
            scrapers["Books to Scrape"] = BooksScraper(
                config=self.config,
                logger=self.logger,
                fetch_details=self.config.FETCH_BOOK_DETAILS,
            )
        if "quotes" in selected_sources:
            scrapers["Quotes to Scrape"] = QuotesScraper(
                config=self.config,
                logger=self.logger,
            )

        actual_concurrency = use_concurrency and len(scrapers) > 1
        exec_mode = (
            f"Concurrent ThreadPoolExecutor ({len(scrapers)} workers)"
            if actual_concurrency
            else "Sequential Execution"
        )

        if actual_concurrency:
            self.logger.info(f"Scraping {len(scrapers)} sources concurrently with ThreadPoolExecutor...")
            with ThreadPoolExecutor(max_workers=len(scrapers)) as executor:
                future_to_src = {
                    executor.submit(scraper.scrape, max_pages, rec_limit): name
                    for name, scraper in scrapers.items()
                }
                for future in as_completed(future_to_src):
                    src_name = future_to_src[future]
                    scraper_instance = scrapers[src_name]
                    try:
                        data = future.result()
                        raw_records.extend(data)
                        source_scrape_stats[src_name] = {
                            "records_collected": len(data),
                            "pages_scraped": scraper_instance.pages_scraped,
                            "failed_requests": len(scraper_instance.failed_urls),
                        }
                    except Exception as e:
                        self.logger.error(f"Error executing scraper for {src_name}: {e}", exc_info=True)
                        source_scrape_stats[src_name] = {
                            "records_collected": 0,
                            "pages_scraped": scraper_instance.pages_scraped,
                            "failed_requests": len(scraper_instance.failed_urls) + 1,
                            "error": str(e),
                        }
        else:
            for src_name, scraper in scrapers.items():
                self.logger.info(f"Running scraper sequentially: {src_name}")
                data = scraper.scrape(max_pages=max_pages, max_records=rec_limit)
                raw_records.extend(data)
                source_scrape_stats[src_name] = {
                    "records_collected": len(data),
                    "pages_scraped": scraper.pages_scraped,
                    "failed_requests": len(scraper.failed_urls),
                }

        self.logger.info(f"Scraping completed. Total raw records gathered: {len(raw_records)}")

        # -------------------------------------------------------------
        # STEP 2: DATA CLEANING & STANDARDIZATION
        # -------------------------------------------------------------
        self.logger.info("[Step 2/5] Cleaning and Standardizing Records...")
        cleaned_records: List[StandardRecord] = []
        for raw in raw_records:
            try:
                rec = clean_raw_record(raw)
                cleaned_records.append(rec)
            except Exception as e:
                self.logger.warning(f"Error cleaning raw record: {raw}. Reason: {e}")

        self.logger.info(f"Data cleaning completed. Cleaned {len(cleaned_records)} records.")

        # -------------------------------------------------------------
        # STEP 3: DATA VALIDATION
        # -------------------------------------------------------------
        self.logger.info("[Step 3/5] Validating Cleaned Records Against Constraints...")
        valid_records, validation_report = validate_records(cleaned_records)
        self.logger.info(
            f"Validation completed. Valid: {validation_report.total_valid}, "
            f"Rejected: {validation_report.total_rejected}, "
            f"Validation Rate: {validation_report.validation_rate}%"
        )
        if validation_report.total_rejected > 0:
            self.logger.warning(f"Validation Rejection Summary: {validation_report.rejection_reasons}")

        # -------------------------------------------------------------
        # STEP 4: DUPLICATE DETECTION & RESOLUTION
        # -------------------------------------------------------------
        self.logger.info(f"[Step 4/5] Executing Deduplication (Strategy: {action})...")
        deduped_records, dedup_report = deduplicate_records(valid_records, action=action)
        self.logger.info(
            f"Deduplication completed. Input: {dedup_report.total_input}, "
            f"Duplicates Identified: {dedup_report.duplicates_count}, "
            f"Unique Retained: {dedup_report.unique_count}"
        )

        # -------------------------------------------------------------
        # STEP 5: CONSOLIDATION & OUTPUT GENERATION
        # -------------------------------------------------------------
        self.logger.info("[Step 5/5] Consolidating and Exporting Outputs...")
        csv_path = self.config.OUTPUT_DIR / self.config.FINAL_CSV_FILENAME
        json_path = self.config.OUTPUT_DIR / self.config.SUMMARY_JSON_FILENAME

        self._export_to_csv(deduped_records, csv_path, include_dup_flag=(action == "flag"))

        execution_duration = round(time.time() - start_time, 2)

        # Per-source breakdowns for Section 16 compliance
        books_raw_cnt = source_scrape_stats.get("Books to Scrape", {}).get("records_collected", 0)
        quotes_raw_cnt = source_scrape_stats.get("Quotes to Scrape", {}).get("records_collected", 0)

        books_cleaned_cnt = sum(1 for r in cleaned_records if r.source == "Books to Scrape")
        quotes_cleaned_cnt = sum(1 for r in cleaned_records if r.source == "Quotes to Scrape")

        books_valid_cnt = sum(1 for r in valid_records if r.source == "Books to Scrape")
        quotes_valid_cnt = sum(1 for r in valid_records if r.source == "Quotes to Scrape")

        books_rejected_cnt = books_cleaned_cnt - books_valid_cnt
        quotes_rejected_cnt = quotes_cleaned_cnt - quotes_valid_cnt

        books_duplicates_cnt = dedup_report.duplicates_by_source.get("Books to Scrape", 0)
        quotes_duplicates_cnt = dedup_report.duplicates_by_source.get("Quotes to Scrape", 0)

        books_final_cnt = sum(1 for r in deduped_records if r.source == "Books to Scrape")
        quotes_final_cnt = sum(1 for r in deduped_records if r.source == "Quotes to Scrape")

        summary_data = {
            "execution_time_seconds": execution_duration,
            "execution_mode": exec_mode,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sources_scraped": list(source_scrape_stats.keys()),
            "deduplication_mode": action,
            "books": {
                "records_collected": books_raw_cnt,
                "records_cleaned": books_cleaned_cnt,
                "records_rejected": books_rejected_cnt,
                "duplicates": books_duplicates_cnt,
                "final_records": books_final_cnt,
                "pages_scraped": source_scrape_stats.get("Books to Scrape", {}).get("pages_scraped", 0),
            },
            "quotes": {
                "records_collected": quotes_raw_cnt,
                "records_cleaned": quotes_cleaned_cnt,
                "records_rejected": quotes_rejected_cnt,
                "duplicates": quotes_duplicates_cnt,
                "final_records": quotes_final_cnt,
                "pages_scraped": source_scrape_stats.get("Quotes to Scrape", {}).get("pages_scraped", 0),
            },
            "overall": {
                "total_records_collected": len(raw_records),
                "total_records_cleaned": len(cleaned_records),
                "total_records_rejected": validation_report.total_rejected,
                "total_duplicates": dedup_report.duplicates_count,
                "final_record_count": len(deduped_records),
                "validation_rate": validation_report.validation_rate,
            },
            "validation_details": {
                "total_inspected": validation_report.total_inspected,
                "rejection_reasons": validation_report.rejection_reasons,
                "sample_rejected_records": validation_report.rejected_records[:5],
            },
            "final_dataset": {
                "final_record_count": len(deduped_records),
                "output_csv_file": str(csv_path.resolve()),
                "summary_json_file": str(json_path.resolve()),
            },
            "data_quality_metrics": self._calculate_quality_metrics(deduped_records),
        }

        self._export_to_json(summary_data, json_path)

        self.logger.info("=" * 60)
        self.logger.info(f"PIPELINE COMPLETE in {execution_duration}s")
        self.logger.info(f"Final Dataset: {csv_path} ({len(deduped_records)} rows)")
        self.logger.info(f"Summary Report: {json_path}")
        self.logger.info("=" * 60)

        return summary_data

    def _export_to_csv(
        self, records: List[StandardRecord], output_path: Path, include_dup_flag: bool = False
    ) -> None:
        """Writes standardized records to CSV file using standard field order."""
        field_names = StandardRecord.get_field_names(include_duplicate_flag=include_dup_flag)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=field_names, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for rec in records:
                row = rec.to_dict()
                if not include_dup_flag and "is_duplicate" in row:
                    row.pop("is_duplicate", None)
                writer.writerow(row)

    def _export_to_json(self, data: Dict[str, Any], output_path: Path) -> None:
        """Writes summary report to formatted JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, mode="w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _calculate_quality_metrics(self, records: List[StandardRecord]) -> Dict[str, Any]:
        """Calculates source-aware completeness and statistical distributions."""
        if not records:
            return {}

        total = len(records)
        books_records = [r for r in records if r.source == "Books to Scrape"]
        quotes_records = [r for r in records if r.source == "Quotes to Scrape"]

        total_books = len(books_records)
        total_quotes = len(quotes_records)

        # Source-aware field completeness
        books_completeness = {}
        if total_books > 0:
            books_completeness = {
                "name_or_title": round((sum(1 for r in books_records if r.name_or_title) / total_books) * 100, 1),
                "source_url": round((sum(1 for r in books_records if r.source_url) / total_books) * 100, 1),
                "category": round((sum(1 for r in books_records if r.category) / total_books) * 100, 1),
                "price": round((sum(1 for r in books_records if r.price is not None) / total_books) * 100, 1),
                "rating": round((sum(1 for r in books_records if r.rating is not None) / total_books) * 100, 1),
                "availability": round((sum(1 for r in books_records if r.availability) / total_books) * 100, 1),
                "description": round((sum(1 for r in books_records if r.description) / total_books) * 100, 1),
                "author": "N/A",
                "tags": "N/A",
            }

        quotes_completeness = {}
        if total_quotes > 0:
            quotes_completeness = {
                "name_or_title": round((sum(1 for r in quotes_records if r.name_or_title) / total_quotes) * 100, 1),
                "source_url": round((sum(1 for r in quotes_records if r.source_url) / total_quotes) * 100, 1),
                "author": round((sum(1 for r in quotes_records if r.author) / total_quotes) * 100, 1),
                "tags": round((sum(1 for r in quotes_records if r.tags) / total_quotes) * 100, 1),
                "description": round((sum(1 for r in quotes_records if r.description) / total_quotes) * 100, 1),
                "category": "N/A",
                "price": "N/A",
                "rating": "N/A",
                "availability": "N/A",
            }

        # Pricing stats for items with price (Books)
        prices = [r.price for r in records if r.price is not None]
        price_stats = {}
        if prices:
            price_stats = {
                "count": len(prices),
                "min": min(prices),
                "max": max(prices),
                "avg": round(sum(prices) / len(prices), 2),
            }

        # Rating stats for items with rating (Books)
        ratings = [r.rating for r in records if r.rating is not None]
        rating_stats = {}
        if ratings:
            rating_stats = {
                "count": len(ratings),
                "min": min(ratings),
                "max": max(ratings),
                "avg": round(sum(ratings) / len(ratings), 2),
            }

        return {
            "total_records": total,
            "source_aware_completeness": {
                "books": books_completeness,
                "quotes": quotes_completeness,
            },
            "numeric_price_statistics": price_stats,
            "numeric_rating_statistics": rating_stats,
        }
