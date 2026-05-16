---
name: db-query
description: "Query and manage the Menu.AI PostgreSQL database. Covers SQLAlchemy models, Alembic migrations, seed data, and common queries. Use when inspecting data, debugging DB issues, or writing new queries."
---

# DB Query Skill

## When to Use

- Inspecting database contents
- Debugging data issues
- Writing new queries or migrations
- Managing seed data
- Checking multi-tenant isolation

## Connection

- **ORM**: SQLAlchemy 2.0 declarative
- **Connection**: `database/connection.py` → reads `DATABASE_URL` from `.env`
- **Migrations**: Alembic (`alembic/versions/`)
- **Dev mode**: SQLite fallback if `DATABASE_URL` empty

## Models (database/models.py)

| Model | Table | Key Fields |
|-------|-------|------------|
| `Empresa` | `empresas` | id, nome, cnpj, config |
| `Usuario` | `usuarios` | id, empresa_id, email, role |
| `Contrato` | `contratos` | id, empresa_id, valor_refeicao, refeicoes_dia |
| `Ingrediente` | `ingredientes` | id, empresa_id, nome, custo_unitario |
| `FichaTecnica` | `fichas_tecnicas` | id, empresa_id, nome, rendimento, custo |
| `FichaIngrediente` | `ficha_ingredientes` | ficha_id, ingrediente_id, quantidade |
| `Cardapio` | `cardapios` | id, empresa_id, status, job_id |
| `CardapioDia` | `cardapio_dias` | id, cardapio_id, data |
| `CardapioRefeicao` | `cardapio_refeicoes` | id, dia_id, tipo, pratos |
| `JobAgente` | `jobs_agente` | id, empresa_id, status, step, resultado |
| `LLMAuditLog` | `llm_audit_logs` | id, model, tokens, latency_ms |
| `KnowledgeDocument` | `knowledge_documents` | id, empresa_id, titulo |
| `KnowledgeChunk` | `knowledge_chunks` | id, document_id, embedding |
| `SessaoChat` | `sessoes_chat` | id, empresa_id, job_id |
| `MensagemChat` | `mensagens_chat` | id, sessao_id, role, conteudo |

## Common Queries

```python
from database.connection import get_session
from database.models import FichaTecnica, Empresa, Contrato

# List empresas
session = next(get_session())
empresas = session.query(Empresa).all()

# Count fichas by empresa
from sqlalchemy import func
counts = session.query(
    Empresa.nome,
    func.count(FichaTecnica.id)
).join(FichaTecnica).group_by(Empresa.nome).all()

# Find contracts for an empresa
contratos = session.query(Contrato).filter(
    Contrato.empresa_id == empresa_id
).all()

# Recent jobs
jobs = session.query(JobAgente).order_by(
    JobAgente.created_at.desc()
).limit(10).all()
```

## Migration Workflow

```bash
# Create migration
source venv/bin/activate && alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Current version
alembic current
```

## Seed Data

```bash
source venv/bin/activate && python3 seed_data.py
```

Creates:
- Test empresa
- Admin user
- Sample ingredientes
- Sample fichas técnicas
- Reference data for pipeline testing
