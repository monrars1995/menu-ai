# Story 5.2: implementar-workflow-de-aprovacao

Status: ready-for-dev

## Story

As a gestor,  
I want aprovar ou reprovar cardapios por status,  
so that governanca operacional seja aplicada antes da publicacao.

## Acceptance Criteria

1. Given cardapio em estado elegivel, When usuario autorizado executa transicao, Then status e atualizado conforme regra de aprovacao, And acao fica registrada para auditoria.

## Tasks / Subtasks

- [ ] Consolidar transições de aprovação no backend (AC: 1)
  - [ ] Revisar `POST /api/cardapios/{id}/aprovacao` em `routers/cardapios.py`.
  - [ ] Garantir mapeamento consistente: `aprovado`, `reprovado`, `solicitado_revisao`.
- [ ] Garantir histórico de decisões e rastreabilidade (AC: 1)
  - [ ] Validar persistência em `AprovacaoCardapio`.
  - [ ] Revisar `GET /api/cardapios/{id}/aprovacoes` para timeline de decisões.
- [ ] Validar controle de acesso por papel (AC: 1)
  - [ ] Confirmar acesso restrito a `super_admin/admin/gestor` para ações de aprovação.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `routers/cardapios.py`
- `database/models.py`
- `database/schemas.py`
- `menu/src/lib/api.ts`

### Regras de implementação (guardrails)

- Não permitir publicação sem estado prévio `aprovado`.
- Não perder registro histórico em mudanças subsequentes.
- Não abrir endpoint de aprovação para perfis não autorizados.

### Testes mínimos esperados nesta história

- Aprovação muda status para `aprovado` e cria evento de aprovação.
- Reprovação/solicitação de revisão muda status para `em_revisao`.
- Endpoint de histórico retorna registros ordenados.

### Dependências e sequência

- Depende de `5.1`.
- Base para `5.3` e `5.4`.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2: Implementar workflow de aprovacao]
- [Source: routers/cardapios.py]
- [Source: menu/src/lib/api.ts]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para governança de status com trilha de aprovação.

### File List

- _bmad-output/implementation-artifacts/5-2-implementar-workflow-de-aprovacao.md
