"""A base GPVS-Faults (Bakdi et al., 2020; DOI 10.17632/n76t439f65.1): os 16 ensaios, as colunas, as falhas e a
amostragem de 10 kHz, com a janela de um ciclo de 50 Hz. Pelo M11, FMECA e GPVS são análises independentes: não há
mapeamento entre as falhas do conjunto e os grupos da FMECA.
"""

from __future__ import annotations

from pathlib import Path

# Onde a base fica no projeto (lote 51: era repetido no terminal e no experimento).
DATA_DIR = Path("data/gpvs")

DATASET_NAME = "GPVS-Faults"
DATASET_DOI = "10.17632/n76t439f65.1"
HEALTHY = ("F0L", "F0M")
FAULTY = tuple(f"F{fault}{mode}" for fault in range(1, 8) for mode in "LM")
EXPERIMENTS = HEALTHY + FAULTY
SOURCE_COLUMNS = ("Time", "Ipv", "Vpv", "Vdc", "ia", "ib", "ic", "va", "vb", "vc", "Iabc", "If", "Vabc", "Vf")
# Descrição nativa do conjunto e se a falha é física; sem correspondência com a FMECA (M11).
FAULTS = {
    1: ("Falha completa de um IGBT", True),
    2: ("Erro de 20% no sistema de sensor/realimentação", False),
    3: ("Afundamentos intermitentes de tensão da rede", False),
    4: ("Sombreamento parcial não uniforme (10–20%)", False),
    5: ("Circuito aberto em 15% do arranjo fotovoltaico", True),
    6: ("Ganho do controlador PI reduzido em 20%", False),
    7: ("Constante de tempo do controlador PI elevada em 20%", False),
}
MODES = {"L": "IPPT (potência limitada)", "M": "MPPT (potência máxima)"}
SAMPLING_HZ = 10_000.0
GRID_HZ = 50.0
WINDOW = int(round(SAMPLING_HZ / GRID_HZ))  # um ciclo de rede: 200 amostras
WINDOWS_PER_HOUR = 3600 * SAMPLING_HZ / WINDOW  # 180.000, para a taxa de alarmes por hora
