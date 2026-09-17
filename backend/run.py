"""
run.py

Local development server launcher.

Run this from inside the backend/ folder:
    .venv/Scripts/python run.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["backend/app"],
    )
