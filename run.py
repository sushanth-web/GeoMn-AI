import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ["PYTHONIOENCODING"] = "utf-8"

from backend.app.main import app

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print(" [MOIL] ManganeseAI Dashboard starting...")
    print(" [URL]  http://127.0.0.1:8000")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)