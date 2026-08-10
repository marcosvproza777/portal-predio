# Timeline do Ativo, Comparativo "O que mudou?" e Reuniões — Pred.IO

Data: 2026-08-09
Status: Implementado. Nenhuma migração destrutiva (todas as colunas/abas novas são aditivas).

---

## 0. O que já existia vs. o que foi construído nesta etapa

Boa parte da timeline já existia e funcionava no Portal do Cliente antes desta etapa começar — construída na integração com o App Relatórios. Confirmei isso lendo o código antes de escrever qualquer linha nova. O que era novo de fato:

1. **Timeline real na Supervisão** — `page_sv_ativos.py` só mostrava a timeline com dados de demonstração (`if usando_mock:`); ativos reais não mostravam nada. Ligado ao mesmo dado real que o Portal do Cliente já usa.
2. **Novos tipos de evento** — `alerta_gerado`, `alerta_resolvido`, `status_alterado` (faixa de score) e `recomendacao_tecnica` (manutenção por Condição) passaram a ser escritos automaticamente. `_HT_TIPO_CFG` (`page_ativos.py`) já tinha entradas prontas pra alguns desses tipos, mas nada os escrevia.
3. **Filtro por período na timeline** — só existia filtro por categoria.
4. **Status de resolução em Alertas** — antes só existia criar + apagar. Novo botão "✅ Resolver" (soft, não apaga).
5. **Snapshot de GUT/score do cliente** (`ClientSnapshots`) — GUT e score de saúde nunca tiveram histórico persistido (sempre recalculados na leitura). Sem isso, não tem como comparar "antes × depois" desses dois indicadores.
6. **Reuniões com o cliente** (`ClientMeetings`) — não existia.
7. **Motor de comparativo** (`comparativo.py`) — não existia.
8. **Visão Executiva do Cliente / Top Prioridades / Ativos que Merecem Atenção / Atividade Recente** — não existiam em `/supervisao/clientes/[id]` (só tinha 4 cartões simples de chamados/relatórios).
9. **Botão "Preparar Reunião"** — estende o modal de Resumo Executivo já existente (`resumo_executivo_ui.py`), não duplica.
10. **4 novos gatilhos no Assistente Técnico** (`assistant_engine.py`).

Tudo o mais (coleta de dados por cliente/período/ativo, isolamento por `client_id`, regra "só Publicado alimenta IA/Resumo", gráficos, pontos para gerência) já existia em `executive_summary.py` e foi **reaproveitado**, não duplicado.

---

## 1. Timeline do ativo

**Onde**: `/portal/ativos/[id]` (já existia) e `/supervisao/ativos/[id]` (novo — antes só mock).

**Fonte de dados**: aba `ReportTimeline` (`sheets.py`), lida via `get_report_timeline_events(ativo_id, cliente_id, staff, limit)`. Renderizada por `_render_historico_tecnico()`/`_render_ht_card()` em `page_ativos.py` — componente único, reaproveitado tanto no Portal do Cliente quanto na Supervisão (via um adaptador que converte o DataFrame em lista de dicts).

**Quem escreve eventos hoje**:

| Tipo | Escrito por | Desde quando |
|---|---|---|
| `relatorio_publicado` / `analise_oleo` / `analise_vibracao` / `termografia` | `publish_technical_report()` | já existia |
| `manutencao_concluida` | `complete_maintenance_task()` | já existia |
| `chamado_aberto` / `chamado_respondido` / `chamado_concluido` | `abrir_chamado_v2()` / `responder_chamado()` / `concluir_chamado()` | já existia |
| `alerta_gerado` | `add_alerta_sv()` | novo |
| `alerta_resolvido` | `resolver_alerta_sv()` | novo |
| `status_alterado` | `_update_ativo_score()`, quando a FAIXA do score muda (Bom/Atenção/Crítico/Urgente) | novo |
| `recomendacao_tecnica` | `add_maintenance_task()`, quando `Tipo_Manutencao == "Condição"` | novo |
| `gut_alterado` | `snapshot_cliente()`, quando o item de maior GUT muda entre um snapshot e o anterior | novo |

**Idempotência**: não há um `report_id` único gerado por tentativa de escrita — o guard real é estrutural: `publish_technical_report()` já se recusa a publicar um relatório duas vezes (`Status` já é `"Publicado"` → recusa), então o evento de publicação nunca duplica por esse caminho. Para os tipos novos, cada um só é escrito num ÚNICO ponto de mudança de estado real (criação do alerta, resolução do alerta, mudança de faixa de score, criação de tarefa por condição) — não há reprocessamento em loop que pudesse duplicar.

**Filtros**: categoria (Todos/Relatórios/Chamados/Manutenção/Alertas/Recomendações/GUT/Score de saúde) — os 2 últimos são novos. Período (Tudo/30 dias/90 dias/6 meses/1 ano/Personalizado) — novo; "Tudo" preserva o comportamento anterior à mudança (sem filtro nenhum).

**Visibilidade**: Portal do Cliente só vê eventos com `Visivel_Cliente != "false"` e nunca vê `Obs_Interna`; Supervisão vê tudo (`staff=True`).

---

## 2. Comparativo "O que mudou desde a última reunião?"

**Motor**: `comparativo.py` (novo módulo, sem Streamlit — funções puras). Reaproveita `executive_summary._coletar_dados()` chamada duas vezes (uma por período) em vez de duplicar a coleta.

**UI**: `comparativo_ui.py` — botão + modal (`render_comparativo_button`), em `/supervisao/clientes/[id]`, `/supervisao/dashboard` (Supervisão escolhe o cliente dentro do modal) e `/portal/dashboard` (cliente, rótulo "📊 Resumo do período", `client_id` sempre forçado da sessão).

**Como identifica melhora/piora**:

- **Score de saúde por ativo**: lido do evento `status_alterado` da timeline (que já registra "faixa antiga → faixa nova") dentro do período atual — se a faixa nova é melhor (Bom > Atenção > Crítico > Urgente), vai para "Melhorou"; se pior, para "Piorou".
- **Alertas**: `alerta_resolvido` no período → "Melhorou". `alerta_gerado` no período → "Piorou".
- **Relatórios críticos publicados no período** → "Piorou".
- **Manutenções**: usa `calc_task_status(task, as_of=data)` (novo parâmetro) comparando o status COMO ESTARIA no início do período atual vs como está no fim — se passou de "não vencida" para "Vencida" dentro do período, entra em "Piorou" como "manutenção venceu no período". Manutenções concluídas no período → "Melhorou".
- **GUT**: evento `gut_alterado` da timeline → "Novidades" (não há um "antes/depois" limpo o suficiente pra classificar como melhora/piora só com esse evento).
- **Pendências** (situação atual, não é sobre o período): manutenções vencidas agora, chamados abertos agora, itens GUT Alta/Crítica ainda sem resolução.
- **Pontos para gerência**: até 7, ordenados por impacto (piora crítica → GUT alto → manutenção vencida → alerta crítico → recomendação → melhoria).

**Definição do período**: `resolver_periodo_comparativo()` — se existir reunião registrada, período anterior = o que foi analisado NA reunião, período atual = do dia seguinte até hoje. Sem reunião, cai no padrão manual (30 dias vs os 30 dias anteriores) ou nos períodos escolhidos manualmente na UI.

**Gráficos** (nunca gera gráfico vazio): saúde antes×depois (só se houver snapshot anterior), ativos por status (atual), GUT Alta/Crítica antes×depois (só com snapshot), relatórios por severidade (do período atual). Reaproveita `_chart_saude_ativos`/`_chart_relatorios_severidade` já existentes em `resumo_executivo_ui.py`.

---

## 3. Reuniões (`ClientMeetings`)

Headers: `Id, Cliente_Id, Titulo, Data_Reuniao, Periodo_Inicio, Periodo_Fim, Observacao, Criado_Por, Created_At`.

Botão "📅 Registrar reunião" em `/supervisao/clientes/[id]` — título, data, período analisado, observação opcional. `Observacao` é sempre interna (mesmo padrão de `Obs_Interna` usado no resto do projeto) — nunca é lida por nenhuma tela do cliente.

Ao registrar, chama `snapshot_cliente(client_id)` — grava uma foto do GUT/score atuais, para que a PRÓXIMA comparação (a próxima reunião) tenha uma base real de "antes".

---

## 4. Snapshot GUT/Score (`ClientSnapshots`)

Headers: `Id, Cliente_Id, Data, Score_Medio, Gut_Top_Json, Ativos_Criticos, Ativos_Atencao, Created_At`.

**Por que existe**: `get_gut_summary()` já documentava que GUT "não é persistido — sempre recalculado na leitura", e o score de saúde só existe como valor atual em `Ativos.Score`, sem histórico. Sem guardar uma foto em algum momento, "GUT reduziu de 100 para 64" nunca teria como ser mostrado de verdade — seria inventado.

`snapshot_cliente()` é chamado ao registrar uma reunião, e pode ser chamado de novo a qualquer momento (idempotente — cada chamada só adiciona uma linha nova, nunca sobrescreve).

---

## 5. Visão Executiva do Cliente (`/supervisao/clientes/[id]`)

Bloco no topo (`_render_visao_executiva`): ativos monitorados, saúde média, ativos críticos/atenção, maior GUT, manutenções vencidas, alertas críticos, chamados abertos, relatórios publicados (30 dias).

Reaproveita as mesmas fontes de `executive_summary.py` (`get_all_ativos_sv`, `get_gut_summary`, `get_alertas_sv`, `get_chamados_v2`, `get_technical_reports`) — mas **não** reaproveita `compute_indicadores()` para "manutenções vencidas": aquela função conta pelo campo `Status` bruto salvo na tarefa (que não é recalculado com o tempo — uma tarefa criada como "Em dia" fica com esse texto pra sempre, mesmo vencida há semanas). Aqui, e no comparativo, "vencida" sempre vem de `calc_task_status()` dinâmico.

**Top Prioridades** (`_render_top_prioridades`): Top 5 de `get_gut_summary(client_id)` (já ordenado por score GUT), com botão "Ver →" pro ativo.

**Ativos que Merecem Atenção** (`_render_ativos_atencao`): no máximo 5, ordenados por Urgente → Crítico → maior GUT → pior score. Mostra ativo/score/status/maior GUT/último relatório.

**Atividade Recente** (`_render_atividade_recente`): timeline agregada do cliente (todos os ativos), limitada a 15 eventos via `get_report_timeline_events(..., limit=15)` — nunca carrega o histórico completo.

---

## 6. "Preparar Reunião"

`render_resumo_executivo_button(..., mostrar_comparativo=True)` — mesmo componente do "Gerar Resumo Executivo", com o bloco "O que mudou" (comparativo) injetado ANTES do preview já existente. Não é um sistema novo — é o resumo executivo de sempre mais o comparativo na frente.

---

## 7. Assistente Técnico

Novo intent `mudou_desde_reuniao` (`assistant_engine.py`) — cobre "o que mudou desde a última reunião", "quais ativos pioraram/melhoraram". Chama `comparativo.gerar_comparativo()` sempre com `modo="cliente"` (nunca observação interna) e `client_id` sempre vindo de `ctx["client_id"]` (montado por `get_client_context()`, nunca de input livre).

"Quais são as maiores prioridades do cliente?" já era coberto pelo intent `gut` existente — só adicionamos "maiores prioridades"/"principais prioridades" à lista de gatilhos dele. "O que preciso levar para reunião?" e "principais acontecimentos nos últimos 30 dias" já eram cobertos pelo intent `resumo_periodo` existente.

---

## 8. Portal do Cliente

Botão "📊 Resumo do período" em `/portal/dashboard` — mesmo modal do comparativo (`comparativo_ui.py`), com `client_id` sempre forçado por `current_client_id()` internamente (nunca aceita um `client_id` passado por quem chama, se a sessão não for de staff). Nunca mostra: observações internas, avaliação interna, comentários de reunião (`ClientMeetings.Observacao`), rascunhos, chunks, logs — todos filtrados pelo mesmo `modo="cliente"`/`staff=False` já usado em todo o projeto.

---

## 9. Segurança (checklist)

- `client_id` do Portal do Cliente sempre vem de `current_client_id()` — `render_comparativo_button()` e `render_resumo_executivo_button()` sobrescrevem qualquer valor passado por engano quando `is_staff()==False`.
- Admin só seleciona cliente dentro do modal, na Supervisão (`_dialog_comparativo`/`_dialog_resumo`), nunca por parâmetro de URL.
- Isolamento Cliente A / Cliente B: todas as fontes usadas por `comparativo.py` já filtram por `client_id`/`cliente_id` (mesmas funções de `sheets.py` usadas em todo o projeto).
- Relatórios só entram no comparativo/timeline se `Status == "Publicado"` (via `get_technical_reports(..., staff=False)` dentro de `_coletar_dados`).
- `ClientMeetings.Observacao` e `AlertasSV`/`ReportTimeline.Obs_Interna` nunca são lidos por nenhuma função em modo `"cliente"`.
- Nenhuma mudança em `auth.py`, sidebar, WhatsApp/e-mail, comando remoto ou permissões.

## 10. Limitações de dados aceitas (sem solução retroativa possível)

- **Manutenção por horímetro**: não existe log histórico de leitura — só o valor atual. `calc_task_status(..., as_of=data)` só afeta o cálculo por Calendário; por Horímetro continua sendo "vencida como está agora".
- **Recomendações** não são uma entidade própria com status (é texto livre em `Recomendacoes`/GUT). "Recomendação nova" no comparativo vem da contagem de eventos `recomendacao_tecnica` na timeline do período, não de uma entidade com ciclo de vida próprio.
- **GUT/score antes do primeiro snapshot**: sem uma reunião ou comparativo anterior já registrado, não há "antes" real — o comparativo mostra a situação atual como referência e nunca inventa um valor histórico.

## 11. Testes realizados

Sem suite automatizada no projeto — verificado com scripts pontuais contra a planilha real (dados 100% sintéticos, sempre limpos ao final) e `streamlit.testing.v1.AppTest` para os fluxos de UI:

- Timeline real na Supervisão (ativo real, sem mock) — sem exceção.
- Alerta criado → resolvido: 2 eventos na timeline, some da lista padrão, aparece com `incluir_resolvidos=True`.
- Snapshot: criação, leitura, comparação com o snapshot anterior.
- Reunião: criação, `get_last_meeting` retorna a mais recente.
- **Comparativo — cenário do pedido**: ativo Atenção/GUT 48/sem manutenção vencida → Crítico/GUT 100/1 manutenção vencida/1 relatório crítico novo → confirmado em "Piorou", nada em "Melhorou".
- Comparativo — classificação de melhora (Crítico → Atenção) confirmada isoladamente.
- `render_historico()` completo (Visão Executiva + Top Prioridades + Ativos Atenção + Atividade Recente + 4 botões) sem exceção — inclusive corrigiu um bug pré-existente (`get_historico_cliente` quebrava para qualquer cliente sem chamado real, depois que os dados de teste do mock foram removidos numa sessão anterior).
- Botão "Preparar Reunião": abre modal, gera preview (resumo + comparativo) sem exceção.
- Intent `mudou_desde_reuniao`: `detect_intent()` resolve corretamente para as 3 frases do pedido; resposta completa gerada sem exceção, com fallback correto quando não há reunião registrada.
