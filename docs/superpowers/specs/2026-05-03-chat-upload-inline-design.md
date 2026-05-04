# Design: Upload Inline no Chat de Geração

**Data:** 2026-05-03
**Status:** Aprovado

## Contexto

O chat `/gerar` hoje redireciona o usuário para a página `/contratos` quando precisa fazer upload de um PDF. O streaming SSE do pipeline já funciona (steps 1-7, progresso, pensamentos). Este design adiciona upload inline no chat, mantendo o streaming existente.

## 1. Backend — novo endpoint `POST /api/gerar/upload`

**Entrada:** `multipart/form-data`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `file` | arquivo | sim | PDF/XLSX/XLS do contrato |
| `dias` | int | sim | 1–30 |
| `refeicoes` | JSON string array | sim | `["almoco","jantar"]` |
| `target_custo_total` | float | não | Custo alvo em R$ |
| `restricoes_usuario` | string | não | Texto livre |
| `nome_cardapio` | string | não | Nome customizado |
| `llm_model` | string | não | Slug do modelo LLM |

**Fluxo interno:**

1. Valida extensão (`.pdf`, `.xlsx`, `.xls`) — rejeita com 400
2. Lê conteúdo do arquivo, calcula `SHA256(content)`
3. Busca contrato existente na DB onde `arquivo_hash == hash` OU `arquivo_path` contém o mesmo nome
4. **Se encontrou:** reusa `contrato_id`, carrega `ContratoAnalise` existente
5. **Se não encontrou:**
   - Salva em `data/uploads/contratos/{hash}{ext}`
   - Cria registro `Contrato` (`nome` = filename sem extensão, `arquivo_path`, `arquivo_hash`, `empresa_id` do JWT)
   - Dispara análise síncrona do agente (mesma lógica do admin)
   - Salva resultado em `contrato_analise`
6. Dispara pipeline de geração em background (mesma lógica do `POST /api/gerar`)
7. Retorna JSON:

```json
{
  "job_id": "abc12345",
  "contrato_id": "uuid-here",
  "contrato_nome": "Contrato Exemplo",
  "novo_contrato": true,
  "analise": { ... } | null
}
```

**Erros:**
- `400` — formato inválido, campo obrigatório ausente
- `500` — erro interno (análise falhou, DB indisponível)

**Nota:** O endpoint original `POST /api/gerar` (JSON body) permanece inalterado para seleção de contratos existentes.

## 2. Frontend — Upload inline no chat

### 2a. Botão "Upload PDF" (MessageInput)

- Na fase `welcome`, o botão "Upload PDF" abre `<input type="file" hidden />`
- Ao selecionar arquivo, dispara `handleInlineUpload(file)` no hook

### 2b. Drag-and-drop (ChatContainer)

- `ChatContainer` escuta `onDragOver` + `onDrop`
- Ao arrastar sobre a área do chat, mostra overlay: fundo `bg-white/80 backdrop-blur-sm`, texto central "Solte o PDF do contrato aqui", ícone `Upload`
- Ao soltar, valida `.pdf/.xlsx/.xls` e dispara upload

### 2c. Fluxo no `useChatGenerator`

Novas ações no hook:

```typescript
handleInlineUpload(file: File): void
```

1. Adiciona bolha de usuário: `"Enviando: {filename}"`
2. Muda phase para `"uploading"` (nova fase transitória)
3. Faz `POST /api/gerar/upload` com FormData
4. Ao receber resposta:
   - Atualiza `contratoId`, `contratoAnalise` no state
   - Se `novo_contrato`: bolha agente `"Contrato cadastrado! Analisando..."` + AnalysisCard
   - Se existente: bolha agente `"Contrato '{nome}' encontrado."` + AnalysisCard
   - Transiciona para `config-days`
5. Em caso de erro: bolha vermelha no chat com a mensagem

**Nova fase:** `"uploading"` — durante upload, o MessageInput mostra um inline loader e bloqueia interação.

### 2d. Mudanças nos componentes

**`MessageInput.tsx`:**
- Fase `welcome`: botão "Upload PDF" conecta a `onInlineUpload` (nova prop)
- Nova fase `uploading`: mostra `InlineLoader` com texto "Enviando arquivo..."

**`ChatContainer.tsx`:**
- Adiciona handlers `onDragOver`, `onDrop`, `onDragEnter`, `onDragLeave`
- Novo estado `dragOver: boolean`
- Overlay visual quando `dragOver === true`
- Prop `onFileDrop?: (file: File) => void`

**`MessageBubble.tsx`:**
- Tipo `uploading` — bolha do agente com spinner + "Enviando {filename}..."

### 2e. Estados e tipos novos

```typescript
// Nova fase
type ChatPhase = ... | "uploading";

// Novo tipo de mensagem
type MessageType = ... | "uploading";
```

## 3. Banco de dados — coluna `arquivo_hash`

Se não existir, adicionar coluna `arquivo_hash` (VARCHAR(64), nullable) na tabela `contratos` para deduplicação por hash do arquivo.

Migração Alembic simples.

## 4. Fluxo completo (happy path)

```
Usuário clica "Upload PDF" ou arrasta arquivo
  → Bubbles: "Enviando: contrato.pdf" (user) + spinner (agent)
  → POST /api/gerar/upload (multipart)
  ← { contrato_id, contrato_nome, novo_contrato, analise }
  → Bubbles: "Contrato cadastrado!" + AnalysisCard
  → Phase: config-days → "Para quantos dias?"
  → Usuário configura dias/refeições/custo/restrições
  → Confirm card → "Gerar Cardápio"
  → SSE stream → Pipeline steps 1-7 com progresso
  → Result card → "Cardápio gerado!" + download buttons
```

## 5. O que NÃO muda

- O pipeline de 7 etapas permanece idêntico
- O endpoint `POST /api/gerar` (JSON) continua funcionando
- O SSE `/api/stream/{job_id}` continua idêntico
- A página `/contratos` continua funcionando (CRUD + upload)
- O streaming de progresso no chat já funciona — sem alterações
