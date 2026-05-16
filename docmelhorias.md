A ideia central do **Menu.AI** é transformar a geração de cardápios em um processo inteligente, conversacional e orientado por custo, contrato, fichas técnicas e restrições operacionais.

Hoje o produto já está bem posicionado como uma plataforma com módulos claros: **Dashboard**, **Gerar Cardápio**, **Cardápios**, **Fichas Técnicas**, **Contratos** e **Ingredientes**. Pelos áudios, o foco agora não é criar mais complexidade, mas fazer o fluxo principal rodar até o fim com qualidade.

## 1. Visão geral do produto

O **Menu.AI** é um agente de IA para restaurantes, nutricionistas e operações de alimentação que ajuda a montar cardápios competitivos usando:

* fichas técnicas existentes;
* ingredientes cadastrados;
* contratos e regras de alimentação;
* restrições informadas pelo usuário;
* custo máximo permitido;
* combinação entre prato principal, prato opcional e demais componentes;
* lógica de melhor custo para o dia.

A proposta não é apenas “gerar um cardápio”, mas **negociar inteligentemente o melhor cardápio possível dentro das regras do contrato e da realidade operacional**.

## 2. O agente de IA

O agente deve funcionar como um especialista de cardápios. Ele analisa o contrato, entende o banco de fichas técnicas, considera os custos e conversa com o usuário para chegar no melhor resultado.

A grande sacada dos áudios é que a IA não deve ser só um botão de geração automática. Ela deve ser uma camada de raciocínio e conversa.

Exemplo do papel do agente:

> “Com base no contrato, no custo máximo de R$ 10, nas fichas disponíveis e nas restrições informadas, encontrei três combinações possíveis. A mais competitiva é esta, porque mantém variedade, respeita o custo e usa ingredientes já cadastrados.”

Isso deixa o produto mais humano, porque o usuário pode conversar com a IA, pedir ajustes, questionar escolhas e informar preferências.

## 3. Fluxo principal da versão atual

A versão que precisa ser fechada agora deve priorizar o fluxo completo:

### Etapa 1 — Selecionar ou subir contrato

Na tela **Gerar Cardápio**, a interface já mostra dois caminhos:

* **Selecionar Contrato**
* **Upload PDF**

Esse é o ponto de entrada correto. O usuário deve poder escolher um contrato já cadastrado ou enviar um novo PDF.

### Etapa 2 — IA lê e resume o contrato

Uma das melhores partes mencionadas nos áudios é a IA conseguir ler o contrato e resumir as etapas principais.

Esse resumo deveria extrair, por exemplo:

* nome do contrato;
* cliente ou unidade;
* período;
* custo máximo;
* regras de alimentação;
* tipos de refeição;
* restrições obrigatórias;
* exigências nutricionais;
* quantidades;
* composição esperada do cardápio;
* observações críticas.

A IA não deve apenas “ler o PDF”; ela deve transformar o contrato em regras operacionais utilizáveis pelo gerador de cardápio.

### Etapa 3 — Usuário informa restrições ou intenção

Depois do contrato, o usuário pode conversar com o agente.

Exemplos de entrada:

* “Quero um cardápio mais competitivo.”
* “Evite carne bovina essa semana.”
* “Preciso reduzir custo sem perder qualidade.”
* “Use mais frango e legumes.”
* “Monte uma opção com prato principal e prato opcional.”
* “Não usar ingredientes com preço alto.”
* “Priorize fichas que já existem no banco.”

Essa parte aparece no áudio 4 como algo essencial: a IA precisa ler o que a pessoa escreveu de restrição e interagir com isso para gerar o melhor valor de cardápio.

### Etapa 4 — IA usa fichas técnicas e ingredientes

O sistema já mostra números fortes no dashboard: **3081 fichas técnicas** e **622 ingredientes**. Isso é um ativo enorme para o agente.

A IA deve usar esse banco para montar combinações viáveis. O raciocínio seria:

* buscar fichas compatíveis com o contrato;
* calcular custo das preparações;
* combinar prato principal, opção e acompanhamentos;
* evitar combinações ruins ou repetitivas;
* respeitar restrições;
* comparar alternativas;
* selecionar a composição mais competitiva.

### Etapa 5 — Módulo de precificação

O áudio 2 deixa claro que o módulo de precificação já está bom, mas precisa “rodar até o final e gerar”.

Esse é um dos pontos mais importantes do MVP.

O cardápio gerado precisa sair com:

* custo total;
* custo por preparação;
* custo por porção, se existir essa regra;
* comparação com custo máximo do contrato;
* margem de segurança;
* alerta quando ultrapassar o limite;
* justificativa da escolha.

Exemplo:

> Custo máximo permitido: R$ 10,00
> Custo estimado do cardápio: R$ 8,74
> Margem restante: R$ 1,26
> Status: competitivo

### Etapa 6 — Cardápio gerado e salvo

Na tela **Cardápios**, hoje aparece “Nenhum cardápio encontrado”. A ideia é que, ao final do fluxo, o cardápio apareça ali com status, data, contrato, custo e opção de revisão.

O cardápio salvo poderia conter:

* nome;
* contrato vinculado;
* data de geração;
* custo;
* status;
* pratos selecionados;
* justificativa da IA;
* restrições usadas;
* botão para editar/regenerar;
* botão para exportar.

## 4. O que é prioridade para “fechar a fatura”

Pelos quatro áudios, o escopo principal agora é:

1. **Fazer o gerador rodar até o final.**
2. **Selecionar contrato ou fazer upload de PDF.**
3. **IA ler e resumir o contrato.**
4. **Transformar contrato em regras de geração.**
5. **Usar fichas técnicas para montar cardápio.**
6. **Calcular preço/custo final.**
7. **Gerar cardápio competitivo.**
8. **Permitir que o usuário escreva restrições.**
9. **IA interagir com essas restrições.**
10. **Salvar e exibir o cardápio gerado.**

Esse é o MVP forte.

O produto não precisa ainda criar ficha técnica do zero nem buscar preço de mercado automaticamente. Isso fica para a evolução.

## 5. Versão 2.0

Os áudios trazem duas ideias grandes para uma próxima fase.

### 5.1. Criação de fichas técnicas com IA

Uma dor grande dos nutricionistas é criar as próprias fichas técnicas.

Hoje o sistema parte do princípio de que a empresa já tem banco de dados, mas muitos usuários podem não ter fichas bem estruturadas.

Na V2, o Menu.AI poderia ter um módulo onde o usuário diz:

> “Crie uma ficha técnica para frango grelhado com arroz integral e legumes.”

E a IA monta:

* nome da preparação;
* ingredientes;
* quantidades;
* modo de preparo;
* rendimento;
* porcionamento;
* categoria;
* custo estimado;
* observações;
* possíveis substituições.

Além disso, a IA poderia ajudar a modificar fichas existentes:

> “Troque carne bovina por frango.”
> “Reduza o custo dessa ficha.”
> “Adapte para 100 porções.”
> “Sugira uma versão mais barata.”
> “Crie uma opção vegetariana.”

Esse módulo pode virar uma das maiores forças do produto, porque resolve uma dor anterior à geração de cardápio: a falta de base técnica organizada.

### 5.2. Pesquisa de valor de mercado dos alimentos

Outra ideia de V2 é o agente pesquisar valores de mercado dos alimentos para atualizar os custos automaticamente.

Isso seria muito poderoso, principalmente em um ecossistema como o do Senai, porque permitiria ao sistema ficar mais próximo da realidade atual de preços.

A lógica seria:

* monitorar preços de ingredientes;
* sugerir atualização de custo;
* alertar quando um ingrediente ficou caro;
* sugerir substitutos;
* recalcular fichas técnicas;
* melhorar a geração de cardápios com dados recentes.

Exemplo:

> “O preço do tomate subiu. Recomendo substituir parte da salada por cenoura e repolho para manter o custo dentro do contrato.”

## 6. Análise dos prints da interface

A interface atual está limpa, bem organizada e já comunica uma estrutura de produto madura.

### Dashboard

O dashboard apresenta bem a proposta:

* CTA principal: **Gerar Cardápio**
* total de fichas técnicas;
* total de ingredientes;
* cardápios recentes;
* área de cardápios recentes.

Ponto positivo: o botão “Gerar Cardápio” está em destaque e direciona o usuário para a ação principal.

Ponto de atenção: o dashboard mostra **3081 fichas técnicas**, mas a tela de **Fichas Técnicas** mostra “Nenhuma ficha encontrada”. Pode ser filtro, paginação, API não carregando, tenant diferente ou estado vazio incorreto. Vale revisar porque isso pode passar sensação de inconsistência.

### Gerar Cardápio

A tela de geração está no caminho certo. Ela já tem uma lógica de chat com o agente e botões de entrada:

* selecionar contrato;
* upload PDF.

Essa tela deveria ser o coração do produto. É nela que a experiência conversacional precisa aparecer mais forte.

Sugestão de evolução:

* mostrar etapas do processo;
* exibir resumo do contrato após leitura;
* pedir restrições;
* mostrar alternativas de cardápio;
* permitir refinamento por conversa;
* confirmar antes de salvar.

### Cardápios

A tela está preparada para listagem e filtros, mas ainda vazia.

Depois do fluxo principal funcionar, essa tela deve virar uma área de gestão:

* cardápios gerados;
* status;
* custo;
* contrato vinculado;
* data;
* ações de visualizar, editar, exportar e regenerar.

### Fichas Técnicas

A tela tem busca, filtro por categoria e botão “Nova Ficha”.

Ela já está pronta para receber a evolução futura de criação de ficha técnica com IA.

Hoje ela pode servir como base operacional. Na V2, pode virar um módulo mais inteligente:

* criar ficha com IA;
* revisar ficha;
* recalcular custo;
* sugerir substituições;
* adaptar rendimento;
* validar ingredientes.

### Contratos

A tela de contratos já mostra contratos aprovados e ações por linha. Esse módulo é essencial porque o contrato é a fonte das regras.

A IA precisa conseguir transformar cada contrato em uma “camada de regras” para o gerador.

O contrato não deve ser só um arquivo armazenado. Ele deve virar inteligência operacional.

## 7. Estrutura ideal do produto

A arquitetura conceitual do Menu.AI pode ser organizada assim:

### Camada 1 — Dados

* contratos;
* fichas técnicas;
* ingredientes;
* preços;
* categorias;
* restrições;
* histórico de cardápios.

### Camada 2 — Interpretação

* leitura de contrato;
* resumo;
* extração de regras;
* identificação de custo máximo;
* interpretação de restrições livres escritas pelo usuário.

### Camada 3 — Geração

* busca de fichas compatíveis;
* combinação de pratos;
* cálculo de custo;
* comparação entre alternativas;
* escolha do cardápio mais competitivo.

### Camada 4 — Conversa

* usuário conversa com o agente;
* IA explica escolhas;
* IA sugere ajustes;
* usuário pede mudanças;
* IA regenera ou adapta.

### Camada 5 — Gestão

* salvar cardápio;
* visualizar histórico;
* exportar;
* editar;
* aprovar;
* reutilizar.

## 8. Frase de posicionamento

Uma forma clara de explicar o produto:

> **Menu.AI é um agente inteligente que lê contratos, interpreta regras alimentares, usa fichas técnicas e preços de ingredientes para gerar cardápios competitivos, explicáveis e adaptáveis por conversa.**

Outra versão mais comercial:

> **O Menu.AI ajuda restaurantes, nutricionistas e operações de alimentação a montar cardápios com melhor custo, respeitando contratos, restrições e fichas técnicas existentes.**

## 9. Roadmap sugerido

### Agora — MVP para fechar

* Fluxo completo de geração.
* Leitura e resumo de contrato.
* Uso de fichas técnicas.
* Cálculo de preço.
* Restrições por texto.
* Geração do cardápio final.
* Salvamento em “Cardápios”.

### Depois — Produto mais humano

* Chat mais inteligente com memória do processo.
* IA explicando decisões.
* Comparação entre 2 ou 3 opções de cardápio.
* Ajustes por conversa.
* Sugestões de economia.

### V2 — Expansão forte

* criação de ficha técnica com IA;
* edição de ficha técnica com IA;
* sugestão de substituições;
* pesquisa de preço de mercado;
* atualização automática de custos;
* recomendações baseadas em variação de preço;
* inteligência específica para ecossistema Senai.

## 10. Resumo final da ideia dos 4 áudios

O Menu.AI deve ser um agente que pega contrato, fichas técnicas e ingredientes e transforma isso em um cardápio competitivo com preço calculado. A primeira entrega precisa fazer esse fluxo rodar de ponta a ponta: ler contrato, entender regras, aceitar restrições do usuário, montar o cardápio, calcular custo e salvar o resultado.

A evolução natural é tornar o agente mais conversacional, permitindo que o usuário troque ideia com a IA sobre o melhor cardápio. Depois, o produto pode crescer para criação de fichas técnicas com IA e atualização automática de preços de mercado.

A essência é: **não é só um gerador de cardápios; é um copiloto operacional para decisões de alimentação, custo e contrato.**
