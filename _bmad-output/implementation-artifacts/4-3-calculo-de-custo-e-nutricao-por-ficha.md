# Story 4.3: calculo-de-custo-e-nutricao-por-ficha

Status: ready-for-dev

## Story

As a nutricionista,  
I want recalcular custo e indicadores nutricionais das fichas,  
so that a base tecnica fique consistente para planejamento.

## Acceptance Criteria

1. Given ficha com ingredientes vinculados, When aciona recalculo, Then custo total e por porcao sao atualizados, And indicadores nutricionais disponiveis sao recalculados.

## Tasks / Subtasks

- [ ] Consolidar engine de cálculo da ficha (AC: 1)
  - [ ] Revisar `_calcular_ficha(...)` em `routers/fichas_tecnicas.py`.
  - [ ] Garantir consistência entre custo total, custo por porção e campos nutricionais por porção.
- [ ] Garantir recálculo explícito e em lote (AC: 1)
  - [ ] Validar endpoints `/{ficha_id}/recalcular` e `/recalcular-todas`.
  - [ ] Confirmar fluxo de recálculo em cascata após alteração de ingrediente.
- [ ] Padronizar evidência de resultado do recálculo (AC: 1)
  - [ ] Garantir retorno com métricas atualizadas e mensagens operacionais claras.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `routers/fichas_tecnicas.py`
- `routers/ingredientes.py`
- `services/cascata.py`
- `database/models.py`

### Regras de implementação (guardrails)

- Não usar dados nutricionais nulos como zero silencioso sem regra definida.
- Evitar divergência entre cálculo unitário e cálculo em lote.
- Não bloquear API por recálculo em cascata de alto volume sem feedback.

### Testes mínimos esperados nesta história

- Recalcular ficha individual atualiza custo e nutrição.
- Recalcular todas retorna quantidade de fichas processadas.
- Atualizar custo de ingrediente impacta fichas relacionadas.

### Dependências e sequência

- Depende de `4.1` e `4.2`.
- Base para decisões de `4.4` e geração dos Epics seguintes.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3: Calculo de custo e nutricao por ficha]
- [Source: routers/fichas_tecnicas.py]
- [Source: routers/ingredientes.py]
- [Source: services/cascata.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para consolidar cálculo técnico de custo e nutrição das fichas.

### File List

- _bmad-output/implementation-artifacts/4-3-calculo-de-custo-e-nutricao-por-ficha.md
