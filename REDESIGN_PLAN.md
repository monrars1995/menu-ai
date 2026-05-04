# Plano: Redesign Apple + Supabase Auth

## Estado Atual

### Frontend
- **`templates/index.html`**: SPA com ~1500+ linhas, Tailwind CDN + CSS custom Apple-style já parcial
- Layout 3-colunas: inputs (esquerda) | swarm/resultado (centro) | agentes (direita)
- Já usa cores Apple (Action Blue, parchment, SF Pro-like) mas inconsistente
- **Sem tela de login/register** — auth via localStorage + JWT do backend FastAPI
- Design já bom, mas falta polimento Apple (hero tiles, alternating surfaces, product photography feel)

### Backend Auth
- **JWT próprio** em `routers/auth.py` — login/registro/me com bcrypt + HS256
- Usuários persistidos em `Usuario` (SQLAlchemy) com `senha_hash` no Supabase
- Token stored em `localStorage` como `menuai_access_token`
- Demo mode: `DEMO_GERAR_SEM_AUTH=true` permite uso sem login

### Supabase
- **Conn pooler**: `aws-1-us-east-1.pooler.supabase.com:5432` (IPv4 OK ✅)
- **Tables**: Empresas, Usuarios, FichasTecnicas, Ingredientes, JobAgente, Cardapio, Contratos, Knowledge (pgvector)
- ✅ MCP Supabase configurado em `opencode.json`
- ✅ Agent skills instaladas

---

## FASE 1: Supabase Auth (sem quebrar funcionalidade)

### 1.1 Backend — Supabase Auth Adapter
**Arquivo novo**: `routers/auth_supabase.py`

- Endpoint `POST /api/auth/login` → valida com Supabase Auth (`/auth/v1/token`)
- Endpoint `POST /api/auth/registro` → cria com Supabase Auth (`/auth/v1/signup`)
- Endpoint `GET /api/auth/me` → valida JWT Supabase e busca dados no `usuarios` table
- **Preservar backwards compat**: tokens JWT existentes continuam funcionando (fallback)
- **Migrate**: `Usuario.senha_hash` pode ficar vazio — auth via Supabase
- Supabase envia JWT no mesmo formato (HS256), então `decodificar_token()` funciona com a mesma key

### 1.2 Frontend — Supabase JS SDK
**File**: `templates/index.html` — adicionar Supabase client no `<script>`

```html
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
```

- `login(email, senha)` → `supabase.auth.signInWithPassword()`
- `register(email, senha, nome)` → `supabase.auth.signUp()`
- Token vai pra `localStorage` como antes (Supabase compatível)
- `supabase.auth.onAuthStateChange()` para auto-refresh

### 1.3 UI — Login/Register Modals (Apple-style)
- Modal overlay com fundo escuro translúcido (Apple style: `rgba(0,0,0,0.4)`)
- Form centralizado com card branco, `rounded-md` (11px), sombras mínimas
- Inputs: pill-shaped (`border-radius: 9999px`), 44px high
- Botão: Action Blue pill, `transform: scale(0.95)` on active
- Link "Registrar" / "Já tem conta?" em blue text-link style
- **Sem navegação extra** — modal overlay, não página separada

---

## FASE 2: Redesign Apple DESIGN.md

### 2.1 Global Structure
- **Hero tile**: Edge-to-edge full-bleed com headline "Menu.AI" + tagline + CTA pill
- **Sub-nav**: Frosted glass sticky bar com `backdrop-filter: saturate(180%) blur(20px)`
- **Alternating surfaces**: Light (white) → Dark (#272729) → Parchment (#f5f5f7)
- **Typography**: Inter substituting SF Pro com `-0.01em` letter-spacing tight
- **Zero decorative gradients** — atmosfera via whitespace e tipografia

### 2.2 Layout Redesign
**Current**: 3-colunas fixas (input | swarm | agentes)
**New**: Single-column vertical stack de product tiles

| Tile | Surface | Content |
|------|---------|---------|
| Hero | White (#fff) | Headline "Menu.AI", tagline, LLM model selector |
| Pedido | Parchment (#f5f5f7) | Contrato upload, dias, custo, restrições → Gerar CTA |
| Pipeline | Dark (#272729) | Pipeline pills + progress bar + swarm cards (white on dark) |
| Resultado | White (#fff) | Cardápio table + download buttons + audit panels |

### 2.3 Component Mapping (DESIGN-apple.md → Menu.AI)
| Apple Component | Menu.AI Equivalent |
|----------------|-------------------|
| `button-primary` | "Gerar cardápio", "Baixar Excel" (blue pill) |
| `button-secondary-pill` | "Nova geração", "TXT" (ghost pill with blue border) |
| `product-tile-light` | Estado idle hero, resultado cardápio |
| `product-tile-dark` | Pipeline/swarm state (agentes rodando) |
| `search-input` | Upload drop zone + inputs (all pill-shaped) |
| `sub-nav-frosted` | Sticky progress bar durante geração |
| `store-utility-card` | Agent cards (com `rounded-lg: 18px`) |
| `configurator-option-chip` | LLM model selector (pill chips) |
| `global-nav` | Header com logo + status + base info |

### 2.4 States & Transitions
- **Idle**: Hero tile → foto/ilustração + headline (Apple product-page feel)
- **Running**: Smooth scroll para pipeline tile; sub-nav sticky com progresso
- **Result**: Fade-in do tile resultado; audit panels em cards com `rounded-lg`
- **Error**: Dark tile com headline + message (Apple error state style)

### 2.5 Responsive
- Desktop: 3-colunas mantém (sidebar | centro | swarm)
- Tablet (834px): 2-colunas (sidebar colapsada | centro + swarm)
- Phone (640px): Single column stack, tiles edge-to-edge

---

## FASE 3: Integração Completa

### 3.1 Docker + Supabase
- `docker-compose.yml` já OK (sem postgres local, usa pooler)
- Build com IPv4 fix já funcionando
- `docker_app_start.sh` detecta migrations existentes (não recria)

### 3.2 Test Plan
1. `GET /api/health` → ok, db conectado via pooler
2. `POST /api/auth/login` → Supabase auth funciona
3. Upload contrato + gerar cardápio → pipeline completo OK
4. Redesign visual → todos states (idle, running, result, error) OK
5. Responsivo → desktop/tablet/phone OK

---

## Order of Implementation
1. **Supabase Auth** (backend + frontend) — 2-3 hours
2. **Login/Register Modals** (Apple style) — 1-2 hours  
3. **Global redesign** (hero, tiles, alternating surfaces) — 3-4 hours
4. **Component polish** (buttons, cards, typography) — 2-3 hours
5. **Responsive + final validation** — 1-2 hours

**Total**: ~10-14 hours de trabalho
