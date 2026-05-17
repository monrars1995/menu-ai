# Story 5.1: persistir-cardapio-e-contexto-de-geracao

Status: ready-for-dev

## Story

As a nutricionista,  
I want salvar cardapios gerados com contexto completo,  
so that eu recupere o historico com rastreabilidade.

## Acceptance Criteria

1. Given geracao concluida, When o resultado e salvo, Then cardapio, parametros e referencias de job/sessao ficam persistidos, And dados podem ser consultados posteriormente.

## Tasks / Subtasks

- [ ] Consolidar persistência de resultado de geração (AC: 1)
  - [ ] Revisar `services/geracao.py` para garantir gravação de `Cardapio` e atualização de `JobAgente`.
  - [ ] Validar vínculo de `job_id`, `contrato_id`, `empresa_id`, parâmetros e resultado bruto.
- [ ] Garantir persistência de contexto conversacional (AC: 1)
  - [ ] Revisar `routers/chat.py` para criação/consulta de sessão e mensagens.
  - [ ] Validar segurança de acesso por usuário/tenant nas sessões.
- [ ] Validar consulta posterior de cardápio persistido (AC: 1)
  - [ ] Confirmar leitura por `GET /api/cardapios/{id}` com detalhe completo.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `services/geracao.py`
- `routers/cardapios.py`
- `routers/chat.py`
- `database/models.py`

### Regras de implementação (guardrails)

- Não persistir cardápio sem escopo de empresa resolvido.
- Não perder referência de `job_id` no ciclo de conclusão.
- Não permitir acesso cruzado ao contexto de sessão.

### Testes mínimos esperados nesta história

- Job concluído grava `Cardapio` e atualiza `JobAgente` como concluído.
- Sessão de chat vinculada a job pode ser recuperada pelo dono.
- Consulta de cardápio preserva dados de contexto e escopo.

### Dependências e sequência

- Depende de Epic 3 (geração funcional).
- Base para `5.2`, `5.3` e `5.4`.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1: Persistir cardapio e contexto de geracao]
- [Source: services/geracao.py]
- [Source: routers/cardapios.py]
- [Source: routers/chat.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para persistência ponta a ponta de cardápio, job e contexto de sessão.

### File List

- _bmad-output/implementation-artifacts/5-1-persistir-cardapio-e-contexto-de-geracao.md
