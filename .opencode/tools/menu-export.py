#!/usr/bin/env python3
"""Menu.AI opencode tool: export generated menu as XLSX/TXT.

Usage:
  python3 .opencode/tools/menu-export.py JOB_ID [--format xlsx|txt] [--output PATH]

Downloads the result of a completed menu generation job.
"""
import argparse, os, sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

def main():
    parser = argparse.ArgumentParser(description="Export menu from completed job")
    parser.add_argument("job_id", help="Job UUID")
    parser.add_argument("--format", choices=["xlsx", "txt"], default="xlsx")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    import requests
    fmt = args.format
    url = f"{args.base_url}/api/download/{args.job_id}?formato={fmt}"
    resp = requests.get(url, timeout=30)

    if resp.status_code != 200:
        print(f"[ERROR] {resp.status_code}: {resp.text}")
        sys.exit(1)

    out = args.output or f"cardapio_{args.job_id[:8]}.{fmt}"
    with open(out, "wb") as f:
        f.write(resp.content)
    print(f"[menu-export] Saved to {out} ({len(resp.content)} bytes)")

if __name__ == "__main__":
    main()
