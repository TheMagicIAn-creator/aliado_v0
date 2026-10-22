# Spec 0044 - revisão e fechamento da 0.8.0

Estado: implementado e validado localmente em 20/10/2026; aguarda a revisão e o commit do pesquisador.

## Propósito e decisões

Fechar a versão 0.8.0 com os lotes 37 a 44 num único commit do pesquisador. A revisão dos lotes 37 a 43 encontrou
criação concorrente de conversas e escalada que anunciava o Gemini Flash, mas podia chamar o modelo menor.
O pesquisador aprovou um novo lote de revisão, preservando os registros das entregas anteriores.

## Requisitos vivos

- **INT-01, novo:** o anexo fica na conversa do envio; criação compartilhada com a primeira pergunta e navegação
  protegida contra respostas atrasadas. A spec viva de interface começa com esse requisito.
- **PRV-02, alterado:** a reprovação de uma resposta local é refeita explicitamente pelo Gemini Flash, inclusive
  quando o modelo menor foi escolhido por escrito. Flash sem configuração ou com falha mantém a resposta local
  com o motivo na rota e não dispara uma segunda tentativa automática.
- **BIB-01 e BIB-02, sem alteração:** ganham conferência integrada da reindexação sintética, além dos testes isolados.

## Implementação e compatibilidade

- A interface compartilha a promessa pendente; pergunta e anexo usam o identificador retornado pelo servidor.
  Abrir, criar ou apagar a conversa ativa muda a geração de navegação; resultados antigos não mudam a tela atual.
  O anexo continua indo ao destino original, e uma pergunta ainda esperando a criação é interrompida ao navegar.
- A criação espera os documentos já fixados; respostas tardias de fixação e mensagens não mudam outra conversa.
  Uma criação que falha pode ser tentada novamente.
- A escalada usa o alias `flash`, uma vez, com o local desligado nessa repetição. Sem Flash ou na falha dele, a rota
  explica o ocorrido; erros técnicos do SDK não aparecem ao pesquisador. O registro preserva a resposta local e
  conta como pago apenas o Gemini efetivamente concluído.
- Não mudam rotas HTTP, formatos dos pedidos existentes, limites de custo nem a configuração do modelo local.

## Registros e pacote

- Os registros 35/36 voltam ao conteúdo do commit 77fb76d. Os adendos posteriores são preservados na validação
  do lote 44, separados das novas verificações; o manifesto do lote 36 mantém seu hash original.
- O pacote final vem de uma cópia limpa dos fontes, em `dist/v0.8.0-fechamento/`, com conteúdo e SHA-256 registrados.
  Os pacotes anteriores são preservados. O README aponta esse diretório.
- As configurações locais de desenvolvimento não entram na lista explícita dos arquivos para commit.

## Aceitação

- Regressão JavaScript sem rede: anexo e pergunta nas duas ordens, navegação, nova conversa, falha e nova tentativa,
  documentos previamente fixados e respostas atrasadas. Node é necessário apenas para esse teste de desenvolvimento.
- Escalada com escolha escrita do menor, Flash indisponível, resposta cortada, Ollama fora do ar e registro de uso.
- Documento sintético: pendência real antes da descrição simulada, página em branco sem pendência e estado pronto
  após reindexar com a descrição, ainda pesquisável.
- Bateria completa offline por arquivo, Ruff, specs, isolamento do núcleo e pacote importado fora dos fontes.
- Nenhuma chamada a modelos reais, download, reindexação da biblioteca real, commit ou publicação neste fechamento.
