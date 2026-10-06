"""
Main CLI Entry Point for Multi-Source Web Scraping & Data Consolidation Pipeline.
"""
import argparse
import logging
from pathlib import Path
import sys

from config.settings import Config, DEFAULT_CONFIG
from processing.pipeline import ScrapingPipeline
from utils.logger import setup_logger


def parse_arguments() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="Multi-Source Web Scraping & Data Consolidation Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--sources",
        nargs="+",
        default=["all"],
        choices=["all", "books", "quotes"],
        help="Target data sources to scrape (default: all).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Maximum pages to scrape per source (0 or omitted = scrape all available pages).",
    )
    parser.add_argument(
        "--limit",
        "--max-records",
        dest="limit",
        type=int,
        default=0,
        help="Maximum records to scrape per source (0 or omitted = scrape all available records).",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.05,
        help="Politeness delay in seconds between HTTP page requests.",
    )
    parser.add_argument(
        "--dedup-action",
        choices=["remove", "flag"],
        default="remove",
        help="Deduplication strategy: 'remove' drops duplicates, 'flag' marks is_duplicate=True.",
    )
    parser.add_argument(
        "--fetch-details",
        action="store_true",
        default=False,
        help="Fetch detail pages for Books to extract category and full description (deep crawl).",
    )
    parser.add_argument(
        "--no-concurrency",
        action="store_true",
        default=False,
        help="Disable concurrent execution of multi-source scrapers and run sequentially.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save final dataset and summary report.",
    )
    parser.add_argument(
        "--logs-dir",
        type=str,
        default="logs",
        help="Directory to save execution log files.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity level.",
    )

    return parser.parse_args()


def main() -> int:
    """Entry point execution function."""
    args = parse_arguments()

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger = setup_logger(
        name="web_scraping_pipeline",
        log_dir=Path(args.logs_dir),
        log_file="scraper.log",
        level=log_level,
    )

    config = Config(
        RATE_LIMIT_DELAY=args.rate_limit,
        MAX_PAGES=args.max_pages,
        MAX_RECORDS=args.limit if args.limit > 0 else None,
        FETCH_BOOK_DETAILS=args.fetch_details,
        DEDUP_ACTION=args.dedup_action,
        OUTPUT_DIR=Path(args.output_dir),
        LOGS_DIR=Path(args.logs_dir),
    )

    logger.info("Initializing Scraping Pipeline with CLI arguments...")
    logger.info(f"Sources: {args.sources} | Max Pages: {args.max_pages or 'ALL'} | Record Limit: {args.limit or 'ALL'}")
    logger.info(f"Deduplication Action: {args.dedup_action} | Concurrency: {not args.no_concurrency}")

    try:
        pipeline = ScrapingPipeline(config=config, logger=logger)
        summary = pipeline.run(
            sources=args.sources,
            max_pages=args.max_pages if args.max_pages > 0 else None,
            max_records=args.limit if args.limit > 0 else None,
            dedup_action=args.dedup_action,
            use_concurrency=not args.no_concurrency,
        )

        final_count = summary.get("final_dataset", {}).get("final_record_count", 0)
        logger.info(f"Pipeline executed successfully. Total final records: {final_count}")
        return 0

    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user.")
        return 130
    except Exception as e:
        logger.critical(f"Pipeline fatal failure: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
