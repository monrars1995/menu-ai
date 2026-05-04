"""
seed_data.py — Importa dados da planilha para o banco configurado em DATABASE_URL.

Uso:
    export MENUAI_FICHAS_IMPORT_XLSX=/caminho/para/menuai_fichas_importacao_1.xlsx
    python seed_data.py
"""
import os
import sys
import uuid

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import engine, SessionLocal
from database import models  # registra todos os models na Base
from database.connection import Base
from database.models import Empresa, Ingrediente, FichaTecnica, FichaIngrediente

# Planilha de importação (única fonte para o seed; não usada em runtime da API)
_DEFAULT_XLSX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "menuai_fichas_importacao_1.xlsx")
XLSX_PATH = os.getenv("MENUAI_FICHAS_IMPORT_XLSX", _DEFAULT_XLSX).strip()
TEST_EMPRESA_ID = "00000000-0000-0000-0000-000000000001"

VALID_UNIDADE    = {"kg", "g", "L", "ml", "un", "cx", "pct"}
VALID_CATEGORIA  = {"PROTEINA", "CARBOIDRATO", "HORTALICA", "FRUTA",
                    "LATICINIOS", "GORDURA", "CONDIMENTO", "BEBIDA", "OUTRO"}
VALID_DIFICULDADE = {"facil", "medio", "dificil"}


def _str(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def _float(val):
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _int(val):
    if pd.isna(val):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _bool(val):
    s = _str(val)
    return s is not None and s.upper() == "SIM"


def seed_empresa(db):
    empresa = db.query(Empresa).filter_by(id=TEST_EMPRESA_ID).first()
    if not empresa:
        empresa = Empresa(id=TEST_EMPRESA_ID, nome="Empresa Teste", ativo=True)
        db.add(empresa)
        db.commit()
        print("✅ Empresa de teste criada")
    else:
        print("   Empresa de teste já existe")
    return empresa


def seed_ingredientes(db, xl):
    df = xl["INGREDIENTES"]
    # Row 0 = title, row 1 = warning, row 2 = column headers, row 3+ = data
    data = df.iloc[3:].reset_index(drop=True)

    ing_map = {}   # codigo → uuid
    inserted = 0
    skipped  = 0

    for _, row in data.iterrows():
        codigo = _str(row.iloc[0])
        nome   = _str(row.iloc[1])
        if not nome:
            continue

        unidade   = _str(row.iloc[2]) or "kg"
        if unidade not in VALID_UNIDADE:
            unidade = "kg"

        categoria = _str(row.iloc[5]) or "OUTRO"
        if categoria not in VALID_CATEGORIA:
            categoria = "OUTRO"

        # Skip se código já existe no mapa (duplicado na planilha)
        if codigo and codigo in ing_map:
            skipped += 1
            continue

        # Verifica se já está no banco
        if codigo:
            existing = db.query(Ingrediente).filter_by(codigo=codigo).first()
        else:
            existing = db.query(Ingrediente).filter_by(nome=nome, empresa_id=None).first()

        if existing:
            if codigo:
                ing_map[codigo] = existing.id
            skipped += 1
            continue

        ing_id = str(uuid.uuid4())
        ing = Ingrediente(
            id=ing_id,
            empresa_id=None,  # ingrediente global
            codigo=codigo,
            nome=nome,
            unidade_medida=unidade,
            custo_unitario=_float(row.iloc[3]) or 0.0,
            fator_correcao=_float(row.iloc[4]) or 1.0,
            categoria=categoria,
            calorias_100g=_float(row.iloc[6]),
            proteina_100g=_float(row.iloc[7]),
            carboidrato_100g=_float(row.iloc[8]),
            gordura_100g=_float(row.iloc[9]),
            fibra_100g=_float(row.iloc[10]),
            sodio_100g=_float(row.iloc[11]),
            alergeno=_bool(row.iloc[12]),
            tipo_alergeno=_str(row.iloc[13]),
            fornecedor=_str(row.iloc[14]),
            ativo=True,
        )
        db.add(ing)
        if codigo:
            ing_map[codigo] = ing_id
        inserted += 1

        if inserted % 100 == 0:
            db.commit()

    db.commit()
    print(f"✅ Ingredientes: {inserted} inseridos, {skipped} já existentes/duplicados")
    return ing_map


def seed_fichas(db, xl):
    df = xl["FICHAS_TÉCNICAS"]
    # Row 0 = title, row 1 = warning, row 2 = headers, row 3+ = data
    data = df.iloc[3:].reset_index(drop=True)

    ficha_map = {}  # codigo → uuid
    inserted = 0
    skipped  = 0

    for _, row in data.iterrows():
        codigo = _str(row.iloc[0])
        nome   = _str(row.iloc[1])
        if not codigo or not nome:
            continue

        if codigo in ficha_map:
            skipped += 1
            continue

        existing = db.query(FichaTecnica).filter_by(
            codigo=codigo, empresa_id=TEST_EMPRESA_ID
        ).first()
        if existing:
            ficha_map[codigo] = existing.id
            skipped += 1
            continue

        dificuldade = _str(row.iloc[6]) or "medio"
        if dificuldade not in VALID_DIFICULDADE:
            dificuldade = "medio"

        ft_id = str(uuid.uuid4())
        ft = FichaTecnica(
            id=ft_id,
            empresa_id=TEST_EMPRESA_ID,
            codigo=codigo,
            nome=nome.strip(),
            categoria=_str(row.iloc[2]) or "OUTRO",
            rendimento_porcoes=_int(row.iloc[3]) or 1,
            peso_porcao_g=_float(row.iloc[4]),
            tempo_preparo_min=_int(row.iloc[5]),
            dificuldade=dificuldade,
            temperatura_servico=_str(row.iloc[7]),
            equipamento=_str(row.iloc[8]),
            contem_gluten=_bool(row.iloc[9]),
            contem_lactose=_bool(row.iloc[10]),
            vegana=_bool(row.iloc[11]),
            vegetariana=_bool(row.iloc[12]),
            modo_preparo=_str(row.iloc[13]),
            observacoes=_str(row.iloc[14]),
            ativo=True,
        )
        db.add(ft)
        ficha_map[codigo] = ft_id
        inserted += 1

        if inserted % 200 == 0:
            db.commit()

    db.commit()
    print(f"✅ Fichas técnicas: {inserted} inseridas, {skipped} já existentes/duplicadas")
    return ficha_map


def seed_composicao(db, xl, ficha_map, ing_map):
    df = xl["COMPOSIÇÃO_FICHAS"]
    # Row 0 = title, row 1 = headers, row 2+ = data
    data = df.iloc[2:].reset_index(drop=True)

    inserted = 0
    skipped  = 0

    for _, row in data.iterrows():
        cod_ficha = _str(row.iloc[0])
        cod_ing   = _str(row.iloc[3])

        if not cod_ficha or not cod_ing:
            continue

        ficha_id = ficha_map.get(cod_ficha)
        ing_id   = ing_map.get(cod_ing)

        if not ficha_id or not ing_id:
            skipped += 1
            continue

        qtd = _float(row.iloc[5]) or 0.0
        fc  = _float(row.iloc[6]) or 1.0

        fi = FichaIngrediente(
            id=str(uuid.uuid4()),
            ficha_tecnica_id=ficha_id,
            ingrediente_id=ing_id,
            quantidade_bruta_g=qtd,
            fator_correcao=fc,
            quantidade_liquida_g=round(qtd / fc, 4) if fc > 0 else qtd,
            custo_calculado=0.0,
            ordem=_int(row.iloc[2]) or 0,
            observacao=_str(row.iloc[7]),
        )
        db.add(fi)
        inserted += 1

        if inserted % 500 == 0:
            db.commit()

    db.commit()
    print(f"✅ Composições: {inserted} inseridas, {skipped} puladas (referência não encontrada)")


def main():
    if not XLSX_PATH or not os.path.isfile(XLSX_PATH):
        print(
            "❌ Defina MENUAI_FICHAS_IMPORT_XLSX com o caminho completo do ficheiro .xlsx de importação."
        )
        print("   Ex.: export MENUAI_FICHAS_IMPORT_XLSX=/caminho/menuai_fichas_importacao_1.xlsx")
        sys.exit(1)

    print("=" * 55)
    print("  Menu.AI — Seed de Dados")
    print("=" * 55)
    print(f"\n📂 Planilha: {XLSX_PATH}")
    print(f"🗄️  Banco:    {engine.url.render_as_string(hide_password=True)}\n")

    print("Criando tabelas...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas prontas\n")

    print("Lendo planilha Excel...")
    xl = pd.read_excel(XLSX_PATH, sheet_name=None, header=None)
    print(f"✅ Abas carregadas: {list(xl.keys())}\n")

    db = SessionLocal()
    try:
        seed_empresa(db)
        print()
        ing_map   = seed_ingredientes(db, xl)
        print()
        ficha_map = seed_fichas(db, xl)
        print()
        seed_composicao(db, xl, ficha_map, ing_map)

        print("\n" + "=" * 55)
        print("  🎉  Seed concluído com sucesso!")
        print("=" * 55)
        print(f"\n  Banco:        {engine.url.render_as_string(hide_password=True)}")
        print(f"  Empresa ID:   {TEST_EMPRESA_ID}")
        print("\n  Para testar a API, rode:")
        print("  python app.py\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Erro durante o seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
