# Menu.AI — Documentação Técnica do Projeto

> **Versão:** 3.3.0 | **Tipo:** Backend API + Frontends Web | **Framework:** FastAPI + Next.js
> **Scan:** Deep Scan — 2026-05-16

---

## 1. Visão Geral

**Menu.AI** é um sistema inteligente de planejamento de cardápios para refeições coletivas. Utiliza uma pipeline de **7 agentes LLM sequenciais** com ferramentas reais (banco de dados SQL, análise de contratos) para gerar cardápios otimizados em custo, nutrição e conformidade regulatória.

### Características Principais

| Feature | Descrição |
|---------|-----------|
| **Multi-tenant** | Isolamento por `empresa_id` em todas as tabelas |
| **Pipeline LLM 7-etapas** | Analista → Gestor → Nutricionista → Analista Nutricional → Controller → Compras → Exportador |
| **Model Router** | Fallback cross-provider automático (OpenRouter → Groq → OpenAI → Anthropic) |
| **Fichas Técnicas** | Base de receitas com custos reais, FC, dados nutricionais e alergênicos |
| **Workflow de Aprovação** | Rascunho → Em Revisão → Aguardando Aprovação → Aprovado → Publicado |
| **Exportação** | XLSX (multi-sheet estilizado), CSV, PDF, TXT |
| **Auth Supabase** | JWKS (ES256) + fallback legado (HS256) + sincronização local |
| **RBAC** | 5 roles: super_admin, admin, nutricionista, gestor, visualizador |

---

## 2. Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     MENU.AI — Arquitetura                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │  Menu     │    │  Admin   │    │  API FastAPI (app.py)│   │
│  │  Next.js  │───▶│  Next.js │───▶│  :8000               │   │
│  │  :3000    │    │  :8001   │    │                      │   │
│  └──────────┘    └──────────┘    └──────────┬───────────┘   │
│                                              │               │
│                          ┌───────────────────┼──────────┐   │
│                          │                   │          │   │
│                   ┌──────▼──────┐  ┌────────▼───────┐  │   │
│                   │   Routers    │  │   Services     │  │   │
│                   │ auth,cardapio│  │ geracao,       │  │   │
│                   │ fichas,etc   │  │ job_state      │  │   │
│                   └──────┬──────┘  └────────┬───────┘  │   │
│                          │                   │          │   │
│                   ┌──────▼──────────────────▼───────┐  │   │
│                   │        Pipeline LLM             │  │   │
│                   │  orchestrator → sequential_spec │  │   │
│                   │  litellm_runner → model_router  │  │   │
│                   └──────────────┬──────────────────┘  │   │
│                                  │                      │   │
│                   ┌──────────────▼──────────────────┐  │   │
│                   │          Tools LLM              │  │   │
│                   │   db_tools + cardapio_tools     │  │   │
│                   └──────────────┬──────────────────┘  │   │
│                                  │                      │   │
│                   ┌──────────────▼──────────────────┐  │   │
│                   │     Database (SQLAlchemy)       │  │   │
│                   │   PostgreSQL / SQLite + Alembic │  │   │
│                   └─────────────────────────────────┘  │   │
│                                                         │   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Estrutura de Diretórios

```
MENU I.A/
├── app.py                    # Composição FastAPI, CORS, rotas, middleware
├── run_server.py             # Entry point produção (uvicorn)
├── start.py                  # Entry point dev (reload)
├── seed_data.py              # Seed de dados iniciais + importação XLSX
├── requirements.txt          # Dependências Python
├── docker-compose.yml        # Compose dev (Supabase Cloud)
├── docker-stack.yml          # Stack produção (Docker Swarm)
├── Dockerfile                # Container da API
├── Dockerfile.admin          # Container do admin
├── Dockerfile.menu           # Container do menu frontend
├── alembic.ini               # Config Alembic
│
├── database/                 # Camada de dados
│   ├── connection.py         # Engine SQLAlchemy, SessionLocal, Base
│   ├── models.py             # 13 modelos ORM (712 linhas)
│   └── schemas.py            # Schemas Pydantic para validação
│
├── pipeline/                 # Motor de IA
│   ├── orchestrator.py       # MenuOrchestrator: setup contexto + tools
│   ├── sequential_spec.py    # 7 etapas: system/user prompts + tools por agente
│   ├── litellm_runner.py     # Executor turn-based com tool calling
│   ├── model_router.py       # Fallback cross-provider + audit logging
│   ├── openrouter_models.py  # Catálogo de modelos OpenRouter (UI ↔ slug)
│   ├── llm_litellm.py        # Config LiteLLM (env resolution)
│   └── protocolo.py          # SharedContext dataclass
│
├── routers/                  # Endpoints API
│   ├── auth_supabase.py      # Auth JWT Supabase + sync local
│   ├── cardapios.py          # CRUD + workflow + exportação cardápios
│   ├── fichas.py             # CRUD fichas técnicas + ingredientes
│   ├── ingredientes.py       # CRUD ingredientes
│   ├── contratos.py          # CRUD contratos + upload PDF
│   ├── empresas.py           # CRUD empresas
│   └── chat.py               # Chat conversacional (HITL)
│
├── services/                 # Lógica de negócio
│   ├── geracao.py            # Worker background + hydration de jobs
│   ├── job_state.py          # Dicionário de jobs em memória
│   ├── fichas_db_stats.py    # Cache TTL de contagens/categorias
│   └── receitas_stats.py     # Shim legado (reexporta fichas_db_stats)
│
├── tools/                    # Ferramentas para agentes LLM
│   ├── db_tools.py           # SQL tools (fichas, contratos, histórico, vector)
│   ├── cardapio_tools.py     # Business tools (custos, nutrição, sazonalidade)
│   └── compat.py             # Compatibilidade LangChain
│
├── menu/                     # Frontend público (Next.js)
│   ├── package.json
│   └── src/
│
├── admin/                    # Painel administrativo (Next.js)
│   ├── package.json
│   └── src/
│
├── scripts/                  # Utilitários
│   ├── alembic_upgrade.sh    # Migração automatizada
│   ├── verify_stack.py       # Diagnóstico do sistema
│   ├── smoke_flow.py         # Smoke test local
│   └── patches/              # Patches experimentais legados
│
└── docs/                     # Documentação
    ├── index.md              # Este arquivo
    └── project-scan-report.json
```

---

## 4. Modelo de Dados

### Diagrama ER (Simplificado)

```
                    ┌─────────────┐
                    │   Empresa    │
                    │   (tenant)   │
                    └──────┬──────┘
          ┌────────┬───────┼───────┬─────────┐
          │        │       │       │         │
     ┌────▼───┐ ┌──▼──┐ ┌─▼──┐ ┌─▼──────┐ ┌▼────────┐
     │Usuario │ │Contr.│ │Ingr│ │FichaTec│ │Cardápio │
     └────────┘ └──┬──┘ └─┬──┘ └──┬─────┘ └──┬──────┘
                   │      │    ┌──▼────┐   ┌──▼──────┐
                   │      └────▶FichaIng│   │CardDia  │
                   │           └───────┘   └──┬──────┘
                   │                       ┌──▼──────┐
                   └───────────────────────▶CardRefeição│
                                          └──┬──────┘
                                          ┌──▼──────┐
                                          │Aprovação │
                                          └─────────┘
```

### Tabelas Principais

| # | Tabela | Descrição | FK Principal |
|---|--------|-----------|-------------|
| 1 | `empresas` | Tenant root — clientes contratantes | — |
| 2 | `usuarios` | Users com roles RBAC por empresa | `empresa_id` |
| 3 | `contratos` | Contratos de fornecimento + regras extraídas | `empresa_id` |
| 4 | `ingredientes` | Insumos com custo, FC, alérgenos, sazonalidade | `empresa_id` (nullable = global) |
| 5 | `fichas_tecnicas` | Receitas completas com nutrição e custos | `empresa_id` |
| 6 | `ficha_ingredientes` | Junction: ingredientes por receita | `ficha_tecnica_id`, `ingrediente_id` |
| 7 | `cardapios` | Cardápios gerados (período, status, job) | `empresa_id`, `contrato_id` |
| 8 | `cardapio_dias` | Dias individuais do cardápio | `cardapio_id` |
| 9 | `cardapio_refeicoes` | Pratos por dia por tipo de refeição | `dia_id`, `ficha_tecnica_id` |
| 10 | `aprovacoes_cardapio` | Workflow de aprovação | `cardapio_id`, `usuario_id` |
| 11 | `jobs_agente` | Jobs de geração IA | `empresa_id`, `cardapio_id` |
| 12 | `sessoes_chat` | Sessões de chat conversacional | `job_id` |
| 13 | `mensagens_chat` | Mensagens do chat | `sessao_id` |

---

## 5. Pipeline LLM (7 Etapas)

O pipeline executa **7 agentes sequenciais**, cada um com prompt system/user dedicado e ferramentas específicas:

| # | Agente | Ferramentas | Responsabilidade |
|---|--------|-------------|-----------------|
| 1 | **Analista de Contratos** | `ler_contrato`, `salvar_regras`, `contrato_banco`, `contexto_semantico` | Extrai regras, proibições, incidências e gramaturas do contrato |
| 2 | **Gestor de Fichas** | `fichas_banco`, `detalhe_ficha`, `listar_pratos`, `buscar_pratos`, `historico` | Seleciona repertório de pratos disponíveis com custos reais |
| 3 | **Nutricionista** | `fichas_banco`, `calcular_custo`, `sazonalidade`, `recuperar_regras` | Monta o cardápio dia-a-dia respeitando regras e nutrição |
| 4 | **Analista Nutricional** | `validar_nutri`, `fichas_banco`, `recuperar_regras` | Valida conformidade CFN/ANVISA e corrige desvios |
| 5 | **Controller Financeiro** | `calcular_custo`, `fichas_banco`, `recuperar_regras` | Valida custos por porção e por dia contra limites do contrato |
| 6 | **Agente de Compras** | `lista_compras`, `ler_contexto` | Gera lista de compras consolidada por ingrediente |
| 7 | **Exportador** | — | Consolida output final em formato estruturado |

### Fluxo de Execução

```
POST /api/gerar
  └─▶ services/geracao.py::executar_crew() [background]
       └─▶ pipeline/orchestrator.py::MenuOrchestrator.run()
            └─▶ pipeline/litellm_runner.py::run_lite_pipeline()
                 ├─▶ Etapa 1: LiteLLM + tools → contexto acumulado
                 ├─▶ Etapa 2: LiteLLM + tools → contexto acumulado
                 ├─▶ ... (7 etapas)
                 └─▶ Resultado final → salvo em JobAgente + Cardápio
```

---

## 6. Autenticação e Segurança

### Fluxo de Auth

```
Request → Bearer Token
  ├─▶ Decodifica JWT local (ES256 via JWKS do Supabase)
  │    └─▶ Se válido → extrai user_id, sincroniza com DB local
  ├─▶ Fallback: JWT legado (HS256 com SECRET_KEY)
  └─▶ Fallback remoto: GET supabase.co/auth/v1/user
       └─▶ Se válido → cria/atualiza usuário local
```

### Roles RBAC

| Role | Permissões |
|------|-----------|
| `super_admin` | Acesso total (plataforma) |
| `admin` | Admin da empresa |
| `nutricionista` | Cria/edita cardápios e fichas |
| `gestor` | Aprova cardápios, visualiza relatórios |
| `visualizador` | Somente leitura |

---

## 7. API Endpoints

### Autenticação (`/api/auth/`)
- `POST /api/auth/login` — Login com email/senha (Supabase)
- `POST /api/auth/registro` — Registro (se `ALLOW_OPEN_REGISTRO=true`)
- `GET /api/auth/me` — Dados do usuário autenticado
- `PUT /api/auth/perfil` — Atualizar perfil

### Geração de Cardápios (`/api/`)
- `POST /api/gerar` — Iniciar geração de cardápio (background job)
- `GET /api/gerar/{job_id}` — Status do job
- `GET /api/gerar/{job_id}/stream` — SSE stream de progresso
- `GET /api/llm-models` — Listar modelos LLM disponíveis

### Cardápios (`/api/cardapios/`)
- `GET /api/cardapios/` — Listar cardápios da empresa
- `GET /api/cardapios/{id}` — Detalhe do cardápio
- `POST /api/cardapios/` — Criar cardápio manual
- `PUT /api/cardapios/{id}` — Atualizar cardápio
- `DELETE /api/cardapios/{id}` — Deletar cardápio
- `POST /api/cardapios/{id}/aprovar` — Workflow de aprovação
- `GET /api/cardapios/{id}/exportar` — Exportar (XLSX/CSV/PDF/TXT)

### Fichas Técnicas (`/api/fichas/`)
- CRUD completo de receitas com ingredientes

### Outros
- `GET /api/health` — Healthcheck
- `GET /api/info` — Stats do sistema (contagens, categorias)

---

## 8. Deployment

### Docker Compose (Desenvolvimento)

```bash
# Subir
docker compose up -d

# Logs
docker compose logs -f
```

### Docker Stack (Produção)

```bash
# Build e push
docker build -t registry/menuai-app:latest .
docker build -f Dockerfile.menu -t registry/menuai-menu:latest .
docker build -f Dockerfile.admin -t registry/menuai-admin:latest .

# Deploy
docker stack deploy -c docker-stack.yml menuai
```

### Serviços

| Serviço | Porta | Container | Descrição |
|---------|-------|-----------|-----------|
| API | 8000 | menuai-app | FastAPI backend |
| Admin | 8001 | menuai-admin | Painel administrativo Next.js |
| Menu | 3000 | menuai-menu | Frontend público Next.js |

---

## 9. Variáveis de Ambiente

### Obrigatórias (Produção)

| Variável | Descrição |
|----------|-----------|
| `SECRET_KEY` | Chave forte para JWT legado (obrigatório fora de DEBUG) |
| `SUPABASE_DB_URL` / `DATABASE_URL` | URL PostgreSQL do Supabase |
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_PUBLISHABLE_KEY` | Chave pública do Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Chave de serviço do Supabase |
| `OPENROUTER_API_KEY` | Chave para API OpenRouter |

### Opcionais

| Variável | Default | Descrição |
|----------|---------|-----------|
| `DEBUG` | `false` | Modo debug |
| `CORS_ORIGINS` | `*` (debug) | Origens CORS permitidas |
| `CREATE_ALL_ON_START` | auto | Criar tabelas no startup |
| `DEMO_GERAR_SEM_AUTH` | `false` | Endpoints sem auth (demo) |
| `ALLOW_OPEN_REGISTRO` | `false` | Registro público ativo |
| `OPENROUTER_DEFAULT_MODEL` | — | Modelo padrão quando não especificado |
| `MENUAI_LLM_LEGACY` | `false` | Usar cadeia legada (Groq/OpenAI direto) |
| `LLM_TEMPERATURE` | — | Temperatura do LLM |
| `FICHAS_DB_STATS_TTL` | — | Cache TTL em segundos |

---

## 10. Dependências Principais

### Python

| Pacote | Versão | Uso |
|--------|--------|-----|
| `fastapi` | — | Framework web |
| `uvicorn` | — | Servidor ASGI |
| `sqlalchemy` | — | ORM |
| `alembic` | — | Migrações |
| `litellm` | — | Abstração de modelos LLM |
| `langchain` / `langchain-core` | — | Framework de agentes |
| `openpyxl` | — | Export XLSX |
| `reportlab` | — | Export PDF |
| `pandas` | — | Manipulação de dados |
| `PyJWT` / `python-jose` | — | Auth JWT |
| `httpx` | — | HTTP client async |
| `slowapi` | — | Rate limiting |
| `pgvector` | — | Busca vetorial (opcional) |

### Frontend (Next.js)
- `@supabase/supabase-js` — Auth e DB client
- `lucide-react` — Ícones
- `framer-motion` — Animações
- `recharts` — Gráficos

---

## 11. Comandos Úteis

```bash
# Desenvolvimento
source venv/bin/activate
uvicorn app:app --reload

# Produção
python3 run_server.py

# Migrações
bash scripts/alembic_upgrade.sh

# Seed de dados
python3 seed_data.py

# Verificação
python3 scripts/verify_stack.py
python3 scripts/smoke_flow.py

# Docker
docker compose up -d
docker compose logs -f
```

---

## 12. Próximos Passos Recomendados

1. **Auditoria de Logs** — Revisar logs do `model_router.py` para medir efetividade do fallback
2. **Otimização de Queries** — Otimizar `_enriquecer_custos_dataframe` em `cardapios.py` para volumes maiores
3. **Redesign UI** — Implementar plano em `REDESIGN_PLAN.md`
4. **Testes** — Rodar `test_import.py` e `test_llm.py` regularmente
5. **LangGraph** — Considerar migração do pipeline para LangGraph para checkpoint/retomada

---

*Gerado automaticamente pelo BMad Document Project — Deep Scan*
*Data: 2026-05-16 | Versão: 3.3.0*
