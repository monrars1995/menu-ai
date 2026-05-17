# Story 4.4: expor-metricas-de-consistencia-da-base

Status: ready-for-dev

## Story

As a gestor,  
I want ver indicadores de saude da base tecnica,  
so that eu identifique lacunas antes da geracao.

## Acceptance Criteria

1. Given base de fichas e ingredientes cadastrada, When consulta indicadores de consistencia, Then sistema informa volumes e situacoes relevantes, And dados suportam decisao de melhoria de base.

## Tasks / Subtasks

- [ ] Consolidar fonte única de métricas de base (AC: 1)
  - [ ] Revisar `services/fichas_db_stats.py` como origem de contagens.
  - [ ] Garantir cache por empresa com TTL configurável e invalidação adequada.
- [ ] Expor métricas no endpoint canônico (AC: 1)
  - [ ] Validar `/api/info` em `app.py` para retornar contagens e categorias coerentes por escopo.
  - [ ] Preservar estados claros: carregado, indisponível, sem contexto autenticado.
- [ ] Integrar métricas em header/dashboard (AC: 1)
  - [ ] Validar consumo em UI principal e visão administrativa sem discrepância de escopo.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `services/fichas_db_stats.py`
- `app.py` (`GET /api/info`)
- `templates/index.html` (header/idle)
- `admin/routers/meta.py`

### Regras de implementação (guardrails)

- Não usar contagem global por padrão para usuário comum autenticado.
- Não manter dupla fonte de contagem para os mesmos indicadores.
- Mensagens de erro devem indicar indisponibilidade de base sem confundir com ausência de dados.

### Testes mínimos esperados nesta história

- `/api/info` retorna contagens coerentes para empresa autenticada.
- Cache TTL funciona e respeita escopo por empresa.
- Header/idle exibem os mesmos totais.

### Dependências e sequência

- Depende de `1.2` e `4.1`/`4.2`.
- Fecha o Epic 4.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.4: Expor metricas de consistencia da base]
- [Source: services/fichas_db_stats.py]
- [Source: app.py]
- [Source: admin/routers/meta.py]
- [Source: templates/index.html]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para consolidar indicadores de base e consistência entre API/UI.

### File List

- _bmad-output/implementation-artifacts/4-4-expor-metricas-de-consistencia-da-base.md
