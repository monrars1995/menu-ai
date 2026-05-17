---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief.md
  - _bmad-output/design-thinking-2026-05-16.md
  - docs/index.md
  - docs/superpowers/specs/2026-05-03-chat-upload-inline-design.md
  - docs/superpowers/specs/2026-05-03-gerar-cardapio-chat-design.md
  - docs/superpowers/specs/2026-05-05-chat-conversacional-premium.md
  - docs/v2-fichas-ia-design.md
documentCounts:
  productBrief: 1
  research: 0
  brainstorming: 1
  projectDocs: 5
workflowType: 'prd'
classification:
  projectType: saas_b2b
  domain: general
  complexity: medium
  projectContext: brownfield
visionInsights:
  vision: "Ser o copiloto operacional de IA para planejamento de cardápios em alimentação coletiva, conectando contrato, custo e nutrição em um fluxo conversacional de ponta a ponta."
  differentiator: "Interpretação automática de contrato + base real de fichas técnicas + otimização de custo com justificativa explícita da IA."
  coreInsight: "O usuário não quer só gerar cardápio; quer negociar restrições e custo com transparência e rastreabilidade durante a geração."
releaseMode: single-release
polishNotes:
  - "FRs padronizados em Portugues BR"
  - "Ideias de experiencia do brainstorming reconciliadas no PRD"
workflowCompletedAt: "2026-05-16T22:10:00-03:00"
---

# Product Requirements Document - MENU I.A

**Author:** Monrars
**Date:** 2026-05-16

## Executive Summary

O MENU I.A e uma plataforma SaaS B2B multi-tenant para planejamento de cardapios em alimentacao coletiva, orientada a custo, contrato e conformidade nutricional. O produto reduz um processo manual e sujeito a erro (planilhas e validacoes dispersas) para um fluxo unico: contrato -> configuracao -> geracao assistida por IA -> validacao de custo/nutricao -> salvamento e exportacao. O foco do MVP e fechar o fluxo operacional de ponta a ponta em minutos, com rastreabilidade das decisoes da IA.

### What Makes This Special

O diferencial central e combinar tres ativos no mesmo loop de decisao: interpretacao automatica de contratos reais, uso de fichas tecnicas reais da empresa e otimizacao de custo com explicacao em linguagem natural. Em vez de entregar apenas um resultado, o sistema permite iteracao guiada por restricoes e evidencia de viabilidade economica (PU alvo versus custo real), incluindo cenarios de fallback quando o alvo e inatingivel. Essa transparencia transforma a IA em copiloto operacional confiavel, nao em caixa-preta.

## Project Classification

- **Project Type:** `saas_b2b`
- **Domain:** `general` (foodservice/planejamento operacional)
- **Complexity:** `medium`
- **Project Context:** `brownfield`

## Success Criteria

### User Success

Usuarios conseguem sair de contrato e restricoes para um cardapio salvo e exportavel sem trocar de ferramenta nem depender de planilha manual. O fluxo principal deve ser concluido com interacao guiada e feedback continuo, incluindo transparencia sobre custo alvo versus custo alcancado. O momento de valor esperado e quando o usuario recebe um cardapio tecnicamente valido com justificativa clara das escolhas e possibilidade de ajuste.

### Business Success

Reducao relevante do tempo operacional de elaboracao de cardapio e aumento de previsibilidade de margem por contrato. Adocao recorrente do fluxo de geracao por nutricionistas/gestores dentro da empresa tenant, com uso consistente de exportacao e aprovacao. Queda de retrabalho causado por inconsistencias contratuais e por estouro de PU em relacao ao baseline atual.

### Technical Success

Disponibilidade e estabilidade do fluxo completo (auth, leitura de contrato, pipeline, persistencia, exportacao) em ambiente Docker/Supabase. Integracao LLM centralizada via OpenRouter, com suporte operacional aos modelos definidos no projeto e selecao consistente por endpoint. Integridade multi-tenant preservada em leitura/escrita e em estatisticas exibidas na interface.

### Measurable Outcomes

- Tempo medio para gerar e salvar um cardapio de 30 dias: `<= 5 minutos`
- Taxa de fluxos completos sem erro (contrato -> gerar -> salvar): `>= 95%`
- Cardapios dentro do limite de PU configurado: `>= 90%` dos casos com dados suficientes
- Quando PU inatingivel: `100%` dos casos com mensagem explicativa e melhor cenario calculado
- Acesso a dashboard/header com contagens consistentes por empresa: `100%` das sessoes autenticadas

## Product Scope

### MVP - Minimum Viable Product

Selecao/upload de contrato, analise automatica, configuracao de dias/refeicoes/restricoes/custo, geracao de cardapio com pipeline IA, validacao de custo e nutricao, persistencia no banco, exportacao (XLSX/CSV/PDF) e visualizacao no modulo de cardapios. Inclui setup operacional em Docker com banco PostgreSQL/Supabase e observabilidade basica via endpoints de status.

### Growth Features (Post-MVP)

Refinamento conversacional avancado (HITL hibrido persistente), comparacao de multiplas alternativas de cardapio, melhorias de explainability e recomendacoes de substituicao orientadas a custo. Melhorias de governanca (auditoria de decisao por etapa, trilha de ajustes) e automacoes de revisao/aprovacao entre perfis.

### Vision (Future)

Geracao e edicao de fichas tecnicas com IA, inteligencia de mercado para variacao de preco de ingredientes, recalculo proativo de impacto financeiro e motor preditivo de custo. Evolucao para plataforma de inteligencia alimentar com API de integracao ERP e capacidades de planejamento assistido em escala multiunidade.

## User Journeys

### Jornada 1 - Nutricionista (fluxo principal de sucesso)

Camila, nutricionista de UAN, recebe um contrato novo com limite de custo por refeicao e regras detalhadas. Hoje ela costuma abrir planilhas antigas, copiar formulas e validar manualmente combinacoes de pratos. No MENU I.A, ela entra na tela de geracao, seleciona ou envia o contrato, revisa o resumo extraido e informa dias, refeicoes e restricoes operacionais. A geracao acontece em etapas com feedback visivel. No momento critico, ela compara custo alvo e custo encontrado com justificativa explicita da IA. Ela salva o cardapio e exporta para operacao. Resultado: sai de horas de tentativa/erro para minutos com rastreabilidade.

### Jornada 2 - Nutricionista (edge case: PU inatingivel)

Na semana seguinte, Camila recebe meta de PU agressiva para o mesmo contrato. A geracao nao consegue bater o valor sem quebrar restricoes nutricionais e contratuais. Em vez de falhar sem contexto, o sistema retorna o melhor cenario alcancavel, explica os bloqueios (fichas disponiveis, estrutura de refeicao, limites do contrato) e sugere ajustes. Camila usa a conversa para testar alternativas de restricao e refeicoes. O fluxo fecha com decisao informada: ajustar meta comercial, revisar base de fichas ou aceitar plano de custo minimo viavel.

### Jornada 3 - Gestor/Administrador de Operacao

Rafael, gestor da conta, precisa garantir uso padronizado e governanca. Ele acompanha indicadores no dashboard, confere consistencia de base (fichas, ingredientes, cardapios), valida se o modelo LLM ativo esta correto e monitora tempos de geracao. Quando ha mudanca de contrato ou politica interna, ele garante que a equipe use o fluxo oficial e que os resultados sejam salvos com historico. A virada de valor para Rafael e previsibilidade operacional: menos retrabalho, mais comparabilidade entre periodos e controle de risco de margem.

### Jornada 4 - Suporte/Troubleshooting

Luciana, analista de suporte interno, recebe chamado de "geracao travou no passo 3". Ela consulta status do job, logs de progresso e estado da sessao para identificar se foi erro de contrato, timeout externo ou inconsistencia de base. Com diagnostico rapido, orienta o usuario em acao corretiva objetiva (reenvio, ajuste de parametro ou reprocessamento). A resolucao eficaz depende de visibilidade tecnica e mensagens de erro acionaveis, evitando ciclos longos de tentativa cega.

### Jornada 5 - Integracao Tecnica (API/ERP)

Igor, desenvolvedor de integracao, conecta o ERP da empresa ao MENU I.A para disparar geracao e coletar resultados estruturados. Ele precisa autenticacao previsivel, payload validavel, status de job confiavel e formatos de exportacao estaveis. O ganho para Igor e reduzir acoplamento artesanal: a API passa a ser um componente governado do processo, permitindo automacao de ponta a ponta sem quebrar o fluxo humano quando necessario.

### Journey Requirements Summary

- Upload/selecao de contrato com deduplicacao e analise reutilizavel
- Fluxo conversacional com etapas claras e estados de carregamento/erro coerentes
- Mecanismo de justificativa de decisao (custo, restricoes, fallback)
- Persistencia de jobs, sessoes e mensagens para suporte e auditoria
- Dashboards e estatisticas consistentes por empresa (multi-tenant)
- Operacao admin para governanca de modelo, base e monitoramento
- API de integracao com contratos estaveis de autenticacao, status e exportacao

## Domain-Specific Requirements

### Compliance & Regulatory

- Conformidade com requisitos nutricionais aplicaveis (referencias operacionais CFN/ANVISA) para validacao do cardapio
- Aderencia estrita a clausulas contratuais de composicao de refeicoes, proibicoes e limites de custo
- Governanca de dados pessoais conforme LGPD para usuarios autenticados e trilhas de acesso

### Technical Constraints

- Isolamento multi-tenant por `empresa_id` em API, persistencia e estatisticas
- Transparencia de calculo de custo com rastreabilidade por ficha tecnica/ingrediente
- Observabilidade de jobs e estados de pipeline para diagnostico rapido
- Disponibilidade operacional em ambiente Docker + Supabase, com migracoes controladas

### Integration Requirements

- Integracao com armazenamento/consulta de contratos e artefatos de exportacao
- Endpoints estaveis para iniciar geracao, acompanhar status e consumir resultado exportavel
- Compatibilidade com fluxo humano (chat/UI) e fluxo sistemico (ERP/automacao)

### Risk Mitigations

- Risco: metas de PU inviaveis sem aviso claro
  Mitigacao: retorno obrigatorio de melhor cenario + justificativa
- Risco: inconsistencia entre regras de contrato e dados de fichas
  Mitigacao: validacao cruzada e bloqueios de geracao quando violacao critica
- Risco: degradacao por dependencia de provedor LLM
  Mitigacao: roteamento centralizado de modelos e controle administrativo de configuracao
- Risco: suporte lento por baixa visibilidade do pipeline
  Mitigacao: persistencia de jobs/sessoes/mensagens e status detalhado por etapa

## Innovation & Novel Patterns

### Detected Innovation Areas

- Orquestracao de agentes IA aplicada a problema operacional de alto atrito (contrato + custo + nutricao) com resultado acionavel
- Fluxo conversacional com explainability de decisao economica, nao apenas resposta textual
- Integracao entre base de fichas reais da empresa e raciocinio adaptativo para restricoes de contrato
- Possibilidade de operacao hibrida humano + automacao (UI conversacional e API de integracao)

### Market Context & Competitive Landscape

O mercado costuma separar ferramentas de cardapio, planilhas de custo e analise de contrato. O posicionamento aqui unifica estes blocos no mesmo fluxo operacional, com foco em viabilidade de PU e justificativa de escolha. Isso desloca a competicao de "gerador de cardapio" para "copiloto de decisao de margem e conformidade".

### Validation Approach

- Validar ganho operacional com pilotos comparando tempo e taxa de retrabalho contra baseline manual
- Medir precisao de aderencia contratual e nutricional em amostras de contratos reais
- Testar robustez de fallback em cenarios com PU inviavel
- Validar adocao por papel (nutricionista, gestor, suporte) e estabilidade de integracao API

### Risk Mitigation

- Risco de percepcao de "caixa-preta" da IA
  Mitigacao: detalhamento por etapa e justificativa de custo/restricao
- Risco de dependencias externas de modelo
  Mitigacao: gateway unico e controle central de modelos/parametros
- Risco de overpromessa comercial de inovacao
  Mitigacao: rollout por casos de uso mensuraveis com criterios de aceite objetivos

## SaaS B2B Specific Requirements

### Project-Type Overview

O produto deve operar como SaaS multi-tenant orientado a operacao critica de negocio (planejamento alimentar), com papeis organizacionais distintos e necessidade de governanca entre contrato, custo e conformidade. A experiencia precisa equilibrar autonomia do time funcional e controle administrativo.

### Technical Architecture Considerations

- Isolamento logico por tenant em toda a stack (API, jobs, banco e estatisticas)
- Controle de acesso por papel e escopo de empresa
- Camada de integracao com sistemas corporativos para consumo de resultados
- Telemetria operacional para monitorar geracoes, falhas e qualidade de saida

### Tenant Model

- Tenant primario: empresa de alimentacao coletiva
- Dados segregados por `empresa_id` (contratos, fichas, ingredientes, cardapios, sessoes e jobs)
- Operacoes cross-tenant permitidas apenas para papel `super_admin` com trilha de auditoria

### RBAC Matrix

- `super_admin`: visao global e administracao de plataforma
- `admin`: governanca da empresa/tenant, configuracoes e supervisao
- `nutricionista`: execucao principal de geracao e revisao tecnica
- `gestor`: aprovacao e controle de custo/operacao
- `visualizador`: consulta e acompanhamento sem alteracao

### Subscription Tiers

- Tier Basico: geracao assistida, persistencia e exportacao padrao
- Tier Profissional: recursos avancados de explainability, analytics e maior capacidade operacional
- Tier Enterprise: integracoes ampliadas, governanca estendida e suporte prioritario

### Integration List

- Integracao API para disparo e consulta de jobs
- Integracao com ERP/BI para consumo de cardapios e custos consolidados
- Integração com repositorio de contratos/documentos no fluxo operacional da empresa

### Compliance Requirements

- Conformidade de processos de dados com LGPD
- Aderencia a restricoes contratuais e politicas internas de auditoria
- Trilhas de acao para decisoes de geracao/aprovacao e eventos administrativos

### Implementation Considerations

- Priorizar estabilidade e previsibilidade do fluxo central antes de ampliar escopo
- Padronizar contratos de API para reduzir custo de integracao por cliente
- Estruturar feature flags para rollout gradual de capacidades IA avancadas

## Project Scoping

### Strategy & Philosophy

**Approach:** single-release orientado a valor operacional imediato, com entrega completa do fluxo central (contrato -> geracao -> validacao -> persistencia -> exportacao) sem remover requisitos declarados nos artefatos de entrada.

**Resource Requirements:** equipe minima com 1 backend, 1 frontend, 1 engenheiro de dados/plataforma e 1 perfil funcional (nutricao/operacao) para validacao de regra de negocio e aceite.

### Complete Feature Set

**Core User Journeys Supported:**
- Jornada principal de geracao (nutricionista)
- Jornada de excecao com PU inatingivel
- Jornada de governanca (gestor/admin)
- Jornada de suporte/diagnostico operacional
- Jornada de integracao tecnica por API

**Must-Have Capabilities:**
- Upload/selecao e analise de contrato
- Configuracao conversacional de parametros de geracao
- Pipeline de geracao com feedback de progresso
- Validacao de custo e conformidade nutricional
- Persistencia de cardapio, job e historico de execucao
- Exportacao em formatos operacionais
- Multi-tenant + RBAC + observabilidade minima

**Nice-to-Have Capabilities:**
- Explainability estendida com detalhamento tecnico por etapa
- Automacoes avancadas de aprovacao e revisao
- Integracoes corporativas ampliadas alem do fluxo principal
- Ajustes conversacionais mais sofisticados de HITL

### Risk Mitigation Strategy

**Technical Risks:** inconsistencias entre contrato e base tecnica, instabilidade de provedores LLM, falhas de fluxo assíncrono.  
Mitigacao: validacao cruzada, gateway centralizado de modelos, persistencia de estado e retries controlados.

**Market Risks:** baixa confianca em IA para decisao de custo e adesao parcial do time.  
Mitigacao: justificativa explicita de decisao, rollout por equipe piloto, metricas de ganho de tempo e margem.

**Resource Risks:** capacidade limitada para entregar tudo com qualidade no prazo.  
Mitigacao: foco no fluxo central, congelamento de escopo de release, backlog claro para evolucoes pos-release.

## Principios de Experiencia do Produto

- O fluxo deve ser orientado por etapas claras (wizard conversacional) sem quebrar o contexto do usuario.
- O sistema deve exibir a IA "pensando" e progredindo em tempo real para aumentar confianca operacional.
- A justificativa de custo deve aparecer em destaque, sempre conectando limite contratual, custo encontrado e margem.
- Ajustes do usuario devem ser tratados como parte do fluxo (nao excecao), com retorno explicavel.

## Functional Requirements

### Tenant & Access Management

- FR1: Super admins podem gerir organizacoes da plataforma e politicas globais de acesso.
- FR2: Admins de empresa podem gerir usuarios e papeis dentro da propria organizacao.
- FR3: O sistema pode aplicar permissoes por papel para `super_admin`, `admin`, `nutricionista`, `gestor` e `visualizador`.
- FR4: Usuarios autenticados podem acessar apenas dados e operacoes da propria organizacao.
- FR5: O sistema pode registrar eventos relevantes de acesso para auditoria.

### Contract Intelligence

- FR6: Usuarios podem selecionar um contrato existente como base para geracao de cardapio.
- FR7: Usuarios podem enviar um novo arquivo de contrato para iniciar o fluxo de geracao.
- FR8: O sistema pode extrair e persistir regras operacionais de contratos.
- FR9: O sistema pode apresentar resultados da interpretacao contratual em formato legivel.
- FR10: Usuarios podem prosseguir com a geracao mesmo com analise contratual parcial, com aviso explicito.

### Conversational Planning Workflow

- FR11: Usuarios podem configurar parametros de geracao por fluxo conversacional guiado.
- FR12: Usuarios podem definir horizonte de planejamento (dias) para uma solicitacao de geracao.
- FR13: Usuarios podem definir tipos de refeicao incluidos na solicitacao de geracao.
- FR14: Usuarios podem definir metas de custo e restricoes textuais adicionais.
- FR15: Usuarios podem revisar e confirmar todos os parametros antes da execucao.

### Menu Generation & Decision Transparency

- FR16: O sistema pode gerar cardapios usando restricoes contratuais e fichas tecnicas especificas da organizacao.
- FR17: O sistema pode expor estados de progresso da geracao durante a execucao.
- FR18: O sistema pode fornecer justificativa explicativa para decisoes-chave de planejamento e custo.
- FR19: O sistema pode reportar o melhor cenario alcancavel quando metas nao sao viaveis.
- FR20: Usuarios podem solicitar nova geracao apos ajustar restricoes.

### Technical Sheets & Ingredient Base

- FR21: Usuarios autorizados podem listar, visualizar, criar e atualizar fichas tecnicas.
- FR22: Usuarios autorizados podem listar, visualizar, criar e atualizar ingredientes.
- FR23: O sistema pode usar dados de fichas tecnicas e ingredientes como base autoritativa para calculo de custo.
- FR24: O sistema pode expor metricas de consistencia da base de fichas e ingredientes.

### Menu Lifecycle & Governance

- FR25: O sistema pode persistir cardapios gerados com contexto organizacional completo.
- FR26: Usuarios com autoridade de aprovacao podem executar transicoes de status de aprovacao de cardapio.
- FR27: Usuarios podem recuperar historico de cardapios gerados e metadados associados.
- FR28: O sistema pode preservar contexto de sessao de geracao necessario para suporte e rastreabilidade.

### Export & Operational Distribution

- FR29: Usuarios podem exportar cardapios finalizados em formatos operacionais.
- FR30: O sistema pode fornecer artefatos prontos para download e uso operacional.
- FR31: Usuarios podem acessar visualizacao detalhada de cardapio para revisao e publicacao.

### Administration, Monitoring & Integration

- FR32: Admins de empresa podem monitorar throughput de geracao e indicadores de saude operacional.
- FR33: Admins de plataforma podem controlar politicas ativas de configuracao de LLM em nivel de sistema.
- FR34: Perfis de suporte podem inspecionar estado de geracao e historico de sessao para troubleshooting.
- FR35: Sistemas externos podem disparar geracao e recuperar status/resultados por endpoints de API.
- FR36: O sistema pode expor endpoints canonicos de informacao usados por resumos de header/dashboard.

## Non-Functional Requirements

### Performance

- NFR1: Endpoints de leitura de estado operacional (`/api/health`, `/api/info`) devem responder em ate `2s` no percentil p95, sob carga nominal.
- NFR2: Operacoes de navegacao critica na UI (carregar dashboard, abrir fluxo de geracao, listar contratos) devem apresentar feedback inicial em ate `2s` no p95.
- NFR3: Geracao de cardapio deve iniciar processamento de job em ate `5s` apos confirmacao do usuario, salvo indisponibilidade externa explicitamente reportada.

### Security

- NFR4: Todo trafego entre cliente, API e servicos externos deve ocorrer com transporte criptografado.
- NFR5: O sistema deve aplicar controle de acesso por papel e por tenant em `100%` dos endpoints protegidos.
- NFR6: Segredos operacionais (tokens/chaves) nao podem ser expostos em logs, responses ou artefatos versionados.

### Reliability

- NFR7: O sistema deve manter rastreabilidade de jobs e sessoes para permitir retomada/diagnostico sem perda de contexto operacional.
- NFR8: Falhas em dependencias externas devem retornar estado de erro compreensivel e acionavel para usuario e suporte.
- NFR9: Operacoes de migracao e inicializacao devem falhar de forma explicita quando pre-condicoes de banco/ambiente nao forem atendidas.

### Scalability

- NFR10: A arquitetura deve suportar crescimento de `10x` no volume de jobs com degradacao controlada e monitoravel.
- NFR11: Camadas de estatistica e consultas frequentes devem utilizar estrategias de cache/otimizacao para reduzir impacto em banco.
- NFR12: O isolamento multi-tenant deve permanecer consistente independentemente de crescimento de tenants, usuarios e contratos.

### Accessibility

- NFR13: Interfaces web devem manter navegabilidade por teclado e contraste funcional em componentes de uso recorrente.
- NFR14: Estados de carregamento, erro e confirmacao devem ser apresentados em texto claro e nao depender apenas de indicacao visual.

### Integration

- NFR15: Endpoints de integracao devem manter contratos de request/response estaveis com versionamento controlado em mudancas quebradoras.
- NFR16: Formatos de exportacao devem preservar estrutura consistente para consumo operacional (planilhas, BI, ERP).
- NFR17: Integracoes externas devem expor status de processamento consultavel por identificador de job.
