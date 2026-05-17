# Story 3.3: exibir-progresso-de-pipeline-em-tempo-real

Status: ready-for-dev

## Story

As a nutricionista,  
I want acompanhar etapas e progresso da geracao,  
so that eu entenda o andamento sem recarregar a pagina.

## Acceptance Criteria

1. Given job em execucao, When o frontend abre o stream de progresso, Then eventos de etapa/progresso sao exibidos de forma incremental, And falhas interrompem o fluxo com mensagem acionavel.

## Tasks / Subtasks

- [ ] Consolidar emissão de eventos de progresso no worker (AC: 1)
  - [ ] Revisar `emit(...)` e `progress(...)` em `services/geracao.py`.
  - [ ] Garantir eventos relevantes: `log`, `task_complete`, `agent_thought`, `aguardando_confirmacao`, `done`, `error`.
- [ ] Garantir contrato estável de streaming/status (AC: 1)
  - [ ] Validar `/api/stream/{job_id}` (SSE) e `/api/status/{job_id}` em `app.py`.
  - [ ] Cobrir cenário de reidratação de job após restart.
- [ ] Atualizar UI para consumo robusto dos eventos (AC: 1)
  - [ ] Revisar parsing de eventos no `useChatGenerator.ts`.
  - [ ] Garantir render incremental no chat sem duplicações e com fallback para desconexão.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `services/geracao.py`
- `services/job_state.py`
- `app.py`
- `menu/src/components/chat/useChatGenerator.ts`
- `menu/src/components/chat/MessageBubble.tsx`

### Regras de implementação (guardrails)

- Não bloquear thread principal com polling agressivo quando SSE está ativo.
- Mensagens de erro devem orientar ação de retry/ajuste.
- Preservar compatibilidade com eventos HITL.

### Testes mínimos esperados nesta história

- SSE recebe eventos progressivos até `done` para job bem-sucedido.
- Falha no pipeline gera evento `error` e UI muda para estado de erro.
- Reconexão após refresh consulta `/api/status/{job_id}` e restaura contexto.

### Dependências e sequência

- Depende de `3.2`.
- Base para `3.4`.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3: Exibir progresso de pipeline em tempo real]
- [Source: services/geracao.py]
- [Source: app.py]
- [Source: menu/src/components/chat/useChatGenerator.ts]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para consolidar streaming incremental e feedback operacional em tempo real.

### File List

- _bmad-output/implementation-artifacts/3-3-exibir-progresso-de-pipeline-em-tempo-real.md
