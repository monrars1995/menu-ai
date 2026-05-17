# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Menu.AI — contexto do repositório

## O que é

API **FastAPI** multi-tenant (empresas, contratos, cardápios, jobs) com geração de cardápios via **LLM (LiteLLM)** e ferramentas (SQL, contratos). O *pipeline* de 7 etapas está em `pipeline/litellm_runner.py` + `pipeline/sequential_spec.py` (orquestrador LiteLLM/LangChain; sem runtime CrewAI).

## Arranque (caminhos suportados)

- **Recomendado (produção, sem reload):** `python3 run_server.py` (ou `PORT=8000 python3 run_server.py`).
- **Desenvolvimento com reload:** `source venv/bin/activate` → `uvicorn app:app --reload` ou `python3 start.py` (respeita `DEBUG` no `.env`).

**Ambiente virtual:** o `venv/` deve ser criado **nesta pasta do repositório**. Se os scripts em `venv/bin/` apontarem para outro caminho de máquina, execute `bash fix_venv.sh` (escolhe `python3.13` do PATH, p.ex. Homebrew). Não existe `alembic/__init__.py` na pasta de migrações — evita que o directório `alembic/` *sombreie* o pacote PyPI `alembic`.

Detalhes e Docker: ver `INICIAR.md`.

## Variáveis de ambiente (resumo)

| Variável | Notas |
|----------|--------|
| `SECRET_KEY` | Obrigatório fora de `DEBUG` se não for o valor por defeito (inseguro). |
| `DATABASE_URL` | Uma única URL para app, Alembic e `seed_data`. Em desenvolvimento suportado: PostgreSQL Docker local. |
| `DEFAULT_EMPRESA_ID` | Opcional; com `DEBUG` + `DEMO_GERAR_SEM_AUTH` e sem JWT, usada em `POST /api/gerar` (por defeito UUID da empresa de teste do seed). |
| `CORS_ORIGINS` | Lista separada por vírgulas. Em produção com lista vazia, o app cai em origens locais (avisar no log). |
| `DEMO_GERAR_SEM_AUTH` | `true` = endpoints de geração aceitam pedidos sem JWT (só para demo). |
| `ALLOW_OPEN_REGISTRO` | `true` = `POST /api/auth/registro` ativo. |
| `CREATE_ALL_ON_START` | `true` (default em DEBUG) = `criar_tabelas()`; em produção usar **`alembic upgrade head`** e tipicamente `false`. |
| `OPENAI_API_KEY` | Habilita modelos diretos OpenAI via LiteLLM; default recomendado `openai-gpt-5.5`. |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Habilita modelos diretos Gemini via LiteLLM. |
| `OPENROUTER_API_KEY` | Habilita modelos OpenRouter (`queen-3.6`, `glm-5-1`, `kimi-k2.5`). |
| `MENUAI_DEFAULT_LLM_MODEL` | Id interno opcional quando o pedido não envia `llm_model`; default `openai-gpt-5.5`. |
| `OPENROUTER_DEFAULT_MODEL` | Legado; ainda aceito se `MENUAI_DEFAULT_LLM_MODEL` estiver vazio. |
| `MENUAI_APP_TITLE` / `OPENROUTER_HTTP_REFERER` | Opcional; headers de atribuição OpenRouter. |
| `FICHAS_DB_STATS_TTL` | Segundos de cache em memória para `/api/info` e mensagens de progresso (fichas SQL). |
| `MENUAI_FICHAS_IMPORT_XLSX` | Caminho do `.xlsx` apenas para `seed_data.py` (importação inicial; não usado em runtime). |

## Banco e migrações

- **Mesma `DATABASE_URL`:** `database/connection.py` e `alembic/env.py` partilham a mesma URL do PostgreSQL configurado no `.env`.
- **Produção:** aplicar **apenas** `alembic upgrade head` — evitar `create_all` (drift de schema).
- **Dev:** `CREATE_ALL_ON_START=true` ou chamar `criar_tabelas()` manualmente.
- **Script:** com `venv` ativo: `bash scripts/alembic_upgrade.sh` (lê `DATABASE_URL` do `.env`). Diagnóstico: `python3 scripts/verify_stack.py`; smoke local: `python3 scripts/smoke_flow.py` (ver `INICIAR.md`).

## Módulos principais

- `app.py` — composição, CORS, limites, rotas de geração/stream; `empresa_id` em `POST /api/gerar` preenchido pelo JWT se o body omitir.
- `services/geracao.py` — worker de geração e reidratação de jobs a partir de `JobAgente`.
- `services/job_state.py` — dicionário de jobs em memória.
- `services/fichas_db_stats.py` — contagens e categorias a partir de `FichaTecnica` / `Ingrediente` (cache TTL).
- `services/receitas_stats.py` — *shim* legado que reexporta `fichas_db_stats` (evita imports antigos a falharem).
- `pipeline/llm_providers.py` / `pipeline/openrouter_models.py` — catálogo LLM multi-provider; `GET /api/llm-models`.
- `pipeline/orchestrator.py` — configura contexto; `run()` delega a `run_lite_pipeline`.
- `tools/` — ferramentas LLM (`compat.py` prefere `langchain_core`).

## Fase 2 (opcional)

Se precisar de *checkpoint*, retomar após falha ou HITL, o grafo lógico pode ser modelado em **LangGraph** reutilizando as mesmas etapas e *tools* — ver item no plano de auditoria; não implementado no código base.

## Scripts legados

Ficheiros `scripts/patches/patch_*.py` — experimentos antigos; não são parte do fluxo de arranque.

---

## Arquitetura de alto nível

### Modelo two-process

```
┌──────────────────┐         ┌──────────────────┐
│  API Principal    │         │  Admin Panel      │
│  app.py :8000    │◄───────►│  admin/main.py     │
│  (FastAPI)       │  shared │  (FastAPI + Next.js)
│                  │   DB    │  :8001             │
└────────┬─────────┘         └────────┬─────────┘
         │                            │
         └────────────┬───────────────┘
                      │
              ┌───────▼────────┐
              │  PostgreSQL     │
              │  (Docker ou     │
              │   Supabase)     │
              └────────────────┘
```

- **API principal** (`app.py`): serve endpoints públicos, autenticação JWT, geração de cardápios via LLM pipeline, CRUD multi-tenant.
- **Admin** (`admin/main.py`): segundo processo ASGI na porta 8001. Reutiliza os routers de domínio da API principal substituindo `get_usuario_atual` por `get_usuario_admin` (JWT admin/super_admin ou `X-Admin-Api-Key`). Frontend em **Next.js** (`admin/src/`).

### Pipeline de 7 etapas (geração de cardápios)

Cada etapa é um agente LLM com ferramentas específicas, executado sequencialmente via `litellm.completion()`:

1. **Analista de Contratos** — lê contrato (PDF/arquivo), extrai regras de negócio
2. **Gestor de Fichas Técnicas** — consulta repertório de pratos do banco
3. **Nutricionista** — planeja cardápios respeitando regras nutricionais
4. **Analista Nutricional** — valida conformidade do cardápio gerado
5. **Controller Financeiro** — verifica custos vs. metas
6. **Agente de Compras** — gera lista de compras de insumos
7. **Exportador** — consolida e formata cardápio final

Execução: `pipeline/orchestrator.py` → `pipeline/litellm_runner.py` → `pipeline/sequential_spec.py`

### Camada de dados

- **ORM**: SQLAlchemy 2.0 com declarative base em `database/connection.py`
- **Migrações**: Alembic (`alembic/versions/`)
- **Multi-tenant**: todas as entidades ligadas a `Empresa` via foreign key
- **Vector search**: Supabase pgvector para semantic knowledge base (`services/knowledge_base.py`)

### Routers da API (`/api/*`)

| Router | Prefixo | Responsabilidade |
|--------|---------|-----------------|
| `routers/auth.py` | `/api/auth` | Login, registro, JWT local |
| `routers/auth_supabase.py` | `/api/auth` | Login, registro via Supabase Auth |
| `routers/empresas.py` | `/api/empresas` | CRUD empresas |
| `routers/contratos.py` | `/api/contratos` | CRUD contratos + upload PDF |
| `routers/ingredientes.py` | `/api/ingredientes` | CRUD ingredientes |
| `routers/fichas_tecnicas.py` | `/api/fichas-tecnicas` | CRUD fichas técnicas |
| `routers/cardapios.py` | `/api/cardapios` | CRUD cardápios + aprovação + export |
| `routers/knowledge.py` | `/api/knowledge` | Base vetorial (stats, reindex, search) |

---

## Comandos de desenvolvimento

### Local (sem Docker)

```bash
# Ativar venv
source venv/bin/activate

# Instalar deps
pip install -r requirements.txt

# Iniciar com reload (dev)
uvicorn app:app --reload
# ou
python3 start.py

# Iniciar sem reload
python3 run_server.py

# Diagnóstico rápido
python3 scripts/verify_stack.py

# Smoke test do fluxo de geração
DEBUG=true DEMO_GERAR_SEM_AUTH=true python3 scripts/smoke_flow.py
```

### Docker

```bash
# Primeiro setup
./setup.sh

# Subir/replicar
docker compose up -d --build

# Logs
docker compose logs -f app
docker compose logs -f admin

# Parar
docker compose down

# Migrações
docker compose exec app python -m alembic upgrade head
docker compose exec app python seed_data.py

# Nova migração
docker compose exec app alembic revision --autogenerate -m "descricao"
```

### Admin (Next.js frontend)

```bash
cd admin/
npm install
npm run dev        # dev server Next.js
npm run build      # build produção
```

### Testes

O projeto não possui suite de testes formal. Existem 3 scripts de smoke/conexão:

```bash
python3 test_import.py   # valida imports
python3 test_llm.py      # testa conexão LLM
python3 test_anthropic.py # testa conexão Anthropic
```

---

## Convenções e notas

- **Ids**: UUIDs como strings (`str(uuid.uuid4())`), não `UUID` nativo do PostgreSQL.
- **Autenticação**: dois modos — JWT local (`routers/auth.py`) ou Supabase Auth (`routers/auth_supabase.py`). O admin usa `get_usuario_admin` em `admin/deps.py`.
- **Tools LLM**: `tools/compat.py` abstrai `langchain_core.tools.BaseTool` para fallback.
- **Jobs assíncronos**: `services/job_state.py` (dict em memória) + `services/geracao.py` (worker background).
- **Seed**: `seed_data.py` popula empresa de teste, usuário admin, ingredientes e fichas técnicas iniciais.
