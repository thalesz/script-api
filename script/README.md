# Script — Automação de exportação de dados

Este README descreve a pasta `script/` do projeto: propósito, como executar, configurações importantes, comportamento de checkpoint, logs e resolução de problemas. Há um README geral separado que será criado depois — este documento trata apenas do conteúdo dentro de `script/`.

## Visão geral

- A pasta `script/` contém o código que automatiza a exportação de CSVs por estado no site alvo.
- Estrutura principal:
  - `data/` — checkpoints e dados brutos/processados usados pela automação.
  - `logs/` — registros de execução (ex.: `app.log`).
  - `output/` — arquivos CSV baixados.
  - `src/` — código-fonte Python (autoria principal do bot): `main.py`, `downloader.py`, `config.py`, `logger.py`, etc.

## Requisitos

- Python 3.10+ (ou compatível com as dependências do projeto).
- Dependências listadas em `requirements.txt` na raiz do projeto — instale no virtualenv:

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

- Playwright: caso ainda não esteja instalado, execute:

```bash
playwright install
```

## Configuração de ambiente (.env)

### De onde os parâmetros são lidos

- `script/src/config.py` carrega `.env` automaticamente.
- Ordem de busca:
  1. `.env` na raiz do repositório.
  2. `.env` dentro de `script/`.
- Se a variável não existir, o código usa valor default.

### Variáveis obrigatórias para banco (local)

- `PG_HOST`
- `PG_PORT`
- `PG_DATABASE`
- `PG_USER`
- `PG_PASSWORD`

Exemplo mínimo para rodar local com Postgres em Docker Compose:

```env
PG_HOST=localhost
PG_PORT=5433
PG_DATABASE=sncr
PG_USER=postgres
PG_PASSWORD=postgres
```

Exemplo mínimo para rodar local com Postgres nativo da máquina:

```env
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=sncr
PG_USER=postgres
PG_PASSWORD=postgres
```

## Principais scripts

- `script/src/main.py` — entrypoint CLI. Opções úteis:
  - `--states` — lista de UFs a processar (ex.: `--states SP,MG`).
  - `--reset-checkpoint` — quando presente, força a remoção do checkpoint antes de iniciar. Se não fornecido, o comportamento padrão é lido de `config.py` (`RESET_CHECKPOINT`).
  - `--concurrency` — número de workers (cada worker abre um navegador próprio).
  - `--interactive` — força a busca ao vivo da lista de estados no site (avisa: isso abrirá o navegador); por padrão o script lista uma cópia local de estados para seleção sem abrir o navegador.

- `script/src/downloader.py` — automação: navega até o site, clica em "Dados Abertos", seleciona estado, lê o texto do captcha (`#captcha-text-export`), preenche o campo, dispara o download e grava metadados.

- `script/src/loader.py` — carga no PostgreSQL em modo **insert-only**:
  - cria/verifica as tabelas (`states`, `sncr_records`),
  - carrega CSV em tabela temporária,
  - insere apenas `codigo_incra` que ainda não existem na `sncr_records`,
  - registra resumo por arquivo (`linhas_csv`, `codigos_unicos`, `novos`, `ja_existiam`, `linhas_inseridas`).

- `script/src/auto_loader.py` — orquestra a carga local:
  - encontra todos os CSVs em `script/output/`,
  - chama `loader._process_file(...)` arquivo a arquivo,
  - gera resumo final de sucesso/falha.

- `script/src/config.py` — centraliza parâmetros runtime (HEADLESS, DOWNLOAD_DIR, MAX_ATTEMPTS, TIMEOUTS, CONCURRENCY, CHECKPOINT_DIR, LOGS_DIR, etc.). Edite aqui com cuidado.

- `script/src/logger.py` — cria logger com saída em console e arquivo `logs/app.log`.

## Fluxo de execução e comportamento

- O bot percorre estados (UFs). Para cada estado:
  1. Seleciona o estado no dropdown (mantém "Todos os municípios").
  2. Lê o texto do captcha exibido no seletor `#captcha-text-export`.
  3. Preenche o captcha, submete e aguarda `expect_download()` do Playwright.
  4. Se o site responder com alerta de "Captcha já utilizado. Gere um novo captcha.", o bot gera/atualiza o captcha e tenta novamente.
  5. Em caso de falha, há um loop de retries até `MAX_ATTEMPTS` (configurável).

### Separação de responsabilidades (Scraper x Loader)

- **Scraper (`main.py`/`downloader.py`)**: somente baixa CSV e mantém checkpoint.
- **Loader (`loader.py`/`auto_loader.py`)**: único responsável por tocar no banco.
- A regra de deduplicação fica no banco via insert-only por `codigo_incra`.

Resumo prático:
- se o `codigo_incra` já existe, não reinsere;
- se não existe, insere;
- execução repetida é idempotente.

## Seleção de estados (entrada do usuário)

-- Por padrão o script mostra uma lista local de estados numerada (não abre o navegador) e pede que o usuário escolha usando números.
-- Aceita entradas como `1,2,3` (somente números separados por vírgula). Pressionar `ENTER` processa todos os estados.
- Alternativas:
  - Use `--states SP,MG` para passar UFs diretamente (não abre navegador para listar).
  - Use `--interactive` (ou digitar `i` no prompt) para solicitar a lista ao vivo do site — isso abrirá o navegador para obter os textos/values atuais antes da seleção.

## Checkpoint e retomada

- O progresso é registrado em `data/checkpoints/checkpoint.json` (escrita atômica).
- Ao iniciar, o script carrega o checkpoint e pula UFs já concluídas.
- O comportamento padrão de limpeza do checkpoint é controlado por `config.py` via a variável `RESET_CHECKPOINT`.
  - Se `RESET_CHECKPOINT = True` em `config.py`, o checkpoint será removido automaticamente ao iniciar (a menos que `--reset-checkpoint` seja explicitamente passado para controlar o comportamento na execução atual).
  - Se preferir forçar a remoção somente por linha de comando, deixe `RESET_CHECKPOINT = False` e use `--reset-checkpoint` quando quiser limpar antes de executar.

## Logs e metadados

- Cada download bem-sucedido grava metadados no log: timestamp, UF, município (se aplicável), total de registros (contagem de linhas do CSV).
- Logs vão para `script/logs/app.log` (veja `config.py` para ajustar caminho e nível).

## Diretório de saída

- Arquivos CSV são gravados em `script/output/` por padrão (ajustável em `config.py`).

## Concorrência e cuidado no Windows

- O mecanismo de concorrência usa `ProcessPoolExecutor` e cria um navegador por worker (cada worker abre/fecha seu próprio browser).
- No Windows, aumentar muito o `--concurrency` pode consumir muita RAM/CPU; comece com `1` ou `2` e monitore.

## Execução — exemplos

- Rodar com seleção interativa (modo padrão):

```bash
python script/src/main.py --interactive
```

- Rodar para dois estados e 2 workers, resetando checkpoint:

```bash
python script/src/main.py --states SP,MG --concurrency 2 --reset-checkpoint
```

- Rodar carga no banco para os CSVs já baixados:

```bash
python script/src/auto_loader.py
```

- Testar local 1 estado por vez (download + carga):

```bash
python script/src/main.py --states SP --reset-checkpoint --concurrency 1
python script/src/auto_loader.py
```

## Debug / Resolução de problemas

- Se os downloads não iniciarem:
  - Verifique se o Playwright foi instalado e `playwright install` foi executado.
  - Habilite modo não-headless em `config.py` (`HEADLESS=False`) para observar o fluxo.

- Se permanecerem browsers abertos após a execução:
  - Confirme que a versão do Playwright e dependências estão compatíveis.
  - Execute com `--concurrency 1` para isolar o problema.

- Se o captcha sempre falha:
  - O site pode ter anti-bot adicional. Tente aumentar delays (`SHORT_SLEEP`, `SELECT_TIMEOUT`) em `config.py`.

## Teste de Idempotência do Loader

Existe um teste dedicado para provar que executar a carga duas vezes não duplica registros por `codigo_incra`.

Arquivo:

- `script/tests/test_loader_idempotencia.py`

Executar:

```bash
python -m pytest script/tests/test_loader_idempotencia.py -q
```

Comando único (API + loader):

```bash
python -m pytest api/tests script/tests/test_loader_idempotencia.py -q
```

Resultado esperado:

- Primeira carga insere 1 registro de teste
- Segunda carga não aumenta a contagem (permanece 1)
- O teste remove o dado temporário ao final

## Script de Análise de Performance (EXPLAIN ANALYZE)

Para validar o SLA de 2 segundos com dados reais:

**Arquivo**: `script/analyze_performance.py`

**Comando**:
```bash
python script/analyze_performance.py
```

**O que ele faz**:
- Conecta ao PostgreSQL via credenciais do `.env`
- Insere 3 registros de teste
- Executa `EXPLAIN (ANALYZE, BUFFERS, TIMING)` na query exata da API
- Extrai e exibe métricas de performance no terminal
- Limpa dados de teste automaticamente

**Resultado esperado**:
```
✅ EXPLAIN ANALYZE executado com sucesso

## EXPLAIN ANALYZE - Medição Real
...
- Total Time: 0.05 ms << 2000 ms (SLA)
- Rows Escaneadas: 1
- Usa índice: ✓ PRIMARY KEY B-tree
```

**Alternativa sem BD**: Se PostgreSQL não estiver disponível, o script gera um relatório estimado baseado em teoria de B-tree indexes.

Mais detalhes em: [../docs/PERFORMANCE_INDEXES.md](../docs/PERFORMANCE_INDEXES.md#como-executar-o-script-de-captura-explain-analyze)

## Próximos Passos

- Este README documenta apenas a pasta `script/`

## Navegação

- Voltar ao README principal: [../README.md](../README.md)

## Navegacao

- Voltar ao hub de docs: [../docs/README.md](../docs/README.md)
- Voltar ao README principal: [../README.md](../README.md)
