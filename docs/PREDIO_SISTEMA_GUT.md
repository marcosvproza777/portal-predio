# Sistema GUT — Etapa 6

> Data: 2026-08-07 | Escopo: Portal do Cliente + Supervisão | Sem sidebar, sem alteração de regra de cliente_id

## 1. Conceito

**GUT = Gravidade × Urgência × Tendência.** Cada eixo recebe uma nota de 1 a 5 (definida pela Supervisão). O score (1 a 125) prioriza tecnicamente o que precisa de atenção primeiro — manutenções, alertas, chamados e recomendações de relatório.

**GUT nunca decide sozinho.** É só priorização. A frase abaixo aparece em toda tela onde GUT é editado ou explicado, e o Assistente a repete sempre que fala de GUT:

> "GUT é uma ferramenta de priorização e não substitui a avaliação técnica da equipe Pred.IO."

## 2. Cálculo

Função reutilizável em `gut.py`:

```python
from gut import calculate_gut
calculate_gut(gravidade, urgencia, tendencia)
# -> {"score": int, "prioridade": "Baixa"|"Moderada"|"Alta"|"Crítica"}  ou None
```

Regras: se **qualquer** nota estiver vazia ou fora de 1-5, retorna `None` (não calcula com dado incompleto). Recalcula toda vez que é chamada — nunca há um score "desatualizado" guardado sem recálculo (`sheets._gut_campos()` sempre recalcula antes de salvar).

## 3. Faixas de prioridade

| Score | Prioridade |
|---|---|
| 1 – 20 | Baixa |
| 21 – 50 | Moderada |
| 51 – 80 | Alta |
| 81 – 125 | Crítica |

Mesmas cores em todo o portal via `ui.STATUS_REGISTRY["gut"]` (Design System da Etapa 2): Baixa=cinza, Moderada=âmbar, Alta=laranja, Crítica=vermelho.

## 4. Onde os campos GUT vivem (sem migração destrutiva)

6 campos por item — `Gut_Gravidade`, `Gut_Urgencia`, `Gut_Tendencia`, `Gut_Score`, `Gut_Prioridade`, `Gut_Observacao` — adicionados a 4 abas do Google Sheets: **MaintenanceTasks**, **AlertasSV**, **Chamados**, **TechnicalReports**.

**Como a migração funciona sem apagar nada:** `sheets._ensure_extra_cols(aba, colunas)` (nova função, generaliza o padrão já existente `_ensure_chamados_v2_cols`) só **adiciona colunas ao final do cabeçalho que ainda não existem** — nunca remove, reordena ou sobrescreve dado existente. É chamada automaticamente na primeira vez que alguém salva um GUT (`update_maintenance_task_gut`, `update_alerta_gut`, `update_chamado_gut`, `update_report_gut`), não a cada carregamento de página — abas que ninguém usa GUT ainda continuam exatamente como estão.

Nas leituras (`get_maintenance_tasks`, `get_alertas_sv`, `get_chamados_v2`, `get_technical_reports`), os campos `Gut_*` já aparecem nas listas de cabeçalho — `.get("Gut_Gravidade")` nunca quebra mesmo antes da coluna existir de fato na planilha (retorna vazio/None, e `calculate_gut` trata isso corretamente como "não calcular").

## 5. Onde foi aplicado

| Local | Cliente vê | Supervisão pode editar |
|---|---|---|
| **Manutenção** (`page_manutencao.py` / `page_sv_manutencao.py`) | Badge de prioridade GUT + score + "ação recomendada" em cada tarefa | Expander "🎯 GUT" por tarefa: G, U, T, observação técnica |
| **Alertas** (`page_sv_alertas.py`) | — (Central de Alertas do cliente ainda roda sobre dado mock, ver §8) | Expander "🎯 GUT" por alerta publicado |
| **Chamados** (`page_chamados.py` / `page_sv_chamado_detalhe.py`) | Badge de prioridade GUT + score no card do chamado | G/U/T + observação no mesmo formulário "Atualizar Chamado" já existente |
| **Relatórios** (`page_relatorios.py` / `page_sv_relatorios.py`) | Badge de prioridade GUT + score junto da recomendação | Expander "🎯 Prioridade GUT da recomendação" no formulário de edição |
| **Ativos — lista** (`page_ativos.py`) | Badge "🎯 GUT {score} · {prioridade}" no cabeçalho do card — maior GUT entre tudo relacionado a esse ativo | — |
| **Ativos — detalhe** | 4º card de métricas: "Prioridade GUT" + GUT máximo, ao lado de Status/Score/Criticidade | — |
| **Dashboard** (`page_dashboard.py`) | Seção "🎯 Prioridade GUT": Itens Críticos, Itens Alta Prioridade, Top 5 Ativos por GUT, Manutenções com Maior GUT | — |
| **Assistente Técnico** | Responde perguntas sobre GUT (ver §7) | — |

Em todo lugar onde o **cliente** vê GUT, só aparecem **prioridade e score** — nunca as notas G/U/T individuais nem a observação técnica (essas são edição/uso interno da Supervisão), conforme pedido.

## 6. Agregação — `sheets.get_gut_summary(client_id)`

Função central que todo o resto reaproveita: busca manutenção + alertas + chamados + relatórios do cliente (as mesmas 4 consultas, sempre filtradas por `client_id`/`staff=False`), calcula GUT de cada item e devolve uma lista única ordenada por score decrescente. Dashboard, Ativos e Assistente usam essa mesma função — nenhum deles refaz a consulta ao Sheets por conta própria.

## 7. Assistente Técnico

Nova intenção `"gut"` em `assistant_engine.py`, verificada **antes** de `manutencao`/`alertas`/`chamados`/`status_ativo` (perguntas de GUT citam essas mesmas palavras). Cobre as 5 perguntas pedidas:

- "Qual manutenção é mais crítica?" → maior GUT entre as tarefas de manutenção
- "Qual ativo tem maior prioridade?" → ativo com o item de maior GUT vinculado
- "O que devo fazer primeiro?" → maior GUT entre todos os itens (qualquer origem)
- "Tenho algum item GUT crítico?" → contagem + lista dos itens com prioridade Crítica
- "Quais alertas têm maior GUT?" → alertas ordenados por GUT decrescente

Funciona nos dois modos do Assistente:
- **Sem IA** (`assistant_engine._build_response`, fallback controlado): respostas acima, testadas isoladamente.
- **Com IA real** (`ai_assistant.py`, Claude via Anthropic API): o resumo GUT do cliente entra no contexto enviado à IA (`=== PRIORIZAÇÃO GUT ===`), e o system prompt ganhou uma seção "REGRA ESPECIAL — PRIORIZAÇÃO GUT" com as mesmas faixas, a mesma frase obrigatória e a mesma proibição de autorizar ação automática.

Toda resposta sobre GUT crítico recomenda abrir chamado técnico (`suggested_actions`/`related_links` apontando para `chamados`) — nunca recomenda overhaul, troca de peça ou parada de máquina.

## 8. O que não foi feito (fora de escopo desta etapa)

- **`page_alertas.py`** (Central de Alertas do portal do cliente) continua sobre `_ALERTAS_MOCK`, gap já documentado na Etapa 1 — o GUT foi cabeado no lado que já é real (`AlertasSV`, usado por Dashboard/Ativos/`page_sv_alertas.py`), não no mock.
- **Bug pré-existente encontrado, não corrigido**: `page_sv_relatorios.py` salva edições de relatório chamando `update_technical_report(id, _dados())`, mas `_dados()` usa chaves em `snake_case` ("titulo", "resumo"...) enquanto `update_technical_report()` só grava campos cujo nome bate **exatamente** com o cabeçalho da planilha (`Título`, `Resumo` em `Title_Case`). Ou seja, o botão "💾 Salvar Rascunho" ao **editar** um relatório existente parece não estar de fato persistindo as mudanças de título/resumo/severidade etc. (só atualiza `Updated_At`, que é o único nome que já bate por coincidência). **Não é um bug do GUT** — o `update_report_gut()` novo usa nomes `Title_Case` corretos e funciona independente disso — mas vale investigar antes de confiar em edições de relatório já salvas.

## 9. Segurança

- `client_id` continua vindo exclusivamente de `current_client_id()`/sessão em toda função nova — nenhuma delas aceita `client_id` de URL ou input.
- `get_gut_summary`, `update_*_gut` e as leituras de GUT em cada página reutilizam as MESMAS funções já auditadas em etapas anteriores (`get_maintenance_tasks(..., staff=False)`, `get_technical_reports(..., staff=False)` — só `Status=="Publicado"` —, `get_alertas_sv(client_id)`, `get_chamados_v2(client_id=...)`) — nenhuma consulta nova sem filtro por cliente foi criada.
- `Obs_Interna`/`Observacoes_Internas` de nenhuma aba são lidos pelos componentes GUT.
- Cliente nunca vê as notas G/U/T nem a observação técnica — só prioridade e score (ver tabela do §5).
- Cliente não edita GUT em lugar nenhum — os 4 formulários de edição (`page_sv_manutencao.py`, `page_sv_alertas.py`, `page_sv_chamado_detalhe.py`, `page_sv_relatorios.py`) estão todos atrás de `require_staff()`, já existente nessas páginas.

## 10. Testes (os 7 pedidos)

| # | Teste | Resultado |
|---|---|---|
| 1 | G=5, U=4, T=5 → GUT=100, Crítica | ✅ `calculate_gut(5,4,5) == {"score": 100, "prioridade": "Crítica"}` |
| 2 | G=2, U=2, T=3 → GUT=12, Baixa | ✅ `calculate_gut(2,2,3) == {"score": 12, "prioridade": "Baixa"}` |
| 3 | Alterar nota → recalcula | ✅ `_gut_campos()` sempre chama `calculate_gut()` de novo antes de salvar; nunca reaproveita um score antigo |
| 4 | Cliente A não vê dado de Cliente B | ✅ por construção — toda função GUT nova recebe `client_id` e delega para funções já filtradas por cliente; nenhuma nova consulta sem esse filtro |
| 5 | Dashboard mostra itens críticos | ✅ seção "🎯 Prioridade GUT" — card "Itens Críticos GUT" |
| 6 | Assistente responde qual item é mais crítico | ✅ testado isoladamente (`test_assistant_gut.py`) — as 5 perguntas do pedido, incluindo "qual item é mais crítico" |
| 7 | GUT crítico não gera overhaul automático | ✅ nenhuma função GUT dispara ação automática (só grava os 6 campos); todas as respostas do Assistente testadas não mencionam overhaul/parada automática, só recomendam abrir chamado |

Testes 1-3 e 6-7 rodados via scripts isolados (sem depender de credenciais reais do Google Sheets, usando `unittest`-style asserts com dados sintéticos); 4 e 5 verificados por leitura de código (mesma base de funções já auditada nas etapas anteriores).

## 11. Checks técnicos

Sem lint/typecheck/build configurados no projeto (mesma situação de todas as etapas). `py -m py_compile` nos 45 arquivos `.py` (44 + `gut.py` novo) — sem erro. `import` de todos os 16 módulos alterados/criados — sem erro de nome.

## 12. Confirmações pedidas

- Não foi criada sidebar.
- WhatsApp e e-mail não foram tocados (inclusive o envio de WhatsApp já existente em `page_sv_alertas.py` ficou intacto — só adicionei um expander de GUT ao lado).
- `client_id` continua protegido — todas as novas funções o recebem por parâmetro vindo da sessão, nunca do front-end.
- GUT crítico não gera overhaul, troca de peça ou parada automática em lugar nenhum — nem no backend, nem no Assistente.

## 13. Arquivos criados

`gut.py`

## 14. Arquivos alterados

`sheets.py`, `ui.py`, `assistant_engine.py`, `ai_assistant.py`, `page_manutencao.py`, `page_sv_manutencao.py`, `page_sv_alertas.py`, `page_chamados.py`, `page_sv_chamado_detalhe.py`, `page_ativos.py`, `page_dashboard.py`, `page_relatorios.py`, `page_sv_relatorios.py`.

## 15. Próxima etapa recomendada

1. Investigar e corrigir o bug de `update_technical_report`/`_dados()` encontrado no §8 — é maior prioridade que qualquer refinamento de GUT.
2. Decidir se `page_alertas.py` (Central de Alertas do cliente) deve ser reescrita para usar `AlertasSV` real — hoje o GUT "funciona" para alertas nos lugares que já usam dado real (Dashboard, Ativos), mas não na própria tela de Alertas do cliente.
3. Com dados reais de produção, confirmar visualmente que os badges GUT aparecem corretamente após a Supervisão definir as primeiras notas G/U/T.
