# Validação do lote 25 — confiabilidade por componente e disponibilidade

Verificação local em **30/09/2026**, sobre o commit `0cc8f78` (lote 24). **Nenhuma chamada paga.** O
assistente não fez push nem tag.

## Fontes conferidas nas páginas

As páginas foram renderizadas a partir dos PDFs da biblioteca e lidas antes de gravar `reparos.json`:
- **IEEE 493-2007, p. 290:** "Inverters, all types" com MTTR de 26 h, 2 falhas e 414,8 unidades-ano.
- **IEEE 493-2007, p. 283:** partidas de motor com contato de 0 a 600 V, 65,1 h de média e 24,5 h de mediana.
- **Baschel et al. (2018), Fig. 7:** inversor com MTTD de 1 dia, MTTR de 5 dias e parada de 6 dias. O OCR não lia as células verdes; a leitura foi feita na imagem.

## Números (só as taxas e os tempos das fontes)

| Grupo | Base | λ/ano | F(20 anos) | Disponibilidade, IEEE 493 a Baschel | Horas paradas por ano |
|---|---|---:|---:|---|---|
| CCB | operação | 0,256 | 99,4% | 99,924% a 99,581% | 6,65 a 36,8 h |
| CCB | calendário | 0,558 | 99,98% | 99,835% a 99,091% | 14,5 a 80,4 h |
| Contatores | operação | 0,0334 | 48,7% | 99,990% a 99,945% | 0,87 a 4,8 h |
| IGBT | operação | 0,0357 | 51,1% | 99,989% a 99,941% | 0,93 a 5,2 h |
| IGBT | calendário | 0,078 | 79,0% | 99,977% a 99,872% | 2,0 a 11,2 h |
| Ventiladores | operação | 0,107 | 88,3% | 99,968% a 99,824% | 2,8 a 15,4 h |

A CCB, com a maior taxa, é a que mais para: até 80 h por ano no calendário com a parada de campo.

## Testes

- `tests/test_components.py`, com 7 testes:
  - os blocos por grupo e base;
  - os números do IGBT e da CCB;
  - a disponibilidade igual à do serviço RAM;
  - as tabelas de reparo inválidas;
  - as fontes com tabela e página;
  - a FMECA e a skill;
  - a rota.
- `tests/test_fmeca.py`: o limite antigo ("sem tempo de reparo") deu lugar ao novo, com os dois cenários.

**416 testes passaram** (409 do lote 24 e 7 novos). O Ruff não apontou problemas, e `ciencia.js` e `graficos.js` passaram na checagem de sintaxe.

## Aceite no navegador

A interface de teste rodou em `127.0.0.1:8774`, com a cópia `tmp/lote-25`. Os prints foram feitos por Chrome headless.

| Item | Resultado |
|---|---|
| Confiabilidade | O seletor funciona nas 3 posições (as duas, operação e calendário). Aparecem o gráfico dos 4 grupos (cheia e tracejada), os 4 painéis com os cartões e a faixa de disponibilidade com a tabela, as fontes e o explorador no fim. |
| FMECA | A matriz S × O traz os 4 grupos e o D no rótulo. Os pares discordantes aparecem pelo nome. |
| Termos na tela | A varredura das 6 seções de dados não achou códigos M, "canônica", commit, caminho do projeto anterior nem nome de arquivo. "Semente" só aparece dentro da nota que a explica. |
| Exportação | SVG em fundo branco, sem variáveis de CSS, com o tracejado da base de calendário. PNG com 3.125 px de largura, e a matriz com 1.625 px. |
| Tela estreita (360 px) | Sem rolagem lateral na Confiabilidade (as duas bases e só a operação) e na FMECA. |
| Console e servidor | Sem erros. |

## Defeitos encontrados e corrigidos no aceite

1. **A tabela de disponibilidade não aparecia.** A seção é uma grade, e o contêiner que rola na horizontal encolhia a zero. A tabela passou a ficar dentro de uma seção, como nas outras. A mesma checagem nas demais seções não achou outra tabela com altura zero.
2. **Termos internos:**
   - os 8 cenários diziam "Horizonte de 20 anos (M12)", que também aparecia no formulário do explorador;
   - uma ressalva da FMECA citava commit e caminho do projeto anterior;
   - o limite novo citava o nome do arquivo `reparos.json`.
3. **Cartões densos:** os nomes dos cenários de reparo ficaram curtos nos cartões e na tabela, e F(t) passou a 4 algarismos, porque "100%" escondia 99,98%.

## Estado final

- `.claude/launch.json` ganhou a entrada `aliado-web-lote-25`.
- `tmp/lote-25` pode ser apagada depois da revisão.
- O commit do lote 25 foi feito pelo assistente, com a autorização do pesquisador (30/09), sem push.
