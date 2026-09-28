# Spec 0002 — preparação dos módulos e triagem

Data: 15/09/2026. Plano aprovado pelo usuário para implementação local.
Este lote prepara fronteiras e documentação; não entrega indexação ou execução
científica. O lote 01 permanece como base funcional da CLI e do gateway.

## Decisões aprovadas

- Nova base documental vazia. O pesquisador fornecerá documentos e referências
  posteriormente; repositórios entram como fontes documentais, sem indexar código.
- Memórias antigas serão triadas antes de qualquer ativação. Dados pessoais e
  trechos de conversas ficam fora do Git e fora do pacote instalável.
- Instruções, hipóteses e procedimentos editáveis em Markdown; cálculos e treino
  permanecem candidatos a módulos Python reproduzíveis, sem execução neste lote.
- Módulo web reservado agora; implementação, dependências e instalação opcionais
  serão definidas posteriormente. Não há servidor ou extra `web` instalável ainda.
- Origem fixa: `55c44df6bda807b73c4ac3762f0a89734633d384`, em `mestrado-utfpr`.

## Requisitos verificáveis

| ID | Comportamento |
|---|---|
| P01 | Pacotes `aliado.knowledge`, `aliado.memory`, `aliado.science` e `aliado.interfaces.web` importáveis, sem operações fictícias ou inicialização de serviços. |
| P02 | CLI e contratos do lote 01 preservados. Nenhuma nova ferramenta anunciada ao LLM. |
| P03 | Registro histórico de 13/09 preservado byte a byte; skill de pesquisa distingue acervo futuro, histórico e triagem não aprovada. |
| P04 | Inventário cobre os 30 arquivos de memória do commit-fonte; candidatos têm evidência localizada, motivo, domínio, recomendação e revisão humana pendente. |
| P05 | Relatórios privados em `data/memory-review/`, ignorados pelo Git e não carregados pelo agente. Nenhuma memória ativada. |
| P06 | Catálogo cobre as 13 ferramentas registradas na origem, distinguindo serviços gerais, texto editável, execução científica e funções adiadas. |
| P07 | Procedimentos em Markdown identificam finalidade, entradas, hipóteses, passos, limites e critérios de verificação. Divergência FMECA de seis versus quatro grupos documentada. |
| P08 | Origem intacta; sem restauração de índices, cópia de corpus ou datasets, treino, servidor, inferência paga, commit, push ou PR automático. |

## Entregáveis e aceitação

- [Fronteiras dos módulos](../arquitetura/modulos.md).
- [Catálogo de ferramentas](../migracao/ferramentas-lote-02.md) e
  [procedimentos científicos](../ciencia/procedimentos.md).
- Relatório privado de arquivos e candidatos, em grupos pequenos, aguardando
  revisão do pesquisador; a triagem não equivale a nova validação bibliográfica.
- [Manifesto do lote](../migracao/lote-02.json), separação dos lotes para revisão
  e registro dos testes em [validação](../migracao/validacao-lote-02.md).

Aceitação: cobertura de inventários e hashes, teste de importação sem estado,
CLI offline, bateria existente, lint e importação do wheel fora da pasta do
projeto. Não incluir relatórios privados na distribuição. Apresentar o resultado
ao usuário antes de qualquer operação Git de publicação ou versionamento.
