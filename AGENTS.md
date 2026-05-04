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
| `DATABASE_URL` | Uma única URL para app, Alembic e `seed_data`. Se vazia: SQLite em `menuai_test.db` na **raiz do repo** (caminho absoluto). |
| `DEFAULT_EMPRESA_ID` | Opcional; com `DEBUG` + `DEMO_GERAR_SEM_AUTH` e sem JWT, usada em `POST /api/gerar` (por defeito UUID da empresa de teste do seed). |
| `CORS_ORIGINS` | Lista separada por vírgulas. Em produção com lista vazia, o app cai em origens locais (avisar no log). |
| `DEMO_GERAR_SEM_AUTH` | `true` = endpoints de geração aceitam pedidos sem JWT (só para demo). |
| `ALLOW_OPEN_REGISTRO` | `true` = `POST /api/auth/registro` ativo. |
| `CREATE_ALL_ON_START` | `true` (default em DEBUG) = `criar_tabelas()`; em produção usar **`alembic upgrade head`** e tipicamente `false`. |
| `OPENROUTER_API_KEY` | **Produção:** chave em [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys); LiteLLM usa modelos `openrouter/...`. Sem esta chave (e sem legacy), a geração falha ao iniciar o worker. |
| `OPENROUTER_DEFAULT_MODEL` | Id interno opcional (`queen-3.6`, `glm-5-1`, `kimi-k2.5`) quando o pedido não envia `llm_model`. |
| `OPENROUTER_SLUG_*` | Overrides opcionais dos slugs OpenRouter — ver `.env.example`. |
| `MENUAI_LLM_LEGACY` | `true` = cadeia antiga Groq/OpenAI/Anthropic/Qwen/Ollama (só dev); ignora seleção OpenRouter da UI. |
| `MENUAI_APP_TITLE` / `OPENROUTER_HTTP_REFERER` | Opcional; headers de atribuição OpenRouter. |
| `FICHAS_DB_STATS_TTL` | Segundos de cache em memória para `/api/info` e mensagens de progresso (fichas SQL). |
| `MENUAI_FICHAS_IMPORT_XLSX` | Caminho do `.xlsx` apenas para `seed_data.py` (importação inicial; não usado em runtime). |
| Chaves legacy (`GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, …) | Só com `MENUAI_LLM_LEGACY=true`. |

## Banco e migrações

- **Mesma `DATABASE_URL`:** `database/connection.py` e `alembic/env.py` partilham a URL resolvida (defeito SQLite na raiz do projecto se a env estiver vazia).
- **Produção:** aplicar **apenas** `alembic upgrade head` — evitar `create_all` (drift de schema).
- **Dev:** `CREATE_ALL_ON_START=true` ou chamar `criar_tabelas()` manualmente.
- **Script:** com `venv` ativo: `bash scripts/alembic_upgrade.sh` (lê `DATABASE_URL` do `.env`). Diagnóstico: `python3 scripts/verify_stack.py`; smoke local: `python3 scripts/smoke_flow.py` (ver `INICIAR.md`).

## Módulos principais

- `app.py` — composição, CORS, limites, rotas de geração/stream; `empresa_id` em `POST /api/gerar` preenchido pelo JWT se o body omitir.
- `services/geracao.py` — worker de geração e reidratação de jobs a partir de `JobAgente`.
- `services/job_state.py` — dicionário de jobs em memória.
- `services/fichas_db_stats.py` — contagens e categorias a partir de `FichaTecnica` / `Ingrediente` (cache TTL).
- `services/receitas_stats.py` — *shim* legado que reexporta `fichas_db_stats` (evita imports antigos a falharem).
- `pipeline/openrouter_models.py` — catálogo OpenRouter (ids UI ↔ slug); `GET /api/llm-models`.
- `pipeline/orchestrator.py` — configura contexto; `run()` delega a `run_lite_pipeline`.
- `tools/` — ferramentas LLM (`compat.py` prefere `langchain_core`).

## Fase 2 (opcional)

Se precisar de *checkpoint*, retomar após falha ou HITL, o grafo lógico pode ser modelado em **LangGraph** reutilizando as mesmas etapas e *tools* — ver item no plano de auditoria; não implementado no código base.

## Scripts legados

Ficheiros `scripts/patches/patch_*.py` — experimentos antigos; não são parte do fluxo de arranque.
