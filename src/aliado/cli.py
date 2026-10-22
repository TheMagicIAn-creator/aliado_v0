"""Entrada local para inspecionar skills, preparar pedidos e consultar um provedor."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

from aliado import specializations
from aliado.agent import Agent, prepare_request
from aliado.llm.providers.base import ProviderError, ProviderNotConfiguredError
from aliado.llm.providers.gateway import build_default_gateway
from aliado.llm.providers.local import LocalUnavailable
from aliado.llm.usage_log import DEFAULT_USAGE_LOG, record_usage, usage_line
from aliado.skills.library import list_skills


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass
    parser = argparse.ArgumentParser(prog="aliado", description="AL-IAdo — pesquisa e engenharia")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("skills", help="Lista skills locais sem chamar provedores")
    for name in ("preparar", "perguntar"):
        command = commands.add_parser(name)
        command.add_argument("question", help="Pergunta ao agente")
        command.add_argument("--skill", help="Nome ou 'nenhuma' (padrão: a skill da especialização instalada)")
        command.add_argument("--apoio", help="Skill geral complementar")
        command.add_argument("--biblioteca", type=Path, help="Biblioteca local explicitamente selecionada")
        command.add_argument("--resultados", action="store_true",
                             help="Inclui os resultados da pesquisa (blocos [R1]…), como no chat")
        command.add_argument("--resultados-dir", type=Path, default=Path("data/resultados"),
                             help="Pasta dos resultados da pesquisa")
        command.add_argument("--referencias", type=Path,
                             help="Pasta com a FMECA, os cenários e os tempos de reparo (padrão: a da especialização)")
        if name == "perguntar":
            command.add_argument("--provider", choices=("openai", "google"), required=True)
            command.add_argument("--model-alias", required=True, help="Alias configurado no gateway")
            command.add_argument("--env-file", type=Path, help="Arquivo .env explicitamente selecionado")
            command.add_argument("--registro-uso", type=Path, default=DEFAULT_USAGE_LOG,
                                 help="JSONL local com tokens por chamada, sem o texto")
    library = commands.add_parser("biblioteca", help="Acervo local do projeto")
    library_commands = library.add_subparsers(dest="operation", required=True)
    model = library_commands.add_parser("preparar-modelo", help="Baixa o encoder local de revisão fixa")
    model.add_argument("--diretorio", type=Path)
    reranker = library_commands.add_parser("preparar-reordenador", help="Baixa a rede local que ordena páginas")
    reranker.add_argument("--diretorio", type=Path)
    for name in ("adicionar", "listar", "buscar", "verificar", "avaliar", "reindexar", "figuras"):
        operation = library_commands.add_parser(name)
        operation.add_argument("--biblioteca", type=Path, required=True)
        if name in ("reindexar", "figuras"):  # lote 29
            operation.add_argument("--documento", help="Identificador de um documento; sem ele, todos")
        if name == "figuras":
            operation.add_argument("--modelo", choices=("flash", "flash_lite"), default="flash")
            operation.add_argument("--paginas", type=int, help="No máximo este número de páginas por documento")
            operation.add_argument("--executar", action="store_true",
                                   help="Envia as páginas ao modelo; sem isto, só mostra quantas são e a estimativa")
            operation.add_argument("--env-file", type=Path, help="Arquivo .env, necessário com --executar")
            operation.add_argument("--registro-uso", type=Path, default=DEFAULT_USAGE_LOG)
        if name == "avaliar":  # mede a busca com perguntas de referência (lote 19)
            operation.add_argument("--perguntas", type=Path, default=Path("data/avaliacao-busca/perguntas.json"))
            operation.add_argument("--saida", type=Path, help="Pasta nova para guardar o relatório")
            operation.add_argument("--reescrever", action="store_true",
                                   help="Mede com a consulta reescrita pelo modelo mais barato, como no chat")
            operation.add_argument("--env-file", type=Path, help="Arquivo .env, necessário com --reescrever")
            operation.add_argument("--registro-uso", type=Path, default=DEFAULT_USAGE_LOG)
        if name == "adicionar":
            operation.add_argument("arquivo", type=Path)
            operation.add_argument("--titulo", help="Identificador lógico; reutilize para novas versões")
            operation.add_argument("--forcar-ocr", action="store_true")
            operation.add_argument("--reprocessar", action="store_true")
        if name == "buscar":
            operation.add_argument("consulta")
            operation.add_argument("--limite", type=int, default=6)
    uploads = library_commands.add_parser(
        "arquivos", help="O que a leitura de documentos inteiros deixou no serviço de arquivos do Google")
    uploads.add_argument("--dados", type=Path, default=Path("data"), help="Pasta dos dados, onde fica o registro dos envios")
    uploads.add_argument("--apagar", action="store_true", help="Apaga do serviço o que foi enviado; sem isto, só lista")
    uploads.add_argument("--env-file", type=Path, help="Arquivo .env, necessário com --apagar")
    web = commands.add_parser("web", help="Interface local no navegador (127.0.0.1)")
    web.add_argument("--env-file", type=Path, help="Arquivo .env explicitamente selecionado")
    web.add_argument("--porta", type=int, default=8765)
    web.add_argument("--biblioteca", type=Path, default=Path("data/bibliotecas/principal"))
    web.add_argument("--dados", type=Path, default=Path("data"), help="Conversas e registro de uso")
    web.add_argument("--resultados", type=Path, help="Resultados da aba Ciência (padrão: <dados>/resultados)")
    web.add_argument("--base", type=Path, help="Base de dados dos experimentos (padrão: a do experimento)")
    web.add_argument("--sem-navegador", action="store_true", help="Não abrir o navegador")
    web.add_argument("--sem-obsidian", action="store_true",
                     help="Não gerar as notas do Obsidian em <dados>/obsidian")
    experiment = commands.add_parser("experimento", help="Experimentos das especializações: rodar do zero e exportar o PDF")
    experiment_commands = experiment.add_subparsers(dest="operation", required=True)
    experiment_commands.add_parser("listar", help="Os experimentos instalados")
    for name in ("rodar", "pdf"):
        operation = experiment_commands.add_parser(name)
        operation.add_argument("chave", help="Identificador do experimento (veja 'aliado experimento listar')")
        operation.add_argument("--resultados", type=Path, default=Path("data/resultados"))
        if name == "rodar":
            operation.add_argument("--base", type=Path, help="Pasta da base de dados (padrão: a do experimento)")
            operation.add_argument("--parametro", action="append", default=[], metavar="NOME=VALOR",
                                   help="Um parâmetro diferente do padrão; repita para mais de um")
            operation.add_argument("--frase", help="Frase de confirmação, quando a rodada usa os dados de teste")
            operation.add_argument("--saida", type=Path, help="Pasta nova da rodada (padrão: a próxima rodada-NNN)")
        else:
            operation.add_argument("--saida", type=Path, required=True, help="Arquivo PDF novo")
    science = commands.add_parser("ciencia", help="Cálculos numéricos com cenário explícito")
    science_commands = science.add_subparsers(dest="operation", required=True)
    calculation = science_commands.add_parser("calcular")
    calculation.add_argument("--cenario", type=Path, required=True)
    calculation.add_argument("--saida", type=Path, required=True)
    calculation.add_argument("--grafico", action="store_true")
    fmeca = science_commands.add_parser("fmeca", help="NPR e leitura separada pelas taxas de falha")
    fmeca.add_argument("--tabela", type=Path, help="Tabela da FMECA (padrão: a da especialização instalada)")
    fmeca.add_argument("--saida", type=Path, required=True, help="Pasta nova para o relatório")
    # Os comandos de cada especialização, como os do experimento por etapa (lote 36).
    for add in specializations.gather("add_commands"):
        add(science_commands)
    args = parser.parse_args(argv)
    try:
        if args.command == "skills":
            print(json.dumps([asdict(item) for item in list_skills()], ensure_ascii=False, indent=2))
            return 0
        if args.command == "biblioteca":
            from aliado.knowledge.embeddings import prepare_model
            from aliado.knowledge.library import DocumentLibrary

            if args.operation == "preparar-modelo":
                payload = prepare_model(args.diretorio)
            elif args.operation == "preparar-reordenador":
                from aliado.knowledge.reranking import prepare_model as prepare_reranker

                payload = prepare_reranker(args.diretorio)
            elif args.operation == "arquivos":
                payload = _uploads(args)
            else:
                library = DocumentLibrary(args.biblioteca)
                if args.operation == "adicionar":
                    payload = library.add(args.arquivo, title=args.titulo, force_ocr=args.forcar_ocr,
                                          reprocess=args.reprocessar)
                elif args.operation == "listar":
                    payload = library.documents()
                elif args.operation == "buscar":
                    payload = library.search(args.consulta, limit=args.limite)
                elif args.operation == "avaliar":
                    from aliado.knowledge.evaluation import (
                        evaluate_search,
                        export_evaluation,
                        load_questions,
                    )

                    if args.saida is not None and args.saida.exists():
                        raise ValueError("A pasta de saída já existe; escolha uma pasta nova.")
                    questions = load_questions(args.perguntas)
                    payload = evaluate_search(library, questions,
                                              rewrite=_rewriter(args) if args.reescrever else None)
                    if args.saida is not None:
                        payload = export_evaluation(payload, args.saida)
                elif args.operation == "reindexar":
                    payload = [{key: result[key] for key in ("id", "title", "version", "status", "chunks", "issues")}
                               for result in map(library.reindex, _latest(library, args.documento))]
                elif args.operation == "figuras":
                    payload = _figures(library, args)
                else:
                    payload = library.verify()
            print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
            if isinstance(payload, dict) and (payload.get("status") in {"partial", "failed"} or payload.get("ok") is False):
                return 2
            if isinstance(payload, list) and any(item.get("status") == "failed" for item in payload):
                return 2
            return 0
        if args.command == "ciencia" and args.operation == "fmeca":
            from aliado.science.fmeca.artefatos import export_fmeca
            from aliado.science.fmeca.calculo import evaluate_fmeca
            from aliado.science.fmeca.tabela import load_table

            if args.saida.exists():
                raise ValueError("A pasta de saída já existe; escolha uma pasta nova.")
            reference = specializations.first("REFERENCE_DIR")
            table = args.tabela or (reference / "fmeca.json" if reference else None)
            if table is None:
                raise ValueError("Informe a tabela da FMECA com --tabela.")
            print(json.dumps(export_fmeca(evaluate_fmeca(*load_table(table)), args.saida),
                             ensure_ascii=False, indent=2))
            return 0
        if getattr(args, "handler", None) is not None:  # um comando de especialização
            return args.handler(args)
        if args.command == "ciencia":
            from aliado.science.confiabilidade.artefatos import export_result
            from aliado.science.confiabilidade.cenarios import evaluate_scenario

            scenario = json.loads(args.cenario.read_text(encoding="utf-8-sig"))
            result = evaluate_scenario(scenario)
            paths = export_result(result, args.saida, plot=args.grafico)
            print(json.dumps(paths, ensure_ascii=False, indent=2))
            return 0
        if args.command == "experimento":
            return _experiment(args)
        if args.command == "web":
            return _serve_web(args)
        if args.command == "perguntar" and args.env_file is not None:
            if not args.env_file.is_file():
                raise ValueError("Arquivo de configuração não encontrado.")
            from dotenv import load_dotenv

            load_dotenv(args.env_file, override=False)
        selected_library = None
        if args.biblioteca is not None:
            from aliado.knowledge.library import DocumentLibrary

            selected_library = DocumentLibrary(args.biblioteca)
        skill_name = None if args.skill == "nenhuma" else (args.skill or specializations.first("DEFAULT_SKILL"))
        results = None
        if args.resultados:
            digest = specializations.first("results_digest")
            if digest is None:
                raise ValueError("Nenhuma especialização com resultados está instalada.")
            results = digest(args.resultados_dir, args.referencias or specializations.first("REFERENCE_DIR"))
        if args.command == "preparar":
            print(json.dumps(asdict(prepare_request(args.question, skill_name=skill_name,
                                                   supporting_skill_name=args.apoio, library=selected_library,
                                                   results=results)),
                             ensure_ascii=False, indent=2))
            return 0
        result = Agent(build_default_gateway()).answer(
            args.question, provider=args.provider, model_alias=args.model_alias, skill_name=skill_name,
            supporting_skill_name=args.apoio, library=selected_library, results=results,
        )
        print(result.content)
        if result.truncated:
            print("\nAviso: a resposta foi interrompida pelo limite de tamanho e pode estar incompleta. "
                  "Peça de novo ou restrinja a pergunta.", file=sys.stderr)
        print(f"\nProvedor: {result.provider} | Modelo: {result.model}", file=sys.stderr)
        if result.route_reason:
            print(f"Rota: {result.route_reason}", file=sys.stderr)  # o modelo local passou a vez (lote 38)
        print(usage_line(result), file=sys.stderr)
        try:
            record_usage(result, args.registro_uso)
        except OSError:
            # A resposta já foi entregue; uma falha no registro não deve ocultá-la.
            print("Aviso: não foi possível gravar o registro de uso.", file=sys.stderr)
        return 0
    except ProviderNotConfiguredError:
        print("Configure a chave do provedor e instale o extra 'llm'.", file=sys.stderr)
        return 2
    except LocalUnavailable as exc:
        print(str(exc), file=sys.stderr)  # a mensagem é nossa, sem texto do SDK; nada foi ao Gemini
        return 2
    except ProviderError:
        # Exceções de SDK podem incluir cabeçalhos, URLs ou credenciais.
        print("Não foi possível consultar o provedor. Verifique chave, alias, modelo e disponibilidade.",
              file=sys.stderr)
        return 2
    except ValueError as exc:
        if args.command in {"biblioteca", "ciencia", "experimento", "web"}:
            print(f"Pedido inválido: {exc}", file=sys.stderr)
            return 2
        print("Pedido inválido. Verifique a pergunta, a skill e a configuração selecionada.",
              file=sys.stderr)
        return 2
    except (OSError, ImportError, RuntimeError, sqlite3.DatabaseError):
        print("Operação local indisponível. Confira arquivos, diretório novo de saída e dependências opcionais.",
              file=sys.stderr)
        return 2


def _latest(library, doc_id: str | None) -> list[str]:
    """Os documentos a tratar: o pedido ou a versão mais recente de cada título."""
    latest = {document["title"]: document["id"] for document in library.documents()}  # em ordem de versão
    if doc_id is not None and doc_id not in latest.values():
        raise ValueError("Documento não encontrado, ou não é a versão mais recente.")
    return [doc_id] if doc_id is not None else list(latest.values())


def _figures(library, args) -> dict:
    """Descrição das figuras e tabelas pelo modelo (lote 29): uma chamada por página com conteúdo visual.

    Sem `--executar`, nada é enviado: mostra as páginas por ler e a estimativa de tokens."""
    from aliado.knowledge import figures

    documents = []
    for doc_id in _latest(library, args.documento):
        target = library.figure_pages(doc_id, scan=True)  # acha as páginas, sem custo e sem refazer a extração
        pending = [page for page in target["pages"] if not page["read"]]
        documents.append({"id": doc_id, "titulo": target["title"], "paginas_com_figura": len(target["pages"]),
                          "por_ler": len(pending[:args.paginas] if args.paginas else pending)})
    total = sum(document["por_ler"] for document in documents)
    estimate = {key: total * value for key, value in figures.TOKENS_PER_PAGE.items()}
    if not args.executar:
        return {"enviado": False, "paginas_por_ler": total, "estimativa_de_tokens": estimate, "documentos": documents,
                "aviso": "Nada foi enviado ao modelo. Use --executar e --env-file para descrever as páginas."}
    if args.env_file is None or not args.env_file.is_file():
        raise ValueError("Com --executar, informe o .env com --env-file.")
    from dotenv import load_dotenv

    load_dotenv(args.env_file, override=False)
    gateway = build_default_gateway()

    def execute(request):
        return gateway.execute(request, provider="google", model_alias=args.modelo)

    for document in documents:
        if document["por_ler"]:
            document["resultado"] = figures.describe(
                library, document["id"], execute, limit=args.paginas,
                record=lambda result: record_usage(result, args.registro_uso))
    return {"enviado": True, "modelo": args.modelo, "documentos": documents}


def _uploads(args) -> dict:
    """O que o registro local diz estar no serviço de arquivos do Google (lote 30); com `--apagar`, tira de lá.

    A leitura de documentos inteiros envia os PDFs por esse serviço, que os guarda por até 48 horas."""
    from aliado.llm.providers.gemini import GeminiProvider
    from aliado.llm.usage_log import FILES_LOG_NAME

    if args.apagar:
        if args.env_file is None or not args.env_file.is_file():
            raise ValueError("Com --apagar, informe o .env com --env-file.")
        from dotenv import load_dotenv

        load_dotenv(args.env_file, override=False)
    provider = GeminiProvider(files=args.dados / "uso" / FILES_LOG_NAME)
    listed = provider.uploaded()
    payload = {"arquivos": len(listed), "bytes": sum(item.get("bytes") or 0 for item in listed),
               "itens": [{key: item.get(key) for key in ("chave", "bytes", "enviado", "expira")} for item in listed]}
    if args.apagar:
        payload["resultado"] = provider.forget_uploads()
    return payload


def _rewriter(args):
    """Consulta reescrita pelo modelo mais barato configurado, como no chat (lote 22).

    Cada chamada entra no registro de uso."""
    if args.env_file is None or not args.env_file.is_file():
        raise ValueError("Com --reescrever, informe o .env com --env-file.")
    from dotenv import load_dotenv

    from aliado.knowledge.rewrite import rewrite_query

    load_dotenv(args.env_file, override=False)
    gateway = build_default_gateway()
    aliases = [m["alias"] for m in gateway.registry.status()["models"]
               if m["provider"] == "google" and m["configured"]]
    alias = "flash_lite" if "flash_lite" in aliases else (aliases[0] if aliases else "flash_lite")

    def rewrite(question: str) -> str:
        query, result = rewrite_query(lambda request: gateway.execute(request, provider="google", model_alias=alias),
                                      question=question, subject=", ".join(specializations.gather("REWRITE_SUBJECT")))
        try:
            record_usage(result, args.registro_uso)
        except OSError:
            pass
        return query

    return rewrite


def _experiment(args) -> int:
    """Rodada do zero, numa pasta nova, ou o PDF da rodada atual (spec 0034)."""
    from aliado import experiments

    if args.operation == "listar":
        print(json.dumps([{"chave": item.KEY, "titulo": item.TITLE, "base": item.DATASET}
                          for item in experiments.available()], ensure_ascii=False, indent=2))
        return 0
    experiment = experiments.find(args.chave)
    if args.operation == "pdf":
        from aliado.experiments.pdf import render

        result = experiments.current(args.resultados, experiment)
        if result is None:
            raise ValueError("Ainda não há resultado deste experimento.")
        if args.saida.exists():
            raise ValueError("O arquivo de saída já existe; escolha outro nome.")
        args.saida.write_bytes(render(result, experiment.report(result)))
        print(json.dumps({"pdf": str(args.saida), "rodada": result["rodada"]}, ensure_ascii=False, indent=2))
        return 0
    values = {}
    for item in args.parametro:
        name, sep, value = item.partition("=")
        if not sep:
            raise ValueError("Use --parametro nome=valor.")
        values[name.strip()] = value.strip()
    params = experiments.normalize(experiment, values)
    dataset = args.base or experiment.DATASET_DIR
    absent = experiment.missing(dataset)
    if absent:
        raise ValueError("Faltam " + "; ".join(absent) + ".")
    phrase = getattr(experiment, "CONFIRMATION", None)
    if phrase and str(args.frase or "").strip().lower() != phrase:
        raise ValueError(f'A rodada usa os dados de teste: confirme com --frase "{phrase}".')
    folder = args.saida or experiments.next_folder(args.resultados, experiment.KEY)
    if folder.resolve().parent != experiments.runs_dir(args.resultados, experiment.KEY).resolve() \
            or not folder.name.startswith("rodada-"):
        raise ValueError(f"A rodada fica em {experiments.runs_dir(args.resultados, experiment.KEY)}/rodada-NNN.")
    if folder.exists():
        raise ValueError("A pasta de saída já existe; escolha uma pasta nova.")
    folder.mkdir(parents=True)
    result = experiment.run(params, folder, results_dir=args.resultados, dataset_dir=dataset, phrase=args.frase or "",
                            progress=lambda line: print(line, file=sys.stderr, flush=True))
    experiments.write_result(folder, result)
    print(json.dumps({"pasta": str(folder), "rodada": result["rodada"], "rotulo": result["rotulo"]},
                     ensure_ascii=False, indent=2))
    return 0


def _serve_web(args) -> int:
    if not 1024 <= args.porta <= 65535:
        raise ValueError("Porta deve estar entre 1024 e 65535.")
    if args.env_file is not None:
        if not args.env_file.is_file():
            raise ValueError("Arquivo de configuração não encontrado.")
        from dotenv import load_dotenv

        load_dotenv(args.env_file, override=False)
    try:
        import uvicorn

        from aliado.interfaces.web.app import create_app, default_settings
    except ImportError as exc:
        raise ImportError("Instale o extra 'web' para usar a interface.") from exc
    settings = default_settings(data_dir=args.dados, library_dir=args.biblioteca, port=args.porta,
                                results_dir=args.resultados, dataset_dir=args.base,
                                obsidian=not args.sem_obsidian)
    url = f"http://127.0.0.1:{args.porta}"
    print(f"AL-IAdo em {url} (Ctrl+C encerra)", file=sys.stderr)
    if not settings.models:
        print("Aviso: nenhum modelo Gemini configurado; use --env-file .env.", file=sys.stderr)
    if not args.sem_navegador:
        import threading
        import webbrowser

        threading.Timer(1.2, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(settings), host="127.0.0.1", port=args.porta, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
