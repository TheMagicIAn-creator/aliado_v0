"""Resultados sintéticos: uma avaliação no formato da de 27/09/2026 e a rodada oficial em miniatura."""

from __future__ import annotations

import csv
import json
from pathlib import Path

SHA = "a" * 64
FIELDS = ["modelo", "semente", "ensaio", "detectado", "atraso_ms", "atraso_janelas", "alarmes_pre_falha",
          "janelas_pre_falha", "sensibilidade", "especificidade", "precisao", "f1", "acuracia_balanceada", "mcc",
          "auc_roc", "auc_pr", "vp", "fn", "fp", "vn"]


def synthetic(root: Path) -> Path:
    """Uma avaliação sintética com 2 modelos, 2 treinamentos (sementes 1 e 2) e os 14 ensaios."""
    from aliado.specializations.mestrado import gpvs, summary

    folder = root / summary.EVALUATION
    folder.mkdir(parents=True)
    rows = []
    for kind in ("denso", "lstm"):
        for seed in (1, 2):
            for index, name in enumerate(gpvs.FAULTY):
                vp, fn, fp, vn = 100 + index + seed, 50 - index, index % 3 + seed, 150 + seed
                metrics = summary.from_counts(vp, fn, fp, vn)
                detected = index % 4 != 0
                rows.append({"modelo": kind, "semente": seed, "ensaio": name, "detectado": str(detected),
                             "atraso_ms": 1000.0 + 10 * index + seed if detected else "", "atraso_janelas": 50,
                             "alarmes_pre_falha": index % 2, "janelas_pre_falha": 160,
                             **{k: metrics[k] for k in summary.COUNT_METRICS},
                             "auc_roc": 0.8 + index / 100, "auc_pr": 0.9 - index / 100, "vp": vp, "fn": fn, "fp": fp, "vn": vn})
    with (folder / "metricas_por_ensaio.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    spread = {f"{k}_media": [0.1, 0.9] for k in summary.METRICS} | {"detectados": [9, 10], "atraso_mediano_ms": [900.0, 1100.0],
                                                                     "alarmes_teste_saudavel": [0, 1], "alarmes_pre_falha": [3, 7]}
    model = lambda name: {  # noqa: E731
        "nome": name, "limiar": 2.0, "faixa_sementes": spread, "sementes": {},
        "referencia": {"resumo": {"detectados": 10, "atraso_mediano_ms": 1000.0, **{f"{k}_media": 0.5 for k in summary.METRICS}},
                       "falsos_alarmes": {"teste_saudavel": {"janelas": 263, "janelas_acima": 2, "alarmes": 0, "duracao_s": 5.26,
                                                             "alarmes_por_hora": 0.0, "limite_superior_por_hora": 2050.3,
                                                             "fracao_janelas_acima": 2 / 263,
                                                             "fracao_janelas_acima_ic95": [0.0, 0.019]},
                                          "pre_falha": {"janelas": 2348, "janelas_acima": 55, "alarmes": 7, "duracao_s": 46.96,
                                                        "fracao_janelas_acima": 55 / 2348,
                                                        "fracao_janelas_acima_ic95": [0.018, 0.027]},
                                          "combinado": {"alarmes": 7, "duracao_s": 52.22,
                                                        "limite_superior_por_hora": 950.0}}}}
    report = {"semente_referencia": 2, "top_k": 5, "confirmacao": 3,
              "modelos": {"denso": model("Autoencoder Denso"), "lstm": model("AE-LSTM")},
              "comparacao": [{"objetivo": "Detecta mais falhas", "metrica": "sensibilidade", "maior_e_melhor": True, "media": 0.02,
                              "ic95": [-0.01, 0.04], "n": 14, "mesmo_sinal_sementes": 5, "sementes": 5,
                              "leitura": "sem diferença clara"}]}
    (folder / "relatorio.json").write_text(json.dumps(report), encoding="utf-8")
    (folder / "configuracao.json").write_text(json.dumps({"executado_em": "2026-09-27", "treino": {"pasta": "gpvs-modelos-002"}}),
                                              encoding="utf-8")
    return root


def legacy_results(root: Path) -> Path:
    """A avaliação de 27/09 em miniatura: avaliação sintética, treino e os hashes que o resultado cita."""
    from aliado.specializations.mestrado import autoencoders

    results = synthetic(root / "resultados")
    evaluation = results / autoencoders.LEGACY_EVALUATION / "configuracao.json"
    evaluation.write_text(json.dumps({"executado_em": "2026-09-27", "sha256": "c" * 64,
                                      "treino": {"pasta": "data/resultados/gpvs-modelos-002", "configuracao_sha256": SHA},
                                      "dados": {"hashes": {"F0L": "d" * 64}}}), encoding="utf-8")
    training = results / "gpvs-modelos-002"
    training.mkdir()
    (training / "configuracao.json").write_text(json.dumps({"sha256": SHA, "ambiente": {"python": "3.12"}, "configuracao": {
        "purge": 11, "seeds": [2, 1], "reference_seed": 2, "fractions": [0.5, 0.15, 0.15, 0.2], "top_k": 5,
        "percentile": 99.0, "hyperparameters": {"max_epochs": 2000, "sequence": 8, "patience": 20}}}), encoding="utf-8")
    return results
