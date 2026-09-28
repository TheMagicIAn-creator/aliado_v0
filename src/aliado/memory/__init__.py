"""Memória persistente do AL-IAdo (lote 11): anotações com origem, versões e conflitos.

`store.MemoryStore` guarda as anotações em SQLite local (`data/memoria/`, fora do Git);
`reviewer` propõe anotações a partir das conversas e das fichas de leitura e valida cada
proposta. A triagem das memórias antigas (lotes 02–05) continua fora deste pacote e não
é importada; isso fica para a v1.
"""
