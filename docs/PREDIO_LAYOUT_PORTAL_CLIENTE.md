# Layout do Portal do Cliente — Etapa 3

> Data: 2026-08-07 | Escopo: Portal do Cliente (`/portal/*`) | Sem sidebar, sem GUT, sem alteração de regra de negócio

Esta etapa partiu de uma auditoria do estado atual do Portal do Cliente antes de mexer em qualquer coisa: boa parte do que a Etapa 3 pedia **já estava implementado** (navegação sem sidebar, header fixo, dashboard executivo, filtros de manutenção, campos de relatório). O trabalho real desta etapa foi: completar o que faltava no Dashboard e no Detalhe do Ativo, corrigir a ordem do menu, e documentar o que já existia — sem reescrever telas que já funcionavam bem.

## 1. Navegação

Sem sidebar (confirmado — `render_client_topnav` já esconde a sidebar nativa do Streamlit no portal do cliente).

- **Desktop**: menu superior horizontal (`render_client_topnav` em `ui.py`), com logo, nome do cliente e itens de navegação.
- **Mobile**: menu inferior fixo com 4 itens mais usados (Home, Ativos, Manutenção, Chamados) + botão "Mais" com os demais (Avisos, Alertas, Relatórios, Biblioteca, Config.) — `inject_bottom_nav()` em `pwa.py`. Esse recorte de 4+Mais é intencional (prioriza por frequência de uso) e continua diferente da ordem do menu desktop — não é inconsistência, é adaptação ao espaço da tela.
- **Assistente Técnico**: continua botão flutuante (`inject_floating_assistant`), sem alteração.

**Alteração feita**: a ordem de `PORTAL_NAV_ITEMS` (`ui.py`) foi ajustada para bater com o menu pedido — Dashboard, Ativos, Manutenção, Relatórios, Chamados, Alertas, Biblioteca, Notificações (antes a Biblioteca vinha antes de Chamados, e Notificações antes de Alertas). Assistente e Config. continuam no fim da lista (funcionalidades extras já existentes, não fazem parte do menu pedido mas não foram removidas).

## 2. Layout base

Já existia e foi mantido sem alteração: header fixo com logo + nome do cliente + menu (`render_client_topnav`), `page_header()` padronizado para título/subtítulo/divisor em toda página, largura `layout="wide"`. Nenhuma tela usa mais nem menos espaço que as outras — a auditoria confirmou que todas as 8 páginas do cliente já usam `page_header()` do Design System (Etapa 2).

## 3. Dashboard (`page_dashboard.py`)

**Antes**: 6 cards no topo (Ativos Monitorados, Saúde Média, Ativos em Atenção, Ativos Críticos, Manutenções Vencidas, Chamados Abertos), em grid 3×2.

**Depois**: 8 cards, grid 4×2, na ordem pedida — os 6 anteriores + **Relatórios Recentes** e **Alertas Críticos**, novos. Nenhuma consulta nova ao Sheets foi necessária — os dois cards novos reaproveitam dados que a página já carregava (`d["relatorios"]`, `d["alertas"]`); só foi adicionada uma contagem de alertas com prioridade Urgente/Crítica (`d["alertas_criticos"]`) antes da lista ser truncada em 5 itens.

O restante do dashboard (banner de notificações não lidas, seção Alertas/Manutenções/Chamados, Últimos Relatórios, Recomendações por Condição, Ações Prioritárias, rodapé com disclaimer) já estava bem organizado e não foi alterado.

## 4. Ativos — lista (`page_ativos.py`)

Já mostrava: nome, tipo, status (badge colorido), score de saúde (com barra), planta, última atualização, componentes monitorados, botão "Ver detalhes →".

**Alteração feita**: o botão "Ver detalhes →" ocupava só ~23% da largura do card (`st.columns([1.2, 4])`) — pequeno demais como ação principal e como alvo de toque no celular. Agora ocupa a largura total do card e usa `type="primary"` para ficar visualmente claro como a ação principal do card.

**Não implementado — motivo técnico, não é falta de tempo**: "próxima manutenção" e "último relatório" por ativo (pedidos no item 5) não foram adicionados à lista porque o `id` que este arquivo usa para cada ativo (`_norm(tag)`, derivado do nome) **não é o mesmo `Id` real gerado pela planilha** (`AT-2026-XXX`) usado como chave estrangeira em `Chamados`/`ManutencaoTarefas`/`TechnicalReports`. Cruzar por esse id incorretamente arriscaria mostrar "nenhuma manutenção" para todo ativo mesmo quando existe uma real — um bug pior que a ausência do campo. Corrigir isso é uma mudança de modelo de dados (não visual) e deveria ser feito com quem mantém `sheets.py`.

## 5. Detalhe do ativo (`page_ativos.py`)

Já existia: banner com identificação, métricas rápidas (Status/Score/Criticidade), dados técnicos, evolução do score (gráfico), componentes, plano de manutenção (real, via `get_maintenance_tasks(ativo_id=...)`), análise de óleo, histórico técnico (real, via `get_report_timeline_events`), recomendação técnica.

**Adicionado nesta etapa** (seções que faltavam do pedido original):
- **"Relacionados a este ativo"** — 3 colunas: Últimos Relatórios, Alertas e Chamados vinculados a este ativo específico (filtrando por `Ativo_Id` em cima de uma única consulta cada, sem custo extra de rate-limit).
- **"Ações Rápidas"** — 4 botões ao final da página: Ver relatórios, Abrir chamado, Ver manutenção, Perguntar ao Assistente.

Essas duas seções usam o `id` real recebido em `a.get("id","")` do jeito que o restante do arquivo já fazia para plano de manutenção/histórico — ou seja, herdam o mesmo comportamento (podem retornar vazio se o `id` não bater, mas nunca mostram dado errado, já que o filtro é sempre "== id", nunca aproximado).

## 6. Manutenção, Relatórios, Chamados, Biblioteca

Auditados contra os campos pedidos nos itens 7–10 — **nenhuma mudança necessária**, já atendiam:

- **Manutenção**: já organizada com 4 métricas (Em dia/Próximas/Vencidas/Por condição), alerta de urgência, filtros (tipo/status/prioridade) e lista ordenada por urgência, com seção separada para tarefas "Por condição".
- **Relatórios**: já mostra título, tipo, severidade, ativo, data, badge "Publicado", botão baixar — e nunca mostra rascunho/em revisão (filtro por `Status=="Publicado"` em `security.py`/`sheets.py`, intocado).
- **Chamados**: já mostra status/prioridade coloridos, histórico de mensagens, formulário de resposta — mensagens internas (`Visivel_Cliente=false`) já são filtradas antes de chegar à página.
- **Biblioteca**: já mostra título, tipo, e um badge claro de "Disponível para consulta IA" vs "Disponível apenas para download".

## 7. Mobile

CSS responsivo global (`pwa.py`) já cobre: toque mínimo 44px, `st.columns` colapsando para 2→1 coluna, tabs/topnav com scroll horizontal, bottom nav fixo. Verificado que nenhuma mudança desta etapa quebra esse comportamento — as novas seções (Relacionados/Ações Rápidas no detalhe do ativo, 8º/7º card do dashboard) são `st.columns()` simples, então herdam o mesmo colapso responsivo automaticamente.

## 8. Pontos preparados para GUT (não implementados)

Conforme pedido, nenhum campo de GUT foi criado. O layout já comporta a adição futura sem redesenho:
- Card de ativo (lista): há espaço abaixo do score para uma futura linha de "Prioridade" sem quebrar o layout atual.
- Detalhe do ativo: a seção de métricas rápidas (Status/Score/Criticidade) é uma grade de `st.columns(3)` — pode virar `st.columns(4)` para incluir "Prioridade GUT" sem redesenho.
- Manutenção: os filtros já são um padrão extensível (`st.selectbox` em `st.columns`) — Gravidade/Urgência/Tendência podem entrar como filtros adicionais no mesmo `st.expander("🔍 Filtros")`.

## 9. Segurança — confirmação

Nenhuma regra tocada. Confirmado nesta etapa:
- `client_id` continua vindo exclusivamente de `current_client_id()` (sessão) em todos os pontos novos — nunca de parâmetro de URL ou input do usuário.
- Os relatórios/alertas/chamados novos no Detalhe do Ativo usam as mesmas funções já filtradas por `client_id` (`get_technical_reports(..., staff=False)`, `get_alertas_sv(client_id)`, `get_chamados_v2(client_id=...)`) — nenhuma nova consulta sem filtro de cliente.
- Nenhuma tela nova expõe `observacoes_internas`, rascunho, `Visivel_Cliente=false` ou chunks brutos.

## 10. Checks técnicos

Sem lint/typecheck/build configurados no projeto (mesma situação das etapas anteriores). `py -m py_compile` nos 44 arquivos — sem erros. `import` direto de `ui`, `page_dashboard` e `page_ativos` (os três módulos alterados) — sem erro de nome/import.

## 11. Confirmações pedidas

- Não foi criada sidebar.
- Sistema GUT não foi implementado (apenas layout deixado extensível).
- WhatsApp e e-mail não foram tocados.
- Login e permissões não foram alterados.
- `client_id` continua vindo exclusivamente da sessão em todo o código novo.

## 12. Arquivos alterados

`ui.py` (ordem do menu), `page_dashboard.py` (8 cards), `page_ativos.py` (seções novas no detalhe + botão "Ver detalhes" full-width).

## 13. Próxima etapa recomendada

Resolver a divergência de `id` entre `page_ativos.py` (derivado do Tag) e o `Id` real gerado pela planilha (`AT-2026-XXX`) — é o bloqueio técnico para "próxima manutenção"/"último relatório" por ativo na lista, e vale mais que qualquer novo ajuste visual.
