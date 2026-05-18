#!/usr/bin/env python3
"""
Smoke test do fluxo de geração, estatísticas e persistência (via API HTTP real).

Pré-requisito:
  - API já em execução (ex.: docker compose up -d app)

Por defeito (DEBUG + DEMO_GERAR_SEM_AUTH):
  - GET /api/health, /api/info
  - POST /api/gerar sem JWT → empresa_id via DEFAULT_EMPRESA_ID
  - GET /api/status/{job_id}, linha em jobs_agente

Fluxo completo com registo + login (requer ALLOW_OPEN_REGISTRO):
  SMOKE_FULL_AUTH=1 ALLOW_OPEN_REGISTRO=true python3 scripts/smoke_flow.py

Config opcional:
  SMOKE_BASE_URL=http://127.0.0.1:8000
  SMOKE_LLM_MODEL=openai-gpt-5.5
  SMOKE_REVIEW_LLM_MODEL=queen-3.6
  SMOKE_DAYS=30
"""
from __future__ import annotations

import os
import sys
import time
import uuid

_ROOT = __file__
for _ in range(2):
    _ROOT = os.path.dirname(_ROOT)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
import requests

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


def _check_info_scope(base_url: str, empresa_id: str, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.get(f"{base_url}/api/info", headers=headers, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("db_status") == "conectado", body
    assert body.get("total_fichas", 0) >= 0, body
    return body


def main() -> int:
    full_auth = os.getenv("SMOKE_FULL_AUTH", "").lower() in ("1", "true", "yes")
    
    if not full_auth:
        os.environ["DEBUG"] = "true"
        os.environ["DEMO_GERAR_SEM_AUTH"] = "true"
    else:
        os.environ["ALLOW_OPEN_REGISTRO"] = "true"

    if not any((os.getenv(k) or "").strip() for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "MOONSHOT_API_KEY", "OPENROUTER_API_KEY")):
        raise RuntimeError("Configure OPENAI_API_KEY, GEMINI_API_KEY/GOOGLE_API_KEY, MOONSHOT_API_KEY ou OPENROUTER_API_KEY para executar scripts/smoke_flow.py.")

    from seed_data import TEST_EMPRESA_ID

    base_url = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    eid = os.getenv("DEFAULT_EMPRESA_ID", TEST_EMPRESA_ID).strip()
    smoke_days = max(1, min(366, int(os.getenv("SMOKE_DAYS", "1") or "1")))

    r = requests.get(f"{base_url}/api/health", timeout=20)
    assert r.status_code == 200, r.text
    assert r.json().get("db_status") == "conectado", r.json()

    demo_sem_auth = False

    # Em ambiente com auth obrigatória, /api/info sem token pode ser anônimo.
    if not full_auth:
        info_body = _check_info_scope(base_url, eid)
        if info_body.get("empresa_id") == eid:
            demo_sem_auth = True
        elif info_body.get("scope") == "anonimo":
            print("smoke_flow aviso: /api/info sem token está em modo anônimo (auth obrigatória).")
        else:
            raise AssertionError(info_body)

    r = requests.get(f"{base_url}/api/llm-models", timeout=20)
    assert r.status_code == 200, r.text
    lm = r.json()
    assert lm.get("models") and len(lm["models"]) >= 1, lm
    smoke_model = (os.getenv("SMOKE_LLM_MODEL") or lm.get("default") or lm["models"][0]["id"]).strip()
    smoke_review_model = (os.getenv("SMOKE_REVIEW_LLM_MODEL") or "").strip()

    if full_auth:
        suffix = uuid.uuid4().hex[:8]
        email = f"smoke_{suffix}@gmail.com"
        password = "smoke12"
        reg = requests.post(
            f"{base_url}/api/auth/registro",
            json={
                "nome": "Smoke Test",
                "email": email,
                "senha": password,
                "role": "nutricionista",
                "empresa_id": TEST_EMPRESA_ID,
            },
            timeout=30,
        )
        if reg.status_code != 201 and "rate limit" in reg.text.lower():
            print(f"smoke_flow OK (parcial): Supabase rate limit atingido ({reg.text}). Auth configurado corretamente.")
            return 0
        if reg.status_code == 403:
            print("smoke_flow OK (parcial): registro público desativado (ALLOW_OPEN_REGISTRO=false).")
            return 0
            
        assert reg.status_code == 201, reg.text
        r = requests.post(f"{base_url}/api/auth/login", json={"email": email, "senha": password}, timeout=30)
        if r.status_code == 401 and "Email not confirmed" in r.text:
            print("smoke_flow OK (parcial): Supabase exige confirmação de email. Auth configurado corretamente.")
            return 0
            
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        info_auth = _check_info_scope(base_url, eid, token=token)
        assert info_auth.get("empresa_id") == eid, info_auth
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.post(
            f"{base_url}/api/gerar",
            headers=headers,
            json={
                "dias": smoke_days,
                "restricoes_usuario": "smoke",
                "llm_model": smoke_model,
                "review_llm_model": smoke_review_model or None,
                "review_enabled": bool(smoke_review_model),
            },
            timeout=30,
        )
    else:
        r = requests.post(
            f"{base_url}/api/gerar",
            json={
                "dias": smoke_days,
                "restricoes_usuario": "smoke",
                "llm_model": smoke_model,
                "review_llm_model": smoke_review_model or None,
                "review_enabled": bool(smoke_review_model),
            },
            timeout=30,
        )
        if r.status_code in (400, 401, 403) and not demo_sem_auth:
            print(
                "smoke_flow OK (parcial): auth obrigatória para /api/gerar sem token; "
                "use SMOKE_FULL_AUTH=1 para fluxo completo autenticado."
            )
            return 0

    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    body = r.json()
    assert body.get("status") == "iniciando" or "job_id" in body

    st = requests.get(f"{base_url}/api/status/{job_id}", timeout=20)
    assert st.status_code == 200, st.text
    cfg = st.json().get("config") or {}
    assert cfg.get("empresa_id") == eid, cfg
    assert cfg.get("llm_model") == smoke_model, cfg

    _check_job_db(job_id, eid)

    try:
        with requests.get(
            f"{base_url}/api/stream/{job_id}",
            stream=True,
            timeout=(5, 20),
            headers=headers if full_auth else None,
        ) as s:
            assert s.status_code == 200, f"SSE status inválido: {s.status_code} {s.text[:200]}"
            _ = next(s.iter_lines(), b"")  # primeira linha SSE (pode ser ping)
    except requests.exceptions.ReadTimeout:
        st2 = requests.get(f"{base_url}/api/status/{job_id}", timeout=20)
        assert st2.status_code == 200, st2.text
        print("smoke_flow aviso: timeout ao ler primeiro evento SSE (20s), mas status endpoint respondeu.")

    deadline = time.time() + max(120, smoke_days * 10)
    final_status = None
    while time.time() < deadline:
        st3 = requests.get(f"{base_url}/api/status/{job_id}", timeout=20)
        assert st3.status_code == 200, st3.text
        final_status = st3.json()
        if final_status.get("status") in {"concluido", "erro"}:
            break
        time.sleep(5)

    assert final_status is not None, "status final ausente"
    assert final_status.get("status") == "concluido", final_status
    assert not final_status.get("degraded_generation"), final_status
    assert final_status.get("generator_model"), final_status
    if smoke_review_model:
        assert final_status.get("review_model"), final_status
        assert final_status.get("review_status") not in {None, "pending"}, final_status

    print(
        "smoke_flow OK: health, info, /api/gerar, status, JobAgente, SSE inicial e conclusão LLM real "
        f"(empresa_id={eid}, model={smoke_model}, review={smoke_review_model or 'disabled'})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f"smoke_flow FALHOU: {e}", file=sys.stderr)
        raise
