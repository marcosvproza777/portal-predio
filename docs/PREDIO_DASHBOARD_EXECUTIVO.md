# Dashboard Executivo — Etapa 4

> Data: 2026-08-07 | Escopo: `page_dashboard.py` (`/portal/dashboard`) | Sem sidebar, sem GUT, sem alteração de regra de negócio

O dashboard já estava bem avançado antes desta etapa (construído nas Etapas 1–3). O trabalho aqui foi: completar os 8 cards pedidos, criar a seção "Saúde dos Ativos" que faltava, adicionar gráficos simples em CSS (sem instalar nada novo), reordenar as seções na sequência pedida, e padronizar as mensagens de estado vazio.

## 1. Cards superiores (Visão Geral)

8 cards, grid 4×2, nesta ordem exata: **Ativos Monitorados, Saúde Média, Ativos em Atenção, Ativos Críticos, Manutenções Vencidas, Chamados Abertos, Alertas Críticos, Relatórios no Mês**.

Cada card já segue o padrão pedido: ícone + título curto, número em destaque, cor de status (verde/âmbar/vermelho conforme severidade), descrição curta, botão "Ver →" que navega para a tela correspondente.

**Novo nesta etapa**: o card de relatórios agora conta especificamente os publicados **no mês corrente** (`d["relatorios_mes"]`, calculado comparando `MM/AAAA` da data do relatório com o mês atual) — antes contava os "últimos 5" independente do mês. E o card de Alertas Críticos usa uma contagem real de prioridade Urgente/Crítica (`d["alertas_criticos"]`) calculada antes da lista de alertas ser truncada em 5 itens, para não subcontar clientes com muitos alertas.

Nenhum card novo exigiu consulta nova ao Google Sheets — as duas contagens novas reaproveitam dados que a página já carregava.

## 2. Seções do dashboard (ordem final)

1. **Visão Geral** — os 8 cards.
2. **Saúde dos Ativos** *(nova)* — score médio em destaque + barra de "Ativos por status" (Bom/Atenção/Crítico/Urgente).
3. **Manutenções Prioritárias** — vencidas/próximas/por condição/em dia, com barra de status e lista das mais urgentes.
4. **Alertas Recentes** — lista por prioridade.
5. **Chamados em Aberto** — resumo por status, com barra de status e lista.
6. **Relatórios Recentes** — últimos publicados, com severidade e botão de download/visualização.
7. **Ações Recomendadas** — lista dinâmica de ações prioritárias, ao lado de "Recomendações por Condição" (conteúdo extra já existente, mantido).

As seções 3, 4 e 5 continuam lado a lado em 3 colunas (não empilhadas) — é uma escolha deliberada de manter a visão executiva compacta e "de relance" no desktop; no mobile o CSS responsivo já existente colapsa essas 3 colunas automaticamente.

## 3. Gráficos simples

O projeto já tem `plotly` instalado (usado em `page_farois.py`), mas **não foi usado aqui** — os gráficos pedidos são simples o bastante para barras em CSS puro, o que carrega mais rápido no dashboard (item 9 do pedido: "dashboard deve carregar rápido") e evita o overhead de renderizar múltiplos componentes Plotly numa mesma tela.

Novo helper `_mini_bar_html()` (barra horizontal segmentada + legenda, só CSS) usado em 3 lugares:
- **Ativos por status** (seção Saúde dos Ativos) — Bom/Atenção/Crítico/Urgente.
- **Manutenções por status** (seção Manutenções Prioritárias) — Vencidas/Próximas/Por condição/Em dia.
- **Chamados por status** (seção Chamados em Aberto) — Em análise/Aguardando/Outros abertos/Concluídos no mês.

**Não implementado, com motivo:**
- **Alertas por prioridade** — a lista de alertas já mostra no máximo 5 itens, cada um com uma cor de prioridade; um gráfico de barras sobre 5 itens no máximo teria pouco valor visual sobre a lista já colorida.
- **Evolução da saúde média** (série temporal) — não existe hoje nenhum histórico de score médio salvo por cliente/data no Sheets (o `historico_score` por ativo só existe nos dados de demonstração/mock, não nos ativos reais). Criar essa série exigiria uma tabela nova de snapshots — é mudança de modelo de dados, fora do escopo desta etapa.

## 4. Como os dados são filtrados por cliente_id

Sem alteração de regra — `render()` continua chamando `current_client_id()` (nunca aceita `client_id` de parâmetro de URL ou input) e passa esse valor para `_load_data(client_id)`, que por sua vez chama todas as funções de `sheets.py` (`get_ativos`, `get_maintenance_tasks`, `get_technical_reports`, `get_alertas_sv`, `get_chamados_resumo_assistente`) sempre com esse `client_id`. As duas novas contagens (`relatorios_mes`, `alertas_criticos`) são computadas em cima dos mesmos DataFrames já filtrados — nenhum dado de outro cliente é lido em nenhum momento.

## 5. Estados vazios

Textos padronizados para bater exatamente com o pedido:

| Situação | Mensagem |
|---|---|
| Sem ativos | "Nenhum ativo cadastrado ainda." — dashboard inteiro mostra esse estado e não renderiza os cards/seções (não faz sentido mostrar 8 cards zerados) |
| Sem relatórios | "Nenhum relatório publicado até o momento." (agora via `ui.empty_state()`, antes era `st.info()` com texto diferente) |
| Sem chamados | "Nenhum chamado aberto." (antes: "Nenhum chamado em aberto.") |
| Sem alertas | "Nenhum alerta crítico no momento." (antes: "Nenhum alerta ativo.") |
| Sem manutenções vencidas | "Nenhuma manutenção vencida." (antes: "Nenhuma manutenção urgente no momento.") |

## 6. Mobile

Nenhuma mudança específica de CSS foi necessária — a seção nova (Saúde dos Ativos) e as barras novas (`_mini_bar_html`) são `st.columns()`/`st.markdown()` simples, herdando o mesmo colapso responsivo (2→1 coluna) e touch-target mínimo de 44px já configurados globalmente em `pwa.py`. As barras CSS não têm nenhuma dependência de JS ou canvas, então não têm risco de "quebrar" no celular como um gráfico interativo poderia ter.

## 7. Pontos preparados para GUT

Nenhum campo de GUT foi criado. Espaço já reservado, sem redesenho necessário:
- A barra "Manutenções por status" aceita mais um segmento (ex: "Prioridade GUT") sem mudar de layout — é só adicionar um item à lista de segmentos.
- O card "Saúde dos Ativos" tem uma coluna lateral (`col_score`) livre para uma futura métrica de risco consolidado.
- "Ações Recomendadas" já é uma lista ordenada por urgência — priorização por GUT entraria como um critério de ordenação novo na mesma função (`_load_data`, bloco "Ações Prioritárias"), sem mudar a renderização.

## 8. Checks técnicos

Sem lint/typecheck/build configurados no projeto. `py -m py_compile` nos 44 arquivos — sem erros. `import page_dashboard` — sem erro de nome/import. Testado isoladamente (fora do Streamlit, já que os cálculos não dependem de `st`): `_mini_bar_html()` com segmentos zerados/não-zerados, e a lógica de recorte de data usada em `relatorios_mes` — ambos corretos.

## 9. Confirmações pedidas

- Não foi criada sidebar.
- Sistema GUT não foi implementado.
- WhatsApp e e-mail não foram tocados.
- `client_id` continua vindo exclusivamente da sessão em todo o código novo — nenhuma consulta nova sem esse filtro.

## 10. Arquivos alterados

Só `page_dashboard.py`.

## 11. Próxima etapa recomendada

Se "Evolução da saúde média" for um gráfico realmente desejado, é preciso primeiro decidir onde/como armazenar snapshots periódicos do score médio por cliente (ex: uma aba `ScoreHistorico` no Sheets, gravada uma vez por dia) — sem isso não há dado histórico real para mostrar.
