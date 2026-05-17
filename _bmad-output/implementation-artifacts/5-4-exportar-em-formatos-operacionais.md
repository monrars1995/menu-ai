# Story 5.4: exportar-em-formatos-operacionais

Status: ready-for-dev

## Story

As a gestor,  
I want exportar cardapios em formatos padrao,  
so that operacao, compras e BI consumam os dados.

## Acceptance Criteria

1. Given cardapio aprovado ou elegivel para distribuicao, When usuario solicita exportacao, Then arquivo e gerado em formato suportado, And estrutura do arquivo permanece consistente entre execucoes.

## Tasks / Subtasks

- [ ] Consolidar exportação multi-formato (AC: 1)
  - [ ] Revisar endpoint `GET /api/cardapios/{id}/exportar` para `xlsx`, `csv`, `txt`, `pdf`.
  - [ ] Garantir `Content-Disposition` e tipo MIME corretos por formato.
- [ ] Garantir consistência estrutural dos arquivos (AC: 1)
  - [ ] Validar geração de dataset base (`_cardapio_export_dataframe`).
  - [ ] Confirmar layout estável de colunas/abas no XLSX.
- [ ] Integrar download no frontend (AC: 1)
  - [ ] Validar `api.cardapios.exportar/download` em `menu/src/lib/api.ts`.
  - [ ] Garantir feedback de erro quando cardápio não possui conteúdo exportável.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `routers/cardapios.py`
- `menu/src/lib/api.ts`
- `menu/src/lib/types.ts`

### Regras de implementação (guardrails)

- Não gerar export com conteúdo vazio sem erro explícito.
- Preservar consistência de colunas para consumo ERP/BI.
- Evitar divergência entre conteúdo de detalhe e conteúdo exportado.

### Testes mínimos esperados nesta história

- Exportação XLSX/CSV/TXT/PDF funciona para cardápio válido.
- Cardápio sem conteúdo retorna erro coerente.
- Arquivos mantêm estrutura estável entre execuções.

### Dependências e sequência

- Depende de `5.3`.
- Fecha o Epic 5.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.4: Exportar em formatos operacionais]
- [Source: routers/cardapios.py]
- [Source: menu/src/lib/api.ts]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para padronizar distribuição operacional dos cardápios.

### File List

- _bmad-output/implementation-artifacts/5-4-exportar-em-formatos-operacionais.md
