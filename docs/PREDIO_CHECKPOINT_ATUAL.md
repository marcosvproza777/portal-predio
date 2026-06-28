# CHECKPOINT TÉCNICO — Portal Pred.IO
**Data:** 2026-06-28  
**Branch:** main (up to date with origin/main)  
**Último commit:** `c2cabf2` — fix: remove dados de teste fictícios de chamados

---

## Stack Identificada

| Camada | Tecnologia |
|--------|-----------|
| Framework | Streamlit >= 1.35.0 |
| Backend / dados | Google Sheets via gspread >= 6.1.0 |
| Autenticação | SHA-256 + token de sessão em URL (?sid=) |
| IA / Síntese | Anthropic >= 0.40.0 (Claude Haiku) |
| Busca web | Tavily API (tavily-python >= 0.3.0) |
| PDFs | PyPDF2 >= 3.0.0 (primário) + pdfplumber >= 0.10.0 (fallback ≤ 5 MB) |
| Gráficos | Plotly >= 5.17.0, Matplotlib >= 3.8.0 |
| Word | python-docx >= 1.1.0 |
| PWA | pwa.py (manifest, bottom nav, sininho mobile) |
| Hosting | Render.com — free tier (512 MB RAM) |
| Imagens | Pillow >= 10.0.0 |
| Storage externo | Nenhum ativo (GCS sem billing; upload em memória) |

---

## Arquivos Principais

| Arquivo | Função |
|---------|--------|
| `app.py` | Entry point — roteador cliente / supervisão |
| `auth.py` | Autenticação SHA-256, sessão, client_id da sessão |
| `sheets.py` | Todas as operações com Google Sheets (cache, CRUD) |
| `ui.py` | CSS global, topnav, sidebar supervisão, faróis, assistente flutuante |
| `assistant_engine.py` | Motor de respostas controladas do Assistente Técnico |
| `assistant_mock_data.py` | Contexto mock por cliente (fallback) |
| `ai_assistant.py` | Módulo Claude API (não ativo — ANTHROPIC_API_KEY sem crédito) |
| `document_processor.py` | Extração de texto PDF + criação de chunks |
| `web_search_service.py` | Busca web controlada via Tavily |
| `notification_engine.py` | Motor de notificações internas |
| `notifications.py` | Helpers de notificação (contagem não lidas, etc.) |
| `pwa.py` | PWA: manifest, bottom nav mobile, sininho |
| `security.py` | Sanitização de rotas/parâmetros de URL |
| `report_word_generator.py` | Gerador de relatório executivo Word (.docx) |
| `version.py` | Grava static/version.txt a cada deploy (auto-refresh) |
| `drive_storage.py` | GCS upload (inativo — billing desabilitado) |
| `homologacao_setup.py` | Setup de cliente de homologação |

---

## Rotas — Portal do Cliente

| Rota (`portal_page`) | Módulo | Status |
|----------------------|--------|--------|
| `dashboard` | `page_dashboard.py` | ✅ Ativo |
| `farois` | `page_farois.py` | ✅ Ativo |
| `ativos` | `page_ativos.py` | ✅ Ativo |
| `manutencao` | `page_manutencao.py` | ✅ Ativo |
| `relatorios` | `page_relatorios.py` | ✅ Ativo |
| `assistente` | `page_assistente.py` | ✅ Ativo (botão flutuante) |
| `chamados` | `page_chamados.py` | ✅ Ativo |
| `alertas` | `page_alertas.py` | ✅ Ativo |
| `biblioteca` | `page_biblioteca.py` | ✅ Ativo (leitura) |
| `preferencias` | `page_preferencias_notificacao.py` | ✅ Ativo |
| `notificacoes` | `page_notificacoes_portal.py` | ✅ Ativo |

## Rotas — Supervisão Pred.IO (`sv_view`)

| Rota | Módulo | Status |
|------|--------|--------|
| `dashboard` | `page_sv_dashboard.py` | ✅ Ativo |
| `chamados` / `chamado_detalhe` | `page_sv_chamados.py` / `page_sv_chamado_detalhe.py` | ✅ Ativo (com delete + confirmação) |
| `clientes` / `cliente_historico` / `cliente_novo` | `page_sv_clientes.py` | ✅ Ativo |
| `ativos_sv` / `ativo_detalhe` / `ativo_novo` | `page_sv_ativos.py` | ✅ Ativo |
| `manutencao_sv` | `page_sv_manutencao.py` | ✅ Ativo |
| `alertas_sv` | `page_sv_alertas.py` | ✅ Ativo |
| `notificacoes_sv` | `page_sv_notificacoes.py` | ✅ Ativo |
| `biblioteca_sv` | `page_sv_biblioteca.py` | ✅ Ativo (cadastro + processamento) |
| `relatorios_sv` / `relatorio_novo` / `relatorio_editar` | `page_sv_relatorios.py` | ✅ Ativo |
| `assistente_sv` | `page_sv_assistente.py` | ✅ Ativo (auditoria + diagnóstico web) |
| `homologacao` | `page_sv_homologacao.py` | ✅ Ativo |
| `relatorio_executivo` | `page_sv_relatorio_executivo.py` | ✅ Ativo |

---

## Abas / Planilhas Google Sheets Identificadas

| Aba | Uso |
|-----|-----|
| `Clientes` | Usuários, empresa, perfil, senha hash |
| `Sessoes` | Tokens de sessão persistentes |
| `Chamados` | Chamados técnicos (CRUD completo) |
| `Mensagens_Chamados` | Histórico de mensagens por chamado |
| `Ativos` | Ativos industriais por cliente |
| `Componentes` | Componentes de ativos |
| `Horímetros` | Leituras de horímetro por ativo |
| `Manutencao` | Tarefas de manutenção |
| `Relatorios` | Relatórios técnicos publicados |
| `Relatorios_Chunks` | Chunks de relatórios para RAG |
| `Documentos_Tecnicos` | Biblioteca técnica (manuais, datasheets) |
| `Documento_Chunks` | Chunks de documentos para RAG |
| `Alertas` | Alertas da supervisão |
| `Notificacoes` | Notificações internas do portal |
| `WebSearchLog` | Log de auditoria de buscas web |
| `Relatorios_Executivos` | Relatórios executivos publicados |

---

## O Que Está Funcionando

- ✅ Login com SHA-256 + sessão persistente por token em URL
- ✅ Bifurcação cliente / supervisão com isolamento por client_id
- ✅ Dashboard do cliente com faróis de condição
- ✅ Plano de manutenção com cálculo de status
- ✅ Relatórios técnicos publicados (leitura + chunks)
- ✅ Relatório executivo de confiabilidade (criação + visualização)
- ✅ Gerador Word de relatório executivo (python-docx)
- ✅ Chamados técnicos — criação, detalhamento, resposta, delete (supervisão)
- ✅ Biblioteca Técnica — cadastro de documentos, upload em memória, indexação
- ✅ Assistente Técnico — motor controlado com +20 intents (oleos, mypro touch, mycom, etc.)
- ✅ Assistente — busca web via Tavily com fallback sem IA
- ✅ Assistente — consulta chunks de documentos e relatórios do cliente
- ✅ Alertas — criação e visualização
- ✅ Notificações internas do portal (lidas / não lidas)
- ✅ Preferências de notificação por cliente
- ✅ PWA — manifest, bottom nav mobile, sininho, banner de atualização
- ✅ Auditoria do Assistente (painel diagnóstico na supervisão)
- ✅ Homologação — setup de cliente de teste

---

## O Que Está Incompleto / Com Limitações

| Item | Situação |
|------|----------|
| Síntese web via Claude Haiku | Funciona mas conta Anthropic sem crédito — usa fallback de extração de trecho |
| Upload de PDF para storage externo | GCS sem billing → upload processado em memória (limite: 15 MB, PDFs simples) |
| Indexação de PDFs complexos (layout gráfico) | pdfplumber limitado a ≤5 MB; PDFs ≥5 MB com layout gráfico podem falhar |
| `drive_storage.py` | Implementação GCS mantida no código mas inativa |
| `ai_assistant.py` | Código existe mas ANTHROPIC_API_KEY sem crédito — motor controlado cobre os casos |
| Mock data em `document_processor.py` | Chunks mock ainda presentes para docs de demonstração (MYCOM, Mypro Touch, óleos) |
| Mock clientes em `assistant_mock_data.py` | Contexto fictício quando cliente não tem dados reais |

---

## Erros e Riscos Percebidos (Não Corrigidos)

1. **Anthropic sem crédito**: síntese da busca web cai no fallback de texto bruto — funcional mas menos preciso
2. **PDFs protegidos ou escaneados**: PyPDF2 não extrai texto de imagens — retorna vazio ou falha silenciosa
3. **Limite 15 MB upload**: PDFs grandes (manuais completos) precisariam de storage externo
4. **Mock data em documentos**: se o Assistente não encontrar chunks reais, o contexto usa mocks de demonstração que podem não corresponder ao equipamento real do cliente
5. **Sem lint/typecheck formal**: projeto não tem mypy nem flake8 configurados — erros de tipo podem existir silenciosamente
6. **`credentials_oneline.txt` e `credentials_b64.txt` na raiz**: arquivos de credenciais não devem estar no repositório git

---

## Próximos Passos Recomendados

1. Adicionar créditos na conta Anthropic para síntese web funcionar com Claude Haiku
2. Corrigir/validar fluxo de upload e indexação de PDF com documento real do cliente
3. Verificar se `credentials_oneline.txt` está no `.gitignore`
4. Avançar para Dashboard Executivo Final (etapa 2)
5. Implementar Preferências de Notificação e envio interno (etapa 4)
6. Homologação com cliente teste real (etapa 6)
