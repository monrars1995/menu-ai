# Story 2.4: fallback-para-analise-parcial

Status: ready-for-dev

## Story

As a nutricionista,  
I want continuar o fluxo mesmo com analise parcial,  
so that eu nao fique bloqueada por falhas nao criticas.

## Acceptance Criteria

1. Given falha parcial na analise contratual, When o fluxo avanca, Then o sistema exibe aviso explicito de limitacao, And permite geracao com comportamento de fallback controlado.

## Tasks / Subtasks

- [ ] Garantir fallback controlado na etapa de análise (AC: 1)
  - [ ] Revisar tratamento de exceção da análise em `services/geracao.py`.
  - [ ] Confirmar que falha parcial não derruba o job quando ainda há contexto mínimo para continuar.
- [ ] Padronizar mensagem de limitação para usuário (AC: 1)
  - [ ] Definir payload de aviso no estado do job e no stream (`/api/stream/{job_id}`).
  - [ ] Exibir aviso claro no frontend antes da confirmação/continuação.
- [ ] Preservar rastreabilidade de fallback (AC: 1)
  - [ ] Registrar ocorrência de fallback (erro/limitação) no estado do job e, quando aplicável, em auditoria técnica.
  - [ ] Garantir distinção entre falha total (erro terminal) e falha parcial (continua com aviso).

## Dev Notes

### Contexto funcional e técnico

- O worker já captura exceção na análise de contrato e marca resumo com erro.
- O fluxo HITL em `/api/gerar/{job_id}/confirmar` já permite controle explícito de continuidade.

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `services/geracao.py`
- `app.py` (`/api/stream/{job_id}`, `/api/status/{job_id}`, `/api/gerar/{job_id}/confirmar`)
- `services/job_state.py`
- `menu/src/app/(app)/gerar/page.tsx`

### Regras de implementação (guardrails)

- Falha parcial deve gerar aviso explícito, nunca silêncio.
- Não transformar fallback em sucesso pleno sem sinalização.
- Erros fatais devem continuar encerrando o job com estado terminal adequado.

### Testes mínimos esperados nesta história

- Simular erro no analista de contratos e confirmar continuidade com aviso.
- Validar evento/mensagem de fallback no stream e no status do job.
- Validar que falha total ainda interrompe com erro terminal.

### Dependências e sequência

- Depende de `2.3`.
- Fecha o Epic 2 e prepara Epic 3 (execução conversacional principal).

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4: Fallback para analise parcial]
- [Source: services/geracao.py]
- [Source: app.py]
- [Source: services/job_state.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para robustez operacional do fluxo contratual com fallback explícito.

### File List

- _bmad-output/implementation-artifacts/2-4-fallback-para-analise-parcial.md
