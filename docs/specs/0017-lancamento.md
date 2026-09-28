# Lote 17 — lançamento da v0.1.0

Último lote do [roteiro da v0](../roteiro-v0.md), autorizado em 27/09/2026. Prova os critérios
de pronto numa instalação do zero e deixa o repositório pronto para os commits e a tag do
pesquisador.

## Decisões do pesquisador

| Tema | Decisão |
|---|---|
| Instalação | **Completa:** clone simulado, novo download do encoder pela rede e o Tesseract existente. |
| Python | O **3.14** do PATH, que é o que o README instrui nesta máquina. O ambiente de trabalho usa 3.12. |
| Aceite | Chamadas reais ao `gemini-3.5-flash-lite` na interface da instalação limpa, com um PDF sintético. |
| Guia de uso | O **README vira o guia**. O histórico por lote fica nas specs e no mapa de migração. |

## Escopo implementado

- **README reescrito para quem instala e usa:** o que faz, instalação, `.env`, interface, linha de comando, confiabilidade, FMECA, GPVS, pacote, documentação e pendências.
- **`CHANGELOG.md`** com a versão 0.1.0.
- **Ajustes de texto:**
  - `.env.example` ganha `AL_IADO_TESSERACT_CMD`, comentado;
  - o guia da biblioteca passa a descrever o envio pela interface.
- **Correção no `.gitignore`:** a regra `data/` ignorava também `tests/data/`, e os arquivos de referência dos testes do GPVS ficariam fora do Git. Passou a `/data/`.
- **Correção de privacidade da resposta:**
  - o contexto de memória enviado ao modelo não leva mais o identificador interno das anotações, que o modelo copiava para a resposta;
  - a regra da biblioteca pede um identificador por colchete.
- **Pacote** `dist/v0.1.0/aliado-0.1.0-py3-none-any.whl`.

## Critérios de aceitação

- Um clone simulado (só os arquivos não ignorados) instala pelo README no Python 3.14. Os 331 testes e o Ruff passam, inclusive a reprodução bit a bit dos modelos da origem.
- `aliado biblioteca preparar-modelo`, com um cache vazio, baixa o encoder com os mesmos hashes.
- Na interface da instalação limpa:
  - o PDF sintético é citado com a página certa;
  - um feedback é lembrado numa conversa nova e, corrigido, fica como superado, preservado;
  - a busca na web cita as fontes.
- O pacote instala num ambiente novo, e os comandos e a interface funcionam.
- A auditoria antes do commit não encontra segredos, `.env` nem pastas de dados na lista do Git.
