"""
Local development server runner for the FastAPI application.
Run via:
    python server.py
or
    uvicorn api.index:app --reload
"""
import sys
import uvicorn
from api.index import app

PORT = 8000

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    print("=" * 60)
    print(f" Web Dashboard & API Server listening at: http://localhost:{port}")
    print(f" Swagger API Documentation: http://localhost:{port}/docs")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=port)
