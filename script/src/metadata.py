from datetime import datetime


def build_metadata(uf: str, municipio: str, total_registros: int) -> dict:
    return {
        "executado_em": datetime.now().isoformat(),
        "uf": uf,
        "municipio": municipio,
        "total_registros": total_registros,
    }


class MetadataBuilder:
    """Constrói dicionários de metadados para cada extração."""

    @staticmethod
    def build(uf: str, municipio: str, total_registros: int) -> dict:
        return build_metadata(uf, municipio, total_registros)
