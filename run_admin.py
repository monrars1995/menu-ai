"""
Arranque da consola administrativa (porta por defeito 8001).

    ADMIN_PORT=8001 python3 run_admin.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
os.chdir(BASE)

from dotenv import load_dotenv

load_dotenv()

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("ADMIN_PORT", "8001"))
    reload = os.getenv("ADMIN_RELOAD", "false").lower() == "true"
    print()
    print("Menu.AI — Admin")
    print("===============")
    print(f"   http://127.0.0.1:{port}")
    print(f"   Docs: http://127.0.0.1:{port}/api/docs")
    if os.getenv("DEBUG", "false").lower() == "true":
        print(f"   DEBUG: JWT de desenvolvimento na página inicial → http://127.0.0.1:{port}/")
    print()
    uvicorn.run(
        "admin.main:app",
        host=os.getenv("ADMIN_HOST", "0.0.0.0"),
        port=port,
        reload=reload,
    )
