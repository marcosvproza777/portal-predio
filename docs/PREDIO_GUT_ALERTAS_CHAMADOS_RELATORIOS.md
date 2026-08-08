# Integração GUT com Alertas, Chamados e Relatórios — Etapa 8

> Data: 2026-08-07 | Escopo: `page_alertas.py`, `page_sv_alertas.py`, `page_chamados.py`, `page_sv_chamados.py`, `page_dashboard.py`, `page_ativos.py`, `assistant_engine.py`, `sheets.py` | Sem sidebar, sem alteração de cliente_id

A Etapa 6 criou o GUT e a Etapa 7 completou a integração com Manutenção. Esta etapa estende GUT para as demais origens — Alertas, Chamados e Recomendações por Condição (relatórios) — e consolida a visão cruzada entre elas no Dashboard, no Ativo e no Assistente.

## 1. Alertas

### Supervisão (`page_sv_alertas.py`)

O formulário "Publicar novo alerta" ganhou campo **Ativo** (vínculo opcional) e três seletores opcionais **Gravidade/Urgência/Tendência** (default `"—"`, não obrigatórios). Se os três forem preenchidos, o alerta é criado normalmente e depois `update_alerta_gut()` grava o score — se algum ficar em `"—"`, o alerta é criado sem GUT (pode ser avaliado depois, como qualquer outro item).

### Cliente (`page_alertas.py`)

Reescrita para consumir dados reais em vez do mock hardcoded (`_ALERTAS_MOCK`, removido). `_load_alertas()` lê `sheets.get_alertas_sv(client_id)` e traz também `Gut_Gravidade/Urgencia/Tendencia`. Como a aba `AlertasSV` não tem coluna de "lido/não lido", os filtros passaram a ser por **prioridade GUT** (Todos/Crítica/Alta/Moderada/Baixa) em vez de categoria, e o contador do sino (`get_unread_count`) passou a contar alertas com GUT Crítica. Cada card mostra o badge de prioridade GUT e a ação recomendada (`gut_acao_recomendada`) quando o alerta tem GUT calculado; alertas sem GUT aparecem normalmente, sem essa linha.

`page_farois.py` tinha uma função morta (`_render_alertas_importantes`, nunca chamada em lugar nenhum) que importava os símbolos removidos de `page_alertas.py` — removida, para não deixar um `ImportError` latente.

## 2. Chamados

### Cliente (`page_chamados.py`)

O formulário de abertura ganhou um expander opcional **"🎯 Sua avaliação de prioridade"**, com aviso de que é uma sugestão e a equipe Pred.IO pode ajustar (mais o `GUT_DISCLAIMER`). Se o cliente preencher G/U/T, `update_chamado_gut()` é chamado após a criação do chamado com a observação "Avaliação inicial sugerida pelo cliente na abertura." Preenchimento parcial ou vazio não bloqueia a abertura do chamado — GUT aqui é sempre opcional.

### Supervisão (`page_sv_chamados.py`)

Novo filtro **Prioridade GUT** (Todas/Crítica/Alta/Moderada/Baixa). A lista é ordenada por prioridade GUT (Crítica → Alta → Moderada → Baixa → sem GUT), e cards com GUT Crítica ganham borda vermelha e uma linha "🚨 Prioridade GUT Crítica — tratar primeiro". Métricas do topo ganharam o card "Críticos por GUT".

## 3. Recomendações por Condição (Relatórios)

`get_gut_summary()` já retornava tarefas de manutenção "por Condição" com `origem == "manutencao"` (para não quebrar filtros existentes em Dashboard/Ativos que dependem desse valor). Esta etapa adicionou o campo `subtipo` (valor bruto de `Tipo_Manutencao`) a cada item, permitindo distinguir "Condição" das demais sem alterar `origem`. Nova função:

```python
def get_recomendacoes_condicao(client_id: str) -> list[dict]:
    return [i for i in get_gut_summary(client_id)
            if i["origem"] == "manutencao" and i.get("subtipo") == "Condição"]
```

Testado isoladamente (`test_recomendacoes_condicao.py`): com duas tarefas sintéticas (uma "Condição", uma "Calendário"), `get_gut_summary` continua retornando as duas com `origem == "manutencao"` (compatibilidade preservada) e `get_recomendacoes_condicao` retorna só a de Condição.

Relatórios técnicos (`TechnicalReports`) já tinham GUT desde a Etapa 6 (`origem == "relatorio"` em `get_gut_summary`) — não recriado, só consumido nas novas seções abaixo.

## 4. Dashboard (`page_dashboard.py`)

A seção "🎯 Prioridade GUT" ganhou uma nova linha de 4 cards com o **breakdown por origem** dos itens críticos: Alertas Críticos GUT, Chamados Críticos GUT, Recomendações Críticas GUT (só subtipo Condição) e Manutenções Críticas GUT — ao lado dos dois cards gerais já existentes (Itens Críticos / Alta Prioridade, todas as origens somadas).

A linha de listas (antes 2 colunas) passou a 3: **Top 5 Ativos por GUT** (mantido), **Top 5 Ações Prioritárias** (novo — os 5 itens de maior score em qualquer origem, ordenados por `score` decrescente) e **Manutenções com Maior GUT** (mantido).

## 5. Ativo (`page_ativos.py`)

Novo bloco **"🎯 Prioridades Técnicas"**, inserido entre os dados do ativo e o bloco de Manutenções Prioritárias (Etapa 7). Mostra um card de destaque com a maior prioridade GUT do ativo (prioridade, score, origem, ação recomendada) e 4 contadores pequenos — Alertas, Chamados, Manutenções e Recomendações críticas, todos escopados a esse ativo (`ativo_id`). Reaproveita `get_gut_summary(client_id)` filtrado por `ativo_id`, sem nova consulta à planilha.

## 6. Assistente Técnico (`assistant_engine.py`)

A intenção `"gut"` ganhou 3 capacidades novas, na ordem certa (checagens mais específicas antes das genéricas, mesmo padrão das Etapas 6/7):

- **"Qual chamado devo tratar primeiro?"** — filtra `origem == "chamado"`, ordena por score.
- **"Tenho recomendações críticas?"** — filtra `subtipo == "Condição"` e prioridade Crítica; resposta reforça explicitamente que "nunca são executadas automaticamente por GUT".
- **"Algum relatório gerou prioridade alta?"** — filtra `origem == "relatorio"` com prioridade Alta/Crítica; resposta diferente para caso vazio ("Nenhum relatório gerou...") e caso com itens.

Também corrigido nesta etapa: a pergunta "O que devo resolver primeiro?" (uma das perguntas pedidas) não batia em nenhuma palavra-chave da intenção `gut` — só existiam variantes com "fazer primeiro". Adicionadas as variantes "o que devo resolver primeiro", "resolver primeiro", "o que devo olhar primeiro" à lista de keywords.

As perguntas já existentes desde a Etapa 6/7 ("Qual item está mais crítico?", "Qual alerta tem maior GUT?", "Qual ativo tem maior prioridade?") continuam funcionando sem mudança.

## 7. Segurança

Nenhuma função nova sem filtro de `client_id`: alertas, chamados e recomendações passam sempre por `get_alertas_sv(client_id)`, `get_chamados_v2(client_id)` ou `get_gut_summary(client_id)`, já auditados. Os campos de avaliação GUT do cliente (nos formulários de alerta/chamado) são apenas sugestões — a Supervisão sempre pode reavaliar. `Obs_Interna`/`Observacoes_Internas` continuam fora de qualquer tela ou resposta do Assistente voltada ao cliente.

## 8. Regra GUT (reafirmada)

Em nenhum ponto desta etapa — formulários, dashboard, ativo ou Assistente — GUT dispara automaticamente overhaul, troca de rolamento ou parada de máquina. Toda prioridade Crítica só recomenda abrir chamado técnico com a equipe Pred.IO. O `GUT_DISCLAIMER` aparece nos formulários que envolvem avaliação GUT (alerta da Supervisão, chamado do cliente) e nas respostas do Assistente sobre o tema.

## 9. O que ficou de fora (com motivo)

- **Status de leitura ("lido/não lido") em alertas**: a aba `AlertasSV` não tem essa coluna. Adicionar exigiria migração de schema para um conceito que não existia antes desta etapa e não foi pedido explicitamente — o contador do sino usa GUT Crítica como proxy de "precisa de atenção", que é a informação que já existe e é a mais relevante para o cliente.

## 10. Testes (isolados, scratchpad)

| Teste | Resultado |
|---|---|
| `add_alerta_sv` retorna Id (str) ou None, compatível com os 3 chamadores existentes que fazem `if ok:` | ✅ verificado por leitura de código, sem quebra |
| `get_gut_summary` mantém `origem == "manutencao"` para tarefas por Condição (não quebra filtros existentes) | ✅ `test_recomendacoes_condicao.py` |
| `get_recomendacoes_condicao` isola só subtipo Condição | ✅ `test_recomendacoes_condicao.py` |
| `page_alertas._load_alertas` monta os campos certos a partir de dados reais, incluindo GUT | ✅ `test_page_alertas_real.py` |
| `get_unread_count` conta GUT-Crítica; `client_id` vazio não chama `sheets` | ✅ `test_page_alertas_real.py` |
| Assistente: "Qual chamado devo tratar primeiro?" responde o chamado de maior score | ✅ `test_assistant_etapa8.py` |
| Assistente: "Tenho recomendações críticas?" responde e reforça que não é automático | ✅ `test_assistant_etapa8.py` |
| Assistente: "Algum relatório gerou prioridade alta?" — vazio vs. com itens | ✅ `test_assistant_etapa8.py` |
| Assistente: guardrail — nenhuma resposta autoriza overhaul/troca de rolamento/parada automática | ✅ `test_assistant_etapa8.py` |

## 11. Checks técnicos

Sem lint/typecheck/build configurados (mesma situação de todas as etapas). `py -m py_compile *.py` na raiz do projeto — sem erro. Os 13 scripts de teste isolados acumulados desde a Etapa 4 (incluindo os 2 novos desta etapa) rodam juntos sem regressão — a única falha observada (`test_assistant_manutencao_gut.py`, `UnicodeEncodeError` no `print` de um emoji) é um artefato do codepage cp1252 do console do Windows, não uma falha de lógica: reexecutado com `PYTHONIOENCODING=utf-8`, passa por completo.

## 12. Arquivos alterados

`sheets.py`, `page_alertas.py`, `page_sv_alertas.py`, `page_chamados.py`, `page_sv_chamados.py`, `page_dashboard.py`, `page_ativos.py`, `assistant_engine.py`, `page_farois.py` (remoção de código morto).

## 13. Arquivos criados

`docs/PREDIO_GUT_ALERTAS_CHAMADOS_RELATORIOS.md`

## 14. Confirmações pedidas

- Não foi criada sidebar.
- WhatsApp e e-mail não foram tocados.
- `client_id` continua vindo exclusivamente da sessão em todo código novo.
- Login e permissões não foram alterados.
- GUT crítico não gera overhaul automático em nenhuma tela ou resposta.
- GUT crítico não gera troca automática de rolamento em nenhuma tela ou resposta.
- GUT crítico não gera parada de máquina automática — sempre recomenda abrir chamado técnico com a equipe Pred.IO.
