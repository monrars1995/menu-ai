# Story 6.2: configuracao-administrativa-de-modelos-llm

Status: ready-for-dev

## Story

As a super_admin,  
I want controlar modelos e politicas de execucao de LLM,  
so that a plataforma mantenha governanca tecnica.

## Acceptance Criteria

1. Given painel administrativo habilitado, When super_admin altera configuracao de modelo, Then mudancas sao persistidas e refletidas no fluxo de geracao, And tentativas sem permissao sao bloqueadas.

## Tasks / Subtasks

- [ ] Consolidar catálogo e configuração em OpenRouter-first (AC: 1)
  - [ ] Revisar `pipeline/openrouter_models.py` e `pipeline/llm_providers.py` para catálogo efetivo.
  - [ ] Garantir IDs internos suportados e default consistente.
- [ ] Validar endpoints admin de toggle de modelos (AC: 1)
  - [ ] Revisar `admin/routers/llm_admin.py` (`GET` e `PATCH`).
  - [ ] Garantir persistência em `llm_model_config` e reflexo em `/api/llm-models`.
- [ ] Alinhar UI admin para troca prática de modelo (AC: 1)
  - [ ] Validar consumo em `admin/src/app/llm/page.tsx` e `admin/static/admin.js`.
  - [ ] Garantir feedback de permissão para perfis não admin.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `admin/routers/llm_admin.py`
- `pipeline/openrouter_models.py`
- `pipeline/llm_providers.py`
- `admin/src/app/llm/page.tsx`
- `admin/static/admin.js`

### Regras de implementação (guardrails)

- Não aceitar `model_id` fora do catálogo suportado.
- Não permitir alteração por usuário sem role admin/super_admin.
- Mudanças de configuração devem ser refletidas sem inconsistência entre API pública e painel.

### Testes mínimos esperados nesta história

- Admin lista modelos com status `enabled`.
- Toggle de modelo persiste e aparece em nova leitura.
- Usuário não autorizado recebe 403 ao tentar alterar modelo.

### Dependências e sequência

- Depende de Epic 1 (RBAC).
- Pode rodar em paralelo com `6.1` e `6.3`.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.2: Configuracao administrativa de modelos LLM]
- [Source: admin/routers/llm_admin.py]
- [Source: pipeline/openrouter_models.py]
- [Source: pipeline/llm_providers.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para governança administrativa de modelos LLM no fluxo OpenRouter.

### File List

- _bmad-output/implementation-artifacts/6-2-configuracao-administrativa-de-modelos-llm.md
