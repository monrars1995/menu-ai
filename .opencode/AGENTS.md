# Menu.AI — AGENTS.md (opencode)

> Convenções e padrões para agentes opencode

## Projeto

**Menu.AI** — Geração de cardápios institucionais via LLM pipeline de 7 etapas

## Comandos

```bash
source venv/bin/activate && python3 run_server.py   # Produção (:8000)
source venv/bin/activate && python3 start.py         # Dev com reload
source venv/bin/activate && uvicorn app:app --reload # Dev alternativo
cd admin && npm run dev    # Admin panel (:8001)
cd menu && npm run dev     # Menu frontend (:8002)
source venv/bin/activate && alembic upgrade head     # Migrações
source venv/bin/activate && python3 seed_data.py     # Seed
source venv/bin/activate && python3 scripts/verify_stack.py  # Diagnóstico
docker compose up -d --build                         # Docker
docker compose exec app alembic upgrade head         # Migrações (Docker)
```

## Stack

- **FastAPI** + **SQLAlchemy 2.0** + **Alembic** (backend :8000)
- **LiteLLM** + **LangChain Core** (LLM pipeline)
- **Next.js 14** + **TailwindCSS** (admin :8001, menu :8002)
- **Supabase** (Auth + PostgreSQL + pgvector)
- **Docker Swarm** + **Traefik** (deploy)

## Convenções de Código

- Python: type hints em tudo, async/await nos services
- UUIDs como strings (`str(uuid.uuid4())`), não `UUID` nativo
- Multi-tenant: tudo ligado a `Empresa` via FK
- LLM tools em `tools/` com `langchain_core.tools.BaseTool`
- Jobs assíncronos: `services/job_state.py` (dict em memória) + `services/geracao.py`
- Sem suite de testes formal; scripts de smoke em `test_*.py` e `scripts/smoke_flow.py`

## Pipeline de 7 Etapas

Definido em `pipeline/sequential_spec.py`:

1. Analista de Contratos — lê contrato, extrai regras
2. Gestor de Fichas Técnicas — consulta pratos do banco
3. Nutricionista — planeia cardápios
4. Analista Nutricional — valida conformidade
5. Controller Financeiro — verifica custos
6. Agente de Compras — gera lista de compras
7. Exportador — consolida cardápio final

## Variáveis de Ambiente Chave

```
DATABASE_URL=             # PostgreSQL
OPENROUTER_API_KEY=       # LLM gateway
OPENROUTER_DEFAULT_MODEL= # ex: queen-3.6
SUPABASE_URL=             # Supabase
SECRET_KEY=               # Auth
DEBUG=true                # Dev mode
DEMO_GERAR_SEM_AUTH=true  # Demo sem auth
```

## Git Conventions

- Branches: `feat/description`, `fix/description`, `chore/description`
- Commits: conventional commits (feat:, fix:, chore:, docs:)
