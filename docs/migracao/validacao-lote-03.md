# Validação do lote 03

Data: 22/09/2026. Implementação local autorizada e concluída para revisão.
O lote transfere diretrizes aprovadas para o contexto do agente; não executa
ciência, cria memória persistente ou importa o acervo antigo.

## Resultados observados

| Verificação | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest` | 50 testes passaram (Python 3.12.14, pytest 9.1.1). |
| `.venv/Scripts/python.exe -m ruff check .` | Sem problemas. |
| Skill Creator `quick_validate.py`, com `-X utf8` | Skill `pesquisa-inversores` válida, versão 0.1.2. |
| Construção do wheel | Backend `setuptools.build_meta.build_wheel`, setuptools 84.0.0 já disponível no Python auxiliar; sem instalar dependências. |
| Inspeção do wheel | 28 entradas, 23 arquivos do pacote conferidos byte a byte contra `src/aliado/`; somente pacote e metadados. |
| Importação e CLI do wheel em diretório externo | Preparação offline passou com rede, subprocessos, escrita e leitura do projeto bloqueadas, exceto o wheel e dependências já instaladas na venv. |
| Isolamento do domínio | Pedidos sem skill e com `engenharia` não recebem GPVS, FMECA, p99 ou horizonte de 20 anos nas instruções. |
| Referência vigente | M09–M14 correspondem aos textos aprovados; carregadas somente por `pesquisa-inversores`, como contexto documental. |
| Preservação do núcleo | Comparação AST confirma que funções e APIs de `agent.py` permanecem iguais; mudou apenas `CORE_INSTRUCTIONS`. |
| Histórico e privacidade | Registro de 13/09 preservado no checkout e no wheel, sem carregamento automático. Revisão privada inalterada e fora do Git/pacote. |
| Escopo | 10 arquivos existentes alterados, 3 novos, nenhuma exclusão; demais arquivos e estado Git da origem preservados. |

Wheel: `tmp/lote-03/dist/aliado-0.1.0-py3-none-any.whl`.
SHA-256: `8032fb970327363900fb419c1fc2e34ac7c4a8e6286915b6738eab603a6f954f`.

O build usa a instalação auxiliar já existente de setuptools; a venv do projeto
não tem esse backend. Nenhuma biblioteca foi instalada ou alterada neste lote.
A primeira tentativa da checagem isolada bloqueou também a leitura legítima de
PyYAML na venv. O verificador foi corrigido para permitir dependências instaladas;
o pacote passou mantendo bloqueio dos fontes do projeto, dados e relatórios privados.

## Critérios da spec

- **D01:** M01–M08 e M16 mapeadas ao núcleo; M09–M14 à referência da pesquisa;
  M15 à arquitetura. IDs, destinos e hashes constam do [manifesto](lote-03.json).
- **D02–D03:** referências restritas à skill selecionada; o histórico permanece
  arquivado e a referência aprovada substitui seu carregamento automático.
- **D04:** preparação não lê arquivos externos à skill; verificação do wheel
  confirma exclusão de relatórios, conversas e arquivos temporários.
- **D05:** sem mudanças nos contratos, CLI, gateway ou funções do agente;
  nenhuma ferramenta oferecida e nenhum SDK, ML ou servidor importado ao iniciar.
- **D06:** wheel importado e CLI executada diretamente dele, fora do projeto,
  sem rede, credenciais ou criação de arquivos no diretório de execução.
- **D07:** instruções e documentos distinguem planejamento textual, regras
  aprovadas, evidência científica e implementação futura.

## Exemplo de contexto verificado

Na preparação de “Planeje o estudo com horizonte de 15 anos”, a CLI inclui as
regras aprovadas da pesquisa (padrão de 20 anos substituível pelo prazo solicitado)
e preserva o pedido de 15 anos como última mensagem. Nenhum cálculo é executado.
Para pedidos gerais e de engenharia, essa referência não é incluída.

Este teste verifica o pedido enviado ao modelo. Não houve inferência real,
avaliação da qualidade científica de respostas, treinamento, indexação ou consulta
a PDFs. O módulo científico continua reservado; p99 e os percentuais são regras
de planejamento configuráveis, não resultados demonstrados neste destino.

## Proveniência e revisão

O manifesto mapeia as 16 decisões sem publicar o relatório privado ou suas
transcrições. As decisões científicas foram preservadas textualmente na nova
referência; os princípios gerais foram adaptados às capacidades atuais do núcleo.
M15 é uma decisão de arquitetura, sem integração MCP instalada.

O baseline e a checagem isolada ficam em `tmp/lote-03/`, ignorado pelo Git.
A verificação final confere hashes, conteúdo curado, links locais, escopo,
privacidade e preservação da origem. A distinção entre histórico dos lotes
anteriores e estado atual foi mantida; seus manifestos e validações não mudaram.

O resultado está disponível para revisão antes do primeiro commit. Não houve
commit, push ou PR. A implementação de novos serviços exige outro lote combinado.
