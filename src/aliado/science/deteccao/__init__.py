"""Detecção de falhas por reconstrução (lotes 13 a 15): o que vale para qualquer base de dados, na ordem do método.

1. `particao/`: os blocos de treino, validação, calibração e teste; as sequências; a autocorrelação.
2. `normalizacao/`: a escala robusta pela linha de base do treino.
3. `redes/`: o autoencoder denso e o AE-LSTM.
4. `treino/`: as sementes e o laço de treino.
5. `pesos/`: gravar e carregar os pesos.
6. `inferencia/`: o erro quadrático por variável.
7. `escore/`: a média dos k maiores erros.
8. `limiar/`: a calibração do limiar.
9. `alarmes/`: a confirmação por janelas seguidas e a taxa de alarmes falsos.
10. `metricas/`: as métricas por janela e a incerteza.
11. `registro/`: o registro das consultas aos dados de teste.

Só `redes`, `treino`, `pesos`, `inferencia` e `escore` exigem o PyTorch (extra `ml`); o resto, só o numpy. O que aplica
isto a uma base de dados fica na especialização da pesquisa (lote 36).
"""
