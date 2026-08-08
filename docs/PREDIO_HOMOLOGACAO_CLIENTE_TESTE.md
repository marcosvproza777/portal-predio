# Homologação com Cliente Teste — Etapa 10

> Data: 2026-08-08 | Cliente teste: Pred.IO Teste (`pred.io teste`) | Cliente isolamento: Pred.IO Teste B (`pred.io teste b`)

## 0. Resumo executivo

Esta etapa deveria ser, em essência, rodar o checklist de homologação já existente (`homologacao_setup.py` + `page_sv_homologacao.py`, construídos na Etapa 6) contra o portal. Na prática, ao tentar popular e validar os dados de teste, **três bugs de produção reais e sérios foram descobertos e corrigidos** — o mais grave deles (corrupção estrutural na aba `Ativos`) afetava **todos os clientes reais**, não só dados de teste, e provavelmente já fazia a tela "Meus Equipamentos" aparecer vazia para RJR, Vigor Alimentos e qualquer outro cliente há semanas. Ver §3 para detalhes técnicos completos.

**Veredito de pronto-para-produção: NÃO ainda** — não porque o GUT/mobile/assistente tenham problemas novos, mas porque a infraestrutura de dados (Google Sheets) tinha corrupção pré-existente que só foi descoberta ao tentar popular dados reais nesta etapa. Os bugs encontrados foram corrigidos e verificados, mas seu impacto histórico (há quanto tempo estava quebrado, quantos clientes afetados) não pôde ser totalmente dimensionado nesta sessão. Ver §8.

## 1. Cliente de teste

Já existia infraestrutura completa para isso (`homologacao_setup.py`, tela "🔬 Homologação" na Supervisão) — não foi recriada do zero, apenas executada e estendida.

- **Cliente A** (principal): Pred.IO Teste — `pred.io teste` — login `cliente.teste@predio.io`
- **Cliente B** (isolamento): Pred.IO Teste B — `pred.io teste b` — login `cliente.teste.b@predio.io`
- **Staff de teste**: `supervisor.teste@predio.io`

## 2. Dados criados

| Categoria | Criado | Detalhe |
|---|---|---|
| Ativos (Cliente A) | 3 | MYCOM Compressor Q63 (Atenção, 72), Motor Principal 75kW (Atenção, 68), Bomba de Óleo Industrial (Bom, 88) |
| Ativo (Cliente B) | 1 | Compressor Teste Isolamento (Bom, 75) — só para teste de isolamento |
| Relatórios | 4 | 3 Publicados (Vibração, Óleo, Preventiva) + 1 Rascunho (invisível ao cliente) |
| Manutenção | 6 | 2 Calendário, 2 Horímetro (1 vencida com GUT Crítica), 2 Condição/preditiva (1 com GUT Baixa) |
| Alertas | 3 | Crítica (MYCOM temperatura, GUT Alta), Alta (vibração motor), Média (óleo bomba) |
| Chamados | 3 | Respondido + observação interna (GUT Moderada), Aberto sem resposta, Em análise |
| Biblioteca | 3 (+3 pré-existentes) | 1 vinculado ao cliente (não indexado), 1 vinculado indexado, 1 **interno Pred.IO** (nunca visível a cliente) |
| GUT | 4 itens com score explícito | Crítica (manutenção, 100), Alta (alerta, 80), Moderada (chamado, 36), Baixa (manutenção por condição, 12) |

### Não implementado, com motivo

- **Manutenção "Concluída"**: a função que calcula o status de uma tarefa (`sheets._task_status`) só retorna `Vencida`/`Próxima do vencimento`/`Em dia`/`Depende de análise preditiva` — não existe um estado "Concluída" derivado de execução no modelo atual (provavelmente dependeria de um registro em `MaintenanceExecutions`, não investigado a fundo). Não forcei um dado artificial para simular um status que o próprio motor de cálculo não produz.
- **Alerta "Resolvido"**: `AlertasSV` não tem campo de status/ciclo-de-vida — só `Prioridade` (Crítica/Alta/Média/Baixa), a mesma limitação já documentada na Etapa 8. Não modelado.

## 3. Bugs de produção encontrados e corrigidos

### 3.1 — CRÍTICO: corrupção estrutural na aba `Ativos` (afetava todos os clientes)

Ao popular dados de teste, `sheets.load_sheet("Ativos")` retornava sempre vazio. Investigação revelou que **100% das 47 linhas de dados** da aba tinham seus valores gravados em blocos de colunas muito distantes das colunas nomeadas do cabeçalho (a partir da coluna ~280 em vez da coluna A), num padrão de "escada" — cada linha nova começando um pouco mais à direita que a anterior. Isso quebrava a leitura padrão do app (`get_all_records()` falhava com "header row contains duplicates") para **qualquer cliente**, não só o de teste — incluindo dados reais de **RJR** e **Vigor Alimentos**.

**Causa raiz** (ver §3.3): `sheets.append_row()` usava `gspread`'s `append_row()` sem limitar o intervalo de colunas considerado, então em abas com colunas fantasmas à direita (cabeçalho historicamente mal gerenciado), a API do Google Sheets "descobria" uma tabela muito mais larga que o conteúdo real e inseria cada linha nova deslocada.

**Correção aplicada**: com autorização explícita do usuário e backup completo salvo antes de qualquer alteração (`backups/ativos_backup_20260807_2303.json`), a aba foi realinhada — cada linha teve seu bloco de dados (sempre intacto e na ordem correta, só deslocado) reescrito nas colunas corretas A:V, as ~1164 colunas fantasmas foram removidas, e uma linha órfã sem Id foi descartada. **Nenhum dado de cliente real foi perdido** — RJR e Vigor Alimentos foram realinhados, não apagados. Duplicatas geradas pelas minhas próprias tentativas de setup (mesmo ativo criado 3x por falha de leitura em cadeia) foram removidas; **duplicatas que já existiam antes desta sessão em dados de clientes reais (RJR, Vigor Alimentos, uma conta interna "Pred.IO") foram deixadas intactas e apenas sinalizadas** — não tenho contexto de negócio para decidir sozinho quais são intencionais.

Verificado após o reparo: `sheets.get_all_ativos_sv()` retorna corretamente todos os clientes; dashboard e tela de Ativos testados no navegador mostrando os 3 ativos do Cliente A corretamente.

### 3.2 — Corrupção equivalente em `Chamados`

O mesmo padrão de "escada" apareceu em `Chamados` ao criar os chamados de teste — consequência do mesmo bug de causa raiz (§3.3), não de uma corrupção pré-existente separada (a aba tinha poucochamados). Adicionalmente, `abrir_chamado_v2()` gravava valores numa ordem posicional fixa (`_HEADERS_CHAMADOS_V2`) que **não bate com a ordem real do cabeçalho da planilha** (que é legado, com as colunas V2 anexadas ao final por `_ensure_chamados_v2_cols()`), causando desalinhamento campo-a-campo mesmo sem o efeito "escada".

**Correção**: `abrir_chamado_v2()` agora monta um dicionário campo→valor e grava na ordem real do cabeçalho lido da planilha (`ws.row_values(1)`), em vez de uma lista posicional fixa — mesmo padrão já usado por `update_chamado()`. As 3 linhas de teste corrompidas foram apagadas e recriadas corretamente após a correção.

### 3.3 — Causa raiz comum: `sheets.append_row()` sem limite de colunas

```python
# Antes
ws.append_row(values, value_input_option="USER_ENTERED")
# Depois
last_col = gspread.utils.rowcol_to_a1(1, len(values)).rstrip("0123456789")
ws.append_row(values, value_input_option="USER_ENTERED", table_range=f"A1:{last_col}1")
```

Esta é a correção de maior alcance desta etapa: `append_row()` é usado por praticamente toda função de criação no `sheets.py`. Sem o `table_range` explícito, a API do Google Sheets podia "descobrir" uma tabela muito mais larga que o conteúdo real em abas com histórico de colunas fantasmas, deslocando novas linhas para a direita — o mesmo mecanismo por trás dos bugs em Ativos e Chamados. Com o limite explícito, cada escrita fica restrita exatamente à largura dos dados que está gravando, protegendo **todas as abas do sistema**, não só as duas que apresentaram sintomas visíveis nesta sessão.

Validado empiricamente: após a correção, os 3 novos chamados de teste foram criados e leem corretamente (`shape (3, 27)`, `Id`/`Empresa`/`Client_Id`/`Titulo`/`Status` todos na coluna certa); os 3 alertas de teste (criados numa aba nova, sem bloat prévio) também vieram corretos, confirmando que o problema era mesmo o bloat de colunas acumulado, não a lógica em si.

### 3.4 — Bug de renderização: HTML vazando nos cards de Ativos/Faróis

Detalhado em `docs/PREDIO_MOBILE_PWA.md` §4 — corrigido em `page_ativos.py` e `page_farois.py`.

### 3.5 — Bug real no Assistente Técnico: intenção genérica demais sequestrando perguntas específicas

Ao testar as 10 perguntas de homologação, `detect_intent()` classificava "Tenho algum alerta crítico agora?", "Qual o status do meu chamado...", e "Como ativo as notificações..." todas como `status_ativo` — porque esse intent tem palavras-chave muito genéricas (`"status"`, `"crítico"`, `"motor"`, `"compressor"`, `"ativo"`) e era checado **antes** de `chamados`/`alertas`/`notificacoes_portal` na ordem de prioridade.

**Correção**: reordenado para checar `chamados`, `notificacoes_portal` e `alertas` antes de `status_ativo`. Validado sem regressão nos 3 scripts de teste acumulados das Etapas 6-8 (GUT no Assistente). Também adicionado um intent `identidade` (não existia nenhum) para "Quem é você?" — pergunta explicitamente exigida no checklist de homologação, que antes caía em "não encontrado".

**Limitação conhecida, não corrigida**: `get_client_context()` — o motor que monta o contexto do Assistente — inicia sempre com dados **mock** (`assistant_mock_data.get_mock_context`) e só substitui por dados reais os campos de relatórios, manutenção, chamados (`chamados_reais`) e alertas (`alertas_reais`). O campo `ctx["ativos"]` **nunca é substituído pelos ativos reais do cliente** — isso já está documentado no próprio docstring da função como item "Futuramente". Por isso, perguntas sobre ativos específicos por nome (ex.: "explique o score 68 do Motor Principal") ainda respondem com dados de exemplo genéricos ("Unidade Compressora Parafuso 200 VLD") em vez dos ativos reais do cliente. Não tentei essa integração nesta etapa — é uma mudança de arquitetura maior (não um bug pontual) e arriscada de fazer com pressa num sistema que já tem cuidado extra de segurança/isolamento por cliente. Recomendo como próxima etapa dedicada.

## 4. Testes de segurança (dados reais, não mock)

Script isolado (`test_isolamento_real.py`) rodado contra o Google Sheets real, Cliente A vs Cliente B:

| Teste | Resultado |
|---|---|
| Ativos — A vê 3, B vê 1, sem mistura de `Client_Id` | ✅ |
| Manutenção — A vê 6 tarefas, B vê 0 | ✅ |
| Chamados — A vê 3, B vê 0 | ✅ |
| Alertas — A vê 3, B vê 0 | ✅ |
| Relatórios — cliente vê só os 3 Publicados; Rascunho não aparece | ✅ |
| Biblioteca — documento interno Pred.IO não aparece; `Observacoes_Internas` removido da resposta | ✅ |
| GUT summary — isolado por cliente, nenhum item cruzado | ✅ |
| Assistente — Cliente B não recebe dado de ativo do Cliente A | ✅ |

`cliente_id` confirmado como vindo sempre de sessão/parâmetro explícito nas funções testadas — nenhuma leitura de front-end encontrada nesta varredura.

## 5. Testes do GUT

Cálculo confirmado (já validado em testes isolados das Etapas 6-8, `calculate_gut`): G=5,U=4,T=5 → 100 Crítica; G=2,U=2,T=3 → 12 Baixa. Nos dados de teste desta etapa, os 4 itens com GUT explícito (§2) confirmam visualmente a integração: dashboard, ativo e manutenção mostram a prioridade corretamente (validado via `sheets.get_gut_summary` e no navegador). Nenhuma ação automática de overhaul/troca de rolamento/parada foi gerada em nenhum ponto testado. Disclaimer "GUT é uma ferramenta de priorização e não substitui a avaliação técnica da equipe Pred.IO." presente nas respostas do Assistente sobre GUT.

## 6. Testes do Assistente Técnico (10 perguntas)

Script isolado (`test_assistente_homolog.py`) usando `assistant_engine.query_assistant()` real (não mock) contra o Cliente A:

| # | Pergunta | Resultado |
|---|---|---|
| 1 | Ativos em atenção | ⚠️ responde com dado de exemplo genérico, não os ativos reais (ver §3.5) |
| 2 | Último relatório | ✅ cita os relatórios reais publicados |
| 3 | Manutenções próximas do vencimento | ✅ cita a tarefa vencida real |
| 4 | Alerta crítico agora | ✅ corrigido nesta etapa — cita os 3 alertas reais |
| 5 | Status do chamado sobre ruído | ✅ corrigido nesta etapa — cita o chamado real e status correto |
| 6 | Explicar score 68 do Motor Principal | ⚠️ mesma limitação do item 1 |
| 7 | Documento técnico do MYCOM Q63 | ✅ encontra o manual na Biblioteca |
| 8 | Óleo do MYCOM Q63 | ✅ responde com base no manual |
| 9 | Notificações por e-mail | ⚠️ mesma limitação do item 1 (intent correto seria um específico de notificação, mas a frase não bate com as palavras-chave existentes) |
| 10 | Quem é você? | ✅ corrigido nesta etapa — identifica-se como Assistente Técnico Pred.IO, nunca menciona Claude/IA genérica |

Guardrails confirmados em todas as 10 respostas: nenhuma menciona overhaul/troca de rolamento/parada automática.

## 7. Mobile/PWA

Ver `docs/PREDIO_MOBILE_PWA.md` (Etapa 9) — testado em conjunto com esta etapa, usando o mesmo cliente de teste.

## 8. Pendências antes de cliente real

1. **Auditar o histórico da corrupção em Ativos/Chamados**: não sei há quanto tempo a tela de Ativos estava efetivamente quebrada para RJR e Vigor Alimentos, nem se eles reportaram isso. Vale confirmar com esses clientes se perceberam o problema.
2. **Revisar duplicatas reais sinalizadas, não apagadas**: RJR tem ~15 linhas com tag `CP S1`/`cp-s1` repetida, Vigor Alimentos tem 5 linhas `CP NH3` quase idênticas — parecem duplicatas acidentais (mesmo padrão do bug desta sessão, mas de uso real anterior), mas só quem conhece os clientes pode confirmar.
3. **Assistente não usa ativos reais no contexto** (§3.5) — funcional mas com respostas genéricas para perguntas específicas sobre um ativo nomeado.
4. **Teste mobile em dispositivo físico** — não foi possível nesta sessão (ver `PREDIO_MOBILE_PWA.md` §9).
5. **Checklist interativo de 20 itens** já existente na Supervisão (`🔬 Homologação → ✅ Checklist`) ainda não foi preenchido por um humano — os itens verificáveis por código/script foram confirmados aqui, mas os itens de julgamento visual ("layout bonito", "fácil de usar") dependem de um humano realmente navegando.

## 9. Checks técnicos

Sem lint/typecheck/build formal configurado (mesma situação de todas as etapas). `py -m py_compile *.py` limpo na raiz do projeto após todas as correções. Backup da aba Ativos salvo em `backups/ativos_backup_20260807_2303.json` antes do reparo.

## 10. Confirmações pedidas

- Não foi criada sidebar.
- WhatsApp e e-mail não foram tocados.
- `client_id` continua vindo exclusivamente da sessão — nenhuma mudança nessa regra; os bugs corrigidos eram de alinhamento de colunas na planilha, não de lógica de autorização.
- Login e permissões não foram alterados.

## 11. Arquivos alterados

`sheets.py` (`append_row`, `abrir_chamado_v2`), `assistant_engine.py` (reordenação de intents + novo intent `identidade`), `page_ativos.py`, `page_farois.py` (bug de HTML — ver `PREDIO_MOBILE_PWA.md`), `homologacao_setup.py` (comentário de documentação, sem mudança funcional).

## 12. Arquivos criados

`docs/PREDIO_HOMOLOGACAO_CLIENTE_TESTE.md`, `docs/PREDIO_MOBILE_PWA.md`, `backups/ativos_backup_20260807_2303.json`.

## 13. Confirmação final: pronto para cliente real?

**Não ainda.** As correções desta etapa foram necessárias e críticas (a tela de Ativos estava efetivamente inutilizável para clientes reais), mas descobrir e corrigir 3 bugs de infraestrutura de dados no meio de uma etapa de homologação significa que a homologação "normal" (visual, fluxos, checklist humano de 20 itens) ainda não foi completada. Recomendo: (1) revisar as pendências do §8, (2) um humano rodar o checklist interativo da Supervisão navegando de verdade pelo portal, (3) só então liberar.
