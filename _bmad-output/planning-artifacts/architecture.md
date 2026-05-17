---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/product-brief.md
  - _bmad-output/design-thinking-2026-05-16.md
  - docs/index.md
  - docs/superpowers/specs/2026-05-03-chat-upload-inline-design.md
  - docs/superpowers/specs/2026-05-03-gerar-cardapio-chat-design.md
  - docs/superpowers/specs/2026-05-05-chat-conversacional-premium.md
  - docs/v2-fichas-ia-design.md
workflowType: 'architecture'
project_name: 'MENU I.A'
user_name: 'Monrars'
date: '2026-05-16'
lastStep: 8
status: 'complete'
completedAt: '2026-05-16'
---

# Architecture Decision Document

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**  
O produto exige isolamento multi-tenant, autenticacao com RBAC, interpretacao de contratos, fluxo conversacional de geracao, pipeline IA com explicabilidade, persistencia de cardapios/jobs/sessoes e exportacao operacional.

**Non-Functional Requirements:**  
Baixa latencia nos endpoints de estado, seguranca de segredos, confiabilidade em jobs assincronos, escalabilidade de 10x, acessibilidade minima e contratos de integracao estaveis.

**Scale & Complexity:**  
Complexidade `medium` com risco operacional alto por impacto em custo e conformidade contratual.  
Dominio principal: `SaaS B2B de planejamento alimentar`.

### Technical Constraints & Dependencies

- Banco principal PostgreSQL (Supabase em nuvem)
- Vetorizacao em `pgvector`
- Gateway LLM centralizado via OpenRouter
- Containers Docker para reproducao local/producao
- Stack existente em FastAPI + Next.js (menu/admin)

### Cross-Cutting Concerns Identified

- Isolamento por `empresa_id` em toda leitura/escrita
- Trilha de auditoria para aprovacoes e operacoes sensiveis
- Coerencia de status de job entre API, banco e interface
- Padronizacao de tratamento de erro e mensagens operacionais

## Starter Template Evaluation

### Primary Technology Domain

Backend/API multi-tenant com frontends web acoplados.

### Starter Options Considered

- Reaproveitar base existente do repositorio (escolhido)
- Rebootstrap de API em novo boilerplate (descartado)
- Rebootstrap de frontends em novo boilerplate (descartado)

### Selected Starter: Existing Repository Baseline

**Rationale for Selection:**  
Ja existe base funcional com modelos, migracoes, endpoints e fluxo de geracao; o menor risco tecnico e evoluir sobre a estrutura atual.

**Initialization Command:**

```bash
docker compose up -d --build
```

**Architectural Decisions Provided by Starter:**

- Runtime API: Python/FastAPI
- Frontend: Next.js em apps separados (`menu` e `admin`)
- Banco: PostgreSQL/Supabase via SQLAlchemy + Alembic
- Execucao local: Docker Compose

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

- Estrategia unica de tenant scope por `empresa_id`
- Padrao oficial de autenticacao JWT Supabase com RBAC local
- Contrato de job assincrono para pipeline de geracao
- Modelo de persistencia para cardapio, sessao e mensagens

**Important Decisions (Shape Architecture):**

- OpenRouter como gateway unico de LLM
- Modelo de explainability no fluxo conversacional
- Estrategia de deduplicacao de contratos por hash
- Estrategia de exportacao e consumo operacional

### Data Architecture

- Banco relacional unico por ambiente
- Entidades principais: `empresas`, `usuarios`, `contratos`, `fichas_tecnicas`, `ingredientes`, `cardapios`, `jobs_agente`, `sessoes_chat`, `mensagens_chat`
- Vetores semanticos em `knowledge_chunks.embedding` (pgvector)
- Migracoes com Alembic como fonte de verdade de schema

### Authentication & Security

- JWT validado via Supabase JWKS
- Fallback legacy controlado por configuracao
- RBAC aplicado em rotas de negocio e admin
- Segredos via `.env` local e variaveis de ambiente em runtime

### API & Communication Patterns

- REST para CRUD e operacoes administrativas
- Endpoints de job para status/stream/download
- SSE para progresso de geracao
- Respostas JSON padronizadas com codigos HTTP semanticos

### Frontend Architecture

- App Router Next.js com separacao `menu` (usuario final) e `admin` (governanca)
- UI guiada por estado de workflow no fluxo de geracao
- Atualizacao de estado via chamadas API e stream de eventos

### Infrastructure & Deployment

- Dev local suportado: Docker Desktop
- Persistencia cloud suportada: Supabase Postgres
- Build de API e frontends por Dockerfiles dedicados
- Healthchecks por container para orquestracao

### Decision Impact Analysis

**Implementation Sequence:**

1. Fundacao de acesso e tenant scope
2. Contratos + base tecnica
3. Orquestracao de geracao
4. Ciclo de vida e exportacao
5. Governanca, suporte e integracao

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Database Naming Conventions:**

- Tabelas em `snake_case` plural
- Chaves estrangeiras no formato `{entidade}_id`
- Indices no formato `idx_{tabela}_{coluna}`

**API Naming Conventions:**

- Rotas REST em plural (`/api/contratos`, `/api/cardapios`)
- Acoes especiais em sufixo semantico (`/upload`, `/analise`, `/exportar`)
- Query params em `snake_case`

**Code Naming Conventions:**

- Python com `snake_case` para funcoes/variaveis
- Componentes React em `PascalCase`
- Arquivos TSX em `kebab-case` quando padrao local exigir

### Structure Patterns

- Routers FastAPI por dominio (`routers/`)
- Regras de negocio em `services/`
- Ferramentas de agente em `tools/`
- Frontend separado por app (`menu/`, `admin/`)

### Format Patterns

- Datas em ISO-8601
- Erros de API com status + detalhe textual
- Campos JSON em `snake_case` no backend e mapeamento no frontend quando necessario

### Communication Patterns

- Eventos de progresso emitidos por SSE
- Jobs como unidade de comunicacao assincrona
- Mensagens de chat persistidas para rastreabilidade de sessao

### Process Patterns

- Falha explicita sem fallback silencioso de banco em ambiente suportado
- Retry controlado para operacoes externas
- Logs orientados a diagnostico de job e integracao

### Enforcement Guidelines

- Todo endpoint novo deve validar tenant scope
- Toda nova funcionalidade de negocio deve mapear para FR/NFR do PRD
- Todo fluxo assincrono deve persistir estado consultavel

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
MENU I.A/
├── app.py
├── run_server.py
├── start.py
├── Dockerfile
├── Dockerfile.admin
├── Dockerfile.menu
├── docker-compose.yml
├── requirements.txt
├── alembic/
├── database/
├── routers/
├── services/
├── tools/
├── pipeline/
├── menu/
└── admin/
```

### Architectural Boundaries

**API Boundaries:**

- Frontends comunicam apenas com API HTTP
- Integracoes externas entram por endpoints dedicados

**Component Boundaries:**

- `menu`: experiencia operacional
- `admin`: configuracao e governanca

**Service Boundaries:**

- `services/geracao.py`: execucao de pipeline
- `services/job_state.py`: estado de jobs
- `services/fichas_db_stats.py`: estatisticas e cache

**Data Boundaries:**

- ORM central em `database/models.py`
- Schemas de I/O em `database/schemas.py`

### Requirements to Structure Mapping

- FRs de auth/tenant: `routers/auth_supabase.py`, `routers/auth.py`, `routers/empresas.py`
- FRs de contratos: `routers/contratos.py`, `services/contract_*`
- FRs de geracao: `app.py`, `services/geracao.py`, `pipeline/*`
- FRs de fichas/ingredientes: `routers/fichas.py`, `routers/ingredientes.py`, `tools/db_tools.py`
- FRs de ciclo de vida/exportacao: `routers/cardapios.py`

## Architecture Validation Results

### Coherence Validation ✅

- Decisoes de stack e execucao estao alinhadas com o repositorio existente.
- Padroes de naming/estrutura reduzem conflito entre agentes e contribuidores.
- Limites entre front, API e dados estao claros para evolucao incremental.

### Requirements Coverage Validation ✅

- Todas as areas funcionais do PRD possuem suporte arquitetural.
- Requisitos de confiabilidade, seguranca e integracao foram tratados como restricoes de desenho.
- Suporte a explainability e fallback de custo esta contemplado no fluxo de geracao.

### Implementation Readiness Validation ✅

- Estrutura do projeto e boundaries definidos.
- Sequenciamento de implementacao claro.
- Dependencias externas e pontos de risco mapeados.

### Gap Analysis Results

**Critical Gaps:** nenhum bloqueador identificado.  
**Important Gaps:** detalhar contratos de API por endpoint em documento de interface.  
**Nice-to-Have Gaps:** expandir matriz de observabilidade por metrica e alerta.

## Completion & Handoff

Arquitetura concluida e pronta para decomposicao em epicos e historias.  
Este documento e a referencia tecnica principal para consistencia de implementacao por equipes e agentes.
