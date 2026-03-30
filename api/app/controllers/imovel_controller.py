from app.schemas.imovel import ImovelResponse
from app.services.imovel_service import get_imovel_by_codigo


def find_imovel_by_codigo(codigo_incra: str) -> ImovelResponse | None:
    return get_imovel_by_codigo(codigo_incra)
