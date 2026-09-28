# Spec 0001 — fundação e primeira transferência

Estado: lote 01 implementado e validado localmente; sujeito à revisão do usuário
antes de commit, push ou PR. Especificação de 2026-09-13; validação consolidada em 2026-09-14.

## Propósito e decisões

O AL-IAdo dará apoio à pesquisa e engenharia, inicialmente ao mestrado do usuário
sobre detecção de falhas em inversores fotovoltaicos. O núcleo é independente de
domínio e as especializações são carregadas como skills. Futuramente atenderá
outros trabalhos e pesquisas.

O produto completo deverá ter acesso web privado por convite, dados privados por
usuário e execução supervisionada de ações. Este lote entrega uma biblioteca e
um CLI local sem persistência; autenticação, interface web, RAG, memória e
execução de ferramentas são lotes posteriores, a definir com o usuário.

## Requisitos do lote

| ID | Comportamento verificável |
|---|---|
| F01 | Contratos, registro de modelos e gateway vêm de um commit imutável da origem, com mapa e hashes dos arquivos-fonte. |
| F02 | Importar o núcleo não inicializa SDKs, bancos, datasets, ML, rede ou leitura de `.env`. |
| F03 | Listar skills lê seus metadados; preparar uma pergunta carrega apenas a skill selecionada e suas referências declaradas. |
| F04 | Sem skill, o núcleo não contém regras do mestrado. Com `pesquisa-inversores`, recebe as decisões de 13/09/2026 como contexto histórico, sem promovê-las a auditoria bibliográfica nova. |
| F05 | OpenAI e Gemini preservam a distinção entre instruções, mensagens do usuário e respostas; encaminham contexto e saída estruturada. |
| F06 | Preparar um pedido é offline. Inferência exige comando explícito, provedor e modelo configurados; nenhuma ferramenta de escrita ou execução é oferecida neste lote. |
| F07 | Ausência de chave, modelo ou SDK é comunicada sem mostrar credenciais. Modelos desabilitados ou incompatíveis falham antes da chamada. |
| F08 | Acervo, snapshots, memórias, `.env`, resultados e dados brutos da origem não entram no novo ambiente. O repositório de origem permanece intacto. |

## Interfaces e organização

- `aliado.llm.contracts`: contratos `LLMRequest`, `LLMResult`, `LLMStreamChunk` e metadados de uso, preservando a API conceitual da origem.
- `aliado.llm.providers`: registro, gateway e adaptadores OpenAI/Gemini com SDKs opcionais e configuração explícita.
- `aliado.skills`: descoberta e leitura de skills empacotadas; referências Markdown são dados de contexto e nunca código executável.
- `aliado.agent`: prepara pedidos com núcleo geral e skill opcional; recebe o gateway por injeção para testes offline.
- `aliado.cli`: comandos `skills`, `preparar` e `perguntar`; a escolha inicial da interface é a skill de pesquisa, sem fixá-la no núcleo.

Usamos `SKILL.md` com frontmatter `name`/`description` e `metadata` textual.
O metadado próprio `references` declara nomes de arquivos Markdown separados por
vírgula, dentro de `references/`. Suporte a scripts, descoberta remota, instalação
automática de skills e escolha automática de skill não fazem parte deste lote.

## Aceitação e limites

- Reexecutar testes reaproveitados dos contratos, gateway e adaptadores, com clientes simulados.
- Testar transmissão das instruções nos dois provedores, leitura seletiva das skills,
  bloqueio de caminhos externos e falhas de configuração antes de rede.
- Testar CLI offline e a distribuição instalável contendo as referências.
- Não executar chamadas pagas, treinos ou indexação como validação automática.
- Os testes provam integração e contratos; qualidade científica das respostas requer
  avaliação posterior com o novo corpus e perguntas reais do pesquisador.
- Quantidades/representação dos contatores, taxa do IGBT e revisão dos NPR continuam
  pendentes. Não completar essas decisões com valores herdados.

## Sequência posterior para discussão

1. Revisar e versionar este lote com o usuário.
2. Selecionar o novo corpus e migrar recuperação documental/guardas de evidência.
3. Isolar e validar as ferramentas e os experimentos do mestrado conforme decisões atuais.
4. Adaptar interface, memória, autenticação e isolamento antes de acesso por convidados.

O formato das specs segue requisitos e cenários revisáveis em Markdown, inspirado
no [OpenSpec](https://github.com/Fission-AI/OpenSpec). A adoção do CLI desse projeto
permanece uma decisão posterior; não é dependência da execução do AL-IAdo.
