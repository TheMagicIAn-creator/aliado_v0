"""Comandos do terminal do mestrado (lotes 13 a 15, 24 e 36): `aliado ciencia preparar-gpvs`, `treinar-gpvs`,
`avaliar-gpvs` e `reanalisar-gpvs`, um passo do experimento de cada vez.

O núcleo os acrescenta ao comando `ciencia` (`add_commands`) e chama o `handler` de cada um; numpy e PyTorch
só entram dentro dele. Cada comando grava numa pasta nova e nunca sobrescreve outra."""

from __future__ import annotations

import json
import sys
from pathlib import Path

DATA = Path("data/gpvs")
CACHE = DATA / "processado" / "variaveis.npz"


def add_commands(science_commands) -> None:
    """Os comandos do experimento por etapa, no `aliado ciencia` do núcleo."""
    gpvs = science_commands.add_parser("preparar-gpvs", help="Prepara os dados do GPVS: divisão e normalização, sem modelos")
    gpvs.add_argument("--dados", type=Path, default=DATA)
    gpvs.add_argument("--saida", type=Path, required=True, help="Pasta nova para o relatório")
    gpvs.add_argument("--cache", type=Path, default=CACHE)
    gpvs.add_argument("--separacao", type=int, help="Janelas entre blocos (padrão: 11)")
    gpvs.set_defaults(handler=_prepare)
    training = science_commands.add_parser("treinar-gpvs", help="Treina os autoencoders e fixa o limiar p99")
    training.add_argument("--dados", type=Path, default=DATA)
    training.add_argument("--saida", type=Path, required=True, help="Pasta nova para modelos e relatório")
    training.add_argument("--cache", type=Path, default=CACHE)
    training.add_argument("--separacao", type=int, help="Janelas entre blocos (padrão: 11)")
    training.add_argument("--sementes", help="Lista separada por vírgulas (padrão: 13,29,42,71,101)")
    training.add_argument("--teto-epocas", type=int,
                          help="Teto de épocas (padrão: 2000, só de segurança; 150 reproduz a origem)")
    training.set_defaults(handler=_train)
    evaluation = science_commands.add_parser("avaliar-gpvs", help="Avalia os modelos treinados nos ensaios de teste")
    evaluation.add_argument("--modelos", type=Path, required=True, help="Pasta de uma rodada de treinar-gpvs")
    evaluation.add_argument("--saida", type=Path, required=True, help="Pasta nova para a avaliação")
    evaluation.add_argument("--dados", type=Path, default=DATA)
    evaluation.add_argument("--cache", type=Path, default=CACHE)
    evaluation.set_defaults(handler=_evaluate)
    reanalysis = science_commands.add_parser(
        "reanalisar-gpvs", help="Reanalisa os mesmos escores com o início observado das falhas")
    reanalysis.add_argument("--avaliacao", type=Path, default=Path("data/resultados/gpvs-avaliacao-001"))
    reanalysis.add_argument("--modelos", type=Path, default=Path("data/resultados/gpvs-modelos-002"))
    reanalysis.add_argument("--saida", type=Path, required=True, help="Pasta nova para a reanálise")
    reanalysis.add_argument("--dados", type=Path, default=DATA)
    reanalysis.add_argument("--cache", type=Path, default=CACHE)
    reanalysis.set_defaults(handler=_reanalyze)


def _purge(args) -> dict:
    return {} if args.separacao is None else {"purge": args.separacao}


def _new(folder: Path) -> None:
    if folder.exists():
        raise ValueError("A pasta de saída já existe; escolha uma pasta nova.")


def _prepare(args) -> int:
    from aliado.specializations.mestrado.gpvs import export_preparation, prepare, report

    _new(args.saida)
    prepared = prepare(args.dados, cache=args.cache, **_purge(args))
    print(json.dumps(export_preparation(prepared, report(prepared), args.saida), ensure_ascii=False, indent=2))
    return 0


def _train(args) -> int:
    from aliado.science.deteccao.redes.autoencoders import Hyperparameters
    from aliado.specializations.mestrado.gpvs import prepare
    from aliado.specializations.mestrado.training import (
        ExperimentConfig,
        export_training,
        train_detectors,
        training_blocks,
    )

    _new(args.saida)
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


def _evaluate(args) -> int:
    from aliado.specializations.mestrado.evaluation import (
        EvaluationConfig,
        export_evaluation,
        load_training,
        score_all,
    )
    from aliado.specializations.mestrado.gpvs import prepare

    _new(args.saida)
    trained = load_training(args.modelos)
    prepared = prepare(args.dados, cache=args.cache, purge=trained.config.purge, fractions=trained.config.fractions)
    config = EvaluationConfig()
    print(json.dumps(export_evaluation(score_all(trained, prepared), trained, prepared, config, args.saida),
                     ensure_ascii=False, indent=2))
    return 0


def _reanalyze(args) -> int:
    from aliado.science.deteccao.registro import consultas as registry
    from aliado.specializations.mestrado.reanalysis import EVALUATION, run

    _new(args.saida)
    paths = run(args.avaliacao, args.modelos, args.dados, args.saida, cache=args.cache)
    frozen = json.loads(Path(paths["configuracao"]).read_text(encoding="utf-8"))
    number = registry.record_reanalysis(args.saida.parent, source=args.avaliacao.name, output=args.saida.name,
                                        training=args.modelos.name,
                                        training_sha=frozen["origem"]["treino_configuracao_sha256"],
                                        config_sha=frozen["sha256"], canonical=EVALUATION)
    print(json.dumps(paths | {"consulta": number}, ensure_ascii=False, indent=2))
    return 0
