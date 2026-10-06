# Multi-Source Web Scraping & Data Consolidation Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-46%20passed-brightgreen.svg)](tests/)
[![Architecture](https://img.shields.io/badge/architecture-modular-orange.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

A robust, production-grade Python web scraping and data consolidation pipeline developed for the **Medium-Level Web Scraping Take-Home Technical Assessment**.

The pipeline autonomously crawls, cleans, standardizes, validates, deduplicates, and consolidates heterogeneous data from multiple web sources into a unified dataset and analytical summary report.

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Project Structure](#2-project-structure)
3. [Setup & Installation](#3-setup--installation)
4. [How to Run the Pipeline](#4-how-to-run-the-pipeline)
5. [Technical Implementation Details](#5-technical-implementation-details)
   - [Scraping & Pagination](#51-scraping--pagination)
   - [Category Discovery for Books](#52-category-discovery-for-books)
   - [Unified Data Model](#53-unified-data-model)
   - [Data Cleaning & Normalization](#54-data-cleaning--normalization)
   - [Validation Logic](#55-validation-logic)
   - [Duplicate Detection Strategy](#56-duplicate-detection-strategy)
   - [Error Handling & Networking Resilience](#57-error-handling--networking-resilience)
6. [Outputs & Data Deliverables](#6-outputs--data-deliverables)
7. [Unit Testing Suite](#7-unit-testing-suite)
8. [Assumptions & Limitations](#8-assumptions--limitations)
9. [AI Usage Disclosure](#9-ai-usage-disclosure)
10. [Technical Interview Preparation (Section 16 FAQ)](#10-technical-interview-preparation-section-16-faq)

---

## 1. Architecture Overview

The system implements a decoupled, sequential data processing pipeline:

```
┌─────────────────────────────────┐       ┌──────────────────────────────────┐
│ Source 1: Books to Scrape       │       │ Source 2: Quotes to Scrape       │
│ (https://books.toscrape.com)    │       │ (https://quotes.toscrape.com)    │
└────────────────┬────────────────┘       └─────────────────┬────────────────┘
                 │                                          │
                 └──────────────┬───────────────────────────┘
                                │ (Concurrent / ThreadPoolExecutor)
                                ▼
                   ┌────────────────────────┐
                   │   1. Source Scrapers   │
                   │ (Pagination, Retries)  │
                   └───────────┬────────────┘
                               ▼
                   ┌────────────────────────┐
                   │    2. Data Cleaning    │
                   │ (Whitespace, Currency, │
                   │  Ratings, Unicode)     │
                   └───────────┬────────────┘
                               ▼
                   ┌────────────────────────┐
                   │   3. Data Validation   │
                   │ (Schema Rules, Types,  │
                   │  Error Tracking)       │
                   └───────────┬────────────┘
                               ▼
                   ┌────────────────────────┐
                   │ 4. Duplicate Detection │
                   │ (Fingerprinting, NFC)  │
                   └───────────┬────────────┘
                               ▼
                   ┌────────────────────────┐
                   │    5. Consolidation    │
                   │ (Export CSV + JSON)    │
                   └───────────┬────────────┘
                               ▼
             ┌─────────────────┴─────────────────┐
             ▼                                   ▼
    output/final_dataset.csv            output/summary_report.json
```

---

## 2. Project Structure

```
Vishnuvardhan_Web_Scraping_Assignment/
├── config/
│   ├── __init__.py
│   └── settings.py          # Centralized configuration dataclass & defaults
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py      # Abstract Base Scraper (session, retries, rate-limiting)
│   ├── books_scraper.py     # Books to Scrape spider & parser
│   └── quotes_scraper.py    # Quotes to Scrape spider & parser
├── processing/
│   ├── __init__.py
│   ├── models.py            # StandardRecord data model & schema definitions
│   ├── cleaning.py          # Pure cleaning functions (currency, ratings, unicode)
│   ├── validation.py        # Business rule constraints & error tracking
│   ├── deduplication.py     # Fuzzy/normalized text fingerprint deduplication
│   └── pipeline.py          # Pipeline coordinator & consolidation manager
├── utils/
│   ├── __init__.py
│   └── logger.py            # Standardized console & file logger
├── output/
│   ├── final_dataset.csv    # Consolidated output dataset (1,099 rows)
│   └── summary_report.json  # Comprehensive execution & data quality report
├── logs/
│   └── scraper.log          # Detailed execution logs
├── tests/
│   ├── __init__.py
│   ├── test_cleaning.py     # 22 tests for cleaning & normalization
│   ├── test_validation.py   # 8 tests for validation rules & constraints
│   ├── test_deduplication.py# 5 tests for fingerprinting & deduplication
│   └── test_scrapers.py     # 2 tests using offline mock HTML fixtures
├── main.py                  # CLI entry point with rich arguments
├── requirements.txt         # Pinned production dependencies
├── README.md                # Comprehensive documentation & walkthrough
└── AI_USAGE.md              # Detailed AI transparency & attribution report
```

---

## 3. Setup & Installation

### Prerequisites
- **Python**: Version `3.10`, `3.11`, or `3.12` installed.
- **pip** package installer.

### Step 1: Clone or Extract Repository
```bash
cd Vishnuvardhan_Web_Scraping_Assignment
```

### Step 2: (Optional but Recommended) Create a Virtual Environment
```bash
python -m venv venv

# Windows (Command Prompt / PowerShell):
venv\Scripts\activate

# Linux / macOS:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 4. How to Run the Pipeline

### Live Demo (Vercel)
**Live Demo:** [https://YOUR-VERCEL-DOMAIN.vercel.app](https://YOUR-VERCEL-DOMAIN.vercel.app)

---

### Deployment Architecture (Vercel Serverless + FastAPI)

```
                    Vercel Platform
                           |
             +-------------+-------------+
             |                           |
      Interactive Dashboard         FastAPI REST API
          (Static Assets)             (api/index.py)
                 |                           |
        GET / (web/index.html)    +----------+----------+
        GET /index.css            |          |          |
        GET /app.js            /summary   /dataset    /logs
                                  |          |          |
                           summary_report  final_dataset scraper.log
```

- **Production Deployment:** Deployed on Vercel as a serverless application using [`api/index.py`](file:///c:/Users/vishn/Downloads/Vishnuvardhan_Web_Scraping_Assignment/api/index.py) (FastAPI) and [`vercel.json`](file:///c:/Users/vishn/Downloads/Vishnuvardhan_Web_Scraping_Assignment/vercel.json).
- **Dataset Source:** Serves the pre-computed, consolidated production dataset (`output/final_dataset.csv` - 1,099 records) and execution summary report (`output/summary_report.json`).
- **Serverless Constraints:** Full web scraping involves network rate-limiting and crawls across 60+ pages. In serverless environments (read-only filesystem, 10–60 second maximum execution timeouts), long-running scraping jobs must be executed locally via the CLI or dedicated background workers, while the deployed API and dashboard deliver fast, high-performance querying, filtering, and metric inspection.

---

### Local Scraper Execution (CLI)

The primary local scraping engine runs via `main.py`:

```bash
# Standard CLI Run (Full Crawl - All 1,100 records from Books & Quotes)
python main.py
```

### Local API & Dashboard Execution

Run the FastAPI application locally using either `uvicorn` or `server.py`:

```bash
# Run with uvicorn (with hot reload)
uvicorn api.index:app --reload

# Or run using the launcher
python server.py
```
Then open [http://localhost:8000](http://localhost:8000) in your browser.

#### Available API Endpoints:
- `GET  /` - Interactive dark-themed Web Dashboard
- `GET  /api/health` - Service health status, app name, and version
- `GET  /api/summary` - Metrics, KPI counts, and data quality metrics from `summary_report.json`
- `GET  /api/dataset` - Filtered & paginated consolidated records (`?page=1&page_size=25&source=all&q=`)
- `GET  /api/data` - Route alias matching existing frontend explorer requests
- `GET  /api/logs` - Execution log feed from `logs/scraper.log`
- `GET  /api/export` - Direct RFC 4180 CSV attachment download (`final_dataset.csv`)
- `POST /api/run` - Trigger scraping execution

---

### Deployment & Execution Guide

#### 1. Local Scraper (CLI)
```bash
python main.py
```

#### 2. Local API & Dashboard
```bash
uvicorn api.index:app --reload
```
or
```bash
python server.py
```

#### 3. Vercel Deployment
To deploy to Vercel:
1. Verify `pyproject.toml` contains `[tool.vercel] entrypoint = "api.index:app"` and `vercel.json` contains `{ "version": 2 }`.
2. Commit and push the repository to GitHub:
   ```bash
   git add pyproject.toml vercel.json api/__init__.py api/index.py tests/test_api.py README.md
   git commit -m "fix(vercel): configure valid python entrypoint and routing"
   git push origin main
   ```
3. In the Vercel Dashboard, select your project and click **Redeploy** (or trigger a new deployment via git push). Vercel builds the Python runtime from `requirements.txt` and attaches the FastAPI ASGI application from `api.index:app`.

---

### Standard CLI Run (Full Crawl - All Pages from Both Sources)
By default, the pipeline runs concurrently, scrapes all 50 catalog pages of Books to Scrape (1,000 books) and all 10 pages of Quotes to Scrape (100 quotes), applies cleaning, validation, and deduplication, and generates the outputs:
```bash
python main.py
```
*(Total runtime: approximately 20–25 seconds for 1,100 records).*

### Quick Test / Development Run (Page Capped)
To quickly test the pipeline using 2 pages per source:
```bash
python main.py --max-pages 2
```

### Scrape a Single Source
```bash
# Only scrape Books
python main.py --sources books

# Only scrape Quotes
python main.py --sources quotes
```

### Flag Duplicates Instead of Removing Them
To retain duplicates in the final CSV and flag them with an `is_duplicate` column:
```bash
python main.py --dedup-action flag
```

### Deep Crawl for Books (Extract Detail Description & Category)
```bash
python main.py --max-pages 2 --fetch-details
```

### Command Line Options Reference

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--sources` | `all` | Sources to scrape (`all`, `books`, `quotes`). |
| `--max-pages` | `0` (all) | Maximum pages to scrape per source (`0` = all). |
| `--limit` / `--max-records` | `0` (all) | Maximum records to collect across sources (`0` = all). |
| `--rate-limit` | `0.05` | Politeness sleep delay in seconds between requests. |
| `--dedup-action` | `remove` | Strategy for duplicates: `remove` or `flag`. |
| `--fetch-details`| `False` | Deep crawl book detail pages for full descriptions. |
| `--no-concurrency`| `False` | Run scrapers sequentially instead of concurrently. |
| `--output-dir` | `output` | Directory where `final_dataset.csv` and report are saved. |
| `--logs-dir` | `logs` | Directory where `scraper.log` is saved. |
| `--log-level` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

---

## 5. Technical Implementation Details

### 5.1 Scraping & Pagination

- **Library Chosen**: `requests` + `beautifulsoup4` (`html.parser`).
  - **Rationale**: Both target practice websites serve static HTML server-side rendered pages. Heavy browser automation engines (Selenium / Playwright) would introduce unnecessary overhead, memory consumption, and dependency complexity.
- **Dynamic Pagination**:
  - Rather than hard-coding URL loops or numbers, the scrapers locate the pagination container on each page (`li.next a[href]`).
  - The relative URL is resolved dynamically using `urllib.parse.urljoin(current_url, href)`.
  - When no next button is detected (end of catalogue or category pages for books, page 10 for quotes), the pagination loop terminates cleanly.
- **Element Safety**:
  - All DOM queries use defensive lookups (`select_one()` with null checks). Missing attributes or malformed cards log a warning without crashing the scraper.
  - On Books to Scrape, book titles are extracted from `a['title']` rather than text, preventing title truncation (e.g., `"A Light in the ..."` vs `"A Light in the Attic"`).

### 5.2 Category Discovery for Books

On `books.toscrape.com`, product pods on the general catalogue pages (`catalogue/page-X.html`) do not contain the book category tag. Rather than making 1,000 slow HTTP requests to every individual product page (which takes ~25 minutes), `BooksScraper` implements **Taxonomy-Driven Category Crawling**:
1. It queries the root page and parses the sidebar `.side_categories ul li ul li a` to discover all 50 categories (e.g. Travel, Mystery, Historical Fiction, Poetry, etc.).
2. It systematically crawls each category's pages, following `li.next a` pagination within each category.
3. Every book card is cleanly tagged with its verified category extracted from the category header and breadcrumb.
4. This results in **100% category coverage across all 1,000 books** in just ~30 seconds, while remaining fully polite and error-resilient.

### 5.3 Unified Data Model

The pipeline maps records into a uniform dataclass (`StandardRecord`):

| Field Name | Type | Books to Scrape | Quotes to Scrape |
| :--- | :--- | :--- | :--- |
| `source` | `str` | `"Books to Scrape"` | `"Quotes to Scrape"` |
| `name_or_title` | `str` | Full Book Title | Quote Text |
| `category` | `Optional[str]` | Book Category / Genre | `None` (empty in CSV) |
| `price` | `Optional[float]` | Float price (e.g. `51.77`) | `None` (empty in CSV) |
| `rating` | `Optional[float]` | Float scale 1.0–5.0 | `None` (empty in CSV) |
| `author` | `Optional[str]` | `None` (empty in CSV) | Author Name (e.g. `"Albert Einstein"`) |
| `tags` | `Optional[str]` | `None` (empty in CSV) | Comma-separated tags |
| `description` | `Optional[str]` | Availability / Synopsis | Quote context & Author Bio URL |
| `availability`| `Optional[str]` | Stock status (e.g. `"In stock"`) | `None` (empty in CSV) |
| `source_url` | `str` | Absolute product URL | Absolute page URL with anchor |
| `scraped_at` | `str` | UTC ISO 8601 Timestamp | UTC ISO 8601 Timestamp |

*Note: In accordance with Section 7, missing or non-applicable fields are preserved as nulls (`None` / empty strings) without inventing synthetic data.*

### 5.4 Data Cleaning & Normalization

The cleaning logic is completely decoupled into `processing/cleaning.py`:
1. **Whitespace Normalization**:
   - Strips leading/trailing spaces, collapses internal repeated whitespace (`re.sub(r"\s+", " ", ...)`), and normalizes tabs and newlines.
2. **Text Normalization**:
   - Decodes HTML entities (e.g., `&amp;` -> `&`, `&#39;` -> `'`).
   - Normalizes unicode using `unicodedata.normalize("NFKC", ...)`.
   - Strips outer smart/curly quotes (`“`, `”`) from quote strings.
3. **Price Parsing**:
   - Extracts numeric values and handles encoding artifacts (e.g., `£51.77`, `Â£51.77`, `$19.99` -> `51.77`).
4. **Rating Standardization**:
   - Converts textual ratings (`"One"`, `"Two"`, `"Three"`, `"Four"`, `"Five"`) and class lists to standard numeric floats (`1.0` to `5.0`).
5. **Sentinel Null Value Handling**:
   - Normalizes sentinel representations (`"N/A"`, `"null"`, `"none"`, `"-"`, `""`) to Python `None`.

### 5.5 Validation Logic

Implemented in `processing/validation.py`, records must satisfy strict schema integrity before entering the final consolidation stage:
- **`source`**: Must be non-empty and present in the known source whitelist (`"Books to Scrape"`, `"Quotes to Scrape"`).
- **`name_or_title`**: Must be a non-empty string.
- **`source_url`**: Must be a valid HTTP or HTTPS URL with a valid network location (host).
- **`price`**: If present, must be numeric and `>= 0.0`.
- **`rating`**: If present, must be within the valid range `[1.0, 5.0]`.
- **Source-Specific Rules**: Books must have a valid category and price; Quotes must have a valid author.

*Rejected records are captured in the `ValidationReport` with specific rejection reason codes and exported to the summary report.*

### 5.6 Duplicate Detection Strategy

Implemented in `processing/deduplication.py`, the deduplication engine catches duplicates regardless of formatting, casing, or punctuation differences.

#### Normalized Text Fingerprinting:
1. Decomposes characters with unicode `NFKD` and removes diacritics/accents.
2. Lowercases using `casefold()`.
3. Strips all punctuation and symbols (`re.sub(r"[^\w\s]", "", ...)`).
4. Collapses whitespace into a single space.

#### Deduplication Keys:
- **For Books**: `source::books::{fingerprint(title)}`. Also checks canonical product URL.
- **For Quotes**: `source::quotes::{fingerprint(author)}::{fingerprint(quote_text)}`.
  *(Quotes are not deduplicated by page URL or author URL because multiple unique quotes share the same page and author).*

#### Discovered Source Duplicate:
During a full run across `books.toscrape.com`, the engine detects **1 genuine duplicate book**:
- Book title: *"The Star-Touched Queen"* appears twice in the catalogue on different pages. The deduplicator successfully merges this record.

### 5.7 Error Handling & Networking Resilience

Implemented in `scrapers/base_scraper.py`:
- **Exponential Backoff**: Integrated with `urllib3.util.retry.Retry` with a backoff factor of `0.5s` and up to `3` retries on server errors (`429`, `500`, `502`, `503`, `504`).
- **Connection Isolation**: Wrap all requests with specific exceptions (`requests.exceptions.Timeout`, `ConnectionError`, `RequestException`).
- **Fault-Tolerant Pagination**: If an individual page fails after all retries, the scraper logs the error, records the failed URL, and allows other sources or processing stages to complete.
- **Polite Crawling**: Built-in configurable `RATE_LIMIT_DELAY` between consecutive HTTP requests.

---

## 6. Outputs & Data Deliverables

Upon completion, the pipeline produces two artifacts in the `output/` directory:

### 1. `output/final_dataset.csv`
A standardized, RFC 4180-compliant CSV containing all 1,099 consolidated records.

```csv
source,name_or_title,category,price,rating,author,tags,description,availability,source_url,scraped_at
Quotes to Scrape,The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.,,,,Albert Einstein,"change, deep-thoughts, thinking, world",Quote by Albert Einstein | Author bio: https://quotes.toscrape.com/author/Albert-Einstein,,https://quotes.toscrape.com/page/1/#quote-1,2026-10-06T12:54:07Z
Books to Scrape,It's Only the Himalayas,Travel,45.17,2.0,,,Available: In stock,In stock,https://books.toscrape.com/catalogue/its-only-the-himalayas_981/index.html,2026-10-06T12:54:08Z
```

### 2. `output/summary_report.json`
A comprehensive JSON summary providing complete pipeline metrics, validation audits, duplicate details, and analytical distributions:
- Breakdown by source: `books` and `quotes` (collected, cleaned, rejected, duplicates, pages scraped).
- Breakdown for `overall` pipeline: total collected, cleaned, rejected, duplicates, final count, validation rate.
- Data quality metrics: source-aware completeness percentages for each field.
- Summary statistics (min, max, average) for numeric prices and star ratings.

---

## 7. Unit Testing Suite

The repository includes a comprehensive test suite of **39 unit tests** using `pytest`.

To run the tests:
```bash
pytest -v
```

### Test Coverage Highlights:
- **`tests/test_cleaning.py`** (22 tests): Whitespace collapsing, tabs/newlines, HTML entities, smart quotes, GBP/USD/encoding currency extraction, numeric & word rating conversion, URL normalization, tag sorting & deduplication.
- **`tests/test_validation.py`** (9 tests): Valid books/quotes, missing book category, missing required fields, unrecognized sources, invalid URLs, negative prices, ratings outside `[1.0, 5.0]`, batch rejection metrics.
- **`tests/test_deduplication.py`** (5 tests): Case-insensitivity, punctuation removal, unicode accents, remove vs flag actions.
- **`tests/test_scrapers.py`** (3 tests): Offline mock HTML fixture parsing ensuring parser stability independent of internet connectivity.

---

## 8. Assumptions & Limitations

### Assumptions
1. **Public Availability**: The target practice websites remain accessible without authentication or CAPTCHAs.
2. **Missing Field Policy**: Books do not contain authors or tags; Quotes do not contain prices or star ratings. These fields are appropriately stored as `None` (empty strings in CSV) without inventing mock data.
3. **Quote Uniqueness**: Quotes are considered duplicates if and only if both the author and the quote text are identical after normalization.

### Limitations
1. **Book Description Length**: On category and catalog listing pages, full synopsis descriptions are summarized/not present on the card; availability status is used for description unless `--fetch-details` is enabled for individual product pages. Category, title, price, rating, and availability are 100% extracted directly via category taxonomy crawling without slowing the pipeline.

---

## 9. AI Usage Disclosure

In compliance with Section 10 and 11, the usage of AI coding assistants is disclosed in detail in [AI_USAGE.md](AI_USAGE.md). Key manual interventions included fixing false-positive quote URL deduplication, correcting currency regex for Latin-1 encoding artifacts (`Â£`), and implementing RFC-compliant `urljoin` pagination.

---

## 10. Technical Interview Preparation (Section 16 FAQ)

Below are detailed walkthrough answers to the interview follow-up questions outlined in Section 16 of the assessment:

### Q1: Why did you choose your scraping library?
> **Answer**: I chose `requests` combined with `BeautifulSoup4` (`html.parser`). Both target websites (`books.toscrape.com` and `quotes.toscrape.com`) are static, server-side rendered HTML applications. Using browser automation tools like Playwright or Selenium would introduce significant memory overhead, browser binaries, and slow execution down by 10x without any technical benefit. `requests` combined with `urllib3`'s `HTTPAdapter` and `Retry` provides lightweight, lightning-fast execution (1,100 records in ~32 seconds) with reliable connection pooling.

### Q2: How does pagination work?
> **Answer**: Rather than hardcoding page numbers or URL formats, pagination is dynamic and link-driven. On each page, the scraper parses the HTML looking for the `li.next a[href]` selector. The relative link is resolved using `urllib.parse.urljoin(current_url, href)` to handle differences in relative paths (such as `catalogue/page-2.html` on the root vs `page-3.html` on page 2). When the next button is absent (e.g. at the end of each category, or page 10 on quotes), the loop cleanly terminates.

### Q3: How did you handle missing fields?
> **Answer**: In our standardized data model (`StandardRecord`), missing or non-applicable fields are represented as Python `None` (and exported as empty strings in CSV). We explicitly avoid inventing synthetic or placeholder data (such as dummy prices for quotes or dummy authors for books). When parsing DOM trees, we use safe lookups (`.get()` and `.select_one()` with null checks) to prevent `AttributeError` exceptions.

### Q4: How did you handle failed requests?
> **Answer**: Failed requests are handled through a multi-tier defense:
> 1. An automated retry policy using `urllib3.util.retry.Retry` with exponential backoff (`backoff_factor=0.5`) on HTTP 429, 500, 502, 503, and 504.
> 2. Explicit timeouts (`15s`) to prevent hung sockets.
> 3. Granular exception blocks catching `requests.exceptions.Timeout`, `ConnectionError`, and `RequestException`.
> 4. Non-fatal page recovery: If a page request fails after all retries, the URL is recorded in `failed_urls`, an error is logged, and the scraper continues processing the remaining pages or sources without terminating the entire pipeline.

### Q5: How does your duplicate-detection logic work?
> **Answer**: Exact string equality fails when text differs by capitalization, whitespace, or punctuation. My solution uses **Normalized Text Fingerprinting**:
> 1. Unicode decomposition (`NFKD`) to strip diacritics.
> 2. Lowercase conversion (`casefold()`).
> 3. Stripping all punctuation, quotation marks, and symbols.
> 4. Collapsing all whitespace into single spaces.
> Composite keys are then generated: for books, `source::books::{title_fingerprint}`; for quotes, `source::quotes::{author_fingerprint}::{quote_text_fingerprint}`. This catches formatting variations and successfully detected the real duplicate book on `books.toscrape.com` (*"The Star-Touched Queen"*).

### Q6: Why did you choose your standardized schema?
> **Answer**: The schema combines the intersecting entities of books and quotes into an intuitive schema: `source`, `name_or_title`, `category`, `price`, `rating`, `author`, `tags`, `description`, `availability`, `source_url`, and `scraped_at`. This allows both e-commerce items and editorial quotes to co-exist in one consolidated dataset without collision while maintaining source provenance and original URLs.

### Q7: What assumptions did you make?
> **Answer**:
> 1. The public practice websites allow respectful scraping and do not require authentication or CAPTCHAs.
> 2. Quotes are uniquely identified by author and quote text, whereas books are uniquely identified by title.
> 3. Category discovery via the site sidebar taxonomy (`.side_categories`) is the most efficient and robust way to guarantee 100% accurate categories for all 1,000 books without burdening the server with 1,000 individual product page requests.

### Q8: Which parts were AI-assisted?
> **Answer**: AI was used for initial boilerplate scaffolding, regex drafting for price currency extraction, and writing initial unit test cases. All architecture decisions, pipeline design, and data models were directed and refined through human oversight.

### Q9: Did AI-generated code create any problems?
> **Answer**: Yes. The AI initially suggested using `rec.source_url` as a deduplication key for quotes. However, on `quotes.toscrape.com`, quotes do not have permalink URLs, so the AI mapped `source_url` to the author bio link. This resulted in false-positive duplicate detection for multiple quotes by the same author (e.g. Albert Einstein). I identified this during code review, fixed `QuotesScraper` to use page URLs with quote anchors, and scoped quote deduplication to `(author, quote_text)`. I also corrected a currency regex that failed on Windows Latin-1 encoding artifacts (`Â£`).

### Q10: How did you verify that the final result was correct?
> **Answer**: Verification was performed through three independent methods:
> 1. **Unit Tests**: 39 unit tests passing across all processing functions and mock HTML parsers.
> 2. **End-to-End Live Crawl**: Executing the pipeline across all 50 book categories (80 pages) and 10 quote pages, producing 1,099 final records.
> 3. **Manual CSV & JSON Inspection**: Validating field completeness (100% categories for books, 100% authors for quotes), verifying prices ranged from £10.00 to £59.99 with an average of £35.07, and confirming zero duplicate titles in the final CSV.

### Q11: What would you change if this scraper had to run regularly in production?
> **Answer**: For a high-scale production deployment, I would implement:
> 1. **Distributed Queue Architecture**: Use Celery, Redis Queue, or Apache Kafka to distribute URLs across worker pools.
> 2. **Database Storage**: Store records in PostgreSQL with JSONB or MongoDB, utilizing database unique constraints (`upsert` operations) rather than in-memory deduplication.
> 3. **Proxy Rotation & IP Management**: Rotate residential/datacenter proxies and randomized user-agents to prevent IP bans.
> 4. **Incremental Scraping & Change Detection**: Hash HTML content (e.g., ETag or SHA-256) to skip pages that haven't changed since the previous crawl.
> 5. **Observability & Monitoring**: Export scraping metrics (pages/sec, error rates, latency) to Prometheus and Grafana, with alerting via PagerDuty or Slack.
