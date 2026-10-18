"""Detecção de falhas por reconstrução (lotes 13–15): o que vale para qualquer base de dados.

`protocol` (partição temporal), `threshold` e `metrics` só dependem do numpy; `models` (os autoencoders) exige o
extra `ml`; `registry` guarda as consultas aos dados de teste. O que aplica isto a uma base de dados fica na
especialização da pesquisa (lote 36).
"""
