# Spec 0063 — o modo sem internet

Estado: feito em 23/10/2026; commit f920740.

## Propósito e decisões

**A origem:** o pesquisador perguntou se dá para rodar o AL-IAdo sem internet. Quase tudo já roda no computador (o
modelo local, a busca, a tela, a memória e o Obsidian). Mas, sem rede, o que iria ao Gemini falhava com "O Gemini não
respondeu. Tente de novo em instantes.", às vezes depois de o local já ter trabalhado.

**A decisão (pesquisador, 23/10/2026):** "Sim, implemente o lote 63 como planejado."

**O que muda:**
- **Como liga:** `AL_IADO_OFFLINE=1` no `.env`, ou `aliado web --sem-internet` para uma vez só. Sem isso, nada muda.
- **No gateway:** toda chamada que iria a um provedor remoto é recusada antes de abrir a conexão, com o motivo. Isso
  vale para a escalada no limite do local, para o que o local não alcança (web, contexto, páginas) e para o pedido com
  `local=False`.
- **Na tela, antes do modelo:** a busca na web, a leitura ampla e a conferência de uma anotação na web são recusadas
  na hora.
- **A resposta local que o Gemini refaria** (sem citação ou com números que não conferem) fica como veio, com
  "modo sem internet" na rota, como já acontece quando o Flash não está configurado.
- **O selo:** "Sem internet" no topo da tela, com uma nota ao passar o mouse.
- **O custo:** nenhum token. Nenhuma chamada nova.

**Uma mudança em relação ao plano:** o plano recusava a descrição das figuras na hora. Com o modelo local ligado,
porém, é ele que descreve as figuras (PRV-01), então ela segue pelo local; a página que ele não alcança fica por
descrever, como já acontecia quando uma página falhava.

## Requisitos vivos

- **PRV-08 (novo), em `provedores.md`:** sem internet, nada sai do computador.
- **INT-02 (novo), em `interface.md`:** o selo e a recusa com o motivo.

## Implementação

- **`src/aliado/llm/providers/gateway.py`:** `OfflineRefusal`, `offline_from_env` e a recusa em `execute` e em `stream`.
- **`src/aliado/interfaces/web/app.py`:** o campo `offline` das configurações, as recusas antes do modelo, a mensagem
  da recusa, a escalada que não acontece e o `sem_internet` em `/api/estado`.
- **`src/aliado/interfaces/web/static/`:** o selo (`index.html`, `app.css`, `app.js`).
- **`src/aliado/cli.py`:** a opção `--sem-internet` e a mensagem no terminal.

## Aceitação

- **Os testes do PRV-08 e do INT-02:** o Gemini falso não é chamado em nenhum caso recusado, e sem a variável tudo
  segue como antes.
- **A bateria completa e o Ruff.**
- **Fica de fora:** a escolha do modo na própria tela (a tela não tem seletores), o modo sem a chave do Gemini no
  `.env` (a tela ainda pede um modelo Gemini configurado) e um teste com a internet desligada de verdade.
