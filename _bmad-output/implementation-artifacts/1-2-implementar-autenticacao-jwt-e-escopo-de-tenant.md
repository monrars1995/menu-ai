# Story 1.2: implementar-autenticacao-jwt-e-escopo-de-tenant

Status: ready-for-dev

## Story

As a usuario autenticado,  
I want acessar apenas dados da minha empresa apos login valido,  
so that informacoes de outros tenants permaneçam isoladas.

## Acceptance Criteria

1. Given um token JWT valido, When o usuario acessa endpoints protegidos, Then o sistema valida autenticacao e aplica filtro por empresa, And acessos fora do escopo retornam erro de autorizacao.

## Tasks / Subtasks

- [ ] Consolidar validação JWT no fluxo oficial Supabase (AC: 1)
  - [ ] Revisar `routers/auth_supabase.py` para garantir ordem de validação estável (JWKS ES256 -> validação remota -> fallback legado quando habilitado).
  - [ ] Garantir payload mínimo consistente (`sub`, `role`, `empresa_id`) para uso em filtros de escopo.
  - [ ] Cobrir erros 401 com mensagens acionáveis e sem ambiguidade de causa.
- [ ] Padronizar escopo de tenant no backend principal (AC: 1)
  - [ ] Validar `_resolve_info_scope()` e `_empresa_id_efetivo_gerar()` em `app.py` para bloquear mismatch entre token e `empresa_id` de entrada.
  - [ ] Confirmar uso de `usuario.empresa_id` como escopo padrão quando não há `empresa_id` explícito no request.
  - [ ] Preservar exceção de `super_admin` apenas quando explicitamente permitida pelo endpoint.
- [ ] Verificar isolamento em endpoints de domínio já publicados (AC: 1)
  - [ ] Revisar routers com leitura/escrita por tenant (`routers/fichas_tecnicas.py`, `routers/ingredientes.py`, `routers/contratos.py`, `routers/cardapios.py`, `routers/chat.py`).
  - [ ] Garantir retorno 403 para acesso cruzado entre empresas e 401 para token inválido/ausente.
- [ ] Alinhar clientes web com sessão autenticada e escopo efetivo (AC: 1)
  - [ ] Confirmar envio de bearer token no menu (`menu/src/lib/auth.tsx`) e no admin (`admin/src/lib/auth.tsx`).
  - [ ] Validar middleware do admin (`admin/src/middleware.ts`) para impedir navegação sem sessão válida.

## Dev Notes

### Contexto funcional e técnico

- O projeto já possui base de autenticação JWT e escopo multi-tenant; esta história formaliza consistência entre endpoints, evitando brechas de acesso cruzado.
- O endpoint `/api/info` já foi evoluído para escopo por tenant com exceção controlada para `super_admin`.

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `routers/auth_supabase.py`
  - Dependência principal `get_usuario_atual` no fluxo atual
  - Fallback de validação de token (JWKS/remote/legacy)
- `app.py`
  - `get_usuario_geracao`, `alinhar_empresa`, `_empresa_id_efetivo_gerar`, `_resolve_info_scope`
  - Rotas sensíveis: `/api/info`, `/api/gerar`, `/api/gerar/upload`
- `routers/fichas_tecnicas.py`, `routers/ingredientes.py`, `routers/contratos.py`, `routers/cardapios.py`, `routers/chat.py`
  - Regras de escopo de empresa e exceções de `super_admin`
- `menu/src/lib/auth.tsx`
  - Persistência/renovação de token da sessão
- `admin/src/lib/auth.tsx`, `admin/src/middleware.ts`
  - Sessão administrativa por JWT e/ou `X-Admin-Api-Key`

### Regras de implementação (guardrails)

- Não permitir fallback implícito para dados globais quando existir token de usuário comum.
- Não misturar erro de autenticação (401) com erro de autorização de escopo/role (403).
- Não quebrar compatibilidade do fluxo de demo (`DEBUG + DEMO_GERAR_SEM_AUTH`) já documentado.
- Evitar duplicação de lógica de escopo; preferir funções centrais já existentes em `app.py`.

### Testes mínimos esperados nesta história

- `/api/info` com token de usuário comum retorna somente escopo da empresa do token.
- `/api/info?empresa_id=<outra_empresa>` para usuário comum retorna 403.
- `/api/gerar` sem `empresa_id` no body usa `empresa_id` do JWT.
- `/api/gerar` com `empresa_id` divergente para usuário comum retorna 403.
- Rotas de CRUD multi-tenant bloqueiam leitura/escrita cruzada entre empresas.

### Dependências e sequência

- Depende da Story `1.1` (stack estável e migrações aplicadas).
- Habilita diretamente a Story `1.3` (RBAC completo) e reforça `1.4` (auditoria/saúde).

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1: Fundacao de Plataforma e Seguranca Multi-tenant]
- [Source: _bmad-output/planning-artifacts/architecture.md#Security Architecture]
- [Source: app.py]
- [Source: routers/auth_supabase.py]
- [Source: routers/fichas_tecnicas.py]
- [Source: routers/ingredientes.py]
- [Source: routers/contratos.py]
- [Source: routers/cardapios.py]
- [Source: routers/chat.py]
- [Source: menu/src/lib/auth.tsx]
- [Source: admin/src/lib/auth.tsx]
- [Source: admin/src/middleware.ts]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada com escopo explícito de autenticação e isolamento de tenant.
- Critérios de validação distinguem 401 x 403 para evitar regressões.

### File List

- _bmad-output/implementation-artifacts/1-2-implementar-autenticacao-jwt-e-escopo-de-tenant.md
