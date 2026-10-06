"""
Lightweight REST API & Web Dashboard Server for the Web Scraping Pipeline.
Built using Python standard library (http.server) with zero external server dependencies.
"""
import csv
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import logging
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from config.settings import DEFAULT_CONFIG
from processing.pipeline import ScrapingPipeline
from utils.logger import setup_logger

PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"


class PipelineServerHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving the dashboard frontend and pipeline API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        # Enable CORS and disable aggressive caching for live data
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/api/summary":
            self._handle_get_summary()
        elif path == "/api/data":
            self._handle_get_data(params)
        elif path == "/api/logs":
            self._handle_get_logs()
        elif path == "/api/export":
            self._handle_export_csv()
        else:
            # Fallback to serving static dashboard files from web/
            if path == "/" or not (WEB_DIR / path.lstrip("/")).exists():
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            self._handle_trigger_pipeline()
        else:
            self.send_error(404, "Endpoint Not Found")

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_get_summary(self) -> None:
        summary_path = OUTPUT_DIR / DEFAULT_CONFIG.SUMMARY_JSON_FILENAME
        if summary_path.exists():
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json(data)
                return
            except Exception as e:
                self._send_json({"error": f"Failed reading summary: {e}"}, status=500)
                return
        self._send_json({"error": "Summary report does not exist yet. Please run pipeline first."}, status=404)

    def _handle_get_data(self, params: Dict[str, List[str]]) -> None:
        csv_path = OUTPUT_DIR / DEFAULT_CONFIG.FINAL_CSV_FILENAME
        if not csv_path.exists():
            self._send_json({"total": 0, "records": []})
            return

        try:
            records = []
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(row)

            # Collect unique non-empty categories for frontend filter dropdown
            all_categories = sorted(list({r.get("category", "").strip() for r in records if r.get("category") and r.get("category").strip()}))

            # Filtering
            source_filter = params.get("source", ["all"])[0].lower()
            if source_filter != "all":
                records = [r for r in records if source_filter in r.get("source", "").lower()]

            category_filter = params.get("category", ["all"])[0].lower()
            if category_filter != "all":
                records = [r for r in records if r.get("category") and category_filter == r.get("category", "").strip().lower()]

            rating_filter = params.get("rating", ["all"])[0].lower()
            if rating_filter != "all":
                try:
                    target_rating = float(rating_filter)
                    records = [r for r in records if r.get("rating") and float(r.get("rating")) == target_rating]
                except ValueError:
                    pass

            query = params.get("q", [""])[0].strip().lower()
            if query:
                records = [
                    r for r in records
                    if query in r.get("name_or_title", "").lower()
                    or query in r.get("author", "").lower()
                    or query in r.get("tags", "").lower()
                    or query in r.get("category", "").lower()
                ]

            total = len(records)

            # Pagination parameters
            page = max(1, int(params.get("page", ["1"])[0]))
            page_size = min(200, max(1, int(params.get("page_size", ["25"])[0])))
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size

            paginated = records[start_idx:end_idx]

            self._send_json({
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
                "categories": all_categories,
                "records": paginated,
            })
        except Exception as e:
            self._send_json({"error": f"Failed reading data: {e}"}, status=500)

    def _handle_get_logs(self) -> None:
        log_path = LOGS_DIR / DEFAULT_CONFIG.LOG_FILENAME
        if not log_path.exists():
            self._send_json({"logs": "Log file not yet initialized."})
            return

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            # Return last 200 lines
            recent = "".join(lines[-200:])
            self._send_json({"logs": recent})
        except Exception as e:
            self._send_json({"error": f"Failed reading logs: {e}"}, status=500)

    def _handle_export_csv(self) -> None:
        csv_path = OUTPUT_DIR / DEFAULT_CONFIG.FINAL_CSV_FILENAME
        if not csv_path.exists():
            self.send_error(404, "File not found")
            return

        with open(csv_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="final_dataset.csv"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_trigger_pipeline(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            options = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            options = {}

        max_pages = options.get("max_pages", 0)
        max_records = options.get("max_records", None)
        sources = options.get("sources", ["all"])
        dedup_action = options.get("dedup_action", "remove")

        try:
            logger = logging.getLogger("server_trigger")
            pipeline = ScrapingPipeline(config=DEFAULT_CONFIG, logger=logger)
            summary = pipeline.run(
                sources=sources,
                max_pages=max_pages if (max_pages and max_pages > 0) else None,
                max_records=max_records if (max_records and max_records > 0) else None,
                dedup_action=dedup_action,
                use_concurrency=True,
            )
            self._send_json({"status": "success", "summary": summary})
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, status=500)


def run_server(port: int = PORT) -> None:
    server_address = ("", port)
    httpd = HTTPServer(server_address, PipelineServerHandler)
    print(f"============================================================")
    print(f" Web Dashboard & API Server listening at: http://localhost:{port}")
    print(f" API Endpoints:")
    print(f"   GET  /api/summary   - Pipeline summary report metrics")
    print(f"   GET  /api/data      - Filtered & paginated consolidated records")
    print(f"   GET  /api/logs      - Live execution log feed")
    print(f"   GET  /api/export    - Download output CSV dataset")
    print(f"   POST /api/run       - Trigger live pipeline execution")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        httpd.server_close()


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port=p)
