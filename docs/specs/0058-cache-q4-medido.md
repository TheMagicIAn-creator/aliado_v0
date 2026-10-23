# Spec 0058 — o cache q4_0 medido no modelo local

Estado: medido em 22/10/2026, sem commit; o commit fica com o pesquisador. O Ollama voltou para o q8_0, como ele
pediu. Adotar o q4_0 é decisão dele.

## Propósito e decisões

Vem da lista "Depois" do plano de 21/10: a folga da placa e o log do Ollama, incluindo medir o cache q4_0. Responde
também ao lote 46 do relatório em LaTeX, que pedia o cache em 4 bits. A decisão de 20/10 (32 camadas, 32 mil tokens de
contexto e cache q8_0) vale até ele decidir de novo.

**O que muda:** só a variável `OLLAMA_KV_CACHE_TYPE` do servidor do Ollama, no usuário do Windows.
- O AL-IAdo, o Modelfile e o `.env` não mudam.
- O contexto continua em 32 mil tokens: a janela de 8 mil do relatório não entra (decisão de 20/10).
- Nenhum requisito muda.

**A autorização (pesquisador, 22/10/2026):** trocar a variável para q4_0, reiniciar o Ollama e medir, com até 30
chamadas locais, o Gemini simulado e nenhuma chamada paga. No fim, voltar para q8_0 e reiniciar o Ollama.

**O critério, fixado antes da medição:**
- **A base:** a medição de 22/10 com o q8_0, feita depois do lote 57. Foram as mesmas 16 perguntas, as mesmas
  cópias da biblioteca e dos resultados e o mesmo Ollama (0.40.8).
- **As margens de qualidade:** aceitam a variação já vista entre duas rodadas iguais (lote 43: 13 e 11 respostas do
  local).

| Medida | q8_0 (base) | O q4_0 precisa de |
|---|---|---|
| Memória da placa com o modelo carregado | 5.625 MiB | até 5.425 MiB |
| Respostas finais do local | 11 de 16 | ao menos 9 |
| Documento esperado citado pelo local | 9 | ao menos 7 |
| Chamada mediana do local nas leituras de páginas e do documento | 62,5 s | até 75 s |
| Erros do Ollama | 0 | 0 |

## Resultado

O q4_0 passou nos cinco itens.

| Medida | q8_0 | q4_0 |
|---|---|---|
| Memória da placa com o modelo carregado | 5.625 MiB | **5.377 MiB** (248 MiB a menos) |
| Pico da placa durante as 16 perguntas | não medido nessa rodada | 5.385 MiB, em 2.451 amostras |
| Modelo no Ollama: total e na placa | 6,38 e 5,40 GiB (84,7%) | 6,13 e 5,15 GiB (84,1%) |
| Respostas finais do local | 11 de 16 | 13 de 16 |
| Documento esperado citado pelo local | 9 | 12 |
| Marcas inválidas ou cópias de exemplo | 1 marca (P2) | nenhuma |
| Chamada mediana do local nas leituras | 62,5 s | 68,4 s |
| Tempo por pergunta: média e mediana | 75,0 e 71,9 s | 75,7 e 73,8 s |
| Erros do Ollama | 0 | 0 |

**Como ler:**
- **A memória:** a folga é a prevista. O cache de 32 mil tokens passa de 544 MiB (q8_0) para 288 MiB (q4_0); a
  conta dava 256 MiB, e a medida deu 248 MiB.
  - O pico ficou só 8 MiB acima do valor com o modelo carregado: o Ollama reserva tudo ao carregar.
  - A parte do modelo na placa não muda, porque o Modelfile fixa 32 camadas.
- **A qualidade:** não piorou. As 2 respostas e as 3 citações a mais estão dentro da variação entre rodadas iguais,
  então não provam ganho.
- **O tempo:** as leituras de páginas ficaram 9% mais lentas na mediana, dentro do critério. Com uma rodada de cada,
  essa diferença também pode ser variação.

**A decisão fica com o pesquisador:**
- **Ficar com o q4_0:** dá 248 MiB a mais de folga na placa, contra falhas como as da P2 no lote 45. Elas
  aconteceram com o Firefox e o VS Code abertos. Se essa folga basta para eles, só uma medição com os dois abertos
  diria.
- **Manter o q8_0:** guarda o cache mais preciso e as leituras um pouco mais rápidas.
- **O que muda se ele ficar com o q4_0:** só a variável e o README, que hoje recomenda o q8_0.

## O log do Ollama

O item "Depois" pedia achar o log do Ollama, para diagnosticar o próximo erro 500.
- **Onde fica:** o Ollama 0.40.8 grava o log do servidor em `%LOCALAPPDATA%\Ollama\server.log`. A cada início, a
  versão anterior é renomeada para `server-1.log`, `server-2.log` e assim por diante.
- **O que ele guarda:** a configuração com que o servidor iniciou, com as variáveis `OLLAMA_*`.
- **O que não guarda:**
  - o carregamento do modelo, como o tamanho do cache;
  - as respostas com erro 500.

  Só o log de 18/10, da versão anterior, tem as linhas do cache.
- **O reinício da atualização automática:** o de 22/10, às 07:53, não gravou log nenhum.

Por isso, a medição confirmou o q4_0 por três caminhos:
- a variável no registro do Windows, com a hora da troca, comparada com a hora em que o servidor iniciou;
- a configuração no log do próprio servidor em execução;
- o tamanho do modelo carregado, 0,25 GiB menor. Esta é a prova direta.

## Implementação

Nada no produto. A medição fica fora do Git:
- `tmp/lote-58/medir_q4.py`:
  - **O método:** o do lote 46, com as marcas do lote 48.
  - **Um processo por pergunta:** no lote 57, o processo único ficou sem memória na 16ª pergunta.
  - **A placa:** amostrada a cada 0,5 s.
  - **As travas:** o script confere o q4_0 antes de começar e para se o modelo carregar com o tamanho do q8_0.
- `tmp/lote-58/comparar.py`: a tabela das duas rodadas, pergunta por pergunta.

## Aceitação

- **O critério:** aplicado como foi fixado, sobre a medição registrada na [validação](../migracao/validacao-lote-58.md).
- **A volta para o q8_0:** conferida no log do servidor reiniciado, com a variável do usuário em q8_0.
- **Ruff, nos scripts da medição.**
