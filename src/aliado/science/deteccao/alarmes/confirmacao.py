"""A regra do alarme: a m-ésima janela seguida acima do limiar; uma sequência longa é um alarme só."""

from __future__ import annotations

import numpy as np

CONFIRMATIONS = 3


def alarm_starts(above, confirmations: int = CONFIRMATIONS) -> np.ndarray:
    """Janelas em que um alarme dispara: a m-ésima de uma sequência seguida acima do limiar.

    Enquanto as janelas seguem acima, é o mesmo alarme; um novo exige voltar abaixo antes.
    """
    if isinstance(confirmations, bool) or int(confirmations) < 1:
        raise ValueError("A confirmação exige ao menos uma janela.")
    alarms, run = [], 0
    for index, flag in enumerate(np.asarray(above, dtype=bool)):
        run = run + 1 if flag else 0
        if run == confirmations:
            alarms.append(index)
    return np.asarray(alarms, dtype=int)


def first_alarm(above, confirmations: int = CONFIRMATIONS) -> int | None:
    starts = alarm_starts(above, confirmations)
    return int(starts[0]) if len(starts) else None
