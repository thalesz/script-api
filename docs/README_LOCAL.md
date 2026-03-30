# Execucao Local (sem Docker para app)

Este guia roda scraper, loader e API localmente.
O banco pode ser PostgreSQL nativo da maquina ou o container do Docker Compose.

## Pre-requisitos

- Python 3.11+
- PostgreSQL ativo (local ou container)
- Ambiente virtual criado

## 1) Criar e ativar ambiente Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 2) Instalar dependencias

```powershell
pip install -r .\script\requirements.txt
pip install -r .\api\requirements.txt
python -m playwright install --with-deps
```

## 3) Configurar .env

```powershell
Copy-Item .env.example .env
```

Minimo obrigatorio:

```env
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=sncr
PG_USER=postgres
PG_PASSWORD=postgres
```

Se estiver usando o banco do Docker Compose (container `desafio_postgres`):

```env
PG_HOST=localhost
PG_PORT=5433
```

## 4) Inicializar banco e schema

```powershell
python .\script\src\init_db.py
```

## 5) Rodar scraper

```powershell
python .\script\src\main.py
```

Exemplo para 1 UF:

```powershell
python .\script\src\main.py --states SP
```

## 6) Rodar loader

```powershell
python .\script\src\auto_loader.py
```

## 7) Subir API

```powershell
cd .\api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 8) Validacao rapida

- Swagger: http://localhost:8000/docs
- Teste API:

```powershell
curl http://localhost:8000/imovel/01001000000
```

## Erros comuns (resolucao rapida)

Erro: `could not translate host name "postgres"`

- Causa: execucao local com host da rede Docker.
- Correcao: no `.env`, usar `PG_HOST=localhost`.

Erro: `3D000` ou `nao existe o banco de dados "sncr"`

- Causa: banco ainda nao criado.
- Correcao: rodar novamente:

```powershell
python .\script\src\init_db.py
```

O init cria o banco automaticamente quando ele ainda nao existe.

## Navegacao

- Voltar ao hub de docs: [README.md](README.md)
- Voltar ao README principal: [../README.md](../README.md)
