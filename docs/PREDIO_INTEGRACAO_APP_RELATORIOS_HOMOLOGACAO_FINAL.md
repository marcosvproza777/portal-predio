# Integração App Relatórios ↔ Portal Pred.IO — Homologação Final (Etapa 6)

Data: 2026-08-09
Status: **Lógica validada e aprovada. Integração NÃO está no ar ainda — dois bloqueios de infraestrutura impedem uso por cliente real hoje (ver §0).**

Pré-requisitos lidos antes de começar: [Etapa 1](PREDIO_INTEGRACAO_APP_RELATORIOS_ETAPA_1.md) (arquitetura), Etapa 2 (upload direto), Etapa 3 (`integration_api.py` + botão no App), [Etapa 4](PREDIO_INTEGRACAO_DADOS_RELATORIOS_ETAPA_4.md) (dados estruturados), [Etapa 5](PREDIO_INTEGRACAO_RELATORIOS_ETAPA_5.md) (IA/histórico/GUT/Dashboard/Resumo Executivo).

---

## 0. Veredito — pronto para cliente real?

**NÃO ainda**, por dois motivos que não são bugs de código, são infraestrutura fora do meu alcance de corrigir sozinho:

1. **🔴 BLOQUEADOR — Faturamento do projeto GCP desativado.** Ao testar upload de PDF de verdade, a chamada ao Google Cloud Storage falhou com: *"The billing account for the owning project is disabled in state absent"* (projeto `lyrical-oath-400401`). Isso significa que **armazenamento de PDF está fora do ar agora mesmo** — não só para a integração do App Relatórios, mas também para o Upload Direto (Etapa 2) e a Biblioteca Técnica, que usam o mesmo bucket/projeto. Precisa reativar o faturamento no console do Google Cloud antes de liberar qualquer fluxo que dependa de PDF.
2. **🟡 BLOQUEADOR — `integration_api.py` nunca foi implantado.** Desde a Etapa 3, por decisão explícita sua, o serviço ficou só preparado em código — não existe uma URL real rodando no Render, e o App Relatórios ainda tem `PORTAL_INTEGRATIONS_BASE`/`PORTAL_INTEGRATION_TOKEN` como placeholders vazios. Sem isso, o botão "Publicar no Portal Pred.IO" no App não tem pra onde mandar a requisição.

A **lógica em si já foi validada de ponta a ponta** contra o Google Sheets real (ver §2) — criação, atualização sem duplicar, GUT, histórico, indexação para IA, Dashboard, isolamento entre clientes. O que falta é: reativar o faturamento, publicar o serviço, gerar o token, configurar os dois lados, e então fazer **um teste manual real no navegador** (que eu não consegui fazer nesta sessão — ver §7).

---

## 1. Como testei (nota sobre segurança dos dados)

Não existe mais nenhum cliente de teste no Portal (o "Pred.IO Teste" de uma homologação anterior, documentada em `PREDIO_HOMOLOGACAO_CLIENTE_TESTE.md`, foi removido depois daquela sessão). Com sua autorização, criei um novo cliente de teste claramente rotulado:

- **Cliente A**: `Pred.IO Teste Etapa 6` (`pred.io teste etapa 6`) — 2 ativos
- **Cliente B**: `Pred.IO Teste Etapa 6 B` (`pred.io teste etapa 6 b`) — 1 ativo (só para teste de isolamento)

Rodei todo o fluxo contra esses dados reais (Google Sheets de produção, sem staging disponível), e **apaguei tudo ao final** — cliente A, cliente B, os 3 ativos, o relatório publicado, os 4 chunks, o evento de histórico, e as linhas de auditoria geradas pelos testes. Verifiquei a limpeza com consultas depois de apagar (todas retornaram "não encontrado", ver §2.9).

---

## 2. Testes executados e resultados (contra dados reais, depois removidos)

### 2.1 Fluxo completo — criar → Em revisão → publicar → visível ao cliente
`POST /api/integrations/reports` (via `TestClient`, mesmo código que rodaria em produção) criando um relatório de Termografia para o Cliente A: **✅** `Status = "Em revisão"`, `App_Report_Id` gravado, todos os campos estruturados corretos (`Cliente_Id`, `Ativo_Id`, `Titulo`, `Tipo_Servico`, `Severidade`, `Resumo`, `Conclusao`, `Recomendacoes`, `Medicoes_Json`).

Cliente A **não via** o relatório em "Em revisão" (`get_technical_reports(staff=False)` vazio para esse Id) — **✅**.

Publiquei via `sheets.publish_technical_report()` (mesma função que o botão "Publicar" da Supervisão usa): **✅** Status → "Publicado", score do ativo ajustado (-15, coerente com severidade Crítico), evento de histórico criado, indexação para IA disparada automaticamente (`indexado: True`), alerta interno criado (severidade Crítico).

Depois de publicado, Cliente A **via** o relatório; Cliente B **não via nada** — **✅**.

### 2.2 GUT
Enviado G=5, U=4, T=5 (exatamente o exemplo do pedido) → **✅ Gut_Score = 100, Gut_Prioridade = "Crítica"**, recalculado no backend (não confiou em nenhum valor pronto). `acao_recomendada` retornada por `get_gut_summary`: *"Prioridade máxima — solicitar avaliação técnica da equipe Pred.IO o quanto antes."* — **nenhuma menção a overhaul, troca de rolamento, parada ou desmontagem** — **✅**.

Testei também G=9 (fora de 1–5): **✅** rejeitado com `422` antes de qualquer gravação.

### 2.3 Duplicação / atualização pelo mesmo `report_id`
Reenviei o mesmo `report_id` três vezes (1x antes de publicar, 1x depois de publicado com conteúdo alterado):
- **✅** Nunca criou uma segunda linha em `TechnicalReports` (confirmado contando linhas por `App_Report_Id` — sempre 1).
- **✅** Depois de publicado, reenviar **não rebaixou** o Status (continuou "Publicado").
- **✅** Conteúdo atualizado corretamente (título, resumo, recomendações).
- **✅** Chunks reindexados com o conteúdo novo (não duplicaram — continuaram 4, texto atualizado).
- **✅** Evento de histórico **não duplicou** (continuou 1 evento).

### 2.4 Cliente e ativo — isolamento e vínculo
- **✅** Ativo do Cliente B enviado com `cliente_id` do Cliente A → `403 "O ativo informado pertence a outro cliente."`
- **✅** `ativo_id` inexistente → `404` com a mensagem exata pedida: *"O ativo selecionado ainda não está vinculado ao Portal Pred.IO. Cadastre ou vincule o ativo antes de publicar o relatório."*
- **✅** `cliente_id` inexistente → `404 "Cliente não encontrado no Portal Pred.IO."`
- **✅** `get_gut_summary`, histórico do ativo e listagem de relatórios do Cliente B nunca retornaram nada do Cliente A, em nenhum momento do teste.

### 2.5 Autenticação
- **✅** Sem token → `401`. Token errado → `401`. Nenhuma delas vazou o token esperado na resposta de erro.
- **✅** Confirmei no log de auditoria (`AcessoAuditoria`) que a falha de autenticação é registrada **sem o valor do token** — só o resultado ("negado") e um texto fixo.

### 2.6 PDF
- **✅ Estrutura de dados**: `Storage_Path`/`Arquivo_Nome` seguem o padrão privado (`clientes/{cliente}/relatorios/{ativo}/{report}/relatorio.pdf`), nunca URL pública permanente — inalterado desde a Etapa 3.
- **🔴 Upload de verdade falhou** — não por bug, mas porque o faturamento do GCS está desativado (§0). Isso **confirmou** o comportamento esperado em caso de falha: o relatório **não ficou marcado como sincronizado com sucesso** no App — corrigi um bug real para isso (ver §4.1).
- **✅ PDF inválido** (bytes que não começam com `%PDF-`): rejeitado com mensagem clara, relatório continuou existindo com os dados estruturados (não perdeu o relatório), exatamente como pedido.
- Não pude testar visualização/download de um PDF real nem "Cliente A não acessa PDF do Cliente B" nesta sessão, porque nenhum PDF chegou a ser armazenado (bloqueio de faturamento). A lógica de URL assinada de curta duração em si não mudou desde a Etapa 3 (já homologada por leitura de código).

### 2.7 Assistente Técnico / IA
- **✅** Chunks só são criados quando `Status == "Publicado"` — testei chamar a reindexação num relatório inexistente e confirmei que nada é gravado.
- **✅** 4 chunks criados (Ficha técnica, Resumo, Recomendações, Conclusão) — nenhum contém `Obs_Interna`.
- **✅** `get_chunks_relatorio` e `get_technical_reports` usados pelo Assistente (`assistant_engine.py`) sempre exigem `client_id` e sempre forçam `staff=False` (Publicado obrigatório) — confirmado lendo o código, sem regressão.
- Não testei as perguntas ao Assistente literalmente (ex.: "o que o último relatório concluiu") porque isso exige uma sessão de chat real com a chave da Anthropic configurada — validei que os **dados** que essas perguntas consultariam estão corretos e isolados, que é a parte que esta etapa de integração controla.

### 2.8 Dashboard e Resumo Executivo
- **✅** `page_sv_dashboard.py`: o relatório de teste apareceu corretamente em "Relatórios Críticos" (1), "GUT Alto" (1), "Recomendações Geradas", e na lista "Últimos Relatórios Publicados" (no topo, mais recente).
- **🐛 Bug real encontrado e corrigido** no caminho: "Relatórios no Mês" sempre dava errado (ver §4.3).
- **✅** Consulta equivalente ao Resumo Executivo (`get_technical_reports(client_id, ativo_id, staff=False)`) retornou o relatório com todos os campos que `executive_summary.py` usa (diagnóstico, conclusão, recomendações, GUT, data) — sem precisar abrir PDF.

### 2.9 Limpeza confirmada
Depois de apagar tudo, reconsultei cada item: relatório publicado (não encontrado), relatório de teste do PDF inválido (não encontrado), os 3 ativos (não encontrados), o cliente de teste (não aparece mais em `get_all_clientes`), os 4 chunks (nenhum órfão), o evento de histórico (nenhum órfão), a linha de auditoria de teste (removida). Rodei o Dashboard de novo depois da limpeza — voltou ao estado normal, sem erro.

---

## 3. Tipos de relatório

O App Relatórios só tem 3 tipos hoje — **OAT, Termografia e Alinhamento a Laser** (confirmado desde a Etapa 1; não existem tipos separados de "Vibração"/"Visita técnica"/"Óleo" no App — "Visita técnica/comercial" são categorias dentro de um OAT). Testei com um payload no formato de Termografia; o código do lado do Portal (`integration_api.py`) **não depende do tipo** — trata `tipo_relatorio` como texto livre e `medicoes` como um objeto JSON genérico — então o mesmo caminho vale para os 3 tipos reais do App. Não montei um payload de exemplo para cada um dos 3 separadamente nesta sessão; recomendo, no primeiro teste manual real (§7), publicar pelo menos um de cada tipo.

---

## 4. Bugs encontrados e corrigidos nesta etapa

### 4.1 App Relatórios — falha de PDF aparecia como sucesso total
`submitPortalPublish()` marcava `portalSyncStatus` como `'sent'`/`'updated'` mesmo quando o servidor avisava que o PDF falhou (`resp.aviso`). Isso contraria a regra explícita desta homologação ("se upload falhar, relatório não deve aparecer como sincronizado com sucesso"). **Corrigido**: agora, se vier `aviso`, o status fica `'failed'` (com a mensagem de erro do servidor), mesmo que os dados estruturados tenham sido salvos — o técnico vê "🔁 Falhou · Tentar novamente" e sabe que precisa reanexar o PDF.

### 4.2 App Relatórios — botão de envio podia ser clicado várias vezes
O botão "Publicar no Portal Pred.IO" (atrás do modal) já ficava desabilitado durante o envio, mas o botão **"📤 Enviar ao Portal" dentro do próprio modal não tinha essa proteção** — cliques rápidos podiam disparar duas requisições em paralelo. **Corrigido**: trava de "em andamento" (`_portalPublishInFlight`) independente do estado da tela, mais o botão do modal desabilitado com texto "⏳ Enviando…" durante a chamada.

### 4.3 Portal — "Relatórios no Mês" sempre errado (bug pré-existente, não introduzido por este projeto)
`page_sv_dashboard.py` comparava os 5 primeiros caracteres de `Data_Relatorio` (formato `DD/MM/YYYY`) direto contra o mês atual no formato `YYYY-MM` — nunca podiam bater. O card "Relatórios no Mês" do Dashboard da Supervisão estava efetivamente sempre errado, provavelmente desde que foi criado (não faz parte das Etapas 1–5 deste projeto de integração). **Corrigido**: agora faz o parse de verdade da data antes de comparar.

### 4.4 Portal — integração sem nenhum log de auditoria
`integration_api.py` não registrava nada — nenhuma visibilidade de quem publicou o quê, nem de falhas de autenticação. **Corrigido**: reaproveitei `security.log_acesso()` (mesma aba `AcessoAuditoria` usada pelo resto do Portal, nada duplicado) para registrar autenticação negada, cliente/ativo inválido, e o resultado de cada publicação/atualização — nunca o token em si, confirmado por teste (§2.5).

---

## 5. Segurança — checklist final

| Item | Status |
|---|---|
| Secrets fora do front-end | ✅ — token do App é o único segredo do lado cliente; nunca abre acesso a Sheets/GCS diretamente |
| Integração autenticada | ✅ — Bearer token, comparação em tempo constante |
| `cliente_id` validado no backend | ✅ — nunca aceito sem checar contra `get_all_clientes()` |
| Ativo pertence ao cliente | ✅ — checado antes de qualquer gravação, com mensagens específicas |
| PDF privado | ✅ (estrutural — não pôde ser testado de ponta a ponta por causa do bloqueio de faturamento) |
| Rascunho/Em revisão protegidos | ✅ — nunca aparecem para cliente nem entram na IA |
| Chunks protegidos | ✅ — nunca renderizados diretamente para o cliente em nenhuma tela |
| Observações internas protegidas | ✅ — nunca aparecem em chunk, timeline ou resposta da API |
| Cliente A isolado do Cliente B | ✅ — testado em relatórios, GUT, histórico, listagem |
| Logs nunca guardam senha/token completo/chave privada | ✅ — confirmado por teste |

---

## 6. Checks de código

Sem lint/typecheck/build formal configurado (mesma situação de todas as etapas anteriores). `py_compile` + import real de todos os módulos Python tocados (`sheets.py`, `integration_api.py`, `page_sv_relatorios.py`, `page_relatorios.py`, `page_sv_dashboard.py`, `security.py`, `drive_storage.py`) — todos OK. JavaScript do App Relatórios extraído do HTML (322KB) e validado com `node --check` — sem erro de sintaxe.

---

## 7. Pendências antes de liberar para cliente real

1. **Reativar o faturamento do projeto GCP** (`lyrical-oath-400401`) — bloqueia todo upload de PDF (App Relatórios, Upload Direto, Biblioteca Técnica).
2. **Implantar `integration_api.py`** como segundo serviço no Render (`render.yaml` já preparado desde a Etapa 3) e gerar o `INTEGRATION_API_TOKEN`.
3. **Configurar `PORTAL_INTEGRATIONS_BASE`/`PORTAL_INTEGRATION_TOKEN`** no App Relatórios com os valores reais, e reimplantar o App (Cloudflare).
4. **Um teste manual real, no navegador**, depois dos 3 itens acima: criar e publicar pelo menos um relatório de cada tipo (OAT, Termografia, Laser), confirmar visualmente que o PDF sobe e abre, e rodar as perguntas do Assistente Técnico listadas no pedido original. Esta sessão validou toda a lógica de backend, mas não substitui um clique real de ponta a ponta.
5. **Duplicatas conhecidas em dados de clientes reais**, sinalizadas na homologação anterior (`PREDIO_HOMOLOGACAO_CLIENTE_TESTE.md` §8.2) e nunca confirmadas com os clientes — não é deste projeto, mas ainda pendente.

---

## 8. Riscos residuais

- **Concorrência real entre duas requisições simultâneas para o mesmo `report_id`** (ex.: duas abas do navegador, ou um retry automático colidindo com um clique manual) não foi testada sob carga — o Google Sheets não tem trava de linha nativa, então uma corrida genuína entre dois requests ao mesmo tempo poderia, em teoria, criar duas linhas antes de qualquer um deles terminar de escrever. É uma limitação inerente de usar Planilhas como banco, não um bug introduzido aqui; a trava de duplo-clique do App (§4.2) cobre o caso mais comum (usuário impaciente), mas não uma corrida entre dois processos diferentes.
- PDF, especificamente, não pôde ser validado de ponta a ponta (upload real, visualização, isolamento de arquivo entre clientes) por causa do bloqueio de faturamento — recomendo repetir esses testes específicos assim que o GCS voltar a funcionar.
