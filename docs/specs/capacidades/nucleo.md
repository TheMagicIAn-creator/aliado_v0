# Capacidade: núcleo e especializações

Spec viva: diz o que vale **hoje** para a separação entre o núcleo do AL-IAdo e as especializações. Vem da
[spec 0001](../0001-fundacao.md): o núcleo é independente de domínio, e as especializações entram à parte.

Criada no lote 34 (17/10/2026), pela [spec 0034](../0034-experimentos.md).

## Requisitos

**NUC-01. Núcleo sem domínio.** Nenhum arquivo do núcleo menciona o domínio de uma especialização. O núcleo é
tudo em `src/aliado/` fora de `src/aliado/specializations/<nome>/`, em .py, .js, .html, .css, .md e .json; a
menção é medida por `gpvs|inversor|mestrado|fotovolt`, sem diferenciar maiúsculas. O núcleo acha as
especializações percorrendo a pasta, sem citá-las pelo nome.
*Cenário:* dado um arquivo novo no núcleo com "GPVS" no texto, então `tests/test_isolation.py` falha.
*Transição:* até o lote 36, os arquivos que ainda têm menções estão listados no teste, com o número de linhas;
cada lote só pode diminuí-lo, e o lote 36 zera a lista.
