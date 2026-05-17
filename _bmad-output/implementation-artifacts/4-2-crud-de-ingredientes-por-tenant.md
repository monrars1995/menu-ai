# Story 4.2: crud-de-ingredientes-por-tenant

Status: ready-for-dev

## Story

As a nutricionista,  
I want gerenciar ingredientes e custos unitarios,  
so that os calculos de ficha reflitam a realidade operacional.

## Acceptance Criteria

1. Given usuario com permissao, When cria, altera, lista ou consulta ingredientes, Then operacoes respeitam escopo de empresa, And custo e unidade ficam disponiveis para composicao de fichas.

## Tasks / Subtasks

- [ ] Consolidar CRUD de ingredientes por tenant (AC: 1)
  - [ ] Revisar endpoints em `routers/ingredientes.py`.
  - [ ] Garantir tratamento correto de ingredientes globais (`empresa_id=None`) para `super_admin`.
- [ ] Garantir integridade de custos e unidade (AC: 1)
  - [ ] Validar campos de custo/fator de correção e limites de entrada.
  - [ ] Confirmar que atualizações sensíveis disparam recálculo em cascata quando necessário.
- [ ] Preservar filtros e paginação para operação diária (AC: 1)
  - [ ] Validar filtros por categoria, busca textual, ativos e inclusão de globais.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `routers/ingredientes.py`
- `services/cascata.py`
- `database/models.py`
- `database/schemas.py`

### Regras de implementação (guardrails)

- Usuário não-super-admin não cria ingrediente global.
- Não permitir edição de ingrediente fora do escopo de empresa.
- Não quebrar uso de ingredientes globais no cálculo de fichas.

### Testes mínimos esperados nesta história

- CRUD de ingrediente por tenant com filtros funcionando.
- Edição de custo/fator dispara recálculo de fichas relacionadas.
- Bloqueio 403 para edição fora do escopo.

### Dependências e sequência

- Pode executar em paralelo com `4.1`.
- Base para `4.3`.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2: CRUD de ingredientes por tenant]
- [Source: routers/ingredientes.py]
- [Source: services/cascata.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para gestão de ingredientes e custos por escopo organizacional.

### File List

- _bmad-output/implementation-artifacts/4-2-crud-de-ingredientes-por-tenant.md
