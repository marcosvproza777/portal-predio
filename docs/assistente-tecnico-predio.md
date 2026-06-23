# Assistente Técnico Pred.IO — Documentação Técnica

## 1. O que o assistente faz hoje

O Assistente Técnico é um botão flutuante presente em todas as páginas do
Portal do Cliente. Permite que o cliente faça perguntas em linguagem natural
sobre a sua operação e receba respostas controladas e seguras.

**Funcionalidades ativas:**
- Detecta a intenção da pergunta (manutenção, relatórios, documentos, etc.)
- Busca dados autorizados do cliente (ativos, manutenções, relatórios, chamados, alertas, documentos)
- Responde com texto estruturado + botões de navegação para as páginas do portal
- Sugestões rápidas clicáveis na janela do chat
- Persiste estado aberto/fechado via localStorage
- Navega para páginas do portal via botões de ação

## 2. O que ele ainda NÃO faz

- Não usa IA generativa (Claude, OpenAI, etc.)
- Não consulta n8n
- Não lê PDFs automaticamente
- Não envia WhatsApp ou e-mail
- Não acessa dados fora do portal Pred.IO
- Não inventa especificações técnicas — se não houver dado cadastrado, informa ao usuário
- Não tem memória de conversas anteriores (stateless)

## 3. Como funciona a busca controlada

```
Cliente digita pergunta
        ↓
JavaScript detecta intenção (espelho de assistant_engine.py)
        ↓
Consulta PRED_CONTEXT (JSON embutido server-side ao renderizar a página)
        ↓
Monta resposta estruturada + links de navegação
        ↓
Exibe resposta ao cliente com botões de ação
```

**O PRED_CONTEXT é construído em Python** (`assistant_engine.get_client_context(client_id)`)
e embutido no iframe do assistente no momento do render. O `client_id` vem da
sessão do servidor — nunca do front-end.

## 4. Quais dados o assistente consulta

| Categoria       | Fonte atual              | Futura integração         |
|-----------------|--------------------------|---------------------------|
| Ativos          | `assistant_mock_data.py` | `sheets.get_ativos()`     |
| Manutenções     | `assistant_mock_data.py` | `sheets.get_manutencoes()`|
| Relatórios      | `assistant_mock_data.py` | `sheets.get_relatorios()` |
| Documentos      | `assistant_mock_data.py` | `sheets.get_documentos()` |
| Chamados        | `assistant_mock_data.py` | `sheets.get_chamados()`   |
| Alertas         | `assistant_mock_data.py` | `sheets.get_alertas_sv()` |
| Espec. de óleo  | `assistant_mock_data.py` | Campo no cadastro do ativo|

Para substituir mock por dados reais: editar `assistant_engine.get_client_context()`
e descomentar a chamada às funções de sheets.

## 5. Regras de segurança por client_id

- `client_id` é obtido de `st.session_state["client_id"]` (definido na autenticação)
- `client_id` é passado para `inject_floating_assistant(sid, client_id)` via `app.py`
- `get_client_context(client_id)` filtra TODOS os dados por `client_id` antes de retornar
- O JavaScript no iframe recebe apenas dados já autorizados (PRED_CONTEXT)
- O JavaScript NUNCA tem acesso ao `client_id` — apenas aos dados já filtrados
- Dados da Supervisão Pred.IO NÃO aparecem em PRED_CONTEXT
- Observações internas de chamados NÃO são incluídas
- Documentos internos da Pred.IO NÃO são incluídos

## 6. Como será a futura integração com IA

Quando a IA for integrada, o fluxo mudará assim:

```
Cliente pergunta no assistente flutuante
          ↓
JavaScript faz fetch('POST /api/assistant/technical-query', { pergunta, rota_atual, ativo_id })
          ↓
Endpoint Python obtém client_id da SESSÃO (nunca do payload)
          ↓
assistant_engine.query_assistant(client_id, pergunta) busca dados autorizados
          ↓
IA (Claude/n8n/RAG) gera resposta usando APENAS as fontes encontradas
          ↓
Portal exibe resposta + fontes + botões de ação
```

**Endpoint preparado:**

```
POST /api/assistant/technical-query
Headers: Authorization: Bearer <token_sessao>
Payload: {
  "pergunta":      "Quais são as próximas manutenções?",
  "rota_atual":    "manutencao",     (opcional)
  "ativo_id":      "ativo-001",      (opcional)
  "componente_id": "comp-001"        (opcional)
}
Resposta: {
  "answer":            "As próximas ações programadas são...",
  "related_links":     [{"label": "📅 Ver Plano", "page": "manutencao"}],
  "related_documents": [],
  "related_reports":   [],
  "suggested_actions": []
}
```

A lógica do endpoint já existe em `assistant_engine.query_assistant()`.
Basta expô-la via Flask/FastAPI quando necessário.

## 7. Como evitar respostas inventadas

Regras implementadas:
1. O assistente responde apenas com dados presentes em PRED_CONTEXT
2. Se não houver dado, responde: "Não encontrei informação suficiente..."
3. Para especificação de óleo: se `especificacoes.oleo` for `null`, informa que não há cadastro e orienta abrir chamado
4. Nenhuma string de resposta é gerada por IA — são textos fixos parametrizados com dados reais

Exemplo — pergunta: "Qual óleo usar nessa unidade?"
- Se `especificacoes.oleo` tiver valor → retorna o valor cadastrado
- Se `especificacoes.oleo` for `null` → "Não encontrei especificação de óleo cadastrada para este ativo..."

## 8. Como tratar solicitação de manuais técnicos

Ao detectar intenção `documentos`:
1. Busca `ctx.documentos` — lista de documentos da Biblioteca Técnica do cliente
2. Se houver documentos → lista os títulos + botão "Abrir Biblioteca Técnica"
3. Se não houver → orienta contato com equipe Pred.IO + botão "Abrir Chamado"

**O assistente NÃO lê o PDF diretamente.** Direciona para a Biblioteca Técnica
onde o cliente pode visualizar e baixar o documento.

## 9. Arquivos do assistente

| Arquivo                    | Papel                                               |
|----------------------------|-----------------------------------------------------|
| `assistant_engine.py`      | Motor: detect_intent, get_client_context, query_assistant |
| `assistant_mock_data.py`   | Dados mockados estruturados por client_id           |
| `assistant.py`             | Webhooks n8n: call_assistant, send_whatsapp         |
| `ui.py`                    | inject_floating_assistant() — iframe + CSS + JS     |
| `app.py`                   | Chama inject_floating_assistant(sid, client_id)     |
| `docs/assistente-tecnico-predio.md` | Esta documentação                          |

## 10. Intenções detectadas

| Intenção       | Palavras-chave (exemplos)                               | Resposta                        |
|----------------|---------------------------------------------------------|---------------------------------|
| manutencao     | manutenção, plano, vibração, termografia, horímetro...  | Lista ações programadas + link  |
| relatorios     | relatório, laudo, análise preditiva...                  | Lista relatórios + link         |
| documentos     | manual, datasheet, biblioteca, pdf...                   | Lista documentos + link         |
| oleo           | qual óleo, óleo usar, especificação de óleo...          | Valor cadastrado ou aviso       |
| status_ativo   | status, condição, score, crítico, compressor...         | Status + score + componentes    |
| chamados       | chamado, solicitação, suporte...                        | Status chamados + link          |
| alertas        | alerta, aviso, notificação...                           | Lista alertas ativos + link     |
| nao_encontrado | qualquer outra pergunta                                 | Orienta abrir chamado           |

---

*Pred.IO — Manutenção Preditiva Inteligente*
