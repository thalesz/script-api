# Decisões Técnicas Relevantes

Este documento resume as principais decisões técnicas adotadas no projeto, com contexto e impacto prático.

## 1) Separação clara de responsabilidades (Scraper x Loader x API)

- Decisão:
  - Scraper apenas baixa CSVs.
  - Loader é o único responsável por escrever no banco.
  - API apenas consulta e valida dados.
- Motivo:
  - Reduz acoplamento entre etapas.
  - Facilita debug e operação.
- Impacto:
  - Fluxo mais previsível e manutenção mais simples.

## 2) Carga em modo insert-only no Loader

- Decisão:
  - Inserir somente registros novos por codigo_incra.
  - Registros existentes não são atualizados durante carga recorrente.
- Motivo:
  - Garantir idempotência nas reexecuções.
  - Evitar sobrescrita acidental de dados já carregados.
- Impacto:
  - Reexecuções seguras, com auditoria clara de novos x existentes.

## 3) Deduplicação orientada ao banco

- Decisão:
  - Regra de unicidade centralizada no banco por codigo_incra.
- Motivo:
  - O banco é a fonte de verdade para consistência.
  - Evita regras duplicadas no scraper.
- Impacto:
  - Menos risco de divergência entre aplicação e persistência.

## 4) Scraper sem bloqueio por estado já existente no banco

- Decisão:
  - O scraper não decide por dados existentes no banco.
  - Sempre trabalha no escopo solicitado (todos ou UFs especificadas).
- Motivo:
  - Evitar falso positivo de "já processado" por lógica indevida.
- Impacto:
  - Download confiável e controle de carga concentrado no loader.

## 5) Checkpoint para retomada segura

- Decisão:
  - Persistir progresso em checkpoint atômico.
- Motivo:
  - Permitir retomada após falhas sem repetir todo o processo.
- Impacto:
  - Menor tempo de recuperação e maior robustez operacional.

## 6) Tolerância a falhas no download

- Decisão:
  - Retry por estado com número de tentativas configurável.
- Motivo:
  - Lidar com instabilidade de rede, captcha e variações do site-alvo.
- Impacto:
  - Aumento da taxa de sucesso em execuções longas.

## 7) Normalização de nomes de arquivo

- Decisão:
  - Normalizar acentos e caracteres especiais no nome dos CSVs.
- Motivo:
  - Evitar problemas de compatibilidade em diferentes sistemas/terminais.
- Impacto:
  - Nomes estáveis e scripts de automação mais confiáveis.

## 8) Configuração por .env com perfis local e Docker

- Decisão:
  - Local Python usa PG_*.
  - Docker Compose usa DOCKER_*.
- Motivo:
  - Diferenças reais de rede/host entre execução local e container.
- Impacto:
  - Menos erro de conexão por variável incorreta.

## 9) Defaults voltados para execução local simples

- Decisão:
  - Defaults de host/porta e documentação orientados ao onboarding rápido.
- Motivo:
  - Facilitar uso para quem nunca rodou o projeto.
- Impacto:
  - Menor fricção na primeira execução.

## 10) API com validação estrita e retorno seguro

- Decisão:
  - Validar codigo_incra no endpoint e anonimizar CPF na resposta.
- Motivo:
  - Garantir contrato consistente e reduzir exposição de dado sensível.
- Impacto:
  - API mais segura, previsível e adequada para consumo externo.

## 11) Inicialização de schema idempotente

- Decisão:
  - Criação/ajuste de schema sem quebrar reexecuções.
- Motivo:
  - Evitar operações manuais repetitivas e erro em ambiente novo.
- Impacto:
  - Provisionamento mais confiável e repetível.

## 12) Documentação segmentada por responsabilidade

- Decisão:
  - README principal curto e guias detalhados em docs/.
- Motivo:
  - Melhor navegação para perfis diferentes (avaliador, dev, operador).
- Impacto:
  - Curva de aprendizado menor e consulta mais rápida.

## Navegacao

- Voltar ao hub de docs: [README.md](README.md)
- Voltar ao README principal: [../README.md](../README.md)

