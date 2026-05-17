# Story 3.4: explicar-resultado-e-permitir-regeneracao

Status: ready-for-dev

## Story

As a nutricionista,  
I want receber justificativa de custo e opcao de ajustar restricoes,  
so that eu consiga otimizar o resultado quando PU nao for atingido.

## Acceptance Criteria

1. Given resultado concluido ou fallback de inviabilidade, When o sistema apresenta o output, Then justificativas de decisao ficam visiveis, And o usuario pode ajustar entradas e solicitar nova geracao.

## Tasks / Subtasks

- [ ] Expor explicabilidade no resultado final (AC: 1)
  - [ ] Revisar payload final de geração para incluir justificativas relevantes.
  - [ ] Garantir render de blocos de explicação no chat (`MessageBubble`/resultado).
- [ ] Implementar regeneração orientada por ajuste (AC: 1)
  - [ ] Revisar `handleAdjust` e fluxo de nova geração em `useChatGenerator.ts`.
  - [ ] Reutilizar contexto anterior (contrato/parâmetros) com alterações incrementais.
- [ ] Tratar inviabilidade de meta de custo com alternativa acionável (AC: 1)
  - [ ] Garantir mensagem objetiva de melhor cenário quando alvo não for alcançável.
  - [ ] Permitir retorno direto para ajuste de custo/restrições.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `menu/src/components/chat/useChatGenerator.ts`
- `menu/src/components/chat/MessageBubble.tsx`
- `services/geracao.py`
- `pipeline/sequential_spec.py`
- `pipeline/litellm_runner.py`

### Regras de implementação (guardrails)

- Não mascarar resultado inviável como sucesso sem ressalva.
- Regeneração deve criar novo job com rastreabilidade própria.
- Evitar perda do contexto de sessão durante ajustes iterativos.

### Testes mínimos esperados nesta história

- Resultado final exibe justificativas de custo/decisão.
- Ajustar restrição dispara nova geração com novo `job_id`.
- Cenário inviável exibe mensagem clara com orientação de ajuste.

### Dependências e sequência

- Depende de `3.3`.
- Fecha o Epic 3.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4: Explicar resultado e permitir regeneracao]
- [Source: menu/src/components/chat/useChatGenerator.ts]
- [Source: menu/src/components/chat/MessageBubble.tsx]
- [Source: services/geracao.py]
- [Source: pipeline/sequential_spec.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para explicabilidade de resultado e iteração de nova geração.

### File List

- _bmad-output/implementation-artifacts/3-4-explicar-resultado-e-permitir-regeneracao.md
