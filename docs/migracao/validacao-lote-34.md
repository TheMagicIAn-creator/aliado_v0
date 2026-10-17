# Validação do lote 34 — experimentos do zero, rodada atual e PDF por pedido

Data: 17/10/2026. Escopo na [spec 0034](../specs/0034-experimentos.md); requisitos vivos em
[capacidades/experimentos.md](../specs/capacidades/experimentos.md) e [capacidades/nucleo.md](../specs/capacidades/nucleo.md).
Nenhuma chamada paga. O `data/resultados` do pesquisador não foi tocado: as rodadas reais foram feitas numa cópia,
em `tmp/lote-34/resultados`, com a avaliação de 27/09 e o registro de consultas copiados.

## Bateria

| Conferência | Resultado |
|---|---|
| `pytest` | 764 testes passaram (eram 757 na 0.6.0) |
| `ruff check .` | sem apontamentos |
| Testes novos | `test_experiments.py` (10), `test_specs.py` (2), `test_isolation.py` (2) |
| Requisitos vivos citados por testes | EXP-01 a EXP-11 e NUC-01: todos |

## Rodada do zero com os parâmetros de 27/09 (terminal)

`aliado experimento rodar ae-denso-lstm --resultados tmp/lote-34/resultados --frase "consultar o teste"`, com a
separação de 11 janelas, as repetições 13, 29, 42, 71 e 101 e o teto de 2.000 épocas.

| O que foi comparado com 27/09 | Igual? |
|---|---|
| Configuração do treino (código SHA-256) | sim |
| Os 10 arquivos de pesos dos modelos, byte a byte | sim |
| Relatório do treino | sim |
| Relatório e métricas por ensaio da avaliação | sim |
| Os escores de todas as janelas (`escores.npz`) | sim |
| Início das falhas: relatório, menos o aviso e as pastas de origem | sim |

- **Tempo:** 2 min 16 s no total.
- **Registro:** a rodada entrou como a 6ª consulta ao teste, aberta logo antes de pontuar o teste e concluída no
  fim, e o rótulo saiu "Rodada de 17/10/2026 · 6ª vez que os dados de teste foram usados".

## Pela tela (servidor de teste `aliado-web-lote-34`, porta 8782)

- **Rodada atual na aba:** a aba abriu mostrando a rodada da cópia; o Resumo diz "Rodada de 17/10/2026 · 6ª
  vez que os dados de teste foram usados".
- **Botão com os mesmos parâmetros:** com os parâmetros dessa rodada, "Rodar experimento" ficou desativado e
  esmaecido, com o motivo escrito.
- **Rodada nova pela tela:** com a separação de 2 janelas e o teto de 150 épocas, o botão ficou ativo. A janela de
  confirmação disse "já foram usados 6 vezes; esta será a 7ª" e só liberou com a frase. A rodada andou com o
  progresso na tela e terminou em 107 s, e a aba inteira passou a mostrá-la (7ª consulta).
- **PDF:** "Baixar PDF" devolveu `AL-IAdo_AE-Denso-x-AE-LSTM_rodada-002.pdf` (235 KB, 6 páginas: capa, sumário e
  as seções), sem gravar nada nas pastas de resultados.
- **Comparação:** esse PDF, comparado com a rodada atual, deu 28 de 28 indicadores iguais, e a tabela apareceu
  na tela.
- **Console:** só os 400 de `/api/memoria`, que o servidor de teste não tem; nenhum erro do lote.

## O PDF

- **Montagem:** com o matplotlib, sem dependência nova, e o pypdf anexa o `resultado.json` e põe um marcador por
  seção. O pypdf passou a fazer parte do extra `science`.
- **Conteúdo:** capa com a identificação da rodada; sumário com as páginas certas, conferido no teste; seções
  numeradas (objetivo, rodada e reprodutibilidade, resultados por modelo, comparação, por tipo de falha, início
  das falhas, limites, arquivo anexo).
- **Tabelas:** no estilo de publicação, com legenda numerada, notas dos indicadores e continuação na página
  seguinte quando não cabem; cabeçalho e rodapé com "página n de N".
- **Tempo:** cerca de 2 s para montar.
- **Correções durante a validação:**
  - colunas curtas espremidas;
  - uma linha sozinha no alto da página;
  - a versão do AL-IAdo, que saía 0.1.0 porque a instalação de desenvolvimento no `.venv` era antiga. Ela foi
    refeita com `pip install -e . --no-deps --no-build-isolation`, sem baixar nada.

## Menções ao domínio no núcleo

As menções agora estão nas especializações. O teste `test_isolation.py` guarda a lista do que ainda está no
núcleo; o lote 36 a zera.

| Arquivo | Antes | Depois |
|---|---:|---:|
| `interfaces/web/app.py` | 15 | 4 |
| `interfaces/web/science.py` | 15 | 0 |
| `interfaces/web/gpvs_runs.py` | 20 | apagado |
| `interfaces/web/static/ciencia.js` | 14 | 0 |
| `science/detection/registry.py` | 3 | 0 |

## Fica para depois

- **Nomes dos modelos:** ainda estão fixos no código da aba (`MODELOS` em `ciencia.js`); não são menções ao domínio.
- **Figuras no PDF:** fora deste lote.
- **Registro de consultas:** as rodadas de validação ficaram no registro da cópia, não no do pesquisador. O dele
  continua com 5 consultas.
- **Uso no dia a dia:** para usar a seção nova, é preciso reiniciar o AL-IAdo.
