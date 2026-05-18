"""Geração rápida de cardápios com uma chamada LLM e validação determinística."""
from __future__ import annotations

import json
import logging
import os
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session


OUTPUT_COLUMNS = [
    "Dia",
    "Refeição",
    "Pão",
    "Recheio 1",
    "% Consumo Recheio 1",
    "Recheio 2",
    "% Consumo Recheio 2",
    "Acompanhamento Café",
    "Bebida Café",
    "Fruta Café",
    "Prato Proteico Principal",
    "% Consumo Principal",
    "Opção Proteica 2",
    "% Consumo Opção 2",
    "Opção Proteica 3",
    "% Consumo Opção 3",
    "Arroz",
    "Feijão",
    "Guarnição 1",
    "Guarnição 2",
    "Salada Grãos",
    "Salada Crua",
    "Salada Cozida",
    "Salada Folhosa/Elaborada",
    "Sobremesa",
    "Bebida",
    "Fruta",
    "Tema Especial",
    "Custo Gerencial (R$)",
]

SLOT_BUCKETS = {
    "Pão": "paes",
    "Recheio 1": "recheios",
    "Recheio 2": "recheios",
    "Acompanhamento Café": "acompanhamentos_cafe",
    "Bebida Café": "bebidas",
    "Fruta Café": "frutas",
    "Prato Proteico Principal": "proteicos",
    "Opção Proteica 2": "proteicos",
    "Opção Proteica 3": "proteicos",
    "Arroz": "arroz",
    "Feijão": "feijao",
    "Guarnição 1": "guarnicoes",
    "Guarnição 2": "guarnicoes",
    "Salada Grãos": "saladas_graos",
    "Salada Crua": "saladas_cruas",
    "Salada Cozida": "saladas_cozidas",
    "Salada Folhosa/Elaborada": "saladas_elaboradas",
    "Sobremesa": "sobremesas",
    "Bebida": "bebidas",
    "Fruta": "frutas",
}

PERCENT_COLUMNS = {
    "% Consumo Recheio 1",
    "% Consumo Recheio 2",
    "% Consumo Principal",
    "% Consumo Opção 2",
    "% Consumo Opção 3",
}

BREAKFAST_FIELDS = {
    "Pão",
    "Recheio 1",
    "% Consumo Recheio 1",
    "Recheio 2",
    "% Consumo Recheio 2",
    "Acompanhamento Café",
    "Bebida Café",
    "Fruta Café",
}

MEAL_FIELDS = set(SLOT_BUCKETS) - {
    "Pão",
    "Recheio 1",
    "Recheio 2",
    "Acompanhamento Café",
    "Bebida Café",
    "Fruta Café",
}

REFEICAO_LABELS = {
    "cafe_manha": "Café da manhã",
    "lanche_manha": "Lanche da manhã",
    "almoco": "Almoço",
    "lanche_tarde": "Lanche da tarde",
    "jantar": "Jantar",
    "ceia": "Ceia",
}

SPECIAL_THEMES = [
    "-",
    "Bella Massa",
    "-",
    "-",
    "Regional",
    "Fast Food",
    "-",
    "-",
    "Oriental",
]

logger = logging.getLogger("menuai.fast_generation")


class FastGenerationTimeout(RuntimeError):
    """Erro explícito para timeout de orçamento da geração rápida."""

    def __init__(self, message: str, timeout_reason: str):
        super().__init__(message)
        self.timeout_reason = timeout_reason
        self.error_type = "timeout_budget_exceeded"


@dataclass(frozen=True)
class Candidate:
    id: str
    codigo: str
    nome: str
    categoria: str
    custo: float
    vegetariana: bool
    vegana: bool
    gluten: bool
    lactose: bool


def _norm(text: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = raw.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def _clean_cell(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or "-"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).replace("%", "").replace(",", ".").strip()
        if not text or text == "-":
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def _bucket_for(category: str, name: str) -> str:
    cat = _norm(category)
    nome = _norm(name)
    if "pao" in cat or "pao" in nome or "broa" in nome:
        return "paes"
    if "recheio" in cat or "manteiga" in nome or "margarina" in nome or "ricota" in nome or "queijo" in nome:
        return "recheios"
    if "bebida" in cat or "suco" in nome or "cafe" in nome or "leite" in nome or "cha" in nome:
        return "bebidas"
    if "sobremesa" in cat or "fruta" in cat or "doce" in cat:
        if "fruta" in cat or any(fruit in nome for fruit in ("banana", "maca", "melao", "mamao", "melancia", "manga", "laranja")):
            return "frutas"
        return "sobremesas"
    if "cafe" in cat or "desjejum" in cat or "lanche" in cat or "bolo" in nome or "mingau" in nome or "cuscuz" in nome:
        return "acompanhamentos_cafe"
    if "arroz" in cat or "arroz" in nome:
        return "arroz"
    if "feij" in cat or "feij" in nome:
        return "feijao"
    if "salada" in cat:
        if "grao" in cat or "graos" in cat or "grao" in nome or "fradinho" in nome:
            return "saladas_graos"
        if "coz" in cat or "cozid" in nome or "beterraba" in nome or "abobora" in nome or "chuchu" in nome:
            return "saladas_cozidas"
        if "elabor" in cat or "folh" in cat or "grao" in nome or "macarronese" in nome or "caprese" in nome:
            return "saladas_elaboradas"
        return "saladas_cruas"
    if (
        "guarn" in cat
        or "arroz" in cat
        or "feij" in cat
        or "acompanhamento" in cat
        or "massa" in cat
    ):
        return "guarnicoes"
    if (
        "prot" in cat
        or "carne" in cat
        or "frango" in cat
        or "peixe" in cat
        or "ovo" in cat
        or "suino" in cat
    ):
        return "proteicos"
    return "outros"


def _catalog_snapshot(db: Session, empresa_id: str, max_per_bucket: int = 80) -> dict[str, list[Candidate]]:
    from database.models import FichaTecnica

    buckets: dict[str, list[Candidate]] = {
        "paes": [],
        "recheios": [],
        "acompanhamentos_cafe": [],
        "bebidas": [],
        "frutas": [],
        "proteicos": [],
        "arroz": [],
        "feijao": [],
        "guarnicoes": [],
        "saladas_graos": [],
        "saladas_cruas": [],
        "saladas_cozidas": [],
        "saladas_elaboradas": [],
        "sobremesas": [],
        "outros": [],
    }
    rows = (
        db.query(FichaTecnica)
        .filter(FichaTecnica.empresa_id == empresa_id, FichaTecnica.ativo == True)
        .order_by(FichaTecnica.categoria.asc(), FichaTecnica.custo_porcao.asc(), FichaTecnica.nome.asc())
        .all()
    )
    for f in rows:
        bucket = _bucket_for(f.categoria, f.nome)
        if len(buckets[bucket]) >= max_per_bucket:
            continue
        buckets[bucket].append(
            Candidate(
                id=str(f.id),
                codigo=f.codigo or "",
                nome=f.nome or "",
                categoria=f.categoria or "",
                custo=float(f.custo_porcao or 0),
                vegetariana=bool(f.vegetariana),
                vegana=bool(f.vegana),
                gluten=bool(f.contem_gluten),
                lactose=bool(f.contem_lactose),
            )
        )
    return buckets


def _candidate_for(bucket: list[Candidate], index: int) -> Optional[Candidate]:
    if not bucket:
        return None
    return bucket[index % len(bucket)]


def _is_breakfast_ref(ref: str) -> bool:
    norm = _norm(ref)
    return norm in {"cafe manha", "cafe da manha", "desjejum", "lanche manha"}


def _candidate_cost(catalog: dict[str, list[Candidate]], name: Any) -> float:
    needle = _norm(name)
    if not needle or needle == "-":
        return 0.0
    for items in catalog.values():
        for item in items:
            if _norm(item.nome) == needle or (item.codigo and _norm(item.codigo) == needle):
                return float(item.custo or 0)
    return 0.0


def _apply_consumption_and_costs(row: dict[str, Any], catalog: dict[str, list[Candidate]], is_breakfast: bool) -> None:
    if is_breakfast:
        if row.get("Recheio 1", "-") != "-":
            row["% Consumo Recheio 1"] = "70"
        if row.get("Recheio 2", "-") != "-":
            row["% Consumo Recheio 2"] = "30"
        weighted_recheio = (
            _candidate_cost(catalog, row.get("Recheio 1")) * (_safe_float(row.get("% Consumo Recheio 1")) / 100)
            + _candidate_cost(catalog, row.get("Recheio 2")) * (_safe_float(row.get("% Consumo Recheio 2")) / 100)
        )
        fixed = sum(
            _candidate_cost(catalog, row.get(col))
            for col in ("Pão", "Acompanhamento Café", "Bebida Café", "Fruta Café")
        )
        row["Custo Gerencial (R$)"] = f"{fixed + weighted_recheio:.2f}"
        return

    protein_cols = ["Prato Proteico Principal", "Opção Proteica 2", "Opção Proteica 3"]
    protein_items = [(col, row.get(col), _candidate_cost(catalog, row.get(col))) for col in protein_cols]
    protein_items = [item for item in protein_items if _clean_cell(item[1]) != "-"]
    if len(protein_items) >= 3:
        ordered = sorted(protein_items, key=lambda item: item[2])
        for col, (_, name, _) in zip(protein_cols, ordered):
            row[col] = name
        row["% Consumo Principal"] = "70"
        row["% Consumo Opção 2"] = "20"
        row["% Consumo Opção 3"] = "10"
    elif len(protein_items) == 2:
        ordered = sorted(protein_items, key=lambda item: item[2])
        row["Prato Proteico Principal"] = ordered[0][1]
        row["Opção Proteica 2"] = ordered[1][1]
        row["% Consumo Principal"] = "80"
        row["% Consumo Opção 2"] = "20"
        row["% Consumo Opção 3"] = "0"
        row["Opção Proteica 3"] = "-"
    elif len(protein_items) == 1:
        row["% Consumo Principal"] = "100"
        row["% Consumo Opção 2"] = "0"
        row["% Consumo Opção 3"] = "0"

    protein_cost = (
        _candidate_cost(catalog, row.get("Prato Proteico Principal")) * (_safe_float(row.get("% Consumo Principal")) / 100)
        + _candidate_cost(catalog, row.get("Opção Proteica 2")) * (_safe_float(row.get("% Consumo Opção 2")) / 100)
        + _candidate_cost(catalog, row.get("Opção Proteica 3")) * (_safe_float(row.get("% Consumo Opção 3")) / 100)
    )
    fixed_cols = [
        "Arroz",
        "Feijão",
        "Guarnição 1",
        "Guarnição 2",
        "Salada Grãos",
        "Salada Crua",
        "Salada Cozida",
        "Salada Folhosa/Elaborada",
        "Sobremesa",
        "Bebida",
        "Fruta",
    ]
    fixed_cost = sum(_candidate_cost(catalog, row.get(col)) for col in fixed_cols)
    row["Custo Gerencial (R$)"] = f"{fixed_cost + protein_cost:.2f}"


def _bucket_candidates(catalog: dict[str, list[Candidate]], bucket_name: str) -> list[Candidate]:
    items = catalog.get(bucket_name, [])
    if items:
        return items
    if bucket_name.startswith("saladas_"):
        return (
            catalog.get("saladas_cruas", [])
            + catalog.get("saladas_cozidas", [])
            + catalog.get("saladas_elaboradas", [])
        )
    if bucket_name in {"arroz", "feijao"}:
        return catalog.get("guarnicoes", [])
    if bucket_name in {"frutas", "sobremesas"}:
        return catalog.get("frutas", []) + catalog.get("sobremesas", [])
    if bucket_name in {"paes", "recheios", "acompanhamentos_cafe"}:
        return catalog.get("acompanhamentos_cafe", []) + catalog.get("guarnicoes", [])
    return items


def _catalog_for_prompt(catalog: dict[str, list[Candidate]], limit: int = 45) -> dict[str, list[dict[str, Any]]]:
    prompt_catalog: dict[str, list[dict[str, Any]]] = {}
    for bucket, items in catalog.items():
        if bucket == "outros":
            continue
        prompt_catalog[bucket] = [
            {
                "nome": c.nome,
                "categoria": c.categoria,
                "custo": round(c.custo, 2),
                "flags": [
                    flag
                    for flag, enabled in (
                        ("vegetariana", c.vegetariana),
                        ("vegana", c.vegana),
                        ("gluten", c.gluten),
                        ("lactose", c.lactose),
                    )
                    if enabled
                ],
            }
            for c in items[:limit]
        ]
    return prompt_catalog


def _resolve_prompt_catalog_limit(dias: int, refeicoes: list[str]) -> int:
    env_raw = (os.getenv("MENUAI_FAST_PROMPT_CATALOG_LIMIT") or "").strip()
    if env_raw:
        try:
            return max(8, min(60, int(env_raw)))
        except ValueError:
            pass
    rows = max(1, dias * max(1, len(refeicoes)))
    if rows >= 60:
        return 28
    if rows >= 30:
        return 24
    return 20


def _compact_contract_rules_for_prompt(regras_contrato: dict[str, Any], max_chars: int) -> str:
    if not isinstance(regras_contrato, dict):
        return "-"

    def _to_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (str, int, float, bool)):
            return [str(value)]
        if isinstance(value, dict):
            nome = value.get("nome") if isinstance(value.get("nome"), str) else None
            return [nome] if nome else [json.dumps(value, ensure_ascii=False)]
        if isinstance(value, list):
            out: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    nome = item.get("nome") if isinstance(item.get("nome"), str) else None
                    out.append(nome or json.dumps(item, ensure_ascii=False))
                else:
                    out.append(str(item))
            return [v for v in out if v and v != "-"]
        return [str(value)]

    servicos = regras_contrato.get("servicos") or {}
    necessidades = regras_contrato.get("necessidades") or {}
    compact = {
        "num_refeicoes_dia": servicos.get("num_refeicoes_dia") or necessidades.get("num_refeicoes_dia"),
        "dietas_especiais": _to_list(regras_contrato.get("dietas_especiais")),
        "proibicoes": _to_list(regras_contrato.get("proibicoes")),
        "restricoes_alergenos": _to_list(regras_contrato.get("restricoes_alergenos")),
        "incidencias": regras_contrato.get("incidencias") or {},
        "gramaturas": regras_contrato.get("gramaturas") or {},
        "observacoes": regras_contrato.get("observacoes") or necessidades.get("observacoes") or "",
    }
    return json.dumps(compact, ensure_ascii=False)[:max_chars]


def _extract_json(text: str) -> dict[str, Any]:
    content = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
    if fenced:
        content = fenced.group(1).strip()
    if not content.startswith("{"):
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            content = content[start : end + 1]
    return json.loads(content)


def _message_content(response: Any) -> str:
    if not getattr(response, "choices", None):
        return ""
    msg = response.choices[0].message
    return getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else "") or ""


def _llm_generate(
    *,
    job_id: str,
    empresa_id: str,
    llm_model: Optional[str],
    dias: int,
    refeicoes: list[str],
    regras_contrato: dict[str, Any],
    restricoes_usuario: str,
    target_custo_total: float,
    target_custo_proteico: float,
    catalog: dict[str, list[Candidate]],
    repair_context: Optional[str] = None,
    request_timeout_seconds: Optional[float] = None,
    max_attempts: Optional[int] = None,
    on_attempt: Optional[Callable[[dict[str, Any]], None]] = None,
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    from pipeline.model_router import ModelRouter

    prompt_catalog_limit = _resolve_prompt_catalog_limit(dias, refeicoes)
    prompt_catalog = _catalog_for_prompt(catalog, limit=prompt_catalog_limit)
    rules_max_chars_raw = (os.getenv("MENUAI_FAST_PROMPT_RULES_MAX_CHARS") or "2400").strip()
    catalog_max_chars_raw = (os.getenv("MENUAI_FAST_PROMPT_CATALOG_MAX_CHARS") or "14000").strip()
    try:
        rules_max_chars = max(500, int(rules_max_chars_raw))
    except ValueError:
        rules_max_chars = 2400
    try:
        catalog_max_chars = max(3000, int(catalog_max_chars_raw))
    except ValueError:
        catalog_max_chars = 14000
    contract_rules_prompt = _compact_contract_rules_for_prompt(regras_contrato or {}, rules_max_chars)

    system = (
        "Você é nutricionista de refeições coletivas. Gere cardápio operacional em JSON puro. "
        "Use somente pratos existentes no catálogo. Não inclua markdown fora do JSON."
    )
    repair_block = f"\n\nCORRIJA A SAÍDA ANTERIOR:\n{repair_context}" if repair_context else ""
    user = (
        f"Gere um cardápio de {dias} dias para as refeições: "
        f"{', '.join(REFEICAO_LABELS.get(r, r) for r in refeicoes)}.\n"
        f"Custo alvo total por refeição: R$ {target_custo_total:.2f}. "
        f"Custo alvo proteico: R$ {target_custo_proteico:.2f}.\n"
        f"Regras do contrato (resumo estruturado):\n{contract_rules_prompt}\n"
        f"Restrições adicionais:\n{restricoes_usuario or '-'}\n"
        f"Catálogo permitido (amostra otimizada):\n{json.dumps(prompt_catalog, ensure_ascii=False)[:catalog_max_chars]}\n\n"
        "Retorne exatamente este JSON:\n"
        "{\n"
        '  "dias": [\n'
        "    {\n"
        '      "Dia": 1,\n'
        '      "Refeição": "Almoço",\n'
        '      "Pão": "-",\n'
        '      "Recheio 1": "-",\n'
        '      "% Consumo Recheio 1": "-",\n'
        '      "Recheio 2": "-",\n'
        '      "% Consumo Recheio 2": "-",\n'
        '      "Acompanhamento Café": "-",\n'
        '      "Bebida Café": "-",\n'
        '      "Fruta Café": "-",\n'
        '      "Prato Proteico Principal": "nome do prato",\n'
        '      "% Consumo Principal": 70,\n'
        '      "Opção Proteica 2": "nome do prato",\n'
        '      "% Consumo Opção 2": 20,\n'
        '      "Opção Proteica 3": "nome do prato",\n'
        '      "% Consumo Opção 3": 10,\n'
        '      "Arroz": "nome do prato",\n'
        '      "Feijão": "nome do prato",\n'
        '      "Guarnição 1": "nome do prato",\n'
        '      "Guarnição 2": "nome do prato",\n'
        '      "Salada Grãos": "nome do prato ou -",\n'
        '      "Salada Crua": "nome do prato",\n'
        '      "Salada Cozida": "nome do prato",\n'
        '      "Salada Folhosa/Elaborada": "nome do prato",\n'
        '      "Sobremesa": "nome do prato ou -",\n'
        '      "Bebida": "nome do prato ou -",\n'
        '      "Fruta": "nome do prato ou -",\n'
        '      "Tema Especial": "tema ou -",\n'
        '      "Custo Gerencial (R$)": 0\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Regras: gere todos os dias; evite repetir prato proteico principal em dias consecutivos; "
        "mantenha opção vegetariana quando contrato exigir; use '-' só se não houver opção no catálogo. "
        "Para desjejum/café da manhã, preencha os campos Pão/Recheio/Acompanhamento Café/Bebida Café/Fruta Café "
        "e deixe campos de almoço como '-'. Para almoço/jantar, faça o inverso. "
        "Calibre % Consumo das opções para equilibrar custo: normalmente 70/20/10 ou 80/20/0."
        f"{repair_block}"
    )
    prompt_chars = len(system) + len(user)
    router = ModelRouter(
        model_id=llm_model,
        job_id=job_id,
        empresa_id=empresa_id,
        step_label="Geração rápida de cardápio",
        step_index=10 if not repair_context else 11,
        timeout_seconds=request_timeout_seconds,
        max_attempts=max_attempts,
        on_attempt=on_attempt,
    )
    fast_temp_raw = (os.getenv("MENUAI_FAST_LLM_TEMPERATURE") or "0.25").strip()
    try:
        fast_temp = float(fast_temp_raw)
    except ValueError:
        fast_temp = 0.25
    result = router.call(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=fast_temp,
    )
    if not result.success:
        raise RuntimeError(result.error or "Falha ao chamar LLM no modo rápido.")
    content = _message_content(result.response)
    payload = _extract_json(content)
    rows = payload.get("dias") or payload.get("cardapio") or []
    if not isinstance(rows, list):
        raise ValueError("Resposta LLM sem lista 'dias'.")
    return rows, content, {
        "model_id": result.model_id,
        "model_used": result.model_used,
        "provider_used": result.provider_used,
        "attempts": result.attempts,
        "fallback_used": result.is_fallback,
        "prompt_chars": prompt_chars,
        "prompt_catalog_limit": prompt_catalog_limit,
    }


def _deterministic_rows(catalog: dict[str, list[Candidate]], dias: int, refeicoes: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dia in range(1, dias + 1):
        for meal_idx, ref in enumerate(refeicoes):
            idx = (dia - 1) + meal_idx
            is_breakfast = _is_breakfast_ref(ref)
            row: dict[str, Any] = {
                "Dia": dia,
                "Refeição": REFEICAO_LABELS.get(ref, ref.title()),
                "Tema Especial": SPECIAL_THEMES[(dia - 1) % len(SPECIAL_THEMES)],
            }
            for col in OUTPUT_COLUMNS:
                row.setdefault(col, "-")
            row["Dia"] = dia
            row["Refeição"] = REFEICAO_LABELS.get(ref, ref.title())
            for col, bucket_name in SLOT_BUCKETS.items():
                if is_breakfast and col not in BREAKFAST_FIELDS:
                    continue
                if not is_breakfast and col not in MEAL_FIELDS:
                    continue
                bucket = _bucket_candidates(catalog, bucket_name)
                offset = idx
                if col == "Opção Proteica 2":
                    offset = idx + max(1, len(bucket) // 3)
                elif col == "Opção Proteica 3":
                    offset = idx + max(2, (len(bucket) * 2) // 3)
                elif col.endswith("2"):
                    offset = idx + 1
                cand = _candidate_for(bucket, offset)
                row[col] = cand.nome if cand else "-"
            _apply_consumption_and_costs(row, catalog, is_breakfast)
            rows.append(row)
    return rows


def _validate_and_normalize(
    rows: list[dict[str, Any]],
    *,
    dias: int,
    refeicoes: list[str],
    catalog: dict[str, list[Candidate]],
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    expected_count = dias * max(1, len(refeicoes))
    allowed_by_slot = {
        col: {_norm(candidate.nome) for candidate in _bucket_candidates(catalog, bucket)}
        for col, bucket in SLOT_BUCKETS.items()
    }
    by_key: dict[tuple[int, str], dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        try:
            dia = int(str(raw.get("Dia") or raw.get("dia") or "").replace("*", "").strip())
        except ValueError:
            continue
        refeicao = _clean_cell(raw.get("Refeição") or raw.get("refeicao") or REFEICAO_LABELS.get(refeicoes[0], "Almoço"))
        by_key[(dia, _norm(refeicao))] = raw

    fallback = _deterministic_rows(catalog, dias, refeicoes)
    fallback_by_key = {(int(r["Dia"]), _norm(r["Refeição"])): r for r in fallback}
    normalized: list[dict[str, Any]] = []
    for dia in range(1, dias + 1):
        for ref in refeicoes:
            refeicao_label = REFEICAO_LABELS.get(ref, ref.title())
            is_breakfast = _is_breakfast_ref(ref)
            key = (dia, _norm(refeicao_label))
            raw = by_key.get(key)
            if raw is None and len(refeicoes) == 1:
                raw = next((v for (d, _), v in by_key.items() if d == dia), None)
            if raw is None:
                warnings.append(f"Dia {dia}/{refeicao_label} ausente; preenchido por rotação determinística.")
                raw = fallback_by_key[key]
            row = {}
            fallback_row = fallback_by_key[key]
            for col in OUTPUT_COLUMNS:
                if is_breakfast and col in MEAL_FIELDS:
                    row[col] = "-"
                    continue
                if not is_breakfast and col in BREAKFAST_FIELDS:
                    row[col] = "-"
                    continue
                value = raw.get(col)
                if value in (None, ""):
                    value = fallback_row.get(col, "-")
                    if col not in {"Tema Especial", "Custo Gerencial (R$)", *PERCENT_COLUMNS}:
                        warnings.append(f"Campo {col} ausente no dia {dia}; preenchido automaticamente.")
                value = _clean_cell(value)
                if col in SLOT_BUCKETS and value != "-" and _norm(value) not in allowed_by_slot.get(col, set()):
                    fallback_value = fallback_row.get(col, "-")
                    warnings.append(
                        f"Campo {col} no dia {dia} não existe no catálogo; substituído por ficha ativa."
                    )
                    value = fallback_value
                row[col] = _clean_cell(value)
            row["Dia"] = str(dia)
            row["Refeição"] = refeicao_label
            _apply_consumption_and_costs(row, catalog, is_breakfast)
            normalized.append(row)

    if len(normalized) != expected_count:
        warnings.append(f"Quantidade normalizada ({len(normalized)}) diferente da esperada ({expected_count}).")
    for i in range(1, len(normalized)):
        prev = normalized[i - 1].get("Prato Proteico Principal")
        cur = normalized[i].get("Prato Proteico Principal")
        if prev == "-" or cur == "-":
            continue
        if prev and cur and _norm(prev) == _norm(cur):
            replacement = next(
                (candidate.nome for candidate in _bucket_candidates(catalog, "proteicos") if _norm(candidate.nome) != _norm(prev)),
                None,
            )
            if replacement:
                normalized[i]["Prato Proteico Principal"] = replacement
                _apply_consumption_and_costs(normalized[i], catalog, False)
                warnings.append(f"Proteico principal repetido entre linhas {i} e {i + 1}; substituído automaticamente.")
            else:
                warnings.append(f"Proteico principal repetido entre linhas {i} e {i + 1}.")
    return normalized, warnings


def _core_catalog_errors(catalog: dict[str, list[Candidate]], refeicoes: list[str]) -> list[str]:
    errors = []
    needs_meal = any(not _is_breakfast_ref(ref) for ref in refeicoes)
    needs_breakfast = any(_is_breakfast_ref(ref) for ref in refeicoes)
    if needs_meal and not catalog.get("proteicos"):
        errors.append("Nenhuma ficha proteica ativa encontrada para a empresa.")
    if needs_meal and not (catalog.get("guarnicoes") or catalog.get("arroz") or catalog.get("feijao")):
        errors.append("Nenhuma ficha de guarnição/acompanhamento ativa encontrada para a empresa.")
    if needs_meal and not (
        catalog.get("saladas_cruas")
        or catalog.get("saladas_cozidas")
        or catalog.get("saladas_elaboradas")
        or catalog.get("saladas_graos")
    ):
        errors.append("Nenhuma ficha de salada ativa encontrada para a empresa.")
    if needs_breakfast and not (catalog.get("paes") or catalog.get("acompanhamentos_cafe")):
        errors.append("Nenhuma ficha de desjejum/café da manhã ativa encontrada para a empresa.")
    return errors


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    header = "| " + " | ".join(OUTPUT_COLUMNS) + " |"
    sep = "| " + " | ".join(["---"] * len(OUTPUT_COLUMNS)) + " |"
    lines = [header, sep]
    for row in rows:
        cells = [str(row.get(col, "-")).replace("|", "/") for col in OUTPUT_COLUMNS]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _candidate_lookup(catalog: dict[str, list[Candidate]]) -> dict[str, Candidate]:
    lookup: dict[str, Candidate] = {}
    for items in catalog.values():
        for item in items:
            lookup.setdefault(_norm(item.nome), item)
            if item.codigo:
                lookup.setdefault(_norm(item.codigo), item)
    return lookup


def _tipo_refeicao(label: str) -> str:
    norm = _norm(label)
    for key, human in REFEICAO_LABELS.items():
        if _norm(human) == norm or _norm(key) == norm:
            return key
    return "almoco"


def _persist_cardapio(
    db: Session,
    *,
    job_id: str,
    empresa_id: str,
    contrato_id: Optional[str],
    nome_cardapio: Optional[str],
    dias: int,
    target_custo_total: float,
    target_custo_proteico: float,
    llm_model: Optional[str],
    markdown: str,
    rows: list[dict[str, Any]],
    catalog: dict[str, list[Candidate]],
    warnings: list[str],
    duration_seconds: float,
    attempts: int,
    model_used: Optional[str],
    provider_used: Optional[str],
    timeout_reason: Optional[str],
    prompt_chars: Optional[int] = None,
    prompt_catalog_limit: Optional[int] = None,
) -> str:
    from database.models import Cardapio, CardapioDia, CardapioRefeicao, JobAgente
    from services.knowledge_base import sync_cardapio_document
    from services.knowledge_hooks import sync_knowledge_safe

    lookup = _candidate_lookup(catalog)
    cardapio = Cardapio(
        empresa_id=empresa_id,
        contrato_id=contrato_id,
        nome=nome_cardapio or f"Cardápio {dias} dias — {job_id}",
        status="rascunho",
        num_dias=dias,
        resultado_raw=markdown,
        job_id=job_id,
        parametros_json={
            "dias": dias,
            "target_custo_total": target_custo_total,
            "target_custo_proteico": target_custo_proteico,
            "llm_model": llm_model,
            "generation_mode": "fast",
            "duration_seconds": round(duration_seconds, 2),
            "attempts": attempts,
            "model_used": model_used or llm_model,
            "provider_used": provider_used,
            "timeout_reason": timeout_reason,
            "prompt_chars": prompt_chars,
            "prompt_catalog_limit": prompt_catalog_limit,
            "validation_warnings": warnings[:100],
        },
        updated_at=datetime.utcnow(),
    )
    db.add(cardapio)
    db.flush()

    rows_by_day: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_day.setdefault(int(row["Dia"]), []).append(row)

    total_cost = 0.0
    for dia_num in range(1, dias + 1):
        day_rows = rows_by_day.get(dia_num, [])
        dia_db = CardapioDia(cardapio_id=cardapio.id, numero_dia=dia_num, custo_total=0.0)
        db.add(dia_db)
        db.flush()
        day_cost = 0.0
        for row in day_rows:
            refeicao = _tipo_refeicao(row.get("Refeição", "Almoço"))
            for ordem, col in enumerate(SLOT_BUCKETS.keys(), start=1):
                nome = _clean_cell(row.get(col))
                if nome == "-":
                    continue
                cand = lookup.get(_norm(nome))
                custo = float(cand.custo) if cand else 0.0
                day_cost += custo
                db.add(
                    CardapioRefeicao(
                        dia_id=dia_db.id,
                        ficha_tecnica_id=cand.id if cand else None,
                        tipo_refeicao=refeicao,
                        categoria=col,
                        codigo_prato=cand.codigo if cand else None,
                        nome_prato=nome,
                        custo_porcao=round(custo, 2),
                        observacoes=None,
                        ordem=ordem,
                    )
                )
        dia_db.custo_total = round(day_cost, 2)
        total_cost += day_cost

    cardapio.custo_medio_dia = round(total_cost / max(dias, 1), 2)
    job_db = db.query(JobAgente).filter(JobAgente.job_id == job_id).first()
    if job_db:
        job_db.status = "concluido"
        job_db.progresso = 100
        job_db.resultado_raw = markdown
        job_db.cardapio_id = cardapio.id
        if isinstance(job_db.parametros_json, dict):
            params = dict(job_db.parametros_json)
        else:
            params = {}
        params.update(
            {
                "duration_seconds": round(duration_seconds, 2),
                "attempts": attempts,
                "model_used": model_used or llm_model,
                "provider_used": provider_used,
                "timeout_reason": timeout_reason,
                "prompt_chars": prompt_chars,
                "prompt_catalog_limit": prompt_catalog_limit,
            }
        )
        job_db.parametros_json = params
        job_db.concluido_em = datetime.utcnow()
        job_db.updated_at = datetime.utcnow()

    sync_knowledge_safe(sync_cardapio_document, db, cardapio)
    db.commit()
    return str(cardapio.id)


def run_fast_generation(
    *,
    job_id: str,
    dias: int,
    target_custo_total: float,
    target_custo_proteico: float,
    restricoes_usuario: str,
    refeicoes: Optional[list[str]],
    empresa_id: Optional[str],
    contrato_id: Optional[str],
    nome_cardapio: Optional[str],
    llm_model: Optional[str],
    regras_contrato: dict[str, Any],
    started_ts: float,
    progress: Callable[[int, str, str], None],
) -> dict[str, Any]:
    if not empresa_id:
        raise ValueError("empresa_id é obrigatório para geração rápida com fichas do banco.")

    from database.connection import SessionLocal
    from services import job_state

    db = SessionLocal()
    try:
        budget_seconds_raw = (os.getenv("MENUAI_FAST_BUDGET_SECONDS") or "300").strip()
        per_call_timeout_raw = (os.getenv("MENUAI_FAST_LLM_ATTEMPT_TIMEOUT_SECONDS") or "55").strip()
        max_attempts_raw = (os.getenv("MENUAI_FAST_LLM_MAX_ATTEMPTS") or "3").strip()
        try:
            budget_seconds = max(60.0, float(budget_seconds_raw))
        except ValueError:
            budget_seconds = 300.0
        try:
            per_call_timeout = max(20.0, float(per_call_timeout_raw))
        except ValueError:
            per_call_timeout = 55.0
        try:
            max_attempts = max(1, int(max_attempts_raw))
        except ValueError:
            max_attempts = 3

        def touch_job(step_hint: Optional[str] = None) -> None:
            job = job_state.jobs.get(job_id)
            if not job:
                return
            job["last_update_at"] = datetime.utcnow().isoformat()
            job["last_update_ts"] = time.time()
            if step_hint:
                job["current_step"] = step_hint

        def remaining_budget_seconds() -> float:
            return budget_seconds - (time.time() - started_ts)

        def ensure_budget(stage: str, reserve_seconds: float = 0.0) -> None:
            remaining = remaining_budget_seconds()
            if remaining <= reserve_seconds:
                raise FastGenerationTimeout(
                    (
                        f"Tempo limite da geração rápida excedido ({int(budget_seconds)}s). "
                        f"Etapa atual: {stage}. Tente novamente, troque o modelo ou reduza os dias."
                    ),
                    timeout_reason=f"budget_exceeded_at_{stage}",
                )

        logger.info(
            "job_event=%s",
            json.dumps(
                {
                    "event": "fast_generation_started",
                    "job_id": job_id,
                    "empresa_id": empresa_id,
                    "dias": dias,
                    "budget_seconds": budget_seconds,
                    "per_call_timeout_seconds": per_call_timeout,
                    "max_attempts": max_attempts,
                },
                ensure_ascii=False,
                default=str,
            ),
        )
        refeicoes_norm = refeicoes or ["almoco"]
        ensure_budget("catalog_snapshot", reserve_seconds=25)
        progress(45, "📚 Montando catálogo rápido de fichas técnicas...", "Gestor de Fichas Técnicas")
        catalog = _catalog_snapshot(db, empresa_id)
        errors = _core_catalog_errors(catalog, refeicoes_norm)
        if errors:
            raise ValueError(" ".join(errors))

        ensure_budget("initial_llm_generation", reserve_seconds=20)
        progress(58, "🧠 Gerando matriz operacional do cardápio...", "Nutricionista")
        warnings: list[str] = []
        llm_attempts_total = 0
        llm_model_used: Optional[str] = None
        llm_provider_used: Optional[str] = None
        llm_prompt_chars: Optional[int] = None
        llm_prompt_catalog_limit: Optional[int] = None
        timeout_reason: Optional[str] = None
        def on_llm_attempt(meta: dict[str, Any]) -> None:
            attempt = int(meta.get("attempt") or 0)
            max_att = int(meta.get("max_attempts") or max_attempts)
            model_label = str(meta.get("model_id") or meta.get("model_string") or "modelo")
            provider = str(meta.get("provider") or "")
            provider_part = f" ({provider})" if provider else ""
            touch_job(f"Tentativa LLM {attempt}/{max_att}: {model_label}{provider_part}")

        try:
            timeout_for_this_call = min(
                per_call_timeout,
                max(20.0, remaining_budget_seconds() - 12.0),
            )
            touch_job("Iniciando chamada LLM para montar matriz operacional")
            rows, raw_response, call_meta = _llm_generate(
                job_id=job_id,
                empresa_id=empresa_id,
                llm_model=llm_model,
                dias=dias,
                refeicoes=refeicoes_norm,
                regras_contrato=regras_contrato or {},
                restricoes_usuario=restricoes_usuario,
                target_custo_total=target_custo_total,
                target_custo_proteico=target_custo_proteico,
                catalog=catalog,
                request_timeout_seconds=timeout_for_this_call,
                max_attempts=max_attempts,
                on_attempt=on_llm_attempt,
            )
            llm_attempts_total += int(call_meta.get("attempts") or 0)
            llm_model_used = str(call_meta.get("model_used") or llm_model or "")
            llm_provider_used = str(call_meta.get("provider_used") or "")
            llm_prompt_chars = int(call_meta.get("prompt_chars") or 0) or llm_prompt_chars
            llm_prompt_catalog_limit = int(call_meta.get("prompt_catalog_limit") or 0) or llm_prompt_catalog_limit
        except Exception as exc:
            warnings.append(f"Geração LLM inicial falhou; usada rotação determinística. Erro: {exc}")
            rows = _deterministic_rows(catalog, dias, refeicoes_norm)
            raw_response = ""

        ensure_budget("validation", reserve_seconds=10)
        progress(76, "🔎 Validando dias, colunas e repetições...", "Analista Nutricional")
        normalized, validation_warnings = _validate_and_normalize(
            rows,
            dias=dias,
            refeicoes=refeicoes_norm,
            catalog=catalog,
        )
        warnings.extend(validation_warnings)

        if validation_warnings and raw_response:
            ensure_budget("repair_llm_generation", reserve_seconds=8)
            progress(82, "🛠️ Ajustando automaticamente inconsistências do cardápio...", "Nutricionista")
            try:
                timeout_for_repair = min(
                    per_call_timeout,
                    max(20.0, remaining_budget_seconds() - 8.0),
                )
                touch_job("Iniciando chamada LLM de reparo")
                repaired, _, repair_meta = _llm_generate(
                    job_id=job_id,
                    empresa_id=empresa_id,
                    llm_model=llm_model,
                    dias=dias,
                    refeicoes=refeicoes_norm,
                    regras_contrato=regras_contrato or {},
                    restricoes_usuario=restricoes_usuario,
                    target_custo_total=target_custo_total,
                    target_custo_proteico=target_custo_proteico,
                    catalog=catalog,
                    repair_context=json.dumps(
                        {"warnings": validation_warnings[:30], "saida_anterior": normalized[: max(dias, 30)]},
                        ensure_ascii=False,
                    )[:12000],
                    request_timeout_seconds=timeout_for_repair,
                    max_attempts=max_attempts,
                    on_attempt=on_llm_attempt,
                )
                llm_attempts_total += int(repair_meta.get("attempts") or 0)
                if not llm_model_used:
                    llm_model_used = str(repair_meta.get("model_used") or llm_model or "")
                if not llm_provider_used:
                    llm_provider_used = str(repair_meta.get("provider_used") or "")
                if not llm_prompt_chars:
                    llm_prompt_chars = int(repair_meta.get("prompt_chars") or 0) or None
                if not llm_prompt_catalog_limit:
                    llm_prompt_catalog_limit = int(repair_meta.get("prompt_catalog_limit") or 0) or None
                normalized, repair_warnings = _validate_and_normalize(
                    repaired,
                    dias=dias,
                    refeicoes=refeicoes_norm,
                    catalog=catalog,
                )
                warnings.extend(repair_warnings)
            except Exception as exc:
                warnings.append(f"Reparo LLM falhou; mantida versão normalizada. Erro: {exc}")

        ensure_budget("persist", reserve_seconds=0)
        progress(90, "💾 Persistindo cardápio estruturado...", "Sistema")
        markdown = _markdown_table(normalized)
        duration_seconds = time.time() - started_ts
        cardapio_id = _persist_cardapio(
            db,
            job_id=job_id,
            empresa_id=empresa_id,
            contrato_id=contrato_id,
            nome_cardapio=nome_cardapio,
            dias=dias,
            target_custo_total=target_custo_total,
            target_custo_proteico=target_custo_proteico,
            llm_model=llm_model,
            markdown=markdown,
            rows=normalized,
            catalog=catalog,
            warnings=warnings,
            duration_seconds=duration_seconds,
            attempts=llm_attempts_total,
            model_used=llm_model_used,
            provider_used=llm_provider_used,
            timeout_reason=timeout_reason,
            prompt_chars=llm_prompt_chars,
            prompt_catalog_limit=llm_prompt_catalog_limit,
        )
        logger.info(
            "job_event=%s",
            json.dumps(
                {
                    "event": "fast_generation_completed",
                    "job_id": job_id,
                    "cardapio_id": cardapio_id,
                    "duration_seconds": round(duration_seconds, 2),
                    "attempts": llm_attempts_total,
                    "model_used": llm_model_used or llm_model,
                    "provider_used": llm_provider_used,
                    "prompt_chars": llm_prompt_chars,
                    "prompt_catalog_limit": llm_prompt_catalog_limit,
                    "warnings_count": len(warnings),
                },
                ensure_ascii=False,
                default=str,
            ),
        )
        return {
            "markdown": markdown,
            "cardapio_id": cardapio_id,
            "warnings": warnings,
            "duration_seconds": round(duration_seconds, 2),
            "attempts": llm_attempts_total,
            "model_used": llm_model_used or llm_model,
            "provider_used": llm_provider_used,
            "prompt_chars": llm_prompt_chars,
            "prompt_catalog_limit": llm_prompt_catalog_limit,
        }
    except FastGenerationTimeout as timeout_exc:
        timeout_reason = timeout_exc.timeout_reason
        logger.warning(
            "job_event=%s",
            json.dumps(
                {
                    "event": "fast_generation_timeout",
                    "job_id": job_id,
                    "duration_seconds": round(time.time() - started_ts, 2),
                    "timeout_reason": timeout_reason,
                },
                ensure_ascii=False,
                default=str,
            ),
        )
        raise
    finally:
        db.close()
