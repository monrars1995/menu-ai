# Story 1.1: subir-stack-base-em-ambiente-oficial

Status: ready-for-dev

## Story

As a admin de plataforma,  
I want executar a stack base em Docker com banco PostgreSQL/Supabase,  
so that o time tenha ambiente consistente para desenvolvimento e validacao.

## Acceptance Criteria

1. Given o repositorio com configuracoes de runtime, When o ambiente e inicializado, Then API e componentes essenciais ficam disponiveis, And as migracoes sao aplicadas com falha explicita em caso de erro.

## Tasks / Subtasks

- [ ] Garantir bootstrap Docker consistente para API e admin (AC: 1)
  - [ ] Revisar e alinhar `docker-compose.yml` para suportar fluxo oficial local e modo Supabase sem ambiguidade.
  - [ ] Verificar healthchecks de `app` e `admin` com timeout/retries adequados.
  - [ ] Validar que o startup da API aplica migracoes de forma idempotente (`scripts/docker_app_start.sh`).
- [ ] Garantir validações de ambiente no runtime local (AC: 1)
  - [ ] Confirmar comportamento de falha explicita para banco invalido em `run_server.py` e `start.py`.
  - [ ] Alinhar mensagens de erro para orientar setup de PostgreSQL/Supabase.
- [ ] Padronizar setup de desenvolvimento e documentação operacional (AC: 1)
  - [ ] Revisar `setup.sh` para refletir stack suportada sem fallback silencioso.
  - [ ] Validar que `INICIAR.md` e `README.md` estão compatíveis com o fluxo real de boot.
- [ ] Validar stack fim-a-fim (AC: 1)
  - [ ] Rodar `python3 scripts/verify_stack.py` com DB PostgreSQL/Supabase configurado.
  - [ ] Executar smoke básico (`scripts/smoke_flow.py`) quando credenciais LLM estiverem válidas.

## Dev Notes

### Contexto funcional e técnico

- Esta história prepara o terreno para as demais do Epic 1; não deve implementar RBAC/tenant scope ainda, apenas garantir base operacional confiável.
- O projeto já possui stack ativa com:
  - API FastAPI (`app.py`)
  - Admin Next.js (`Dockerfile.admin`)
  - Frontend menu Next.js (`Dockerfile.menu`, não sobe via compose atual)
  - Banco PostgreSQL em modo local Docker e/ou Supabase Cloud.

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `docker-compose.yml`
  - Serviços atuais: `app`, `admin`
  - `app` usa `SUPABASE_DB_URL` e define `DATABASE_URL` a partir dele
  - Healthcheck API em `/api/health`
- `scripts/docker_app_start.sh`
  - Aguarda DB com `SELECT 1`
  - Faz `alembic stamp heads` quando schema existe sem `alembic_version`
  - Executa `alembic upgrade heads`
- `run_server.py`
  - `ensure_dev_postgres()` bloqueia SQLite explicitamente
- `start.py`
  - Valida `SUPABASE_DB_URL`/`DATABASE_URL` e bloqueia SQLite
- `setup.sh`
  - Faz validação de Docker e sobe stack com `docker compose up -d --build ...`
  - Ainda imprime banner `v3.2.0`; considerar alinhamento de versão textual
- `scripts/verify_stack.py`
  - Diagnóstico de conexão, contagens e OpenRouter key
- `scripts/smoke_flow.py`
  - Smoke de `/api/health`, `/api/info`, `/api/gerar`, `/api/status`, stream

### Regras de implementação (guardrails)

- Não introduzir fallback para SQLite no fluxo suportado.
- Qualquer falha de conexão/migração deve ser explícita e acionável.
- Não alterar contratos de endpoint nesta história.
- Preservar idempotência do startup de migração no container.
- Não quebrar execução existente de `docker compose up -d --build`.

### Testes mínimos esperados nesta história

- Subida da stack com Docker Desktop ativo.
- `docker compose ps` com `app` e `admin` saudáveis.
- `python3 scripts/verify_stack.py` retornando conexão OK.
- Smoke com `scripts/smoke_flow.py` (quando chaves estiverem configuradas).

### Dependências e sequência

- Não depende de histórias futuras.
- Habilita diretamente as histórias `1.2`, `1.3` e `1.4`.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1: Fundacao de Plataforma e Seguranca Multi-tenant]
- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: docker-compose.yml]
- [Source: scripts/docker_app_start.sh]
- [Source: run_server.py]
- [Source: start.py]
- [Source: setup.sh]
- [Source: scripts/verify_stack.py]
- [Source: scripts/smoke_flow.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada com contexto completo para execução por `dev-story`.
- Fluxo de stack e validação técnica mapeados para evitar regressões de setup.

### File List

- _bmad-output/implementation-artifacts/1-1-subir-stack-base-em-ambiente-oficial.md
