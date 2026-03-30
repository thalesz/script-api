# Variaveis de Ambiente

Este guia explica quais variaveis usar em cada contexto.

## Regra principal

- Execucao local Python usa PG_*
- Execucao com Docker Compose usa DOCKER_*

## Politica de versionamento de ambiente

- `.env` (com valores reais) nao deve ser commitado.
- `.env.example` fica no repositorio intencionalmente para facilitar onboarding e avaliacao tecnica deste teste.

## Perfil local Python (script e API fora de container)

```env
PG_HOST=localhost
PG_PORT=5433
PG_DATABASE=sncr
PG_USER=postgres
PG_PASSWORD=postgres
```

Notas:
- Use 5433 quando o banco for o container do compose (mapeamento 5433:5432)
- Use 5432 quando o banco for Postgres nativo da maquina

## Perfil Docker Compose

```env
DOCKER_PG_HOST=postgres
DOCKER_PG_PORT=5432
DOCKER_PG_DATABASE=sncr
DOCKER_PG_USER=postgres
DOCKER_PG_PASSWORD=postgres
DOCKER_POSTGRES_DB=sncr
DOCKER_POSTGRES_USER=postgres
DOCKER_POSTGRES_PASSWORD=postgres
```

## Variaveis opcionais comuns

```env
HEADLESS=false
CONCURRENCY=1
RESET_CHECKPOINT=true
STATE_RETRY_ROUNDS=2
MAX_ATTEMPTS=100
DOWNLOAD_TIMEOUT=15000
CAPTCHA_TIMEOUT=7
SHORT_SLEEP=0.8
SELECT_TIMEOUT=5
BASE_URL=https://data-engineer-challenge-production.up.railway.app/
APP_NAME=Desafio API
APP_VERSION=0.1.0
```

## Erros comuns

Host postgres nao resolvido:
- Em execucao local, use PG_HOST=localhost

Conexao recusada:
- Verifique se a porta esta correta (5433 para compose, 5432 para Postgres local)

## Navegacao

- Voltar ao hub de docs: [README.md](README.md)
- Voltar ao README principal: [../README.md](../README.md)
