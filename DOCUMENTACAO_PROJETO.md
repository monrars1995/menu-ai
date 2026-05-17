# Menu.AI — Documentação do Projeto

> **Versão API:** 3.4.0 | **Framework:** FastAPI + Next.js | **IA:** LiteLLM + OpenAI/Gemini/OpenRouter

Documento de referência do repositório **Menu.AI**: arquitetura, operação, dados, API e pipeline de IA.

## 📖 Documentação Completa

A documentação técnica detalhada está em **[docs/index.md](docs/index.md)**, incluindo:

- Visão geral e arquitetura
- Modelo de dados (13 tabelas)
- Pipeline LLM de 7 etapas
- Autenticação e RBAC
- Endpoints da API
- Deployment (Docker Compose / Stack)
- Variáveis de ambiente
- Dependências

## Visão Geral

| Item | Descrição |
|------|-----------|
| **Nome** | Menu.AI |
| **Versão API** | 3.4.0 |
| **Propósito** | API FastAPI multi-tenant para planejamento inteligente de cardápios coletivos |
| **LLM** | OpenAI, Gemini e OpenRouter via LiteLLM (7 agentes sequenciais) |
| **Auth** | Supabase (JWKS/ES256) + fallback legado (HS256) |
| **Frontends** | Menu (Next.js :3000) + Admin (Next.js :8001) |

## Stack

- Python 3.11+ — FastAPI, Uvicorn, SlowAPI
- SQLAlchemy 2.x + Alembic — PostgreSQL (Supabase) / SQLite (dev)
- LiteLLM + LangChain — Pipeline de agentes IA
- Next.js — Frontends (menu + admin)
- Docker — Compose (dev) + Stack (produção)

## Estrutura Principal

```text
MENU I.A/
├── app.py                    # Composição FastAPI
├── run_server.py             # Entry point produção
├── start.py                  # Entry point dev
├── seed_data.py              # Seed de dados
├── database/                 # ORM, conexão, schemas
├── pipeline/                 # Motor de IA (7 etapas)
├── routers/                  # Endpoints API (auth, cardapios, fichas...)
├── services/                 # Workers, estado de jobs
├── tools/                    # Ferramentas LLM (db_tools, cardapio_tools)
├── menu/                     # Frontend público (Next.js)
├── admin/                    # Painel admin (Next.js)
├── scripts/                  # Utilitários
├── alembic/                  # Migrações
├── docker-compose.yml        # Dev
├── docker-stack.yml          # Produção
├── docs/                     # Documentação técnica
│   ├── index.md              # Doc completa
│   └── project-scan-report.json
└── .env.example
```

## Execução

```bash
# Setup
source venv/bin/activate

# Dev (com reload)
python3 start.py

# Produção
python3 run_server.py

# Docker
docker compose up -d

# Migrações
bash scripts/alembic_upgrade.sh

# Verificação
python3 scripts/verify_stack.py
```

## Arquivos de Referência

- [docs/index.md](docs/index.md) — Documentação técnica completa
- [INICIAR.md](INICIAR.md) — Guia de início rápido
- [AGENTS.md](AGENTS.md) — Contexto para agentes IA
- [CLAUDE.md](CLAUDE.md) — Instruções para Claude
- [.env.example](.env.example) — Variáveis de ambiente
- [README.md](README.md) — README do repositório

## Contato

- Instagram: @monrars
- Site: goldneuron.io
- GitHub: @monrars1995
