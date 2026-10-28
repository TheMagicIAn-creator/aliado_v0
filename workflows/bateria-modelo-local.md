# Workflow: bateria do modelo local

**Quando usar:** medir como o modelo local (Ollama) responde de verdade: depois de mudar instruções,
roteador, revisor ou leitura, ou para comparar com uma rodada anterior. Segue o [WORKFLOW.md](../WORKFLOW.md).

## Antes de rodar — autorização

- Rodar o modelo real pede a autorização do pesquisador **nesta conversa**, com o número máximo de
  chamadas combinado. Uma autorização de outra rodada não vale para esta.
- Só o modelo local responde. O Gemini entra simulado; chamada paga só com autorização própria.
- Os dados ficam numa cópia, em `tmp/lote-NN/medicao/`: a memória, as conversas e a biblioteca reais
  não são alteradas.

## Preparação

1. Parta do script da rodada anterior (`tmp/lote-70/bateria.py`), com os mesmos casos e a mesma semente,
   para a comparação valer. Mudou o método? Diga o que mudou e por que os números deixam de ser comparáveis.
2. Confira a placa de vídeo (`nvidia-smi`): o modelo precisa de cerca de 5 GB livres. Outros apps com
   aceleração (o app do ChatGPT/Codex, por exemplo) podem ocupar a memória e derrubar o carregamento.
3. Rode primeiro o modo de conferência do script (`--conferir`), que não chama o modelo.

## Rodada

- Rode em segundo plano e acompanhe o contador de chamadas; pare no teto combinado.
- Com o Ollama carregado, o pytest e o próprio script da bateria precisam de `OPENBLAS_NUM_THREADS=1`.
- Confira também a memória do Windows (RAM e arquivo de paginação), além da placa de vídeo. Com o modelo carregado,
  o Ollama ocupa cerca de 7,5 GB. Em 28/10, com o Firefox aberto (6 GB), sobraram 0,3 GB:
  - os 30 processos de caso caíram antes de chamar o modelo ("OpenBLAS error: Memory allocation still failed");
  - na segunda tentativa, o próprio `nvidia-smi` falhou (código 0xC000012D, falta de memória virtual).
- Uma falha no meio (falta de memória, Ollama fora do ar) também é resultado: registre.

## Registro — no mesmo dia

- Escreva o resultado na spec do lote (seção "Aceitação") e no roteiro, com o que melhorou, o que piorou
  e o que não é comparável. **Medição feita e não registrada é o erro do lote 70.**
- Guarde o log e o JSON da comparação em `tmp/lote-NN/medicao/`.
- Separe o que é efeito da mudança do que é ruído do modelo (temperatura 0,6).

## Saída

Tabela curta antes × depois, achados novos e a proposta do próximo passo.
