# Plano de Manutenção com Prioridade GUT — Etapa 7

> Data: 2026-08-07 | Escopo: `/portal/manutencao`, `/supervisao/manutencao` + integrações | Sem sidebar, sem alteração de cliente_id

A Etapa 6 já tinha colocado GUT na tela de manutenção (badge de prioridade+score, ação recomendada, edição G/U/T na Supervisão). Esta etapa completa o que faltava: **filtros, ordenação padrão, ações rápidas, e a integração de "manutenção GUT" com Ativos, Dashboard e Assistente especificamente** (não só GUT genérico). Também corrigi, a pedido, o bug encontrado na Etapa 6.

## 0. Bug corrigido (pedido explícito)

`page_sv_relatorios.py`: os botões "💾 Salvar Rascunho" e "📢 Publicar" passavam `_dados()` (chaves em `snake_case`: `"titulo"`, `"resumo"`...) direto para `update_technical_report()`, que só grava campos cujo nome bate **exatamente** com o cabeçalho da planilha (`Title_Case`: `"Titulo"`, `"Resumo"`...). Resultado: editar um relatório existente não salvava título/resumo/severidade/etc — só `Updated_At` batia por coincidência.

**Correção**: nova função `_dados_sheet()` traduz as chaves de `_dados()` para os nomes reais das colunas antes de chamar `update_technical_report()`. `add_technical_report()` (criação) não foi tocado — já usava `_dados()` corretamente (esperava `snake_case`). Validado com teste isolado: as 12 colunas mapeadas batem 100% com `_HEADERS_TECH_REPORTS`.

## 1. Tela de manutenção do cliente (`page_manutencao.py`)

### Filtros (antes: Tipo, Status, Prioridade do chamado)

Adicionados dois novos, sem tornar o filtro complexo:
- **Prioridade GUT** — Todas / Crítica / Alta / Moderada / Baixa
- **Ativo** — lista dos ativos que aparecem nas tarefas carregadas

Os filtros de Status foram renomeados para bater com o vocabulário pedido (Vencidas/Próximas/Concluídas/Por condição/Em dia) — mesmo comportamento de antes, só o rótulo mudou.

### Ordenação padrão (nova)

1. Prioridade GUT Crítica
2. Prioridade GUT Alta
3. Vencidas
4. Data mais próxima (para tarefas por Horímetro, horas restantes; para Calendário, dias até a data — usado só para desempate dentro do mesmo grupo)

Testado isoladamente com 4 tarefas sintéticas (`test_manutencao_ordering.py`) — confirma que uma tarefa "Próxima" com GUT Alta aparece **antes** de uma tarefa "Vencida" sem GUT, exatamente como pedido no critério 1→2→3.

### Ações rápidas (antes: só "Abrir chamado" em tarefas vencidas/próximas)

Agora toda tarefa tem: **⚙️ Ver ativo** · **📁 Ver relatórios** · **🤖 Perguntar ao Assistente** — e tarefas vencidas/próximas mantêm **🔧 Abrir chamado**. "Ver relatório relacionado" foi implementado como link para a aba Relatórios (não existe um vínculo direto tarefa→relatório no modelo de dados hoje — ver §8).

**Não implementado, com motivo:** "Marcar como concluída" com checagem de permissão do perfil. O modelo de usuário do portal hoje não tem um campo de permissão granular para isso — o cliente é sempre perfil `"cliente"`, sem sub-níveis. Implementar exigiria criar um novo conceito de permissão (mudança de modelo de dados/auth, fora do escopo desta etapa). Como a regra explícita era "se não tiver permissão, não mostrar o botão", e não existe hoje nenhum cliente com essa permissão, o botão foi **omitido** (comportamento correto por omissão, já que mostrar um botão que ninguém pode usar seria pior).

## 2. Tela de manutenção da Supervisão (`page_sv_manutencao.py`)

Adicionados os mesmos filtros do cliente (Status, Prioridade GUT, Ativo) à lista de tarefas cadastradas, mais a mesma ordenação padrão (Crítica → Alta → vencida). A edição de G/U/T por tarefa (expander "🎯 GUT", da Etapa 6) não mudou.

## 3. Visual GUT (padronização)

Sem mudança nas faixas (já corretas desde a Etapa 6): 1-20 Baixa, 21-50 Moderada, 51-80 Alta, 81-125 Crítica — cores em `ui.STATUS_REGISTRY["gut"]`. O texto informativo (`GUT_DISCLAIMER` em `gut.py`) já aparece no topo da tela de manutenção do cliente desde a Etapa 6; mantido.

## 4. Integração com Ativos

Novo bloco **"🎯 Manutenções Prioritárias"** no detalhe do ativo (`page_ativos.py`), entre "Componentes" e o plano de manutenção completo. Mostra até 5 itens — vencidas, GUT Crítica/Alta, e próximas do vencimento — ordenados pela mesma regra (Crítica → Alta → vencida). O "maior GUT do ativo" já existia desde a Etapa 6 (4º card de métricas "Prioridade GUT"); não foi duplicado aqui, só referenciado.

## 5. Integração com Dashboard

A seção "🎯 Prioridade GUT" (Etapa 6) ganhou duas métricas específicas de manutenção ao lado das gerais: **Manutenções Críticas GUT** e **Manutenções Alta Prioridade** (grid de 4 cards agora, era 2). "Top 5 Manutenções por GUT" e "Manutenções Vencidas" já existiam (Etapas 4 e 6) — não recriados. Cada uma das duas listas ("Top 5 Ativos por GUT" / "Manutenções com Maior GUT") ganhou um botão de navegação abaixo ("Ver Ativos →" / "Ver Manutenção →") — decisão de manter navegação por seção em vez de um botão por item de 5 itens × 2 listas, para não poluir visualmente; é o mesmo padrão já usado em todas as outras seções do dashboard.

## 6. Integração com o Assistente Técnico

A intenção `"gut"` (criada na Etapa 6) ganhou 3 capacidades novas, testadas isoladamente:

- **"Quais tarefas estão vencidas?"** — única pergunta desta lista que **não depende de GUT estar definido** (usa `ctx["tarefas_manutencao"]`, que tem o status real calculado de toda tarefa, com ou sem GUT). Checada antes de qualquer outra coisa na intenção `gut`.
- **"Tenho manutenção GUT crítica?"** — variante da pergunta genérica da Etapa 6, mas escopada só a `origem == "manutencao"`.
- **"Qual ativo tem maior prioridade de manutenção?"** — variante de "qual ativo tem maior prioridade" escopada a manutenção. Importante: como a pergunta contém tanto "ativo" quanto "manutenção", ela é verificada **antes** dos dois casos isolados (só "ativo" / só "manutenção"), senão pegaria a resposta errada (ex.: responder com o item de maior GUT de qualquer origem, que pode ser um alerta, não uma manutenção).

"Quais manutenções são mais críticas?" e "O que devo fazer primeiro?" já funcionavam desde a Etapa 6, sem mudança.

Testado (`test_assistant_manutencao_gut.py`): as 5 perguntas roteiam para a intenção certa, cada uma responde com o item certo (incluindo o caso de desambiguação ativo-com-maior-GUT-de-manutenção vs. ativo-com-maior-GUT-geral), e nenhuma resposta menciona overhaul ou parada automática.

O prompt da IA real (`ai_assistant.py`) também ganhou o score/prioridade GUT em cada linha de tarefa no contexto enviado ao Claude — antes só aparecia na seção agregada "PRIORIZAÇÃO GUT" (que só lista itens com GUT definido); agora aparece também por tarefa, inclusive nas sem GUT (mostrando status), o que ajuda a IA a responder "quais estão vencidas" mesmo sem prioridade GUT cadastrada.

## 7. Segurança

Nenhuma função nova sem filtro de `client_id`. Tudo reaproveita as mesmas fontes já auditadas (`get_maintenance_tasks(client_id=..., staff=False)`, `get_gut_summary(client_id)`, `get_client_context(client_id)`). `Obs_Interna` de tarefas de manutenção não é lido em nenhum lugar novo desta etapa. O cliente continua sem ver G/U/T individuais, só prioridade e score (mesma regra da Etapa 6).

## 8. O que ficou de fora (com motivo)

- **Rotas `/portal/manutencao/[id]` e `/supervisao/manutencao/[id]`**: não existem hoje (item 1 dizia "se existir, melhorar também") — o padrão do app é mostrar tarefas como cards expansíveis numa lista só, sem tela de detalhe dedicada por tarefa. Não criei uma do zero, para não expandir o escopo além do pedido.
- **"Ver relatório relacionado" como vínculo direto**: `MaintenanceTasks` não tem uma coluna `Report_Id` (diferente de `Chamados`, que tem `Report_Id`/`Maintenance_Task_Id`/`Alert_Id`). O botão navega para a aba Relatórios em geral, não para um relatório específico — vincular exigiria adicionar uma coluna nova ao modelo de dados, o que acumularia com a mesma cautela de "não fazer migração destrutiva sem necessidade clara" já seguida nas etapas anteriores.
- **"Marcar como concluída" no portal do cliente**: ver §1 — não existe hoje um sistema de permissão granular no modelo de usuário para decidir isso.

## 9. Testes (os 8 pedidos)

| # | Teste | Resultado |
|---|---|---|
| 1 | G=5,U=4,T=5 → GUT 100, Crítica | ✅ (já validado na Etapa 6, `calculate_gut` não mudou) |
| 2 | Filtro Prioridade Crítica só mostra críticos | ✅ testado isoladamente — filtro `gut_f` compara `_gut_prioridade(e) == gut_f` |
| 3 | Ordenação padrão — críticos/vencidos primeiro | ✅ testado (`test_manutencao_ordering.py`) |
| 4 | Cliente A não vê manutenção de Cliente B | ✅ por construção — toda consulta nova recebe `client_id` e delega às funções já auditadas |
| 5 | Supervisão edita G, U, T | ✅ já implementado na Etapa 6 (expander "🎯 GUT"), mantido; `st.number_input(1,5,...)` impede valor fora da faixa |
| 6 | Portal Cliente não vê observações internas | ✅ nenhuma função nova lê `Obs_Interna`/`Observacoes_Internas` |
| 7 | Assistente responde qual manutenção é mais crítica | ✅ testado (`test_assistant_manutencao_gut.py`) |
| 8 | GUT crítico não gera overhaul automático | ✅ nenhuma ação automática disparada; guardrail testado nas 5 novas respostas |

## 10. Checks técnicos

Sem lint/typecheck/build configurados (mesma situação de todas as etapas). `py -m py_compile` nos 45 arquivos — sem erro. `import` dos 7 módulos alterados — sem erro. Os 10 scripts de teste isolados acumulados desde a Etapa 4 (incluindo os 3 novos desta etapa) rodam juntos sem regressão.

## 11. Confirmações pedidas

- Não foi criada sidebar.
- WhatsApp e e-mail não foram tocados.
- `client_id` continua vindo exclusivamente da sessão em todo código novo.
- GUT crítico não gera overhaul, troca de peça ou parada automática — nem no backend, nem nas ações rápidas, nem no Assistente.

## 12. Arquivos alterados

`page_sv_relatorios.py` (bug + já tinha GUT), `page_manutencao.py`, `page_sv_manutencao.py`, `page_ativos.py`, `page_dashboard.py`, `assistant_engine.py`, `ai_assistant.py`.

## 13. Arquivos criados

`docs/PREDIO_MANUTENCAO_GUT.md`

## 14. Próxima etapa recomendada

Se "marcar como concluída pelo cliente" for realmente necessário, definir primeiro o modelo de permissão (provavelmente um campo novo em `Usuarios`/`Clientes`, ex. `Permite_Concluir_Manutencao`) antes de criar o botão — decisão de produto, não só de tela.
