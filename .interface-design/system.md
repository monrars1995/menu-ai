# Menu.AI — Interface system

**Direção:** Apple HIG + ficheiro de design do projecto (DESIGN-apple.md) — clareza, **Action Blue** `#0066cc` como único acento de interacção, canvas **parchment** `#f5f5f7`, cromo com vidro leve; **sem** sombras de cartão no cromo; **sem** gradientes decorativos. Tipografia: **Inter** + *fallback* sistema Apple.

## Domínio (5+)

- Cozinha e contrato de refeição, custo por prato, conformidade, cardápio cíclico, rastreio **identificado → cruzado → resultado**.

## Mundo de cor (monocromia + acento)

- Tinta: `#1d1d1f` e gris neutros; superfícies branco / pearl / parchment; **um** azul de acção (`--color-primary`).
- Estados sem “paleta semântica” (sem verde/vermelho de fundo no cromo); relevo por **borda** e hierarquia de texto (4 níveis).

## Assinatura (produto)

- **Auditoria em 3 colunas** durante o processamento.
- **Sidebar “Enxame de agentes”** em lista ordenada (ordem fixa: contrato → export), **ícones Lucide** sem caixa (sem fundo nem borda no alinhador `.agent-ic-wrap`), cor de traço legível (`--color-ink` / primário por estado), nome + **função** (linha terciária), estado em tempo real; cabeçalho de secção com ícone `network` e título.
- **Lucide** (um só conjunto) via UMD; `refreshIcons()` após inserções dinâmicas.

## Profundidade (um sistema)

- **Bordas** + vidro; inputs levemente “inset” (fundo canvas vs parchment); sombras mínimas só onde o spec exige (evitar cromo pesado).

## Tokens (CSS) — ficheiro principal

- Texto: `--text-primary` / `--text-dim` / `--text-muted` alinhados a `--color-ink*`.
- Bordas: `--color-hairline`, `rgba(0,0,0,0.08)`.
- Raio: `--radius-sm` … `--radius-pill`.
- Acento: `--color-primary` / `--color-primary-focus`.

## Spacing

- Grelha **4px**; secções 16–24; cartões de agente `gap` 0.5rem na lista.

## Padrões de componente

- `btn-primary` / `btn-secondary` com `icon-inline` quando houver ícone; ícones em branco sobre primário.
- `swarm-side-head` + `swarm-ordered` + `agent-role` na coluna direita.
- `label-section` (uppercase) para grupos no painel esquerdo: **Entrada** vs **Parâmetros e restrições**.

## Não fazer

- Múltiplos acentos de cor; sombras fortes; sidebar com cor sólida diferente do canvas; emojis no UI (substituir por Lucide).

## Última actualização

- 2026-04-29: documento inicial + refactor visual.
- 2026-04-29: alinhamento DESIGN-apple (Inter, #0066cc, Lucide, coluna enxame com lista, wells e funções per agente).
- 2026-04-29: coluna enxame minimal — sem legenda/parágrafo de cabeçalho, sem coluna de índice 01–08; mantém `agent-role` e ARIA.
- 2026-04-29: ícones do enxame sem poço (fundo/borda removidos); traço com contraste; correcção do bloco CSS `.btn-secondary` órfão.
