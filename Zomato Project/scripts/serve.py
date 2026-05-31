"""Run the API server: py -m scripts.serve"""

from __future__ import annotations

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("ENV", "production").lower() == "development"
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
        app_dir="src",
    )

