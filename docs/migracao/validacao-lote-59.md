# Validação do lote 59 — a limpeza do disco

Data: 23/10/2026. Escopo na [spec 0059](../specs/0059-limpeza.md). Sem commit: o commit fica com o pesquisador.
Nenhum modelo foi chamado.

## A limpeza

| Conferência | Resultado |
|---|---|
| Itens da lista autorizada | 22, todos na Lixeira; nenhum ficou no lugar e nenhum deu erro |
| Tamanho somado | 13.151 MiB (12,8 GiB) |
| A Lixeira do C: | de 1,83 GB para 14,65 GB; a capacidade é de 25,8 GB, e nada do que já estava nela saiu |
| Espaço livre no C: | 28,2 GB, o mesmo de antes: ele só volta quando a Lixeira for esvaziada |
| `reranker-mmarco` igual a `reranker` | os mesmos SHA-256 no modelo ONNX e no tokenizador, conferidos antes |
| `.txt` igual ao `.md` do diagnóstico de 20/10 | idênticos byte a byte, conferidos antes |
| `erros-*.npz` sem uso | a chave dos dois não tem os pesos nem as variáveis, e a do explorador tem desde o lote 46 |

A lista, com o tamanho de cada item, fica em `tmp/lote-59/lista.tsv`. O registro da execução fica em
`tmp/lote-59/lixeira.log`, e o script, em `tmp/lote-59/lixeira.ps1`.

## Depois da limpeza

| Conferência | Resultado |
|---|---|
| O reordenador da pasta padrão (`data/models/reranker`) | carrega, confere os hashes e dá 4,84 a uma frase sobre falha de IGBT e −9,22 a uma receita de bolo |
| A bateria rápida (`ferramentas/bateria.py --rapida`) | 36 grupos e 830 testes passando, nenhum ignorado; 129,9 s |
| A cópia fixa das medições (`tmp/lote-46/medicao`) | no lugar |
| Os testes com os dados reais | não rodaram: a base GPVS e os resultados não foram tocados |
