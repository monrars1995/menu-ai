---
name: pipeline-debug
description: "Debug the 7-step LLM menu generation pipeline. Use when pipeline generation fails, hangs, or produces unexpected results. Covers job state inspection, LLM call tracing, tool call verification, and step-by-step replay."
---

# Pipeline Debug Skill

## When to Use

- Pipeline generation fails or returns errors
- Job hangs without progress
- Generated menus are incorrect or incomplete
- Need to trace LLM calls and tool usage
- HITL (Human-in-the-Loop) confirmation issues

## Key Files

| File | Purpose |
|------|---------|
| `pipeline/sequential_spec.py` | 7-step definitions (labels, prompts, tools) |
| `pipeline/litellm_runner.py` | Step execution via `litellm.completion()` |
| `pipeline/orchestrator.py` | Context setup, delegates to runner |
| `pipeline/protocolo.py` | SharedContext, AgentMessage protocol |
| `pipeline/model_router.py` | Cross-provider fallback routing |
| `services/geracao.py` | Background worker, job lifecycle |
| `services/job_state.py` | In-memory job dict + queues |
| `tools/cardapio_tools.py` | Recipe tools (search, cost, seasonality) |
| `tools/db_tools.py` | Database tools (fichas, contracts, semantic) |

## Debug Workflow

### Step 1: Check Job State

```bash
# Verify stack is healthy
source venv/bin/activate && python3 scripts/verify_stack.py

# Check if FastAPI is responding
curl -s http://localhost:8000/api/health | python3 -m json.tool
```

Read `services/job_state.py` — the `jobs` dict holds all in-memory job states. Key fields:
- `status`: `pending` → `running` → `paused` (HITL) → `running` → `completed` / `failed`
- `step`: current pipeline step (1-7)
- `messages`: list of `AgentMessage` from each step
- `result`: final output when completed

### Step 2: Check LLM Provider

```bash
# Test LLM connection
source venv/bin/activate && python3 test_llm.py
```

Read `pipeline/llm_providers.py` — verify API keys are set:
- `OPENROUTER_API_KEY` (primary)
- `OPENROUTER_DEFAULT_MODEL` (fallback model)

Read `pipeline/model_router.py` — the `ModelRouter` class handles fallback chains. Check:
- Which providers are configured
- Fallback order
- Rate limit handling

### Step 3: Trace Step Execution

Read `pipeline/litellm_runner.py` → `run_lite_pipeline()`:

1. Iterates over `build_steps()` from `sequential_spec.py`
2. Each step gets: system prompt, user prompt, tool list
3. Calls `litellm.completion()` with tool calling
4. Processes tool calls → feeds results back
5. Collects `AgentMessage` per step

Common issues:
- **Step 1 fails**: Contract PDF parsing issue → check `tools/db_tools.py` `read_contract`
- **Step 2 fails**: DB query issue → check `tools/db_tools.py` `query_fichas`
- **Steps 3-6 fail**: LLM output format issue → check prompts in `sequential_spec.py`
- **Step 7 fails**: Export formatting → check output parsing in `litellm_runner.py`

### Step 4: Check HITL Pause

After step 1, pipeline pauses for human confirmation:
- `POST /api/gerar/{job_id}/confirmar` — resume pipeline
- Job status should be `paused`
- If stuck at `paused`, check `services/geracao.py` resume logic

### Step 5: Inspect Tool Calls

Read `tools/cardapio_tools.py` and `tools/db_tools.py`:
- Tools use `langchain_core.tools.BaseTool` via `tools/compat.py`
- Each tool wraps a SQL query or business logic function
- Check if database has required data (fichas, ingredientes, contratos)

### Step 6: Check Audit Logs

Read `services/audit_log.py` — LLM call audit trail:
- Every LLM call is logged to `LLMAuditLog` table
- Check via admin panel: `GET /api/admin/llm/audit`

## Common Fixes

| Issue | Fix |
|-------|-----|
| `OPENROUTER_API_KEY` missing | Set in `.env` |
| Model not found | Check `OPENROUTER_DEFAULT_MODEL` in `.env` and `llm_providers.py` catalog |
| DB connection refused | Verify `DATABASE_URL`, check PostgreSQL/Supabase status |
| Empty fichas/ingredientes | Run `python3 seed_data.py` |
| Job stuck at `paused` | Call `POST /api/gerar/{job_id}/confirmar` |
| CORS errors | Add origins to `CORS_ORIGINS` in `.env` |
| venv broken | Run `bash fix_venv.sh` |

## Quick Smoke Test

```bash
source venv/bin/activate
DEBUG=true DEMO_GERAR_SEM_AUTH=true python3 scripts/smoke_flow.py
```
