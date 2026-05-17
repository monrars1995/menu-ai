# Menu.AI v3.5.6

Backend, admin e banco de dados empacotados para Docker Desktop com FastAPI, PostgreSQL, OpenAI, Gemini e OpenRouter.

## Stack suportada

- API principal: FastAPI em container
- Admin: FastAPI em container
- Banco: PostgreSQL em container
- Banco cloud suportado: Supabase Postgres
- Vetor: Supabase pgvector
- LLM gateway: OpenAI, Gemini e OpenRouter via LiteLLM
- Modelos iniciais:
  - `openai-gpt-5.5` -> `openai/gpt-5.5`
  - `gemini-3.1-pro-preview` -> `gemini/gemini-3.1-pro-preview`
  - `gemini-3-flash-preview` -> `gemini/gemini-3-flash-preview`
  - `gemini-3.1-flash-lite` -> `gemini/gemini-3.1-flash-lite`
  - `queen-3.6` -> `qwen/qwen3.6-plus`
  - `glm-5-1` -> `z-ai/glm-5.1`
  - `kimi-k2.5` -> `moonshotai/kimi-k2.5`

Padrão de geração: OpenAI direto (`openai-gpt-5.5`) como modelo principal; Gemini direto e OpenRouter permanecem ativos no catálogo conforme chaves configuradas.

## Início rápido

1. Configure `.env` a partir de `.env.example`.
2. Defina pelo menos uma chave LLM: `OPENAI_API_KEY`, `GEMINI_API_KEY`/`GOOGLE_API_KEY` ou `OPENROUTER_API_KEY`.
3. Se for usar Supabase, configure `SUPABASE_DB_URL` e as variáveis de embeddings.
4. Execute `./setup.sh` ou `docker compose up -d --build`.
5. Abra `http://localhost:8000` e `http://localhost:8001`.

## Supabase + vetor

- `SUPABASE_DB_URL`: conexão Postgres do projeto Supabase
- `SUPABASE_URL`: `https://seu-projeto.supabase.co`
- `SUPABASE_PUBLISHABLE_KEY`: chave cliente pública (`sb_publishable_...`)
- `SUPABASE_SECRET_KEY`: chave de backend (`sb_secret_...`) quando precisar chamar APIs privilegiadas do Supabase
- `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `EMBEDDING_BASE_URL`: geração de embeddings
- Endpoints principais:
  - `GET /api/knowledge/stats`
  - `POST /api/knowledge/reindex`
  - `POST /api/knowledge/search`
- Admin:
  - `GET /api/admin/knowledge/stats`
  - `POST /api/admin/knowledge/reindex`
  - `POST /api/admin/knowledge/search`

Detalhes operacionais: [INICIAR.md](INICIAR.md) e [DOCUMENTACAO_PROJETO.md](DOCUMENTACAO_PROJETO.md).

## Contato

- Instagram: @monrars
- Site: goldneuron.io
- GitHub: @monrars1995
