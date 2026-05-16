# Product Brief: Menu.AI

> **Versão:** 1.0 | **Data:** 2026-05-16 | **Autor:** Monrars / GoldNeuron  
> **Status:** Rascunho para Validação

---

## Sumário Executivo

O **Menu.AI** é uma plataforma SaaS de inteligência artificial para planejamento de cardápios em operações de alimentação coletiva. O sistema resolve um problema crônico do setor: a montagem manual de cardápios que respeitem simultaneamente contratos, custos, nutrição e fichas técnicas — um processo que hoje consome horas de trabalho especializado e frequentemente resulta em estouros de custo ou descumprimento contratual.

A proposta é transformar esse processo em uma experiência conversacional com IA. O nutricionista ou gestor informa o contrato, define o **preço unitário (PU)** alvo por refeição, e o agente de IA monta o cardápio mais competitivo possível usando a base real de fichas técnicas e ingredientes da empresa. Se o PU desejado não for alcançável, a IA comunica o melhor cenário possível e explica por quê.

O Menu.AI não é apenas um gerador automático — é um **copiloto operacional** que raciocina, conversa e negocia o melhor resultado dentro das regras do jogo. Isso muda a dinâmica: ao invés de montar cardápios por tentativa e erro, o profissional conversa com um especialista de IA que conhece o contrato, os custos e as fichas técnicas.

---

## O Problema

Nutricionistas e gestores de alimentação coletiva enfrentam uma equação complexa toda semana:

- **Contratos rígidos**: cada contrato de fornecimento de refeições define regras de composição, tipos de refeição, gramatura, restrições e limites de custo. Descumprir um contrato pode gerar multas ou perda do cliente.
- **Custo unitário apertado**: o PU (Preço Unitário por refeição) é a métrica central do negócio. Um almoço que deveria custar no máximo R$ 8,29 precisa respeitar esse limite em cada um dos 30 dias do cardápio — sem repetir pratos excessivamente e mantendo qualidade nutricional.
- **Base técnica volumosa**: empresas do setor operam com centenas a milhares de fichas técnicas (receitas padronizadas com ingredientes, custos e rendimentos). Cruzar manualmente fichas com contratos e orçamentos é inviável em escala.
- **Ferramentas inadequadas**: hoje, a montagem é feita em planilhas Excel, com cálculos manuais de custo. Não existe inteligência que combine contrato + fichas + custo + nutrição de forma automatizada e conversacional.

**Consequência:** profissionais gastam horas montando cardápios que frequentemente estouram o orçamento, repetem pratos demais ou descumprem cláusulas contratuais. A "planilha" não conversa, não sugere alternativas e não justifica escolhas.

---

## A Solução

O Menu.AI opera como um agente inteligente de 7 etapas que:

1. **Lê e interpreta o contrato** — extrai regras, limites de custo, tipos de refeição, restrições e gramaturas
2. **Consulta fichas técnicas reais** — seleciona pratos compatíveis com custo e contrato do banco da empresa
3. **Monta o cardápio otimizado** — combina prato principal, opções e acompanhamentos dia a dia
4. **Valida nutrição** — confere conformidade com normas CFN/ANVISA
5. **Calcula o custo real** — custo por porção, por dia, margem vs. PU alvo
6. **Gera lista de compras** — consolidada por ingrediente
7. **Conversa com o profissional** — explica decisões, aceita ajustes, regenera conforme pedido

O diferencial central: **se o PU alvo não for alcançável, a IA busca o valor mais próximo possível e comunica claramente**: *"Este é o máximo que consigo fazer dentro das regras do contrato. Quer que eu tente uma alternativa?"*

---

## O que Torna o Menu.AI Diferente

| Aspecto | Planilhas / Concorrentes | Menu.AI |
|---------|--------------------------|---------|
| **Montagem** | Manual, tentativa e erro | IA monta e justifica |
| **Contrato** | Arquivo ignorado / decorado | Lido, interpretado, transformado em regras |
| **Custo** | Calculado manualmente | Calculado em tempo real por ficha técnica |
| **PU** | Verificado no final (surpresas) | É o ponto de partida da geração |
| **Nutrição** | Checada por fora | Validada automaticamente (CFN/ANVISA) |
| **Conversa** | Inexistente | Agente explica, sugere, adapta |
| **Escala** | 1 cardápio = horas | 1 cardápio = minutos |

**Vantagem competitiva real:** a combinação de interpretação de contratos reais + base de fichas técnicas próprias da empresa + otimização de custo com IA conversacional é única. Não existe solução no mercado que faça esse cruzamento de forma inteligente e interativa.

---

## Quem o Menu.AI Atende

### Público Primário

- **Nutricionistas de alimentação coletiva**: profissionais que montam cardápios para restaurantes industriais, escolas, hospitais, UAN (Unidades de Alimentação e Nutrição). Precisam equilibrar custo, nutrição, contrato e variedade. Hoje gastam horas em planilhas.

- **Empresas de alimentação coletiva**: concessionárias de refeições (Graal, Sapore, CRM e similares regionais) que gerenciam múltiplos contratos com PUs diferentes. Precisam de escala e padronização.

### Público Secundário

- **Gestores operacionais**: responsáveis por aprovação de cardápios e controle de custos em operações de alimentação.
- **Consultores de nutrição**: que prestam serviços para múltiplas empresas e precisam de produtividade.

### Perfil do Usuário Ideal (MVP)

Nutricionista ou gestor que:
- Opera com 500+ fichas técnicas cadastradas
- Gerencia pelo menos 1 contrato de fornecimento de refeições
- Precisa montar cardápios mensais (30 dias) com PU controlado
- Hoje usa Excel e leva 4-8 horas por cardápio

---

## Critérios de Sucesso (MVP)

### Métrica Principal: PU Alcançado

O cardápio gerado deve respeitar o **Preço Unitário (PU)** alvo informado pelo usuário.

**Meta:** em um cardápio de 30 dias, o custo unitário do almoço **não exceder R$ 8,29** (ou o valor configurado pelo contrato).

**Cenário de fallback:** se o PU alvo for inatingível com as fichas disponíveis, o sistema deve:
1. Informar o valor mais próximo alcançável
2. Explicar por que não conseguiu atingir o PU
3. Sugerir alternativas (substituição de fichas, renegociação do contrato)

### Métricas Complementares

| Métrica | Alvo |
|---------|------|
| Fluxo completo (contrato → cardápio salvo) | Funcionar de ponta a ponta |
| Tempo de geração de um cardápio 30 dias | < 5 minutos |
| Conformidade com regras do contrato | 100% |
| Conformidade nutricional CFN/ANVISA | Reportada automaticamente |
| Satisfação do usuário com a IA | Usuário entende as escolhas da IA |

---

## Escopo

### MVP (V1) — Fechar o fluxo de ponta a ponta

**Dentro do escopo:**
- Selecionar contrato existente ou fazer upload de PDF
- IA ler e resumir contrato (extrair regras operacionais)
- Usuário informar PU alvo e restrições por texto livre
- IA montar cardápio usando fichas técnicas reais da empresa
- Cálculo de custo real por preparação, por dia e total
- Comparação custo vs. PU alvo com margem de segurança
- Comunicação inteligente quando PU não for alcançável
- Salvamento do cardápio gerado com status e histórico
- Exportação (XLSX, CSV, PDF)
- Dashboard com métricas de fichas, ingredientes e cardápios

**Fora do escopo (V1):**
- Criação de fichas técnicas com IA
- Pesquisa de preços de mercado
- Comparação entre múltiplas alternativas de cardápio lado a lado
- Memória de preferências entre sessões
- App mobile

### Modelo de Negócio

**SaaS por empresa (multi-tenant)**
- Cada empresa é um tenant isolado
- Dados (fichas, contratos, cardápios) são exclusivos por empresa
- Modelo de cobrança baseado em plano por empresa

---

## Visão (2-3 anos)

### V2 — Produto mais inteligente
- **Criação de fichas técnicas com IA**: o usuário descreve uma preparação e a IA monta a ficha completa (ingredientes, quantidades, custo, modo de preparo, rendimento)
- **Edição inteligente de fichas**: "Troque carne bovina por frango", "Reduza o custo dessa ficha", "Adapte para 100 porções"
- **Chat com memória**: IA lembra preferências e decisões anteriores do usuário
- **Comparação de alternativas**: apresentar 2-3 opções de cardápio para o usuário escolher

### V3 — Ecossistema de inteligência alimentar
- **Pesquisa de preços de mercado**: monitoramento automático de preços de ingredientes com alertas e sugestões de substituição
- **Recalculamento automático**: quando um ingrediente sobe de preço, o sistema recalcula fichas e sugere ajustes
- **Análise preditiva**: previsão de custos futuros baseada em tendências de mercado
- **Marketplace de fichas técnicas**: compartilhamento de receitas entre empresas (opt-in)
- **API para integração**: conexão com ERPs de alimentação coletiva

---

## Frase de Posicionamento

> **Menu.AI é o copiloto de IA que lê contratos, interpreta regras alimentares, usa fichas técnicas e preços reais para gerar cardápios competitivos — explicáveis, adaptáveis por conversa e sempre dentro do PU.**

---

## Abordagem Técnica (Alto Nível)

| Componente | Tecnologia |
|------------|------------|
| Backend API | FastAPI (Python) |
| Frontend | Next.js |
| Pipeline IA | 7 agentes LLM sequenciais (LiteLLM + LangChain) |
| Banco de dados | PostgreSQL (Supabase) |
| Auth | Supabase (JWKS) + RBAC (5 roles) |
| Deploy | Docker Stack (produção) |
| Modelos LLM | OpenRouter (multi-provider fallback) |

O pipeline de 7 agentes garante que cada aspecto do cardápio é tratado por um "especialista" dedicado: análise de contrato, seleção de fichas, montagem nutricional, validação, cálculo de custo, lista de compras e exportação final.

---

*Documento gerado como parte do workflow BMad Product Brief*  
*Projeto: Menu.AI | GoldNeuron.io | @monrars*
