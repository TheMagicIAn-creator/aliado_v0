# Capacidade: núcleo e especializações

Spec viva: diz o que vale **hoje** para a separação entre o núcleo do AL-IAdo e as especializações. Vem da
[spec 0001](../0001-fundacao.md): o núcleo é independente de domínio, e as especializações entram à parte.

Criada no lote 34 (17/10/2026), pela [spec 0034](../0034-experimentos.md); NUC-01 completado e NUC-02 e NUC-03
acrescentados no lote 36 (18/10/2026), pela [spec 0036](../0036-mestrado-fora-do-nucleo.md).

## Requisitos

**NUC-01. Núcleo sem domínio.** Nenhum arquivo do núcleo menciona o domínio de uma especialização. O núcleo é
tudo em `src/aliado/` fora de `src/aliado/specializations/<nome>/`, em .py, .js, .html, .css, .md e .json; a
menção é medida por `gpvs|inversor|mestrado|fotovolt`, sem diferenciar maiúsculas. O núcleo acha as
especializações percorrendo a pasta, sem citá-las pelo nome.
*Cenário:* dado um arquivo novo no núcleo com "GPVS" no texto, então `tests/test_isolation.py` falha.

**NUC-02. O que uma especialização entrega.** Uma especialização é um pacote em `src/aliado/specializations/<nome>/`,
só com a biblioteca padrão no topo. O núcleo lê dele estes atributos, quando precisa e nunca ao importar os módulos
do núcleo:
- `EXPERIMENTS`: os experimentos que a aba Ciência roda do zero;
- `DEFAULT_SKILL`, `DATASET_DIR` e `REFERENCE_DIR`: a skill da pesquisa, a base de dados e a pasta com a FMECA,
  os cenários e os tempos de reparo;
- `ROUTING`: frases de exemplo do roteador, a skill da pesquisa e as palavras que levam aos resultados;
- `REWRITE_SUBJECT`: os assuntos da biblioteca, para a reescrita da busca;
- `NOTES`: o glossário da aba Ciência e dos resultados no chat;
- `add_commands`: comandos do terminal, dentro de `aliado ciencia`;
- `science_routes`: as rotas e o estado da aba Ciência que dependem da pesquisa (a rodada atual e os exploradores);
- `results_digest`: os resultados citáveis [R1]… do chat.

Sem nenhuma especialização, o núcleo abre e responde, sem esses extras.
*Cenário:* dada a especialização do mestrado, então `aliado ciencia treinar-gpvs` existe, o roteador leva "GPVS"
aos resultados e a aba recebe o glossário; e importar o terminal, o roteador e o agente não importa a especialização.

**NUC-03. Skills de especialização.** As skills de uma especialização ficam em `specializations/<nome>/skills/` e
aparecem com as do núcleo (`aliado skills`); com o mesmo nome, vale a do núcleo. A skill geral que acompanha uma
skill quando ninguém escolhe outra é declarada no SKILL.md dela (`metadata.apoio`), não no código.
*Cenário:* dada a skill da pesquisa com `apoio: "confiabilidade"`, quando o chat a usa, então as instruções de
confiabilidade vão junto; a de engenharia vai sozinha.

**NUC-04. Pastas que dizem o que têm.** Toda pasta de `src/aliado` com código é um pacote (tem `__init__.py`), para
não sumir do pacote instalado. Nas pastas de `science/` e nas do mestrado, o `__init__.py` só explica o que a pasta
tem e em que etapa entra, sem importar nada; a exceção é o `__init__.py` do próprio mestrado, o contrato com o núcleo
(NUC-02). O mapa das pastas fica em `docs/ciencia/mapa-das-pastas.md`.
*Cenário:* dada uma pasta nova em `science/` sem `__init__.py`, ou com um `__init__.py` que importa algo, então
`tests/test_isolation.py` falha.
