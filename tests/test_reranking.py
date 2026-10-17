"""Seleção local de páginas e integração no degrau de leitura, sem chamadas externas."""

from pathlib import Path

import pytest
from test_reading import shelf as reading_shelf

from aliado.agent import prepare_request
from aliado.cli import main
from aliado.knowledge.reranking import ARTIFACT_HASHES, LocalReranker, rank_pages

shelf = reading_shelf


def candidate(page, text="trecho", document="a", **kwargs):
    return {"document_id": document, "page": page, "locator": f"página {page}", "title": document,
            "text": text} | kwargs


class Scores:
    def __init__(self, scores):
        self.scores, self.calls = scores, []

    def score(self, query, texts):
        self.calls.append((query, texts))
        return self.scores


def test_pages_use_best_of_two_chunks_and_stable_ties():
    model = Scores([0.1, 0.9, 0.5, 0.5])
    pages, report = rank_pages(model, "pergunta", [candidate(1), candidate(1), candidate(1, "ignorado"),
                                                  candidate(2), candidate(3)])
    assert pages == [("a", 1), ("a", 2), ("a", 3)]
    assert report["estado"] == "aplicada" and report["candidatos"] == 4
    assert len(model.calls[0][1]) == 4


def test_candidate_limit_is_enforced_before_inference():
    model = Scores(list(range(60)))
    pages, report = rank_pages(model, "Q", [candidate(page) for page in range(75)])
    assert len(model.calls[0][1]) == 60 and report["candidatos"] == 60
    assert pages[0] == ("a", 59) and all(page < 60 for _, page in pages)


def test_cli_prepares_only_the_requested_model(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr("aliado.knowledge.reranking.prepare_model",
                        lambda directory: calls.append(directory) or {"directory": str(directory)})
    target = tmp_path / "modelo"
    assert main(["biblioteca", "preparar-reordenador", "--diretorio", str(target)]) == 0
    assert calls == [target] and "directory" in capsys.readouterr().out
    assert not target.exists()


@pytest.mark.parametrize("scores", [[1], [float("nan"), 2], [float("inf"), 2]])
def test_invalid_scores_preserve_original_order(scores):
    pages, report = rank_pages(Scores(scores), "Q", [candidate(2), candidate(1)])
    assert pages == [("a", 2), ("a", 1)] and report["estado"] == "indisponivel"


def test_missing_model_never_downloads_or_breaks_the_search(tmp_path):
    model = LocalReranker(tmp_path / "ausente")
    pages, report = rank_pages(model, "Q", [candidate(2), candidate(1)])
    assert pages == [("a", 2), ("a", 1)] and report["estado"] == "indisponivel"
    assert not model.directory.exists()
    assert model.score("Q", []) == []


def test_corrupt_artifact_is_refused_before_loading(tmp_path):
    (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="revisão fixa"):
        LocalReranker(tmp_path).score("Q", ["texto"])


def test_only_pages_rung_uses_reranker_and_preserves_priority(shelf):
    class PreferBeta:
        calls = 0

        def score(self, query, texts):
            self.calls += 1
            return [10 if "O beta" in text else 1 if "O alfa" in text else 0 for text in texts]

    lib = shelf.library
    lib.reranker = model = PreferBeta()
    options = {"budget": 60_000, "whole": False, "search": True, "pages": 1}
    query = "Onde aparece o alfa ou o beta?"
    request = prepare_request(query, library=lib, reading=options)
    assert request.metadata["citations"][0]["document_id"] == shelf.article["id"]
    assert request.metadata["citations"][0]["page"] == 2
    assert request.metadata["reading"]["reordenacao"]["estado"] == "aplicada"
    priority = prepare_request(query, library=lib, reading=options | {"priority": [(shelf.book["id"], 7)]})
    assert priority.metadata["citations"][0]["document_id"] == shelf.book["id"]
    focus = prepare_request(query, library=lib, reading=options | {"focus": [shelf.book["id"]]})
    assert focus.metadata["citations"][0]["document_id"] == shelf.book["id"]
    calls = model.calls
    prepare_request(query, library=lib)
    prepare_request(query, library=lib, reading=options | {"search": False, "priority": [(shelf.book["id"], 7)]})
    assert model.calls == calls


def test_failure_preserves_the_pages_that_would_have_been_sent(shelf):
    options = {"budget": 60_000, "whole": False, "search": True, "pages": 2}
    old = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=options)
    shelf.library.reranker = Scores([float("nan")])
    new = prepare_request("Onde aparece o alfa?", library=shelf.library, reading=options)
    assert new.metadata["citations"] == old.metadata["citations"]
    assert new.metadata["reading"]["reordenacao"]["estado"] == "indisponivel"


def test_installed_local_model_ranks_portuguese_query_against_english_passages():
    model = LocalReranker(Path(__file__).resolve().parents[1] / "data/models/reranker")
    if not all((model.directory / name).is_file() for name in ARTIFACT_HASHES):
        pytest.skip("Reordenador local não preparado nesta máquina")
    texts = ["An autoencoder reconstructs its input and can detect faults by reconstruction error.",
             "The solar panel is connected to the inverter using a direct current cable.",
             "Mean time to repair measures the average duration of corrective maintenance."]
    first = model.score("Como um autoencoder detecta falhas?", texts)
    second = model.score("Qual indicador mede o tempo de reparo?", texts)
    assert first.index(max(first)) == 0 and second.index(max(second)) == 2
