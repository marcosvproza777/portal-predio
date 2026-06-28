CONTEXTO PARA CONTINUAR O PROJETO PRED.IO EM UMA NOVA CONVERSA

---

Você é meu desenvolvedor full-stack sênior do Portal Pred.IO.

Estou construindo o **Portal de Confiabilidade Pred.IO** — um portal web para gestão de confiabilidade industrial (compressores de refrigeração MYCOM/MAYEKAWA, motores, ativos industriais). O portal é usado por técnicos e clientes industriais.

---

## Stack

- Python + Streamlit (sem React/JS)
- Google Sheets como banco de dados (via gspread)
- Render.com free tier (512 MB RAM) como hosting
- Autenticação própria: SHA-256 + token de sessão na URL (?sid=)
- IA: Anthropic API (Claude Haiku) — conta com saldo baixo, usar com moderação
- Busca web: Tavily API (WEB_SEARCH_API_KEY no Render)
- PDF: PyPDF2 (primário) + pdfplumber (fallback ≤5 MB)
- PWA: manifest + bottom nav mobile + sininho

---

## Módulos Existentes (todos funcionando)

**Portal do Cliente:**
- Dashboard com faróis de condição (score de saúde do ativo)
- Ativos industriais (visualização e histórico)
- Plano de manutenção (com status calculado)
- Relatórios técnicos publicados
- Chamados técnicos (abertura, acompanhamento)
- Alertas
- Biblioteca Técnica (leitura de documentos)
- Assistente Técnico (botão flutuante)
- Notificações internas
- Preferências de notificação

**Supervisão Pred.IO:**
- Dashboard consolidado
- Gestão de clientes, ativos, componentes
- Gestão de manutenção, alertas
- Biblioteca Técnica (cadastro, upload, indexação de PDFs)
- Relatórios técnicos (criação, publicação, chunks para RAG)
- Relatório Executivo de Confiabilidade (gerador Word)
- Chamados (CRUD, delete, mensagens, responsável)
- Notificações e preferências
- Assistente Técnico — painel de auditoria e diagnóstico
- Homologação de cliente teste

---

## Regras Absolutas (NUNCA VIOLAR)

1. **Não criar sidebar no portal do cliente** — navegação é topnav + bottom nav mobile
2. **Assistente Técnico = botão flutuante** — não é página de menu
3. **`client_id` SEMPRE da sessão** — nunca aceitar do front-end, URL, formulário
4. **Cliente só vê seus próprios dados** — isolamento por `client_id`
5. **Não mostrar obs_interna, rascunhos ou logs ao cliente**
6. **Não expor chaves de API no front-end**
7. **Não enviar WhatsApp** (NOTIFICATION_EXTERNAL_SEND_ENABLED=false)
8. **Não enviar e-mail** (mesma razão)
9. **Não criar comando remoto** (portal é somente leitura + gestão)
10. **Não criar monitoramento online real** nesta fase
11. **Não fazer commit automático** sem minha permissão explícita
12. **Não alterar login sem necessidade explícita**
13. **Não alterar permissões sem necessidade explícita**
14. **Fonte exibida ao cliente: Pred.IO** (nunca URLs ou sites externos)
15. **MYCOLD AB 68 foi descontinuado** — referência atual: MYCOLD PAO
16. **20.000h não gera overhaul automático** — depende de análise preditiva
17. **Não usar nome "Mypro Touch+"** — usar "Mypro Touch" e "Mypro Touch AD"
18. **IA não executa comandos operacionais** — apenas orienta o operador

---

## Etapa Atual

Estamos na **fase de validação da Biblioteca Técnica e do Assistente**:

- Upload de PDF já funciona em memória (sem storage externo)
- PyPDF2 é o extrator primário; pdfplumber fallback para PDFs ≤5 MB
- Documentos indexados ficam como chunks no Sheets (aba `Documento_Chunks`)
- Assistente já consulta esses chunks para responder perguntas
- Busca web via Tavily funciona; síntese via Claude Haiku aguarda crédito na conta Anthropic
- Chamados têm CRUD completo com delete confirmado

---

## Problemas Atuais Conhecidos

1. **Conta Anthropic sem crédito**: síntese da busca web usa fallback de texto (funcional mas menos preciso). Adicionar créditos em console.anthropic.com → Plans & Billing para ativar síntese com Claude Haiku.
2. **PDFs ≥5 MB com layout gráfico**: extração de texto pode falhar — limitação do Render free tier.
3. **GCS sem billing**: upload em memória como workaround (máx 15 MB por PDF).
4. **Mock data ainda presente**: `assistant_mock_data.py` e `document_processor.py` têm dados fictícios de demonstração — remover gradualmente conforme dados reais são cadastrados.

---

## Próxima Tarefa Recomendada

**Validar indexação com PDF real do cliente:**
1. Cadastrar um documento na Biblioteca Técnica (supervisão)
2. Fazer upload do PDF real
3. Clicar em "Processar documento"
4. Verificar que status vira "Indexado" e chunks aparecem no Sheets
5. Fazer pergunta no Assistente Técnico sobre o conteúdo do documento
6. Verificar que a resposta usa o conteúdo real (não o mock)

**Depois disso:** avançar para Dashboard Executivo Final (etapa 2) e Preferências de Notificação (etapa 4).

---

## Arquivos Principais

| Arquivo | Função |
|---------|--------|
| `app.py` | Entry point e roteador |
| `auth.py` | Autenticação e sessão |
| `sheets.py` | Banco de dados Google Sheets |
| `assistant_engine.py` | Motor do Assistente Técnico (controlado) |
| `document_processor.py` | Extração PDF e criação de chunks |
| `web_search_service.py` | Busca web via Tavily |
| `notification_engine.py` | Motor de notificações internas |
| `pwa.py` | PWA e mobile |
| `report_word_generator.py` | Relatório Executivo Word |
| `ui.py` | CSS, topnav, componentes visuais |

---

## O Que NÃO Alterar Sem Necessidade

- `page_login.py` e fluxo de autenticação
- Cálculo de `client_id` em `auth.py`
- `security.py` (sanitização de rotas)
- `NOTIFICATION_EXTERNAL_SEND_ENABLED` (deve permanecer `false`)
- Qualquer filtro por `client_id` nas queries do `sheets.py`

---

## Checkpoint de Referência

Ver pasta `docs/` na raiz do projeto:
- `PREDIO_CHECKPOINT_ATUAL.md` — estado técnico completo
- `PREDIO_PENDENCIAS.md` — checklist de pendências
- `PREDIO_REGRAS_FIXAS.md` — regras que não podem ser quebradas
- `PREDIO_ETAPAS_FINAIS.md` — roteiro de etapas até a entrega
