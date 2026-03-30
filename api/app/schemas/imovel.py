from pydantic import BaseModel, Field


class ProprietarioResponse(BaseModel):
    nome_completo: str = Field(min_length=1)
    cpf: str = Field(pattern=r"^\*\*\*\.\*\*\*\.\*\*\*-(\d{2}|\*\*)$")
    vinculo: str = Field(min_length=1)
    participacao_pct: float = Field(ge=0.0, le=100.0)


class ImovelResponse(BaseModel):
    codigo_incra: str = Field(min_length=1)
    area_ha: float | None = Field(default=None, ge=0.0)
    situacao: str = Field(min_length=1)
    proprietarios: list[ProprietarioResponse]
