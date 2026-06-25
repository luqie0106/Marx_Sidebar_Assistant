"""
Marx AI Assistant - FastAPI Backend
Entry point for the application (run from project root).
"""

import sys
import os

# Ensure backend/ is on the path so `app` package can be found
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import uvicorn
from app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
