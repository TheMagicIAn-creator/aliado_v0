# Spec 0050 — a ciência geral em pastas com nomes em português

Estado: feito em 22/10/2026, com commits locais autorizados pelo pesquisador no plano de 21/10; push e tag ficam com
ele.

## Propósito e decisões

O pesquisador quer verificar cada etapa do método no mestrado, cada uma numa pasta com o nome do que tem e só aquilo.
Os nomes ficam em português por enquanto; o inglês vem depois.

**Decisões de 21/10:**
- `src/aliado/science/` mantém o nome, pela regra 4 do relatório em LaTeX, e as pastas técnicas de dentro ficam em
  português;
- as funções e as classes ficam com os nomes de hoje;
- mover não muda conta: só o caminho de importação;
- nenhum atalho de compatibilidade para os caminhos antigos.

## Requisitos vivos

- **NUC-04, novo:** toda pasta com código é um pacote. Nas pastas de `science/` e do mestrado, o `__init__.py` só
  explica o que a pasta tem.

## Implementação

**Dois commits, para o Git seguir o histórico:**
1. **A mudança de lugar** (e4e59ab), com os arquivos inteiros:
   - `detection/` → `deteccao/`, com `models.py` → `redes/autoencoders.py`, `protocol.py` → `particao/blocos.py`,
     `threshold.py` → `limiar/calibracao.py`, `metrics.py` → `metricas/por_janela.py` e `registry.py` →
     `registro/consultas.py`;
   - `ram.py` → `confiabilidade/cenarios.py`;
   - `fmeca.py` → `fmeca/calculo.py`;
   - `components.py` → `componentes/disponibilidade.py`;
   - `digest.py` → `resumo_citavel/formato.py`.
2. **A divisão:** as definições inteiras vão para os arquivos de cada pasta (lista completa no
   [mapa das pastas](../ciencia/mapa-das-pastas.md)):
   - `treino/laco.py`, `pesos/arquivos.py`, `inferencia/erros.py` e `escore/top_k.py`;
   - `particao/sequencias.py`, `particao/autocorrelacao.py` e `normalizacao/escala_robusta.py`;
   - `alarmes/confirmacao.py`, `alarmes/taxa.py` e `metricas/incerteza.py`;
   - `confiabilidade/artefatos.py`;
   - `fmeca/tabela.py`, `fmeca/relatorio.py` e `fmeca/artefatos.py`;
   - `componentes/reparos.py`.

**As importações:**
- Foram reescritas pelo caminho novo de cada nome, em `src`, `tests` e `ferramentas`.
- `science/__init__.py` deixou de reexportar `evaluate_scenario` e `export_result`; os usos importam de
  `confiabilidade/`.
- O extra `science`, `science_routes` e `interfaces/web/science.py` mantêm os nomes.

**Documentos:**
- o mapa das pastas, novo: etapa → equação → pasta → funções → teste, e a tabela do nome antigo para o novo;
- a skill de confiabilidade;
- `docs/arquitetura/modulos.md`.

## Aceitação

- A bateria completa passando, com os testes com os dados reais.
- A equivalência sem nenhuma diferença contra a referência do lote 49, depois de cada commit.
- NUC-01, NUC-02, NUC-04 e Ruff.
- Os comandos `aliado ciencia treinar-gpvs --help`, `aliado experimento listar` e `aliado experimento pdf`.
- Toda importação de `aliado…` resolve, nenhuma pasta fica só com `__pycache__`, e o wheel traz todos os módulos.
