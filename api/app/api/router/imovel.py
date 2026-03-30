from fastapi import APIRouter, HTTPException, Path

from app.controllers.imovel_controller import find_imovel_by_codigo
from app.schemas.imovel import ImovelResponse
from app.services.imovel_service import DatabaseError

router = APIRouter(tags=["imovel"])


@router.get("/imovel/{codigo_incra}", response_model=ImovelResponse)
def get_imovel(
    codigo_incra: str = Path(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9./_-]+$",
        description="Codigo INCRA do imovel",
    )
) -> ImovelResponse:
    normalized_codigo = codigo_incra.strip()
    if not normalized_codigo:
        raise HTTPException(status_code=422, detail="codigo_incra nao pode ser vazio")

    try:
        result = find_imovel_by_codigo(normalized_codigo)
    except DatabaseError:
        raise HTTPException(status_code=503, detail="Banco de dados indisponivel")

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Imovel com codigo INCRA '{normalized_codigo}' nao encontrado na base.",
        )
    return result
