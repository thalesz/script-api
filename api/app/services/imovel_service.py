import re
from dataclasses import dataclass

from app.db.connection import get_connection
from app.schemas.imovel import ImovelResponse, ProprietarioResponse


CPF_PATTERN = re.compile(r"(\d{3})\.?\s*(\d{3})\.?\s*(\d{3})\-?(\d{2})")
OWNER_SPLIT_PATTERN = re.compile(r"\s*(?:;|\||\s/\s|\s+e\s+)\s*", re.IGNORECASE)


@dataclass
class DatabaseError(Exception):
    message: str = "Falha ao consultar o banco de dados"


def _extract_cpf(value: str | None) -> str | None:
    if not value:
        return None
    match = CPF_PATTERN.search(value)
    if not match:
        return None
    return "".join(match.groups())


def _extract_nome_completo(value: str | None) -> str:
    if not value:
        return "Nao informado"
    # Remove CPF quando vier embutido no mesmo campo do nome.
    nome = CPF_PATTERN.sub("", value)
    nome = re.sub(r"\s*-\s*$", "", nome).strip(" -:\t")
    return nome or "Nao informado"


def _mask_cpf(cpf: str | None) -> str:
    # Decisao de contrato: seguir o formato do exemplo oficial da resposta.
    # Exemplo: 12345678972 -> ***.***.***-72
    if not cpf or len(cpf) != 11 or not cpf.isdigit():
        return "***.***.***-**"
    return f"***.***.***-{cpf[-2:]}"


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_participacao_pct(value) -> float:
    # Keep API stable even when source has null/invalid or out-of-range percentages.
    parsed = _to_float(value)
    if parsed is None:
        return 100.0
    if parsed < 0:
        return 0.0
    if parsed > 100:
        return 100.0
    return parsed


def _parse_proprietarios(value: str | None, pct_obtencao) -> list[ProprietarioResponse]:
    if not value:
        return []

    owners: list[ProprietarioResponse] = []
    seen: set[tuple[str, str]] = set()
    parts = [p.strip() for p in OWNER_SPLIT_PATTERN.split(value) if p and p.strip()]
    if not parts:
        parts = [value]

    for raw_owner in parts:
        cpf = _extract_cpf(raw_owner)
        nome = _extract_nome_completo(raw_owner)
        key = (nome.lower(), cpf or "")
        if key in seen:
            continue
        seen.add(key)
        owners.append(
            ProprietarioResponse(
                nome_completo=nome,
                cpf=_mask_cpf(cpf),
                vinculo="Proprietario",
                participacao_pct=_to_participacao_pct(pct_obtencao),
            )
        )

    return owners


def get_imovel_by_codigo(codigo_incra: str) -> ImovelResponse | None:
    query = """
        SELECT codigo_incra, pct_obtencao, denominacao, proprietario
        FROM sncr_records
        WHERE codigo_incra = %s
        LIMIT 1;
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (codigo_incra,))
                row = cur.fetchone()
    except Exception as exc:
        raise DatabaseError() from exc

    if row is None:
        return None

    codigo, pct_obtencao, denominacao, proprietario = row
    return ImovelResponse(
        codigo_incra=codigo,
        area_ha=_to_float(pct_obtencao),
        situacao=denominacao or "Nao informado",
        proprietarios=_parse_proprietarios(proprietario, pct_obtencao),
    )
