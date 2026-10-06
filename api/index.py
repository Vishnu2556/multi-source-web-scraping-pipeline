"""
Vercel Serverless Function & FastAPI Entrypoint for Multi-Source Web Scraping Pipeline.
"""
import csv
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

# Resolve project base directory robustly
CURRENT_FILE = Path(__file__).resolve()
BASE_DIR = CURRENT_FILE.parent.parent if CURRENT_FILE.parent.name == "api" else CURRENT_FILE.parent
WEB_DIR = BASE_DIR / "web"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Ensure root directory is on Python path for internal imports
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import DEFAULT_CONFIG
from processing.pipeline import ScrapingPipeline

# Real top-level FastAPI application required by Vercel
app = FastAPI(
    title="Multi-Source Web Scraping Pipeline",
    description="REST API and interactive dashboard for scraped books and quotes dataset",
    version="1.0.0",
)

# CORS configuration: allow local development and Vercel production domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """Health check endpoint indicating service status."""
    return {
        "status": "healthy",
        "app_name": "Multi-Source Web Scraping Pipeline",
        "version": "1.0.0",
    }


@app.get("/api/summary")
async def get_summary():
    """Return actual latest summary_report.json data without hardcoded values."""
    summary_path = OUTPUT_DIR / DEFAULT_CONFIG.SUMMARY_JSON_FILENAME
    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"Failed reading summary: {e}"},
            )

    return {
        "status": "not_ready",
        "message": "No scraping results available",
    }


def _read_and_filter_dataset(
    page: int,
    page_size: int,
    source: str,
    category: str,
    rating: str,
    q: str,
) -> Dict[str, Any]:
    """Helper to read, filter, search, and paginate records from final_dataset.csv."""
    csv_path = OUTPUT_DIR / DEFAULT_CONFIG.FINAL_CSV_FILENAME
    if not csv_path.exists():
        return {
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
            "categories": [],
            "records": [],
        }

    records: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    # Collect unique categories for frontend filters
    all_categories = sorted(list({
        r.get("category", "").strip()
        for r in records
        if r.get("category") and r.get("category").strip()
    }))

    # Source filter
    if source and source.lower() != "all":
        records = [r for r in records if source.lower() in r.get("source", "").lower()]

    # Category filter
    if category and category.lower() != "all":
        records = [
            r for r in records
            if r.get("category") and category.lower() == r.get("category", "").strip().lower()
        ]

    # Rating filter
    if rating and rating.lower() != "all":
        try:
            target_rating = float(rating)
            records = [
                r for r in records
                if r.get("rating") and float(r.get("rating")) == target_rating
            ]
        except ValueError:
            pass

    # Search query
    clean_q = q.strip().lower() if q else ""
    if clean_q:
        records = [
            r for r in records
            if clean_q in r.get("name_or_title", "").lower()
            or clean_q in r.get("author", "").lower()
            or clean_q in r.get("tags", "").lower()
            or clean_q in r.get("category", "").lower()
        ]

    total = len(records)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated = records[start_idx:end_idx]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "categories": all_categories,
        "records": paginated,
    }


@app.get("/api/dataset")
async def get_dataset(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    source: str = Query(default="all"),
    category: str = Query(default="all"),
    rating: str = Query(default="all"),
    q: str = Query(default=""),
):
    """Expose consolidated final_dataset.csv as paginated and filtered JSON records."""
    try:
        return _read_and_filter_dataset(
            page=page,
            page_size=page_size,
            source=source,
            category=category,
            rating=rating,
            q=q,
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Failed reading dataset: {e}"},
        )


@app.get("/api/data")
async def get_data_alias(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    source: str = Query(default="all"),
    category: str = Query(default="all"),
    rating: str = Query(default="all"),
    q: str = Query(default=""),
):
    """Route alias matching existing frontend /api/data requests."""
    return await get_dataset(
        page=page,
        page_size=page_size,
        source=source,
        category=category,
        rating=rating,
        q=q,
    )


@app.get("/api/logs")
async def get_logs():
    """Return execution logs from scraper.log or a fallback if uninitialized."""
    log_path = LOGS_DIR / DEFAULT_CONFIG.LOG_FILENAME
    if not log_path.exists():
        return {"logs": "No logs available. Run pipeline locally using 'python main.py' to generate logs."}

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        recent = "".join(lines[-200:])
        return {"logs": recent}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Failed reading logs: {e}"},
        )


@app.get("/api/export")
async def export_csv():
    """Download the consolidated CSV dataset."""
    csv_path = OUTPUT_DIR / DEFAULT_CONFIG.FINAL_CSV_FILENAME
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file not found")

    return FileResponse(
        path=str(csv_path),
        media_type="text/csv",
        filename="final_dataset.csv",
    )


@app.post("/api/run")
async def trigger_pipeline(request: Request):
    """Trigger pipeline execution or return status."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    max_pages = payload.get("max_pages", 0)
    max_records = payload.get("max_records", None)
    sources = payload.get("sources", ["all"])
    dedup_action = payload.get("dedup_action", "remove")

    try:
        logger = logging.getLogger("api_trigger")
        pipeline = ScrapingPipeline(config=DEFAULT_CONFIG, logger=logger)
        summary = pipeline.run(
            sources=sources,
            max_pages=max_pages if (max_pages and max_pages > 0) else None,
            max_records=max_records if (max_records and max_records > 0) else None,
            dedup_action=dedup_action,
            use_concurrency=True,
        )
        return {"status": "success", "summary": summary}
    except OSError as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Filesystem write failed ({e}). Note that serverless runtimes have read-only filesystems. Run full scraping locally via 'python main.py'.",
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


# ---------------------------------------------------------------------------
# Frontend Static Asset Delivery
# ---------------------------------------------------------------------------

@app.get("/")
@app.get("/index.html")
async def serve_dashboard():
    """Serve the existing rich web dashboard HTML."""
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    return HTMLResponse("<h1>DataScrape Studio</h1><p>Dashboard HTML not found.</p>", status_code=200)


@app.get("/index.css")
async def serve_css():
    """Serve dashboard CSS."""
    css_file = WEB_DIR / "index.css"
    if css_file.exists():
        return FileResponse(str(css_file), media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS not found")


@app.get("/app.js")
async def serve_js():
    """Serve dashboard JavaScript."""
    js_file = WEB_DIR / "app.js"
    if js_file.exists():
        return FileResponse(str(js_file), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JavaScript not found")


@app.get("/{file_path:path}")
async def serve_static_file(file_path: str):
    """Serve additional assets from web directory."""
    if file_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Endpoint not found")

    target = WEB_DIR / file_path
    if target.exists() and target.is_file():
        media_type = None
        if file_path.endswith(".css"):
            media_type = "text/css"
        elif file_path.endswith(".js"):
            media_type = "application/javascript"
        elif file_path.endswith(".html"):
            media_type = "text/html"
        elif file_path.endswith(".svg"):
            media_type = "image/svg+xml"
        elif file_path.endswith(".json"):
            media_type = "application/json"
        return FileResponse(str(target), media_type=media_type)

    # Fallback to dashboard
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    raise HTTPException(status_code=404, detail="File not found")
