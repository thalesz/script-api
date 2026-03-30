# Execucao com Docker

## Subir ambiente completo

```powershell
docker compose up --build
```

Fluxo executado:
1. Postgres sobe
2. Scraper baixa CSVs
3. Loader insere apenas novos registros
4. API sobe em http://localhost:8000

## Verificacoes

Logs do scraper:

```powershell
docker compose logs -f scraper
```

Logs do loader:

```powershell
docker compose logs -f loader
```

Consulta no banco:

```powershell
docker exec desafio_postgres psql -U postgres -d sncr -c "SELECT uf, COUNT(*) AS total FROM sncr_records GROUP BY uf ORDER BY uf;"
```

## Parar

Sem apagar dados:

```powershell
docker compose down
```

Apagando dados (reset total):

```powershell
docker compose down -v
```

## Navegacao

- Voltar ao hub de docs: [README.md](README.md)
- Voltar ao README principal: [../README.md](../README.md)
