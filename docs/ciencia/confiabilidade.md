# Cálculos de confiabilidade, mantenabilidade e disponibilidade

O serviço executa cenários definidos pelo usuário. Não estima parâmetros a partir
de dados nem presume que uma fórmula se aplica fisicamente a um inversor.

## Contrato

Campos obrigatórios: `name`, `kind`, `time_unit`, `parameters`, `sources` e
`assumptions`. Curvas exigem também `times`, lista crescente de tempos finitos,
não negativos e sem repetições. `sources` e `assumptions` são listas de textos.
Unidades aceitas: `s`, `min`, `h`, `day`, `year`. Não há conversão automática,
exceto a opção explícita `time_base`, descrita abaixo.

| `kind` | `parameters` | Resultado |
|---|---|---|
| `exponential` | `rate > 0`, em 1/tempo | R(t), F(t), h(t), MTTF |
| `weibull` | `shape > 0`, adimensional; `scale > 0`, em tempo | R(t), F(t), h(t), MTTF |
| `series` | `independent: true`, `components` | R(t), F(t) do sistema |
| `parallel` | `independent: true`, `components` | R(t), F(t) do sistema |
| `maintainability_exponential` | `mttr > 0`, em tempo | M(t), probabilidade de reparo até t |
| `availability_inherent` | `mtbf > 0`, `mttr >= 0`, mesma unidade | disponibilidade inerente estacionária; não aceita `times` |

Cada componente de série/paralelo contém `name`, `model` (`exponential` ou
`weibull`) e `parameters` do modelo. Nomes devem ser distintos. Os componentes
usam a unidade temporal comum ao cenário; não aceitam unidades individuais.

### Taxa por hora em horizonte anual

A única conversão oferecida é opcional e vale só para `exponential` com
`time_unit: "year"`. Ela existe para que a taxa em 1/h nunca seja convertida
em probabilidade de cabeça:

```json
"time_base": {"rate_unit": "h", "hours_per_year": 4015, "basis": "operation"}
```

`rate` continua em 1/h. O serviço multiplica a taxa por `hours_per_year`, que deve
ser maior que 0 e no máximo 8.784. Os tempos e o MTTF são expressos em anos dessa
base; h(t), em 1/ano; R(t) e F(t) são probabilidades adimensionais.
O valor `basis` (`operation` ou `calendar`) indica se as horas são de operação
ou de calendário. O resultado registra `summary.rate` em 1/ano,
`units["parameters.rate"] = "1/h"` e a conversão nas limitações. F(t) permanece
uma probabilidade entre 0 e 1; uma taxa nunca é apresentada como porcentagem.

## Métodos e hipóteses

Exponencial: `R(t)=exp(-rate*t)`, `F(t)=1-R(t)`, `h(t)=rate`, `MTTF=1/rate`.
Exige taxa constante. [NIST: distribuição exponencial](https://www.itl.nist.gov/div898/handbook/apr/section1/apr161.htm).

Weibull: `R(t)=exp(-(t/scale)^shape)`, `F(t)=1-R(t)`,
`h(t)=(shape/scale)*(t/scale)^(shape-1)` e
`MTTF=scale*Gamma(1+1/shape)`. Para `shape < 1`, h(0) tem limite infinito:
o JSON usa `null` e `hazard_status: positive_infinity`, sem números JSON inválidos.
[NIST: Weibull](https://www.itl.nist.gov/div898/handbook/apr/section1/apr162.htm).

Série: `R_s=produto(R_i)`. Paralelo ativo: `R_p=1-produto(1-R_i)`.
Ambos pressupõem independência; o paralelo exige que um componente sozinho baste.
Não incluem reparo, standby, causa comum ou redistribuição de carga.
[NIST: série](https://www.itl.nist.gov/div898/handbook/apr/section1/apr182.htm),
[NIST: paralelo](https://www.itl.nist.gov/div898/handbook/apr/section1/apr183.htm).

Mantenabilidade exponencial: `M(t)=1-exp(-t/MTTR)`, assumindo tempo de reparo
exponencial. Disponibilidade inerente: `A_i=MTBF/(MTBF+MTTR)` no regime estacionário.
MTBF significa tempo médio de operação entre falhas; MTTF não o substitui
automaticamente. A disponibilidade inerente exclui manutenção preventiva e
atrasos logísticos/administrativos; não é disponibilidade operacional.
[NASA: definições de disponibilidade](https://extapps.ksc.nasa.gov/Reliability/Documents/Availability_What_is_it.pdf).

## Execução e revisão

O exemplo distribuído é **sintético**, sem parâmetros de equipamento:

```powershell
.\.venv\Scripts\python.exe -m aliado ciencia calcular --cenario docs/ciencia/exemplo-sintetico.json --saida data/resultados/exemplo-001 --grafico
```

PNG requer o extra `science`. A pasta de saída precisa ser nova; repetir o mesmo
comando com pasta existente falha sem sobrescrever. JSON conserva cenário,
referências de métodos, unidades, resultados e limitações; CSV contém curvas;
Markdown apresenta parâmetros, fontes e hipóteses. A exportação não altera o JSON
de entrada. A correção das fontes informadas não é verificada automaticamente.

O chat pode ajudar a redigir o cenário e explicar resultados fornecidos. Ele não
chama este serviço sozinho. O núcleo geral não tem horizonte padrão; os 20 anos
da pesquisa e eventuais mudanças pelo chat orientam o cenário da especialização.
No lote 07, Rodolfo escolheu as taxas e a análise isolada dos componentes dos
inversores, em duas bases temporais; não há topologia de sistema nesses cenários.
As taxas ainda precisam de reconferência nos PDFs. No lote 16, Rodolfo decidiu a FMECA:
- o NPR é o da fonte das notas;
- a leitura pelas taxas (MTBF, chance de falhar e falhas esperadas) fica separada;
- não há disponibilidade para os inversores enquanto não houver fonte de tempo de reparo.

Veja os [cenários da especialização](../pesquisa-inversores/cenarios/) e a
[tabela da FMECA](../pesquisa-inversores/fmeca.json).

Os limites de representação numérica são verificados. Aproximações extremas em
ponto flutuante não validam uma hipótese física. Os testes usam valores analíticos
e sintéticos; nenhuma curva desta entrega é resultado empírico do mestrado.
