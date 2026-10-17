"""Medição local do lote 33, sem tokens: roteador, reescrita seletiva e plano por partes.

Execute da raiz: python docs/migracao/medir-lote-33.py --saida data/validacao-lote-33
A pasta deve ser nova. Lê, sem alterar, as conversas em data/conversas, o catálogo da biblioteca e o resumo dos
resultados; não carrega o .env, não faz downloads e não chama provedores. O roteador anterior é carregado em memória
do commit 98be273, sem mudar o checkout.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import types
from pathlib import Path

from aliado import routing
from aliado.knowledge.coverage import explicit_units, has_parts
from aliado.knowledge.embeddings import LocalEncoder
from aliado.knowledge.library import DocumentLibrary
from aliado.knowledge.rewrite import rewrite_kind
from aliado.science import digest
from aliado.skills.library import list_skills

BASELINE = "98be273"
ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = json.loads((ROOT / "docs" / "migracao" / "perguntas-lote-33.json").read_text(encoding="utf-8"))


def previous_router():
    """O roteador do lote 31, com as frases de exemplo daquela versão."""
    def show(path):
        return subprocess.run(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", check=True).stdout
    examples = types.ModuleType("exemplos_anteriores")
    exec(compile(show("src/aliado/routing_examples.py"), f"git:{BASELINE}/routing_examples.py", "exec"), examples.__dict__)
    sys.modules["exemplos_anteriores"] = examples
    source = show("src/aliado/routing.py").replace("from aliado.routing_examples import", "from exemplos_anteriores import")
    module = types.ModuleType("roteador_anterior")
    sys.modules["roteador_anterior"] = module  # as dataclasses procuram o próprio módulo
    exec(compile(source, f"git:{BASELINE}/routing.py", "exec"), module.__dict__)
    return module


def conversations():
    """As conversas reais, da mais antiga para a mais nova."""
    folder = ROOT / "data" / "conversas"
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(folder.glob("*.json"), key=lambda path: path.stat().st_mtime)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", required=True, type=Path)
    output = parser.parse_args().saida
    output.mkdir(parents=True, exist_ok=False)

    encoder = LocalEncoder()
    library = DocumentLibrary(ROOT / "data" / "bibliotecas" / "principal", encoder=encoder)
    cards = library.cards()
    skills = [skill["name"] if isinstance(skill, dict) else getattr(skill, "name", skill) for skill in list_skills()]
    names = routing.results_vocabulary(digest.build_digest(ROOT / "data" / "resultados", ROOT / "docs" / "pesquisa-inversores"))
    old = previous_router()

    def both(text, previous=None, results=True):
        common = {"encoder": encoder, "cards": cards, "skills": skills, "library": True, "results": results,
                  "previous": previous}
        return old.route(text, **common), routing.route(text, vocabulary=names, **common)

    report = {"vocabulario": {key: sorted(values) for key, values in names.items()}}

    # 1. Perguntas guardadas antes da mudança.
    held = {}
    pairs = [both(text) for text in QUESTIONS["resultados"]]
    held["resultados"] = {"antes": sum(a.intent == "resultados" for a, _ in pairs),
                          "depois": sum(b.intent == "resultados" for _, b in pairs), "de": len(pairs),
                          "rotas": [{"pergunta": text, "antes": a.intent, "depois": b.intent}
                                    for text, (a, b) in zip(QUESTIONS["resultados"], pairs)]}
    pairs = [both(text) for text in QUESTIONS["nao_resultados"]]
    held["nao_resultados"] = {"tratadas_como_resultados_antes": sum(a.intent == "resultados" for a, _ in pairs),
                              "tratadas_como_resultados_depois": sum(b.intent == "resultados" for _, b in pairs),
                              "de": len(pairs), "rotas": [{"pergunta": text, "antes": a.intent, "depois": b.intent}
                                                          for text, (a, b) in zip(QUESTIONS["nao_resultados"], pairs)]}
    after = {"rung": routing.PASSAGES}
    groups = QUESTIONS["depois_da_biblioteca"]
    for name, check in (("conversa", lambda r: r.rung == routing.NONE), ("biblioteca", lambda r: r.rung >= routing.PASSAGES),
                        ("reclamacao", lambda r: r.rung >= routing.PAGES)):
        pairs = [both(text, after) for text in groups[name]]
        held[f"depois_da_biblioteca_{name}"] = {
            "certas_antes": sum(check(a) for a, _ in pairs), "certas_depois": sum(check(b) for _, b in pairs),
            "de": len(pairs), "rotas": [{"mensagem": text, "antes": [a.intent, a.rung], "depois": [b.intent, b.rung]}
                                        for text, (a, b) in zip(groups[name], pairs)]}
    held["partes"] = [{"pergunta": case["pergunta"], "partes": len(explicit_units(case["pergunta"]))
                       if has_parts(case["pergunta"]) else 1, "minimo": case["minimo"]} for case in QUESTIONS["partes"]]
    first = [{"role": "user", "content": QUESTIONS["continuacao_partes"]["antes"]}]
    held["continuacao_partes"] = {"tem_partes": has_parts(QUESTIONS["continuacao_partes"]["depois"], first)}
    held["reescrita"] = {
        "dispensa": [rewrite_kind(text) for text in QUESTIONS["reescrita"]["dispensa"]],
        "precisa": [rewrite_kind(case["pergunta"], [{"role": "user", "content": case["antes"]}])
                    for case in QUESTIONS["reescrita"]["precisa"]]}
    report["perguntas_guardadas"] = held

    # 2. Mensagens reais: o que mudou de rota, e a reescrita das perguntas que foram à biblioteca.
    changed, total, kinds, searches = [], 0, {"nenhuma": 0, "simples": 0, "plano": 0}, []
    for conversation in conversations():
        messages = conversation.get("messages", [])
        previous_old = previous_new = None
        for index, message in enumerate(messages):
            if message.get("role") != "user":
                continue
            total += 1
            text, history = message["content"], messages[:index]
            common = {"encoder": encoder, "cards": cards, "skills": skills, "library": True, "results": True}
            a = old.route(text, previous=previous_old, **common)
            b = routing.route(text, previous=previous_new, vocabulary=names, **common)
            previous_old = {"rung": min(a.rung, routing.PAGES), "results": a.results}
            previous_new = {"rung": min(b.rung, routing.PAGES), "results": b.results}
            if (a.intent, a.rung, a.model) != (b.intent, b.rung, b.model):
                changed.append({"mensagem": text[:120], "antes": [a.intent, routing.RUNG_NAMES[a.rung], a.model],
                                "depois": [b.intent, routing.RUNG_NAMES[b.rung], b.model]})
            reply = messages[index + 1] if index + 1 < len(messages) else {}
            query = reply.get("consulta_biblioteca")
            if b.rung > routing.NONE:
                kind = rewrite_kind(text, history, intent=b.intent)
                kinds[kind] += 1
                if kind == "nenhuma" and query:
                    # A busca pela própria pergunta traz os documentos que a consulta reescrita trazia?
                    plain_docs = [hit["title"] for hit in library.search(text, limit=10)]
                    rewritten_docs = [hit["title"] for hit in library.search(query, limit=10)]
                    searches.append({"pergunta": text[:120], "consulta_reescrita": query[:200],
                                     "primeiro_da_reescrita_esta_entre_os_10": rewritten_docs[:1] == []
                                     or rewritten_docs[0] in plain_docs,
                                     "documentos_em_comum": len(set(plain_docs) & set(rewritten_docs)),
                                     "documentos_reescrita": len(set(rewritten_docs))})
    report["mensagens_reais"] = {"total": total, "rotas_mudadas": changed, "reescrita": kinds,
                                 "busca_sem_reescrita": searches}

    # O relatório completo traz trechos das conversas reais e fica na pasta de saída, fora do Git. O resumo,
    # que pode ir para docs/, traz só as perguntas guardadas e as contagens das mensagens reais.
    (output / "medicao-lote-33.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    real = {"total": total, "rotas_mudadas": len(changed), "reescrita": kinds,
            "sem_reescrita_comparadas": len(searches),
            "sem_reescrita_com_o_mesmo_primeiro_documento": sum(s["primeiro_da_reescrita_esta_entre_os_10"] for s in searches),
            "mudancas": [{"antes": item["antes"], "depois": item["depois"]} for item in changed]}
    summary = {"medido_em": "2026-10-17", "base": BASELINE, "vocabulario": report["vocabulario"],
               "perguntas_guardadas": held, "mensagens_reais": real}
    (output / "resumo-lote-33.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"perguntas_guardadas": {key: {k: v for k, v in value.items() if k != "rotas"}
                                              if isinstance(value, dict) else value for key, value in held.items()},
                      "mensagens_reais": real}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
