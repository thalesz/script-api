from pathlib import Path
import sys
import uuid

import pytest

# Permite rodar pytest tanto na raiz quanto dentro de script/.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from loader import Loader


def _build_test_csv(path: Path, codigo_incra: str) -> None:
    path.write_text(
        "codigo_incra;matricula;municipio;denominacao;proprietario;pct_obtencao\n"
        f"{codigo_incra};MTR123;Cidade Teste;Ativo;Pessoa Teste 123.456.789-72;100,0\n",
        encoding="utf-8",
    )


def _get_loader_or_skip() -> Loader:
    loader = Loader()
    try:
        with loader._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"PostgreSQL indisponivel para teste de idempotencia: {exc}")
    return loader


def test_loader_idempotencia_duas_execucoes_nao_duplicam(tmp_path: Path):
    loader = _get_loader_or_skip()

    unique_code = f"IDEMP{uuid.uuid4().hex[:20].upper()}"
    csv_path = tmp_path / "SP_idempotencia_test.csv"
    _build_test_csv(csv_path, unique_code)

    loader.prepare_table()

    # Limpeza defensiva caso o codigo ja exista por algum motivo.
    with loader._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sncr_records WHERE codigo_incra = %s", (unique_code,))
            conn.commit()

    loader._process_file(csv_path)
    with loader._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sncr_records WHERE codigo_incra = %s", (unique_code,))
            first_count = cur.fetchone()[0]

    loader._process_file(csv_path)
    with loader._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sncr_records WHERE codigo_incra = %s", (unique_code,))
            second_count = cur.fetchone()[0]

    assert first_count == 1
    assert second_count == 1

    # Cleanup do dado de teste.
    with loader._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sncr_records WHERE codigo_incra = %s", (unique_code,))
            conn.commit()
