"""Lote 22: apagar um documento da biblioteca de vez e revogar as deduções tiradas dele."""

from __future__ import annotations

import threading
import time

import pytest

from aliado.knowledge.library import DocumentLibrary
from aliado.memory.store import MemoryStore


class Encoder:
    fingerprint = "synthetic-test-encoder-v1"

    def split(self, text):
        return [text] if text.strip() else []

    def encode(self, texts):
        return [[float("mttf" in t.lower()), float("reparo" in t.lower()), 1.0] for t in texts]


def put(folder, name, text):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def library(tmp_path):
    return DocumentLibrary(tmp_path / "library", encoder=Encoder())


def test_delete_removes_every_version_extraction_index_and_card(tmp_path):
    lib = library(tmp_path)
    first = lib.add(put(tmp_path, "vida.md", "# Vida\nMTTF é o tempo médio até a falha."))
    second = lib.add(put(tmp_path / "v2", "vida.md", "# Vida\nMTTF revisto, vida útil."), title="vida.md")
    kept = lib.add(put(tmp_path, "reparo.md", "# Reparo\nO MTTR mede o tempo médio de reparo."))
    lib.set_card("vida.md", {"titulo": "Vida", "autores": ["Silva"]}, edited=True)
    assert second["version"] == 2 and len(lib.documents()) == 3

    result = lib.delete(first["id"])

    assert result == {"title": "vida.md", "ids": [first["id"], second["id"]], "versions": 2,
                      "chunks": result["chunks"], "leftovers": []} and result["chunks"] > 0
    assert [d["title"] for d in lib.documents()] == ["reparo.md"] and "vida.md" not in lib.cards()
    assert all(hit["title"] == "reparo.md" for hit in lib.search("mttf vida"))
    assert not (lib.root / "extracted" / first["id"]).exists()
    assert not (lib.root / "extracted" / second["id"]).exists()
    assert len(list((lib.root / "originals").iterdir())) == 1
    assert lib.verify() == {"ok": True, "documents": 1, "runs": 1, "issues": []}
    assert lib.search("reparo")[0]["document_id"] == kept["id"]


def test_an_original_shared_with_another_document_stays(tmp_path):
    lib = library(tmp_path)
    source = put(tmp_path, "vida.md", "# Vida\nMTTF é o tempo médio até a falha.")
    old = lib.add(source, title="x.md")
    lib.add(put(tmp_path, "vida2.md", "# Vida\nOutra versão."), title="x.md")
    shared = lib.add(source, title="y.md")  # mesmo conteúdo da versão antiga de x.md, outro título
    original = next(d["original"] for d in lib.documents() if d["id"] == old["id"])
    assert not shared["duplicate"] and next(d["original"] for d in lib.documents() if d["title"] == "y.md") == original
    lib.delete(old["id"])
    assert [d["title"] for d in lib.documents()] == ["y.md"] and (lib.root / original).is_file()
    assert len(list((lib.root / "originals").iterdir())) == 1
    assert lib.verify()["ok"]


def test_unknown_document_is_refused(tmp_path):
    lib = library(tmp_path)
    with pytest.raises(ValueError, match="não encontrado"):
        lib.delete("nada")
    lib.add(put(tmp_path, "vida.md", "# Vida\nMTTF."))
    with pytest.raises(ValueError, match="não encontrado"):
        lib.delete("nada")


def test_only_deductions_from_the_deleted_document_are_revoked(tmp_path):
    store = MemoryStore(tmp_path / "memoria")
    gone = store.add(kind="fato", text="Série: uma falha derruba o sistema.", origin="inferido",
                     source={"document_id": "d1", "title": "recorte.pdf", "page": 1})
    other = store.add(kind="fato", text="O MTTR mede o reparo.", origin="inferido",
                      source={"document_id": "d2", "title": "reparo.pdf", "page": 3})
    mine = store.add(kind="decisao", text="Usar o manual completo.", origin="feedback",
                     source={"document_id": "d1"})
    assert store.revoke_from_documents(["d1"]) == [gone["id"]]
    assert store.get(gone["id"])["status"] == "revogada"
    assert store.get(other["id"])["status"] == "ativa" and store.get(mine["id"])["status"] == "ativa"
    assert store.revoke_from_documents(["d1"]) == []  # já revogada: nada muda


@pytest.fixture
def web(tmp_path):
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    from aliado.interfaces.web.app import WebSettings, create_app

    lib = library(tmp_path)
    memory = MemoryStore(tmp_path / "dados" / "memoria")

    def stream(question, **kwargs):
        yield from ()

    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=lib.root, port=8765, stream=stream,
                           models=[{"alias": "flash", "model_id": "teste"}], library_factory=lambda: lib,
                           memory=memory)
    client = TestClient(create_app(settings), base_url="http://127.0.0.1:8765")
    return {"client": client, "library": lib, "memory": memory, "tmp": tmp_path}


def test_route_needs_the_header_refuses_unknown_and_waits_for_uploads(web):
    client, lib, memory = web["client"], web["library"], web["memory"]
    doc = lib.add(put(web["tmp"], "recorte.md", "# Recorte\nMTTF de sistemas em série."))
    deduction = memory.add(kind="fato", text="Em série, uma falha derruba o sistema.", origin="inferido",
                           source={"document_id": doc["id"], "title": "recorte.md", "page": 1})
    headers = {"x-aliado": "1"}
    assert client.delete(f"/api/biblioteca/{doc['id']}").status_code == 403
    assert client.delete("/api/biblioteca/nada", headers=headers).status_code == 404

    release, original_add = threading.Event(), lib.add

    def slow_add(*args, **kwargs):
        release.wait(5)
        return original_add(*args, **kwargs)

    lib.add = slow_add
    upload = client.post("/api/biblioteca", headers=headers,
                         files={"arquivo": ("novo.md", b"# Novo\nVida util.", "text/markdown")})
    assert upload.status_code == 202
    busy = client.delete(f"/api/biblioteca/{doc['id']}", headers=headers)
    assert busy.status_code == 409 and "Espere" in busy.json()["erro"]
    release.set()
    for _ in range(50):
        if client.get(f"/api/biblioteca/tarefas/{upload.json()['tarefa']}").json()["estado"] == "concluido":
            break
        time.sleep(0.1)

    done = client.delete(f"/api/biblioteca/{doc['id']}", headers=headers)
    assert done.status_code == 200
    assert done.json() == {"apagado": "recorte.md", "versoes": 1, "trechos": 1, "anotacoes_revogadas": 1,
                           "sobras": []}
    assert memory.get(deduction["id"])["status"] == "revogada"
    assert [d["title"] for d in client.get("/api/biblioteca").json()] == ["novo.md"]
    page = client.get(f"/api/biblioteca/{doc['id']}/original")
    assert page.status_code == 404 and "apagado" in page.text and page.headers["content-type"].startswith("text/html")
    assert client.get(f"/api/biblioteca/{doc['id']}/markdown").status_code == 404
