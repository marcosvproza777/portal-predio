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

## 12. Como o Assistente Consulta o Manual Operacional MYCOM

O manual `doc-mycom-001` (21 chunks) é carregado no contexto via `assistant_mock_data.py`.
O `assistant_engine.py` detecta o intent `mycom_manual` quando a pergunta contém termos como
`mycom`, `chiller`, `fluxostato`, `soft-starter`, `pressão de descarga`, etc.

Handlers específicos (em `_build_response()`):
- `fluxostato` → resposta direta do chunk 13
- `pressão de óleo baixa` → resposta do chunk 10
- `análise de óleo / quando fazer` → resposta do chunk 19
- `filtro coalescente / quando trocar` → resposta do chunk 20
- `alinhamento / eixos` → resposta do chunk 19
- Outros → busca via `_buscar_chunk_mycom()` por word-matching nos chunks

---

## 13. Como o Assistente Consulta a Tabela de Óleos Homologados

A tabela `doc-mycom-002` (4 chunks) é carregada no contexto. O `assistant_engine.py` detecta
os intents `mycold` e `oleo_homologado` antes do intent genérico `oleo`.

Fluxo de intents (ordem de prioridade):
1. `mycold` → MYCOLD AB/PAO queries
2. `oleo_homologado` → tabela de óleos, fluido específico, listagem
3. `revisao_condicao` → 20k horas, overhaul, desmontagem
4. `mycom_manual` → manual MYCOM genérico
5. `oleo` → óleo genérico (fallback com referência ao manual + tabela)

---

## 14. Como Responde sobre Manutenção MYCOM

O plano de manutenção em `page_ativos.py` inclui tarefas derivadas do Manual MYCOM:

| Pergunta tipo | Resposta esperada |
|---------------|-------------------|
| "Quando inspeção semanal?" | Semanal — sistema de gás e óleo, inspeção do selo de vedação |
| "Quando fazer análise de óleo?" | Semestral / 5.000 horas — coletar amostra para laboratório |
| "Quando trocar filtro coalescente?" | Anual / 10.000 horas — item da inspeção anual |
| "Quando calibrar PSV?" | Anual / 10.000 horas — calibração de instrumentos e segurança |
| "Quando conferir alinhamento?" | Semestral / 5.000 horas — tolerância 0,06 mm |

---

## 15. Como Responde sobre Óleo MYCOM

| Pergunta | Intent detectado | Resposta |
|----------|-----------------|----------|
| "Qual óleo MYCOM homologado?" | `mycold` / `oleo_homologado` | MYCOLD PAO |
| "O Mycold AB ainda é usado?" | `mycold` | MYCOLD AB 68 foi descontinuado → MYCOLD PAO |
| "O Mycold AB pode ser usado?" | `mycold` | Descontinuado. Usar MYCOLD PAO |
| "Quais óleos homologados?" | `oleo_homologado` | Lista dos 11 óleos ativos |
| "Óleo para R134a?" | `oleo_homologado` | MOBIL EAL ARCTIC 68, ICEMATIC SW 68, CAPELLA HFC 68 (POE) |
| "Óleo para Amônia?" | `oleo_homologado` | Opções PAO e mineral compatíveis com NH3 |
| "Pode usar qualquer ISO 68?" | `oleo_homologado` | Não — fluido, classe e tabela determinam a escolha |

---

## 16. Como Responde sobre MYCOLD AB 68

Quando o cliente perguntar sobre MYCOLD AB 68:

```
O MYCOLD AB 68 foi descontinuado. No Portal Pred.IO, a referência atual deve ser MYCOLD PAO.
O MYCOLD AB 68 pode aparecer apenas como referência histórica/inativa para redirecionamento,
mas não deve ser recomendado como óleo homologado atual.
```

Fonte obrigatória: `Tabela de Óleos Homologados MAYEKAWA/MYCOM`

---

## 17. Como Responde sobre MYCOLD PAO

```
Com base na Tabela de Óleos Homologados MAYEKAWA/MYCOM, o óleo MYCOM homologado atual
na base Pred.IO é MYCOLD PAO (ISO VG 68, classe PAO sintético, fluido: NH3/R22, 53 cSt @ 40°C).
A referência antiga MYCOLD AB 68 foi descontinuada e não deve ser usada como recomendação atual.
```

---

## 18. Como Responde sobre 20.000 horas

Quando o cliente perguntar sobre 20.000 horas, revisão geral, overhaul, desmontagem ou kit revisão,
o intent `revisao_condicao` é detectado e a resposta obrigatória é:

```
O manual cita a revisão/desmontagem como referência técnica para inspeção bienal ou 20.000 horas,
porém no Portal Pred.IO essa decisão não é automática por horímetro. A indicação deve considerar
a saúde real da máquina, com base em análise de vibração, análise de óleo, termografia, histórico
operacional, tendência de score, falhas recorrentes e avaliação técnica da equipe Pred.IO.

20.000 horas é referência técnica, não gatilho automático de overhaul.
A decisão depende da saúde real da máquina.

Recomenda-se abrir um chamado técnico ou aguardar a recomendação dos relatórios preditivos.
```

---

## 19. Como Evita Recomendações Automáticas de Overhaul

1. O plano de manutenção **não tem** tarefa com `tipo = "horimetro"` e `vencimento_horas = 20000`.
2. Os itens `pm-revisao-geral` e `pm-kit-revisao` têm `tipo = "condicao"`.
3. O `_SYSTEM_PROMPT` em `ai_assistant.py` instrui explicitamente a IA a nunca recomendar overhaul por horímetro.
4. O intent `revisao_condicao` captura qualquer variante de pergunta antes da IA responder.
5. A resposta sempre inclui a frase-chave obrigatória.

---

## 20. Como Orienta Abertura de Chamado em Situações Críticas

- Qualquer resposta sobre falha crítica, parada de máquina, ou risco operacional inclui
  o botão `🔧 Abrir Chamado Técnico` (page: `chamados`).
- Respostas sobre overhaul, desmontagem e kit revisão sempre incluem o botão de chamado.
- Respostas com `confidence: "baixa"` sempre incluem o chamado em `suggested_actions`.
- A função `is_critical_question()` em `ai_assistant.py` força o botão de chamado
  independentemente da resposta da IA.

---

## 21. Segurança — Confirmações

- ✅ Não criou sidebar
- ✅ Não expôs `ANTHROPIC_API_KEY` no front-end
- ✅ Não enviou WhatsApp ou e-mail
- ✅ `client_id` sempre da sessão Python
- ✅ Documentos internos (`Apenas equipe Pred.IO`) excluídos antes do prompt
- ✅ Observações internas removidas em `get_documentos_tecnicos(staff=False)`
- ✅ Dados de outros clientes nunca entram no contexto
- ✅ Perguntas sem autenticação não chegam à IA (require_auth no portal)
- ✅ MYCOLD AB 68 não aparece como óleo homologado ativo
- ✅ MYCOLD PAO cadastrado como óleo MYCOM atual
- ✅ 20.000 horas não gera tarefa automática no plano de manutenção
- ✅ Overhaul / desmontagem / kit revisão apenas como Decisão por Condição
