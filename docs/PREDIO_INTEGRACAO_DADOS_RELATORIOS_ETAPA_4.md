# Integração App Relatórios ↔ Portal Pred.IO — Etapa 4 (Dados Estruturados + PDF + Vínculo Cliente/Ativo)

Data: 2026-08-08
Status: Implementado sobre a base da Etapa 2 (upload direto) e Etapa 3 (publicação do App via `integration_api.py`). Nenhuma migração destrutiva — todas as colunas novas são aditivas.

Pré-requisitos: [Etapa 1](PREDIO_INTEGRACAO_APP_RELATORIOS_ETAPA_1.md) (arquitetura), Etapa 2 (upload direto no Portal), Etapa 3 (`integration_api.py`, botão "Publicar no Portal Pred.IO" no App).

---

## 1. O que mudou nesta etapa

A Etapa 3 já enviava dados estruturados (não só PDF) — a Etapa 4 fechou três lacunas reais encontradas ao revisar esse fluxo:

1. **GUT podia ser aceito "pronto" sem recálculo.** `integration_api.py` tinha um caminho que aceitava `gut_score`/`gut_prioridade` direto, sem as notas G/U/T, violando a regra "nunca confiar só no valor recebido". Removido — GUT só é gravado quando as 3 notas (1–5) vêm juntas, e `gut.calculate_gut()` sempre recalcula score/prioridade no backend. Notas fora de 1–5 agora retornam erro 422 explícito.
2. **Histórico do ativo não trazia resumo/recomendação.** O evento de timeline criado ao publicar (`publish_technical_report` em `sheets.py`) só citava tipo/título/equipamento. Agora inclui severidade, um trecho do resumo e da recomendação — sem nunca inserir o PDF inteiro.
3. **Vínculo cliente/ativo era só um cache temporário.** Na Etapa 3, a escolha de cliente/ativo do Portal ficava só num cache local (`localStorage`) por equipamento. Nesta etapa, o vínculo passou a ser **salvo no próprio cadastro** do cliente e do equipamento no App (`portalClienteId`, `portalAtivoId`), com telas dedicadas para vincular, e é atualizado automaticamente a cada publicação bem-sucedida.

---

## 2. Campos enviados pelo App (modelo estruturado)

Endpoint: `POST /api/integrations/reports` (`integration_api.py`), multipart/form-data com um campo `payload` (JSON) e um campo `pdf` (arquivo, opcional).

| Campo no payload do App | Equivalente pedido na Etapa 4 | Coluna no Portal (`TechnicalReports`) |
|---|---|---|
| `report_id` | `external_report_id` | `App_Report_Id` (chave de idempotência) |
| `cliente_id` | `cliente_id` | `Cliente_Id` |
| `ativo_id` | `ativo_id` | `Ativo_Id` |
| `titulo` | `titulo` | `Titulo` |
| `tipo_relatorio` | `tipo_relatorio` | `Tipo_Servico` |
| `data_relatorio` | `data_relatorio` | `Data_Relatorio` |
| `tecnico` | `tecnico` | `Tecnico` |
| `severidade` | `severidade` | `Severidade` |
| `resumo` | `diagnostico` | `Resumo` |
| `conclusao` | `conclusao` | `Conclusao` |
| `recomendacoes` | `recomendacoes` | `Recomendacoes` |
| `medicoes` (objeto/JSON livre) | medições técnicas | `Medicoes_Json` (string JSON, truncada em ~45.000 caracteres) |
| `gut_gravidade`/`urgencia`/`tendencia` | `gut_gravidade/urgencia/tendencia` | `Gut_Gravidade/Urgencia/Tendencia` |
| — (calculado no backend) | `gut_score`/`gut_prioridade` | `Gut_Score`/`Gut_Prioridade` |
| arquivo `pdf` (opcional) | PDF oficial | `Storage_Path` + `Arquivo_Nome` |
| — (fixo no servidor) | `origem` | `Origem = "app_relatorios"` |
| — (fixo no servidor) | `status` | `Status = "Em revisão"` na criação; preservado em atualizações |
| — (fixo no servidor) | `synced_at` | `Sincronizado_Em` |
| — (já existentes) | `created_at`/`updated_at` | `Created_At`/`Updated_At` |

Campos do pedido original sem equivalente **porque não existem no App** (não inventados, conforme instrução de não criar estrutura que o App não tem):
- **`observacoes_visiveis_cliente`** — o App não distingue esse campo de `Resumo`/`Conclusão`/`Recomendações`, que já são todos visíveis ao cliente. Nenhum campo novo criado.
- **`gut_score`/`gut_prioridade` enviados prontos** — nunca aceitos diretamente (ver §1.1); só existem como saída do cálculo do backend.

---

## 3. Medições técnicas — mapeamento real (não genérico)

O App Relatórios tem **3 tipos de relatório** (confirmado na Etapa 1): OAT, Termografia (`termo`) e Alinhamento a Laser (`laser`) — não existem tipos separados de "Vibração" ou "Óleo" hoje. Em vez de inventar uma estrutura nova, o campo `medicoes` do payload é o **objeto `current.data` inteiro do relatório**, ou seja, exatamente os dados que o App já registra por tipo:

- **Termografia (`termo`)**: `equip[]` — pontos inspecionados, com temperatura medida, temperatura de referência, ΔT e severidade por ponto (campos já existentes no formulário do App); mais `situacao` (semáforo geral), `conclusao`, `recomendacao`.
- **OAT (`oat`)**: `equip[]` — linhas de equipamento/serviço executado, categorias de serviço (`serviceCategories`), dias de trabalho.
- **Alinhamento a laser (`laser`)**: medições de desalinhamento angular/paralelo antes-depois, TAG, acoplamento.

Isso fica gravado em `Medicoes_Json` como está — não fica bonito para leitura direta na planilha, mas fica **disponível e estruturado** para o Dashboard/IA/Resumo Executivo consultarem via `json.loads()`, sem precisar abrir o PDF.

---

## 4. Cliente e Ativo — como o vínculo funciona agora

### 4.1 Na hora de publicar (já existia desde a Etapa 3)
O modal "Publicar no Portal Pred.IO" só lista clientes/ativos que **realmente existem no Portal** (via `GET /api/integrations/clientes` e `GET /api/integrations/ativos`) — nunca é possível digitar um ID à mão.

### 4.2 Vínculo persistente no cadastro (novo — Etapa 4)
Agora o cadastro de cliente e de equipamento no App tem uma seção **"🔗 Vínculo com o Portal Pred.IO"**:
- Tela do cliente: seletor "Cliente no Portal", carregado sob demanda (botão "Carregar clientes do Portal"). Salvo como `portalClienteId`/`portalClienteLabel` no registro do cliente (IndexedDB).
- Tela do equipamento: seletor "Ativo no Portal", só carrega depois que o cliente já estiver vinculado (mostra aviso se não estiver). Salvo como `portalAtivoId`/`portalAtivoLabel` no registro do equipamento.

Ao abrir "Publicar no Portal", a ordem de resolução é:
1. Vínculo do cadastro do equipamento/cliente (`resolvePortalLinkForCurrentReport()`), se o relatório tiver `equipmentSnapshot`.
2. Cache local por equipamento da Etapa 3 (mantido por compatibilidade).
3. Nenhum vínculo conhecido → App mostra: **"Cliente ou ativo ainda não está vinculado ao Portal Pred.IO. Selecione abaixo."** — não bloqueia a publicação (o técnico escolhe manualmente), só avisa.

Toda publicação bem-sucedida **grava de volta** a escolha feita no modal no cadastro do equipamento/cliente — da próxima vez já vem pré-selecionado, sem duplicar vínculo.

### 4.3 Validação no backend (nunca só por nome)
`integration_api.py`:
- Cliente precisa existir na lista real do Portal (`sheets.get_all_clientes()`).
- Ativo precisa existir (`sheets.get_ativo_by_id`) — se não existir, retorna 404 com a mensagem exata pedida: *"O ativo selecionado ainda não está vinculado ao Portal Pred.IO. Cadastre ou vincule o ativo antes de publicar o relatório."*
- Ativo precisa pertencer ao cliente informado (`sheets.ativo_pertence_cliente`, mesma função usada pelo Upload Direto da Etapa 2 — nenhuma lógica duplicada) — senão, 403.
- Relatório incompleto (sem `resumo`, sem `cliente_id`, sem `ativo_id`) nunca é aceito — 422 antes de qualquer gravação.

---

## 5. PDF

Sem mudança de mecanismo desde a Etapa 3 — continua privado:
- Enviado como parte do mesmo `multipart/form-data` da publicação (campo `pdf`, opcional).
- Sobe para o storage privado do GCS via `drive_storage.upload_report_pdf()` (mesma função da Etapa 2), caminho `clientes/{cliente_id}/relatorios/{ativo_id}/{report_id}/relatorio.pdf`.
- Nunca gera URL pública permanente — visualização usa `get_report_pdf_url()` (assinada, 30 min).
- **Limitação conhecida, documentada na Etapa 3**: o App gera PDF via impressão nativa do navegador, que não expõe o arquivo para envio automático via script. O técnico anexa manualmente o PDF já salvo, no mesmo modal de publicação. O PDF continua sendo o documento oficial; os dados estruturados não dependem dele.

---

## 6. Criação/atualização e como duplicação é evitada

Chave de integração: `App_Report_Id` = `report_id` do App (imutável, gerado uma vez por relatório).

- `sheets.get_technical_report_by_app_id(report_id)` busca por esse campo antes de qualquer gravação.
- **Encontrado** → `update_technical_report()` atualiza título/tipo/data/técnico/severidade/resumo/conclusão/recomendações/medições/GUT/PDF. **Nunca mexe no `Status`** — se já foi publicado ou arquivado pela equipe, reenviar do App não republica nem rebaixa sozinho.
- **Não encontrado** → `add_technical_report()` cria com `Status = "Em revisão"`.
- Reenviar o mesmo `report_id` nunca cria uma segunda linha.

---

## 7. Histórico do ativo

Sem endpoint novo — `publish_technical_report()` (chamado pela Supervisão ao publicar, igual para relatórios de qualquer origem) já cria o evento em `ReportTimeline` automaticamente. Nesta etapa, a descrição do evento passou a incluir:

```
{Tipo de Serviço} — {Título}. Severidade: {Severidade}. Equipamento: {Equipamento}.
Score impactado em {delta} pontos. Resumo: {trecho do resumo, até 220 caracteres}.
Recomendação: {trecho da recomendação, até 220 caracteres}.
```

PDF nunca entra no histórico — só o texto acima. Reenvio do mesmo relatório não duplica o evento (publicação só acontece uma vez; reenviar do App só atualiza o conteúdo do relatório, não re-executa a publicação).

---

## 8. Preparação para GUT

- Se o App enviar as 3 notas (1–5), o Portal recalcula score/prioridade (nunca aceita valor pronto) e grava.
- Se o App não enviar GUT, os campos ficam em branco — a Supervisão continua podendo definir depois (`update_report_gut`, já existente desde a Etapa 2).
- Não foi inventado nenhum valor de GUT nesta etapa.

## 9. Preparação para Dashboard

Nenhum gráfico foi criado (fora do escopo desta etapa). O que já é possível hoje, sem código novo, porque os relatórios do App usam exatamente a mesma aba/função que qualquer relatório do Portal:

```python
sheets.get_technical_reports(client_id=..., status=..., ativo_id=..., staff=True)
```

retorna um DataFrame com `Cliente_Id`, `Ativo_Id`, `Data_Relatorio`, `Tipo_Servico`, `Severidade`, `Gut_Prioridade`, `Status`, `Origem` — todas as dimensões pedidas já são colunas prontas para filtrar/agrupar.

## 10. Preparação para o Resumo Executivo

Já funciona sem mudança — `executive_summary.py` já lê via `get_technical_reports()`, então relatórios publicados pelo App aparecem automaticamente com `Resumo`, `Conclusao`, `Recomendacoes`, `Severidade`, GUT, `Data_Relatorio`, `Ativo_Id`, `Tipo_Servico` — sem precisar ler o PDF.

## 11. Preparação para o Assistente Técnico

`index_relatorio_tecnico()` (aba `TechnicalReportChunks`) já roda automaticamente na publicação de qualquer relatório técnico (independente da origem), criando chunks de Resumo, Recomendações e Conclusão. Relatórios do App entram nesse índice do mesmo jeito. Nenhuma lógica de busca/resposta do Assistente foi implementada nesta etapa — só os dados ficaram disponíveis para uma indexação/consulta futura.

---

## 12. Segurança

- Toda rota de integração exige `Authorization: Bearer <INTEGRATION_API_TOKEN>`.
- `cliente_id`/`ativo_id` sempre revalidados no backend, nunca só pelo que o front-end (App) mandou.
- PDF fica em storage privado, nunca com URL pública permanente.
- Cliente só vê relatórios com `Status == "Publicado"` — "Em revisão" e "Rascunho" continuam só internos (`get_technical_reports(staff=False)`, inalterado).
- `storage_path` bruto nunca é exibido em nenhuma tela — só usado internamente para gerar a URL assinada.
- Cliente A nunca recebe dado do Cliente B — mesma garantia de `Cliente_Id` da sessão usada em todo o Portal.

---

## 13. Nota sobre testes

Os testes de leitura (autenticação, listagem de clientes/ativos, validações 401/404/422/403) foram executados contra o Portal de produção **sem gravar nada**. Um teste de criação foi rodado por engano contra dados reais durante o desenvolvimento desta etapa — o relatório de teste (`REP-20260808-FD2D0D`, cliente "vigor alimentos") foi identificado e removido imediatamente após a criação, confirmado via `get_technical_report_by_id()` retornando `None`. Nenhum outro teste de escrita foi executado.
