"""Medição da busca da biblioteca com perguntas de referência (lote 19).

Cada pergunta traz os documentos esperados, escolhidos pelo conteúdo e não pelo que a busca
devolve. Há acerto quando um deles aparece entre os resultados. As perguntas descrevem o acervo
do pesquisador e ficam fora do Git, em `data/avaliacao-busca/`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LIMIT = 6
GROUPS = ("idioma", "tipo", "cruzamento")


def load_questions(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    questions = data.get("perguntas") if isinstance(data, dict) else None
    if not questions:
        raise ValueError("Arquivo sem perguntas de referência.")
    for question in questions:
        if not str(question.get("pergunta", "")).strip() or not question.get("esperados"):
            raise ValueError(f"Pergunta {question.get('id', '?')} sem texto ou sem documento esperado.")
    return questions


def evaluate_search(library, questions: list[dict], *, limit: int = LIMIT, rewrite=None) -> dict:
    """Roda a busca de cada pergunta e resume acertos, posição do primeiro acerto e diversidade.

    `rewrite(pergunta) -> consulta` mede a busca com a consulta reescrita (lote 22), como no chat."""
    known = {document["title"] for document in library.documents()}
    missing = sorted({title for question in questions for title in question["esperados"] if title not in known})
    if missing:
        raise ValueError("Documentos esperados fora da biblioteca: " + ", ".join(missing))
    rows = []
    for question in questions:
        query = rewrite(question["pergunta"]) if rewrite else question["pergunta"]
        titles = [hit["title"] for hit in library.search(query, limit=limit)]
        rank = next((position for position, title in enumerate(titles, 1) if title in question["esperados"]), None)
        rows.append({
            "id": question.get("id"), "idioma": question.get("idioma"), "tipo": question.get("tipo"),
            "cruzamento": "outro idioma" if question.get("idioma") != question.get("idioma_documento")
            else "mesmo idioma",
            "acerto": rank is not None, "posicao": rank, "documentos_distintos": len(set(titles)),
            "resultados": titles,
        } | ({"consulta": query} if rewrite else {}))
    return {
        "data": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "limite": limit,
        "busca": getattr(library, "search_settings", None),
        "consulta_reescrita": bool(rewrite),
        "resumo": _summary(rows),
        "por_grupo": {group: {value: _summary([row for row in rows if row[group] == value])
                              for value in sorted({row[group] for row in rows})} for group in GROUPS},
        "detalhe": rows,
    }


def _summary(rows: list[dict]) -> dict:
    count = len(rows)
    hits = sum(row["acerto"] for row in rows)
    return {
        "perguntas": count,
        "acertos": hits,
        "taxa_de_acerto": round(hits / count, 3) if count else None,
        # Média de 1/posição do primeiro acerto (0 quando não há acerto): 1 é sempre em primeiro.
        "mrr": round(sum(1 / row["posicao"] for row in rows if row["posicao"]) / count, 3) if count else None,
        "documentos_distintos_medio": round(sum(row["documentos_distintos"] for row in rows) / count, 2)
        if count else None,
    }


def export_evaluation(result: dict, output: str | Path) -> dict:
    output = Path(output)
    if output.exists():
        raise ValueError("A pasta de saída já existe; escolha uma pasta nova.")
    output.mkdir(parents=True)
    path = output / "avaliacao-busca.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"relatorio": str(path), "resumo": result["resumo"], "por_grupo": result["por_grupo"]}
