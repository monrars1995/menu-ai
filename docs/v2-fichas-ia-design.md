# Especificação: Módulo V2 - Fichas Técnicas com IA

## Visão Geral
Este documento define a arquitetura e o fluxo de dados para a nova feature (V2) do Menu.AI, cujo objetivo é permitir aos utilizadores (Nutricionistas/Empresas) a criação de **Fichas Técnicas através de Inteligência Artificial**. 
Através de um input natural simples (ex: "Receita de Arroz com feijão para 50 pessoas, 5kg de arroz, 2kg de feijão, refogado no alho e cebola"), a IA identificará os ingredientes no banco de dados da empresa, calculará os pesos e o custo e criará o esqueleto da ficha técnica.

## 1. Arquitetura da Interface (UI)

A UI do módulo será construída em Next.js (já existente no ecossistema) e oferecerá uma abordagem híbrida, combinando um input conversacional com um formulário de revisão estruturado.

### 1.1 Input Natural (Chat/Prompt)
- Uma área principal de `textarea` onde o utilizador escreve a receita de forma corrida.
- Botão "Gerar Ficha Técnica com IA".
- Exibição de um estado de _loading_ visual (ex: skeleton) enquanto a IA processa o texto.

### 1.2 Formulário Estruturado (Revisão)
- Após a geração, a UI transita para um formulário editável onde são apresentados:
  - **Nome do Prato** e **Categoria**.
  - **Rendimento** (número de porções e peso total aproximado).
  - **Ingredientes (Tabela)**: Colunas com Nome, Quantidade Líquida, Quantidade Bruta, Fator de Correção (FC) e Custo Unitário estimado.
  - **Modo de Preparo**: Texto extraído/formatado passo-a-passo.

## 2. Pipeline Backend (FastAPI + LiteLLM)

### 2.1 Endpoint de Geração
Será criado um novo endpoint `POST /api/fichas/gerar-ia`. O payload receberá o texto natural introduzido pelo utilizador.

### 2.2 Estrutura do Prompt e Agent
Um agente especializado será configurado no orquestrador:
- **Role**: Analista de Fichas Técnicas.
- **Task**: Ler o texto, identificar ingredientes e modos de preparo.
- **Tools**:
  - `buscar_ingrediente`: Ferramenta para buscar os ingredientes citados contra o catálogo da empresa para obter os IDs reais e o custo base.
- **Output**: JSON estruturado de acordo com o modelo Pydantic da Ficha Técnica.

### 2.3 Cálculo e Custo
- O LLM usará os IDs reais da base de dados e os custos lá definidos.
- A aplicação backend (não o LLM) fará o recalculo de Custo Total e Custo por Porção antes de devolver o resultado ao front-end, garantindo exatidão matemática.

## 3. Fluxo de Aprovação Humana

Para evitar a propagação de "alucinações" do LLM no catálogo da empresa:

1. **Geração (Rascunho)**: O resultado devolvido pela IA nunca é guardado automaticamente na base como final. Ele existe temporariamente no frontend ou é guardado com um status `RASCUNHO`.
2. **Revisão Humana**: O utilizador pode alterar quantidades, substituir um ingrediente incorreto ou refinar o modo de preparo diretamente na UI estruturada.
3. **Submissão**: O utilizador clica em "Salvar Ficha". Só neste momento o sistema insere o registo permanentemente nas tabelas de `FichaTecnica` e `Ingrediente_FichaTecnica`, ficando disponível para os pipelines de Planeamento de Cardápios.

## 4. Próximos Passos
- Definir o schema JSON para o LLM.
- Criar a ferramenta de LangChain para `buscar_ingrediente`.
- Mocar o endpoint e desenhar a página no Next.js (Dashboard).
