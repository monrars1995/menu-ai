---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - docs/superpowers/specs/2026-05-03-chat-upload-inline-design.md
  - docs/superpowers/specs/2026-05-03-gerar-cardapio-chat-design.md
  - docs/superpowers/specs/2026-05-05-chat-conversacional-premium.md
---

# MENU I.A - Epic Breakdown

## Overview

Este documento organiza os requisitos do PRD em epicos e historias independentes, com criterios de aceite testaveis e rastreabilidade para implementacao.

## Requirements Inventory

### Functional Requirements

FR1: Super admins podem gerir organizacoes da plataforma e politicas globais de acesso.  
FR2: Admins de empresa podem gerir usuarios e papeis dentro da propria organizacao.  
FR3: O sistema pode aplicar permissoes por papel para `super_admin`, `admin`, `nutricionista`, `gestor` e `visualizador`.  
FR4: Usuarios autenticados podem acessar apenas dados e operacoes da propria organizacao.  
FR5: O sistema pode registrar eventos relevantes de acesso para auditoria.  
FR6: Usuarios podem selecionar um contrato existente como base para geracao de cardapio.  
FR7: Usuarios podem enviar um novo arquivo de contrato para iniciar o fluxo de geracao.  
FR8: O sistema pode extrair e persistir regras operacionais de contratos.  
FR9: O sistema pode apresentar resultados da interpretacao contratual em formato legivel.  
FR10: Usuarios podem prosseguir com a geracao mesmo com analise contratual parcial, com aviso explicito.  
FR11: Usuarios podem configurar parametros de geracao por fluxo conversacional guiado.  
FR12: Usuarios podem definir horizonte de planejamento (dias) para uma solicitacao de geracao.  
FR13: Usuarios podem definir tipos de refeicao incluidos na solicitacao de geracao.  
FR14: Usuarios podem definir metas de custo e restricoes textuais adicionais.  
FR15: Usuarios podem revisar e confirmar todos os parametros antes da execucao.  
FR16: O sistema pode gerar cardapios usando restricoes contratuais e fichas tecnicas especificas da organizacao.  
FR17: O sistema pode expor estados de progresso da geracao durante a execucao.  
FR18: O sistema pode fornecer justificativa explicativa para decisoes-chave de planejamento e custo.  
FR19: O sistema pode reportar o melhor cenario alcancavel quando metas nao sao viaveis.  
FR20: Usuarios podem solicitar nova geracao apos ajustar restricoes.  
FR21: Usuarios autorizados podem listar, visualizar, criar e atualizar fichas tecnicas.  
FR22: Usuarios autorizados podem listar, visualizar, criar e atualizar ingredientes.  
FR23: O sistema pode usar dados de fichas tecnicas e ingredientes como base autoritativa para calculo de custo.  
FR24: O sistema pode expor metricas de consistencia da base de fichas e ingredientes.  
FR25: O sistema pode persistir cardapios gerados com contexto organizacional completo.  
FR26: Usuarios com autoridade de aprovacao podem executar transicoes de status de aprovacao de cardapio.  
FR27: Usuarios podem recuperar historico de cardapios gerados e metadados associados.  
FR28: O sistema pode preservar contexto de sessao de geracao necessario para suporte e rastreabilidade.  
FR29: Usuarios podem exportar cardapios finalizados em formatos operacionais.  
FR30: O sistema pode fornecer artefatos prontos para download e uso operacional.  
FR31: Usuarios podem acessar visualizacao detalhada de cardapio para revisao e publicacao.  
FR32: Admins de empresa podem monitorar throughput de geracao e indicadores de saude operacional.  
FR33: Admins de plataforma podem controlar politicas ativas de configuracao de LLM em nivel de sistema.  
FR34: Perfis de suporte podem inspecionar estado de geracao e historico de sessao para troubleshooting.  
FR35: Sistemas externos podem disparar geracao e recuperar status/resultados por endpoints de API.  
FR36: O sistema pode expor endpoints canonicos de informacao usados por resumos de header/dashboard.

### NonFunctional Requirements

NFR1: Endpoints de estado operacional respondem em ate 2s p95 sob carga nominal.  
NFR2: Navegacao critica da UI responde com feedback inicial em ate 2s p95.  
NFR3: Job de geracao inicia em ate 5s apos confirmacao.  
NFR4: Trafego criptografado em transito.  
NFR5: Controle de acesso por papel e tenant em 100% dos endpoints protegidos.  
NFR6: Segredos nao expostos em logs ou artefatos versionados.  
NFR7: Rastreabilidade de jobs e sessoes sem perda de contexto.  
NFR8: Falhas externas retornam erro acionavel.  
NFR9: Setup/migracao falham de forma explicita quando pre-condicoes faltarem.  
NFR10: Suporte a crescimento 10x de jobs com degradacao controlada.  
NFR11: Cache/otimizacao para consultas frequentes.  
NFR12: Isolamento multi-tenant preservado com crescimento.  
NFR13: Navegabilidade por teclado e contraste funcional.  
NFR14: Estados de carregamento/erro/confirmacao em texto claro.  
NFR15: Contratos de API estaveis com versionamento de quebra.  
NFR16: Exportacoes com estrutura consistente para ERP/BI.  
NFR17: Integracoes externas consultam status por job id.

### Additional Requirements

- Banco oficial PostgreSQL/Supabase com migracoes Alembic
- OpenRouter como gateway padrao para LLM
- Persistencia de sessao/mensagens de chat para suporte
- Execucao oficial em Docker para ambientes suportados

### UX Design Requirements

UX-DR1: Fluxo de geracao em etapas conversacionais claras (welcome -> contrato -> parametros -> confirmacao -> execucao -> resultado).  
UX-DR2: Upload inline e drag-and-drop de contrato no fluxo de chat.  
UX-DR3: Exibicao de progresso por etapa do pipeline e "pensamento" da IA quando aplicavel.  
UX-DR4: Cartao de justificativa de custo e margem sempre visivel no resultado.  
UX-DR5: Estados de erro com mensagem acionavel e opcao de tentativa novamente.  
UX-DR6: Interface consistente com acessibilidade funcional (teclado, contraste, texto em estados criticos).  
UX-DR7: Possibilidade de ajustes conversacionais sem sair do fluxo.  
UX-DR8: Persistencia da sessao para retomada de contexto e suporte.

### FR Coverage Map

FR1 -> Epic 1 Story 1.2  
FR2 -> Epic 1 Story 1.3  
FR3 -> Epic 1 Story 1.3  
FR4 -> Epic 1 Story 1.2  
FR5 -> Epic 1 Story 1.4  
FR6 -> Epic 2 Story 2.1  
FR7 -> Epic 2 Story 2.2  
FR8 -> Epic 2 Story 2.3  
FR9 -> Epic 2 Story 2.3  
FR10 -> Epic 2 Story 2.4  
FR11 -> Epic 3 Story 3.1  
FR12 -> Epic 3 Story 3.1  
FR13 -> Epic 3 Story 3.1  
FR14 -> Epic 3 Story 3.1  
FR15 -> Epic 3 Story 3.2  
FR16 -> Epic 3 Story 3.3  
FR17 -> Epic 3 Story 3.3  
FR18 -> Epic 3 Story 3.4  
FR19 -> Epic 3 Story 3.4  
FR20 -> Epic 3 Story 3.4  
FR21 -> Epic 4 Story 4.1  
FR22 -> Epic 4 Story 4.2  
FR23 -> Epic 4 Story 4.3  
FR24 -> Epic 4 Story 4.4  
FR25 -> Epic 5 Story 5.1  
FR26 -> Epic 5 Story 5.2  
FR27 -> Epic 5 Story 5.3  
FR28 -> Epic 5 Story 5.1  
FR29 -> Epic 5 Story 5.4  
FR30 -> Epic 5 Story 5.4  
FR31 -> Epic 5 Story 5.3  
FR32 -> Epic 6 Story 6.1  
FR33 -> Epic 6 Story 6.2  
FR34 -> Epic 6 Story 6.3  
FR35 -> Epic 6 Story 6.4  
FR36 -> Epic 6 Story 6.1

## Epic List

### Epic 1: Fundacao de Plataforma e Seguranca Multi-tenant
Entregar autenticacao, autorizacao e isolamento de tenant como base operacional segura.
**FRs covered:** FR1, FR2, FR3, FR4, FR5

### Epic 2: Inteligencia de Contratos
Permitir que contratos sejam usados como entrada confiavel para regras de geracao.
**FRs covered:** FR6, FR7, FR8, FR9, FR10

### Epic 3: Geração Conversacional de Cardápio
Entregar o fluxo principal do usuario com configuracao, execucao e explicabilidade.
**FRs covered:** FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR20

### Epic 4: Base Tecnica e Custos
Garantir base de fichas/ingredientes confiavel para calculo e consistencia.
**FRs covered:** FR21, FR22, FR23, FR24

### Epic 5: Ciclo de Vida do Cardapio e Exportacao
Cobrir persistencia, aprovacao, historico e distribuicao operacional.
**FRs covered:** FR25, FR26, FR27, FR28, FR29, FR30, FR31

### Epic 6: Governanca, Suporte e Integracoes
Entregar visibilidade operacional, configuracao central e integrações externas.
**FRs covered:** FR32, FR33, FR34, FR35, FR36

## Epic 1: Fundacao de Plataforma e Seguranca Multi-tenant

Garantir que toda funcionalidade de negocio opere com autenticacao valida, papeis corretos e escopo de empresa.

### Story 1.1: Subir stack base em ambiente oficial
As a admin de plataforma,  
I want executar a stack base em Docker com banco PostgreSQL/Supabase,  
So that o time tenha ambiente consistente para desenvolvimento e validacao.

**Acceptance Criteria:**

**Given** o repositorio com configuracoes de runtime  
**When** o ambiente e inicializado  
**Then** API e componentes essenciais ficam disponiveis  
**And** as migracoes sao aplicadas com falha explicita em caso de erro.

### Story 1.2: Implementar autenticacao JWT e escopo de tenant
As a usuario autenticado,  
I want acessar apenas dados da minha empresa apos login valido,  
So that informacoes de outros tenants permaneçam isoladas.

**Acceptance Criteria:**

**Given** um token JWT valido  
**When** o usuario acessa endpoints protegidos  
**Then** o sistema valida autenticacao e aplica filtro por empresa  
**And** acessos fora do escopo retornam erro de autorizacao.

### Story 1.3: Aplicar matriz RBAC por papel
As a admin de empresa,  
I want permissões coerentes por papel em cada operacao,  
So that cada perfil execute apenas o permitido.

**Acceptance Criteria:**

**Given** usuarios com papeis distintos  
**When** tentam executar operacoes de leitura/escrita/aprovacao  
**Then** o sistema permite ou bloqueia de acordo com a matriz RBAC  
**And** o comportamento e consistente em menu, admin e API.

### Story 1.4: Registrar eventos de acesso e saude de stack
As a suporte tecnico,  
I want consultar eventos de acesso e endpoints de saude,  
So that diagnosticos sejam rapidos e auditaveis.

**Acceptance Criteria:**

**Given** operacoes autenticadas e chamadas de status  
**When** o sistema processa as requisicoes  
**Then** eventos relevantes sao registrados com contexto minimo  
**And** endpoints canonicos de saude/info respondem em formato consistente.

## Epic 2: Inteligencia de Contratos

Permitir ingestao e interpretacao de contratos com reutilizacao de analises e fallback controlado.

### Story 2.1: Selecionar contrato existente no fluxo de geracao
As a nutricionista,  
I want escolher contratos ja cadastrados no inicio do fluxo,  
So that eu evite retrabalho de upload quando o contrato ja existe.

**Acceptance Criteria:**

**Given** contratos disponiveis para a empresa  
**When** o usuario inicia a geracao  
**Then** o sistema lista contratos elegiveis para selecao  
**And** guarda o contrato selecionado no contexto da sessao.

### Story 2.2: Upload e deduplicacao de contrato
As a nutricionista,  
I want enviar novo contrato no proprio fluxo com deduplicacao por hash,  
So that o sistema nao duplique arquivos e registros equivalentes.

**Acceptance Criteria:**

**Given** um arquivo valido de contrato  
**When** o upload e processado  
**Then** o sistema reaproveita contrato existente quando hash coincidir  
**And** cria novo contrato somente quando nao houver correspondencia.

### Story 2.3: Interpretacao e persistencia de regras contratuais
As a nutricionista,  
I want visualizar o resumo de regras extraidas do contrato,  
So that eu confirme o entendimento antes de gerar o cardapio.

**Acceptance Criteria:**

**Given** um contrato selecionado ou enviado  
**When** a analise e executada  
**Then** regras principais ficam persistidas e consultaveis  
**And** o resumo apresentado inclui refeicoes, limites e restricoes.

### Story 2.4: Fallback para analise parcial
As a nutricionista,  
I want continuar o fluxo mesmo com analise parcial,  
So that eu nao fique bloqueada por falhas nao criticas.

**Acceptance Criteria:**

**Given** falha parcial na analise contratual  
**When** o fluxo avanca  
**Then** o sistema exibe aviso explicito de limitacao  
**And** permite geracao com comportamento de fallback controlado.

## Epic 3: Geração Conversacional de Cardápio

Entregar configuracao guiada, execucao em pipeline e explicabilidade de resultado.

### Story 3.1: Capturar parametros de geracao via chat/wizard
As a nutricionista,  
I want informar dias, refeicoes, custo e restricoes em fluxo guiado,  
So that a solicitacao de geracao fique completa e consistente.

**Acceptance Criteria:**

**Given** contrato no contexto da sessao  
**When** o usuario preenche os parametros obrigatorios  
**Then** o sistema valida os campos e preserva estado da configuracao  
**And** permite ajustes antes da confirmacao final.

### Story 3.2: Confirmar solicitacao e iniciar job de geracao
As a nutricionista,  
I want confirmar os parametros e disparar a geracao,  
So that o pipeline execute com rastreabilidade.

**Acceptance Criteria:**

**Given** parametros validados  
**When** o usuario confirma a geracao  
**Then** um job e criado com identificador unico  
**And** estado inicial fica disponivel para consulta e streaming.

### Story 3.3: Exibir progresso de pipeline em tempo real
As a nutricionista,  
I want acompanhar etapas e progresso da geracao,  
So that eu entenda o andamento sem recarregar a pagina.

**Acceptance Criteria:**

**Given** job em execucao  
**When** o frontend abre o stream de progresso  
**Then** eventos de etapa/progresso sao exibidos de forma incremental  
**And** falhas interrompem o fluxo com mensagem acionavel.

### Story 3.4: Explicar resultado e permitir regeneracao
As a nutricionista,  
I want receber justificativa de custo e opcao de ajustar restricoes,  
So that eu consiga otimizar o resultado quando PU nao for atingido.

**Acceptance Criteria:**

**Given** resultado concluido ou fallback de inviabilidade  
**When** o sistema apresenta o output  
**Then** justificativas de decisao ficam visiveis  
**And** o usuario pode ajustar entradas e solicitar nova geracao.

## Epic 4: Base Tecnica e Custos

Consolidar gestao da base de fichas/ingredientes com calculo confiavel para o motor de geracao.

### Story 4.1: CRUD de fichas tecnicas por tenant
As a nutricionista,  
I want gerenciar fichas tecnicas da minha empresa,  
So that o motor use receitas atualizadas e corretas.

**Acceptance Criteria:**

**Given** usuario com permissao  
**When** cria, altera, lista ou consulta fichas  
**Then** operacoes respeitam escopo de empresa  
**And** dados persistem com validacao minima obrigatoria.

### Story 4.2: CRUD de ingredientes por tenant
As a nutricionista,  
I want gerenciar ingredientes e custos unitarios,  
So that os calculos de ficha reflitam a realidade operacional.

**Acceptance Criteria:**

**Given** usuario com permissao  
**When** cria, altera, lista ou consulta ingredientes  
**Then** operacoes respeitam escopo de empresa  
**And** custo e unidade ficam disponiveis para composicao de fichas.

### Story 4.3: Calculo de custo e nutricao por ficha
As a nutricionista,  
I want recalcular custo e indicadores nutricionais das fichas,  
So that a base tecnica fique consistente para planejamento.

**Acceptance Criteria:**

**Given** ficha com ingredientes vinculados  
**When** aciona recalculo  
**Then** custo total e por porcao sao atualizados  
**And** indicadores nutricionais disponiveis sao recalculados.

### Story 4.4: Expor metricas de consistencia da base
As a gestor,  
I want ver indicadores de saude da base tecnica,  
So that eu identifique lacunas antes da geracao.

**Acceptance Criteria:**

**Given** base de fichas e ingredientes cadastrada  
**When** consulta indicadores de consistencia  
**Then** sistema informa volumes e situacoes relevantes  
**And** dados suportam decisao de melhoria de base.

## Epic 5: Ciclo de Vida do Cardápio e Exportacao

Persistir resultados, suportar aprovacao e distribuir artefatos operacionais.

### Story 5.1: Persistir cardapio e contexto de geracao
As a nutricionista,  
I want salvar cardapios gerados com contexto completo,  
So that eu recupere o historico com rastreabilidade.

**Acceptance Criteria:**

**Given** geracao concluida  
**When** o resultado e salvo  
**Then** cardapio, parametros e referencias de job/sessao ficam persistidos  
**And** dados podem ser consultados posteriormente.

### Story 5.2: Implementar workflow de aprovacao
As a gestor,  
I want aprovar ou reprovar cardapios por status,  
So that governanca operacional seja aplicada antes da publicacao.

**Acceptance Criteria:**

**Given** cardapio em estado elegivel  
**When** usuario autorizado executa transicao  
**Then** status e atualizado conforme regra de aprovacao  
**And** acao fica registrada para auditoria.

### Story 5.3: Exibir detalhamento e historico de cardapios
As a usuario autorizado,  
I want abrir cardapio detalhado e historico relacionado,  
So that eu revise conteudo antes de exportar/publicar.

**Acceptance Criteria:**

**Given** cardapios persistidos  
**When** usuario abre detalhe ou lista historica  
**Then** sistema retorna metadados e composicao consultavel  
**And** acesso respeita papel e tenant.

### Story 5.4: Exportar em formatos operacionais
As a gestor,  
I want exportar cardapios em formatos padrao,  
So that operacao, compras e BI consumam os dados.

**Acceptance Criteria:**

**Given** cardapio aprovado ou elegivel para distribuicao  
**When** usuario solicita exportacao  
**Then** arquivo e gerado em formato suportado  
**And** estrutura do arquivo permanece consistente entre execucoes.

## Epic 6: Governanca, Suporte e Integracoes

Entregar capacidades administrativas e integracao tecnica para escala operacional.

### Story 6.1: Dashboard e endpoints canonicos de informacao
As a admin de empresa,  
I want acompanhar indicadores chave e contagens consistentes,  
So that a equipe tenha visao operacional unificada.

**Acceptance Criteria:**

**Given** dados da empresa no banco  
**When** dashboard/header consulta informacoes  
**Then** endpoints retornam contagens consistentes por tenant  
**And** estados de carregamento/erro sao tratados de forma coerente.

### Story 6.2: Configuracao administrativa de modelos LLM
As a super_admin,  
I want controlar modelos e politicas de execucao de LLM,  
So that a plataforma mantenha governanca tecnica.

**Acceptance Criteria:**

**Given** painel administrativo habilitado  
**When** super_admin altera configuracao de modelo  
**Then** mudancas sao persistidas e refletidas no fluxo de geracao  
**And** tentativas sem permissao sao bloqueadas.

### Story 6.3: Ferramentas de suporte para troubleshooting
As a suporte tecnico,  
I want consultar estado de jobs e sessoes com contexto,  
So that eu resolva incidentes com rapidez.

**Acceptance Criteria:**

**Given** eventos e estado persistidos  
**When** suporte consulta job/sessao  
**Then** sistema retorna trilha suficiente para diagnostico  
**And** mensagens de erro permitem acao corretiva objetiva.

### Story 6.4: API de integração para sistemas externos
As a integrador ERP,  
I want disparar geracao e consultar resultados por API,  
So that processos corporativos executem automacoes ponta a ponta.

**Acceptance Criteria:**

**Given** credenciais validas e payload conforme contrato  
**When** sistema externo aciona endpoints de geracao/status  
**Then** API responde com status e identificadores consistentes  
**And** contratos de integracao mantem compatibilidade versionada.
