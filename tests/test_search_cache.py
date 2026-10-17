"""Lote 32: retratos reutilizados, atualizados por commits e usados em buscas concorrentes."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from test_search_quality import make_library, titles

from aliado.knowledge.chunking import REFERENCES, marked


@pytest.mark.parametrize("wal", [False, True])
def test_warm_index_observes_updates_without_changing_row_count(tmp_path, wal):
    lib = make_library(tmp_path, {"a.md": "# Vida\nvida média"})
    if wal:
        with sqlite3.connect(lib.root / "catalog.sqlite3") as db:
            db.execute("PRAGMA journal_mode=WAL")
    assert lib.search("vida")[0]["status"] == "ready"
    before = lib._snapshot()
    assert lib._snapshot() is before
    with sqlite3.connect(lib.root / "catalog.sqlite3") as db:
        db.execute("UPDATE runs SET status='partial'")
    assert lib.search("vida")[0]["status"] == "partial"
    assert lib._snapshot() is not before
    with sqlite3.connect(lib.root / "catalog.sqlite3") as db:
        db.execute("UPDATE chunks SET vector='[0,0,0,0]'")
    with pytest.raises(ValueError, match="Vetor vazio"):
        lib.search("vida")
    with sqlite3.connect(lib.root / "catalog.sqlite3") as db:
        db.execute("UPDATE chunks SET vector='[1,0,0,0]'")
    assert lib.search("vida")
    lib.close()


def test_cache_refreshes_after_add_reprocess_and_delete(tmp_path):
    lib = make_library(tmp_path, {"a.md": "# Vida\nvida média"})
    original = lib.search("vida")[0]["document_id"]
    before = lib._snapshot()
    source = tmp_path / "b.md"
    source.write_text("# Reparo\nreparo médio", encoding="utf-8")
    other = lib.add(source)
    assert titles(lib.search("reparo")) == ["b.md"]
    assert lib._snapshot() is not before
    before = lib._snapshot()
    lib.add(source, reprocess=True)
    assert lib.search("reparo") and lib._snapshot() is not before
    lib.delete(other["id"])
    assert lib.search("reparo") == []
    assert lib.search("vida")[0]["document_id"] == original
    lib.close()
    assert lib.search("vida")  # reabre sob demanda


def test_concurrent_searches_share_one_immutable_snapshot(tmp_path):
    lib = make_library(tmp_path, {"a.md": "# Vida\nvida média", "b.md": "# Reparo\nreparo médio"})
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(lambda _: (lib.search("vida"), lib._snapshot()), range(16)))
    assert all(titles(hits) == ["a.md"] for hits, _ in result)
    assert len({id(snapshot) for _, snapshot in result}) == 1
    assert not lib._index_db.in_transaction


def test_pool_and_page_ranks_are_cleared_on_empty_results(tmp_path):
    lib = make_library(tmp_path, {"a.md": "# Vida\nvida média"})
    pool, ranked = [], {}
    lib.search("vida", pool=pool, ranked=ranked)
    assert pool and ranked
    lib.search("rio", pool=pool, ranked=ranked)
    assert pool == [] and ranked == {}
    pool.append({"document_id": "old"})
    lib.delete(lib.documents()[0]["id"])
    lib.search("vida", pool=pool, ranked=ranked)
    assert pool == [] and ranked == {}


def test_filtered_reference_vector_does_not_break_prose_search(tmp_path):
    lib = make_library(tmp_path, {"a.md": "# Vida\nvida média", "b.md": "# B\nvida referencias"})
    with sqlite3.connect(lib.root / "catalog.sqlite3") as db:
        db.execute("UPDATE chunks SET locator=?, vector='[0,0,0,0]' WHERE run_id IN "
                   "(SELECT active_run FROM documents WHERE title='b.md')", (marked("página 2", REFERENCES),))
    # Mesmo critério do lote 29: não validar vetores que a pergunta não consulta.
    assert titles(lib.search("vida")) == ["a.md"]
    with pytest.raises(ValueError, match="Vetor vazio"):
        lib.search("referências sobre vida")


def test_cached_search_still_checks_encoder_and_original(tmp_path):
    lib = make_library(tmp_path, {"a.md": "# Vida\nvida média"})
    hit = lib.search("vida")[0]
    with sqlite3.connect(lib.root / "catalog.sqlite3") as db:
        db.execute("UPDATE runs SET encoder='outro-encoder'")
    with pytest.raises(ValueError, match="Encoder"):
        lib.search("vida")
    with sqlite3.connect(lib.root / "catalog.sqlite3") as db:
        db.execute("UPDATE runs SET encoder=?", (lib.encoder.fingerprint,))
    Path(hit["original"]).write_text("alterado", encoding="utf-8")
    with pytest.raises(ValueError, match="Original"):
        lib.search("vida")
