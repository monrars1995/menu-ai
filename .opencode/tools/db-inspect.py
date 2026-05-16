#!/usr/bin/env python3
"""Menu.AI opencode tool: inspect database contents.

Usage:
  python3 .opencode/tools/db-inspect.py empresas                          # List all empresas
  python3 .opencode/tools/db-inspect.py fichas [--empresa-id ID]           # Count fichas
  python3 .opencode/tools/db-inspect.py contratos [--empresa-id ID]        # List contratos
  python3 .opencode/tools/db-inspect.py jobs [--limit N]                   # Recent jobs
  python3 .opencode/tools/db-inspect.py stats                              # DB statistics
  python3 .opencode/tools/db-inspect.py audit [--limit N]                  # LLM audit logs
"""
import argparse, json, os, sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

def load_env():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def get_session():
    from database.connection import SessionLocal
    return SessionLocal()

def cmd_empresas(args):
    from database.models import Empresa
    s = get_session()
    rows = s.query(Empresa).all()
    for r in rows:
        print(f"  {r.id}  {r.nome}  ({getattr(r, 'cnpj', '-')})")
    print(f"Total: {len(rows)}")
    s.close()

def cmd_fichas(args):
    from database.models import FichaTecnica
    from sqlalchemy import func
    s = get_session()
    q = s.query(FichaTecnica)
    if args.empresa_id:
        q = q.filter(FichaTecnica.empresa_id == args.empresa_id)
    count = q.count()
    by_cat = s.query(
        FichaTecnica.categoria, func.count(FichaTecnica.id)
    ).group_by(FichaTecnica.categoria).all()
    print(f"  Total fichas: {count}")
    for cat, n in by_cat:
        print(f"    {cat or 'sem categoria'}: {n}")
    s.close()

def cmd_contratos(args):
    from database.models import Contrato
    s = get_session()
    q = s.query(Contrato)
    if args.empresa_id:
        q = q.filter(Contrato.empresa_id == args.empresa_id)
    for c in q.all():
        print(f"  {c.id}  valor_refeicao={getattr(c, 'valor_refeicao', '-')}  status={getattr(c, 'status', '-')}")
    print(f"Total: {q.count()}")
    s.close()

def cmd_jobs(args):
    from database.models import JobAgente
    s = get_session()
    rows = s.query(JobAgente).order_by(JobAgente.created_at.desc()).limit(args.limit).all()
    for j in rows:
        print(f"  {j.id}  step={getattr(j, 'step', '-')}  status={j.status}  created={j.created_at}")
    print(f"Showing last {len(rows)} jobs")
    s.close()

def cmd_stats(args):
    from database.models import Empresa, FichaTecnica, Ingrediente, Contrato, Cardapio, JobAgente
    s = get_session()
    print(f"  Empresas:    {s.query(Empresa).count()}")
    print(f"  Contratos:   {s.query(Contrato).count()}")
    print(f"  Fichas:      {s.query(FichaTecnica).count()}")
    print(f"  Ingredientes:{s.query(Ingrediente).count()}")
    print(f"  Cardapios:   {s.query(Cardapio).count()}")
    print(f"  Jobs:        {s.query(JobAgente).count()}")
    s.close()

def cmd_audit(args):
    from database.models import LLMAuditLog
    s = get_session()
    rows = s.query(LLMAuditLog).order_by(LLMAuditLog.created_at.desc()).limit(args.limit).all()
    for a in rows:
        print(f"  {a.created_at}  model={getattr(a, 'model', '-')}  tokens={getattr(a, 'tokens_total', '-')}  latency={getattr(a, 'latency_ms', '-')}ms")
    print(f"Showing last {len(rows)} audit entries")
    s.close()

def main():
    load_env()
    parser = argparse.ArgumentParser(description="Menu.AI DB inspector")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("empresas")
    p_f = sub.add_parser("fichas"); p_f.add_argument("--empresa-id")
    p_c = sub.add_parser("contratos"); p_c.add_argument("--empresa-id")
    p_j = sub.add_parser("jobs"); p_j.add_argument("--limit", type=int, default=10)
    sub.add_parser("stats")
    p_a = sub.add_parser("audit"); p_a.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()
    cmds = {
        "empresas": cmd_empresas, "fichas": cmd_fichas, "contratos": cmd_contratos,
        "jobs": cmd_jobs, "stats": cmd_stats, "audit": cmd_audit,
    }
    fn = cmds.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
