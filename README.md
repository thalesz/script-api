# SNCR Scraper Challenge

Documentação principal enxuta. Os guias detalhados foram separados por responsabilidade na pasta docs.

## Início Rápido

1. Copie o ambiente:

```powershell
Copy-Item .env.example .env
```

2. Suba o projeto:

```powershell
docker compose up --build
```

3. Abra a API:

- http://localhost:8000/docs

## Nota sobre .env no teste

- Em projetos reais, o arquivo `.env` com segredos não deve ser commitado.
- Neste desafio, mantivemos `.env.example` versionado de propósito para facilitar setup e avaliação.

## Mapa da Documentação

- Hub central: [docs/README.md](docs/README.md)
- Quickstart: [docs/README_QUICKSTART.md](docs/README_QUICKSTART.md)
- Variáveis de ambiente: [docs/README_ENV.md](docs/README_ENV.md)
- Execução com Docker: [docs/README_DOCKER.md](docs/README_DOCKER.md)
- Execução local: [docs/README_LOCAL.md](docs/README_LOCAL.md)
- Operação e troubleshooting: [docs/README_OPERACAO.md](docs/README_OPERACAO.md)
- Decisões técnicas: [docs/README_DECISOES_TECNICAS.md](docs/README_DECISOES_TECNICAS.md)
- O que faria diferente com mais tempo: [docs/README_MAIS_TEMPO.md](docs/README_MAIS_TEMPO.md)
- Plano de teste: [docs/README_PLANO_TESTE.md](docs/README_PLANO_TESTE.md)

## Guias Técnicos por Componente

- API: [api/README.md](api/README.md)
- Script (scraper e loader): [script/README.md](script/README.md)
- Performance e índices: [docs/PERFORMANCE_INDEXES.md](docs/PERFORMANCE_INDEXES.md)

## Fluxo do sistema

1. Scraper baixa CSVs por UF
2. Loader insere no banco apenas registros novos
3. API consulta os dados por codigo_incra

## Qualidade (testes de API)

Há testes automatizados de integração para contrato e edge cases da API em:

- `api/tests/test_imovel_api.py`

Cenários cobertos: `200`, `404`, `422`, `503` e anonimização de CPF.

Executar testes da API:

```powershell
python -m pytest api/tests -q
```

## Idempotência da Carga (loader)

Há um teste dedicado que comprova que rodar o loader duas vezes não duplica dados por `codigo_incra`:

- `script/tests/test_loader_idempotencia.py`

Executar:

```powershell
python -m pytest script/tests/test_loader_idempotencia.py -q
```

## Execução Unificada de Testes

Para validar API + idempotencia do loader em um comando:

```powershell
python -m pytest api/tests script/tests/test_loader_idempotencia.py -q
```

## SLA de Performance (Etapa 3)

O sistema garante consultas por `codigo_incra` em **< 2 segundos** com índices B-tree.

Para validar a performance com dados reais, execute o script de análise:

```powershell
python script/analyze_performance.py
```

Este script:
- Conecta ao PostgreSQL
- Executa `EXPLAIN ANALYZE` na query da API
- Mostra métricas reais de performance

Detalhes: [docs/PERFORMANCE_INDEXES.md](docs/PERFORMANCE_INDEXES.md#como-executar-el-script-de-captura-explain-analyze)
