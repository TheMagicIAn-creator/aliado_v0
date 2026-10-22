"""Plugin do pytest usado por `ferramentas/bateria.py`: conta os treinos de rede e mede o pico de memória.

Só age com a variável ALIADO_MEDICAO apontando para o JSON de saída. Com ALIADO_CONTAR_TREINOS, envolve o laço de
treino (`fit`) antes de qualquer teste importá-lo, para contar cada chamada; a conta e os pesos não mudam.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

# Onde o laço de treino é definido (lote 50).
FIT_MODULES = ("aliado.science.deteccao.treino.laco",)

_output = os.environ.get("ALIADO_MEDICAO")
_counted = {"treinos": 0}
_counting = False


def _wrap_fit() -> bool:
    for name in FIT_MODULES:
        try:
            module = importlib.import_module(name)
        except ImportError:
            continue
        original = module.fit

        def fit(*args, **kwargs):
            _counted["treinos"] += 1
            return original(*args, **kwargs)

        module.fit = fit
        return True
    return False


def _peak_mib() -> float:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

        kernel32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
        return counters.PeakWorkingSetSize / 2**20
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KiB no Linux


if _output and os.environ.get("ALIADO_CONTAR_TREINOS"):
    _counting = _wrap_fit()


def pytest_sessionfinish(session, exitstatus):
    if _output:
        Path(_output).write_text(json.dumps({"treinos": _counted["treinos"] if _counting else None,
                                             "pico_memoria_mib": round(_peak_mib(), 1)}), encoding="utf-8")
