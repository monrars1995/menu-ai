# Menu.AI — Documentação do projeto

Documento de referência do repositório **Menu.AI v3.2.0**: arquitetura, operação, dados, API e pipeline de IA.

## Visão geral

| Item | Descrição |
|------|-----------|
| **Nome** | Menu.AI |
| **Versão API** | 3.2.0 |
| **Propósito** | API FastAPI multi-tenant para empresas, utilizadores, contratos, ingredientes, fichas técnicas, cardápios e jobs de geração. |
| **LLM** | OpenRouter via LiteLLM |
| **Modelos iniciais** | `queen-3.6`, `glm-5-1`, `kimi-k2.5` |
| **Front-end** | `templates/index.html` servido em `GET /` |

## Stack

- Python 3.11+
- FastAPI, Uvicorn, SlowAPI
- SQLAlchemy 2.x, Alembic
- PostgreSQL no fluxo suportado de desenvolvimento
- LiteLLM sobre OpenRouter
- Pandas, openpyxl, pdfplumber

## Estrutura principal

```text
MENU I.A/
├── app.py
├── start.py
├── run_server.py
├── crew/
├── database/
├── routers/
├── services/
├── tools/
├── templates/
├── static/
├── scripts/
├── alembic/
├── docker-compose.yml
├── .env.example
├── INICIAR.md
└── README.md
```

## Banco de dados

- O ambiente suportado de desenvolvimento usa PostgreSQL em Docker:
  `postgresql+psycopg2://menuai:menuai123@127.0.0.1:5432/menuai_db`
- `app.py`, Alembic e `seed_data.py` devem usar a mesma `DATABASE_URL`
- Migração oficial: `alembic upgrade head`

## LLM e OpenRouter

- Provider único suportado: OpenRouter
- Endpoint base: `https://openrouter.ai/api/v1`
- Catálogo interno em `crew/openrouter_models.py`
- Endpoint público: `GET /api/llm-models`
- Seleção enviada pela UI em `POST /api/gerar`

Mapeamento inicial:
- `queen-3.6` -> `qwen/qwen3.6-plus`
- `glm-5-1` -> `z-ai/glm-5.1`
- `kimi-k2.5` -> `moonshotai/kimi-k2.5`

## Endpoints principais

- `GET /api/health`
- `GET /api/info`
- `GET /api/llm-models`
- `POST /api/upload-contrato`
- `POST /api/gerar`
- `GET /api/status/{job_id}`
- `GET /api/stream/{job_id}`
- `GET /api/download/{job_id}`

## Execução

- Setup inicial: `./setup.sh`
- Servidor sem reload: `python3 run_server.py`
- Servidor dev: `python3 start.py`
- Verificação: `python3 scripts/verify_stack.py`
- Smoke: `python3 scripts/smoke_flow.py`

## Arquivos de referência

- `INICIAR.md`
- `CLAUDE.md`
- `.env.example`
- `README.md`

## Contato

- Instagram: @monrars
- Site: goldneuron.io
- GitHub: @monrars1995
