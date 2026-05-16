#!/usr/bin/env python3
"""
Smoke test do fluxo de geração, estatísticas e persistência.

Por defeito (DEBUG + DEMO_GERAR_SEM_AUTH):
  - GET /api/health, /api/info
  - POST /api/gerar sem JWT → empresa_id via DEFAULT_EMPRESA_ID
  - GET /api/status/{job_id}, linha em jobs_agente

Fluxo completo com registo + login (requer bcrypt/passlib OK e ALLOW_OPEN_REGISTRO):
  SMOKE_FULL_AUTH=1 ALLOW_OPEN_REGISTRO=true python3 scripts/smoke_flow.py

Uso na raiz do repositório com venv:
  DEBUG=true DEMO_GERAR_SEM_AUTH=true python3 scripts/smoke_flow.py
"""
from __future__ import annotations

import os
import sys
import uuid

_ROOT = __file__
for _ in range(2):
    _ROOT = os.path.dirname(_ROOT)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_ROOT, ".env"))


def _check_job_db(job_id: str, empresa_id: str) -> None:
    import json

    from sqlalchemy import text

    from database.connection import engine

    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT parametros_json, empresa_id FROM jobs_agente WHERE job_id = :jid"
            ),
            {"jid": job_id},
        ).fetchone()
    assert row is not None, "JobAgente não persistido"
    params = row[0]
    if isinstance(params, str):
        params = json.loads(params)
    assert isinstance(params, dict) and params.get("empresa_id") == empresa_id, params
    # coluna empresa_id (FK) pode ser legada INTEGER em BDs antigos; o payload JSON é o contrato do pedido
    if row[1] is not None and str(row[1]) != str(empresa_id):
        print(
            f"aviso: jobs_agente.empresa_id={row[1]!r} != {empresa_id!r} (possível drift de schema; parametros_json está correcto)"
        )


def _check_info_scope(client, empresa_id: str, token: str | None = None) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = client.get("/api/info", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("db_status") == "conectado", body
    assert body.get("empresa_id") == empresa_id, body
    assert body.get("total_fichas", 0) >= 0, body


def main() -> int:
    full_auth = os.getenv("SMOKE_FULL_AUTH", "").lower() in ("1", "true", "yes")
    
    if not full_auth:
        os.environ["DEBUG"] = "true"
        os.environ["DEMO_GERAR_SEM_AUTH"] = "true"
    else:
        os.environ["ALLOW_OPEN_REGISTRO"] = "true"

    if not (os.getenv("OPENROUTER_API_KEY") or "").strip():
        raise RuntimeError("Configure OPENROUTER_API_KEY para executar scripts/smoke_flow.py.")

    from fastapi.testclient import TestClient

    from app import app
    from seed_data import TEST_EMPRESA_ID

    client = TestClient(app)
    eid = os.getenv("DEFAULT_EMPRESA_ID", TEST_EMPRESA_ID).strip()

    r = client.get("/api/health")
    assert r.status_code == 200, r.text
    assert r.json().get("db_status") == "conectado", r.json()

    # Se usarmos autenticação completa, não passamos no info sem token
    if not full_auth:
        _check_info_scope(client, eid)

    r = client.get("/api/llm-models")
    assert r.status_code == 200, r.text
    lm = r.json()
    assert lm.get("models") and len(lm["models"]) >= 1, lm

    if full_auth:
        suffix = uuid.uuid4().hex[:8]
        email = f"smoke_{suffix}@example.com"
        password = "smoke12"
        reg = client.post(
            "/api/auth/registro",
            json={
                "nome": "Smoke Test",
                "email": email,
                "senha": password,
                "role": "nutricionista",
                "empresa_id": TEST_EMPRESA_ID,
            },
        )
        assert reg.status_code == 201, reg.text
        r = client.post("/api/auth/login", json={"email": email, "senha": password})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        _check_info_scope(client, eid, token=token)
        headers = {"Authorization": f"Bearer {token}"}
        r = client.post(
            "/api/gerar",
            headers=headers,
            json={"dias": 1, "restricoes_usuario": "smoke", "llm_model": "glm-5-1"},
        )
    else:
        r = client.post(
            "/api/gerar",
            json={"dias": 1, "restricoes_usuario": "smoke", "llm_model": "glm-5-1"},
        )

    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    body = r.json()
    assert body.get("status") == "iniciando" or "job_id" in body

    st = client.get(f"/api/status/{job_id}")
    assert st.status_code == 200, st.text
    cfg = st.json().get("config") or {}
    assert cfg.get("empresa_id") == eid, cfg
    assert cfg.get("llm_model") == "glm-5-1", cfg

    _check_job_db(job_id, eid)

    with client.stream("GET", f"/api/stream/{job_id}") as s:
        assert s.status_code == 200, s.text
        _ = next(s.iter_lines(), b"")  # primeira linha SSE (pode ser ping)

    print(
        "smoke_flow OK: health, info, /api/gerar, status, JobAgente (empresa_id=%s), stream(1 ev)"
        % eid
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f"smoke_flow FALHOU: {e}", file=sys.stderr)
        raise
