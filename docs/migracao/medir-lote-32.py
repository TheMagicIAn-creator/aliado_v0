"""Medição reproduzível e local, com catálogo e perguntas sintéticos; não lê o acervo real.

Execute da raiz: python docs/migracao/medir-lote-32.py --saida data/validacao-lote-32
A pasta deve ser nova. Requer os dois modelos locais já preparados; não faz downloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import time
import types
from pathlib import Path

import numpy as np

from aliado.knowledge.embeddings import LocalEncoder
from aliado.knowledge.library import DocumentLibrary
from aliado.knowledge.reranking import LocalReranker, rank_pages
from aliado.memory.reviewer import needs_review

BASELINE = "98be273"
ROOT = Path(__file__).resolve().parents[2]

# Esperados escritos antes de medir. Cada resposta certa compete com textos do mesmo assunto.
CASES = [
    ("Como detectar uma falha sem exemplos rotulados de falha?", 0),
    ("Qual medida indica quanto dura, em média, o conserto?", 2),
    ("Qual indicador mede o tempo até falhar, e não o tempo para consertar?", 3),
    ("Por que não devo embaralhar janelas sobrepostas entre treino e teste?", 4),
    ("Como preservar a dependência temporal ao estimar a incerteza?", 5),
    ("O que representa a fração de falhas detectadas entre todas as falhas reais?", 6),
    ("O que representa a fração de alarmes que são falhas de verdade?", 7),
    ("Qual métrica conta disparos falsos consecutivos como um único evento?", 8),
    ("Como priorizar os modos de falha usando severidade, ocorrência e detecção?", 9),
    ("Como reduzir alarmes espúrios exigindo persistência acima do limite?", 10),
    ("Como escolher um limite para o erro usando somente registros saudáveis?", 11),
    ("Que métrica mostra a fração do tempo em que o equipamento pode operar?", 12),
]
TEXTS = [
    "An autoencoder trained only on healthy examples detects anomalies when reconstruction error increases. "
    "It does not require labeled examples of faults during training.",
    "A supervised random forest classifies known fault types using labeled examples of healthy and faulty operation.",
    "Mean time to repair (MTTR) is the average duration of corrective maintenance, from failure until restoration.",
    "Mean time to failure (MTTF) measures expected operating time before a non-repairable component fails.",
    "Random splitting of overlapping time windows leaks shared samples between training and test sets. "
    "A chronological split with a purge gap prevents this leakage.",
    "Block bootstrap resamples contiguous groups of observations to preserve temporal dependence when "
    "estimating confidence intervals.",
    "Recall, also called sensitivity, is true positives divided by true positives plus false negatives. "
    "It measures the fraction of actual faults detected.",
    "Precision is true positives divided by true positives plus false positives. It measures how many "
    "positive alarms correspond to actual faults.",
    "Event-based false alarm rate counts contiguous positive healthy windows as one alarm episode and "
    "divides the episodes by healthy monitoring hours.",
    "The risk priority number is the product of severity, occurrence and detection ratings in failure "
    "mode and effects analysis. It helps prioritize failure modes.",
    "A persistence rule requires several consecutive windows above the threshold before raising an alarm. "
    "This filters isolated spikes but may delay detection.",
    "An anomaly threshold can be calibrated as a high percentile of reconstruction errors on a separate "
    "healthy validation set, without consulting the fault test set.",
    "Availability is the fraction of time a repairable system is able to operate. Under steady-state "
    "assumptions it relates mean uptime to mean uptime plus mean repair time.",
    "Accuracy is the proportion of all correctly classified observations, combining healthy and faulty cases.",
    "Window-based false positive rate counts every healthy window above the decision threshold separately.",
    "A histogram of reconstruction errors displays their frequency. It does not alone validate an alarm threshold.",
]
MESSAGES = [query for query, _ in CASES] + [
    "Bom dia", "Obrigado!", "Traga outra fonte.", "Verifique nele.",
    "Meu nome é Rodolfo.", "Prefiro respostas curtas.", "Vamos usar o modelo menor.",
    "Corrigindo: o prazo é novembro.", "Guarde esta definição.", "Meu orientador é Carlos.",
]


class FixedEncoder:
    """Vetores de 384 dimensões; isola o custo da busca do custo da rede de embeddings."""
    fingerprint = "medicao-sintetica-lote-32"

    def split(self, text):
        return [text]

    def encode(self, texts):
        return [[1.0] + [0.0] * 383 for _ in texts]


def catalog(path: Path, count=20_000):
    lib = DocumentLibrary(path, encoder=FixedEncoder())
    random = np.random.default_rng(32)
    with lib._connect(create=True) as db:
        for n in range(26):
            title, original = f"Documento sintético {n}", f"original-{n}.md"
            raw = f"Documento sintético {n}: vida e reparo.".encode()
            (path / original).write_bytes(raw)
            db.execute("INSERT INTO documents VALUES (?, ?, ?, 1, ?, '2026-10-05', ?)",
                       (f"d{n}", title, hashlib.sha256(raw).hexdigest(), original, f"r{n}"))
            db.execute("INSERT INTO runs VALUES (?, ?, 'ready', '[]', ?, '', '', '', '', '2026-10-05')",
                       (f"r{n}", f"d{n}", lib.encoder.fingerprint))
        for start in range(0, count, 1000):
            matrix = random.random((min(1000, count - start), 384))
            rows = [(f"K{i:05d}", f"r{i % 26}", f"vida reparo observação {i}", f"página {i // 26 + 1}",
                     i // 26 + 1, "native", json.dumps(vector.tolist()))
                    for i, vector in enumerate(matrix, start)]
            db.executemany("INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
            db.executemany("INSERT INTO chunk_fts VALUES (?, ?)", [(row[0], row[2]) for row in rows])
        db.commit()
    return lib


def timed(call):
    start = time.perf_counter()
    result = call()
    return result, round(time.perf_counter() - start, 6)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, required=True)
    output = parser.parse_args().saida.resolve()
    output.mkdir(parents=True, exist_ok=False)
    # Carrega só o código da revisão anterior, em memória; não troca arquivos do checkout.
    source = subprocess.run(["git", "show", f"{BASELINE}:src/aliado/knowledge/library.py"],
                            cwd=ROOT, check=True, capture_output=True, encoding="utf-8").stdout
    previous = types.ModuleType("library_before_lot_32")
    exec(compile(source, f"git:{BASELINE}/library.py", "exec"), previous.__dict__)
    library = catalog(output / "catalogo-sintetico")
    old = previous.DocumentLibrary(library.root, encoder=FixedEncoder())
    timings, ids = {}, {}
    for name, instance in (("antes", old), ("agora", library)):
        times = []
        for _ in range(4):
            hits, elapsed = timed(lambda: instance.search("vida reparo", limit=20))
            times.append(elapsed)
        timings[name] = {"primeira_s": times[0], "seguintes_s": times[1:], "mediana_s": statistics.median(times[1:])}
        ids[name] = [item["citation_id"] for item in hits]
    matrix_bytes = library._snapshot()["matrix"].nbytes
    library.close()

    encoder, reranker = LocalEncoder(ROOT / "data/models/minilm"), LocalReranker(ROOT / "data/models/reranker")
    vectors, embed_time = timed(lambda: np.array(encoder.encode(TEXTS)))
    details = []
    for query, expected in CASES:
        vector = encoder.encode([query])[0]
        similarities = np.einsum("ij,j->i", vectors, vector, optimize=False)
        order = sorted(range(len(TEXTS)), key=lambda i: -similarities[i])
        pool = [{"document_id": "sintetico", "page": i + 1, "title": "Manual sintético", "locator": f"página {i + 1}",
                 "text": TEXTS[i]} for i in order]
        (pages, report), elapsed = timed(lambda: rank_pages(reranker, query, pool))
        if report["estado"] != "aplicada":
            raise RuntimeError("O reordenador não executou; esta medição exige os artefatos locais preparados.")
        positions = [page - 1 for _, page in pages]
        details.append({"pergunta": query, "esperada": expected + 1, "antes": order.index(expected) + 1,
                        "depois": positions.index(expected) + 1, "reordenacao_s": elapsed})
    synthetic_60 = [{"document_id": "sintetico", "page": i + 1, "title": "Manual sintético",
                     "locator": f"página {i + 1}", "text": TEXTS[i % len(TEXTS)]} for i in range(60)]
    _, sixty = timed(lambda: rank_pages(reranker, CASES[0][0], synthetic_60))
    result = {
        "base": BASELINE, "rede": reranker.fingerprint, "api_chamadas": 0,
        "desempenho": {"trechos": 20_000, "dimensoes": 384, "tempos": timings,
                       "mesmos_20_resultados": ids["antes"] == ids["agora"], "matriz_bytes": matrix_bytes},
        "qualidade_sintetica": {"perguntas": len(CASES), "paginas": len(TEXTS), "encoder_carga_s": embed_time,
                               "primeiro_antes": sum(row["antes"] == 1 for row in details),
                               "primeiro_depois": sum(row["depois"] == 1 for row in details),
                               "entre_10_antes": sum(row["antes"] <= 10 for row in details),
                               "entre_10_depois": sum(row["depois"] <= 10 for row in details), "detalhe": details,
                               "sessenta_candidatos_s": sixty},
        "revisor": {"mensagens": len(MESSAGES), "chamadas_antes": len(MESSAGES),
                    "chamadas_agora": sum(map(needs_review, MESSAGES)),
                    "decisoes": [{"mensagem": text, "revisar": needs_review(text)} for text in MESSAGES]},
        "limites": "Catálogo e perguntas sintéticos; não mede o acervo real nem qualidade da resposta do Gemini. "
                   "A comparação de qualidade isola a segunda rede, partindo de similaridade de embeddings, "
                   "sem busca híbrida ou reescrita. Não mede economia real de tokens.",
    }
    (output / "medicao.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
