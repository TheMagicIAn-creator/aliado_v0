"""Mestrado do pesquisador: detecção de falhas em inversores fotovoltaicos, com a base de dados GPVS.

O núcleo lê só os atributos deste pacote. No topo, só a biblioteca padrão: numpy e PyTorch entram
dentro das funções de cada experimento.
"""

from aliado.specializations.mestrado import autoencoders

EXPERIMENTS = (autoencoders,)
