# Operacao e Troubleshooting

## Responsabilidades

- Scraper: baixa CSVs para script/output
- Loader: insere no banco apenas registros novos por codigo_incra
- API: consulta por codigo_incra

## Comandos de validacao

Arquivos de saida:

```powershell
Get-ChildItem .\script\output\*.csv
```

Contagem por UF:

```powershell
docker exec desafio_postgres psql -U postgres -d sncr -c "SELECT uf, COUNT(*) AS total FROM sncr_records GROUP BY uf ORDER BY uf;"
```

Endpoint da API:

```powershell
curl http://localhost:8000/imovel/SE000000000000
```

## Problemas comuns

Porta em uso:
- Pare containers antigos com docker compose down

Host postgres nao encontrado no modo local:
- Troque PG_HOST para localhost no .env

Conexao recusada:
- Confirme PG_PORT: 5433 (compose) ou 5432 (Postgres local)

Scraper travado em captcha:
- Rode com menor concorrencia
- Teste HEADLESS=false para observar o fluxo

## Logs importantes

- Aplicacao scraper/loader: script/logs
- Docker scraper: docker compose logs -f scraper
- Docker loader: docker compose logs -f loader

## Navegacao

- Voltar ao hub de docs: [README.md](README.md)
- Voltar ao README principal: [../README.md](../README.md)
