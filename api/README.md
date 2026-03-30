# API README

Guia da API do desafio (FastAPI) para execução local e validação rápida.

## O que esta API faz

- Expõe endpoint para consulta de imóvel por `codigo_incra`.
- Busca dados em `sncr_records` no PostgreSQL.
- Aplica anonimização de CPF no retorno no formato do exemplo oficial da resposta.
- Formato adotado: `***.***.***-72`.

## Endpoints

- `GET /`
- `GET /imovel/{codigo_incra}`

Documentação interativa (Swagger):

- `http://localhost:8000/docs`

## Requisitos

- Python 3.11+
- PostgreSQL com tabela `sncr_records` populada
- Dependências de `api/requirements.txt`

## Configuração (.env)

A API lê variáveis de ambiente via `python-dotenv`.

Ordem de busca:

1. `.env` na raiz do repositório
2. `.env` dentro da pasta `api/`

Variáveis principais:

- `APP_NAME` (default: `Desafio API`)
- `APP_VERSION` (default: `0.1.0`)
- `PG_HOST`
- `PG_PORT`
- `PG_DATABASE`
- `PG_USER`
- `PG_PASSWORD`

Exemplo local usando o Postgres do `docker-compose.yml` do projeto:

```env
PG_HOST=localhost
PG_PORT=5433
PG_DATABASE=sncr
PG_USER=postgres
PG_PASSWORD=postgres
APP_NAME=Desafio API
APP_VERSION=0.1.0
```

## Rodar localmente

Na raiz do projeto:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r .\api\requirements.txt
cd .\api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Testes rápidos

### 1) Health simples

```bash
curl http://localhost:8000/
```

### 2) Consulta por código INCRA

```bash
curl http://localhost:8000/imovel/SE000000000000
```

## Testes automatizados (contrato e edge cases)

Cobertura da suite de integracao em `api/tests/test_imovel_api.py`:

- `200` para imovel existente
- `404` para codigo inexistente
- `422` para codigo invalido
- anonimização de CPF no payload
- `503` para indisponibilidade de banco

Executar os testes:

```powershell
cd .\api
python -m pytest -q
```

## Comportamento Esperado de Erros

- `422` se `codigo_incra` inválido (vazio ou fora do padrão aceito)
- `404` se o código não existir na base
- `503` se o banco estiver indisponível

## Navegação

- Voltar ao README principal: [../README.md](../README.md)

## Exemplo resumido de resposta

```json
{
  "codigo_incra": "SE000000000000",
  "area_ha": 100.0,
  "situacao": "Ativo",
  "proprietarios": [
    {
      "nome_completo": "Nome Exemplo",
      "cpf": "***.***.***-72",
      "vinculo": "Proprietario",
      "participacao_pct": 100.0
    }
  ]
}
```

## Regra de anonimização de CPF

Para evitar divergencia com o contrato de saida esperado, a API segue o formato do exemplo oficial da etapa 4.

Observacao:

- o enunciado textual tem ambiguidade sobre quais 2 digitos manter;
- a implementacao prioriza o formato explicitamente mostrado no JSON de resposta esperada.

Formato adotado:

- mascara os 9 primeiros digitos;
- expoe os 2 ultimos digitos finais.

Exemplo:

- entrada: `123.456.789-72`
- saida: `***.***.***-72`

## Troubleshooting

### Erro: `could not translate host name "postgres"`

Você está rodando a API local fora da rede Docker.

Use no `.env`:

- `PG_HOST=localhost`
- `PG_PORT=5433` (se o banco for o container do compose)

### Erro: conexão recusada

Confira:

- se o Postgres está ligado
- se porta está correta (`5433` para banco do compose, `5432` para banco local nativo)
- se usuário/senha/banco estão corretos

## Navegacao

- Voltar ao hub de docs: [../docs/README.md](../docs/README.md)
- Voltar ao README principal: [../README.md](../README.md)
