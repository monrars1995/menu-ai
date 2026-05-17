# Story 3.1: capturar-parametros-de-geracao-via-chat-wizard

Status: ready-for-dev

## Story

As a nutricionista,  
I want informar dias, refeicoes, custo e restricoes em fluxo guiado,  
so that a solicitacao de geracao fique completa e consistente.

## Acceptance Criteria

1. Given contrato no contexto da sessao, When o usuario preenche os parametros obrigatorios, Then o sistema valida os campos e preserva estado da configuracao, And permite ajustes antes da confirmacao final.

## Tasks / Subtasks

- [ ] Consolidar máquina de estados do fluxo conversacional (AC: 1)
  - [ ] Revisar fases em `useChatGenerator.ts` (`config-days`, `config-meals`, `config-cost`, `config-restrictions`, `confirm`).
  - [ ] Garantir transições idempotentes para reentrada e ajustes.
- [ ] Validar captura/normalização dos parâmetros (AC: 1)
  - [ ] Dias: validar intervalo permitido e feedback imediato.
  - [ ] Refeições: garantir seleção mínima e labels consistentes.
  - [ ] Custo alvo/restrições: aceitar opcionalidade com fallback explícito.
- [ ] Manter estado de sessão e UX fluida no chat (AC: 1)
  - [ ] Atualizar `MessageInput` e `MessageBubble` para refletir fase ativa sem perda de contexto.
  - [ ] Garantir persistência local de estado até confirmação.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `menu/src/components/chat/useChatGenerator.ts`
- `menu/src/components/chat/MessageInput.tsx`
- `menu/src/components/chat/MessageBubble.tsx`
- `menu/src/app/(app)/gerar/page.tsx`

### Regras de implementação (guardrails)

- Não iniciar geração sem parâmetros mínimos validados.
- Não remover suporte a upload/seleção de contrato já implementado.
- Evitar regressão no fluxo HITL posterior.

### Testes mínimos esperados nesta história

- Fluxo completo de parâmetros avança até confirmação.
- Ajuste de parâmetro volta ao passo correto sem reiniciar sessão.
- Estado mantém consistência após mensagens do usuário.

### Dependências e sequência

- Depende de Epic 2 (contrato no contexto).
- Base para `3.2`.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1: Capturar parametros de geracao via chat/wizard]
- [Source: menu/src/components/chat/useChatGenerator.ts]
- [Source: menu/src/app/(app)/gerar/page.tsx]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para estruturar captura guiada de parâmetros no fluxo conversacional.

### File List

- _bmad-output/implementation-artifacts/3-1-capturar-parametros-de-geracao-via-chat-wizard.md
