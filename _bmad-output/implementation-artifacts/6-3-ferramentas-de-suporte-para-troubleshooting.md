# Story 6.3: ferramentas-de-suporte-para-troubleshooting

Status: ready-for-dev

## Story

As a suporte tecnico,  
I want consultar estado de jobs e sessoes com contexto,  
so that eu resolva incidentes com rapidez.

## Acceptance Criteria

1. Given eventos e estado persistidos, When suporte consulta job/sessao, Then sistema retorna trilha suficiente para diagnostico, And mensagens de erro permitem acao corretiva objetiva.

## Tasks / Subtasks

- [ ] Consolidar trilha de troubleshooting de jobs (AC: 1)
  - [ ] Validar `/api/status/{job_id}` e reidratação de estado em `services/geracao.py`.
  - [ ] Garantir logs úteis em memória/DB com progresso e erro.
- [ ] Consolidar troubleshooting de sessões de chat (AC: 1)
  - [ ] Revisar `routers/chat.py` para consulta de sessão e histórico.
  - [ ] Garantir escopo de acesso por usuário/role.
- [ ] Fortalecer mensagens de erro acionáveis (AC: 1)
  - [ ] Revisar pontos críticos de erro em geração, análise e admin para clareza de diagnóstico.

## Dev Notes

### Arquivos e pontos de atenção (UPDATE, não recriar)

- `services/geracao.py`
- `services/job_state.py`
- `routers/chat.py`
- `services/chat_llm.py`
- `app.py`

### Regras de implementação (guardrails)

- Não expor dados sensíveis em logs retornados por API.
- Não misturar erro de autenticação com erro operacional interno.
- Reidratação de job não deve corromper estado já existente.

### Testes mínimos esperados nesta história

- Job pode ser consultado após restart com estado reidratado.
- Sessão de chat retorna histórico completo para usuário autorizado.
- Mensagens de erro incluem ação corretiva básica.

### Dependências e sequência

- Depende de Epics 3 e 5.
- Base para operação contínua de suporte.

### Referências

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.3: Ferramentas de suporte para troubleshooting]
- [Source: services/geracao.py]
- [Source: routers/chat.py]
- [Source: services/chat_llm.py]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- N/A

### Completion Notes List

- Story criada para diagnóstico rápido de incidentes em jobs e sessões.

### File List

- _bmad-output/implementation-artifacts/6-3-ferramentas-de-suporte-para-troubleshooting.md
