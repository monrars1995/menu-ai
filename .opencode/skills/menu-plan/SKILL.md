---
name: menu-plan
description: "Plan and implement menu generation features. Covers adding new pipeline steps, modifying LLM prompts, creating new tools, and extending the menu domain model. Use when building features for the cardápio generation system."
---

# Menu Plan Skill

## When to Use

- Adding or modifying pipeline steps
- Creating new LLM tools
- Extending the menu domain model (Cardapio, FichaTecnica, etc.)
- Modifying generation prompts
- Adding new export formats
- Changing HITL workflow

## Architecture Overview

```
POST /api/gerar
  → services/geracao.py (background worker)
    → pipeline/orchestrator.py (MenuOrchestrator)
      → pipeline/litellm_runner.py (run_lite_pipeline)
        → pipeline/sequential_spec.py (7 steps definition)
          → tools/cardapio_tools.py + tools/db_tools.py
```

## Key Patterns

### Adding a New Pipeline Step

1. Define the step in `pipeline/sequential_spec.py` → `build_steps()`:
   - Add label, system prompt, user prompt template
   - Assign tools the step can use

2. The step will execute automatically via `litellm_runner.py`

3. Update `pipeline/protocolo.py` if new shared context fields are needed

### Creating a New LLM Tool

1. Define the tool in `tools/cardapio_tools.py` or `tools/db_tools.py`:

```python
from langchain_core.tools import tool

@tool
def my_new_tool(param: str) -> str:
    """Tool description for the LLM."""
    # implementation
    return result
```

2. Register it in `pipeline/sequential_spec.py` → assign to relevant steps

3. Use `tools/compat.py` if you need LangChain-free fallback

### Extending the Domain Model

1. Add model in `database/models.py` (SQLAlchemy 2.0 declarative)
2. Add Pydantic schemas in `database/schemas.py`
3. Create Alembic migration: `alembic revision --autogenerate -m "description"`
4. Create router in `routers/` if CRUD endpoints needed
5. Register router in `app.py`

### Modifying Generation Prompts

All prompts live in `pipeline/sequential_spec.py`:
- Each step has `system_prompt` and `user_prompt_template`
- `user_prompt_template` uses `{variable}` placeholders
- Variables come from `SharedContext` in `protocolo.py`

## Database Conventions

- All models inherit from SQLAlchemy `Base` in `database/connection.py`
- Multi-tenant: FK to `Empresa` on all domain entities
- UUIDs as strings: `id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))`
- Status enums as strings (not Python Enum)
- Timestamps: `created_at`, `updated_at` with `default=datetime.utcnow`

## Frontend Conventions

### Menu Frontend (Next.js, port 8002)

- Pages in `menu/src/app/(app)/`
- Components in `menu/src/components/`
- API client in `menu/src/lib/api.ts`
- Auth via Supabase: `menu/src/lib/auth.tsx`
- Types in `menu/src/lib/types.ts`

### Admin Panel (Next.js + FastAPI, port 8001)

- Pages in `admin/src/app/`
- Admin-specific routers in `admin/routers/`
- Auth: JWT admin/super_admin or `X-Admin-Api-Key`

## API Patterns

- FastAPI routers with `APIRouter(prefix="/api/...")`
- Dependency injection: `get_usuario_atual` for auth, `get_db` for DB sessions
- Background tasks via `BackgroundTasks` or `asyncio.create_task`
- SSE streaming: `GET /api/stream/{job_id}` with `StreamingResponse`
