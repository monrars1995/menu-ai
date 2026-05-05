# Design: Chat Conversacional Premium (Evolução HITL e Persistência)

**Data:** 2026-05-05
**Status:** Aprovado via Brainstorming

## 1. Resumo do Entendimento (Understanding Lock)

* **O que será construído:** Uma evolução do Chat de Geração de Cardápios, adicionando persistência em banco de dados, HITL híbrido (formulário estruturado + texto livre via IA) e streaming do raciocínio da LLM em tempo real.
* **Por que existe:** Para garantir confiabilidade (não perder dados se a aba for fechada) e entregar uma experiência "mágica" corporativa onde o usuário sente que a IA está trabalhando ao vivo.
* **Para quem é:** Clientes B2B/corporativos (gestores de refeitórios, nutricionistas).
* **Restrições:** Persistência no banco (Sessões e Mensagens); Edição via JSON ou NLP.
* **Não-Objetivo:** Manter a conversa como "caixa preta" ou apenas como um formulário estático glorificado.

## 2. Premissas (Assumptions)

1. Tabelas de sessão (`sessoes_chat` e `mensagens_chat`) vinculadas à empresa/usuário.
2. O parser de SSE atual suportará emissões do tipo "thought/raciocínio".
3. HITL híbrido exige um agente intermediário menor (LiteLLM Tools) apenas para interpretar texto livre e aplicá-lo ao JSON de `ContratoAnalise`.

## 3. Decision Log

1. **Persistência de Estado:** Decidido pelo uso de Banco de Dados (`sessoes_chat`) ao invés de `localStorage`.
   * *Alternativas consideradas:* LocalStorage (frágil para troca de devices) e LangGraph (YAGNI, excesso de complexidade).
2. **Evolução do HITL:** Abordagem Híbrida (A + B).
   * *Por que:* Atende a quem quer rapidez via botões da UI (Formulário estruturado) e a quem prefere usar NLP livre ("tire todo o camarão").
3. **UX de Processamento:** Transparência Total ("Estilo Cursor").
   * *Por que:* Demonstra o raciocínio complexo por trás do pipeline de 7 etapas da API, elevando a percepção de valor do produto.

## 4. Design Técnico Proposto

### 4.1 Arquitetura de Banco de Dados

Criação de novas tabelas via Alembic:

* **`sessoes_chat`**
  * `id` (UUID, PK)
  * `empresa_id` (FK), `usuario_id` (FK)
  * `job_id` (FK para `jobs_agente`)
  * `contrato_id` (FK)
  * `status` (Enum)

* **`mensagens_chat`**
  * `id` (UUID, PK)
  * `sessao_id` (FK)
  * `role` (user, assistant, system)
  * `tipo` (text, analysis_card, thought, result_card)
  * `content` (texto)
  * `meta_dados` (JSONB - para guardar o card do HITL ou configurações estruturadas)

### 4.2 HITL Híbrido (`POST /api/chat/{sessao_id}/refinar_analise`)

Endpoint misto para refinamento antes da geração final:
- **Payload com JSON Estruturado:** O usuário editou botões/campos na UI. Backend salva diretamente no `ContratoAnalise`.
- **Payload com Texto Livre:** Backend aciona um modelo rápido para entender o texto do usuário, alterar o objeto JSON em memória e salvar no banco, retornando a `ContratoAnalise` atualizada para o chat.
- **Fallback:** Em caso de erro do LLM no modo texto, retorna aviso educado pedindo para o usuário usar a Edição Manual via botão.

### 4.3 Streaming de Transparência (Reasoning)

- **Backend:** Adicionar callback em `pipeline/litellm_runner.py` que capte passos intermediários do LangChain/LiteLLM.
- **SSE:** Enviar blocos `event: thought \n data: "Balanceando calorias..."`.
- **Frontend:** `MessageBubble.tsx` exibe os `thoughts` acumulados em um container retrátil, simulando um log de terminal amigável.
