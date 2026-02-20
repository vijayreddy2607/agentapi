"""
Entry point — re-exports from app.main for GUVI repo structure compliance.
The actual implementation lives in app/ (FastAPI multi-agent pipeline).
"""
from app.main import app  # noqa: F401

# Run with:
#   uvicorn src.main:app --host 0.0.0.0 --port 8000
# or use the root-level start.sh script.
