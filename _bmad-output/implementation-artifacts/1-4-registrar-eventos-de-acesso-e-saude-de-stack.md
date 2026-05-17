# Story 1.4: registrar-eventos-de-acesso-e-saude-de-stack

Status: ready-for-dev

## Story

As a suporte tecnico,  
I want consultar eventos de acesso e endpoints de saude,  
so that diagnosticos sejam rapidos e auditaveis.

## Acceptance Criteria

1. Given operacoes autenticadas e chamadas de status, When o sistema processa as requisicoes, Then eventos relevantes sao registrados com contexto minimo, And endpoints canonicos de saude/info respondem em formato consistente.

## Tasks / Subtasks

- [ ] Consolidar contrato dos endpoints canônicos de status (AC: 1)
  - [ ] Revisar `/api/health` e `/api/info` em `app.py` para garantir payload estável e campos mínimos de diagnóstico.
  - [ ] Garantir distinção explícita entre indisponibilidade de banco e indisponibilidade de contexto autenticado.
  - [ ] Confirmar coerência de escopo em `/api/info` (`empresa`, `global`, `demo`, `anonimo`).
- [ ] Ampliar trilha de auditoria operacional (AC: 1)
  - [ ] Revisar `services/audit_log.py` para manter registro de chamadas LLM (sucesso/falha) sem bloquear pipeline.
  - [ ] Definir eventos mínimos de acesso críticos para troubleshooting (auth, geração, mudança administrativa sensível).
  - [ ] Validar retenção de campos chave (`job_id`, `empresa_id`, `model_used`, `error_type`, `http_status`).
- [ ] Integrar observabilidade no painel/admin (AC: 1)
  - [ ] Verificar endpoints admin de visão agregada (`/api/admin/meta/dashboard`) para refletirem estado operacional útil.
  - [ ] Garantir que indicadores de base (`fichas`, `ingredientes`, `jobs`) respeitem escopo do usuário admin.
- [ ] Cobrir validações de saúde e auditoria com smoke/testes (AC: 1)
  - [ ] Executar smoke de stack (`scripts/verify_stack.py` e `scripts/smoke_flow.py`) após ajustes.
  - [ ] Validar falhas acionáveis quando banco/LLM estiverem indisponíveis.

## Dev Notes

### Contexto funcional e técnico

- O projeto já possui endpoints canônicos (`/api/health`, `/api/info`) e logger de chamadas LLM persistido em banco.
- O principal objetivo desta história é padronizar observabilidade e diagnóstico, não criar novo motor de logs.

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `app.py`
  - Endpoints `/api/health` e `/api/info`
  - Resolução de escopo autenticado para diagnóstico por tenant
- `services/audit_log.py`
  - Persistência de auditoria LLM com falha silenciosa controlada
- `admin/routers/meta.py`
  - Resumo operacional e contagens para suporte/admin
- `services/fichas_db_stats.py`
  - Fonte única das métricas de base exibidas no diagnóstico
- `scripts/verify_stack.py` e `scripts/smoke_flow.py`
  - Validação de saúde e fluxo ponta-a-ponta

### Regras de implementação (guardrails)

- Não incluir segredos em payloads de status, logs ou mensagens de erro.
- Não bloquear execução de geração por falha do logger de auditoria.
- Evitar novos formatos ad hoc de health/info; manter contrato estável.
- Preservar comportamento multi-tenant nos dashboards e endpoints de suporte.

### Testes mínimos esperados nesta história

- `/api/health` responde em formato consistente com status de DB.
- `/api/info` retorna contagens e erro coerente em cenários: autenticado, não autenticado, DB indisponível.
- Chamadas de geração registram auditoria LLM com sucesso/falha.
- Dashboard admin continua carregando contagens no escopo correto.

### Dependências e sequência

- Depende de `1.1` (stack) e `1.2` (auth/tenant scope) para diagnóstico confiável.
- Fecha o Epic 1 e libera execução coordenada dos Epics 2 e 3.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4: Registrar eventos de acesso e saude de stack]
- [Source: _bmad-output/planning-artifacts/architecture.md#Observability and Operations]
- [Source: app.py]
- [Source: services/audit_log.py]
- [Source: admin/routers/meta.py]
- [Source: services/fichas_db_stats.py]
- [Source: scripts/verify_stack.py]
- [Source: scripts/smoke_flow.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada com foco em diagnóstico operacional e trilha mínima de auditoria.
- Contratos canônicos de status mantidos como fonte de suporte e monitoramento.

### File List

- _bmad-output/implementation-artifacts/1-4-registrar-eventos-de-acesso-e-saude-de-stack.md
