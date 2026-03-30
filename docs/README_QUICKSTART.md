# Quickstart

Guia minimo para primeira execucao.

## Pre-requisitos

- Docker e Docker Compose instalados
- PowerShell (Windows) ou terminal equivalente

## Passo a passo (Windows)

1. Crie o arquivo .env:

```powershell
Copy-Item .env.example .env
```

2. Suba os servicos:

```powershell
docker compose up --build
```

3. Acesse a API:

- Swagger: http://localhost:8000/docs

## Resultado esperado

- Postgres ativo
- Scraper gera CSVs em script/output
- Loader insere dados novos no banco
- API responde em http://localhost:8000

## Reiniciar do zero

```powershell
docker compose down -v
docker compose up --build
```

## Navegacao

- Voltar ao hub de docs: [README.md](README.md)
- Voltar ao README principal: [../README.md](../README.md)
