"""
Menu.AI — Registry tipado de tools do copiloto operacional.

Fase inicial:
- leitura/consulta de ingredientes, fichas, contratos e cardápios
- mutações seguras guiadas para ingredientes e fichas
- ações operacionais de contrato/cardápio
"""
from __future__ import annotations

import json
import os
import queue
import time
import uuid
import logging
from dataclasses import dataclass
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Type

from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database.models import (
    AprovacaoCardapio,
    Cardapio,
    Contrato,
    FichaIngrediente,
    FichaTecnica,
    Ingrediente,
    JobAgente,
)
from pipeline.openrouter_models import (
    assert_llm_model_allowed_for_generation,
    assert_llm_model_allowed_for_review,
)
from routers.fichas_tecnicas import _calcular_ficha
from services.contract_parser import (
    analysis_looks_invalid,
    build_contract_extraction_error,
    extract_contract_text,
)
from services.geracao import launch_generation_job
from services.knowledge_base import (
    sync_cardapio_document,
    sync_contrato_document,
    sync_ficha_document,
)
from services.knowledge_hooks import sync_knowledge_safe
from services import job_state

logger = logging.getLogger("menuai.copilot_tools")

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "data" / "uploads"


@dataclass
class CopilotContext:
    usuario: Any
    empresa_id: str
    page_context: str = "gerar"
    sessao_id: Optional[str] = None
    contrato_id: Optional[str] = None
    cardapio_id: Optional[str] = None
    job_id: Optional[str] = None


@dataclass
class ToolExecutionResult:
    tool_name: str
    assistant_message: str
    result: dict[str, Any]
    context_updates: Optional[dict[str, Any]] = None


@dataclass
class CopilotTool:
    name: str
    description: str
    input_model: Type[BaseModel]
    handler: Callable[[Session, CopilotContext, BaseModel], ToolExecutionResult]
    mutation: bool = False

    def openai_schema(self) -> dict[str, Any]:
        schema = self.input_model.model_json_schema()
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }


class BuscarIngredientesArgs(BaseModel):
    busca: Optional[str] = Field(default=None, description="Trecho do nome do ingrediente")
    categoria: Optional[str] = Field(default=None, description="Categoria do ingrediente")
    limit: int = Field(default=12, ge=1, le=50)
    incluir_inativos: bool = False


class CriarIngredienteArgs(BaseModel):
    nome: str
    categoria: str = "OUTRO"
    custo_unitario: Optional[float] = Field(default=None, ge=0)
    unidade_medida: str = "kg"
    fornecedor: Optional[str] = None
    fator_correcao: float = Field(default=1.0, ge=1.0)
    codigo: Optional[str] = None


class EditarIngredienteArgs(BaseModel):
    ingrediente_id: Optional[str] = None
    busca_nome: Optional[str] = None
    nome: Optional[str] = None
    categoria: Optional[str] = None
    custo_unitario: Optional[float] = Field(default=None, ge=0)
    unidade_medida: Optional[str] = None
    fornecedor: Optional[str] = None
    fator_correcao: Optional[float] = Field(default=None, ge=1.0)
    ativo: Optional[bool] = None


class BuscarFichasArgs(BaseModel):
    busca: Optional[str] = None
    categoria: Optional[str] = None
    vegana: Optional[bool] = None
    vegetariana: Optional[bool] = None
    custo_max: Optional[float] = Field(default=None, ge=0)
    limit: int = Field(default=12, ge=1, le=50)


class FichaIngredienteInput(BaseModel):
    ingrediente_id: str
    quantidade_bruta_g: float = Field(..., gt=0)
    fator_correcao: float = Field(default=1.0, ge=1.0)
    observacao: Optional[str] = None


class CriarFichaArgs(BaseModel):
    codigo: Optional[str] = None
    nome: str
    categoria: str
    rendimento_porcoes: int = Field(default=1, ge=1)
    peso_porcao_g: Optional[float] = Field(default=None, ge=0)
    modo_preparo: Optional[str] = None
    observacoes: Optional[str] = None
    ingredientes: list[FichaIngredienteInput] = Field(default_factory=list)


class EditarFichaArgs(BaseModel):
    ficha_id: Optional[str] = None
    busca_nome: Optional[str] = None
    nome: Optional[str] = None
    categoria: Optional[str] = None
    rendimento_porcoes: Optional[int] = Field(default=None, ge=1)
    peso_porcao_g: Optional[float] = Field(default=None, ge=0)
    modo_preparo: Optional[str] = None
    observacoes: Optional[str] = None
    ingredientes: Optional[list[FichaIngredienteInput]] = None
    ativo: Optional[bool] = None


class BuscarContratosArgs(BaseModel):
    busca: Optional[str] = None
    ativo: Optional[bool] = True
    limit: int = Field(default=12, ge=1, le=50)


class AnalisarContratoArgs(BaseModel):
    contrato_id: Optional[str] = None
    busca_nome: Optional[str] = None
    llm_model: Optional[str] = None
    force: bool = False


class ListarCardapiosArgs(BaseModel):
    status: Optional[str] = None
    contrato_id: Optional[str] = None
    limit: int = Field(default=12, ge=1, le=50)


class VerCardapioArgs(BaseModel):
    cardapio_id: Optional[str] = None
    busca_nome: Optional[str] = None


class AprovarCardapioArgs(BaseModel):
    cardapio_id: Optional[str] = None
    comentario: Optional[str] = None


class GerarNovamenteCardapioArgs(BaseModel):
    cardapio_id: Optional[str] = None
    llm_model: Optional[str] = None
    review_llm_model: Optional[str] = None
    dias: Optional[int] = Field(default=None, ge=1, le=366)


class ExportarCardapioArgs(BaseModel):
    cardapio_id: Optional[str] = None
    formato: str = Field(default="xlsx", pattern=r"^(xlsx|csv|pdf|txt)$")


def _slugify_name(value: str) -> str:
    base = " ".join((value or "").split()).strip()
    if not base:
        return "FT"
    compact = "".join(ch for ch in base.upper() if ch.isalnum())
    return (compact[:10] or "FT").ljust(2, "X")


def _resolve_contrato(
    db: Session,
    ctx: CopilotContext,
    *,
    contrato_id: Optional[str] = None,
    busca_nome: Optional[str] = None,
) -> Contrato:
    query = db.query(Contrato).filter(Contrato.empresa_id == ctx.empresa_id)
    if contrato_id:
        contrato = query.filter(Contrato.id == contrato_id).first()
        if not contrato:
            raise ValueError("Contrato não encontrado no contexto atual.")
        return contrato
    if ctx.contrato_id:
        contrato = query.filter(Contrato.id == ctx.contrato_id).first()
        if contrato:
            return contrato
    if busca_nome:
        matches = query.filter(Contrato.nome.ilike(f"%{busca_nome.strip()}%")).order_by(Contrato.nome).limit(2).all()
        if not matches:
            raise ValueError(f"Nenhum contrato encontrado para '{busca_nome}'.")
        if len(matches) > 1:
            nomes = ", ".join(m.nome for m in matches)
            raise ValueError(f"Mais de um contrato encontrado: {nomes}. Informe o ID ou refine o nome.")
        return matches[0]
    raise ValueError("Informe um contrato ou selecione um contrato no contexto atual.")


def _resolve_cardapio(
    db: Session,
    ctx: CopilotContext,
    *,
    cardapio_id: Optional[str] = None,
    busca_nome: Optional[str] = None,
) -> Cardapio:
    query = db.query(Cardapio).filter(Cardapio.empresa_id == ctx.empresa_id)
    if cardapio_id:
        row = query.filter(Cardapio.id == cardapio_id).first()
        if not row:
            raise ValueError("Cardápio não encontrado no contexto atual.")
        return row
    if ctx.cardapio_id:
        row = query.filter(Cardapio.id == ctx.cardapio_id).first()
        if row:
            return row
    if busca_nome:
        matches = query.filter(Cardapio.nome.ilike(f"%{busca_nome.strip()}%")).order_by(Cardapio.created_at.desc()).limit(2).all()
        if not matches:
            raise ValueError(f"Nenhum cardápio encontrado para '{busca_nome}'.")
        if len(matches) > 1:
            nomes = ", ".join(m.nome for m in matches)
            raise ValueError(f"Mais de um cardápio encontrado: {nomes}. Informe o ID ou refine o nome.")
        return matches[0]
    raise ValueError("Informe um cardápio ou use um cardápio já carregado no contexto.")


def _resolve_ficha(
    db: Session,
    ctx: CopilotContext,
    *,
    ficha_id: Optional[str] = None,
    busca_nome: Optional[str] = None,
) -> FichaTecnica:
    query = db.query(FichaTecnica).filter(FichaTecnica.empresa_id == ctx.empresa_id)
    if ficha_id:
        row = query.filter(FichaTecnica.id == ficha_id).first()
        if not row:
            raise ValueError("Ficha técnica não encontrada no contexto atual.")
        return row
    if busca_nome:
        matches = query.filter(FichaTecnica.nome.ilike(f"%{busca_nome.strip()}%")).order_by(FichaTecnica.nome).limit(2).all()
        if not matches:
            raise ValueError(f"Nenhuma ficha técnica encontrada para '{busca_nome}'.")
        if len(matches) > 1:
            nomes = ", ".join(m.nome for m in matches)
            raise ValueError(f"Mais de uma ficha encontrada: {nomes}. Informe o ID ou refine o nome.")
        return matches[0]
    raise ValueError("Informe a ficha técnica ou um nome para localizar.")


def _resolve_ingrediente(
    db: Session,
    ctx: CopilotContext,
    *,
    ingrediente_id: Optional[str] = None,
    busca_nome: Optional[str] = None,
) -> Ingrediente:
    query = db.query(Ingrediente).filter(
        or_(Ingrediente.empresa_id == ctx.empresa_id, Ingrediente.empresa_id == None)  # noqa: E711
    )
    if ingrediente_id:
        row = query.filter(Ingrediente.id == ingrediente_id).first()
        if not row:
            raise ValueError("Ingrediente não encontrado no contexto atual.")
        return row
    if busca_nome:
        matches = query.filter(Ingrediente.nome.ilike(f"%{busca_nome.strip()}%")).order_by(Ingrediente.nome).limit(2).all()
        if not matches:
            raise ValueError(f"Nenhum ingrediente encontrado para '{busca_nome}'.")
        if len(matches) > 1:
            nomes = ", ".join(m.nome for m in matches)
            raise ValueError(f"Mais de um ingrediente encontrado: {nomes}. Informe o ID ou refine o nome.")
        return matches[0]
    raise ValueError("Informe o ingrediente ou um nome para localizar.")


def _fmt_money(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _resolve_timeout_budget_seconds() -> int:
    raw = (os.getenv("MENUAI_FAST_BUDGET_SECONDS") or "300").strip()
    try:
        return max(60, int(float(raw)))
    except ValueError:
        return 300


def _preview_cardapio_rows(cardapio: Cardapio, max_rows: int = 5) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dias = list(cardapio.dias or [])
    for dia in dias[:max_rows]:
        proteicos, acompanhamentos, saladas, finalizacao = [], [], [], []
        for ref in sorted(dia.refeicoes or [], key=lambda item: (item.ordem or 0, item.nome_prato or "")):
            cat = (ref.categoria or "").upper()
            if "PROTE" in cat:
                proteicos.append(ref.nome_prato)
            elif "SALAD" in cat:
                saladas.append(ref.nome_prato)
            elif "SOBREMESA" in cat or "FRUTA" in cat or "BEBIDA" in cat:
                finalizacao.append(ref.nome_prato)
            else:
                acompanhamentos.append(ref.nome_prato)
        rows.append(
            {
                "dia": dia.numero_dia,
                "proteicos": proteicos[:3],
                "acompanhamentos": acompanhamentos[:4],
                "saladas": saladas[:3],
                "finalizacao": finalizacao[:3],
                "custo": dia.custo_total,
            }
        )
    return rows


def _handle_buscar_ingredientes(
    db: Session,
    ctx: CopilotContext,
    args: BuscarIngredientesArgs,
) -> ToolExecutionResult:
    query = db.query(Ingrediente).filter(
        or_(Ingrediente.empresa_id == ctx.empresa_id, Ingrediente.empresa_id == None)  # noqa: E711
    )
    if args.busca:
        query = query.filter(Ingrediente.nome.ilike(f"%{args.busca.strip()}%"))
    if args.categoria:
        query = query.filter(Ingrediente.categoria == args.categoria.upper())
    if not args.incluir_inativos:
        query = query.filter(Ingrediente.ativo == True)  # noqa: E712
    rows = query.order_by(Ingrediente.nome).limit(args.limit).all()
    payload = {
        "items": [
            {
                "id": row.id,
                "nome": row.nome,
                "categoria": row.categoria,
                "unidade_medida": row.unidade_medida,
                "custo_unitario": row.custo_unitario,
                "fornecedor": row.fornecedor,
                "global": row.empresa_id is None,
            }
            for row in rows
        ],
        "total": len(rows),
    }
    if not rows:
        message = "Nao encontrei ingredientes com esses filtros."
    else:
        lines = [
            f"- **{row.nome}** (`{row.id}`) • {row.categoria} • {_fmt_money(row.custo_unitario)} / {row.unidade_medida}"
            for row in rows[:8]
        ]
        suffix = f"\n\nMostrando {len(rows)} item(ns)." if len(rows) else ""
        message = "Encontrei estes ingredientes:\n" + "\n".join(lines) + suffix
    return ToolExecutionResult("buscar_ingredientes", message, payload)


def _handle_criar_ingrediente(
    db: Session,
    ctx: CopilotContext,
    args: CriarIngredienteArgs,
) -> ToolExecutionResult:
    missing = []
    if args.custo_unitario is None:
        missing.append("custo_unitario")
    if missing:
        return ToolExecutionResult(
            "criar_ingrediente",
            "Consigo criar o ingrediente, mas ainda falta `custo_unitario`. Envie esse valor para concluir.",
            {"status": "needs_input", "missing_fields": missing},
        )

    row = Ingrediente(
        id=str(uuid.uuid4()),
        empresa_id=ctx.empresa_id,
        codigo=args.codigo,
        nome=args.nome.strip(),
        categoria=args.categoria.upper(),
        custo_unitario=float(args.custo_unitario),
        unidade_medida=args.unidade_medida,
        fornecedor=args.fornecedor,
        fator_correcao=float(args.fator_correcao),
        ativo=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    payload = {
        "status": "created",
        "item": {
            "id": row.id,
            "nome": row.nome,
            "categoria": row.categoria,
            "custo_unitario": row.custo_unitario,
            "unidade_medida": row.unidade_medida,
        },
    }
    return ToolExecutionResult(
        "criar_ingrediente",
        f"Ingrediente **{row.nome}** cadastrado com sucesso em `{row.categoria}` por {_fmt_money(row.custo_unitario)} / {row.unidade_medida}.",
        payload,
    )


def _handle_editar_ingrediente(
    db: Session,
    ctx: CopilotContext,
    args: EditarIngredienteArgs,
) -> ToolExecutionResult:
    row = _resolve_ingrediente(db, ctx, ingrediente_id=args.ingrediente_id, busca_nome=args.busca_nome)
    if row.empresa_id is None and ctx.usuario.role != "super_admin":
        raise ValueError("Apenas super_admin pode editar ingredientes globais.")
    updates = args.model_dump(exclude_unset=True, exclude={"ingrediente_id", "busca_nome"})
    if not updates:
        return ToolExecutionResult(
            "editar_ingrediente",
            f"Encontrei o ingrediente **{row.nome}** (`{row.id}`), mas nenhum campo de atualização foi informado.",
            {"status": "needs_input", "item": {"id": row.id, "nome": row.nome}},
        )
    for field_name, value in updates.items():
        if field_name == "categoria" and value:
            value = str(value).upper()
        setattr(row, field_name, value)
    db.commit()
    db.refresh(row)
    payload = {
        "status": "updated",
        "item": {
            "id": row.id,
            "nome": row.nome,
            "categoria": row.categoria,
            "custo_unitario": row.custo_unitario,
            "unidade_medida": row.unidade_medida,
            "ativo": row.ativo,
        },
    }
    return ToolExecutionResult(
        "editar_ingrediente",
        f"Ingrediente **{row.nome}** atualizado com sucesso.",
        payload,
    )


def _handle_buscar_fichas(
    db: Session,
    ctx: CopilotContext,
    args: BuscarFichasArgs,
) -> ToolExecutionResult:
    query = db.query(FichaTecnica).filter(FichaTecnica.empresa_id == ctx.empresa_id)
    if args.busca:
        query = query.filter(FichaTecnica.nome.ilike(f"%{args.busca.strip()}%"))
    if args.categoria:
        query = query.filter(FichaTecnica.categoria.ilike(f"%{args.categoria.strip()}%"))
    if args.vegana is not None:
        query = query.filter(FichaTecnica.vegana == args.vegana)
    if args.vegetariana is not None:
        query = query.filter(FichaTecnica.vegetariana == args.vegetariana)
    if args.custo_max is not None:
        query = query.filter(FichaTecnica.custo_porcao <= args.custo_max)
    rows = query.order_by(FichaTecnica.categoria, FichaTecnica.nome).limit(args.limit).all()
    payload = {
        "items": [
            {
                "id": row.id,
                "codigo": row.codigo,
                "nome": row.nome,
                "categoria": row.categoria,
                "custo_porcao": row.custo_porcao,
                "vegetariana": row.vegetariana,
                "vegana": row.vegana,
            }
            for row in rows
        ],
        "total": len(rows),
    }
    if not rows:
        message = "Nao encontrei fichas tecnicas com esses filtros."
    else:
        lines = [
            f"- **{row.nome}** (`{row.codigo}`) • {row.categoria} • custo/porcao {_fmt_money(row.custo_porcao)}"
            for row in rows[:8]
        ]
        message = "Encontrei estas fichas tecnicas:\n" + "\n".join(lines)
    return ToolExecutionResult("buscar_fichas", message, payload)


def _apply_ficha_ingredientes(
    db: Session,
    ficha: FichaTecnica,
    ingredientes: list[FichaIngredienteInput],
) -> None:
    db.query(FichaIngrediente).filter(FichaIngrediente.ficha_tecnica_id == ficha.id).delete()
    for index, item in enumerate(ingredientes):
        ing = db.query(Ingrediente).filter(Ingrediente.id == item.ingrediente_id).first()
        if not ing:
            raise ValueError(f"Ingrediente '{item.ingrediente_id}' não encontrado.")
        db.add(
            FichaIngrediente(
                id=str(uuid.uuid4()),
                ficha_tecnica_id=ficha.id,
                ingrediente_id=item.ingrediente_id,
                quantidade_bruta_g=item.quantidade_bruta_g,
                fator_correcao=item.fator_correcao,
                ordem=index,
                observacao=item.observacao,
            )
        )
    db.flush()
    db.refresh(ficha)
    _calcular_ficha(ficha, db)


def _handle_criar_ficha(
    db: Session,
    ctx: CopilotContext,
    args: CriarFichaArgs,
) -> ToolExecutionResult:
    if not args.codigo:
        return ToolExecutionResult(
            "criar_ficha",
            "Consigo criar a ficha, mas preciso de um `codigo` interno para ela.",
            {"status": "needs_input", "missing_fields": ["codigo"]},
        )
    if not args.ingredientes:
        return ToolExecutionResult(
            "criar_ficha",
            "Para cadastrar a ficha eu preciso da lista de ingredientes com `ingrediente_id` e `quantidade_bruta_g`.",
            {"status": "needs_input", "missing_fields": ["ingredientes"]},
        )
    exists = (
        db.query(FichaTecnica)
        .filter(FichaTecnica.empresa_id == ctx.empresa_id, FichaTecnica.codigo == args.codigo)
        .first()
    )
    if exists:
        raise ValueError(f"Já existe uma ficha com código '{args.codigo}'.")
    ficha = FichaTecnica(
        id=str(uuid.uuid4()),
        empresa_id=ctx.empresa_id,
        codigo=args.codigo,
        nome=args.nome.strip(),
        categoria=args.categoria.strip(),
        rendimento_porcoes=args.rendimento_porcoes,
        peso_porcao_g=args.peso_porcao_g,
        modo_preparo=args.modo_preparo,
        observacoes=args.observacoes,
        ativo=True,
    )
    db.add(ficha)
    db.flush()
    _apply_ficha_ingredientes(db, ficha, args.ingredientes)
    db.commit()
    db.refresh(ficha)
    sync_knowledge_safe(sync_ficha_document, db, ficha)
    db.commit()
    payload = {
        "status": "created",
        "item": {
            "id": ficha.id,
            "codigo": ficha.codigo,
            "nome": ficha.nome,
            "categoria": ficha.categoria,
            "custo_porcao": ficha.custo_porcao,
        },
    }
    return ToolExecutionResult(
        "criar_ficha",
        f"Ficha técnica **{ficha.nome}** (`{ficha.codigo}`) criada com custo/porção {_fmt_money(ficha.custo_porcao)}.",
        payload,
    )


def _handle_editar_ficha(
    db: Session,
    ctx: CopilotContext,
    args: EditarFichaArgs,
) -> ToolExecutionResult:
    ficha = _resolve_ficha(db, ctx, ficha_id=args.ficha_id, busca_nome=args.busca_nome)
    updates = args.model_dump(exclude_unset=True, exclude={"ficha_id", "busca_nome", "ingredientes"})
    if not updates and args.ingredientes is None:
        return ToolExecutionResult(
            "editar_ficha",
            f"Encontrei a ficha **{ficha.nome}** (`{ficha.codigo}`), mas nenhum campo de atualização foi informado.",
            {"status": "needs_input", "item": {"id": ficha.id, "codigo": ficha.codigo, "nome": ficha.nome}},
        )
    for field_name, value in updates.items():
        setattr(ficha, field_name, value)
    if args.ingredientes is not None:
        _apply_ficha_ingredientes(db, ficha, args.ingredientes)
    db.commit()
    db.refresh(ficha)
    sync_knowledge_safe(sync_ficha_document, db, ficha)
    db.commit()
    payload = {
        "status": "updated",
        "item": {
            "id": ficha.id,
            "codigo": ficha.codigo,
            "nome": ficha.nome,
            "categoria": ficha.categoria,
            "custo_porcao": ficha.custo_porcao,
            "ativo": ficha.ativo,
        },
    }
    return ToolExecutionResult(
        "editar_ficha",
        f"Ficha técnica **{ficha.nome}** atualizada com sucesso.",
        payload,
    )


def _handle_buscar_contratos(
    db: Session,
    ctx: CopilotContext,
    args: BuscarContratosArgs,
) -> ToolExecutionResult:
    query = db.query(Contrato).filter(Contrato.empresa_id == ctx.empresa_id)
    if args.busca:
        query = query.filter(Contrato.nome.ilike(f"%{args.busca.strip()}%"))
    if args.ativo is not None:
        query = query.filter(Contrato.ativo == args.ativo)
    rows = query.order_by(Contrato.nome).limit(args.limit).all()
    payload = {
        "items": [
            {
                "id": row.id,
                "nome": row.nome,
                "numero_contrato": row.numero_contrato,
                "ativo": row.ativo,
                "analisado": bool(row.regras_json and not analysis_looks_invalid(row.regras_json)),
            }
            for row in rows
        ],
        "total": len(rows),
    }
    if not rows:
        message = "Nao encontrei contratos com esses filtros."
    else:
        lines = [
            f"- **{row.nome}** (`{row.id}`) • analise {'ok' if row.regras_json and not analysis_looks_invalid(row.regras_json) else 'pendente'}"
            for row in rows[:8]
        ]
        message = "Encontrei estes contratos:\n" + "\n".join(lines)
    return ToolExecutionResult("buscar_contratos", message, payload)


def _handle_analisar_contrato(
    db: Session,
    ctx: CopilotContext,
    args: AnalisarContratoArgs,
) -> ToolExecutionResult:
    contrato = _resolve_contrato(db, ctx, contrato_id=args.contrato_id, busca_nome=args.busca_nome)
    if not contrato.arquivo_path:
        raise ValueError("O contrato selecionado não possui arquivo carregado.")
    extraction = extract_contract_text(contrato.arquivo_path)
    if not extraction.ok or extraction.total_chars < 300:
        raise ValueError(build_contract_extraction_error(extraction))
    if contrato.regras_json and not args.force and not analysis_looks_invalid(contrato.regras_json):
        regras = contrato.regras_json
    else:
        assert_llm_model_allowed_for_generation(db, args.llm_model)
        from pipeline.orchestrator import MenuOrchestrator

        crew = MenuOrchestrator(
            contrato_path=contrato.arquivo_path,
            dias=30,
            target_custo_total=contrato.custo_total_max or 10.00,
            target_custo_proteico=contrato.custo_proteico_max or 3.50,
            restricoes_usuario="",
            refeicoes=None,
            empresa_id=str(contrato.empresa_id),
            contrato_id=str(contrato.id),
            db_disponivel=True,
            llm_model_id=args.llm_model,
        )
        regras = crew.analisar_contrato_apenas()
        if not isinstance(regras, dict):
            regras = {"texto": str(regras)}
        if regras.get("erro"):
            raise ValueError(str(regras.get("erro")))
        if analysis_looks_invalid(regras):
            raise ValueError("A análise retornou conteúdo sem base documental suficiente.")
        contrato.regras_json = regras
        contrato.gramaturas_json = regras.get("gramaturas", contrato.gramaturas_json)
        contrato.incidencias_json = regras.get("incidencias", contrato.incidencias_json)
        contrato.proibicoes_json = regras.get("proibicoes", contrato.proibicoes_json)
        contrato.estrutura_refeicao = regras.get("estrutura", contrato.estrutura_refeicao)
        contrato.observacoes = regras.get("observacoes", contrato.observacoes)
        db.commit()
        db.refresh(contrato)
        sync_knowledge_safe(sync_contrato_document, db, contrato)
        db.commit()
    payload = {
        "status": "analisado",
        "contrato": {
            "id": contrato.id,
            "nome": contrato.nome,
            "numero_contrato": contrato.numero_contrato,
        },
        "regras": regras,
    }
    dietas = regras.get("dietas_especiais", []) if isinstance(regras, dict) else []
    message = (
        f"Analisei o contrato **{contrato.nome}**. "
        f"Refeições/dia: `{contrato.num_refeicoes_dia}`. "
        f"Dietas especiais detectadas: `{', '.join(dietas) if dietas else 'nenhuma'}`."
    )
    return ToolExecutionResult(
        "analisar_contrato",
        message,
        payload,
        context_updates={"contrato_id": contrato.id},
    )


def _handle_listar_cardapios(
    db: Session,
    ctx: CopilotContext,
    args: ListarCardapiosArgs,
) -> ToolExecutionResult:
    query = db.query(Cardapio).filter(Cardapio.empresa_id == ctx.empresa_id)
    if args.status:
        query = query.filter(Cardapio.status == args.status)
    if args.contrato_id:
        query = query.filter(Cardapio.contrato_id == args.contrato_id)
    rows = query.order_by(Cardapio.created_at.desc()).limit(args.limit).all()
    payload = {
        "items": [
            {
                "id": row.id,
                "nome": row.nome,
                "status": row.status,
                "num_dias": row.num_dias,
                "custo_medio_dia": row.custo_medio_dia,
                "review_status": (row.parametros_json or {}).get("review_status"),
                "degraded_generation": bool((row.parametros_json or {}).get("degraded_generation")),
            }
            for row in rows
        ],
        "total": len(rows),
    }
    if not rows:
        message = "Nao encontrei cardapios com esses filtros."
    else:
        lines = [
            f"- **{row.nome}** (`{row.id}`) • {row.status} • {row.num_dias or 0} dias • custo medio {_fmt_money(row.custo_medio_dia)}"
            for row in rows[:8]
        ]
        message = "Encontrei estes cardápios:\n" + "\n".join(lines)
    return ToolExecutionResult("listar_cardapios", message, payload)


def _handle_ver_cardapio(
    db: Session,
    ctx: CopilotContext,
    args: VerCardapioArgs,
) -> ToolExecutionResult:
    row = _resolve_cardapio(db, ctx, cardapio_id=args.cardapio_id, busca_nome=args.busca_nome)
    preview = _preview_cardapio_rows(row)
    payload = {
        "item": {
            "id": row.id,
            "nome": row.nome,
            "status": row.status,
            "num_dias": row.num_dias,
            "custo_medio_dia": row.custo_medio_dia,
            "preview": preview,
            "review_status": (row.parametros_json or {}).get("review_status"),
            "review_summary": (row.parametros_json or {}).get("review_summary"),
            "degraded_generation": bool((row.parametros_json or {}).get("degraded_generation")),
        }
    }
    lines = [
        f"- Dia {item['dia']}: proteicos {', '.join(item['proteicos']) or '—'}; acompanhamentos {', '.join(item['acompanhamentos']) or '—'}"
        for item in preview
    ]
    message = (
        f"**{row.nome}** • status `{row.status}` • {row.num_dias or 0} dias • custo medio {_fmt_money(row.custo_medio_dia)}.\n"
        + ("\n".join(lines) if lines else "Sem linhas de prévia disponíveis.")
    )
    return ToolExecutionResult(
        "ver_cardapio",
        message,
        payload,
        context_updates={"cardapio_id": row.id},
    )


def _handle_aprovar_cardapio(
    db: Session,
    ctx: CopilotContext,
    args: AprovarCardapioArgs,
) -> ToolExecutionResult:
    row = _resolve_cardapio(db, ctx, cardapio_id=args.cardapio_id)
    approval = AprovacaoCardapio(
        id=str(uuid.uuid4()),
        cardapio_id=row.id,
        aprovado_por_id=str(ctx.usuario.id),
        status="aprovado",
        comentario=args.comentario,
        created_at=datetime.utcnow(),
    )
    db.add(approval)
    row.status = "aprovado"
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    sync_knowledge_safe(sync_cardapio_document, db, row)
    db.commit()
    payload = {
        "status": "approved",
        "cardapio": {"id": row.id, "nome": row.nome, "status": row.status},
    }
    return ToolExecutionResult(
        "aprovar_cardapio",
        f"Cardápio **{row.nome}** aprovado com sucesso.",
        payload,
        context_updates={"cardapio_id": row.id},
    )


def _handle_exportar_cardapio(
    db: Session,
    ctx: CopilotContext,
    args: ExportarCardapioArgs,
) -> ToolExecutionResult:
    row = _resolve_cardapio(db, ctx, cardapio_id=args.cardapio_id)
    payload = {
        "status": "ready",
        "cardapio": {"id": row.id, "nome": row.nome},
        "formato": args.formato,
        "download_url": f"/api/cardapios/{row.id}/exportar?formato={args.formato}",
    }
    return ToolExecutionResult(
        "exportar_cardapio",
        f"O arquivo de **{row.nome}** está pronto para exportação em `{args.formato.upper()}`: `{payload['download_url']}`.",
        payload,
        context_updates={"cardapio_id": row.id},
    )


def _handle_gerar_novamente_cardapio(
    db: Session,
    ctx: CopilotContext,
    args: GerarNovamenteCardapioArgs,
) -> ToolExecutionResult:
    row = _resolve_cardapio(db, ctx, cardapio_id=args.cardapio_id)
    if not row.contrato_id:
        raise ValueError("O cardápio selecionado não possui contrato vinculado para regeneração.")

    params = dict(row.parametros_json or {})
    dias = int(args.dias or params.get("dias") or row.num_dias or 30)
    llm_model = str(args.llm_model or params.get("generator_model_used") or params.get("llm_model") or "").strip() or None
    review_llm_model = str(
        args.review_llm_model or params.get("review_model_used") or params.get("review_model_id") or params.get("review_llm_model") or ""
    ).strip() or None
    restricoes_usuario = str(params.get("restricoes_usuario") or "").strip()
    refeicoes = params.get("refeicoes")
    if not isinstance(refeicoes, list):
        refeicoes = None
    target_custo_total = float(params.get("target_custo_total") or row.custo_medio_dia or 10.0)
    target_custo_proteico = float(params.get("target_custo_proteico") or 3.5)

    assert_llm_model_allowed_for_generation(db, llm_model)
    assert_llm_model_allowed_for_review(db, review_llm_model)

    timeout_budget_seconds = _resolve_timeout_budget_seconds()
    job_id = str(uuid.uuid4())[:8]
    now_iso = datetime.utcnow().isoformat()
    now_ts = time.time()
    payload_config = {
        "dias": dias,
        "contrato_id": str(row.contrato_id),
        "target_custo_total": target_custo_total,
        "target_custo_proteico": target_custo_proteico,
        "restricoes_usuario": restricoes_usuario,
        "refeicoes": refeicoes,
        "nome_cardapio": f"{row.nome} — revisão",
        "llm_model": llm_model,
        "review_llm_model": review_llm_model,
        "review_enabled": True,
        "review_strategy": "consultive",
        "generation_mode": "fast",
        "contrato_analise_confirmada": True,
        "timeout_budget_seconds": timeout_budget_seconds,
        "source_cardapio_id": str(row.id),
        "generator_agent_id": params.get("generator_agent_id"),
        "reviewer_agent_id": params.get("reviewer_agent_id"),
        "agent_bindings": params.get("agent_bindings") if isinstance(params.get("agent_bindings"), dict) else {},
    }

    job_state.jobs[job_id] = {
        "status": "iniciando",
        "progress": 0,
        "logs": [],
        "result": None,
        "error": None,
        "error_type": None,
        "timeout_reason": None,
        "config": payload_config,
        "started_at": now_iso,
        "last_update_at": now_iso,
        "started_ts": now_ts,
        "last_update_ts": now_ts,
        "current_step": "iniciando",
        "timeout_budget_seconds": timeout_budget_seconds,
    }
    job_state.job_queues[job_id] = queue.Queue()

    job_db = JobAgente(
        job_id=job_id,
        empresa_id=ctx.empresa_id,
        status="iniciando",
        progresso=0,
        parametros_json=payload_config,
        iniciado_em=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        criado_por_id=(str(getattr(ctx.usuario, "id", "")) or None),
    )
    db.add(job_db)
    db.commit()

    launch_generation_job(
        job_id,
        dias,
        target_custo_total,
        target_custo_proteico,
        restricoes_usuario,
        refeicoes,
        ctx.empresa_id,
        str(row.contrato_id),
        f"{row.nome} — revisão",
        llm_model,
        review_llm_model,
        True,
        "consultive",
        "fast",
        upload_dir=UPLOAD_DIR,
        db_ok=True,
        contrato_analise_confirmada=True,
        agent_bindings=payload_config.get("agent_bindings") if isinstance(payload_config.get("agent_bindings"), dict) else None,
    )

    payload = {
        "status": "started",
        "job_id": job_id,
        "dias": dias,
        "contrato_id": str(row.contrato_id),
        "cardapio_origem_id": str(row.id),
        "llm_model": llm_model,
        "review_llm_model": review_llm_model,
        "generator_agent_id": params.get("generator_agent_id"),
        "reviewer_agent_id": params.get("reviewer_agent_id"),
        "generation_mode": "fast",
        "timeout_budget_seconds": timeout_budget_seconds,
    }
    agent_bindings = payload_config.get("agent_bindings") if isinstance(payload_config.get("agent_bindings"), dict) else {}
    generator_agent_name = str(((agent_bindings or {}).get("generator") or {}).get("profile_name") or llm_model or "default")
    reviewer_agent_name = str(((agent_bindings or {}).get("reviewer") or {}).get("profile_name") or review_llm_model or "default")
    return ToolExecutionResult(
        "gerar_novamente_cardapio",
        (
            f"Iniciei uma nova geração a partir de **{row.nome}**. "
            f"Agente gerador: `{generator_agent_name}` • Agente revisor: `{reviewer_agent_name}` • {dias} dias."
        ),
        payload,
        context_updates={
            "job_id": job_id,
            "contrato_id": str(row.contrato_id),
            "cardapio_id": None,
        },
    )


TOOLS: dict[str, CopilotTool] = {
    "buscar_ingredientes": CopilotTool(
        name="buscar_ingredientes",
        description="Consulta ingredientes do produto por nome, categoria e status.",
        input_model=BuscarIngredientesArgs,
        handler=_handle_buscar_ingredientes,
    ),
    "criar_ingrediente": CopilotTool(
        name="criar_ingrediente",
        description="Cria ingrediente novo quando os campos necessários estiverem completos.",
        input_model=CriarIngredienteArgs,
        handler=_handle_criar_ingrediente,
        mutation=True,
    ),
    "editar_ingrediente": CopilotTool(
        name="editar_ingrediente",
        description="Atualiza dados de um ingrediente existente.",
        input_model=EditarIngredienteArgs,
        handler=_handle_editar_ingrediente,
        mutation=True,
    ),
    "buscar_fichas": CopilotTool(
        name="buscar_fichas",
        description="Consulta fichas técnicas por nome, categoria e filtros operacionais.",
        input_model=BuscarFichasArgs,
        handler=_handle_buscar_fichas,
    ),
    "criar_ficha": CopilotTool(
        name="criar_ficha",
        description="Cria uma ficha técnica nova quando o payload estiver completo, ou orienta o preenchimento que falta.",
        input_model=CriarFichaArgs,
        handler=_handle_criar_ficha,
        mutation=True,
    ),
    "editar_ficha": CopilotTool(
        name="editar_ficha",
        description="Atualiza uma ficha técnica existente de forma segura.",
        input_model=EditarFichaArgs,
        handler=_handle_editar_ficha,
        mutation=True,
    ),
    "buscar_contratos": CopilotTool(
        name="buscar_contratos",
        description="Lista contratos da empresa e indica se já possuem análise.",
        input_model=BuscarContratosArgs,
        handler=_handle_buscar_contratos,
    ),
    "analisar_contrato": CopilotTool(
        name="analisar_contrato",
        description="Executa ou reaproveita a análise de um contrato no contexto atual.",
        input_model=AnalisarContratoArgs,
        handler=_handle_analisar_contrato,
        mutation=True,
    ),
    "listar_cardapios": CopilotTool(
        name="listar_cardapios",
        description="Lista cardápios da empresa por status e contrato.",
        input_model=ListarCardapiosArgs,
        handler=_handle_listar_cardapios,
    ),
    "ver_cardapio": CopilotTool(
        name="ver_cardapio",
        description="Abre um resumo operacional de um cardápio específico.",
        input_model=VerCardapioArgs,
        handler=_handle_ver_cardapio,
    ),
    "aprovar_cardapio": CopilotTool(
        name="aprovar_cardapio",
        description="Aprova um cardápio existente no contexto atual.",
        input_model=AprovarCardapioArgs,
        handler=_handle_aprovar_cardapio,
        mutation=True,
    ),
    "gerar_novamente_cardapio": CopilotTool(
        name="gerar_novamente_cardapio",
        description="Prepara os parâmetros para regenerar um cardápio existente.",
        input_model=GerarNovamenteCardapioArgs,
        handler=_handle_gerar_novamente_cardapio,
    ),
    "exportar_cardapio": CopilotTool(
        name="exportar_cardapio",
        description="Retorna a URL de exportação de um cardápio em xlsx, csv, pdf ou txt.",
        input_model=ExportarCardapioArgs,
        handler=_handle_exportar_cardapio,
    ),
}


def build_openai_tool_specs(allowed_tool_names: Optional[Iterable[str]] = None) -> list[dict[str, Any]]:
    allowed = set(allowed_tool_names) if allowed_tool_names else set(TOOLS.keys())
    return [tool.openai_schema() for name, tool in TOOLS.items() if name in allowed]


def execute_tool(
    db: Session,
    ctx: CopilotContext,
    tool_name: str,
    raw_args: dict[str, Any],
    *,
    allowed_tool_names: Optional[Iterable[str]] = None,
) -> ToolExecutionResult:
    allowed = set(allowed_tool_names) if allowed_tool_names else set(TOOLS.keys())
    if tool_name not in allowed:
        raise ValueError(f"Tool '{tool_name}' não está permitida para o agente ativo.")
    tool = TOOLS.get(tool_name)
    if tool is None:
        raise ValueError(f"Tool '{tool_name}' não registrada.")
    started_at = time.perf_counter()
    parsed = tool.input_model.model_validate(raw_args or {})
    try:
        result = tool.handler(db, ctx, parsed)
        logger.info(
            "tool_event=%s",
            json.dumps(
                {
                    "tool_name": tool_name,
                    "sessao_id": ctx.sessao_id,
                    "empresa_id": ctx.empresa_id,
                    "page_context": ctx.page_context,
                    "mutation": tool.mutation,
                    "success": True,
                    "latency_ms": int((time.perf_counter() - started_at) * 1000),
                },
                ensure_ascii=False,
                default=str,
            ),
        )
        return result
    except Exception as exc:
        logger.warning(
            "tool_event=%s",
            json.dumps(
                {
                    "tool_name": tool_name,
                    "sessao_id": ctx.sessao_id,
                    "empresa_id": ctx.empresa_id,
                    "page_context": ctx.page_context,
                    "mutation": tool.mutation,
                    "success": False,
                    "latency_ms": int((time.perf_counter() - started_at) * 1000),
                    "error": str(exc)[:500],
                },
                ensure_ascii=False,
                default=str,
            ),
        )
        raise


def _extract_search_hint(
    text: str,
    *,
    noun_variants: tuple[str, ...],
) -> Optional[str]:
    normalized = " ".join((text or "").strip().lower().split())
    if not normalized:
        return None
    generic_verbs = ("buscar", "busque", "listar", "liste", "consultar", "consulte", "mostrar", "mostre", "ver")
    generic_fillers = (
        "recente",
        "recentes",
        "ativo",
        "ativos",
        "ativas",
        "disponivel",
        "disponiveis",
        "cadastrado",
        "cadastrados",
        "cadastrada",
        "cadastradas",
    )
    tokens = [tok for tok in re.split(r"[^a-z0-9à-ÿ]+", normalized) if tok]
    filtered = [
        tok
        for tok in tokens
        if tok not in generic_verbs
        and tok not in generic_fillers
        and all(noun not in tok for noun in noun_variants)
    ]
    hint = " ".join(filtered).strip()
    return hint or None


def fallback_route_from_text(
    text: str,
    ctx: CopilotContext,
    allowed_tool_names: Optional[Iterable[str]] = None,
) -> tuple[Optional[str], dict[str, Any]]:
    allowed = set(allowed_tool_names) if allowed_tool_names else set(TOOLS.keys())
    normalized = " ".join((text or "").strip().lower().split())
    if not normalized:
        return None, {}

    def allowed_result(tool_name: str, args: dict[str, Any]) -> tuple[Optional[str], dict[str, Any]]:
        if tool_name not in allowed:
            return None, {}
        return tool_name, args

    if "aprovar" in normalized and "cardap" in normalized:
        return allowed_result("aprovar_cardapio", {"cardapio_id": ctx.cardapio_id})

    if ("gerar novamente" in normalized or "regener" in normalized) and "cardap" in normalized:
        return allowed_result("gerar_novamente_cardapio", {"cardapio_id": ctx.cardapio_id})

    if "export" in normalized and "cardap" in normalized:
        formato = "xlsx"
        for candidate in ("pdf", "csv", "txt", "xlsx"):
            if candidate in normalized:
                formato = candidate
                break
        return allowed_result("exportar_cardapio", {"cardapio_id": ctx.cardapio_id, "formato": formato})

    if "analis" in normalized and "contrat" in normalized:
        return allowed_result("analisar_contrato", {"contrato_id": ctx.contrato_id})

    if "ingred" in normalized and any(token in normalized for token in ("buscar", "listar", "consult", "mostrar")):
        return allowed_result("buscar_ingredientes", {
            "busca": _extract_search_hint(text, noun_variants=("ingred",)),
            "limit": 12,
        })

    if "ficha" in normalized and any(token in normalized for token in ("buscar", "listar", "consult", "mostrar")):
        return allowed_result("buscar_fichas", {
            "busca": _extract_search_hint(text, noun_variants=("ficha", "fichas", "tecnica", "tecnicas")),
            "limit": 12,
        })

    if "contrat" in normalized and any(token in normalized for token in ("buscar", "listar", "consult", "mostrar")):
        return allowed_result("buscar_contratos", {
            "busca": _extract_search_hint(text, noun_variants=("contrat", "contrato", "contratos")),
            "limit": 12,
        })

    if "cardap" in normalized and any(token in normalized for token in ("listar", "mostrar")):
        return allowed_result("listar_cardapios", {"limit": 12})

    if "ver" in normalized and "cardap" in normalized:
        return allowed_result("ver_cardapio", {"cardapio_id": ctx.cardapio_id})

    return None, {}
