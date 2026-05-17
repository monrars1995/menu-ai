# Story 6.1: dashboard-e-endpoints-canonicos-de-informacao

Status: ready-for-dev

## Story

As a admin de empresa,  
I want acompanhar indicadores chave e contagens consistentes,  
so that a equipe tenha visao operacional unificada.

## Acceptance Criteria

1. Given dados da empresa no banco, When dashboard/header consulta informacoes, Then endpoints retornam contagens consistentes por tenant, And estados de carregamento/erro sao tratados de forma coerente.

## Tasks / Subtasks

- [ ] Consolidar endpoints canônicos de informação (AC: 1)
  - [ ] Validar `/api/info` e `/api/health` em `app.py`.
  - [ ] Garantir escopo por tenant e retorno estável em cenários de erro/contexto ausente.
- [ ] Alinhar visão admin com os mesmos números de base (AC: 1)
  - [ ] Revisar `/api/admin/meta/dashboard` para consistência de contagens.
  - [ ] Validar separação de escopo global vs empresa.
- [ ] Harmonizar consumo no frontend (AC: 1)
  - [ ] Confirmar estados de carregamento/erro no header e dashboard.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `app.py`
- `admin/routers/meta.py`
- `services/fichas_db_stats.py`
- `templates/index.html`
- frontends `menu` e `admin`

### Regras de implementação (guardrails)

- Não divergência de fonte de dados entre header e dashboard.
- Não expor contagem global para usuário comum sem permissão.

### Testes mínimos esperados nesta história

- `/api/info` e dashboard admin coerentes com o mesmo tenant.
- Estados de erro/carregamento consistentes no frontend.

### Dependências e sequência

- Depende de `4.4`.
- Base para observabilidade e governança do Epic 6.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.1: Dashboard e endpoints canonicos de informacao]
- [Source: app.py]
- [Source: admin/routers/meta.py]
- [Source: services/fichas_db_stats.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para unificar indicadores operacionais em endpoints canônicos.

### File List

- _bmad-output/implementation-artifacts/6-1-dashboard-e-endpoints-canonicos-de-informacao.md
