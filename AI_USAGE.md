# AI Usage and Attribution Statement

This document details the usage of Artificial Intelligence assistants during the planning, implementation, debugging, and verification of the **Multi-Source Web Scraping & Data Consolidation Pipeline**, in accordance with Section 10 and 11 of the assessment guidelines.

---

## 1. AI Tools Used

| Tool | Version / Engine | Primary Focus |
| :--- | :--- | :--- |
| **Google Antigravity / Gemini 3.8 Flash** | Gemini 3.8 Flash Engine | Architecture design, pipeline orchestration, cleaning regex logic, unit tests, and documentation. |

---

## 2. What Each Tool Was Used For

1. **Architecture & Project Scaffolding:**
   - Drafting the modular folder structure (`scrapers/`, `processing/`, `config/`, `tests/`, `utils/`).
   - Defining the common consolidated schema (`StandardRecord`) covering both Books and Quotes without schema collision.

2. **Scraper & Pagination Architecture:**
   - Developing resilient session configuration with `urllib3`'s `Retry` strategy (status code handling, backoff factor, connection pooling).
   - Formulating dynamic pagination via relative `urljoin` parsing for `li.next a` across both websites.

3. **Data Cleaning & Deduplication:**
   - Designing regex extraction for price conversion (stripping `£`, `Â£`, `$`).
   - Constructing normalized text fingerprints (`NFKD` decomposition, lowercase casefold, punctuation removal) to catch variations in whitespace, casing, and punctuation.

4. **Testing Suite:**
   - Generating comprehensive unit test cases (`pytest`) covering whitespace normalization, price parsing, rating conversions, schema validation constraints, and deduplication logic with mock HTML fixtures.

---

## 3. Representative Prompts Used

### Prompt 1: Resilient Base Scraper Architecture
> *"Draft an abstract BaseScraper class in Python using requests.Session that implements exponential backoff retries with urllib3.util.retry.Retry, custom User-Agent, politeness rate-limiting, and error-safe pagination following HTML next-page links."*

### Prompt 2: Data Cleaning and Normalization Functions
> *"Create modular data cleaning functions for a web scraping pipeline: whitespace normalization, currency price extraction that safely handles unicode Latin-1 artifacts like Â£, textual ratings conversion ('One'..'Five' -> 1.0..5.0), and quote smart-quote trimming."*

### Prompt 3: Fuzzy Duplicate Detection Strategy
> *"Design a duplicate detection module in Python that generates an alphanumeric normalized fingerprint for book titles and quote texts to detect duplicates despite differences in whitespace, capitalization, punctuation, and curly quotation marks. Support both 'remove' and 'flag' actions."*

### Prompt 4: Unit Testing Mock Fixtures
> *"Generate a suite of pytest tests for the scraping, cleaning, validation, and deduplication modules. Include isolated unit tests using mock HTML fixtures for Books to Scrape and Quotes to Scrape so tests do not rely on network access."*

---

## 4. Which Parts of the Code Were AI-Assisted

- **`config/settings.py`**: Initial schema and dataclass structure.
- **`scrapers/base_scraper.py`**: Networking boilerplate and retry adapter configuration.
- **`scrapers/books_scraper.py` & `scrapers/quotes_scraper.py`**: BeautifulSoup parsing selectors.
- **`processing/cleaning.py`**: Regex patterns for currency extraction and unicode handling.
- **`processing/deduplication.py`**: Initial text fingerprinting algorithm.
- **`tests/test_*.py`**: Test case generation across edge cases.

---

## 5. Important Changes & Corrections Made After Reviewing AI Output

During implementation and manual verification, several key edge cases and potential bugs in AI-generated code were identified and corrected:

### 1. Quotes URL Collision in Deduplication (Critical Fix)
- **AI Suggestion**: The initial AI-generated duplicate detection used `rec.source_url` as a secondary deduplication key.
- **Flaw Discovered**: On `quotes.toscrape.com`, individual quotes do not have their own detail pages; the AI originally mapped `source_url` to the author's biography link (`/author/Albert-Einstein`). Because Albert Einstein authored multiple quotes on the same page, the second quote was mistakenly flagged as a duplicate of the first quote simply because they shared the author URL.
- **Correction Applied**: Updated `QuotesScraper` to assign `source_url` to the canonical page URL with an anchor (`https://quotes.toscrape.com/page/1/#quote-1`) and stored the author biography link in `description`. Furthermore, adjusted the deduplication key for quotes to strictly evaluate `(source, author_fingerprint, quote_text_fingerprint)`, eliminating false-positive duplicates.

### 2. Character Encoding Artifact (`Â£51.77`)
- **AI Suggestion**: Initial regex only looked for `£\d+\.\d+`.
- **Flaw Discovered**: In certain Windows shells or HTTP decodings, the British pound symbol `£` on `books.toscrape.com` can decode as `Â£` (Latin-1 vs UTF-8 ambiguity).
- **Correction Applied**: Revised `clean_price()` to use flexible regex matching `r"[-+]?\d+(?:\.\d+)?"` after stripping symbols, correctly extracting `51.77` regardless of prepended symbols.

### 3. Truncated Book Titles in Catalog Anchors
- **AI Suggestion**: The initial scraper extracted title via `pod.select_one("h3 a").text`.
- **Flaw Discovered**: On `books.toscrape.com`, long titles are truncated in the anchor text (e.g., `"A Light in the ..."`), but the full, untruncated title is stored in the `title` attribute of the anchor (`<a title="A Light in the Attic">`).
- **Correction Applied**: Updated selector logic to `title_elem.get("title") or title_elem.get_text(strip=True)` to ensure 100% full book titles are captured.

### 4. Dynamic URL Resolution
- **AI Suggestion**: Hardcoded relative path concatenation (`base_url + "/" + href`).
- **Flaw Discovered**: On `books.toscrape.com`, pagination URLs change format from `catalogue/page-2.html` on the root page to `page-3.html` on page 2. String concatenation resulted in invalid URLs like `https://books.toscrape.com/catalogue/page-2.html/page-3.html`.
- **Correction Applied**: Standardized on `urllib.parse.urljoin(current_url, href)` across all scrapers, ensuring RFC-compliant relative URL resolution.

### 5. Books Category 0% Extraction Flaw
- **AI Suggestion**: Attempting to extract category from the general catalogue cards (`catalogue/page-X.html`).
- **Flaw Discovered**: On `books.toscrape.com`, the category name does not exist on the product card element on catalogue pages. The initial AI implementation left `category=None`, resulting in 0% category completeness on the dashboard. Making 1,000 requests to individual product detail pages was prohibitively slow (~25 minutes).
- **Correction Applied**: Implemented **Taxonomy-Driven Category Crawling**. The scraper queries `.side_categories` on the index page to discover all 50 category URLs, then crawls each category and follows pagination within each category. The category name is dynamically derived from the category page header and breadcrumbs. All 1,000 books are extracted with 100% verified category accuracy in ~30 seconds.

### 6. Quotes Count 0 on Dashboard
- **Root Cause Discovered**: An earlier isolated run with `--sources books` had overwritten `output/summary_report.json` with a 200-record books-only crawl. The Quotes scraper implementation itself was structurally sound, but the UI was displaying stale metrics from the incomplete run.
- **Correction Applied**: Executed full concurrent crawl across both sources, ensured `--sources all` is the default CLI behavior, and confirmed that both scrapers execute concurrently and populate `quotes` and `books` sections in the summary report.

### 7. Global vs Source-Aware Field Completeness
- **AI Suggestion**: Computing field completeness globally across all consolidated records (`filled / total`).
- **Flaw Discovered**: Because books never have authors and quotes never have prices or categories, global completeness showed 0% for Author and Category, giving a misleading impression that the scraper had failed to extract those fields.
- **Correction Applied**: Replaced global calculation with **Source-Aware Completeness** in `processing/pipeline.py` and the dashboard UI. Books completeness is evaluated against book fields (`name_or_title`, `price`, `rating`, `category`, `availability`), and Quotes completeness is evaluated against quote fields (`name_or_title`, `author`, `tags`). Non-applicable fields are clearly marked `"N/A"`.

---

## 6. How the Final Solution Was Tested and Verified

1. **Unit Testing (`pytest`)**:
   - 39 unit tests written and executed, covering all cleaning utilities, rating mappings, price extractions, validation constraints (including category requirement for books and author for quotes), and mock parser fixtures.
   - Result: **39 passed in 0.42 seconds**.

2. **Integration & End-to-End Execution**:
   - Executed `python main.py` against both live production websites.
   - Scraped all 50 category trees of Books to Scrape (1,000 books across 80 pages) and all 10 pages of Quotes to Scrape (100 quotes).
   - Validated dataset generation:
     - `output/final_dataset.csv` contains 1,099 rows (identifying 1 genuine duplicate book on `books.toscrape.com`: *"The Star-Touched Queen"*).
     - `output/summary_report.json` generated with full data quality metrics, price distributions, and execution timings (32.44 seconds total runtime).

3. **CSV & Schema Integrity Check**:
   - Verified column headers match specification: `source`, `name_or_title`, `category`, `price`, `rating`, `author`, `tags`, `description`, `availability`, `source_url`, `scraped_at`.
   - Checked that null fields (e.g. price for quotes, author for books) are represented cleanly without synthetic or invented values.
