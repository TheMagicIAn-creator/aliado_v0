"""Mestrado do pesquisador: detecção de falhas em inversores fotovoltaicos, com a base de dados GPVS.

O núcleo lê só os atributos deste pacote (lotes 34 e 36). No topo, só a biblioteca padrão: numpy, PyTorch e a
interface web entram dentro das funções.

- `EXPERIMENTS`: o experimento AE Denso × AE-LSTM (`autoencoders`).
- `DEFAULT_SKILL`, `DATASET_DIR` e `REFERENCE_DIR`: a skill da pesquisa (em `skills/`), a base GPVS e a pasta
  com a FMECA, os cenários e os tempos de reparo.
- `ROUTING`, `REWRITE_SUBJECT` e `NOTES`: o que o roteador, a reescrita da busca e a aba Ciência leem daqui.
- `add_commands`, `science_routes` e `results_digest`: os comandos `aliado ciencia *-gpvs`, as rotas da aba
  Ciência com a rodada atual e os exploradores, e os resultados [R1]…[R8] do chat.
"""

from pathlib import Path

from aliado.specializations.mestrado import autoencoders
from aliado.specializations.mestrado.comandos.terminal import add_commands
from aliado.specializations.mestrado.digest import cached as results_digest
from aliado.specializations.mestrado.notes import NOTES
from aliado.specializations.mestrado.routing import ROUTING

EXPERIMENTS = (autoencoders,)
DEFAULT_SKILL = "pesquisa-inversores"
DATASET_DIR = autoencoders.DATASET_DIR
REFERENCE_DIR = Path("docs/pesquisa-inversores")
REWRITE_SUBJECT = "confiabilidade, manutenção, sistemas fotovoltaicos e aprendizado de máquina"

__all__ = ["DATASET_DIR", "DEFAULT_SKILL", "EXPERIMENTS", "NOTES", "REFERENCE_DIR", "REWRITE_SUBJECT", "ROUTING",
           "add_commands", "results_digest", "science_routes"]


def science_routes(settings, worker, lock):
    """As rotas da aba Ciência do mestrado e o estado dos exploradores; só a interface web as pede."""
    from aliado.specializations.mestrado.web import science_routes as routes

    return routes(settings, worker, lock)
