# Plano de Teste

Este roteiro e para quem quer validar rapidamente o desafio, sem precisar conhecer toda a arquitetura.

Tempo estimado: 10 a 15 minutos.

## Objetivo

Confirmar que:

1. A stack sobe com um comando.
2. O pipeline scraper -> loader funciona.
3. A API responde consulta por Codigo INCRA.

## Pre-requisitos

- Docker Desktop instalado e rodando.
- PowerShell aberto na raiz do projeto.

## Passo a passo rapido

1. Criar arquivo de ambiente:

```powershell
Copy-Item .env.example .env
```

2. Subir o projeto:

```powershell
docker compose up --build
```

3. Aguardar os servicos concluirem inicializacao.

Sinais esperados nos logs:
- Postgres healthy
- Scraper finalizado
- Loader finalizado
- API ouvindo na porta 8000

4. Abrir Swagger:

- http://localhost:8000/docs

5. Testar endpoint principal:

- GET /imovel/{codigo_incra}
- Exemplo de codigo para teste: `01001000000`

## Validacao minima esperada

- A API retorna status 200 para um codigo existente.
- A resposta inclui os campos principais do imovel.
- CPF vem mascarado no retorno.

## Opcional (validacao de banco)

Executar no PowerShell:

```powershell
docker exec desafio_postgres psql -U postgres -d sncr -c "SELECT uf, COUNT(*) AS total FROM sncr_records GROUP BY uf ORDER BY uf;"
```

Resultado esperado:
- Retorno com contagens por UF (tabela nao vazia).

## Opcional (evidencia de performance com EXPLAIN ANALYZE)

Se quiser validar o requisito de performance por Codigo INCRA, execute:

```powershell
docker exec desafio_postgres psql -U postgres -d sncr -c "EXPLAIN (ANALYZE, BUFFERS) SELECT codigo_incra, pct_obtencao, denominacao, proprietario FROM sncr_records WHERE codigo_incra = '01001000000' LIMIT 1;"
```

O que observar na saida:
- uso de indice da chave primaria em `codigo_incra` (Index Scan ou Index Only Scan);
- tempo de execucao baixo para consulta pontual.

Opcionalmente, rode com outro Codigo INCRA existente para comparar consistencia de tempo.

## Se algo der errado

1. Ver logs da API:

```powershell
docker compose logs -f api
```

2. Ver logs do loader:

```powershell
docker compose logs -f loader
```

3. Reiniciar do zero:

```powershell
docker compose down -v
docker compose up --build
```

## Navegacao

- Voltar ao hub de docs: [README.md](README.md)
- Voltar ao README principal: [../README.md](../README.md)
