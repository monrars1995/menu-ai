# Story 2.2: upload-e-deduplicacao-de-contrato

Status: ready-for-dev

## Story

As a nutricionista,  
I want enviar novo contrato no proprio fluxo com deduplicacao por hash,  
so that o sistema nao duplique arquivos e registros equivalentes.

## Acceptance Criteria

1. Given um arquivo valido de contrato, When o upload e processado, Then o sistema reaproveita contrato existente quando hash coincidir, And cria novo contrato somente quando nao houver correspondencia.

## Tasks / Subtasks

- [ ] Validar deduplicação por hash no endpoint de upload com geração (AC: 1)
  - [ ] Revisar `POST /api/gerar/upload` em `app.py` (SHA256 + busca por `arquivo_hash` e `empresa_id`).
  - [ ] Garantir regra de reuso (`novo_contrato=false`) quando hash já existe no tenant.
- [ ] Garantir persistência correta de novos contratos (AC: 1)
  - [ ] Validar criação de `Contrato` com `arquivo_path`, `arquivo_hash`, `empresa_id` e `nome`.
  - [ ] Confirmar comportamento sem DB (fallback técnico) sem quebrar fluxo principal com DB.
- [ ] Alinhar upload no frontend com UX de feedback (AC: 1)
  - [ ] Validar integração de upload no wizard/menu para refletir contrato reaproveitado vs novo.
  - [ ] Exibir estado de processamento/erro com mensagem acionável.

## Dev Notes

### Contexto funcional e técnico

- O endpoint `/api/gerar/upload` já implementa hash SHA256 e deduplicação por tenant.
- Esta história consolida contrato funcional e valida robustez de bordas (arquivo repetido, extensão inválida, ausência de empresa).

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `app.py` (`POST /api/gerar/upload`)
- `database/models.py` (campos de `Contrato` usados no fluxo)
- `menu/src/lib/api.ts`
- `menu/src/components/wizard/ContractUpload.tsx`
- `menu/src/app/(app)/gerar/page.tsx`

### Regras de implementação (guardrails)

- Deduplicação deve ser por `hash + empresa_id` (não global entre tenants).
- Reuso de contrato não pode alterar metadados históricos indevidamente.
- Erros de formato/tamanho de arquivo devem retornar status HTTP e mensagem clara.

### Testes mínimos esperados nesta história

- Upload do mesmo arquivo duas vezes na mesma empresa reaproveita contrato.
- Upload do mesmo arquivo em empresa diferente cria contrato distinto.
- Upload com extensão inválida retorna 400.
- Resposta contém `contrato_id`, `novo_contrato` e `job_id`.

### Dependências e sequência

- Pode evoluir em paralelo a `2.1`.
- Habilita `2.3` (análise/persistência de regras).

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2: Upload e deduplicacao de contrato]
- [Source: app.py]
- [Source: routers/contratos.py]
- [Source: menu/src/lib/api.ts]
- [Source: menu/src/components/wizard/ContractUpload.tsx]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada com foco em deduplicação por hash e consistência multi-tenant.

### File List

- _bmad-output/implementation-artifacts/2-2-upload-e-deduplicacao-de-contrato.md
