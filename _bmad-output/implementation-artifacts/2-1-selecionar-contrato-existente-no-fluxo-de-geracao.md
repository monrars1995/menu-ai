# Story 2.1: selecionar-contrato-existente-no-fluxo-de-geracao

Status: ready-for-dev

## Story

As a nutricionista,  
I want escolher contratos ja cadastrados no inicio do fluxo,  
so that eu evite retrabalho de upload quando o contrato ja existe.

## Acceptance Criteria

1. Given contratos disponiveis para a empresa, When o usuario inicia a geracao, Then o sistema lista contratos elegiveis para selecao, And guarda o contrato selecionado no contexto da sessao.

## Tasks / Subtasks

- [ ] Garantir listagem de contratos por escopo de empresa no backend (AC: 1)
  - [ ] Revisar `GET /api/contratos/` em `routers/contratos.py` para respeitar tenant e paginação.
  - [ ] Validar retorno consistente de metadados (`items`, `total`, `page`, `per_page`, `pages`).
- [ ] Integrar seleção de contrato no wizard/chat flow (AC: 1)
  - [ ] Validar carregamento inicial em `menu/src/components/wizard/ContractUpload.tsx`.
  - [ ] Garantir persistência de `contrato_id` escolhido no estado de geração.
- [ ] Propagar contrato selecionado para o pedido de geração (AC: 1)
  - [ ] Confirmar montagem de payload em `menu/src/lib/api.ts` e tela de geração (`menu/src/app/(app)/gerar/page.tsx`).
  - [ ] Validar que `/api/gerar` recebe `contrato_id` e usa no pipeline.

## Dev Notes

### Contexto funcional e técnico

- O backend já oferece listagem de contratos com escopo por tenant e endpoint de geração aceita `contrato_id`.
- O frontend já possui componente de seleção; foco é garantir consistência de estado e UX de transição.

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `routers/contratos.py`
- `menu/src/components/wizard/ContractUpload.tsx`
- `menu/src/lib/api.ts`
- `menu/src/app/(app)/gerar/page.tsx`
- `app.py` (`POST /api/gerar`)

### Regras de implementação (guardrails)

- Não permitir listagem/seleção de contratos fora do tenant do usuário.
- Não acoplar seleção de contrato a upload obrigatório.
- Preservar comportamento de `super_admin` com filtro explícito de empresa quando necessário.

### Testes mínimos esperados nesta história

- Usuário autenticado vê somente contratos da própria empresa no wizard.
- Seleção de contrato existente propaga `contrato_id` até o job criado.
- Geração inicia sem upload quando contrato existente foi selecionado.

### Dependências e sequência

- Depende de `1.2` (escopo de tenant).
- Base para `2.3` (interpretação/persistência de regras).

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1: Selecionar contrato existente no fluxo de geracao]
- [Source: routers/contratos.py]
- [Source: menu/src/components/wizard/ContractUpload.tsx]
- [Source: menu/src/lib/api.ts]
- [Source: app.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para consolidar escolha de contrato existente no fluxo inicial de geração.

### File List

- _bmad-output/implementation-artifacts/2-1-selecionar-contrato-existente-no-fluxo-de-geracao.md
