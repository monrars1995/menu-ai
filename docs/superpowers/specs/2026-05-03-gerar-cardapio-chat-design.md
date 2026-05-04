# Design: Pagina Gerar Cardapio — Interface Chat

**Data:** 2026-05-03
**Status:** Em revisao

## Contexto

A pagina `/gerar` atual usa formularios laterais + painel de pipeline. O objetivo e transforma-la em uma interface conversacional estilo ChatGPT onde o agente guia o usuario passo a passo na criacao do cardapio.

## Nao-negociaveis

- **Sidebar** permanece em todas as paginas (route group `(app)`)
- **Contratos com analise** permanece inalterado (`/contratos`)
- **Export XLSX/CSV/PDF/Imprimir** permanece no cardapio detail
- **Gramatura vs fichas** permanece no backend
- **Modelo LLM** nao aparece na UI — definido no admin, aplicado globalmente

## Fluxo Conversacional

### Fase 1 — Boas-vindas + Contrato

**Agente:** "Ola! Vou te ajudar a gerar um cardapio inteligente. Comece selecionando um contrato ou fazendo upload do PDF."

- **Botao "Selecionar Contrato"** — dropdown com contratos existentes da empresa
- **Botao "Upload PDF"** — file picker para .pdf/.xlsx/.xls
- **Campo de texto livre** — usuario pode digitar qualquer coisa

### Fase 2 — Analise do Contrato (automatica)

Apos selecionar/upload, chama `GET /api/contratos/{id}/analise` automaticamente.

**Agente:** "Analisei o contrato. Aqui esta o que entendi:"

- Card com: refeicoes/dia, gramaturas por categoria, proibicoes, dietas especiais, alergenos
- Botao "Ver detalhes completos" expande todas as secoes
- Se sem analise: "O contrato ainda nao foi analisado. Voce pode gerar assim mesmo ou fazer upload do PDF na pagina Contratos."

### Fase 3 — Configuracao Guiada (perguntas sequenciais)

O agente faz perguntas uma por vez, com input na base da conversa:

1. **Dias:** "Para quantos dias deseja o cardapio?"
   - Input numerico com default 5, range 1-30
2. **Refeicoes:** "Quais refeicoes deseja incluir?"
   - Toggle grid: Cafe da Manha, Almoco, Lanche da Tarde, Jantar, Lanche da Manha, Ceia
   - Defaults: Almoco, Jantar
3. **Custo Alvo:** "Qual o custo alvo diario? (opcional)"
   - Input monetario, pode pular
4. **Restricoes:** "Ha alguma restricao adicional?"
   - Textarea, pode pular

### Fase 4 — Confirmacao

**Agente:** "Pronto! Confira os parametros antes de gerar:"

- Resumo: X dias, refeicoes selecionadas, custo alvo, restricoes
- **Botao "Gerar Cardapio"** (primario)
- **Botao "Ajustar"** — volta para a pergunta desejada

### Fase 5 — Geracao com SSE

**Agente:** "Gerando cardapio..."

- Pipeline steps com icones (✓ feito, → em andamento, ○ pendente)
- Painel "Pensamento" expande mostrando raciocinio em tempo real
- Se erro: mensagem com botao "Tentar novamente"

### Fase 6 — Resultado

**Agente:** "Cardapio gerado com sucesso!"

- Resumo: nome, dias, custo medio
- Botoes: Baixar XLSX, Baixar CSV, Baixar PDF, Ver Cardapio Completo

## Arquitetura

### Componentes novos em `menu/src/components/chat/`

| Componente | Responsabilidade |
|------------|-----------------|
| `ChatContainer` | Layout centralizado, scroll, avatar agente |
| `MessageBubble` | Renderiza tipo de mensagem (texto, analise, pipeline, resumo, export) |
| `MessageInput` | Campo de texto + botoes contextuais (upload, selecionar, enviar) |
| `ChatStep` | Gerencia estado de cada fase do wizard conversacional |

### Estado do Chat (hook)

`useChatGenerator()` — hook customizado que gerencia:

```
interface ChatState {
  phase: 'welcome' | 'analysis' | 'config' | 'confirm' | 'generating' | 'result' | 'error';
  contratoId: string | null;
  contratoAnalise: ContratoAnalise | null;
  dias: number;
  refeicoes: string[];
  custoAlvo: string;
  restricoes: string;
  messages: ChatMessage[];
  jobId: string | null;
  pipelineStep: number;
  pensamento: string;
}
```

### Fluxo de dados

```
Usuario → MessageInput → ChatState → api.contratos.analise() → ContractAnalysisCard
                                      → api.gerar.start() → SSE stream → PipelineProgress
                                      → api.cardapios.download() → ExportButtons
```

### Reutilizacao

- **`MealSelector`** — reutilizado como componente inline no chat (Fase 3, refeicoes)
- **`InlineLoader`**, **`Spinner`** — reutilizados para loading
- **ContratoAnalise type** — ja existe em `types.ts`
- **API methods** — ja existem em `api.ts`

## Layout Visual

```
┌─ Sidebar ─┬─────────────────────────────────────────────┐
│           │                                             │
│           │  Chat area (centralizado, max-width 2xl)    │
│           │                                             │
│           │  [Bubble agente: Ola! ...]                  │
│           │  [Bubble agente: Contrato.pdf]              │
│           │  [Card: Analise do contrato]                │
│           │  [Bubble agente: Quantos dias?]             │
│           │  [Input numerico: 5]                        │
│           │  ...                                        │
│           │                                             │
│           │ ──────────────────────────────────────────  │
│           │ [Upload PDF] [Selecionar] [Input] [Enviar]  │
│           │                                             │
└───────────┴─────────────────────────────────────────────┘
```

## Arquivos a modificar

| Arquivo | Acao |
|---------|------|
| `menu/src/app/(app)/gerar/page.tsx` | **Reescrito** — interface chat |
| `menu/src/components/chat/ChatContainer.tsx` | Novo |
| `menu/src/components/chat/MessageBubble.tsx` | Novo |
| `menu/src/components/chat/MessageInput.tsx` | Novo |
| `menu/src/components/chat/useChatGenerator.ts` | Novo (hook) |

## Arquivos inalterados

- `(app)/layout.tsx` — sidebar
- `contratos/page.tsx` — pagina contratos
- `cardapios/[id]/page.tsx` — export e aprovacao
- `api.ts` — metodos ja existem
- `types.ts` — tipos ja existem
- Backend — endpoints ja existem
