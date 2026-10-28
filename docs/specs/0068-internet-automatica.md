# Spec 0068 — a internet automática

## Propósito e decisões

**A origem:** o modo sem internet do lote 63 só ligava com `AL_IADO_OFFLINE=1` no .env ou com
`aliado web --sem-internet`. Sem rede e sem a variável, o que iria ao Gemini falhava com "O Gemini não respondeu" e, na
escalada, a resposta local se perdia.

**A decisão (pesquisador, 24/10/2026):** "Testa antes de usar": antes de chamar o Gemini ou a web, uma conexão rápida
com o servidor do Google, guardada por 30 s; sem rede, o modo entra sozinho, e o selo aparece e some na tela.
`AL_IADO_OFFLINE=1` continua forçando o modo.

## O que muda

- **No gateway (PRV-09, novo):** `Connectivity` abre uma conexão com `generativelanguage.googleapis.com:443`, por até
  2 s, sem enviar nada, e guarda a resposta por 30 s. Só é consultada quando a chamada iria a um provedor remoto: uma
  resposta do modelo local não espera por ela.
- **Na tela (INT-02, alterado):** as recusas, a resposta local mantida e o selo valem também sem rede. A recusa diz
  que o Gemini volta sozinho com a internet, em vez de mandar mexer no .env. O selo é conferido a cada resposta e a
  cada minuto.
- **O custo:** nenhum token. A conexão de teste não chega a enviar um pedido.

## Requisitos vivos

- **PRV-09 (novo), em `provedores.md`:** sem rede, o modo sem internet entra sozinho.
- **INT-02 (alterado), em `interface.md`:** o selo e a recusa também sem rede.

## Implementação

- **`src/aliado/llm/providers/gateway.py`:** `Connectivity`, o `online` e o `disconnected()` do gateway. A recusa
  passou para depois da conferência do modelo: sem modelo configurado, o erro continua sendo "Verifique…", e a rede
  nem é testada.
- **`src/aliado/interfaces/web/app.py`:** `online` nas configurações, `_offline` e `_hint` nas recusas e no
  `sem_internet` de `/api/estado`.
- **`src/aliado/interfaces/web/static/`:** o selo atualizado a cada resposta e a cada minuto (`app.js`) e a nota dele
  (`index.html`).

## Aceitação

- **O teste do PRV-09** (`tests/test_local_provider.py`): sem rede, a recusa; dentro dos 30 s, nenhuma conexão nova;
  com a rede de volta, o Gemini (falso) é chamado.
- **O teste do INT-02 sem rede** (`tests/test_web.py`): o selo segue a conexão e a recusa diz que o Gemini volta
  sozinho.
- **A bateria completa e o Ruff.**
- **Fica de fora:** um teste com a internet desligada de verdade, que fica para a bateria do lote 69.
