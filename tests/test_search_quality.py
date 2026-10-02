"""Lote 19: busca sem palavras vazias, limite por documento, ficha do documento e medição."""

from __future__ import annotations

import json
import sqlite3
import time

import pytest

import aliado.knowledge.library as library_module
from aliado.agent import prepare_request
from aliado.cli import main
from aliado.knowledge.evaluation import evaluate_search, load_questions
from aliado.knowledge.library import DocumentLibrary
from aliado.knowledge.metadata import check_card, extract_card, named_documents, reference, surname
from aliado.llm.contracts import LLMResult, LLMUsage


class Encoder:
    fingerprint = "synthetic-test-encoder-v1"

    def split(self, text):
        return [text] if text.strip() else []

    def encode(self, texts):
        vectors = []
        for text in texts:
            text = text.lower()
            vector = [float(any(word in text for word in group)) for group in (
                ("vida", "mttf", "lifetime"), ("reparo", "repair", "mttr"), ("rio", "água"),
            )]
            vectors.append(vector + [float(not any(vector))])
        return vectors


def make_library(tmp_path, documents: dict[str, str]) -> DocumentLibrary:
    tmp_path.mkdir(parents=True, exist_ok=True)
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Encoder())
    for name, text in documents.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        library.add(path)
    return library


def titles(hits):
    return [hit["title"] for hit in hits]


def test_stopwords_no_longer_pull_documents_in_the_question_language(tmp_path):
    library = make_library(tmp_path, {
        "manual.md": "# Manual\nde da dos segundo para com uma o a rio",
        "artigo.md": "# Repair\nMean time to repair of transformers.",
    })
    # Antes, "de", "segundo" e "o" traziam o manual pela busca por palavras.
    assert titles(library.search("Qual o tempo de reparo segundo a norma?")) == ["artigo.md"]
    assert library.search_settings["peso_palavras"] == 0.5


def test_each_document_takes_at_most_two_results_unless_candidates_run_out(tmp_path):
    big = "".join(f"# Parte {n}\nreparo trecho {n}\n\n" for n in range(1, 5))
    library = make_library(tmp_path, {"grande.md": big, "pequeno.md": "# Outro\nrepair em outro documento"})
    found = titles(library.search("reparo", limit=3))
    assert found.count("grande.md") == 2 and "pequeno.md" in found
    alone = make_library(tmp_path / "so", {"grande.md": big})
    assert titles(alone.search("reparo", limit=3)) == ["grande.md"] * 3


def test_named_document_is_found_by_author_and_cited_by_reference(tmp_path):
    library = make_library(tmp_path, {"baschel.md": "# Impact\nrio e água", "outro.md": "# Reparo\nreparo"})
    assert "baschel.md" not in titles(library.search("taxa de reparo segundo Baschel"))
    library.set_card("baschel.md", {"titulo": "Impact of Component Reliability", "ano": 2018,
                                    "autores": ["Stefan Baschel", "Elena Koubli"]}, edited=False)
    hits = library.search("taxa de reparo segundo Baschel")
    assert "baschel.md" in titles(hits)
    assert next(h for h in hits if h["title"] == "baschel.md")["referencia"] == "Baschel e Koubli, 2018"
    assert named_documents("segundo BASCHEL et al.", library.cards()) == {"baschel.md"}
    assert named_documents("segundo Koubli", {}) == set()


def test_card_keeps_only_what_the_text_shows():
    text = ("Impact of Component Reliability on Large Scale\nPhotovoltaic Systems' Performance\n"
            "Stefan Baschel 1, Elena Koubli 2\nPublished: 15 June 2018\nhttps://doi.org/10.3390/en11061579")
    raw = {"titulo": "Impact of Component Reliability on Large Scale Photovoltaic Systems' Performance",
           "autores": ["Stefan Baschel", "Elena Koubli", "Pessoa Inventada"], "ano": 2018,
           "doi": "10.3390/en11061579."}
    assert check_card(raw, text) == {
        "titulo": raw["titulo"], "autores": ["Stefan Baschel", "Elena Koubli"], "ano": 2018,
        "doi": "10.3390/en11061579"}
    invented = {"titulo": "A Different Paper", "autores": ["Fulano"], "ano": 2019, "doi": "10.1000/xyz"}
    assert check_card(invented, text) == {}
    assert surname("Eduardo A. Sarquis Filho") == "sarquis"
    assert reference({"autores": ["A. Um", "B. Dois", "C. Três"], "ano": 2020}) == "Um et al., 2020"
    assert reference({"autores": ["IEEE"], "ano": 2007}) == "IEEE, 2007"
    assert reference({"autores": ["P. R. MISHRA", "J. C. JOSHI"], "ano": 1996}) == "Mishra e Joshi, 1996"
    assert reference({"titulo": "Manual", "ano": 2001}) == "Manual (2001)"
    assert reference({}) is None


def test_extract_card_asks_for_structured_output_and_checks_the_answer():
    requests = []

    def execute(request):
        requests.append(request)
        return LLMResult("{}", "google", "lite", request.task_type, usage=LLMUsage(10, 5, 15),
                         structured_data={"titulo": "Manual de Confiabilidade", "autores": ["Lafraia", "Outro"],
                                          "ano": 2001})

    card, result = extract_card(execute, title="manual.pdf",
                                text="/gid00030/gid00035 Manual de Confiabilidade\nJoão Lafraia\n2001")
    assert card == {"titulo": "Manual de Confiabilidade", "autores": ["Lafraia"], "ano": 2001}
    assert requests[0].task_type == "biblioteca-ficha" and requests[0].structured_output
    assert "/gid" not in requests[0].messages[1]["content"]
    assert result.usage.total_tokens == 15


def test_edited_card_wins_and_inferred_card_is_kept(tmp_path):
    library = make_library(tmp_path, {"a.md": "# A\nvida", "b.md": "# B\nrio"})
    assert library.titles_without_card() == ["a.md", "b.md"]
    library.set_card("a.md", {"titulo": "Obra A", "autores": ["Ana Souza"]}, edited=False)
    library.set_card("b.md", {}, edited=False)  # tentativa sem dados: não se repete sozinha
    assert library.titles_without_card() == []
    assert "b.md" not in library.cards()
    saved = library.set_card("a.md", {"titulo": "Obra A, 2ª ed.", "autores": "Ana Souza; Beto Lima", "ano": "2020"},
                             edited=True)
    assert saved["ficha_origem"] == "sua" and saved["ficha"]["autores"] == ["Ana Souza", "Beto Lima"]
    with sqlite3.connect(library.root / "catalog.sqlite3") as db:
        inferred = db.execute("SELECT inferred FROM document_cards WHERE title='a.md'").fetchone()[0]
    assert json.loads(inferred)["titulo"] == "Obra A"
    document = next(d for d in library.documents() if d["title"] == "a.md")
    assert document["referencia"] == "Souza e Lima, 2020"
    with pytest.raises(ValueError):
        library.set_card("inexistente.md", {}, edited=True)


def test_catalog_before_lot_19_works_without_the_cards_table(tmp_path):
    library = make_library(tmp_path, {"a.md": "# A\nvida"})
    with sqlite3.connect(library.root / "catalog.sqlite3") as db:
        db.execute("DROP TABLE document_cards")
    assert library.cards() == {} and library.titles_without_card() == ["a.md"]
    assert titles(library.search("vida")) == ["a.md"]
    assert library.documents()[0]["ficha"] is None


def test_catalog_and_context_carry_the_card(tmp_path):
    library = make_library(tmp_path, {"vida.md": "# Vida\nMTTF é o tempo médio até a falha."})
    library.set_card("vida.md", {"titulo": "Vida útil", "autores": ["Ana Souza"], "ano": 2021}, edited=True)
    request = prepare_request("Qual o MTTF?", library=library)
    catalog = next(m["content"] for m in request.messages if m["content"].startswith("Catálogo da biblioteca"))
    item = json.loads(catalog.split("\n", 1)[1])[0]
    assert item["titulo"] == "vida.md" and item["titulo_da_obra"] == "Vida útil"
    assert item["autores"] == ["Ana Souza"] and item["ano"] == 2021 and item["referencia"] == "Souza, 2021"
    chunks = next(m["content"] for m in request.messages if m["content"].startswith("Trechos recuperados"))
    assert json.loads(chunks.split("\n", 1)[1])["documentos"][0]["referencia"] == "Souza, 2021"


class FakeLibrary:
    def __init__(self, answers):
        self.answers = answers

    def documents(self):
        return [{"title": title} for title in ("a.pdf", "b.pdf", "c.pdf")]

    def search(self, query, *, limit):
        return [{"title": title} for title in self.answers[query]][:limit]


def test_evaluation_counts_hits_positions_and_groups(tmp_path):
    questions = [
        {"id": "P1", "idioma": "pt", "tipo": "autor", "idioma_documento": "en", "pergunta": "q1", "esperados": ["a.pdf"]},
        {"id": "E1", "idioma": "en", "tipo": "conteudo", "idioma_documento": "en", "pergunta": "q2",
         "esperados": ["b.pdf", "c.pdf"]},
        {"id": "E2", "idioma": "en", "tipo": "conteudo", "idioma_documento": "en", "pergunta": "q3", "esperados": ["c.pdf"]},
    ]
    result = evaluate_search(FakeLibrary({"q1": ["b.pdf", "a.pdf"], "q2": ["c.pdf"], "q3": ["a.pdf", "a.pdf"]}), questions)
    assert [row["posicao"] for row in result["detalhe"]] == [2, 1, None]
    assert result["resumo"] == {"perguntas": 3, "acertos": 2, "taxa_de_acerto": 0.667, "mrr": 0.5,
                                "documentos_distintos_medio": 1.33}
    assert result["por_grupo"]["cruzamento"]["outro idioma"]["acertos"] == 1
    assert result["por_grupo"]["idioma"]["en"]["perguntas"] == 2
    with pytest.raises(ValueError, match="fora da biblioteca"):
        evaluate_search(FakeLibrary({}), [questions[0] | {"esperados": ["z.pdf"]}])
    bad = tmp_path / "ruim.json"
    bad.write_text(json.dumps({"perguntas": [{"id": "X", "pergunta": " ", "esperados": ["a.pdf"]}]}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_questions(bad)


def test_cli_evaluates_and_never_overwrites_a_report(tmp_path, monkeypatch, capsys):
    library = make_library(tmp_path, {"a.md": "# A\nreparo", "b.md": "# B\nvida"})
    original = library_module.DocumentLibrary
    monkeypatch.setattr(library_module, "DocumentLibrary", lambda root: original(root, encoder=Encoder()))
    questions = tmp_path / "perguntas.json"
    questions.write_text(json.dumps({"perguntas": [
        {"id": "P1", "idioma": "pt", "tipo": "conteudo", "idioma_documento": "pt", "pergunta": "reparo",
         "esperados": ["a.md"]}]}), encoding="utf-8")
    args = ["biblioteca", "avaliar", "--biblioteca", str(library.root), "--perguntas", str(questions),
            "--saida", str(tmp_path / "medicao")]
    assert main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["resumo"]["acertos"] == 1
    saved = json.loads((tmp_path / "medicao" / "avaliacao-busca.json").read_text(encoding="utf-8"))
    assert saved["busca"]["por_documento"] == 2
    assert main(args) == 2


def test_web_cards_on_upload_completion_and_edit(tmp_path):
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    from aliado.interfaces.web.app import WebSettings, create_app

    library = make_library(tmp_path, {"a.md": "# A\nvida", "b.md": "# B\nrio"})
    calls = []

    def card_extractor(*, title, text):
        calls.append(title)
        card = {} if title == "b.md" else {"titulo": f"Obra {title}", "autores": ["Ana Souza"], "ano": 2018}
        return card, LLMResult("{}", "google", "lite", "biblioteca-ficha", usage=LLMUsage(30, 10, 40))

    def stream(question, **kwargs):
        yield "final", LLMResult("ok", "google", "lite", "critical_reasoning")

    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=library.root, port=8765, stream=stream,
                           models=[{"alias": "flash", "model_id": "gemini-teste"}],
                           library_factory=lambda: library, card_extractor=card_extractor)
    headers = {"x-aliado": "1"}
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8765") as client:
        def wait(job):
            for _ in range(100):
                status = client.get(f"/api/biblioteca/tarefas/{job}").json()
                if status["estado"] in {"concluido", "falhou"}:
                    return status
                time.sleep(0.05)
            raise AssertionError("Tarefa não terminou")

        listing = client.get("/api/biblioteca").json()
        assert [d["ficha_pendente"] for d in listing] == [True, True]
        assert client.post("/api/biblioteca/fichas").status_code == 403
        job = client.post("/api/biblioteca/fichas", headers=headers).json()
        assert wait(job["tarefa"])["resultado"] == {"fichas": 1, "sem_dados": 1, "falhas": 0}
        listing = {d["title"]: d for d in client.get("/api/biblioteca").json()}
        assert listing["a.md"]["referencia"] == "Souza, 2018" and not listing["b.md"]["ficha_pendente"]
        edited = client.post(f"/api/biblioteca/{listing['b.md']['id']}/ficha", headers=headers,
                             json={"titulo": "Obra B", "autores": "Beto Lima", "ano": "2019"}).json()
        assert edited["ficha_origem"] == "sua" and edited["referencia"] == "Lima, 2019"
        uploaded = client.post("/api/biblioteca", headers=headers,
                               files={"arquivo": ("c.md", b"# C\nreparo", "text/markdown")}).json()
        assert wait(uploaded["tarefa"])["resultado"]["referencia"] == "Souza, 2018"
    assert calls == ["a.md", "b.md", "c.md"]
    usage = [json.loads(line) for line in (settings.usage_log).read_text(encoding="utf-8").splitlines()]
    assert [row["task_type"] for row in usage] == ["biblioteca-ficha"] * 3
