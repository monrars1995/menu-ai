# Story 4.1: crud-de-fichas-tecnicas-por-tenant

Status: ready-for-dev

## Story

As a nutricionista,  
I want gerenciar fichas tecnicas da minha empresa,  
so that o motor use receitas atualizadas e corretas.

## Acceptance Criteria

1. Given usuario com permissao, When cria, altera, lista ou consulta fichas, Then operacoes respeitam escopo de empresa, And dados persistem com validacao minima obrigatoria.

## Tasks / Subtasks

- [ ] Consolidar CRUD de fichas com escopo multi-tenant (AC: 1)
  - [ ] Revisar endpoints em `routers/fichas_tecnicas.py` (`listar`, `criar`, `buscar`, `atualizar`, `desativar`).
  - [ ] Garantir validação de escopo por `usuario.empresa_id` e exceção controlada de `super_admin`.
- [ ] Fortalecer validações de dados obrigatórios (AC: 1)
  - [ ] Garantir unicidade de código por empresa e validações de payload em schemas.
  - [ ] Cobrir erros de ingrediente inexistente e inconsistências de lista.
- [ ] Sincronizar indexação de conhecimento após mudanças (AC: 1)
  - [ ] Validar `sync_ficha_document` e `sync_knowledge_safe` nos fluxos de create/update/delete lógico.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `routers/fichas_tecnicas.py`
- `database/schemas.py`
- `database/models.py`
- `services/knowledge_base.py`
- `services/knowledge_hooks.py`

### Regras de implementação (guardrails)

- Não permitir leitura/escrita cruzada entre empresas.
- Não quebrar retrocompatibilidade do payload de listagem paginada.
- Não acoplar esta história ao cálculo avançado além do necessário de consistência.

### Testes mínimos esperados nesta história

- CRUD de ficha funcionando para usuário da empresa correta.
- Usuário sem escopo recebe 403 em ficha de outra empresa.
- Código duplicado na mesma empresa retorna erro de validação.

### Dependências e sequência

- Depende de Epic 1 (auth + tenant).
- Base para `4.3`.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1: CRUD de fichas tecnicas por tenant]
- [Source: routers/fichas_tecnicas.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para consolidar CRUD de fichas no escopo correto de empresa.

### File List

- _bmad-output/implementation-artifacts/4-1-crud-de-fichas-tecnicas-por-tenant.md
