"""Entrada local para inspecionar skills, preparar pedidos e consultar um provedor."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

from aliado.agent import Agent, prepare_request
from aliado.llm.providers.base import ProviderError, ProviderNotConfiguredError
from aliado.llm.providers.gateway import build_default_gateway
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
        command.add_argument("--skill", default="pesquisa-inversores", help="Nome ou 'nenhuma'")
        command.add_argument("--apoio", help="Skill geral complementar")
        command.add_argument("--biblioteca", type=Path, help="Biblioteca local explicitamente selecionada")
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
    for name in ("adicionar", "listar", "buscar", "verificar"):
        operation = library_commands.add_parser(name)
        operation.add_argument("--biblioteca", type=Path, required=True)
        if name == "adicionar":
            operation.add_argument("arquivo", type=Path)
            operation.add_argument("--titulo", help="Identificador lógico; reutilize para novas versões")
            operation.add_argument("--forcar-ocr", action="store_true")
            operation.add_argument("--reprocessar", action="store_true")
        if name == "buscar":
            operation.add_argument("consulta")
            operation.add_argument("--limite", type=int, default=6)
    web = commands.add_parser("web", help="Interface local no navegador (127.0.0.1)")
    web.add_argument("--env-file", type=Path, help="Arquivo .env explicitamente selecionado")
    web.add_argument("--porta", type=int, default=8765)
    web.add_argument("--biblioteca", type=Path, default=Path("data/bibliotecas/principal"))
    web.add_argument("--dados", type=Path, default=Path("data"), help="Conversas e registro de uso")
    web.add_argument("--sem-navegador", action="store_true", help="Não abrir o navegador")
    science = commands.add_parser("ciencia", help="Cálculos numéricos com cenário explícito")
    science_commands = science.add_subparsers(dest="operation", required=True)
    calculation = science_commands.add_parser("calcular")
    calculation.add_argument("--cenario", type=Path, required=True)
    calculation.add_argument("--saida", type=Path, required=True)
    calculation.add_argument("--grafico", action="store_true")
    fmeca = science_commands.add_parser("fmeca", help="NPR e leitura separada pelas taxas (lote 16)")
    fmeca.add_argument("--tabela", type=Path, default=Path("docs/pesquisa-inversores/fmeca.json"))
    fmeca.add_argument("--saida", type=Path, required=True, help="Pasta nova para o relatório")
    gpvs = science_commands.add_parser("preparar-gpvs", help="Dados GPVS e protocolo M14 (sem modelos)")
    gpvs.add_argument("--dados", type=Path, default=Path("data/gpvs"))
    gpvs.add_argument("--saida", type=Path, required=True, help="Pasta nova para o relatório")
    gpvs.add_argument("--cache", type=Path, default=Path("data/gpvs/processado/variaveis.npz"))
    gpvs.add_argument("--separacao", type=int, help="Janelas entre blocos (padrão: a canônica, 11)")
    training = science_commands.add_parser("treinar-gpvs", help="Autoencoders e limiar p99 (lote 14)")
    training.add_argument("--dados", type=Path, default=Path("data/gpvs"))
    training.add_argument("--saida", type=Path, required=True, help="Pasta nova para modelos e relatório")
    training.add_argument("--cache", type=Path, default=Path("data/gpvs/processado/variaveis.npz"))
    training.add_argument("--separacao", type=int, help="Janelas entre blocos (padrão: a canônica, 11)")
    training.add_argument("--sementes", help="Lista separada por vírgulas (padrão: 13,29,42,71,101)")
    training.add_argument("--teto-epocas", type=int,
                          help="Teto de épocas (padrão: 2000, só de segurança; 150 reproduz a origem)")
    evaluation = science_commands.add_parser("avaliar-gpvs", help="Avaliação M13 dos modelos treinados (lote 15)")
    evaluation.add_argument("--modelos", type=Path, required=True, help="Pasta de uma rodada de treinar-gpvs")
    evaluation.add_argument("--saida", type=Path, required=True, help="Pasta nova para a avaliação")
    evaluation.add_argument("--dados", type=Path, default=Path("data/gpvs"))
    evaluation.add_argument("--cache", type=Path, default=Path("data/gpvs/processado/variaveis.npz"))
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
            else:
                library = DocumentLibrary(args.biblioteca)
                if args.operation == "adicionar":
                    payload = library.add(args.arquivo, title=args.titulo, force_ocr=args.forcar_ocr,
                                          reprocess=args.reprocessar)
                elif args.operation == "listar":
                    payload = library.documents()
                elif args.operation == "buscar":
                    payload = library.search(args.consulta, limit=args.limite)
                else:
                    payload = library.verify()
            print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
            if isinstance(payload, dict) and (payload.get("status") in {"partial", "failed"} or payload.get("ok") is False):
                return 2
            return 0
        if args.command == "ciencia" and args.operation == "preparar-gpvs":
            from aliado.science.detection.gpvs import export_preparation, prepare, report

            if args.saida.exists():
                raise ValueError("A pasta de saída já existe; escolha uma pasta nova.")
            prepared = prepare(args.dados, cache=args.cache, **_purge(args))
            print(json.dumps(export_preparation(prepared, report(prepared), args.saida),
                             ensure_ascii=False, indent=2))
            return 0
        if args.command == "ciencia" and args.operation == "fmeca":
            from aliado.science.fmeca import evaluate_fmeca, export_fmeca, load_table

            if args.saida.exists():
                raise ValueError("A pasta de saída já existe; escolha uma pasta nova.")
            print(json.dumps(export_fmeca(evaluate_fmeca(*load_table(args.tabela)), args.saida),
                             ensure_ascii=False, indent=2))
            return 0
        if args.command == "ciencia" and args.operation == "treinar-gpvs":
            return _train_gpvs(args)
        if args.command == "ciencia" and args.operation == "avaliar-gpvs":
            return _evaluate_gpvs(args)
        if args.command == "ciencia":
            from aliado.science import evaluate_scenario, export_result

            scenario = json.loads(args.cenario.read_text(encoding="utf-8-sig"))
            result = evaluate_scenario(scenario)
            paths = export_result(result, args.saida, plot=args.grafico)
            print(json.dumps(paths, ensure_ascii=False, indent=2))
            return 0
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
        skill_name = None if args.skill == "nenhuma" else args.skill
        if args.command == "preparar":
            print(json.dumps(asdict(prepare_request(args.question, skill_name=skill_name,
                                                   supporting_skill_name=args.apoio, library=selected_library)),
                             ensure_ascii=False, indent=2))
            return 0
        result = Agent(build_default_gateway()).answer(
            args.question, provider=args.provider, model_alias=args.model_alias, skill_name=skill_name,
            supporting_skill_name=args.apoio, library=selected_library,
        )
        print(result.content)
        print(f"\nProvedor: {result.provider} | Modelo: {result.model}", file=sys.stderr)
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
    except ProviderError:
        # Exceções de SDK podem incluir cabeçalhos, URLs ou credenciais.
        print("Não foi possível consultar o provedor. Verifique chave, alias, modelo e disponibilidade.",
              file=sys.stderr)
        return 2
    except ValueError as exc:
        if args.command in {"biblioteca", "ciencia", "web"}:
            print(f"Pedido inválido: {exc}", file=sys.stderr)
            return 2
        print("Pedido inválido. Verifique a pergunta, a skill e a configuração selecionada.",
              file=sys.stderr)
        return 2
    except (OSError, ImportError, RuntimeError, sqlite3.DatabaseError):
        print("Operação local indisponível. Confira arquivos, diretório novo de saída e dependências opcionais.",
              file=sys.stderr)
        return 2


def _purge(args) -> dict:
    return {} if args.separacao is None else {"purge": args.separacao}


def _train_gpvs(args) -> int:
    from aliado.science.detection.gpvs import prepare
    from aliado.science.detection.models import Hyperparameters
    from aliado.science.detection.training import (
        ExperimentConfig,
        export_training,
        train_detectors,
        training_blocks,
    )

    if args.saida.exists():
        raise ValueError("A pasta de saída já existe; escolha uma pasta nova.")
    options = _purge(args)
    if args.sementes:
        seeds = tuple(int(item) for item in args.sementes.split(","))
        options["seeds"] = seeds
        options["reference_seed"] = 42 if 42 in seeds else seeds[0]
    if args.teto_epocas is not None:
        options["hyperparameters"] = Hyperparameters(max_epochs=args.teto_epocas)
    config = ExperimentConfig(**options)
    prepared = prepare(args.dados, cache=args.cache, purge=config.purge, fractions=config.fractions)
    runs = train_detectors(prepared.scaled, training_blocks(prepared), config,
                           progress=lambda line: print(line, file=sys.stderr, flush=True))
    print(json.dumps(export_training(runs, prepared, config, args.saida), ensure_ascii=False, indent=2))
    return 0


def _evaluate_gpvs(args) -> int:
    from aliado.science.detection.evaluation import (
        EvaluationConfig,
        export_evaluation,
        load_training,
        score_all,
    )
    from aliado.science.detection.gpvs import prepare

    if args.saida.exists():
        raise ValueError("A pasta de saída já existe; escolha uma pasta nova.")
    trained = load_training(args.modelos)
    prepared = prepare(args.dados, cache=args.cache, purge=trained.config.purge, fractions=trained.config.fractions)
    config = EvaluationConfig()
    print(json.dumps(export_evaluation(score_all(trained, prepared), trained, prepared, config, args.saida),
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
    settings = default_settings(data_dir=args.dados, library_dir=args.biblioteca, port=args.porta)
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
