"""Lote 28: espelho do AL-IAdo para o Obsidian — notas, links, limpeza do texto, gravação e disparos."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytest.importorskip("starlette")
from starlette.testclient import TestClient  # noqa: E402

from aliado.interfaces.web.app import WebSettings, create_app  # noqa: E402
from aliado.interfaces.web.conversations import ConversationStore  # noqa: E402
from aliado.interfaces.web.obsidian import (  # noqa: E402
    ABOUT,
    FAILURE,
    MANIFEST,
    Note,
    ObsidianSync,
    build_notes,
    note_name,
    obsidian_text,
    write_vault,
)
from aliado.knowledge.library import DocumentLibrary  # noqa: E402
from aliado.llm.contracts import LLMResult, LLMUsage  # noqa: E402
from aliado.memory.store import MemoryStore  # noqa: E402

UTC = timezone.utc
BASE = "http://127.0.0.1:8765"
HEADERS = {"x-aliado": "1"}
LINK = re.compile(r"(?<!\\)\[\[([^\]\[|#]+)\]\]")


def document(doc_id, title, version=1, *, status="ready", created="2026-09-27T10:00:00+00:00", card=None,
             reference=None, issues=()):
    return {"id": doc_id, "title": title, "version": version, "status": status, "created_at": created,
            "issues": list(issues), "original": "originals/abc.pdf", "sha256": "f" * 64,
            "ficha": card, "ficha_origem": "inferida" if card else None, "referencia": reference}


def memory(memory_id, text, *, kind="fato", origin="inferido", status="ativa", source=None,
           created="2026-09-28T12:00:00+00:00", **extra):
    return {"id": memory_id, "kind": kind, "text": text, "origin": origin, "status": status, "skill": None,
            "source": source or {}, "supersedes": None, "superseded_by": None, "conflict_with": None,
            "diverges_skill": False, "created_at": created, "updated_at": created} | extra


def conversation(cid, title, messages, created="2026-09-30T14:05:00+00:00"):
    return {"id": cid, "title": title, "created_at": created, "updated_at": "2026-10-01T09:00:00+00:00",
            "messages": [{"id": f"{cid}-{n}", "created_at": created, **message}
                         for n, message in enumerate(messages)]}


def sample():
    """Uma biblioteca com duas versões e um documento que falhou, memórias de todas as origens e conversas
    com citações de documento, da web e de resultados."""
    card = {"titulo": "Manual de Confiabilidade", "autores": ["J. Lafraia"], "ano": 2001, "doi": "10.1000/abc.1"}
    documents = [
        document("d1", "manual.pdf", 1, card=card, reference="Lafraia, 2001"),
        document("d2", "manual.pdf", 2, card=card, reference="Lafraia, 2001", status="partial",
                 created="2026-09-29T10:00:00+00:00", issues=["Página 3: sem texto utilizável."]),
        document("d3", "guia de campo.md", created="2026-09-28T08:00:00+00:00"),
        document("d9", "falhou.pdf", status="failed"),
    ]
    memories = [
        memory("m-resumo", "Resumo de manual.pdf: O manual apresenta a confiabilidade.",
               source={"document_id": "d1", "title": "manual.pdf", "ficha": True, "page": None}),
        memory("m-fato", "Confiabilidade é uma probabilidade.",
               source={"document_id": "d1", "title": "manual.pdf", "ficha": True, "page": 10}),
        memory("m-velho", "Fato antigo do manual.", status="superada",
               source={"document_id": "d2", "title": "manual.pdf", "ficha": True, "page": 4}),
        memory("m-apagado", "Fato de um recorte apagado.", status="revogada",
               source={"document_id": "dX", "title": "recorte.pdf", "ficha": True, "page": 1}),
        memory("m-orfao", "Fato em vigor de um documento que saiu.",
               source={"document_id": "dY", "title": "outro.pdf", "page": 2}),
        memory("m-pref", "Prefiro respostas curtas.", kind="preferencia", origin="feedback",
               source={"conversation_id": "c1", "message_id": "c1-1", "conversation_title": "MCC", "trecho": "x"}),
        memory("m-web", "A norma foi revista em 2024.", source={
            "conferida_de": "m-fato", "title": "Exemplo", "url": "https://exemplo.org/norma"}),
        memory("m-manual", "Decidi usar a escala de 1 a 10.", kind="decisao", origin="comando",
               source={"manual": True, "conversation_id": None}),
        memory("m-perdida", "Anotação de uma conversa apagada.", kind="perfil", origin="feedback",
               source={"conversation_id": "c-apagada", "conversation_title": "Conversa que saiu"}),
    ]
    answer = ("## Definição\n\nA confiabilidade é uma probabilidade [Kaaa][Kgone], vale $R(t)$ e custa R$ 5 [W1]. "
              "O resultado foi 0,402 [R1]; a marca [R9] e a [Kzzz] não existem.")
    conversations = [
        conversation("c1", "O que é MCC? [resumo]", [
            {"role": "user", "content": "O que é MCC?"},
            {"role": "assistant", "content": answer, "provider": "google", "validation_status": "citation_ids_verified",
             "sources": [
                 {"citation_id": "Kaaa", "document_id": "d1", "title": "manual.pdf", "locator": "página PDF 10",
                  "page": 10, "referencia": "Lafraia, 2001", "original": "C:\\Users\\Fulano\\biblioteca\\x.pdf",
                  "text": "TRECHO-SECRETO", "passagem": "PASSAGEM-SECRETA", "sha256": "a" * 64},
                 {"citation_id": "Kgone", "document_id": "dX", "title": "recorte.pdf", "locator": "página 1",
                  "referencia": "Silva, 1999"}],
             "web_sources": [{"uri": "https://exemplo.org/a", "title": "Exemplo [site]", "domain": "exemplo.org"}],
             "result_sources": [{"citation_id": "R1", "titulo": "Avaliação oficial", "texto": "| a |"}],
             "recuperados": [{"citation_id": "Kxyz", "document_id": "d3", "title": "guia de campo.md",
                              "text": "RECUPERADO-SECRETO"}],
             "memorias_usadas": [{"id": "m-fato"}, {"id": "m-pref"}, {"id": "m-apagado"}],
             "memorias_criadas": [{"id": "m-pref"}],
             "conversas_lembradas": [{"conversation_id": "c2"}, {"conversation_id": "c-apagada"}]},
        ]),
        conversation("c2", "Segunda conversa", [
            {"role": "user", "content": "Oi"},
            {"role": "assistant", "content": "Aviso local.", "provider": "local", "in_context": False},
        ], created="2026-10-01T08:00:00+00:00"),
        conversation("c3", "Vazia", []),
    ]
    return conversations, documents, memories


def test_notes_cover_conversations_documents_and_memories_with_links_that_resolve():
    notes = build_notes(*sample(), tz=UTC)
    assert sorted(notes) == [
        "Anotações/Anotações – 2026-09-30 O que é MCC resumo.md",
        "Anotações/Anotações – Conversa que saiu.md",
        "Anotações/Anotações – Lafraia, 2001.md",
        "Anotações/Outras anotações.md",
        "Conversas/2026-09-30 O que é MCC resumo.md",
        "Conversas/2026-10-01 Segunda conversa.md",
        "Documentos/Lafraia, 2001.md",
        "Documentos/guia de campo.md",
        f"{ABOUT}.md",
    ]
    names = {Path(path).stem for path in notes}
    for path, note in notes.items():
        assert all(target in names for target in LINK.findall(note.text)), path

    talk = notes["Conversas/2026-09-30 O que é MCC resumo.md"].text
    assert "tipo: \"conversa\"\ncriada: 2026-09-30T14:05\n" in talk and "perguntas: 1" in talk
    assert "## Pergunta 1" in talk and "### Resposta" in talk and "#### Definição" in talk  # título rebaixado
    # A citação de uma versão antiga leva ao documento atual; a de um documento apagado vira texto.
    assert "probabilidade [[Lafraia, 2001]] (página PDF 10) Silva, 1999 (página 1), vale $R(t)$" in talk
    assert "custa R\\$ 5 [Exemplo \\[site\\]](<https://exemplo.org/a>)." in talk
    assert "0,402 (resultado da pesquisa: Avaliação oficial); a marca [R9] e a [Kzzz] não existem." in talk
    assert "> **Documentos citados:** [[Lafraia, 2001]] (página PDF 10); Silva, 1999 (página 1)" in talk
    assert "> **Resultados da pesquisa:** Avaliação oficial" in talk
    assert ("> **Anotações usadas:** [[Anotações – Lafraia, 2001]] (1); "
            "[[Anotações – 2026-09-30 O que é MCC resumo]] (1); 1 de um documento que saiu da biblioteca") in talk
    assert "> **Conversas lembradas:** [[2026-10-01 Segunda conversa]]; uma conversa apagada" in talk
    second = notes["Conversas/2026-10-01 Segunda conversa.md"].text
    assert "*Aviso do próprio AL-IAdo, sem resposta do modelo. Ficou fora do histórico da conversa.*" in second
    assert notes["Conversas/2026-09-30 O que é MCC resumo.md"].created == datetime(2026, 9, 30, 14, 5, tzinfo=UTC)

    doc = notes["Documentos/Lafraia, 2001.md"]
    assert 'arquivo: "manual.pdf"\nversão: 2\nsituação: "lido em parte"\nadicionado: 2026-09-27T10:00' in doc.text
    assert 'aliases: ["manual.pdf"]' in doc.text and "# Manual de Confiabilidade" in doc.text
    assert "- **DOI:** [10.1000/abc.1](<https://doi.org/10.1000/abc.1>)" in doc.text
    assert "- Página 3: sem texto utilizável." in doc.text and "- versão 1, adicionada em 27/09/2026" in doc.text
    assert "Anotações tiradas deste documento: [[Anotações – Lafraia, 2001]]" in doc.text
    assert doc.created == datetime(2026, 9, 27, 10, 0, tzinfo=UTC)  # a chegada da primeira versão
    assert "Este documento ainda não tem ficha." in notes["Documentos/guia de campo.md"].text

    group = notes["Anotações/Anotações – Lafraia, 2001.md"].text
    assert 'fonte: "documento"\nem vigor: 3' in group and "Tiradas do documento [[Lafraia, 2001]]." in group
    assert "## Resumo\n\nO manual apresenta a confiabilidade.\n" in group
    assert "- Confiabilidade é uma probabilidade. — p. 10 · inferida" in group
    # A correção vinda da web fica junto da anotação que ela corrige.
    assert "- A norma foi revista em 2024. — inferida · [Exemplo](<https://exemplo.org/norma>)" in group
    assert "> [!note]- Anotações antigas\n> - (superada) Fato antigo do manual. — p. 4 · inferida" in group
    talk_group = notes["Anotações/Anotações – 2026-09-30 O que é MCC resumo.md"].text
    assert "Criadas na conversa [[2026-09-30 O que é MCC resumo]]." in talk_group
    assert "## Preferências\n\n- Prefiro respostas curtas. — sua" in talk_group
    assert "(conversa apagada)" in notes["Anotações/Anotações – Conversa que saiu.md"].text
    others = notes["Anotações/Outras anotações.md"].text
    assert "- Decidi usar a escala de 1 a 10. — sua" in others
    assert "Fato em vigor de um documento que saiu. — p. 2 · inferida · de um documento que saiu da biblioteca" in others
    everything = "\n".join(note.text for note in notes.values())
    assert "Fato de um recorte apagado" not in everything and "falhou" not in everything


def test_private_fields_and_computer_paths_never_leave():
    everything = "\n".join(note.text for note in build_notes(*sample(), tz=UTC).values())
    for secret in ("TRECHO-SECRETO", "PASSAGEM-SECRETA", "RECUPERADO-SECRETO", "Fulano", "originals/", "a" * 64):
        assert secret not in everything
    assert not re.search(r"(?<![A-Za-z])[A-Za-z]:[\\/](?!/)", everything)


def test_the_result_depends_only_on_the_inputs():
    assert build_notes(*sample(), tz=UTC) == build_notes(*sample(), tz=UTC)
    conversations, documents, memories = sample()
    assert build_notes(conversations[::-1], documents[::-1], memories[::-1], tz=UTC) == build_notes(*sample(), tz=UTC)


@pytest.mark.parametrize("text, expected", [
    ('a/b\\c:d*e?f"g<h>i|j#k^l[m]n', "a b c d e f g h i j k l m n"),
    ("Sarquis et al.", "Sarquis et al"),
    ("  ..oculta  ", "oculta"),
    ("CON", "CON (nota)"),
    ("com1.txt", "com1.txt (nota)"),
    ("???", "reserva"),
    ("palavra " * 40, ("palavra " * 12).strip()),
])
def test_note_names_are_valid_on_windows_and_in_links(tmp_path, text, expected):
    name = note_name(text, "reserva")
    assert name == expected and len(name) <= 100
    (tmp_path / f"{name}.md").write_text("x", encoding="utf-8")  # o sistema de arquivos aceita o nome
    assert (tmp_path / f"{name}.md").read_text(encoding="utf-8") == "x"


def test_repeated_names_get_a_number_and_earlier_notes_keep_theirs():
    card = {"titulo": "T", "autores": ["Silva"], "ano": 2020}
    first = document("a1", "um.pdf", card=card, reference="Silva, 2020", created="2026-09-01T00:00:00+00:00")
    later = document("b1", "dois.pdf", card=card, reference="SILVA, 2020", created="2026-09-05T00:00:00+00:00")
    notes = build_notes([], [later, first], [], tz=UTC)
    assert {"Documentos/Silva, 2020.md", "Documentos/SILVA, 2020 (2).md"} <= set(notes)
    assert 'arquivo: "um.pdf"' in notes["Documentos/Silva, 2020.md"].text
    newest = document("c1", "tres.pdf", card=card, reference="Silva, 2020", created="2026-09-09T00:00:00+00:00")
    again = build_notes([], [newest, later, first], [], tz=UTC)
    assert notes["Documentos/Silva, 2020.md"] == again["Documentos/Silva, 2020.md"]
    assert 'arquivo: "tres.pdf"' in again["Documentos/Silva, 2020 (3).md"].text
    # Uma conversa com o nome de um documento também não toma o lugar dele.
    talks = [conversation("c1", "x", [{"role": "user", "content": "oi"}], created="bad-date")]
    assert "Conversas/x.md" in build_notes(talks, [], [], tz=UTC)


def test_answer_text_is_made_safe_and_code_and_formulas_are_kept():
    text = "\n".join([
        "# Título", "Vale $x_1$ e \\(y\\); custa R$ 5 e R$ 10.", "```python", "np.block([[h, n]]) # $x$ <b>", "```",
        "Fora: [[link]] %%oculto%% #etiqueta <img src=http://mau.example/x> ![a](http://mau.example/p.png)",
        "`[[codigo]] $` e [abrir](obsidian://open?vault=x) e [site](https://exemplo.org) [Kaaa]",
    ])
    safe = obsidian_text(text, lambda kind, value: "[[Doc]]" if value == "Kaaa" else None)
    lines = safe.split("\n")
    assert lines[0] == "### Título"
    assert lines[1] == "Vale $x_1$ e $y$; custa R\\$ 5 e R\\$ 10."
    assert lines[2:5] == ["```python", "np.block([[h, n]]) # $x$ <b>", "```"]
    assert lines[5] == ("Fora: \\[\\[link]] \\%\\%oculto\\%\\% \\#etiqueta &lt;img src=http://mau.example/x> "
                        "!\\[a](http://mau.example/p.png)")
    assert lines[6] == "`[[codigo]] $` e [abrir]\\(obsidian://open?vault=x) e [site](https://exemplo.org) [[Doc]]"
    assert not markdown_problems(safe)
    # Um bloco de código sem fim é fechado, para o resto da nota não virar código.
    assert obsidian_text("antes\n```\ncodigo [[x]]").split("\n") == ["antes", "```", "codigo [[x]]", "```"]
    assert obsidian_text("```\ncodigo\n```\n") == "```\ncodigo\n```"  # o que já está fechado fica como veio
    assert obsidian_text("\\[a+b\\]") == "$$a+b$$" and obsidian_text(None) == ""
    assert obsidian_text("colada[Kaaa][Kaaa]", lambda kind, value: "[[D]]") == "colada [[D]] [[D]]"
    # O que não faz mal continua: o link automático, as marcas de texto simples e o cifrão já escapado.
    kept = "<https://doi.org/10.1/x> e CO<sub>2</sub><br>ok, R\\$5"
    assert obsidian_text(kept) == kept
    # Um bloco de código dentro de uma lista fica inteiro, com a marca de citação intocada.
    listed = "1. item\n\n    ```python\n    x = [[1]] # [Kaaa] $y$ <b>\n    ```\n\nfim [Kaaa]"
    assert obsidian_text(listed, lambda kind, value: "[[D]]") == listed[:-6] + "[[D]]"


IMAGE = '<img src="https://mau.example/t.png">'
LOCAL = "file:///C:/pasta/segredo.txt"
LIVE = "Nota Viva"  # um nome que nenhuma nota gerada tem: se "[[Nota Viva]]" sobrar, foi o texto que o pôs
CRAFTED = [
    "!![a](http://mau.example/p.png)", "[![Nota Viva]]", "!![![Nota Viva]]", "![[Nota Viva]]",
    "\\`" + IMAGE + "`", "a ` b\nc ` " + IMAGE + " ` d", '```a`\n<iframe src="https://mau.example/"></iframe>\n```',
    "- x\n  ```\n" + IMAGE, "\\(a\n\n" + IMAGE + "\n\nb\\)", "$" + IMAGE + "$5", "$$\n```\n$$\n" + IMAGE + "\n```",
    "[x][y]\n\n[y]: obsidian://open?vault=x", "[x](obsidian&#58;//open)", "[x](obsidian\\://open)",
    "[x](Sobre esta pasta)", "[x](../segredo.md)", "[x](<obsidian://a>)", "[x](\nobsidian://a)", "<obsidian://open>",
    "R\\$5 e R\\\\$6", "[W" + "9" * 5000 + "]", "texto\n```\ncodigo sem fim", "- item\n  ```\n  codigo sem fim",
    "<div>\n```\n</div>\n\n" + IMAGE, "    " + IMAGE, "> " + IMAGE, "| a |\n|---|\n| " + IMAGE + " |",
    "<!-- c -->" + IMAGE, "<br onload=x>", "[a]: <obsidian://x>\n[a]", "![a][b]\n\n[b]: http://mau.example/p.png",
    "~~~\n" + IMAGE + "\n~~~~~\nfora " + IMAGE, chr(0xE000) + "5" + chr(0xE001) + " e [Kaaa]",
    # Segunda rodada da revisão: destinos que o analisador recusava em silêncio, e definições dentro de
    # citações e listas.
    "[abrir][b]\n\n> [b]: " + LOCAL, "[abrir][b]\n\n- [b]: javascript:alert(1)", "[abrir][b]\n\n1. item\n\n    [b]: " + LOCAL,
    "> [calculadora]: " + LOCAL + "\n\nAbra a [calculadora].", "\\\\`x` [abrir](" + LOCAL + ") `y`",
    "\\\\`x` ![p](file://mau.example/share/p.png) `y`", "`a\nb` ![p](file://mau.example/share/p.png) `c\nd`",
    "\\(a$ [abrir](" + LOCAL + ") $b\\)", "[x](data:text/html,oi)", "![p](vbscript:x)",
    # O que só o Obsidian interpreta, escondido entre trechos que parecem código ou fórmula.
    "\\\\`x` ![[" + LIVE + "]] %%oculto%% #etiqueta `y`", "`a\nb` ![[" + LIVE + "]] `c\nd`",
    "[a](https://x.org/`) ![[" + LIVE + "]] [b](https://y.org/`)", "<https://x.org/`> ![[" + LIVE + "]] <https://y.org/`>",
    "\\(a$ [[" + LIVE + "]] %%oculto%% #etiqueta $b\\)", "\\[a$$ [[" + LIVE + "|clique]] $$b\\]",
    "\\(a$ %% $b\\) texto escondido \\(a$ %% $b\\)", "\\\\([[" + LIVE + "]]\\\\)",
    "# T $$\n[[" + LIVE + "]] %%oculto%%\n$$", "\\( \\)", "$[[" + LIVE + "]]$ e $a %% b$ e $x$ #etiqueta",
    "<br>\n`" + IMAGE + "`", "`x`#etiqueta",
    # Terceira rodada: blocos de código que só aparecem depois da limpeza, o que a conferência não lia
    # (fórmulas, linguagem do bloco, consulta na linha) e comandos de plugin de modelos.
    "<div>\n```query\ntag:#x\n```\n</div>", "<!--\n\n```dataviewjs\ndv.span(1)\n```\n\n-->",
    "<pre>\n\n```query\nx\n```\n\n</pre>", "<details>\n```dataview\nLIST\n```",
    "\\[a\n- [x]: javascript:alert(1)\n\\]\n\n[x]", "    $$a\n> [x]: " + LOCAL + "\n$$\n\nAbra [x].",
    "``` $a`b$", "<div>$$\n~~~$$\\]", "x ` y\nz ` (#etiqueta) ` q", "\\\\`= this.file.name`", "`= this.file.name\n`",
    "<%* await app.vault.adapter.write('x','y') %>", "Texto <% tp.file.title %> fim", "```js\n<%* x %>\n```",
    "`<%* x %>`", "$<%* x %>$", "    <%* x %>", "_#1 no ranking_ e __#2__ e (#3) e \\\\#4",
    "$$\n# T\n[[" + LIVE + "]]\n$$", "[[" + LIVE + "]].pdf <% x %>",
]
ALLOWED_TAG = re.compile(r"</?(?:br|sub|sup)\s*/?>", re.IGNORECASE)
PLAIN = {"", "python", "text", "js", "json", "bash"}
HASH = r"(?<![^\W_])(?<![/#&])#(?=[^\s#])"


def markdown_problems(text: str, links: tuple[str, ...] = ("Doc",)) -> list[str]:
    """O que ainda está vivo no texto pronto, para um analisador de Markdown que aceita qualquer destino de
    link e não junta o texto escapado ao resto. `links` são os nomes das notas que o gerador pode ligar."""
    from markdown_it import MarkdownIt

    parser = MarkdownIt("commonmark").enable(["table", "strikethrough"]).disable("text_join")
    parser.validateLink = lambda url: True
    for name in sorted(links, key=len, reverse=True):
        text = text.replace(f"[[{name}]]", "LINKDANOTA")  # os links gerados, pelo nome exato da nota
    tokens = parser.parse(text + "\n\nDEPOISDOTEXTO\n")
    found = ["comando de plugin de modelos"] if "<%" in text else []
    for token in tokens:
        if token.type == "fence" and (token.info.split() or [""])[0].lower() not in PLAIN:
            found.append(f"bloco de código em {token.info!r}")
        if token.type == "html_block":
            found.append("bloco de HTML")
        for child in token.children or ():
            if child.type == "image" or (child.type == "html_inline" and not ALLOWED_TAG.fullmatch(child.content)):
                found.append(child.type)
            if child.type == "link_open" and not re.match(r"(?i)https?://|mailto:", child.attrGet("href") or ""):
                found.append(f"link para {child.attrGet('href')}")
            if child.type == "code_inline" and child.content.lstrip().startswith(("=", "$=")):
                found.append("consulta de plugin em código na linha")
            if child.type == "text" and re.search(r"\[\[|%%|" + HASH, child.content):
                found.append(f"marca do Obsidian em {child.content!r}")
    if not (tokens[-3].type == "paragraph_open" and tokens[-3].level == 0 and tokens[-2].content == "DEPOISDOTEXTO"):
        found.append("o texto seguinte cairia dentro de um bloco")
    return found


@pytest.mark.parametrize("text", CRAFTED)
def test_text_crafted_against_the_cleaner_never_stays_live(text):
    answer = obsidian_text(text, lambda kind, value: "[[Doc]]" if value == "Kaaa" else None)
    assert not markdown_problems(answer), answer
    conversations = [conversation("c1", text, [{"role": "user", "content": text},
                                                {"role": "assistant", "content": text},
                                                {"role": "user", "content": "segunda pergunta"}])]
    memories = [memory("m1", text, kind="decisao", origin="comando", source={"manual": True}),
                memory("m2", f"Resumo de a.pdf: {text}", source={"document_id": "d1", "ficha": True, "page": None})]
    documents = [document("d1", text + ".pdf", card={"titulo": text, "autores": [text], "ano": 2020, "doi": text},
                          reference=text, issues=[text])]
    notes = build_notes(conversations, documents, memories, tz=UTC)  # nenhum texto derruba a exportação
    names = tuple(Path(path).stem for path in notes)
    assert LIVE not in names
    assert not any(f"[[{LIVE}]]" in note.text or f"[[{LIVE}|" in note.text for note in notes.values())
    for path, note in notes.items():
        front, _, body = note.text.partition("\n---\n") if note.text.startswith("---\n") else ("", "", note.text)
        assert "[[" not in front and "<%" not in front, path  # as propriedades também não ligam nem executam nada
        assert not markdown_problems(body, names), path
    talk = next(note.text for path, note in notes.items() if path.startswith("Conversas/"))
    assert "\n## Pergunta 2\n" in talk and talk.endswith("\nsegunda pergunta\n")
    # A pergunta seguinte continua sendo um título, fora de qualquer bloco de código aberto pelo texto.
    from markdown_it import MarkdownIt
    headings = [token.map[0] for token in MarkdownIt("commonmark").parse(talk) if token.type == "heading_open"]
    assert talk.split("\n").index("## Pergunta 2") in headings


def test_blocks_that_obsidian_would_run_go_as_text_and_headings_stay_below_the_answer():
    assert obsidian_text("```query\npath:Conversas senha\n```") == "```text\npath:Conversas senha\n```"
    assert obsidian_text("```mermaid\ngraph TD\n```").startswith("```text\n")
    assert obsidian_text("- x\n\n  ~~~dataviewjs title=a\n  dv.span(1)\n  ~~~").split("\n")[2] == "  ~~~text"
    assert obsidian_text("```Python title=x\nx = 1\n```") == "```python\nx = 1\n```"
    assert obsidian_text("```\nx\n```") == "```\nx\n```"
    # A consulta de plugin em código na linha perde o prefixo por um caractere invisível.
    assert obsidian_text("`$= dv.current()` e `= this.file` e `a = 1`") == (
        "`\u200b$= dv.current()` e `\u200b= this.file` e `a = 1`")
    # Títulos feitos com uma linha de = ou -, e os de dentro de citações e listas, não sobem acima de "Resposta".
    assert obsidian_text("Um parágrafo comum.\n---\nOutro.") == "Um parágrafo comum.\n\n---\nOutro."
    assert obsidian_text("Título grande\n===\n\ntexto") == "Título grande\n\n===\n\ntexto"
    assert obsidian_text("> # Em citação\n\n- # Em lista\n\n1. ## Numerada") == (
        "> ### Em citação\n\n- ### Em lista\n\n1. #### Numerada")
    # Num campo de uma linha, "# x" e "> x" não viram título nem citação, e "|" não quebra uma tabela.
    notes = build_notes([], [document("d1", "a.pdf", issues=["# Pendência", "> citação", "a | b"])], [
        memory("m1", "# Título na anotação", source={"document_id": "d1", "page": 3}),
        memory("m2", "Resumo de a.pdf: # Título no resumo", source={"document_id": "d1", "ficha": True, "page": None}),
    ], tz=UTC)
    doc, group = notes["Documentos/a.md"].text, notes["Anotações/Anotações – a.md"].text
    assert "- \\# Pendência\n- \\> citação\n- a \\| b" in doc
    assert "\n\\# Título no resumo\n" in group and "- \\# Título na anotação — p. 3 · inferida" in group
    web = {"web_sources": [{"uri": "https://exemplo.org/a|b", "title": "Guia | Exemplo"}]}
    talk = build_notes([conversation("c1", "t", [{"role": "assistant", "content": "| Fonte | Nota |\n|---|---|\n| [W1] | ok |",
                                                 **web}])], [], [], tz=UTC)["Conversas/2026-09-30 t.md"].text
    assert "| [Guia \\| Exemplo](<https://exemplo.org/a%7Cb>) | ok |" in talk
    # Nas propriedades, "[[x]]" não vira link entre notas.
    linked = build_notes([], [document("d1", "[[Nota]].pdf", reference="[[Nota]]")], [], tz=UTC)
    front = next(note.text for path, note in linked.items() if path.startswith("Documentos/")).split("\n---\n")[0]
    assert 'arquivo: "[ [Nota] ].pdf"' in front and 'referência: "[ [Nota] ]"' in front and "[[" not in front


def test_ordinary_answers_keep_their_formulas_code_and_formatting():
    fourier = "A transformada é $\\mathcal{F}[f](\\omega)$ e o código é `fft(x)`.\n\n```python\nx = [[1]]\n```"
    assert obsidian_text(fourier) == fourier.replace("[f](", "[f] (")  # o espaço não muda a fórmula
    from aliado.interfaces.web import obsidian

    for text in ("Temos $$E[X](t) = \\int x\\,dF$$ e depois **negrito**.", "O termo $a[i](j)$ vale 1 e `b[i](j)` também.",
                 "| a | b |\n|---|---|\n| $x_1$ | `y` |", "$$\n\\begin{aligned}\na &= b \\\\\nc &< d\n\\end{aligned}\n$$",
                 "Custa de $5 a $10 (US$5).", "Veja [o guia](https://exemplo.org/a) e <https://exemplo.org/b>.",
                 "Cardinalidade $\\#A = n$ e $n = \\#\\{x\\}$.", "Resultado: _#1 no ranking_ e a issue \\#12.",
                 "- [ ] tarefa\n- [x] feita\n\n> citação\n\n1. um\n   - dois"):
        # A forma normal passa na conferência: o texto não cai na forma sem marcação nem é trocado pelo aviso.
        normal, check = obsidian._render(text, None, strict=False)
        assert not obsidian._live(check.strip("\n")) and obsidian_text(text) == normal.strip("\n"), normal
    # Sozinha na linha, a quebra de linha vira texto, para não abrir um bloco de HTML; no meio da frase, fica.
    assert obsidian_text("<br>\nTexto **negrito** com `código` e $x^2$.") == "&lt;br>\nTexto **negrito** com `código` e $x^2$."
    unchanged = ("Linha um<br>linha dois, CO<sub>2</sub>.", "Cardinalidade $\\#A = n$.", "issue \\#12 resolvida",
                 "Ver [ref][1].\n\n[1]: https://exemplo.org", "E-mail <mailto:a@b.org>.",
                 "Exemplo:\n\n    # comentário\n    x = 1")
    for text in unchanged:
        assert obsidian_text(text) == text
    assert obsidian_text("Custa de $5 a $10 (US$5).") == "Custa de \\$5 a \\$10 (US\\$5)."
    assert obsidian_text("Resultado: _#1 no ranking_.") == "Resultado: _\\#1 no ranking_."
    # Quando nem a forma sem marcação passa na conferência, entra a frase fixa.
    live, obsidian._live = obsidian._live, lambda text: True
    try:
        assert obsidian_text("qualquer texto") == obsidian.UNSAFE_TEXT
    finally:
        obsidian._live = live
    # Uma linha enorme (o tamanho máximo de uma pergunta) não segura a exportação.
    started = time.perf_counter()
    for huge in ("x" * 20000, "palavra " * 2500, "pergunta\n" + " " * 19989 + "x", ">" * 20000, "`" * 20000):
        assert obsidian_text(huge)
    assert time.perf_counter() - started < 5


def test_malformed_records_and_huge_texts_do_not_stop_the_export():
    conversations = [
        "abc", None, {"id": "c0", "messages": "x"},
        {"id": "c1", "title": None, "created_at": "1969-01-01T00:00:00", "messages": [
            {"role": "user", "content": None}, {"role": ["x"], "content": "y"},
            {"role": "assistant", "content": "[W1] [K1] [R1]", "validation_status": [], "provider": {}, "sources": "x",
             "web_sources": ["x", 3], "result_sources": [None], "memorias_usadas": [{"id": []}], "results_status": []}]},
        {"id": "c2", "created_at": "0001-01-01T00:00:00", "messages": [{"role": "user", "content": "oi"}]},
    ]
    documents = [None, "x", {"id": "d0"}, {"id": "d", "title": "x.pdf", "issues": 3, "status": [], "ficha": "x"},
                 {"id": "e", "title": "y.pdf", "version": "2"}, {"id": "f", "title": "y.pdf", "version": 1, "ficha": {
                     "autores": "x", "ano": [], "doi": 7, "titulo": None}}]
    memories = [None, {"id": "m0"}, {"id": "m1", "status": [], "origin": [], "kind": {}, "source": "texto", "text": None},
                {"id": "m2", "text": "ok", "source": {"document_id": [], "page": "x", "url": 5, "conversation_id": {}}}]
    notes = build_notes(conversations, documents, memories)  # com o fuso do computador, como no servidor
    assert any(path.startswith("Conversas/") for path in notes) and "Documentos/x.md" in notes
    # Duas versões sem número: a ordem de chegada não muda o resultado.
    twins = [{"id": "a", "title": "z.pdf", "created_at": "2026-01-01"}, {"id": "b", "title": "z.pdf", "created_at": "2026-01-02"}]
    assert build_notes([], twins, [], tz=UTC) == build_notes([], twins[::-1], [], tz=UTC)
    # Muitos começos de fórmula sem fim não seguram a exportação.
    started = time.perf_counter()
    assert obsidian_text("\\[x" * 8000).count("x") == 8000 and obsidian_text("$a " * 8000)
    assert time.perf_counter() - started < 10


def test_card_title_and_memory_fields_cannot_inject_links_images_or_comments():
    doi = "10.1000/x](obsidian://a) ![i](http://mau.example/p.png) [[Sobre esta pasta]]"
    documents = [document("d1", "a.pdf", card={"titulo": "T %%x%%", "autores": ["A"], "ano": 2020, "doi": doi},
                          reference="Silva, 2020")]
    talks = [conversation("c1", "Custo %%oculto%% de $5 `x`", [{"role": "user", "content": "oi"}])]
    memories = [memory("m1", "Veja !![x](https://mau.example/p.png) e [![Sobre esta pasta]].", kind="perfil",
                       origin="feedback", source={"conversation_id": "c1"})]
    notes = build_notes(talks, documents, memories, tz=UTC)
    doc = notes["Documentos/Silva, 2020.md"].text
    assert "- **DOI:** 10.1000/x\\]" in doc and "](<https://doi.org/" not in doc and not markdown_problems(doc.split("---\n", 2)[2])
    assert "[[Sobre esta pasta]]" not in doc
    talk = next(path for path in notes if path.startswith("Conversas/"))
    assert "%%" not in talk and "%%" not in notes[talk].text.replace("\\%\\%", "")
    group = notes[next(path for path in notes if path.startswith("Anotações/"))].text
    assert "%%" not in group.replace("\\%\\%", "") and "[[Sobre esta pasta]]" not in group
    assert not markdown_problems(group.split("---\n", 2)[2], tuple(Path(path).stem for path in notes))


def test_corrections_and_conflicts_are_grouped_and_counted_as_in_the_memory_tab():
    documents = [document("d1", "a.pdf", reference=None)]
    memories = [
        memory("m-fato", "Fato do documento apagado.", status="revogada",
               source={"document_id": "dX", "title": "apagado.pdf", "ficha": True, "page": 1}),
        # A correção em vigor não some com o documento da anotação que ela corrigiu.
        memory("m-correcao", "Correção vinda da web.", source={"conferida_de": "m-fato", "url": "https://exemplo.org/a"}),
        memory("m-minha", "Uso a escala de 1 a 10.", kind="decisao", origin="comando",
               source={"document_id": "d1"}, conflict_with="m-inferida"),
        memory("m-inferida", "A escala seria de 1 a 5.", kind="decisao", status="conflito",
               source={"document_id": "d1"}, conflict_with="m-minha"),
        memory("m-a", "Ciclo A.", source={"conferida_de": "m-b"}),
        memory("m-b", "Ciclo B.", source={"conferida_de": "m-a"}),
    ]
    notes = build_notes([], documents, memories, tz=UTC)
    others = notes["Anotações/Outras anotações.md"].text
    assert "Correção vinda da web." in others and "Ciclo A." in others and "Ciclo B." in others
    assert "Fato do documento apagado" not in others
    group = notes["Anotações/Anotações – a.md"].text
    assert 'em vigor: 1\n' in group  # a anotação em conflito não conta como valendo
    assert "- A escala seria de 1 a 5. — inferida · em conflito" in group
    about = notes[f"{ABOUT}.md"].text
    for label in ("**sua:**", "**inferida:**", "**em conflito:**", "**superada:**", "**revogada:**", "**p. 10:**",
                  "**diverge da skill:**", "**em vigor:**"):
        assert label in about  # uma nota para cada marca que aparece nas anotações


def vault_files(root: Path) -> list[str]:
    return sorted(str(path.relative_to(root)).replace("\\", "/") for path in root.rglob("*") if path.is_file())


def test_vault_writes_only_what_changed_and_never_touches_other_files(tmp_path):
    root = tmp_path / "cofre"
    notes = build_notes(*sample(), tz=UTC)
    assert write_vault(root, notes) == {"notas": 9, "escritas": 9, "removidas": 0}
    assert json.loads((root / MANIFEST).read_text(encoding="utf-8")) == {"versao": 1, "arquivos": sorted(notes)}
    graph = json.loads((root / ".obsidian" / "graph.json").read_text(encoding="utf-8"))
    assert [group["query"] for group in graph["colorGroups"]] == ["path:Conversas", "path:Documentos", "path:Anotações"]
    assert graph["showTags"] is False and graph["hideUnresolved"] is True

    mine = root / "Conversas" / "Minha nota.md"
    mine.write_text("minha", encoding="utf-8")
    (root / "ideias.md").write_text("solta", encoding="utf-8")
    (root / ".obsidian" / "graph.json").write_text('{"colorGroups": []}', encoding="utf-8")
    stamps = {path: (root / path).stat().st_mtime_ns for path in [*notes, MANIFEST]}
    assert write_vault(root, notes) == {"notas": 9, "escritas": 0, "removidas": 0}
    assert stamps == {path: (root / path).stat().st_mtime_ns for path in [*notes, MANIFEST]}  # nem o registro muda

    # Uma edição numa nota gerada é substituída; a nota de uma conversa renomeada sai, a nova entra.
    edited = root / "Documentos" / "guia de campo.md"
    edited.write_text("rabisco", encoding="utf-8")
    conversations, documents, memories = sample()
    conversations[1]["title"] = "Outro nome"
    renamed = build_notes(conversations, documents, memories, tz=UTC)
    # Três gravações: a nota editada, a conversa com o nome novo e a conversa que tem um link para ela.
    assert write_vault(root, renamed) == {"notas": 9, "escritas": 3, "removidas": 1}
    assert "[[2026-10-01 Outro nome]]" in (root / "Conversas" / "2026-09-30 O que é MCC resumo.md").read_text(
        encoding="utf-8")
    assert edited.read_text(encoding="utf-8") == notes["Documentos/guia de campo.md"].text
    files = vault_files(root)
    assert "Conversas/2026-10-01 Outro nome.md" in files and "Conversas/2026-10-01 Segunda conversa.md" not in files
    assert mine.read_text(encoding="utf-8") == "minha" and (root / "ideias.md").read_text(encoding="utf-8") == "solta"
    assert (root / ".obsidian" / "graph.json").read_text(encoding="utf-8") == '{"colorGroups": []}'
    assert not [name for name in files if name.endswith(".tmp")]


def test_vault_deletes_only_listed_notes_inside_its_folders(tmp_path):
    root = tmp_path / "cofre"
    write_vault(root, {f"{ABOUT}.md": Note(f"# {ABOUT}\n", None), "Conversas/x.md": Note("x\n", None)})
    outside = tmp_path / "fora.md"
    outside.write_text("fora", encoding="utf-8")
    (root / "ideias.md").write_text("solta", encoding="utf-8")
    (root / "Meus").mkdir()
    (root / "Meus" / "diario.md").write_text("meu", encoding="utf-8")
    (root / ".obsidian" / "modelo.md").write_text("config", encoding="utf-8")
    # Um registro adulterado não leva a exportação a apagar fora das três pastas, nem com barras do Windows.
    (root / MANIFEST).write_text(json.dumps({"versao": 1, "arquivos": [
        "Conversas/x.md", "ideias.md", "../fora.md", "Conversas/../../fora.md", ".obsidian/graph.json",
        "Conversas/..\\ideias.md", "Documentos/..\\Meus\\diario.md", "Conversas/..\\.obsidian\\modelo.md",
        f"Conversas/..\\{ABOUT}.md", "Conversas/x.md:fluxo.md", 7, None]}), encoding="utf-8")
    (root / ".obsidian" / "graph.json").write_text('{"minha": "configuração"}', encoding="utf-8")
    assert write_vault(root, {f"{ABOUT}.md": Note(f"# {ABOUT}\n", None)})["removidas"] == 1
    assert not (root / "Conversas" / "x.md").exists()
    assert outside.is_file() and (root / "ideias.md").is_file()
    assert (root / ".obsidian" / "graph.json").read_text(encoding="utf-8") == '{"minha": "configuração"}'
    assert (root / "Meus" / "diario.md").is_file() and (root / ".obsidian" / "modelo.md").is_file()
    assert (root / f"{ABOUT}.md").is_file()
    (root / MANIFEST).write_text("isto não é json", encoding="utf-8")
    assert write_vault(root, {f"{ABOUT}.md": Note(f"# {ABOUT}\n", None)}) == {"notas": 1, "escritas": 0, "removidas": 0}
    for bad in ("../fora.md", "Outra pasta/x.md", "Conversas/..\\fora.md", "Conversas/a/b.md", "Conversas/x.txt"):
        with pytest.raises(ValueError):
            write_vault(root, {bad: Note("x", None)})
    assert outside.read_text(encoding="utf-8") == "fora"


def test_an_unreadable_record_stops_the_round_before_anything_changes(tmp_path, monkeypatch):
    root = tmp_path / "cofre"
    first = {"Conversas/fica.md": Note("antes\n", None), "Conversas/sai.md": Note("x\n", None)}
    write_vault(root, first)
    record, read_text = root / MANIFEST, Path.read_text

    def busy(self, *args, **kwargs):
        if self.name == MANIFEST:
            raise PermissionError("aberto em outro programa")
        return read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", busy)
    before = record.read_bytes()
    with pytest.raises(PermissionError):
        write_vault(root, {"Conversas/fica.md": Note("depois\n", None), "Conversas/nova.md": Note("n\n", None)})
    # Nada foi gravado, criado nem apagado; tratado como "sem registro", a nota que saiu ficaria para sempre.
    assert (root / "Conversas" / "fica.md").read_text(encoding="utf-8") == "antes\n" and record.read_bytes() == before
    assert sorted(path.name for path in (root / "Conversas").iterdir()) == ["fica.md", "sai.md"]
    monkeypatch.undo()
    assert write_vault(root, {"Conversas/fica.md": Note("depois\n", None)}) == {"notas": 1, "escritas": 1, "removidas": 1}


def test_names_that_only_look_alike_are_different_files(tmp_path):
    root = tmp_path / "cofre"
    generated = Note('---\ntipo: "documento"\n---\n# gerada\n', None)
    write_vault(root, {"Documentos/Weiss, 2019.md": generated, "Documentos/Revisão.md": generated})
    mine = root / "Documentos" / "Weiß, 2019.md"  # para o sistema é outro arquivo, embora "ß" valha "ss" ao comparar
    mine.write_text("meu fichamento do Weiß", encoding="utf-8")
    twin = root / "Documentos" / "Revisa\u0303o.md"  # o mesmo nome escrito com o acento separado
    twin.write_text("minha revisão", encoding="utf-8")
    same = {"Documentos/Weiss, 2019.md": generated, "Documentos/Revisão.md": generated}
    assert write_vault(root, same) == {"notas": 2, "escritas": 0, "removidas": 0}
    assert mine.read_text(encoding="utf-8") == "meu fichamento do Weiß" and twin.read_text(encoding="utf-8") == "minha revisão"
    assert write_vault(root, {}) == {"notas": 0, "escritas": 0, "removidas": 2}
    assert sorted(path.name for path in (root / "Documentos").iterdir()) == sorted([mine.name, twin.name])
    assert mine.read_text(encoding="utf-8") == "meu fichamento do Weiß"


def test_a_name_that_changes_only_in_case_keeps_the_note(tmp_path):
    root = tmp_path / "cofre"
    write_vault(root, {"Conversas/2026-10-01 mcc.md": Note("a\n", None)})
    assert write_vault(root, {"Conversas/2026-10-01 MCC.md": Note("b\n", None)}) == {
        "notas": 1, "escritas": 1, "removidas": 0}
    assert [path.name for path in (root / "Conversas").iterdir()] == ["2026-10-01 MCC.md"]
    assert (root / "Conversas" / "2026-10-01 MCC.md").read_text(encoding="utf-8") == "b\n"
    assert json.loads((root / MANIFEST).read_text(encoding="utf-8"))["arquivos"] == ["Conversas/2026-10-01 MCC.md"]
    assert write_vault(root, {"Conversas/2026-10-01 MCC.md": Note("b\n", None)})["escritas"] == 0


def test_the_researchers_own_files_are_never_covered_or_deleted(tmp_path):
    root = tmp_path / "cofre"
    (root / "Documentos").mkdir(parents=True)
    mine = root / "Documentos" / "lafraia, 2001.md"  # mesmo nome de uma nota gerada, com outra grafia
    mine.write_text("meu fichamento", encoding="utf-8")
    draft = root / "Documentos" / ".~rascunho.tmp"
    draft.write_text("meu rascunho", encoding="utf-8")
    leftover = root / "Documentos" / (".~" + "a" * 32 + ".tmp")  # sobra de uma rodada interrompida
    leftover.write_text("resto", encoding="utf-8")
    generated = Note('---\ntipo: "documento"\n---\n# Manual\n', None)
    other = Note('---\ntipo: "documento"\n---\n# Guia\n', None)
    notes = {"Documentos/Lafraia, 2001.md": generated, "Documentos/Guia.md": other}
    assert write_vault(root, notes) == {"notas": 2, "escritas": 1, "removidas": 0}
    assert mine.read_text(encoding="utf-8") == "meu fichamento" and draft.is_file() and not leftover.exists()
    assert json.loads((root / MANIFEST).read_text(encoding="utf-8"))["arquivos"] == ["Documentos/Guia.md"]
    assert write_vault(root, {}) == {"notas": 0, "escritas": 0, "removidas": 1}
    assert mine.read_text(encoding="utf-8") == "meu fichamento" and not (root / "Documentos" / "Guia.md").exists()

    # Sem o registro, uma nota com a cara das geradas volta a ser atualizada; a sua continua intocada.
    write_vault(root, notes)
    (root / MANIFEST).unlink()
    changed = notes | {"Documentos/Guia.md": Note('---\ntipo: "documento"\n---\n# Guia novo\n', None)}
    assert write_vault(root, changed) == {"notas": 2, "escritas": 1, "removidas": 0}
    assert "Guia novo" in (root / "Documentos" / "Guia.md").read_text(encoding="utf-8")
    assert mine.read_text(encoding="utf-8") == "meu fichamento"


def test_a_note_that_cannot_be_written_or_deleted_does_not_stop_the_others(tmp_path, monkeypatch):
    from aliado.interfaces.web import obsidian

    root = tmp_path / "cofre"
    first = {"Conversas/a.md": Note("a1\n", None), "Conversas/b.md": Note("b1\n", None),
             "Conversas/velha.md": Note("v\n", None), "Conversas/presa.md": Note("p\n", None)}
    write_vault(root, first)
    replace, unlink, busy = obsidian._replace, Path.unlink, {"on": True}

    def held_replace(temporary, target):
        if busy["on"] and target.name == "a.md":
            raise PermissionError("aberta em outro programa")
        replace(temporary, target)

    def held_unlink(self, *args, **kwargs):
        if busy["on"] and self.name == "presa.md":
            raise PermissionError("aberta em outro programa")
        unlink(self, *args, **kwargs)

    monkeypatch.setattr(obsidian, "_replace", held_replace)
    monkeypatch.setattr(Path, "unlink", held_unlink)
    second = {"Conversas/a.md": Note("a2\n", None), "Conversas/b.md": Note("b2\n", None)}
    with pytest.raises(PermissionError):
        write_vault(root, second)
    read = lambda name: (root / "Conversas" / name).read_text(encoding="utf-8")  # noqa: E731
    assert read("a.md") == "a1\n" and read("b.md") == "b2\n" and not (root / "Conversas" / "velha.md").exists()
    # A nota que não pôde ser apagada continua no registro; nenhum arquivo temporário sobra.
    assert json.loads((root / MANIFEST).read_text(encoding="utf-8"))["arquivos"] == [
        "Conversas/a.md", "Conversas/b.md", "Conversas/presa.md"]
    assert not [name for name in vault_files(root) if name.endswith(".tmp")]
    busy["on"] = False
    assert write_vault(root, second) == {"notas": 2, "escritas": 1, "removidas": 1}
    assert read("a.md") == "a2\n" and not (root / "Conversas" / "presa.md").exists()

    # Só um apagar que falha: a rodada também avisa, para a fila tentar de novo.
    write_vault(root, second | {"Conversas/presa.md": Note("p\n", None)})
    busy["on"] = True
    with pytest.raises(PermissionError):
        write_vault(root, {"Conversas/b.md": Note("b2\n", None)})
    assert (root / "Conversas" / "presa.md").is_file() and not (root / "Conversas" / "a.md").exists()
    busy["on"] = False

    # Uma nota que nem pode ser lida (aberta sem compartilhar a leitura) não segura as outras.
    read_bytes = Path.read_bytes

    def held_read(self):
        if self.name == "b.md":
            raise PermissionError("aberta em outro programa")
        return read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", held_read)
    with pytest.raises(PermissionError):
        write_vault(root, {"Conversas/b.md": Note("b2\n", None), "Conversas/nova.md": Note("n\n", None)})
    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    assert read("nova.md") == "n\n" and not (root / "Conversas" / "presa.md").exists()
    assert json.loads((root / MANIFEST).read_text(encoding="utf-8"))["arquivos"] == ["Conversas/b.md", "Conversas/nova.md"]


def test_a_failed_write_never_loses_the_old_note_nor_claims_a_file_it_did_not_write(tmp_path, monkeypatch):
    from aliado.interfaces.web import obsidian

    root = tmp_path / "cofre"
    generated = lambda text: Note(f'---\ntipo: "conversa"\n---\n# {text}\n', None)  # noqa: E731
    write_vault(root, {"Conversas/2026-10-01 mcc.md": generated("conteúdo")})
    replace = obsidian._replace

    def full_disk(temporary, target):
        if target.name in {"2026-10-01 MCC.md", "nova.md"}:
            raise OSError(28, "No space left on device")
        replace(temporary, target)

    monkeypatch.setattr(obsidian, "_replace", full_disk)
    with pytest.raises(OSError):
        write_vault(root, {"Conversas/2026-10-01 MCC.md": generated("conteúdo novo"), "Conversas/nova.md": generated("n")})
    # A nota antiga continua lá, com o texto antigo, e a que nunca foi gravada não entra no registro.
    assert [path.name.casefold() for path in (root / "Conversas").iterdir()] == ["2026-10-01 mcc.md"]
    assert "nova.md" not in (root / MANIFEST).read_text(encoding="utf-8")
    monkeypatch.setattr(obsidian, "_replace", replace)
    mine = root / "Conversas" / "nova.md"
    mine.write_text("texto meu, escrito no Obsidian", encoding="utf-8")
    assert write_vault(root, {"Conversas/2026-10-01 MCC.md": generated("conteúdo novo"),
                              "Conversas/nova.md": generated("n")})["escritas"] == 1
    assert mine.read_text(encoding="utf-8") == "texto meu, escrito no Obsidian"
    assert sorted(path.name for path in (root / "Conversas").iterdir()) == ["2026-10-01 MCC.md", "nova.md"]


@pytest.mark.skipif(os.name != "nt", reason="as junções de pasta são do Windows")
def test_a_folder_that_points_outside_is_left_alone_and_the_others_go_on(tmp_path):
    import _winapi

    root, outside, shared = tmp_path / "cofre", tmp_path / "fora", tmp_path / "config"
    generated = lambda text: Note(f'---\ntipo: "documento"\n---\n# {text}\n', None)  # noqa: E731
    write_vault(root, {f"{ABOUT}.md": Note(f"# {ABOUT}\n", None), "Documentos/d.md": generated("d1")})
    outside.mkdir()
    (outside / "alheio.md").write_text("de outra pasta", encoding="utf-8")
    (outside / (".~" + "b" * 32 + ".tmp")).write_text("de outra pasta", encoding="utf-8")
    _winapi.CreateJunction(str(outside), str(root / "Conversas"))
    (root / MANIFEST).write_text(json.dumps({"versao": 1, "arquivos": [
        f"{ABOUT}.md", "Documentos/d.md", "Conversas/alheio.md"]}), encoding="utf-8")
    with pytest.raises(OSError):
        write_vault(root, {f"{ABOUT}.md": Note(f"# {ABOUT}\n", None), "Documentos/d.md": generated("d2"),
                           "Conversas/nova.md": generated("n")})
    assert "d2" in (root / "Documentos" / "d.md").read_text(encoding="utf-8")  # as outras pastas seguem
    assert sorted(path.name for path in outside.iterdir()) == [".~" + "b" * 32 + ".tmp", "alheio.md"]

    # Enquanto a pasta aponta para fora, o registro guarda o que havia nela; quando ela volta, a nota antiga sai.
    vault, kept = tmp_path / "cofre3", tmp_path / "guardada"
    write_vault(vault, {"Conversas/a.md": generated("a"), "Conversas/velha.md": generated("v"),
                        "Documentos/d.md": generated("d")})
    os.rename(vault / "Conversas", kept)
    _winapi.CreateJunction(str(outside), str(vault / "Conversas"))
    with pytest.raises(OSError):
        write_vault(vault, {"Conversas/a.md": generated("a"), "Documentos/d.md": generated("d")})
    assert "Conversas/velha.md" in json.loads((vault / MANIFEST).read_text(encoding="utf-8"))["arquivos"]
    os.rmdir(vault / "Conversas")
    os.rename(kept, vault / "Conversas")
    assert write_vault(vault, {"Conversas/a.md": generated("a"), "Documentos/d.md": generated("d")}) == {
        "notas": 2, "escritas": 0, "removidas": 1}
    assert not (vault / "Conversas" / "velha.md").exists() and (outside / "alheio.md").is_file()

    # A configuração do Obsidian compartilhada por uma junção também não recebe nada.
    other = tmp_path / "cofre2"
    other.mkdir()
    shared.mkdir()
    _winapi.CreateJunction(str(shared), str(other / ".obsidian"))
    write_vault(other, {"Documentos/d.md": generated("d")})
    assert list(shared.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="a data de criação do arquivo só é gravada no Windows")
def test_file_creation_date_follows_the_record(tmp_path):
    root = tmp_path / "cofre"
    when = datetime(2026, 9, 27, 23, 20, 3, tzinfo=UTC)
    write_vault(root, {"Conversas/x.md": Note("um\n", when)})
    target = root / "Conversas" / "x.md"
    assert abs(target.stat().st_birthtime - when.timestamp()) < 1
    write_vault(root, {"Conversas/x.md": Note("dois\n", when)})  # regravar não perde a data
    assert abs(target.stat().st_birthtime - when.timestamp()) < 1 and target.read_text(encoding="utf-8") == "dois\n"
    assert target.stat().st_mtime > when.timestamp() + 3600  # a data de modificação é a real
    other = datetime(2026, 9, 28, 8, 0, tzinfo=UTC)
    write_vault(root, {"Conversas/x.md": Note("dois\n", other)})  # sem mudar o texto, a data é corrigida
    assert abs(target.stat().st_birthtime - other.timestamp()) < 1


def test_sync_joins_requests_and_survives_failures(capsys):
    release, started, runs = threading.Event(), threading.Event(), []

    def export():
        runs.append(len(runs))
        started.set()
        release.wait(5)
        return {"notas": 3, "escritas": 1, "removidas": 0}

    sync = ObsidianSync(export)
    sync.request()
    assert started.wait(5)
    for _ in range(10):
        sync.request()  # dez pedidos durante a rodada viram uma rodada a mais
    assert not sync.flush(0.05)
    release.set()
    assert sync.flush(5) and len(runs) == 2
    assert sync.state["notas"] == 3 and sync.state["erro"] is None and sync.state["atualizada_em"]

    failing = {"error": OSError("C:\\segredo\\pasta"), "calls": 0}

    def broken():
        failing["calls"] += 1
        if failing["error"]:
            raise failing["error"]
        return {"notas": 1, "escritas": 0, "removidas": 0}

    sync = ObsidianSync(broken)
    sync.RETRY = (0.01, 0.01)
    for _ in range(2):
        sync.request()
        assert sync.flush(5)
    assert sync.state["erro"] == FAILURE and failing["calls"] == 2  # um erro qualquer não é tentado de novo
    assert capsys.readouterr().err == FAILURE + "\n"  # o aviso sai uma vez, e só ele: sem caminho de pasta
    # Arquivo ou banco ocupado: três tentativas antes de desistir da rodada.
    for busy in (PermissionError("ocupado"), sqlite3.OperationalError("database is locked")):
        failing.update(error=busy, calls=0)
        sync.request()
        assert sync.flush(5) and sync.state["erro"] == FAILURE and failing["calls"] == 3
    failing["error"] = None
    sync.request()
    assert sync.flush(5) and sync.state["erro"] is None and sync.state["notas"] == 1
    # Com a fila encerrada (o servidor fechando), um pedido a mais não falha nem fica pendurado.
    sync._executor.shutdown(wait=True)
    sync.request()
    assert sync.flush(1)


def test_store_snapshot_skips_the_trash_and_reads_never_break_writes(tmp_path):
    store = ConversationStore(tmp_path)
    kept, gone = store.create("Fica"), store.create("Sai")
    store.append(kept["id"], {"role": "user", "content": "oi"})
    store.delete(gone["id"])
    (tmp_path / f"{kept['id']}.tmp").write_text("{", encoding="utf-8")
    (tmp_path / "anotacoes.json").write_text("{}", encoding="utf-8")
    assert [item["id"] for item in store.snapshot()] == [kept["id"]]
    assert [item["id"] for item in store.list()] == [kept["id"]]

    # No Windows, trocar um arquivo que outra thread está lendo falhava: a resposta em andamento se perdia.
    errors, stop = [], threading.Event()

    def read():
        while not stop.is_set():
            try:
                store.snapshot()
            except Exception as exc:  # qualquer falha de leitura conta
                errors.append(exc)

    readers = [threading.Thread(target=read) for _ in range(3)]
    for reader in readers:
        reader.start()
    try:
        for number in range(60):
            store.append(kept["id"], {"role": "user", "content": f"pergunta {number}"})
    finally:
        stop.set()
        for reader in readers:
            reader.join(5)
    assert not errors and len(store.get(kept["id"])["messages"]) == 61


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


@pytest.fixture
def web(tmp_path):
    """Biblioteca e memória reais, modelo e revisor simulados, e o espelho ligado em `cofre`."""
    library = DocumentLibrary(tmp_path / "biblioteca", encoder=Encoder())
    added = library.add(put(tmp_path, "vida.md", "# Vida\nMTTF é o tempo médio até a falha."))
    library.set_card("vida.md", {"titulo": "Vida útil", "autores": ["Ana Silva"], "ano": 2020}, edited=False)
    memory_ = MemoryStore(tmp_path / "dados" / "memoria")
    hit = library.search("mttf")[0]
    state = {"sources": (hit,), "content": f"MTTF é o tempo médio até a falha [{hit['citation_id']}]."}

    def stream(question, **kwargs):
        yield "texto", state["content"]
        yield "final", LLMResult(state["content"], "google", "gemini-teste", "critical_reasoning",
                                 usage=LLMUsage(10, 5, 15), sources=state["sources"],
                                 validation_status="citation_ids_verified")

    def reviewer(**kwargs):
        return ([{"kind": "preferencia", "text": "Prefiro respostas curtas.", "origin": "feedback", "source": {},
                  "supersedes": None, "diverges_skill": False}],
                LLMResult("{}", "google", "lite", "memoria-revisor", usage=LLMUsage(1, 1, 2)))

    def checker(target):
        verdict = {"veredito": "contradiz", "correcao": "Correção vinda da web.", "explicacao": "As fontes dizem outra coisa.",
                   "fontes": [{"uri": "https://exemplo.org/a", "title": "Exemplo", "domain": "exemplo.org"}]}
        return verdict, LLMResult("x", "google", "lite", "memoria-conferencia", usage=LLMUsage(1, 1, 2),
                                  web_sources=tuple(verdict["fontes"]), web_queries=("q",))

    def card_extractor(*, title, text):
        return ({"titulo": "Ficha tirada do texto", "autores": ["Caio Lima"], "ano": 2018},
                LLMResult("{}", "google", "lite", "biblioteca-ficha", usage=LLMUsage(1, 1, 2)))

    cofre = tmp_path / "cofre"
    settings = WebSettings(data_dir=tmp_path / "dados", library_dir=library.root, port=8765, stream=stream,
                           models=[{"alias": "flash", "model_id": "gemini-teste"}], library_factory=lambda: library,
                           memory=memory_, reviewer=reviewer, checker=checker, obsidian_dir=cofre)
    app = create_app(settings)
    client = TestClient(app, base_url=BASE)

    def notes() -> list[str]:
        assert app.state.obsidian.flush(10)
        return [name for name in vault_files(cofre) if name.endswith(".md")]

    return {"client": client, "library": library, "memory": memory_, "cofre": cofre, "notes": notes, "tmp": tmp_path,
            "document": added, "sync": app.state.obsidian, "settings": settings,
            # Ligado só no teste das fichas, para os outros envios não ganharem ficha sozinhos.
            "card_extractor": card_extractor}


def ask(client, cid, text="O que é MTTF?"):
    response = client.post(f"/api/conversas/{cid}/mensagens", headers=HEADERS,
                           json={"texto": text, "skill": "pesquisa-inversores", "modelo": "flash", "biblioteca": True})
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def wait_job(client, job):
    for _ in range(100):
        state = client.get(f"/api/biblioteca/tarefas/{job}").json()
        if state["estado"] in {"concluido", "falhou"}:
            return state
        time.sleep(0.05)
    raise AssertionError("o envio não terminou")


def test_vault_follows_answers_renames_and_deletions(web):
    client, cofre = web["client"], web["cofre"]
    assert web["notes"]() == ["Documentos/Silva, 2020.md", f"{ABOUT}.md"]  # a primeira rodada sai ao abrir o servidor

    cid = client.post("/api/conversas", headers=HEADERS).json()["id"]
    assert web["notes"]() == ["Documentos/Silva, 2020.md", f"{ABOUT}.md"]  # conversa vazia não vira nota
    events = ask(client, cid)
    assert [event["tipo"] for event in events][-2:] == ["fim", "memoria"]
    # A data do nome é a da conversa guardada, não a do relógio do teste.
    stored = client.get(f"/api/conversas/{cid}").json()["created_at"]
    today = datetime.fromisoformat(stored).astimezone().strftime("%Y-%m-%d")
    talk = f"Conversas/{today} O que é MTTF.md"
    group = f"Anotações/Anotações – {today} O que é MTTF.md"
    assert web["notes"]() == [group, talk, "Documentos/Silva, 2020.md", f"{ABOUT}.md"]
    text = (cofre / talk).read_text(encoding="utf-8")
    assert "até a falha [[Silva, 2020]] (" in text and "> **Documentos citados:** [[Silva, 2020]]" in text
    assert f"> **Anotações criadas:** [[Anotações – {today} O que é MTTF]] (1)" in text
    assert "- Prefiro respostas curtas. — sua" in (cofre / group).read_text(encoding="utf-8")
    assert str(web["tmp"]) not in text and "originals" not in text

    client.patch(f"/api/conversas/{cid}", headers=HEADERS, json={"title": "Vida útil: resumo"})
    renamed = f"Conversas/{today} Vida útil resumo.md"
    assert renamed in web["notes"]() and talk not in web["notes"]()
    assert f"[[{today} Vida útil resumo]]" in (
        cofre / f"Anotações/Anotações – {today} Vida útil resumo.md").read_text(encoding="utf-8")

    assert client.delete(f"/api/conversas/{cid}", headers=HEADERS).status_code == 200
    left = web["notes"]()
    assert renamed not in left and len([name for name in left if name.startswith("Anotações/")]) == 1
    # A anotação continua na memória; a nota dela passa a dizer que a conversa foi apagada.
    assert "(conversa apagada)" in (cofre / next(n for n in left if n.startswith("Anotações/"))).read_text(encoding="utf-8")


def test_vault_follows_the_library_and_the_memory(web):
    client, cofre, memory_ = web["client"], web["cofre"], web["memory"]
    cid = client.post("/api/conversas", headers=HEADERS).json()["id"]
    ask(client, cid)
    upload = client.post("/api/biblioteca", headers=HEADERS,
                         files={"arquivo": ("reparo.md", b"# Reparo\nO MTTR mede o tempo de reparo.", "text/markdown")})
    assert wait_job(client, upload.json()["tarefa"])["estado"] == "concluido"
    assert "Documentos/reparo.md" in web["notes"]()

    new = next(d for d in web["library"].documents() if d["title"] == "reparo.md")
    saved = client.post(f"/api/biblioteca/{new['id']}/ficha", headers=HEADERS,
                        json={"titulo": "Reparo", "autores": ["Bia Costa"], "ano": 2019})
    assert saved.status_code == 200
    names = web["notes"]()
    assert "Documentos/Costa, 2019.md" in names and "Documentos/reparo.md" not in names
    assert "- **Ficha:** sua (editada por você)" in (cofre / "Documentos/Costa, 2019.md").read_text(encoding="utf-8")

    created = client.post("/api/memoria", headers=HEADERS, json={"tipo": "decisao", "texto": "Usar o manual inteiro."})
    assert created.status_code == 201 and "Anotações/Outras anotações.md" in web["notes"]()
    fact = memory_.add(kind="fato", text="O MTTF mede a vida.", origin="inferido",
                       source={"document_id": web["document"]["id"], "title": "vida.md", "ficha": True, "page": 1})
    assert client.post(f"/api/memoria/{created.json()['id']}/revogar", headers=HEADERS).status_code == 200
    names = web["notes"]()
    assert "Anotações/Anotações – Silva, 2020.md" in names
    assert "(revogada) Usar o manual inteiro." in (cofre / "Anotações/Outras anotações.md").read_text(encoding="utf-8")

    # Apagar o documento tira as notas dele; a citação na conversa vira texto, sem link quebrado.
    assert client.delete(f"/api/biblioteca/{web['document']['id']}", headers=HEADERS).status_code == 200
    names = web["notes"]()
    assert "Documentos/Silva, 2020.md" not in names and "Anotações/Anotações – Silva, 2020.md" not in names
    assert memory_.get(fact["id"])["status"] == "revogada"
    talk = (cofre / next(n for n in names if n.startswith("Conversas/"))).read_text(encoding="utf-8")
    assert "[[Silva, 2020]]" not in talk and "até a falha Silva, 2020 (" in talk
    stems = {Path(name).stem for name in names}
    for name in names:
        assert all(target in stems for target in LINK.findall((cofre / name).read_text(encoding="utf-8"))), name


def test_vault_follows_failed_versions_web_checks_and_completed_cards(web):
    client, cofre, memory_, library = web["client"], web["cofre"], web["memory"], web["library"]
    web["notes"]()
    # Uma versão nova que não pôde ser lida aparece na nota do documento.
    upload = client.post("/api/biblioteca", headers=HEADERS, files={"arquivo": ("vida.md", b"   \n", "text/markdown")})
    assert wait_job(client, upload.json()["tarefa"])["resultado"]["status"] == "failed"
    web["notes"]()
    text = (cofre / "Documentos" / "Silva, 2020.md").read_text(encoding="utf-8")
    assert "## Versões" in text and "(não pôde ser lida)" in text and "versão: 1\n" in text

    # A correção de uma conferência na web entra na nota de anotações do documento.
    fact = memory_.add(kind="fato", text="O MTTF mede a vida.", origin="inferido",
                       source={"document_id": web["document"]["id"], "title": "vida.md", "ficha": True, "page": 1})
    checked = client.post(f"/api/memoria/{fact['id']}/conferir", headers=HEADERS)
    assert checked.status_code == 200 and checked.json()["criada"]
    web["notes"]()
    group = (cofre / "Anotações" / "Anotações – Silva, 2020.md").read_text(encoding="utf-8")
    assert "- Correção vinda da web. — inferida · [Exemplo](<https://exemplo.org/a>)" in group
    assert "(superada) O MTTF mede a vida. — p. 1 · inferida" in group and "em vigor: 1\n" in group

    # "Completar fichas" dá a referência ao documento que ainda não tinha ficha, e a nota muda de nome.
    library.add(put(web["tmp"], "sem-ficha.md", "# Reparo\nO MTTR mede o tempo de reparo."))
    web["sync"].request()
    assert "Documentos/sem-ficha.md" in web["notes"]()
    web["settings"].card_extractor = web["card_extractor"]
    job = client.post("/api/biblioteca/fichas", headers=HEADERS)
    assert job.status_code == 202 and wait_job(client, job.json()["tarefa"])["resultado"]["fichas"] == 1
    names = web["notes"]()
    assert "Documentos/Lima, 2018.md" in names and "Documentos/sem-ficha.md" not in names


def test_a_broken_vault_never_breaks_the_chat_and_off_means_no_folder(tmp_path, web, capsys):
    blocked = tmp_path / "ocupado"
    blocked.write_text("um arquivo no lugar da pasta", encoding="utf-8")
    web["settings"].obsidian_dir = blocked
    cid = web["client"].post("/api/conversas", headers=HEADERS).json()["id"]
    assert [event["tipo"] for event in ask(web["client"], cid)][-2:] == ["fim", "memoria"]
    assert web["sync"].flush(10) and web["sync"].state["erro"] == FAILURE
    assert str(tmp_path) not in capsys.readouterr().err

    # A pasta do espelho não pode ser, conter nem ficar dentro de uma pasta que o AL-IAdo usa.
    data = tmp_path / "dados"
    for refused in (data, tmp_path, data / "conversas", data / "memoria" / "x", data / "uso", data / "uploads-temporarios",
                    data / "resultados", tmp_path / "b", tmp_path / "b" / "originals", tmp_path / "g" / "sub",
                    data / "ciencia", data / "memory-review", data / "models" / "minilm", data / "bibliotecas"):
        with pytest.raises(ValueError, match="pasta própria"):
            WebSettings(data_dir=data, library_dir=tmp_path / "b", port=8765, stream=None, models=[],
                        library_factory=lambda: None, gpvs_dir=tmp_path / "g", obsidian_dir=refused)
    accepted = WebSettings(data_dir=data, library_dir=tmp_path / "b", port=8765, stream=None, models=[],
                           library_factory=lambda: None, gpvs_dir=tmp_path / "g", obsidian_dir=data / "obsidian")
    assert accepted.obsidian_dir == (data / "obsidian").resolve()
    off = WebSettings(data_dir=tmp_path / "sem", library_dir=tmp_path / "b", port=8765, stream=None, models=[],
                      library_factory=lambda: None)
    app = create_app(off)
    assert app.state.obsidian is None and off.obsidian_dir is None and not (tmp_path / "sem" / "obsidian").exists()


def test_an_unreadable_conversation_keeps_the_previous_vault(web):
    client, cofre = web["client"], web["cofre"]
    cid = client.post("/api/conversas", headers=HEADERS).json()["id"]
    ask(client, cid)
    before = web["notes"]()
    (web["tmp"] / "dados" / "conversas" / ("f" * 32 + ".json")).write_text("{ quebrado", encoding="utf-8")
    web["sync"].request()
    assert web["notes"]() == before and web["sync"].state["erro"] == FAILURE
    assert all((cofre / name).is_file() for name in before)


def test_default_settings_turn_the_mirror_on_and_the_command_can_turn_it_off(monkeypatch, tmp_path):
    from aliado import cli
    from aliado.interfaces.web import app as web_app

    # A configuração real: ligado em <dados>/obsidian; desligado, sem pasta.
    on = web_app.default_settings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765)
    assert on.obsidian_dir == (tmp_path / "dados" / "obsidian").resolve()
    off = web_app.default_settings(data_dir=tmp_path / "dados", library_dir=tmp_path / "biblioteca", port=8765,
                                   obsidian=False)
    assert off.obsidian_dir is None

    seen = {}

    def fake_settings(**kwargs):
        seen.update(kwargs)
        raise ValueError("parou aqui")

    monkeypatch.setattr(web_app, "default_settings", fake_settings)
    cli.main(["web", "--sem-navegador", "--dados", str(tmp_path)])
    assert seen["obsidian"] is True
    cli.main(["web", "--sem-navegador", "--sem-obsidian", "--dados", str(tmp_path)])
    assert seen["obsidian"] is False
