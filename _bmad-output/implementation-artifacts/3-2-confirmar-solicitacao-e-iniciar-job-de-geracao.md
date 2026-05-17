# Story 3.2: confirmar-solicitacao-e-iniciar-job-de-geracao

Status: ready-for-dev

## Story

As a nutricionista,  
I want confirmar os parametros e disparar a geracao,  
so that o pipeline execute com rastreabilidade.

## Acceptance Criteria

1. Given parametros validados, When o usuario confirma a geracao, Then um job e criado com identificador unico, And estado inicial fica disponivel para consulta e streaming.

## Tasks / Subtasks

- [ ] Implementar confirmação explícita e montagem final do payload (AC: 1)
  - [ ] Garantir etapa `confirm` no frontend com resumo final.
  - [ ] Confirmar envio de `contrato_id`, `dias`, `refeicoes`, `target_custo_total`, `restricoes_usuario`, `llm_model`.
- [ ] Garantir criação consistente do job no backend (AC: 1)
  - [ ] Revisar `/api/gerar` e `/api/gerar/upload` em `app.py`.
  - [ ] Garantir persistência inicial em `JobAgente` quando DB estiver disponível.
- [ ] Expor rastreabilidade mínima do job (AC: 1)
  - [ ] Validar retorno imediato com `job_id`.
  - [ ] Confirmar disponibilidade de `/api/status/{job_id}` e `/api/stream/{job_id}` após criação.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `menu/src/components/chat/useChatGenerator.ts`
- `menu/src/lib/api.ts`
- `app.py`
- `services/geracao.py`
- `database/models.py` (`JobAgente`)

### Regras de implementação (guardrails)

- Não iniciar execução sem `empresa_id` efetivo resolvido.
- Não gerar múltiplos jobs por clique duplo sem proteção.
- Preservar compatibilidade com fluxo HITL de confirmação contratual.

### Testes mínimos esperados nesta história

- Confirmar geração cria job e retorna `job_id`.
- Job aparece em `/api/status/{job_id}` com estado inicial.
- Stream SSE inicia sem erro para job recém-criado.

### Dependências e sequência

- Depende de `3.1`.
- Base para `3.3`.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2: Confirmar solicitacao e iniciar job de geracao]
- [Source: menu/src/components/chat/useChatGenerator.ts]
- [Source: app.py]
- [Source: services/geracao.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para garantir confirmação final e criação rastreável de job.

### File List

- _bmad-output/implementation-artifacts/3-2-confirmar-solicitacao-e-iniciar-job-de-geracao.md
