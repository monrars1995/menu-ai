"""
Menu.AI — Router de Cardápios
Gestão de cardápios gerados + workflow de aprovação.
"""
import io
import math
import re
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import (
    Cardapio, CardapioDia, CardapioRefeicao,
    AprovacaoCardapio, JobAgente, Contrato, FichaTecnica
)
from database.schemas import (
    CardapioCreate, CardapioDetalhado, CardapioOut, CardapioUpdate,
    AprovacaoCreate, AprovacaoOut,
)
from routers.auth_supabase import exigir_role, get_usuario_atual
from services.knowledge_base import sync_cardapio_document
from services.knowledge_hooks import sync_knowledge_safe

router = APIRouter(prefix="/api/cardapios", tags=["Cardápios"])


def _resolve_empresa_context(usuario, empresa_id: Optional[str]) -> str:
    requested = str(empresa_id).strip() if empresa_id else None
    user_empresa = str(usuario.empresa_id).strip() if getattr(usuario, "empresa_id", None) else None

    if usuario.role == "super_admin":
        resolved = requested or user_empresa
        if not resolved:
            raise HTTPException(
                status_code=400,
                detail="Super admin sem empresa no contexto. Informe empresa_id.",
            )
        return resolved

    if requested and requested != user_empresa:
        raise HTTPException(status_code=403, detail="empresa_id não corresponde ao utilizador autenticado.")
    if not user_empresa:
        raise HTTPException(status_code=400, detail="Utilizador sem empresa associada.")
    return user_empresa


@router.get("/", summary="Listar cardápios")
def listar(
    empresa_id: Optional[str] = Query(None),
    status_filtro: Optional[str] = Query(None, alias="status"),
    contrato_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    q = db.query(Cardapio)

    eid = _resolve_empresa_context(usuario, empresa_id)
    q = q.filter(Cardapio.empresa_id == eid)

    if status_filtro:
        q = q.filter(Cardapio.status == status_filtro)
    if contrato_id:
        q = q.filter(Cardapio.contrato_id == contrato_id)

    total = q.count()
    items = q.order_by(Cardapio.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "items": [CardapioOut.model_validate(c) for c in items],
        "total": total,
        "page": (skip // limit) + 1 if limit else 1,
        "per_page": limit,
        "pages": math.ceil(total / limit) if limit else 0,
    }


@router.get("/{cardapio_id}", response_model=CardapioDetalhado, summary="Buscar cardápio completo")
def buscar(
    cardapio_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Retorna cardápio completo com todos os dias e refeições."""
    cardapio = db.query(Cardapio).filter(Cardapio.id == cardapio_id).first()
    if not cardapio:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")

    if usuario.role != "super_admin" and cardapio.empresa_id != usuario.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    return CardapioDetalhado.model_validate(cardapio)


@router.post("/", response_model=CardapioOut, status_code=status.HTTP_201_CREATED,
             summary="Criar cardápio manualmente")
def criar(
    body: CardapioCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    """Cria cardápio vazio para preenchimento manual."""
    empresa_id = body.empresa_id if usuario.role == "super_admin" else usuario.empresa_id
    cardapio = Cardapio(
        **body.model_dump(exclude={"empresa_id"}),
        empresa_id=empresa_id,
        criado_por_id=usuario.id,
    )
    db.add(cardapio)
    db.commit()
    db.refresh(cardapio)
    sync_knowledge_safe(sync_cardapio_document, db, cardapio)
    db.commit()
    return CardapioOut.model_validate(cardapio)


@router.patch("/{cardapio_id}", response_model=CardapioOut, summary="Atualizar cardápio")
def atualizar(
    cardapio_id: str,
    body: CardapioUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    cardapio = db.query(Cardapio).filter(Cardapio.id == cardapio_id).first()
    if not cardapio:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")

    if usuario.role != "super_admin" and cardapio.empresa_id != usuario.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(cardapio, campo, valor)

    cardapio.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cardapio)
    sync_knowledge_safe(sync_cardapio_document, db, cardapio)
    db.commit()
    return CardapioOut.model_validate(cardapio)


@router.delete("/{cardapio_id}", status_code=status.HTTP_204_NO_CONTENT)
def arquivar(
    cardapio_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin")),
):
    """Arquiva cardápio (soft delete)."""
    cardapio = db.query(Cardapio).filter(Cardapio.id == cardapio_id).first()
    if not cardapio:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")
    cardapio.status = "arquivado"
    db.commit()
    db.refresh(cardapio)
    sync_knowledge_safe(sync_cardapio_document, db, cardapio)
    db.commit()


# ============================================================
# Aprovações (Workflow)
# ============================================================

@router.post("/{cardapio_id}/aprovacao", response_model=AprovacaoOut,
             status_code=status.HTTP_201_CREATED, summary="Aprovar ou reprovar cardápio")
def aprovar(
    cardapio_id: str,
    body: AprovacaoCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "gestor")),
):
    """
    Registra decisão de aprovação no workflow.
    - aprovado → cardápio vai para status 'aprovado'
    - reprovado → volta para 'em_revisao'
    - solicitado_revisao → status 'em_revisao'
    """
    cardapio = db.query(Cardapio).filter(Cardapio.id == cardapio_id).first()
    if not cardapio:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")

    aprovacao = AprovacaoCardapio(
        cardapio_id=cardapio_id,
        aprovado_por_id=usuario.id,
        status=body.status,
        comentario=body.comentario,
    )
    db.add(aprovacao)

    # Atualiza status do cardápio
    if body.status == "aprovado":
        cardapio.status = "aprovado"
    elif body.status in ("reprovado", "solicitado_revisao"):
        cardapio.status = "em_revisao"

    cardapio.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(aprovacao)
    db.refresh(cardapio)
    sync_knowledge_safe(sync_cardapio_document, db, cardapio)
    db.commit()
    return AprovacaoOut.model_validate(aprovacao)


@router.get("/{cardapio_id}/aprovacoes", response_model=List[AprovacaoOut],
            summary="Histórico de aprovações")
def historico_aprovacoes(
    cardapio_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    aprovacoes = db.query(AprovacaoCardapio).filter(
        AprovacaoCardapio.cardapio_id == cardapio_id
    ).order_by(AprovacaoCardapio.created_at.desc()).all()
    return [AprovacaoOut.model_validate(a) for a in aprovacoes]


@router.post("/{cardapio_id}/publicar", response_model=CardapioOut, summary="Publicar cardápio")
def publicar(
    cardapio_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "gestor")),
):
    """Publica cardápio aprovado."""
    cardapio = db.query(Cardapio).filter(Cardapio.id == cardapio_id).first()
    if not cardapio:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")
    if cardapio.status != "aprovado":
        raise HTTPException(status_code=400, detail="Cardápio precisa estar aprovado antes de publicar.")

    cardapio.status = "publicado"
    cardapio.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cardapio)
    sync_knowledge_safe(sync_cardapio_document, db, cardapio)
    db.commit()
    return CardapioOut.model_validate(cardapio)


# ============================================================
# Exportação
# ============================================================

@router.get("/{cardapio_id}/exportar", summary="Exportar cardápio (XLSX, CSV, TXT ou PDF)")
def exportar(
    cardapio_id: str,
    formato: str = Query("xlsx", pattern=r"^(xlsx|csv|txt|pdf)$"),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Exporta cardápio em XLSX, CSV, TXT ou PDF."""
    cardapio = db.query(Cardapio).filter(Cardapio.id == cardapio_id).first()
    if not cardapio:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")

    if not cardapio.resultado_raw and not cardapio.dias:
        raise HTTPException(status_code=404, detail="Cardápio sem conteúdo para exportar.")

    nome_arquivo = re.sub(r"[^\w\-]", "_", cardapio.nome)

    if formato == "txt":
        content = cardapio.resultado_raw or _gerar_txt(cardapio)
        return Response(
            content=content.encode("utf-8"),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}.txt"'},
        )

    if formato == "csv":
        return _gerar_csv(cardapio, db, nome_arquivo)

    if formato == "pdf":
        buf = _gerar_pdf(cardapio, db)
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}.pdf"'},
        )

    # XLSX multi-sheet com formatação
    buf = _gerar_xlsx(cardapio, db)
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}.xlsx"'},
    )


# ============================================================
# Exportação XLSX multi-sheet
# ============================================================

_HEADER_FONT = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
_HEADER_FILL = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
_HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
_DATA_ALIGN = Alignment(vertical="center", wrap_text=True)
_THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

_CAT_COLORS = {
    "ARROZ": "E2EFDA",
    "FEIJAO": "FCE4D6",
    "PRATO PROTEICO": "DCE6F1",
    "GUARNICAO": "FFF2CC",
    "SALADAS CRUA": "E4DFEC",
    "SALADA COZIDA": "E4DFEC",
    "SALADA ELABORADA": "E4DFEC",
    "ACOMPANHAMENTO": "D9D9D9",
    "SOBREMESA": "F8CBAD",
    "FRUTAS": "C6EFCE",
}


def _apply_header_style(ws, num_cols: int):
    for col_idx in range(1, num_cols + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGN
        cell.border = _THIN_BORDER
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _apply_data_style(ws, num_rows: int, num_cols: int):
    for row in range(2, num_rows + 1):
        cat_cell = ws.cell(row=row, column=4)  # Coluna Categoria
        cat = (cat_cell.value or "").upper()
        fill_color = _CAT_COLORS.get(cat, "FFFFFF")
        row_fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
        for col_idx in range(1, num_cols + 1):
            cell = ws.cell(row=row, column=col_idx)
            cell.alignment = _DATA_ALIGN
            cell.border = _THIN_BORDER
            cell.fill = row_fill


def _auto_width(ws, max_width: int = 50):
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, max_width)


def _write_sheet(ws, headers: list[str], rows: list[list], title: str = ""):
    ws.title = title[:31]
    for ci, h in enumerate(headers, 1):
        ws.cell(row=1, column=ci, value=h)
    for ri, row in enumerate(rows, 2):
        for ci, val in enumerate(row, 1):
            ws.cell(row=ri, column=ci, value=val)
    _apply_header_style(ws, len(headers))
    _apply_data_style(ws, len(rows) + 1, len(headers))
    _auto_width(ws)


def _tem_refeicoes_estruturadas(cardapio: Cardapio) -> bool:
    for dia in cardapio.dias or []:
        if dia.refeicoes:
            return True
    return False


def _cardapio_para_dataframe(cardapio: Cardapio) -> pd.DataFrame:
    """Converte estrutura do banco para DataFrame (sem enriquecimento de custos)."""
    if _tem_refeicoes_estruturadas(cardapio):
        rows = []
        for dia in cardapio.dias:
            for ref in dia.refeicoes:
                # Custo: preserva valor real; marca None se zero para preenchimento posterior
                custo = ref.custo_porcao or 0
                rows.append({
                    "Dia": dia.numero_dia,
                    "Data": dia.data.strftime("%d/%m/%Y") if dia.data else "",
                    "Refeição": ref.tipo_refeicao.replace("_", " ").title(),
                    "Categoria": ref.categoria or "",
                    "Código": ref.codigo_prato or "",
                    "Prato": ref.nome_prato,
                    "Custo (R$)": round(custo, 2) if custo > 0 else None,
                })
        return pd.DataFrame(rows) if rows else pd.DataFrame({"Cardápio": [cardapio.nome]})

    if cardapio.resultado_raw and "|" in cardapio.resultado_raw:
        return _extrair_markdown(cardapio.resultado_raw)

    return pd.DataFrame({"Cardápio": [cardapio.nome]})


_CODIGO_COL_CANDIDATES = (
    "Código",
    "Codigo",
    "codigo",
    "Código Prato",
    "Codigo Prato",
    "Código da Ficha",
    "Cod",
)


def _coluna_codigo_df(df: pd.DataFrame) -> Optional[str]:
    for c in _CODIGO_COL_CANDIDATES:
        if c in df.columns:
            return c
    for col in df.columns:
        cl = str(col).strip().lower()
        if cl in ("código", "codigo", "cod", "código prato", "codigo prato"):
            return col
    return None


def _enriquecer_custos_dataframe(
    df: pd.DataFrame,
    cardapio: Cardapio,
    db: Session,
) -> pd.DataFrame:
    """Preenche ou sobrescreve coluna Custo (R$) com custo_porcao das fichas (match por código)."""
    if df.empty or len(df.columns) <= 1:
        return df
    col_cod = _coluna_codigo_df(df)
    if not col_cod or not cardapio.empresa_id:
        return df

    codigos_raw = df[col_cod].dropna().astype(str).str.strip()
    codigos_raw = codigos_raw[codigos_raw != ""]
    codigos = list({c for c in codigos_raw.unique() if c})
    if not codigos:
        return df

    fichas = (
        db.query(FichaTecnica)
        .filter(
            FichaTecnica.empresa_id == cardapio.empresa_id,
            FichaTecnica.codigo.in_(codigos),
        )
        .all()
    )
    custo_por_codigo = {f.codigo.strip(): float(f.custo_porcao or 0) for f in fichas}

    custo_col = "Custo (R$)"
    if custo_col not in df.columns:
        df = df.copy()
        df[custo_col] = None

    def _custo_row(cod: object) -> Optional[float]:
        if cod is None or (isinstance(cod, float) and pd.isna(cod)):
            return None
        key = str(cod).strip()
        if not key:
            return None
        return custo_por_codigo.get(key)

    custos = df[col_cod].map(_custo_row)
    # Só preenche onde: (a) temos match na ficha E (b) o valor atual é nulo/zero
    existing = df[custo_col]
    needs_fill = existing.isna() | (existing == 0) | (existing == 0.0)
    mask = custos.notna() & needs_fill
    df = df.copy()
    df.loc[mask, custo_col] = custos[mask].round(2)
    return df


def _cardapio_export_dataframe(cardapio: Cardapio, db: Session) -> pd.DataFrame:
    """DataFrame para CSV/XLSX: sempre tenta enriquecer custos a partir das fichas."""
    df = _cardapio_para_dataframe(cardapio)
    # Sempre enriquece: preenche custos None/zero com dados reais das fichas técnicas
    return _enriquecer_custos_dataframe(df, cardapio, db)


def _extrair_markdown(texto: str) -> pd.DataFrame:
    linhas = [l.strip() for l in texto.split("\n") if "|" in l]
    linhas = [l for l in linhas if not re.match(r"^\|[\s\-:|]+\|$", l)]
    rows, header = [], None
    for l in linhas:
        cells = [c.strip() for c in l.split("|") if c.strip()]
        if not cells:
            continue
        if header is None:
            header = cells
        elif len(cells) == len(header):
            rows.append(cells)
    if not header or not rows:
        return pd.DataFrame({"Cardápio": texto.split("\n")})
    return pd.DataFrame(rows, columns=header)


def _gerar_txt(cardapio: Cardapio) -> str:
    linhas = [f"CARDÁPIO: {cardapio.nome}\n"]
    for dia in cardapio.dias:
        linhas.append(f"\n=== Dia {dia.numero_dia} ===")
        for ref in dia.refeicoes:
            linhas.append(f"  [{ref.categoria}] {ref.nome_prato} — R$ {ref.custo_porcao:.2f}")
        linhas.append(f"  Total do dia: R$ {dia.custo_total:.2f}")
    return "\n".join(linhas)


def _gerar_csv(cardapio: Cardapio, db: Session, nome_arquivo: str) -> Response:
    """Gera CSV com encoding UTF-8-BOM para compatibilidade com Excel."""
    df = _cardapio_export_dataframe(cardapio, db)
    buf = io.StringIO()
    df.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}.csv"'},
    )


def _gerar_pdf(cardapio: Cardapio, db: Session) -> io.BytesIO:
    """Gera PDF formatado com dias, refeições, pratos e custos."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph, Spacer, Table, TableStyle, SimpleDocTemplate,
        PageBreak, KeepTogether,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#1d1d1f"), spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle2", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#6e6e73"), spaceAfter=12)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#0066cc"), spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle("Body2", parent=styles["Normal"], fontSize=9, leading=12)

    story = []

    # Title
    story.append(Paragraph(cardapio.nome, title_style))
    story.append(Paragraph(f"Gerado em {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    story.append(Spacer(1, 8))

    # Table data
    headers = ["Dia", "Refeição", "Categoria", "Prato", "Custo (R$)"]
    col_widths = [1.5*cm, 3.5*cm, 3*cm, 7*cm, 2.5*cm]

    rows_data = [headers]
    custo_total_geral = 0.0

    if cardapio.dias:
        for dia in cardapio.dias:
            for ref in dia.refeicoes:
                rows_data.append([
                    str(dia.numero_dia),
                    ref.tipo_refeicao.replace("_", " ").title(),
                    ref.categoria or "",
                    ref.nome_prato,
                    f"R$ {ref.custo_porcao:.2f}" if ref.custo_porcao else "—",
                ])
            custo_dia = dia.custo_total or sum(r.custo_porcao or 0 for r in dia.refeicoes)
            custo_total_geral += custo_dia
            # Subtotal row
            rows_data.append([
                "", "", "", f"Subtotal Dia {dia.numero_dia}",
                f"R$ {custo_dia:.2f}",
            ])

    # Total row
    rows_data.append(["", "", "", "TOTAL GERAL", f"R$ {custo_total_geral:.2f}"])

    # Table styling
    table = Table(rows_data, colWidths=col_widths, repeatRows=1)
    table_style_cmds = [
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0066cc")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (4, 0), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#d0d0d0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f5f5f7")]),
        ("FONT", (0, 1), (-1, -2), "Helvetica", 8),
        # Total row
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8e8ed")),
        # Subtotal rows
        ("FONT", (0, -3), (-1, -2), "Helvetica-Bold", 8),
        ("TEXTCOLOR", (0, -3), (-1, -2), colors.HexColor("#6e6e73")),
    ]
    table.setStyle(TableStyle(table_style_cmds))
    story.append(table)

    # Shopping list summary
    if cardapio.dias:
        story.append(PageBreak())
        story.append(Paragraph("Lista de Compras", section_style))

        pratos = set()
        for dia in cardapio.dias:
            for ref in dia.refeicoes:
                if ref.codigo_prato:
                    pratos.add(ref.codigo_prato)

        from collections import defaultdict
        ing_map: dict[str, dict] = defaultdict(lambda: {"qtd": 0.0, "custo": 0.0})
        if pratos:
            fichas = db.query(FichaTecnica).filter(
                FichaTecnica.empresa_id == cardapio.empresa_id,
                FichaTecnica.codigo.in_(list(pratos)),
            ).all()
            for ficha in fichas:
                for item in ficha.ingredientes_ficha:
                    nome = item.ingrediente.nome if item.ingrediente else "Desconhecido"
                    ing_map[nome]["qtd"] += item.quantidade_bruta_g or 0
                    ing_map[nome]["custo"] += item.custo_calculado or 0

            shop_headers = ["Ingrediente", "Qtd Total (g)", "Custo Est. (R$)"]
            shop_rows = [shop_headers]
            for nome in sorted(ing_map):
                d = ing_map[nome]
                shop_rows.append([nome, f"{d['qtd']:.1f}", f"R$ {d['custo']:.2f}"])

            shop_table = Table(shop_rows, colWidths=[8*cm, 4*cm, 3.5*cm], repeatRows=1)
            shop_table.setStyle(TableStyle([
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0066cc")),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d0d0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f7")]),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
            ]))
            story.append(shop_table)

    doc.build(story)
    return buf


def _gerar_xlsx(cardapio: Cardapio, db: Session) -> io.BytesIO:
    """Gera workbook XLSX com múltiplas sheets formatadas."""
    from openpyxl import Workbook

    wb = Workbook()

    # --- Sheet 1: Cardápio ---
    df = _cardapio_export_dataframe(cardapio, db)
    headers = list(df.columns)
    rows = [list(r) for r in df.values]
    ws1 = wb.active
    _write_sheet(ws1, headers, rows, "Cardápio")

    # --- Sheet 2: Lista de Compras (agrupar ingredientes das fichas usadas) ---
    compras_headers = ["Categoria", "Ingrediente", "Qtd Total (g)", "Custo Est. (R$)"]
    compras_rows = []
    if cardapio.dias:
        # Coletar pratos únicos do cardápio
        pratos = set()
        for dia in cardapio.dias:
            for ref in dia.refeicoes:
                if ref.codigo_prato:
                    pratos.add(ref.codigo_prato)
        # Buscar fichas e somar ingredientes
        from collections import defaultdict
        ing_map: dict[str, dict] = defaultdict(lambda: {"qtd": 0.0, "custo": 0.0})
        if pratos:
            fichas = db.query(FichaTecnica).filter(
                FichaTecnica.empresa_id == cardapio.empresa_id,
                FichaTecnica.codigo.in_(list(pratos)),
            ).all()
            for ficha in fichas:
                for item in ficha.ingredientes_ficha:
                    nome = item.ingrediente.nome if item.ingrediente else "Desconhecido"
                    ing_map[nome]["qtd"] += item.quantidade_bruta_g or 0
                    ing_map[nome]["custo"] += item.custo_calculado or 0
            for nome in sorted(ing_map):
                d = ing_map[nome]
                cat = ""
                for ficha in fichas:
                    for item in ficha.ingredientes_ficha:
                        if item.ingrediente and item.ingrediente.nome == nome:
                            cat = item.ingrediente.categoria or ""
                            break
                    if cat:
                        break
                compras_rows.append([cat, nome, round(d["qtd"], 1), round(d["custo"], 2)])
    _write_sheet(wb.create_sheet(), compras_headers, compras_rows, "Lista de Compras")

    # --- Sheet 3: Resumo por Dia ---
    resumo_dia_headers = ["Dia", "Data", "Nº Refeições", "Custo Total (R$)", "Custo Médio/Refeição"]
    resumo_dia_rows = []
    custo_total_geral = 0.0
    for dia in cardapio.dias:
        n_refs = len(dia.refeicoes)
        custo_dia = dia.custo_total or sum(r.custo_porcao or 0 for r in dia.refeicoes)
        custo_medio = round(custo_dia / n_refs, 2) if n_refs else 0
        resumo_dia_rows.append([
            dia.numero_dia,
            dia.data.strftime("%d/%m/%Y") if dia.data else "",
            n_refs,
            round(custo_dia, 2),
            custo_medio,
        ])
        custo_total_geral += custo_dia
    resumo_dia_rows.append([
        "", "TOTAL", "", round(custo_total_geral, 2),
        round(custo_total_geral / max(len(resumo_dia_rows), 1), 2),
    ])
    _write_sheet(wb.create_sheet(), resumo_dia_headers, resumo_dia_rows, "Resumo Diário")

    # --- Sheet 4: Resumo Nutricional (por categoria) ---
    nut_headers = ["Categoria", "Nº Pratos", "Custo Médio (R$)"]
    nut_rows = []
    if cardapio.dias:
        cat_stats: dict[str, dict] = defaultdict(lambda: {"n": 0, "custo": 0.0})
        for dia in cardapio.dias:
            for ref in dia.refeicoes:
                cat = ref.categoria or "Sem categoria"
                cat_stats[cat]["n"] += 1
                cat_stats[cat]["custo"] += ref.custo_porcao or 0
        for cat in sorted(cat_stats):
            s = cat_stats[cat]
            nut_rows.append([cat, s["n"], round(s["custo"] / max(s["n"], 1), 2)])
    _write_sheet(wb.create_sheet(), nut_headers, nut_rows, "Resumo Nutricional")

    # --- Sheet 5: Incidência Proteica ---
    prot_headers = ["Tipo Proteína", "Ocorrências", "% do Total", "Custo Médio (R$)"]
    prot_rows = []
    if cardapio.dias:
        prot_stats: dict[str, dict] = defaultdict(lambda: {"n": 0, "custo": 0.0})
        total_prots = 0
        for dia in cardapio.dias:
            for ref in dia.refeicoes:
                cat_upper = (ref.categoria or "").upper()
                if "PROT" in cat_upper:
                    subtipo = _detectar_subtipo_proteina(ref.nome_prato)
                    prot_stats[subtipo]["n"] += 1
                    prot_stats[subtipo]["custo"] += ref.custo_porcao or 0
                    total_prots += 1
        for tipo in sorted(prot_stats):
            s = prot_stats[tipo]
            pct = round((s["n"] / max(total_prots, 1)) * 100, 1)
            prot_rows.append([
                tipo,
                s["n"],
                f"{pct}%",
                round(s["custo"] / max(s["n"], 1), 2),
            ])
    _write_sheet(wb.create_sheet(), prot_headers, prot_rows, "Incidência Proteica")

    buf = io.BytesIO()
    wb.save(buf)
    return buf


# ============================================================
# Helpers de classificação proteica
# ============================================================

_SUBTIPOS_PROTEINA = {
    "Bovino": ["bovino", "carne", "patinho", "acém", "músculo", "alcatra",
               "lagarto", "cupim", "maminha", "contra filé", "contrafilé",
               "coxão", "paleta", "costela bovina"],
    "Frango": ["frango", "ave", "peito de frango", "coxa", "sobrecoxa",
               "filé de frango", "frango assado", "frango grelhado"],
    "Suíno": ["suíno", "porco", "lombo", "pernil", "bisteca",
              "costela suína", "linguiça"],
    "Peixe": ["peixe", "tilápia", "merluza", "sardinha", "atum",
              "bacalhau", "pescada", "salmão", "filé de peixe"],
    "Ovo": ["ovo", "omelete", "ovos", "ovo cozido", "ovo mexido"],
    "Vegetal": ["soja", "grão-de-bico", "grão de bico", "lentilha",
                "feijão", "tofu", "PTS", "proteína de soja",
                "proteina texturizada"],
}


def _detectar_subtipo_proteina(nome_prato: str) -> str:
    """Classifica o prato proteico por subtipo baseado no nome."""
    nome_lower = (nome_prato or "").lower()
    for subtipo, keywords in _SUBTIPOS_PROTEINA.items():
        if any(kw.lower() in nome_lower for kw in keywords):
            return subtipo
    return "Outro"
