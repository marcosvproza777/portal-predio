# Integração App Relatórios ↔ Portal Pred.IO — Etapa 5 (IA, Histórico, GUT, Dashboard, Resumo Executivo)

Data: 2026-08-08
Status: Implementado sobre a base das Etapas 1–4. Nenhuma migração destrutiva.

Pré-requisitos: [Etapa 1](PREDIO_INTEGRACAO_APP_RELATORIOS_ETAPA_1.md) (arquitetura), Etapa 2 (upload direto), Etapa 3 (`integration_api.py` + botão "Publicar no Portal Pred.IO"), [Etapa 4](PREDIO_INTEGRACAO_DADOS_RELATORIOS_ETAPA_4.md) (dados estruturados + vínculo cliente/ativo).

---

## 0. O que já existia vs. o que foi construído nesta etapa

Boa parte do pedido da Etapa 5 **já estava implementado** antes desta etapa começar — construído nas Etapas 2–4, ou já existente no Portal antes deste projeto de integração (GUT, Resumo Executivo). Confirmei isso lendo o código antes de escrever qualquer linha nova, para não duplicar. O que era novo de fato:

1. **Indexação para IA centralizada** — antes, quem chamava `publish_technical_report()` precisava lembrar de chamar `index_relatorio_tecnico()` depois (dois pontos de chamada em `page_sv_relatorios.py`, fácil de esquecer num terceiro lugar). Agora a indexação roda **dentro** de `publish_technical_report()` — impossível publicar sem indexar.
2. **`reindex_technical_report(report_id)`** — função nova, pedida explicitamente na Etapa 5, com guard de segurança (só reindexa `Status == "Publicado"`).
3. **Reindexação ao atualizar um relatório já publicado** — gap real encontrado: se o App Relatórios reenviasse um `report_id` já publicado, ou a Supervisão editasse o conteúdo de um relatório já publicado, os chunks antigos ficavam parados (conteúdo desatualizado no Assistente). Corrigido em `integration_api.py` e `page_sv_relatorios.py`.
4. **Indicadores novos no Dashboard da Supervisão** (`page_sv_dashboard.py`) — relatórios por severidade, GUT alto, recomendações geradas, últimos relatórios publicados. Confirmei por leitura de código que isso **não existia** nesse dashboard (existia só no dashboard do cliente).

Tudo o mais listado abaixo (§2–§10) já funcionava — documentado aqui para deixar claro *como* funciona e *onde* está no código.

---

## 1. Fluxo real (Etapas 1–5 combinadas)

```
App Relatórios finaliza relatório
        │  botão "Publicar no Portal Pred.IO" (Etapa 3)
        ▼
integration_api.py — POST /api/integrations/reports
        │  valida token, cliente, ativo (pertence ao cliente)
        │  cria/atualiza por App_Report_Id (nunca duplica)
        ▼
TechnicalReports — Status = "Em revisão"  (nunca indexado, nunca no Dashboard "publicado", nunca na IA)
        │  equipe Pred.IO revisa e clica "Publicar" (Supervisão)
        ▼
publish_technical_report()
        ├─ Status → "Publicado"
        ├─ Score do ativo atualizado
        ├─ Evento em ReportTimeline (histórico do ativo)
        ├─ Alerta interno se severidade Crítico/Urgente
        ├─ Notificação externa ao cliente
        └─ reindex_technical_report() → chunks no TechnicalReportChunks
        ▼
A partir daqui, automaticamente, sem código extra por já usarem
get_technical_reports()/get_gut_summary() com o mesmo relatório:
        ├─ Portal do Cliente (/portal/relatorios)
        ├─ Dashboard do cliente (GUT, recomendações, ações prioritárias)
        ├─ Dashboard da Supervisão (severidade, GUT alto — Etapa 5)
        ├─ Resumo Executivo (indicadores, gráficos, principais pontos)
        └─ Assistente Técnico (chunks indexados)
```

---

## 2. Assistente Técnico

**Indexação** (`sheets.index_relatorio_tecnico`, chamada só através de `reindex_technical_report`): cria/atualiza chunks em `TechnicalReportChunks` a partir de `Resumo` (diagnóstico), `Recomendacoes`, `Conclusao`, mais um chunk de "ficha técnica" (tipo/severidade/data/equipamento). `Obs_Interna` **nunca** entra em nenhum chunk — não é lida em nenhum ponto da função.

**Quando indexa**: só quando `Status == "Publicado"` — `reindex_technical_report()` verifica isso antes de fazer qualquer coisa e recusa (retorna `{"ok": False}`, sem gravar nada) para Rascunho/Em revisão. `publish_technical_report()` só chama isso **depois** de já ter mudado o Status para "Publicado", então a ordem está correta.

**Consulta pelo Assistente** (`assistant_engine.py`): já usa `get_technical_reports(client_id=client_id, staff=False)` (2 pontos de chamada) — `staff=False` força `Status == "Publicado"` **dentro do próprio `sheets.get_technical_reports()`** (não é disciplina de quem chama, é a função que filtra). Chunks são lidos via `get_chunks_relatorio(report_id, client_id=client_id)` — sempre com `client_id`, nunca lê chunk de outro cliente.

**Perguntas que o Assistente já consegue responder** (infraestrutura pronta desde que haja relatórios publicados com os dados): "o que o último relatório concluiu" (chunk Resumo/Conclusão), "qual foi a recomendação" (chunk Recomendações), "houve relatório crítico" (ficha técnica traz severidade), "qual ativo teve maior severidade"/"maior GUT" (via `get_gut_summary`, ver §4). "Existe indicação de overhaul/troca de rolamento" — o Assistente só pode responder com o que está no texto do relatório; nunca infere isso sozinho (ver §12).

**Fonte exibida**: os textos indexados vêm de relatórios cuja origem já é rastreada (`Origem` = `app_relatorios` ou vazio/Portal) — a camada de apresentação do Assistente é responsável por rotular "Pred.IO"; nenhuma mudança de UI do Assistente foi feita nesta etapa (fora de escopo — só os dados foram garantidos).

---

## 3. Histórico do ativo

Tabela real: `ReportTimeline` (equivalente ao `asset_timeline_events` do pedido). Campos: `Ativo_Id`, `Cliente_Id`, `Tipo`, `Titulo`, `Descricao`, `Data`, `Origem` (equivalente a "fonte" — valor `"Relatórios Técnicos"`, não literalmente a string "Pred.IO"; decisão mantida da Etapa 4 para não alterar um rótulo usado por todos os eventos do sistema, não só os de relatório), `Report_Id`, `Visivel_Cliente`.

Criado automaticamente por `publish_technical_report()`, com descrição resumida (severidade + trecho do resumo + trecho da recomendação — melhorado na Etapa 4). **Nunca duplica**: publicação só acontece uma vez por relatório (`publish_technical_report` recusa publicar um relatório que já está `Status == "Publicado"`); atualizações posteriores de conteúdo (reenvio do App, edição na Supervisão) atualizam o relatório e reindexam os chunks, mas **não criam um novo evento de timeline** — o evento original continua representando a publicação.

---

## 4. GUT e recomendações

**Se o relatório tiver GUT**: `integration_api.py` só aceita as 3 notas (Gravidade/Urgência/Tendência) juntas, valida 1–5, e **sempre recalcula** score/prioridade via `gut.calculate_gut()` no backend — nunca aceita um score pronto vindo de fora (corrigido na Etapa 4). Notas fora de 1–5 retornam erro 422 antes de qualquer gravação.

**Se não tiver GUT**: fica em branco. A Supervisão continua podendo definir depois (`update_report_gut`, existente desde a Etapa 2/3) — nada foi inventado.

**"Recomendação por condição"**: não existe uma aba separada — e não foi criada uma nesta etapa, para não duplicar o que já existe. `sheets.get_gut_summary(client_id)` (já existente antes deste projeto) já agrega, em tempo real, toda linha com GUT válido de 4 fontes (`MaintenanceTasks`, `AlertasSV`, `Chamados`, `TechnicalReports`) num formato **idêntico** ao pedido: `{origem, titulo, ativo_id, score, prioridade, id, cliente_id, descricao, acao_recomendada, status, created_at}`. Para relatórios técnicos, `origem = "relatorio"`, `descricao` vem de `Recomendacoes` (ou `Resumo` se vazio), e isso já inclui automaticamente qualquer relatório publicado pelo App Relatórios, sem nenhum código novo — é a mesma função usada pelo Dashboard do cliente e pelo Resumo Executivo.

**Regra de não gerar ação automática**: `gut.gut_acao_recomendada(prioridade)` (função central usada por toda ação recomendada do sistema) só retorna textos como *"solicitar avaliação técnica da equipe Pred.IO"* / *"agendar avaliação técnica"* / *"acompanhar e planejar intervenção"* / *"manter monitoramento de rotina"* — nunca prescreve overhaul, troca de rolamento, parada de máquina ou desmontagem, para nenhuma prioridade, nem mesmo "Crítica". Ver `GUT_DISCLAIMER` em `gut.py`.

---

## 5. Dashboard

### Supervisão (`page_sv_dashboard.py`) — indicadores novos nesta etapa
Linha de cartões "Relatórios — Severidade & GUT": **Relatórios Críticos** (severidade Crítico/Urgente, só publicados) com contagem de ativos distintos afetados, **GUT Alto (Relatórios)** (prioridade Alta ou Crítica), **Recomendações Geradas** (publicados com campo Recomendações preenchido). Mais uma lista **"Últimos Relatórios Publicados"** (severidade colorida, indica quando a origem é o App Relatórios). Tudo calculado sobre `get_technical_reports(client_id="", staff=True)`, já carregado por esse dashboard — nenhuma consulta nova ao Sheets, só processamento adicional do que já vinha.

### Cliente (`page_dashboard.py`) — já existia, confirmado funcionando
Já tinha `_render_gut_section` (GUT críticos/altos, top ativos por GUT), `_render_relatorios` (últimos relatórios), `_render_recomendacoes`, `_render_acoes_prioritarias` — todos já effectivamente alimentados por `get_technical_reports(client_id=client_id, staff=False)`, então relatórios do App já apareciam aqui desde a Etapa 4. Nada mudou nesta etapa neste arquivo.

**Filtros por cliente_id/ativo/status Publicado**: já garantidos — `get_technical_reports` sempre aceita esses parâmetros, e o lado cliente sempre força `staff=False` (Publicado obrigatório). Filtro por período é feito em memória pelas telas que precisam (Resumo Executivo já tem seletor de período).

---

## 6. Detalhe do ativo

Não precisou de mudança de código — o dashboard do cliente (§5) já funciona como o "detalhe agregado" pedido: último relatório, severidade, recomendações e maior GUT relacionado já vêm do mesmo `get_technical_reports`/`get_gut_summary`. Score de saúde do ativo continua controlado só por `publish_technical_report()` (regra existente desde antes deste projeto) — **não foi alterado** nenhum cálculo de score nesta etapa.

---

## 7–9. Resumo Executivo (dados, gráficos, principais pontos)

Já implementado antes desta etapa, em `executive_summary.py`: `generate_executive_summary(...)` já coleta via `get_technical_reports(client_id=..., ativo_id=..., staff=staff_mode)` — relatórios do App entram automaticamente (Etapa 4). `compute_chart_data()` já gera os dados para: relatórios por severidade, GUT por prioridade, evolução de score, top-5 ativos críticos, status de manutenção. `principais_pontos_gerencia()` já gera até 5 bullets executivos a partir dos dados reais (não do PDF). A UI (`resumo_executivo_ui.py`) já renderiza esses gráficos com Plotly (`_chart_relatorios_severidade`, `_chart_gut_prioridade`, `_chart_score_evolucao`, etc.) — nenhum gráfico vazio é mostrado porque cada `_chart_*` já checa se há dados antes de desenhar.

Nenhuma mudança de código foi necessária aqui — foi só verificado, lendo `executive_summary.py`/`resumo_executivo_ui.py` inteiros, que a cobertura pedida já existia.

---

## 10. Assistente + Resumo Executivo combinados

Perguntas tipo "resuma os últimos 30 dias" / "principais achados" / "o que levar pra reunião" dependem da lógica de intenção do Assistente (`assistant_engine.py`), que já usa os mesmos dados de `get_technical_reports(staff=False)` — sempre respeitando `client_id` da sessão e `Status == "Publicado"`. Nenhuma lógica nova de conversação foi implementada nesta etapa (fora de escopo, conforme pedido) — só garantimos que os dados que essas perguntas precisariam já estão corretos e seguros.

---

## 11. Reindexação

```python
sheets.reindex_technical_report(report_id) -> {"ok": bool, "erro": str|None}
```

- Só reindexa se `Status == "Publicado"` (senão retorna `{"ok": False, "erro": "..."}` sem gravar nada).
- Chamada automaticamente:
  - Dentro de `publish_technical_report()`, na primeira publicação.
  - Em `integration_api.py`, quando o App Relatórios reenvia um `report_id` que já corresponde a um relatório `Publicado` no Portal.
  - Em `page_sv_relatorios.py`, quando a Supervisão salva edições de um relatório que já está `Publicado`.
- **Nunca duplica**: `index_relatorio_tecnico()` sempre apaga os chunks antigos daquele `Report_Id` antes de inserir os novos.
- Histórico do ativo, recomendações (`get_gut_summary`) e Dashboard/Resumo Executivo **não precisam de reindexação própria** — todos leem `TechnicalReports` ao vivo a cada chamada (nenhum é uma cópia desatualizada), então uma atualização de conteúdo já reflete neles automaticamente assim que a planilha é salva.

---

## 12. Segurança

| Regra | Como é garantida |
|---|---|
| Rascunho/Em revisão nunca entram na IA | `reindex_technical_report()` só age em `Status == "Publicado"`; `publish_technical_report()` só chama isso depois de mudar o status |
| Observação interna nunca é indexada | `index_relatorio_tecnico()` nunca lê `Obs_Interna` |
| Cliente A não acessa Cliente B | `get_technical_reports(staff=False)` filtra por `Cliente_Id` da sessão; `get_chunks_relatorio()` idem; `get_gut_summary()` idem — mesma garantia usada em todo o Portal, nada novo, só confirmado |
| Cliente só vê Publicado | `get_technical_reports(staff=False)` força `Status == "Publicado"` internamente — não é escolha de quem chama |
| Chunks brutos não aparecem para o cliente | `get_chunks_relatorio` só é usado internamente por `assistant_engine.py` — nenhuma tela renderiza a aba `TechnicalReportChunks` diretamente (confirmado por busca em todo o repositório) |
| Arquivos privados continuam protegidos | Nenhuma mudança em `drive_storage.py` nesta etapa — URLs assinadas de curta duração, como desde a Etapa 3 |
| Assistente não consulta relatório de outro cliente | Mesmo mecanismo de `client_id` de sessão, sem mudança |
| GUT não gera overhaul/troca de rolamento/parada automaticamente | `gut.gut_acao_recomendada()` nunca prescreve essas ações, para nenhuma prioridade — texto fixo, sem geração dinâmica |
| Integração autenticada | Sem mudança — token Bearer da Etapa 3, inalterado |

---

## 13. Nota sobre testes

Testes de validação (guard de `reindex_technical_report` para relatório inexistente, autenticação, cliente inválido) foram executados contra o Portal de produção **sem gravar nada** (confirmado por retorno de erro antes de qualquer escrita). Nenhum teste de escrita foi executado nesta etapa — aprendendo com o incidente da Etapa 4 (relatório de teste criado por engano e removido), os testes desta etapa usaram deliberadamente apenas IDs inexistentes/inválidos, que falham antes de qualquer gravação.
