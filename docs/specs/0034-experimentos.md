# Spec 0034 — experimentos do zero, rodada atual e PDF por pedido

Estado: implementado e validado localmente em 17/10/2026; aguarda a revisão e o commit do pesquisador.
Spec de mudança: os requisitos vivos estão em [capacidades/experimentos.md](capacidades/experimentos.md)
(EXP-01 a EXP-11, todos novos) e em [capacidades/nucleo.md](capacidades/nucleo.md) (NUC-01, novo).

## Propósito

O pesquisador quer rodar de novo, do zero, o experimento da pesquisa sempre que quiser, e ver o resultado na
aba Ciência. A aba deve mostrar só a rodada mais nova, sem acumular resultados; para guardar uma rodada, ele
baixa um PDF formal, que serve também para comparar num teste futuro. É o primeiro lote da
[revisão da modularização e das specs](../revisao/2026-10-modularizacao-e-specs.md): o executor não é do GPVS,
que é a base de dados, mas do experimento, e o núcleo não cita a especialização.

## Decisões do pesquisador (17/10/2026)

- O experimento é a comparação **AE Denso × AE-LSTM**; GPVS é a base de dados.
- "Rodar experimento" roda o experimento inteiro, de ponta a ponta, num processo só; não é um encadeamento de
  rotas ou comandos que já existiam.
- O botão fica desativado quando nenhum parâmetro mudou em relação à rodada mostrada.
- Os resultados ficam em JSON e Markdown; o PDF só sai por clique, técnico, profissional, formal, limpo e
  apresentável, com os resultados.
- Antes de rodar, ele digita "consultar o teste"; a janela diz quantas vezes os dados de teste já foram usados.
- "Oficial" só para a avaliação de 27/09/2026; uma rodada nova leva a data e o número da consulta ao teste.
- Nomes de código em inglês (`experiments`, `specializations`); o pacote do mestrado dentro do AL-IAdo; sem
  mecanismo de descoberta por YAML (uma especialização só, por enquanto).
- Specs vivas por capacidade, com o teste que liga cada requisito a um teste; `AGENTS.md` mais enxuto.

## O que muda

- **Núcleo, `src/aliado/experiments/`:** a lista de experimentos (das especializações, sem nomes), a conferência
  dos parâmetros pela declaração do experimento, a pasta `rodada-NNN`, o `resultado.json` gravado por último e de
  uma vez, o `resultado.md`, a rodada atual, a leitura de um resultado salvo (o anexo do PDF ou o JSON) e a
  comparação. O PDF (`pdf.py`) é diagramado com o matplotlib e recebe o anexo e os marcadores pelo pypdf.
- **Núcleo, `src/aliado/specializations/__init__.py`:** acha as especializações percorrendo a pasta.
- **Especialização, `src/aliado/specializations/mestrado/autoencoders.py`:** o experimento AE Denso × AE-LSTM:
  parâmetros (separação, repetições do treino e teto de épocas), o que falta para rodar, a rodada inteira com as
  funções que já existiam, a avaliação de 27/09 no formato de uma rodada, o resultado e o conteúdo do PDF.
- **Rodada atual:** `summary.current` substitui o nome fixo da avaliação de 27/09 no resumo, nos exploradores, no
  início das falhas e no resumo do chat; textos como "5 sementes", "8 de mudança clara" e "27/09" saem da rodada.
- **Interface:** a seção "Rodar e arquivos" vira "Experimento"; saem as rotas `/api/ciencia/gpvs/*`, o
  `gpvs_runs.py` e a listagem `/api/ciencia/resultados`. Entram `/api/experimentos`, `/rodar`, `/cancelar`,
  `/pdf` e `/comparar`. Os botões antigos de preparar, treinar e avaliar por etapa saem com elas.
- **Terminal:** `aliado experimento listar`, `aliado experimento rodar <chave> --parametro nome=valor --frase …`
  e `aliado experimento pdf <chave> --saida arquivo.pdf`. Os comandos por etapa (`aliado ciencia *-gpvs`) ficam.
- **Configuração:** `WebSettings.gpvs_dir` vira `dataset_dir` (padrão: a base do experimento), `gpvs_command`
  vira `experiment_command`, e `aliado web --gpvs` vira `--base`. O registro de consultas recebe o nome da pasta
  da avaliação oficial de quem o chama.

## Fora deste lote

- Mover o código do mestrado para a especialização e zerar as menções no núcleo (lote 36); o lote 34 só não deixa
  nenhuma menção nova entrar (NUC-01, com a lista de transição).
- Figuras no PDF: a aba já tem os gráficos.
- Os nomes dos dois modelos ainda estão fixos no código da aba (`MODELOS` em `ciencia.js`).
- Rodar de novo com os mesmos parâmetros depois de mudar o código: a regra pedida é só pelos parâmetros; o
  terminal continua podendo rodar.

## Aceitação

- `pytest` e `ruff`; testes novos em `tests/test_experiments.py`, `tests/test_specs.py` e `tests/test_isolation.py`.
- Rodada real pelo terminal, com os parâmetros de 27/09, numa cópia dos resultados: números iguais aos de 27/09.
- Na interface, com um servidor de teste: botão desativado com os parâmetros de 27/09; uma rodada com outros
  parâmetros feita pela tela; o PDF baixado e comparado com a rodada atual sem diferenças.
- Nenhuma chamada paga. O registro de consultas real só muda quando o pesquisador aperta o botão.
