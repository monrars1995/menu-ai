#!/usr/bin/env python3
"""Menu.AI opencode tool: trigger menu generation pipeline.

Usage (from opencode):
  python3 .opencode/tools/pipeline-run.py [--empresa-id ID] [--contrato-id ID] [--model MODEL] [--no-confirm]

Environment:
  Reads DATABASE_URL, OPENROUTER_API_KEY from .env in project root.
  Requires venv activated or PYTHONPATH set.
"""
import argparse, json, os, sys, time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

def load_env():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def main():
    load_env()
    import requests

    parser = argparse.ArgumentParser(description="Trigger Menu.AI pipeline")
    parser.add_argument("--empresa-id", help="Empresa UUID")
    parser.add_argument("--contrato-id", help="Contrato UUID")
    parser.add_argument("--model", help="LLM model slug (e.g. queen-3.6)")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--no-confirm", action="store_true", help="Auto-confirm HITL pause")
    parser.add_argument("--timeout", type=int, default=300, help="Max wait seconds")
    args = parser.parse_args()

    payload = {}
    if args.empresa_id:
        payload["empresa_id"] = args.empresa_id
    if args.contrato_id:
        payload["contrato_id"] = args.contrato_id
    if args.model:
        payload["llm_model"] = args.model

    print(f"[pipeline-run] POST {args.base_url}/api/gerar")
    print(f"[pipeline-run] payload: {json.dumps(payload, indent=2)}")

    resp = requests.post(f"{args.base_url}/api/gerar", json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"[ERROR] {resp.status_code}: {resp.text}")
        sys.exit(1)

    data = resp.json()
    job_id = data.get("job_id")
    print(f"[pipeline-run] Job created: {job_id}")
    print(f"[pipeline-run] Status: {data.get('status')}")

    start = time.time()
    while time.time() - start < args.timeout:
        status_resp = requests.get(f"{args.base_url}/api/stream/{job_id}", timeout=5)
        if status_resp.status_code == 200:
            for line in status_resp.text.split("\n"):
                if line.startswith("data: "):
                    try:
                        evt = json.loads(line[6:])
                        step = evt.get("step", "?")
                        status = evt.get("status", "?")
                        msg = evt.get("message", "")
                        print(f"  [{step}] {status}: {msg}")
                        if status == "paused" and args.no_confirm:
                            print(f"[pipeline-run] Auto-confirming...")
                            requests.post(f"{args.base_url}/api/gerar/{job_id}/confirmar",
                                        json={"aprovado": True}, timeout=10)
                        if status in ("completed", "failed"):
                            print(f"\n[pipeline-run] Final: {status}")
                            if evt.get("result"):
                                print(f"[pipeline-run] Result keys: {list(evt['result'].keys())}")
                            return 0 if status == "completed" else 1
                    except json.JSONDecodeError:
                        pass
        time.sleep(2)

    print(f"[ERROR] Timeout after {args.timeout}s")
    return 1

if __name__ == "__main__":
    sys.exit(main())
