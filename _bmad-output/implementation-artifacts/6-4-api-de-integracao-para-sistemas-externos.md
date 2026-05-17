# Story 6.4: api-de-integracao-para-sistemas-externos

Status: ready-for-dev

## Story

As a integrador ERP,  
I want disparar geracao e consultar resultados por API,  
so that processos corporativos executem automacoes ponta a ponta.

## Acceptance Criteria

1. Given credenciais validas e payload conforme contrato, When sistema externo aciona endpoints de geracao/status, Then API responde com status e identificadores consistentes, And contratos de integracao mantem compatibilidade versionada.

## Tasks / Subtasks

- [ ] Consolidar contrato dos endpoints de integração (AC: 1)
  - [ ] Revisar `/api/gerar`, `/api/gerar/upload`, `/api/status/{job_id}`, `/api/stream/{job_id}`.
  - [ ] Garantir payload/resposta estáveis para automações externas.
- [ ] Validar autenticação e escopo em chamadas de integração (AC: 1)
  - [ ] Confirmar uso de bearer token e escopo de empresa em todos os endpoints protegidos.
  - [ ] Garantir erro coerente para credenciais inválidas e escopo divergente.
- [ ] Documentar compatibilidade e versionamento de contrato (AC: 1)
  - [ ] Atualizar documentação técnica dos endpoints com exemplos de request/response.
  - [ ] Definir política de evolução sem quebra para integradores.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `app.py`
- `services/geracao.py`
- `routers/auth_supabase.py`
- `INICIAR.md` e documentação de API

### Regras de implementação (guardrails)

- Não introduzir breaking change silenciosa nos endpoints já consumidos.
- Sempre retornar `job_id`/estado com formato consistente.
- Não permitir bypass de escopo tenant para cliente externo comum.

### Testes mínimos esperados nesta história

- Integração externa cria job e acompanha status por API.
- Fluxo com contrato existente e com upload funciona por endpoint.
- Erros de autenticação/escopo retornam HTTP apropriado com detalhe acionável.

### Dependências e sequência

- Depende dos Epics 1, 2 e 3.
- Fecha o Epic 6.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.4: API de integracao para sistemas externos]
- [Source: app.py]
- [Source: services/geracao.py]
- [Source: routers/auth_supabase.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para formalizar contrato de integração externa ponta a ponta.

### File List

- _bmad-output/implementation-artifacts/6-4-api-de-integracao-para-sistemas-externos.md
