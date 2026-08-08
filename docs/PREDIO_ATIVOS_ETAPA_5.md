# Tela de Ativos — Etapa 5

> Data: 2026-08-07 | Escopo: `/portal/ativos`, `/portal/ativos/[id]` | Sem sidebar, sem GUT, sem alteração de regra de negócio

Etapas anteriores (3 e 4) já tinham deixado a tela de Ativos em bom estado (lista com score/status, detalhe com banner/métricas/plano de manutenção/histórico/ações rápidas). O trabalho real desta etapa foi resolver um bloqueio técnico que impedia cruzar dados corretamente, e então usar essa correção para finalmente entregar os campos que ficaram pendentes nas Etapas 3 e 4: próxima manutenção, último relatório, alertas e chamados por ativo — tanto na lista quanto no detalhe.

## 1. A correção de base: o `id` do ativo estava errado

`page_ativos._load()` gerava o `id` de cada ativo a partir do nome (`Tag` normalizada), **e não do `Id` real gerado pela planilha** (`AT-2026-XXX`) — o mesmo `Id` usado como chave estrangeira em `ManutencaoTarefas`, `TechnicalReports`, `Chamados` e `AlertasSV`. Isso foi identificado nas Etapas 3 e 4 como o motivo de não dar para mostrar "próxima manutenção"/"último relatório" por ativo com segurança.

Corrigido: `_load()` agora usa o `Id` real da planilha (com fallback para o id antigo só se a linha não tiver `Id`, o que não deveria acontecer). Isso não só destrava os campos novos desta etapa — também corrige, silenciosamente, consultas que **já existiam** no detalhe do ativo desde a Etapa 3 (plano de manutenção e histórico técnico) e que podem ter estado retornando vazio por causa do id errado.

## 2. Lista de ativos (`/portal/ativos`)

Cada card agora mostra, além do que já existia (nome, tipo, status, score com barra, planta, última atualização, componentes):

- **Próxima manutenção** — a tarefa mais urgente (Vencida tem prioridade sobre Próxima do vencimento), em vermelho se vencida.
- **Último relatório** — título do relatório publicado mais recente deste ativo.
- **Alertas ativos** — contagem, em vermelho se > 0.
- **Chamados abertos** — contagem, em âmbar se > 0.

**Como isso é buscado sem sobrecarregar o Google Sheets**: uma função nova, `_build_resumos(client_id)`, faz **4 consultas no total para a página inteira** (manutenção, relatórios, alertas, chamados do cliente — não uma consulta por ativo) e agrupa os resultados em memória por `Ativo_Id`. Um cliente com 30 ativos continua gerando as mesmas 4 consultas que um cliente com 2 — não 30× mais. Testado isoladamente com dados sintéticos (sem precisar de credenciais reais do Sheets) — agrupamento, contagem e escolha do "mais urgente"/"mais recente" conferidos.

### Filtros

Antes: status + planta. Agora:
- 🔎 **Busca por nome** (texto livre)
- **Status**: Bom, Atenção, Crítico, Urgente, Em acompanhamento (adicionado "Urgente", que faltava)
- **Tipo de ativo**
- **Planta**
- ☑️ **Com manutenção vencida**
- ☑️ **Com alerta ativo**
- ☑️ **Com chamado aberto**

Os três checkboxes usam os mesmos dados já buscados por `_build_resumos` — nenhuma consulta extra. Mantido simples de propósito (nada de filtro aninhado ou avançado, como pedido).

## 3. Detalhe do ativo (`/portal/ativos/[id]`)

Os 9 blocos pedidos, todos presentes:

1. **Cabeçalho** — banner com nome, tipo, modelo, NS, planta, inversor, última atualização.
2. **Score de saúde** — ver seção 4 abaixo.
3. **Status atual** — badge de status (Bom/Atenção/Crítico/Urgente/Em acompanhamento — "Urgente" era o único que faltava no dicionário de cores, adicionado nesta etapa).
4. **Próxima manutenção** — dentro do bloco "Plano de Manutenção" (já existia desde a Etapa 3), mais uma seção nova **"Concluídas Recentemente"** (até 3 execuções, via `get_maintenance_executions`, nunca mostra o campo interno `Obs_Interna`).
5. **Últimos relatórios** — agora com tipo, severidade (badge colorido), data, resumo curto e botão "Ver relatório" (antes só tinha o título).
6. **Alertas** — agora com data e "ação sugerida" (texto da recomendação do alerta).
7. **Chamados** — agora com a **última resposta** (autor + trecho da mensagem, via `get_mensagens_visiveis_cliente` — que já filtra `Visivel_Cliente` e nunca traz observação interna) e botão "Ver chamado →".
8. **Histórico técnico** — já existia (Etapa 3), sem alteração nesta etapa.
9. **Ações rápidas** — já existia (Etapa 3): Ver relatórios, Abrir chamado, Ver manutenção, Perguntar ao Assistente.

## 4. Score de saúde — padronização

Antes, `_score_color`/`_score_label` só tinham 3 faixas (85+/60+/resto) — sem a faixa "Urgente" que o resto do portal já usa. Corrigido para as 4 faixas exatas pedidas:

| Faixa | Score |
|---|---|
| Bom | 85–100 |
| Atenção | 60–84 |
| Crítico | 30–59 |
| Urgente | 0–29 |

Adicionado também o texto de disclaimer obrigatório logo abaixo do score no detalhe do ativo: *"O score de saúde é uma visão consolidada para priorização técnica e não substitui a avaliação da equipe Pred.IO."* (o mesmo texto já usado no Dashboard, agora também aqui).

## 5. Assistente Técnico com contexto do ativo

O botão "🤖 Perguntar ao Assistente" no detalhe do ativo agora grava `st.session_state["assistente_ativo_contexto"] = nome_do_ativo` antes de navegar. Na página do Assistente (`page_assistente.py`):

- Mostra um banner "🔎 Perguntando sobre: **{ativo}**" com botão para limpar o contexto.
- Troca a lista de sugestões padrão pelas 5 perguntas pedidas nesta etapa, com o nome do ativo já embutido no texto: *"Qual a saúde do ativo X?"*, *"Quais manutenções estão pendentes para o X?"*, *"Existem alertas críticos no X?"*, *"O que o último relatório do X recomenda?"*, *"Preciso abrir chamado para o X?"*

Como `query_ai(client_id, pergunta)` só recebe texto livre (não um parâmetro estruturado de ativo), o contexto é passado embutido na própria pergunta — é assim que o motor do assistente já busca contexto relevante nos dados do cliente. "Fonte: Pred.IO" já era exibido nas respostas (`Assistente Pred.IO` + "Fontes consultadas") — nada a mudar aí.

## 6. Segurança — confirmação

Nenhuma regra tocada. Os campos novos usam funções que já filtram por `client_id`/ownership:
- `get_maintenance_tasks(client_id=..., staff=False)`, `get_technical_reports(client_id=..., staff=False)` (só `Status=="Publicado"`), `get_alertas_sv(client_id)`, `get_chamados_v2(client_id=...)`, `get_maintenance_executions(client_id=..., ativo_id=...)`, `get_mensagens_visiveis_cliente(chamado_id, client_id=...)` (valida ownership do chamado antes de retornar).
- `Obs_Interna` (execuções de manutenção) explicitamente nunca lido nos campos exibidos.
- Nenhum rascunho, observação interna ou chunk bruto é exibido — os mesmos filtros de sempre (`security.py`, `sheets.py`) continuam intactos.

## 7. Mobile

Nenhum CSS novo necessário — filtros novos (`st.text_input` + `st.columns(3)` × 2) e o bloco de resumo do card são elementos simples que herdam o colapso responsivo já configurado globalmente (`pwa.py`). Checkboxes nativos do Streamlit já têm alvo de toque adequado.

## 8. Supervisão (`/supervisao/ativos`, `/supervisao/ativos/[id]`)

Revisado — não identifiquei problema equivalente ao da lista/detalhe do cliente (a listagem de supervisão já tem outro propósito: cadastro/edição, não "consumo" executivo). Não fiz alteração lá nesta etapa; o esforço foi concentrado no portal do cliente, que era o pedido explícito e detalhado desta etapa.

## 9. Pontos preparados para GUT (não implementados)

- Plano de manutenção (`_render_tarefa_card`) já é uma lista de cards por tarefa — Gravidade/Urgência/Tendência entram como badges adicionais no mesmo card, sem redesenho.
- Card da lista de ativos tem o bloco de resumo (`resumo_html`) como um `<div>` de linhas simples — aceita mais uma linha "Prioridade GUT" sem quebrar layout.
- Score de saúde já segue as 4 faixas fixas — um "Score GUT" seria um número/badge adicional ao lado, não uma reestruturação.

## 10. Checks técnicos

Sem lint/typecheck/build configurados (mesma situação de todas as etapas anteriores). `py -m py_compile` nos 44 arquivos — sem erro. `import` de `ui`, `page_ativos`, `page_assistente` — sem erro de nome. Testado isoladamente (com dados sintéticos, sem depender do Streamlit nem de credenciais reais do Sheets): a função `_build_resumos()` — agrupamento por ativo, escolha da manutenção mais urgente, relatório mais recente, contagem de alertas e chamados abertos — todos os casos conferidos.

## 11. Confirmações pedidas

- Não foi criada sidebar.
- Sistema GUT não foi implementado.
- WhatsApp e e-mail não foram tocados.
- `client_id` continua vindo exclusivamente da sessão em todo o código novo.

## 12. Arquivos alterados

`page_ativos.py` (correção do id + lista + detalhe), `page_assistente.py` (contexto do ativo), `ui.py` (severidade "normal" no Design System).

## 13. Próxima etapa recomendada

Validar em produção (com a RJR ou o cliente de homologação) se a correção do `id` real de fato passou a trazer plano de manutenção e histórico técnico que antes apareciam vazios — é a forma mais rápida de confirmar se o bug suspeitado nas Etapas 3/4 estava mesmo silenciando dados reais.
