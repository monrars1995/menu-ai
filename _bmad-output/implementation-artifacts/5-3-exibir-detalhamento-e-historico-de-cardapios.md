# Story 5.3: exibir-detalhamento-e-historico-de-cardapios

Status: ready-for-dev

## Story

As a usuario autorizado,  
I want abrir cardapio detalhado e historico relacionado,  
so that eu revise conteudo antes de exportar/publicar.

## Acceptance Criteria

1. Given cardapios persistidos, When usuario abre detalhe ou lista historica, Then sistema retorna metadados e composicao consultavel, And acesso respeita papel e tenant.

## Tasks / Subtasks

- [ ] Consolidar listagem e detalhamento de cardápios (AC: 1)
  - [ ] Revisar `GET /api/cardapios` e `GET /api/cardapios/{id}`.
  - [ ] Garantir filtros por status/contrato e paginação estável.
- [ ] Garantir histórico consultável de aprovação e execução (AC: 1)
  - [ ] Expor informações de job e aprovações associadas quando aplicável.
  - [ ] Validar consistência entre detalhe de cardápio e histórico de ações.
- [ ] Alinhar UI para navegação eficiente (AC: 1)
  - [ ] Revisar consumo de endpoints no menu para abrir histórico e detalhe sem perda de contexto.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `routers/cardapios.py`
- `menu/src/lib/api.ts`
- `menu/src/lib/types.ts`
- telas de cardápio no frontend menu

### Regras de implementação (guardrails)

- Não permitir visualização de cardápio fora do tenant.
- Não remover campos úteis de metadados para suporte/auditoria.
- Manter contratos de paginação estáveis para listas longas.

### Testes mínimos esperados nesta história

- Listagem retorna paginação e filtros corretos.
- Detalhe de cardápio retorna composição completa no escopo correto.
- Acesso fora de escopo retorna 403.

### Dependências e sequência

- Depende de `5.1` e `5.2`.
- Base imediata para `5.4`.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3: Exibir detalhamento e historico de cardapios]
- [Source: routers/cardapios.py]
- [Source: menu/src/lib/api.ts]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para cobertura de histórico e revisão operacional de cardápios.

### File List

- _bmad-output/implementation-artifacts/5-3-exibir-detalhamento-e-historico-de-cardapios.md
