# Story 2.3: interpretacao-e-persistencia-de-regras-contratuais

Status: ready-for-dev

## Story

As a nutricionista,  
I want visualizar o resumo de regras extraidas do contrato,  
so that eu confirme o entendimento antes de gerar o cardapio.

## Acceptance Criteria

1. Given um contrato selecionado ou enviado, When a analise e executada, Then regras principais ficam persistidas e consultaveis, And o resumo apresentado inclui refeicoes, limites e restricoes.

## Tasks / Subtasks

- [ ] Garantir extração de regras na etapa de análise de contrato (AC: 1)
  - [ ] Validar `analisar_contrato_apenas()` no orquestrador e execução no worker de geração.
  - [ ] Confirmar persistência de resumo no estado do job para HITL (`aguardando_confirmacao`).
- [ ] Persistir regras extraídas no contrato (AC: 1)
  - [ ] Revisar trecho de persistência em `services/geracao.py` (`regras_json`, `gramaturas_json`, `incidencias_json`, `proibicoes_json`).
  - [ ] Garantir idempotência para reprocessamentos do mesmo contrato.
- [ ] Expor consulta de análise em endpoint canônico (AC: 1)
  - [ ] Validar `/api/contratos/{contrato_id}/analise` com fallback controlado e escopo por tenant.
  - [ ] Padronizar status de resposta (`analisado`/`nao_analisado`) com payload útil para UI.

## Dev Notes

### Contexto funcional e técnico

- A análise de contrato é executada no início da geração e já pode pausar para confirmação humana.
- O sistema já possui endpoint de leitura da análise e múltiplos níveis de fallback de origem dos dados.

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `services/geracao.py`
- `pipeline/orchestrator.py`
- `pipeline/sequential_spec.py`
- `routers/contratos.py` (`/{contrato_id}/analise`)
- `menu/src/app/(app)/gerar/page.tsx` (etapa de confirmação do resumo)

### Regras de implementação (guardrails)

- Não substituir regras válidas por payload parcial/inválido sem checagem.
- Não vazar análise de contrato entre empresas.
- Manter compatibilidade de fallback somente como contingência, priorizando dado persistido no DB.

### Testes mínimos esperados nesta história

- Geração com contrato válido cria/persiste `regras_json` no contrato.
- Endpoint de análise retorna resumo consistente após etapa analista.
- Usuário sem escopo no contrato recebe 403.
- Reprocessar contrato não quebra estrutura já persistida.

### Dependências e sequência

- Depende de `2.1` e/ou `2.2` para entrada de contrato.
- Base para `2.4` (fallback com análise parcial) e Epic 3 (execução da geração).

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3: Interpretacao e persistencia de regras contratuais]
- [Source: services/geracao.py]
- [Source: pipeline/orchestrator.py]
- [Source: pipeline/sequential_spec.py]
- [Source: routers/contratos.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para consolidar extração, persistência e consulta das regras contratuais.

### File List

- _bmad-output/implementation-artifacts/2-3-interpretacao-e-persistencia-de-regras-contratuais.md
