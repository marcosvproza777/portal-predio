# Assistente Técnico Pred.IO — Integração com IA

## 1. Estratégia de Integração

**Opção A — Backend direto (escolhida)**

O Streamlit roda em Python no servidor Render.com. A chamada para a Anthropic API
acontece server-side (`ai_assistant.py`), nunca no browser do cliente.

- `ANTHROPIC_API_KEY` em variável de ambiente do servidor — nunca exposta ao front-end
- `client_id` sempre da sessão Python — nunca do payload do browser
- Contexto filtrado e montado em Python antes de qualquer chamada à IA

**Opção B — n8n (disponível como fallback)**

Se `ANTHROPIC_API_KEY` não estiver configurada, `assistant.py` → `call_assistant()`
pode usar `N8N_ASSISTANT_WEBHOOK_URL`. O fluxo de segurança é o mesmo.

---

## 2. Como o Assistente Busca Contexto

Fluxo em `ai_assistant.query_ai(client_id, pergunta)`:

```
1. client_id da sessão Python (st.session_state)
2. assistant_engine.get_client_context(client_id)
   ├── sheets.get_documentos_tecnicos(client_id, staff=False)  ← filtra internos
   ├── sheets.get_chunks_documento(doc_id)                     ← conteúdo dos manuais
   └── assistant_mock_data.get_mock_context(client_id)         ← fallback mock
3. _build_context_str(ctx)  ← monta texto estruturado sem dados internos
4. Anthropic API (server-side, haiku, 1500 tokens)
5. _parse_ai_response(raw)  ← extrai JSON: answer, confidence, sources, actions
```

**Fontes consultadas (em ordem de prioridade):**
1. Plano de manutenção (ações, prazos, tipos)
2. Ativos e componentes (status, score, alertas de componentes)
3. Relatórios técnicos (títulos, datas)
4. Chamados e alertas ativos
5. Biblioteca Técnica — documentos autorizados
6. Chunks dos manuais indexados (conteúdo real extraído do PDF)

---

## 3. Como `client_id` é Protegido

- `client_id` vem de `st.session_state["client_id"]` via `current_client_id()`
- Nunca aceito de parâmetros de URL livres ou do corpo de requisição do browser
- `get_documentos_tecnicos(client_id, staff=False)` filtra por `Cliente_Id` OU `"Público para clientes autorizados"`
- `get_chunks_documento(doc_id)` retorna apenas chunks do `doc_id` fornecido — já implicitamente do cliente
- Dados de outros clientes nunca entram no contexto

---

## 4. Como Documentos Internos são Bloqueados

`get_documentos_tecnicos(client_id, staff=False)` aplica:
```python
df = df[df["Status"].str.strip() == "Ativo"]
df = df[df["Visibilidade"].str.strip() != "Apenas equipe Pred.IO"]
```

Documentos com visibilidade `"Apenas equipe Pred.IO"` nunca chegam ao contexto
e portanto nunca chegam ao prompt da IA.

---

## 5. Como Fontes são Exibidas

A IA retorna um array `sources` em JSON:
```json
[
  {"titulo": "Manual Técnico - 200 VLD", "tipo": "Manual", "secao": "Especificações de Óleo"}
]
```

`page_assistente.py:_render_bot_msg()` exibe as fontes abaixo da resposta em um card
com título, tipo e seção. Botões de ação são exibidos abaixo.

---

## 6. Nível de Confiança

| Confiança | Cor   | Quando                                               |
|-----------|-------|------------------------------------------------------|
| alta      | verde | Resposta de fonte direta (manual, plano, relatório)  |
| media     | amarelo | Correlação entre fontes disponíveis                |
| baixa     | vermelho | Sem fonte suficiente — sempre sugere chamado      |

A IA classifica por conta própria, seguindo o system prompt. Perguntas críticas
detectadas por `is_critical_question()` forçam adição do botão "Abrir Chamado"
independentemente do nível de confiança.

---

## 7. Como Tratar Perguntas sem Base

Se o contexto não tiver a informação, o system prompt instrui:
> "Se a informação não estiver disponível no contexto, diga claramente que não encontrou base suficiente."

Retorna `confidence: "baixa"` e `suggested_actions` com chamado técnico.

---

## 8. Como Tratar Casos Críticos

O system prompt instrui:
> "Para decisões críticas (overhaul, troca de rolamento, parada de equipamento),
> recomende abertura de chamado — nunca tome a decisão sozinho."

`is_critical_question()` em `ai_assistant.py` detecta padrões críticos no texto
da pergunta e força o botão "Abrir Chamado Técnico" na resposta, independentemente
do que a IA classificou.

---

## 9. Como Integrar n8n (se desejado futuramente)

Configurar `N8N_ASSISTANT_WEBHOOK_URL` no Render. O fluxo existente em `assistant.py:call_assistant()`
já envia `client_id` (da sessão), `pergunta` e `timestamp` para o webhook. O n8n
pode então chamar a IA com os mesmos dados e retornar `{resposta, fontes}`.

Para usar n8n como primário: remova `ANTHROPIC_API_KEY` e configure o webhook.
Os dois podem coexistir — `ai_assistant.query_ai()` usa a API key quando disponível.

---

## 10. Auditoria de Perguntas e Respostas

Cada pergunta é salva em `AssistenteLogs` (Google Sheets):
```
Client_Id | Email | Pergunta | Resposta | Fontes | Confidence | Sources_Json | Data_Hora
```

- `salvar_log_assistente()` em `sheets.py` grava cada interação
- `get_historico_assistente(client_id)` retorna o histórico filtrado por cliente
- O histórico é exibido em `page_assistente.py` via botão "Ver histórico completo"
- **Futuramente**: tela na Supervisão para visualizar perguntas, respostas e fontes de todos os clientes

---

## 11. Testes Obrigatórios

| Pergunta | Esperado |
|----------|----------|
| "Quando é a próxima análise de vibração?" | Plano: próxima data 17/08/2026 |
| "Quando é a próxima termografia?" | Plano: próxima data 17/10/2026 |
| "Tem manual do compressor 200 VLD?" | Encontra doc-001, botão Biblioteca |
| "Qual óleo usar nessa unidade?" | Busca chunks → VDL 46 ou "não encontrei" |
| "A bomba de óleo está crítica?" | Status Crítico, sugere chamado |
| "Preciso fazer overhaul?" | Depende de vibração/óleo/termografia, abre chamado |
| "Tem procedimento interno de análise?" | Não retorna doc interno (filtrado) |
| "Mostre dados da Sibele Alimentos" | Não retorna dados de outro cliente |

---

## 12. Segurança — Confirmações

- ✅ Não criou sidebar
- ✅ Não expôs `ANTHROPIC_API_KEY` no front-end
- ✅ Não enviou WhatsApp ou e-mail
- ✅ `client_id` sempre da sessão Python
- ✅ Documentos internos (`Apenas equipe Pred.IO`) excluídos antes do prompt
- ✅ Observações internas removidas em `get_documentos_tecnicos(staff=False)`
- ✅ Dados de outros clientes nunca entram no contexto
- ✅ Perguntas sem autenticação não chegam à IA (require_auth no portal)
