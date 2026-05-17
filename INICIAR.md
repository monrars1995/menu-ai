# Menu.AI v3.5.6 — Como iniciar

## Stack suportada

| Perfil | Quando usar | `DATABASE_URL` | Migrações |
|--------|-------------|----------------|-----------|
| **Docker Desktop** | Desenvolvimento local e operação suportada | `postgresql+psycopg2://menuai:menuai123@postgres:5432/menuai_db` dentro dos containers | `alembic upgrade head` no startup da API |
| **Supabase** | Produção, staging ou dev cloud | `SUPABASE_DB_URL` com conexão Postgres do projeto | `alembic upgrade head` contra o projeto Supabase |

**`POST /api/gerar`:** o servidor preenche `empresa_id` a partir do JWT se o corpo do pedido o omitir. Com `DEBUG=true` e `DEMO_GERAR_SEM_AUTH=true`, sem token usa-se `DEFAULT_EMPRESA_ID`.

**Verificação rápida (CLI):** com o venv ativo, na raiz do repositório: `python3 scripts/verify_stack.py` — valida PostgreSQL, contagens básicas, catálogo LLM e tenta `GET /api/health`. Smoke do fluxo de geração: `DEBUG=true DEMO_GERAR_SEM_AUTH=true python3 scripts/smoke_flow.py`.

## Pré-requisitos

- Docker instalado e rodando
- Chave de API de pelo menos um provedor LLM: OpenAI, Gemini ou OpenRouter

---

## Passo a passo

### 1. Configurar a chave LLM no `.env`

Abra o arquivo `.env` e configure pelo menos um provedor LLM:

```bash
OPENAI_API_KEY=sk-SUA_CHAVE_OPENAI
GEMINI_API_KEY=SUA_CHAVE_GEMINI
# opcional
OPENROUTER_API_KEY=sk-or-v1-SUA_CHAVE_OPENROUTER
MENUAI_DEFAULT_LLM_MODEL=openai-gpt-5.5
```

Catálogo inicial da aplicação:
- `openai-gpt-5.5` -> `openai/gpt-5.5`
- `gemini-3.1-pro-preview` -> `gemini/gemini-3.1-pro-preview`
- `gemini-3-flash-preview` -> `gemini/gemini-3-flash-preview`
- `gemini-3.1-flash-lite` -> `gemini/gemini-3.1-flash-lite`
- `queen-3.6` -> `qwen/qwen3.6-plus`
- `glm-5-1` -> `z-ai/glm-5.1`
- `kimi-k2.5` -> `moonshotai/kimi-k2.5`

Se for usar Supabase:

```bash
SUPABASE_DB_URL=postgresql://postgres.[PROJETO]:[SENHA]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require
SUPABASE_URL=https://[PROJETO].supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SECRET_KEY=sb_secret_...
EMBEDDING_API_KEY=...
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_DIMENSION=1536
EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
```

Para ORM e migrações, prefira direct connection ou Supavisor session mode. A documentação do Supabase diferencia isso de transaction mode.

### 2. Rodar o setup completo

```bash
chmod +x setup.sh
./setup.sh
```

O script faz automaticamente:
- Sobe o PostgreSQL via Docker
- Builda a API principal
- Builda o admin
- Inicia a stack completa

---

## Inicializações seguintes

```bash
docker compose up -d --build
```

---

## Acessos

| Serviço | URL |
|---------|-----|
| API | http://localhost:8000 |
| Admin | http://localhost:8001 |
| Documentação Swagger | http://localhost:8000/api/docs |
| Documentação Admin | http://localhost:8001/api/docs |
| Health check | http://localhost:8000/api/health |
| pgAdmin | http://localhost:5050 |

**pgAdmin login:** `admin@menuai.dev` / `admin123`

---

## Primeiro acesso à API

```bash
curl -X POST http://localhost:8000/api/auth/registro \
  -H "Content-Type: application/json" \
  -d '{
    "empresa_nome": "Minha Empresa",
    "nome": "Carlos",
    "email": "carlos@empresa.com",
    "senha": "senha123",
    "role": "admin"
  }'
```

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "carlos@empresa.com", "senha": "senha123"}'
```

---

## Comandos úteis Docker

```bash
docker compose ps
docker compose logs -f postgres
docker compose down
docker compose down -v
```

## Segurança e operação

- Fluxo oficial de desenvolvimento: `docker compose up -d --build`
- Logs: `docker compose logs -f app` e `docker compose logs -f admin`
- `SECRET_KEY` forte obrigatório fora de `DEBUG`
- `CORS_ORIGINS` explícita em deploy
- `ALLOW_OPEN_REGISTRO=true` apenas quando necessário
- A UI autenticada envia `Authorization: Bearer` em `gerar`/`upload`
- O seletor `Modelo LLM` consome `GET /api/llm-models`, persiste a escolha no navegador e envia o id interno em `POST /api/gerar`

## Migrações

```bash
docker compose exec app python -m alembic upgrade head
docker compose exec app python seed_data.py
docker compose exec app alembic history
docker compose exec app alembic revision --autogenerate -m "descricao da mudanca"
```

## UI (`templates/index.html`)

- O seletor de modelo usa OpenAI, Gemini e OpenRouter quando as respectivas chaves estão configuradas.
- O modelo selecionado fica persistido no navegador.
- Header e fluxo de geração usam o mesmo catálogo exposto pela API.

## Orquestração

Se no futuro for necessário persistir o estado de cada nó, retomar jobs ou aprovação humana a meio do pipeline, pode-se envolver a mesma lógica com LangGraph. Hoje o fluxo é o runner em Python + LiteLLM sobre a OpenRouter.

---

## Contato

- Instagram: @monrars
- Site: goldneuron.io
- GitHub: @monrars1995
