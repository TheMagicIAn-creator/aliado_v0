# Validação do lote 35 — chat com tela mínima e pedidos escritos

Data: 18/10/2026. Escopo na [spec 0035](../specs/0035-chat-tela-minima.md); requisitos vivos em
[capacidades/roteador.md](../specs/capacidades/roteador.md). Nenhuma chamada paga.

## Bateria

| Conferência | Resultado |
|---|---|
| `pytest` | 785 testes passaram (eram 764 no lote 34) |
| `ruff check .` | sem apontamentos |
| Testes novos | `test_routing.py` (17: os pedidos e os casos que não são pedidos), `test_web.py` (3), `test_learning.py` (1) |
| Testes revistos | os da página (sem os seletores e as chaves), o dos resultados (disponíveis sem o campo) e o do "Ler mais fundo" |
| Requisitos vivos citados por testes | ROT-01 a ROT-07: todos |

## Pela tela (servidor de teste `aliado-web-lote-35`, porta 8783)

O servidor usa a interface, as rotas, o roteador e o agente reais, com o modelo e a reescrita simulados e uma
biblioteca de teste com três documentos.

- **Tela mínima:** a barra do topo ficou com o uso de tokens, a fonte e o tema; a caixa de mensagem, com anexar,
  "Documentos" e enviar. A tela de boas-vindas diz as frases que se podem escrever. Nenhum erro no console, a
  1.280 px e a 375 px.
- **Pedido escrito:** "Use o modelo maior. O que é o alfa no manual de manutenção?" respondeu com o modelo maior. A
  linha da rota disse "Modelo: pedido por você", e "seguiu o seu pedido" trouxe "Você pediu por escrito: o modelo
  maior".
- **Só o pedido:** "Faça a leitura ampla." refez a pergunta anterior, com o modelo maior pedido antes. A tela
  perguntou antes de ler ("Leitura ampla, como você pediu. Esta leitura envia cerca de 36 mil tokens…"); com
  "Ler assim", leu os 3 documentos inteiros, e a rota disse "leitura ampla" e que a pergunta anterior foi refeita.

## Correções durante a validação

- **Falsos pedidos:** "Sem a biblioteca de componentes, ..." e "Use o modelo maior do artigo..." eram lidos como
  pedidos. Uma frase seguida de "de/do/da" fala de outra coisa e deixou de valer como pedido; "Leia o artigo inteiro
  do Pertile" continua valendo, porque o pedido do documento inteiro fica no texto.
- **Descrição:** a leitura ampla aparecia como "leitura: leitura ampla"; ficou "leitura ampla".

## Menções ao domínio no núcleo

| Arquivo | Antes | Depois |
|---|---:|---:|
| `interfaces/web/app.py` | 4 | 1 |
| `interfaces/web/static/app.js` | 5 | 0 |
| `interfaces/web/static/index.html` | 1 | 0 |

## Fica para depois

- **Frases fora da lista:** ficam no texto, e o roteador decide como antes.
- **Pedido que fala de outra coisa:** "Usando o modelo maior, o MCC sobe?" ainda é lido como pedido.
- **Uso no dia a dia:** para usar a tela nova, é preciso reiniciar o AL-IAdo.
