from pathlib import Path
import sys

# Permite rodar pytest tanto na raiz do repo quanto dentro de api/.
API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from fastapi.testclient import TestClient

from main import app
import app.services.imovel_service as imovel_service


class _FakeCursor:
    def __init__(self, row):
        self._row = row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self._last_query = query
        self._last_params = params

    def fetchone(self):
        return self._row


class _FakeConnection:
    def __init__(self, row):
        self._row = row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _FakeCursor(self._row)


def test_get_imovel_200_and_cpf_masking(monkeypatch):
    row = (
        "SE000000000000",
        142.5,
        "Ativo",
        "Maria Aparecida de Souza 123.456.789-72",
    )

    def _fake_get_connection():
        return _FakeConnection(row)

    monkeypatch.setattr(imovel_service, "get_connection", _fake_get_connection)
    client = TestClient(app)

    response = client.get("/imovel/SE000000000000")

    assert response.status_code == 200
    data = response.json()
    assert data["codigo_incra"] == "SE000000000000"
    assert data["area_ha"] == 142.5
    assert data["situacao"] == "Ativo"
    assert len(data["proprietarios"]) == 1
    assert data["proprietarios"][0]["nome_completo"] == "Maria Aparecida de Souza"
    assert data["proprietarios"][0]["cpf"] == "***.***.***-72"


def test_get_imovel_404_when_not_found(monkeypatch):
    def _fake_get_connection():
        return _FakeConnection(None)

    monkeypatch.setattr(imovel_service, "get_connection", _fake_get_connection)
    client = TestClient(app)

    response = client.get("/imovel/SE000000000000")

    assert response.status_code == 404
    assert "nao encontrado" in response.json()["detail"].lower()


def test_get_imovel_422_when_codigo_has_invalid_chars():
    client = TestClient(app)

    response = client.get("/imovel/SE0000*INVALIDO")

    assert response.status_code == 422


def test_get_imovel_503_when_db_is_unavailable(monkeypatch):
    def _failing_get_connection():
        raise RuntimeError("db offline")

    monkeypatch.setattr(imovel_service, "get_connection", _failing_get_connection)
    client = TestClient(app)

    response = client.get("/imovel/SE000000000000")

    assert response.status_code == 503
    assert response.json()["detail"] == "Banco de dados indisponivel"


def test_get_imovel_200_with_multiple_proprietarios(monkeypatch):
    """Test que múltiplos proprietários são retornados corretamente."""
    row = (
        "MG123456789012",
        50.0,
        "Ativo",
        "João Silva 123.456.789-72 | Maria Santos 987.654.321-10",
    )

    def _fake_get_connection():
        return _FakeConnection(row)

    monkeypatch.setattr(imovel_service, "get_connection", _fake_get_connection)
    client = TestClient(app)

    response = client.get("/imovel/MG123456789012")

    assert response.status_code == 200
    data = response.json()
    assert len(data["proprietarios"]) == 2
    assert data["proprietarios"][0]["nome_completo"] == "João Silva"
    assert data["proprietarios"][0]["cpf"] == "***.***.***-72"
    assert data["proprietarios"][0]["participacao_pct"] == 50.0
    assert data["proprietarios"][1]["nome_completo"] == "Maria Santos"
    assert data["proprietarios"][1]["cpf"] == "***.***.***-10"
    assert data["proprietarios"][1]["participacao_pct"] == 50.0


def test_get_imovel_200_with_proprietario_without_cpf(monkeypatch):
    """Test que proprietário sem CPF não falha."""
    row = (
        "BA999999999999",
        100.0,
        "Ativo",
        "José da Silva",
    )

    def _fake_get_connection():
        return _FakeConnection(row)

    monkeypatch.setattr(imovel_service, "get_connection", _fake_get_connection)
    client = TestClient(app)

    response = client.get("/imovel/BA999999999999")

    assert response.status_code == 200
    data = response.json()
    assert len(data["proprietarios"]) == 1
    assert data["proprietarios"][0]["nome_completo"] == "José da Silva"
    assert data["proprietarios"][0]["cpf"] == "***.***.***-**"  # Sem CPF válido
    assert data["proprietarios"][0]["participacao_pct"] == 100.0


def test_get_imovel_200_with_malformed_cpf(monkeypatch):
    """Test com CPF parcialmente malformado (mais de 11 dígitos)."""
    row = (
        "SP111111111111",
        100.0,
        "Ativo",
        "Pedro Oliveira 123.456.789-99 extratext",  # 11 dígitos válidos + extras
    )

    def _fake_get_connection():
        return _FakeConnection(row)

    monkeypatch.setattr(imovel_service, "get_connection", _fake_get_connection)
    client = TestClient(app)

    response = client.get("/imovel/SP111111111111")

    # Deve retornar 200 e extrair os 11 dígitos do CPF
    assert response.status_code == 200
    data = response.json()
    # O regex captura os 11 primeiros dígitos no formato válido
    assert data["proprietarios"][0]["cpf"] == "***.***.***-99"


def test_get_imovel_required_fields_present(monkeypatch):
    """Test que todos os campos obrigatórios estão presentes na resposta."""
    row = (
        "RS222222222222",
        400.50,
        "Ativo",
        "Ana Costa 111.222.333-44",
    )

    def _fake_get_connection():
        return _FakeConnection(row)

    monkeypatch.setattr(imovel_service, "get_connection", _fake_get_connection)
    client = TestClient(app)

    response = client.get("/imovel/RS222222222222")

    assert response.status_code == 200
    data = response.json()
    
    # Campos obrigatórios no response
    assert "codigo_incra" in data
    assert "area_ha" in data
    assert "situacao" in data
    assert "proprietarios" in data
    
    # Campos obrigatórios no proprietário
    proprietario = data["proprietarios"][0]
    assert "nome_completo" in proprietario
    assert "cpf" in proprietario
    assert "participacao_pct" in proprietario


def test_get_imovel_200_with_edge_participacao_values(monkeypatch):
    """Test com valores extremos de participação (0%, 100% e out-of-range)."""
    # Test 1: 0% clamped to 0.0
    row_0 = (
        "GO333333333333",
        0.0,
        "Ativo",
        "Owner 1 111.111.111-11 | Owner 2 222.222.222-22",
    )

    def _fake_get_connection():
        return _FakeConnection(row_0)

    monkeypatch.setattr(imovel_service, "get_connection", _fake_get_connection)
    client = TestClient(app)

    response = client.get("/imovel/GO333333333333")
    assert response.status_code == 200
    data = response.json()
    assert len(data["proprietarios"]) == 2
    assert data["proprietarios"][0]["participacao_pct"] == 0.0
    assert data["proprietarios"][1]["participacao_pct"] == 0.0

    # Test 2: 100%
    row_100 = (
        "GO333333333334",
        100.0,
        "Ativo",
        "Owner 1 333.333.333-33",
    )

    def _fake_get_connection_100():
        return _FakeConnection(row_100)

    monkeypatch.setattr(imovel_service, "get_connection", _fake_get_connection_100)
    response = client.get("/imovel/GO333333333334")
    assert response.status_code == 200
    data = response.json()
    assert data["proprietarios"][0]["participacao_pct"] == 100.0

    # Test 3: >100 clamped to 100.0
    row_over = (
        "GO333333333335",
        150.0,
        "Ativo",
        "Owner 1 444.444.444-44",
    )

    def _fake_get_connection_over():
        return _FakeConnection(row_over)

    monkeypatch.setattr(imovel_service, "get_connection", _fake_get_connection_over)
    response = client.get("/imovel/GO333333333335")
    assert response.status_code == 200
    data = response.json()
    assert data["proprietarios"][0]["participacao_pct"] == 100.0  # Clamped


def test_get_imovel_200_with_special_situation_statuses(monkeypatch):
    """Test com diferentes status de situação."""
    for status in ["Ativo", "Inativo", "Em Processo"]:
        row = (
            "MS444444444444",
            200.0,
            status,
            "Test Owner 555.666.777-88",
        )

        def _fake_get_connection():
            return _FakeConnection(row)

        monkeypatch.setattr(imovel_service, "get_connection", _fake_get_connection)
        client = TestClient(app)

        response = client.get("/imovel/MS444444444444")

        assert response.status_code == 200
        data = response.json()
        assert data["situacao"] == status
