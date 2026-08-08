# Resumo Técnico Completo — Portal Pred.IO
> Atualizado em 2026-06-26 | 95 commits | Branch: main | Deploy: Render

---

## 1. O Que Já Foi Criado

### Portal do Cliente (acesso via login com token `sid` na URL)
- Login com sessão persistente por token na URL (`?sid=...`)
- Dashboard executivo com faróis de confiabilidade, KPIs e chamados recentes
- Faróis de Confiabilidade — lista de ativos com score preditivo
- Meus Equipamentos — ativos reais do cliente (mock removido)
- Manutenção Preventiva — planos e tarefas por condição
- Relatórios Técnicos — somente publicados (rascunho nunca exposto ao cliente)
- Assistente IA — FAB flutuante, motor preditivo com RAG
- Chamados Técnicos v2 — abertura, histórico, mensagens visiveis ao cliente
- Alertas Preditivos
- Biblioteca de Documentos
- Preferências de Notificação
- Central de Notificações do Portal
- **Logo do cliente** exibido entre o topnav e o conteúdo
- **Bottom nav mobile** — 5 itens fixos + drawer "Mais" (JS puro, `z-index 999990`)
- **Banner de atualização** — polling `static/version.txt` a cada 3 min, aparece ao detectar novo deploy
- **PWA instalável** — manifest, Service Worker, ícones gerados da logo.jpg

### Supervisão Pred.IO (staff/admin)
- Sidebar dark com 11 itens de menu + logout
- **Topnav pill bar horizontal** — iframe `components.html`, `white-space:nowrap`, sem quebra de texto
- Dashboard de supervisão com métricas globais
- Gestão de Chamados + detalhe + mensagens internas
- **Gestão de Clientes** — listagem, histórico, cadastro com upload de logo, edição de dados
- **Gestão de Ativos** — listagem, detalhe, cadastro, edição de campos
- Planos de Manutenção
- Alertas
- Avisos / Notificações
- Relatórios Técnicos (criação, edição, publicação)
- Biblioteca de Documentos (upload, indexação para IA)
- Assistente IA para supervisores
- Homologação com cliente teste (checklist 20 itens)

---

## 2. Funcionalidades Já Funcionando em Produção

| Status | Funcionalidade |
|--------|---------------|
| ✅ | Login / logout com sessão persistente |
| ✅ | Portal do cliente completo (dashboard, ativos, chamados, relatórios, alertas, biblioteca, assistente) |
| ✅ | Bottom nav mobile com drawer "Mais" |
| ✅ | Assistente flutuante (FAB) posicionado acima do bottom nav |
| ✅ | Supervisão — sidebar dark com navegação completa |
| ✅ | Supervisão — pill nav horizontal sem quebra de texto |
| ✅ | Cadastro de clientes com upload de logo (compressão 160×160 JPEG 75%) |
| ✅ | Logo do cliente exibida no portal entre nav e conteúdo |
| ✅ | Edição de dados do cliente (Nome, Email, Telefone — Empresa read-only) |
| ✅ | Edição de dados do ativo (todos os campos) |
| ✅ | Banner de atualização do app (polling version.txt) |
| ✅ | PWA instalável no mobile |
| ✅ | Remoção do bottom nav ao fazer logout |
| ✅ | Nome da empresa sem quebra de linha no topnav mobile (`white-space:nowrap`) |
| ✅ | Marcador ativo do bottom nav atualiza ao navegar |
| ✅ | load_sheet resiliente com fallback para headers duplicados/vazios |
| ✅ | Segurança: client_id sempre da sessão, guards em security.py |

---

## 3. Arquivos Principais Alterados (histórico recente)

| Arquivo | O que foi alterado |
|---------|-------------------|
| `ui.py` | topnav cliente (logo, nome empresa nowrap), topnav supervisão (pill bar iframe + MutationObserver), remoção label "Empresa", CSS global |
| `app.py` | import version, remove_bottom_nav no logout, limpeza session state logo, botões ocultos `▸sv_*` para pill nav |
| `pwa.py` | remove_bottom_nav(), fix active state bottom nav, banner de atualização (polling version.txt) |
| `sheets.py` | load_sheet resiliente, funções: get_client_logo, save_client_logo, update_usuario, update_ativo, _ensure_logos_tab |
| `page_sv_clientes.py` | upload de logo, edição de cliente (_render_edit_cliente), aba "Editar dados" |
| `page_sv_ativos.py` | edição de ativo (_render_edit_ativo), expander "Editar dados do ativo" |
| `page_ativos.py` | removido mock fallback _MOCK, estado vazio com st.info() |
| `version.py` | **NOVO** — grava Unix timestamp em static/version.txt a cada inicialização do servidor |

---

## 4. Estrutura Atual do Projeto

```
portal-predio/
├── app.py                    # Entry point, roteador, botões ocultos nav
├── auth.py                   # Login, logout, current_client_id() da sessão
├── security.py               # Guards, auditoria, sanitize_portal_page()
├── sheets.py                 # ÚNICO acesso ao Google Sheets (~3200 linhas)
├── ui.py                     # Paleta, CSS global, topnavs, sidebar supervisão
├── pwa.py                    # PWA, bottom nav mobile, banner atualização
├── version.py                # Grava static/version.txt no startup do servidor
├── notifications.py          # Motor notificações portal (12 eventos)
├── assistant_engine.py       # Motor assistente preditivo IA
├── assistant.py              # Interface assistente
├── homologacao_setup.py      # Setup idempotente cliente teste
│
├── page_login.py
├── page_dashboard.py         # Cliente — Dashboard
├── page_farois.py            # Cliente — Faróis de Confiabilidade
├── page_ativos.py            # Cliente — Meus Equipamentos
├── page_manutencao.py        # Cliente — Manutenção
├── page_relatorios.py        # Cliente — Relatórios
├── page_chamados.py          # Cliente — Chamados v2
├── page_alertas.py           # Cliente — Alertas
├── page_biblioteca.py        # Cliente — Biblioteca
├── page_assistente.py        # Cliente — Assistente IA
├── page_preferencias_notificacao.py
├── page_notificacoes_portal.py
│
├── page_sv_dashboard.py      # Supervisão — Dashboard
├── page_sv_chamados.py       # Supervisão — Chamados
├── page_sv_chamado_detalhe.py
├── page_sv_clientes.py       # Supervisão — Clientes + logo + edição
├── page_sv_ativos.py         # Supervisão — Ativos + edição
├── page_sv_manutencao.py
├── page_sv_alertas.py
├── page_sv_notificacoes.py
├── page_sv_relatorios.py
├── page_sv_biblioteca.py
├── page_sv_assistente.py
├── page_sv_homologacao.py    # Supervisão — Homologação
│
├── static/
│   ├── manifest.json         # PWA manifest (name: Pred.IO, standalone)
│   ├── sw.js                 # Service Worker (só cacheia assets estáticos)
│   ├── version.txt           # Timestamp de deploy (gerado por version.py)
│   └── icons/                # icon-192.png, icon-512.png, icon-180.png
│
├── requirements.txt          # streamlit>=1.35, gspread>=6.1, pandas, plotly, Pillow
├── .streamlit/config.toml    # enableStaticServing = true
└── RESUMO_ATUAL_PROJETO.md   # Este arquivo
```

### Google Sheets — Abas Ativas
| Aba | Uso |
|-----|-----|
| `Usuarios` / `Clientes` | Cadastro e dados do cliente |
| `Ativos` | Equipamentos por client_id |
| `Chamados_v2` | Chamados técnicos (versão atual) |
| `Mensagens` | Mensagens dos chamados |
| `Relatorios` | Relatórios (flag: publicado/rascunho) |
| `Alertas` | Alertas preditivos |
| `DocumentosTecnicos` / `Chunks` | Biblioteca RAG do assistente |
| `AssistantLogs` / `AssistantFAQ` | Logs e FAQ da IA |
| `Sessions` | Tokens de sessão persistentes |
| `ClienteLogos` | Logo dos clientes em Base64 |
| `Horimetros` | Leituras de horímetro por ativo |
| `ManutencaoPlanos` / `ManutencaoTarefas` / `ManutencaoExecucoes` | Módulo manutenção |
| `Notificacoes` | Central de notificações |

---

## 5. Decisões Importantes Tomadas

### Segurança (NUNCA mudar sem análise)
- **`client_id` SEMPRE vem da sessão** — derivado em `auth.py` como `empresa.strip().lower()`. Jamais do front-end, URL ou formulário.
- Toda função de dados em `sheets.py` recebe `client_id` como parâmetro e filtra antes de retornar.
- **Empresa é read-only na edição de cliente** — se mudasse, o `client_id` mudaria e quebraria vínculos com ativos/chamados/relatórios em todas as abas.
- Rascunhos e observações internas NUNCA aparecem ao cliente.
- `ANTHROPIC_API_KEY` e credenciais Google NUNCA no front-end — apenas em variáveis de ambiente do Render.

### Navegação (arquitetura atual)
- **Portal cliente**: botões ocultos `▸{page}` no DOM (hidden via CSS `aria-label^="▸"`) clicados por JS do bottom nav e do assistente.
- **Supervisão topnav**: iframe pill bar (`components.html`) + botões ocultos `▸sv_{key}` escondidos via **JavaScript + MutationObserver** (CSS `aria-label^="▸"` não funcionou no contexto do supervisor).
- **Supervisão sidebar**: botões Streamlit nativos, funciona independentemente do topnav.

### Logo do Cliente
- Comprimida para 160×160px, JPEG 75% → ≤15KB → cabe na célula do Sheets (limite ~50K chars em Base64).
- Carregada uma vez por sessão em `st.session_state["client_logo_b64"]` para evitar chamadas repetidas ao Sheets.

### Atualização do App (sem Service Worker de código)
- `version.py` executa em nível de módulo → grava Unix timestamp em `static/version.txt` a cada restart do servidor.
- Render reinicia o processo Python a cada deploy → novo timestamp → browser detecta em ≤3 min → banner aparece.

### load_sheet resiliente
- `get_all_records()` lança exceção se o Sheets tiver headers duplicados ou vazios.
- Fallback: `get_all_values()` → filtra colunas com header válido → reconstrói DataFrame manualmente.

### Produto (regras de negócio)
- Não recomendar overhaul/troca de rolamento automaticamente por horímetro.
- Fonte exibida ao cliente: sempre "Pred.IO".
- Nunca "Mypro Touch+" — apenas "Mypro Touch" e "Mypro Touch AD".
- MYCOLD AB 68 descontinuado → referência atual: MYCOLD PAO.

---

## 6. Pendências Conhecidas

| Prioridade | Item | Detalhe |
|------------|------|---------|
| **Alta** | Confirmar fix botões duplicados supervisor | Commit `a9e7f99` usa MutationObserver para esconder `▸sv_*`. Verificar no Render se ainda aparecem. |
| **Média** | Pill nav ativo vs sidebar | Se usuário navega pela sidebar, o iframe pill atualiza no próximo rerun (comportamento normal, mas pode parecer lag). |
| **Média** | Testar edição em produção | `update_usuario()` e `update_ativo()` implementados mas não testados com dados reais RJR no Render. |
| **Média** | Logo RJR ainda não enviada | Campo de upload criado na supervisão, mas o logo do cliente RJR nunca foi de fato carregado. |
| **Baixa** | Assistente sem dados reais | Chunks para RAG dependem de upload de PDFs via Biblioteca. Nenhum documento indexado ainda. |
| **Baixa** | TTL cache pós-edição | Dados editados via `update_*` só aparecem após 30s (TTL do `load_sheet`) ou rerun manual. |

---

## 7. Próximas Etapas Recomendadas

1. **Verificar botões duplicados no supervisor** — logar como staff no Render e confirmar se `▸sv_dashboard` etc. ainda aparecem. Se sim, abordar com abordagem alternativa (URL query param).
2. **Fazer upload do logo do cliente RJR** — supervisão → Clientes → RJR → aba "🖼️ Logo do cliente no portal".
3. **Testar edição de cliente/ativo** — alterar telefone ou email de RJR e verificar no Sheets se gravou.
4. **Indexar documentos técnicos** — subir PDFs de manuais/laudos na Biblioteca para alimentar o assistente com dados reais.
5. **Validar banner de atualização** — abrir o app no celular, fazer um deploy, aguardar ~3 min e confirmar que o banner aparece.
6. **Adicionar novo cliente real** — usar formulário de "Adicionar Cliente" na supervisão com logo real.
7. **Avaliar migração de Sheets para banco real** — se houver ≥5 clientes simultâneos, o rate-limit do Sheets (10 req/s) pode causar lentidão.

---

## 8. Bugs e Riscos Conhecidos

### Bugs Ativos
| Bug | Status | Workaround |
|-----|--------|------------|
| Botões `▸sv_*` visíveis no supervisor | Em investigação (commit `a9e7f99`) | MutationObserver no iframe os esconde por JS |
| Pill nav não marca ativo se navegado via sidebar antes do rerun | Cosmético | Funciona corretamente após qualquer interação |

### Riscos Técnicos
- ⚠️ **Rate-limit Google Sheets** — máximo 10 req/s. Com TTL=30s o cache protege, mas picos podem causar erros 429.
- ⚠️ **`sheets.py` com ~3200 linhas** — manutenção difícil. Qualquer erro aqui derruba todas as funcionalidades de dados.
- ⚠️ **`SV_NAV_ITEMS` em dois lugares** — `ui.py` define a lista; `app.py` define o roteador `sv_view`. Adicionar item de menu exige atualização nos dois.
- ⚠️ **iframe do pill nav recria a cada rerun** — estado JS não persiste entre reruns (comportamento esperado do Streamlit).
- ⚠️ **`window.parent` no iframe** — depende de mesma origem (mesma URL do Render). Não funciona em cross-origin.
- ⚠️ **`load_sheet` TTL=30s** — edições feitas via `update_*` só são refletidas após 30 segundos no máximo.

### Riscos de Segurança
- ⚠️ Qualquer nova página do cliente DEVE ser adicionada em `VALID_CLIENT_PAGES` em `security.py`.
- ⚠️ Qualquer nova função de dados em `sheets.py` DEVE filtrar por `client_id` antes de retornar.
- ⚠️ Mudar o nome da empresa de um cliente no Sheets diretamente quebra o `client_id` em todas as abas — precisa atualizar manualmente em Ativos, Chamados, Relatorios, Alertas, etc.

---

## 9. Comandos Importantes

```bash
# Rodar localmente
streamlit run app.py

# Ver commits recentes
git log --oneline -20

# Commitar (padrão do projeto)
git add arquivo.py
git commit -m "tipo: descrição em português"
git push origin main
# → Deploy automático no Render após o push

# Ver o que mudou no último commit
git diff HEAD~1..HEAD

# Ver quais arquivos foram alterados
git diff HEAD~1..HEAD --stat

# Deploy no Render é automático via GitHub
# Não há comando manual de deploy — só git push origin main

# Para verificar version.txt (timestamp do último deploy)
# Acessar: https://<url-do-render>/app/static/version.txt
```

---

## 10. Instruções para Continuar o Projeto Após Limpar o Contexto

### Leitura obrigatória antes de qualquer mudança
1. Leia este arquivo (`RESUMO_ATUAL_PROJETO.md`) completo.
2. Leia `app.py` — entender o roteador é a base de tudo.
3. Leia `security.py` — as regras de guarda nunca devem ser contornadas.
4. Leia o início de `sheets.py` (funções `get_spreadsheet`, `load_sheet`, `_build_creds`).

### Regras que NUNCA mudam
- `client_id` vem **sempre** de `st.session_state["client_id"]`, derivado em `auth.py`.
- Não criar sidebar no portal do cliente.
- Não enviar WhatsApp, e-mail ou comando remoto.
- Não alterar o sistema de login sem necessidade explícita.
- Não transformar score/horímetro em decisão automática de parada/overhaul.
- Rascunhos nunca aparecem para o cliente.
- `ANTHROPIC_API_KEY` nunca no front-end.

### Como adicionar uma nova página ao portal do cliente
1. Criar `page_nova.py` com função `render()`.
2. Adicionar rota em `app.py` no bloco `if portal_page == "nova": ...`.
3. Adicionar `"nova"` na lista `VALID_CLIENT_PAGES` em `security.py`.
4. Adicionar botão de nav oculto `▸nova` no loop em `app.py`.
5. Adicionar item no bottom nav em `pwa.py` (`_ITEMS` ou drawer).
6. Adicionar item em `PORTAL_NAV_ITEMS` em `ui.py` se quiser no topnav.

### Como adicionar uma nova página à supervisão
1. Criar `page_sv_nova.py` com função `render()`.
2. Adicionar rota em `_render_supervisao()` em `app.py`.
3. Adicionar item em `SV_NAV_ITEMS` em `ui.py`.
4. Adicionar botão oculto `▸sv_nova` no loop de botões ocultos em `_render_supervisao()` em `app.py`.

### Como adicionar uma nova função de dados
1. Adicionar em `sheets.py` (sempre ao final da seção adequada).
2. Se lê dados de cliente: **sempre** receber `client_id` como parâmetro e filtrar com `df[df["ClientId"] == client_id]`.
3. Se é dado sensível: usar `@st.cache_data(ttl=30)` no load e invalidar via `st.cache_data.clear()` após escrita.

### Stack e dependências
```
Python + Streamlit ≥ 1.35
Google Sheets via gspread ≥ 6.1 (auth via google-auth, não oauth2client)
Pandas ≥ 2.0
Plotly ≥ 5.17
Pillow ≥ 10.0 (para logos e ícones PWA)
Deploy: Render (web service, Python 3.11+)
Repositório: GitHub → push em main = deploy automático
```

### Variáveis de ambiente necessárias no Render
- `ANTHROPIC_API_KEY` — chave da API Claude para o assistente
- `GOOGLE_CREDENTIALS` ou equivalente — credenciais da service account do Google Sheets

### Contexto de negócio
- Produto SaaS de confiabilidade preditiva industrial (Pred.IO)
- Clientes são indústrias com equipamentos rotativos (motores, bombas, compressores)
- Supervisores são engenheiros da Pred.IO que gerenciam os clientes
- Dados são sensíveis (laudos técnicos, ativos industriais, decisões de manutenção)
- Cliente atual em produção: **RJR**
- Cliente de homologação/teste: **pred.io teste**
