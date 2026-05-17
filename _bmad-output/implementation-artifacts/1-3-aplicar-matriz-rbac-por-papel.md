# Story 1.3: aplicar-matriz-rbac-por-papel

Status: ready-for-dev

## Story

As a admin de empresa,  
I want permissões coerentes por papel em cada operacao,  
so that cada perfil execute apenas o permitido.

## Acceptance Criteria

1. Given usuarios com papeis distintos, When tentam executar operacoes de leitura/escrita/aprovacao, Then o sistema permite ou bloqueia de acordo com a matriz RBAC, And o comportamento e consistente em menu, admin e API.

## Tasks / Subtasks

- [ ] Definir matriz RBAC canônica por operação (AC: 1)
  - [ ] Mapear papéis suportados (`super_admin`, `admin`, `nutricionista`, `gestor`, `visualizador`) para cada grupo de endpoint.
  - [ ] Registrar matriz em documentação técnica do módulo para reduzir ambiguidade entre routers.
- [ ] Alinhar enforcement RBAC no backend (AC: 1)
  - [ ] Revisar uso de `exigir_role(...)` nos routers de domínio para manter coerência entre operações de leitura, edição e aprovação.
  - [ ] Verificar endpoints de aprovação e status em `routers/cardapios.py` para manter permissões de `gestor/admin/super_admin`.
  - [ ] Garantir que endpoints administrativos mantenham restrição a `admin`/`super_admin`.
- [ ] Alinhar comportamento do admin app com o RBAC efetivo (AC: 1)
  - [ ] Confirmar `admin/deps.py` como porta única de autorização no app admin.
  - [ ] Validar que telas do admin tratam 403 com feedback claro e sem loops de sessão.
- [ ] Cobrir regressões com testes de autorização (AC: 1)
  - [ ] Criar/ajustar testes para perfis distintos executando as mesmas rotas.
  - [ ] Garantir evidência de bloqueio para papéis sem permissão e sucesso para papéis autorizados.

## Dev Notes

### Contexto funcional e técnico

- A base já utiliza `exigir_role` e checks de escopo por tenant em múltiplos routers.
- O risco principal é inconsistência entre endpoints equivalentes (ex.: leitura liberada em um router e bloqueada em outro para o mesmo papel).

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `routers/auth_supabase.py`
  - `exigir_role(...)` compartilhado por routers de domínio
- `routers/cardapios.py`
  - Operações de aprovação/publicação e regras por papel
- `routers/fichas_tecnicas.py`, `routers/ingredientes.py`, `routers/contratos.py`
  - CRUD e regras de escrita por papel
- `admin/deps.py`
  - Autorização admin por JWT e `X-Admin-Api-Key`
- `admin/routers/meta.py`, `admin/routers/llm_admin.py`, `admin/routers/knowledge_admin.py`
  - Rotas administrativas com dependências de autorização
- `menu/src/components/auth/auth-guard.tsx` e `admin/src/lib/auth.tsx`
  - Gating de sessão e tratamento básico de acesso no frontend

### Regras de implementação (guardrails)

- Não usar lógica de role hardcoded dispersa quando `exigir_role` já cobre o cenário.
- Garantir que `super_admin` preserve capacidade de override administrativo sem abrir acesso indevido a papéis comuns.
- Evitar mudanças de contrato de resposta apenas para tratar 403.
- Não misturar RBAC com escopo de tenant; ambos devem ser validados.

### Testes mínimos esperados nesta história

- Usuário `visualizador` não executa rotas de escrita.
- Usuário `nutricionista` consegue CRUD técnico permitido, mas não ações administrativas globais.
- Usuário `gestor` consegue ações de aprovação previstas e não acessa configuração de modelo admin.
- Usuário `admin` e `super_admin` mantêm acesso administrativo conforme escopo.

### Dependências e sequência

- Depende da Story `1.2` (auth e tenant scope confiáveis).
- Prepara base para stories de ciclo de vida (`Epic 5`) e governança (`Epic 6`).

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3: Aplicar matriz RBAC por papel]
- [Source: _bmad-output/planning-artifacts/architecture.md#Security Architecture]
- [Source: routers/auth_supabase.py]
- [Source: routers/cardapios.py]
- [Source: routers/fichas_tecnicas.py]
- [Source: routers/ingredientes.py]
- [Source: routers/contratos.py]
- [Source: admin/deps.py]
- [Source: admin/routers/meta.py]
- [Source: admin/routers/llm_admin.py]
- [Source: admin/routers/knowledge_admin.py]
- [Source: menu/src/components/auth/auth-guard.tsx]
- [Source: admin/src/lib/auth.tsx]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada com foco em coerência RBAC transversal entre API, app menu e app admin.
- Critérios orientados a teste por papel para reduzir regressões.

### File List

- _bmad-output/implementation-artifacts/1-3-aplicar-matriz-rbac-por-papel.md
