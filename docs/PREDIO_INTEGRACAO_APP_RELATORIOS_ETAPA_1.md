# Integração App Relatórios ↔ Portal Pred.IO — Etapa 1 (Mapeamento e Arquitetura)

Data: 2026-08-08
Status: Análise concluída. Nenhuma implementação, migração ou alteração de dados foi feita nesta etapa.

Projetos analisados:
- **App Relatórios**: `PROJETOS PRED.IO/app relatórios/Pred.IO app relatorios.html` — SPA single-file (HTML+JS vanilla), sem build, sem framework.
- **Portal Pred.IO**: `PROJETOS PRED.IO/portal-predio/` — aplicação Streamlit (Python).

---

## 1. Arquitetura de cada sistema

### App Relatórios

| Item | Detalhe |
|---|---|
| Framework | Nenhum — HTML/JS vanilla, single-file, SDK Firebase via CDN (compat v10.12.2) |
| Autenticação | Firebase Auth **anônimo** (`signInAnonymously()`, linha 1445). Não existe login/senha de app — apenas um "perfil" (nome/e-mail do técnico) salvo em `localStorage` para preencher relatórios, sem função de credencial |
| Banco | **Firestore**, projeto `predio-despesas` (mesmo projeto Firebase usado pelo app de despesas — projeto compartilhado, mas coleções próprias) |
| Storage | Nenhum — **Firebase Storage não é usado** (script nem é carregado; seria plano pago). Todo binário (fotos, assinaturas, logos) é embutido como base64 dentro do próprio documento |
| Persistência principal | **IndexedDB local** (`predio_reports`, v3) — é a fonte de verdade real do app; Firestore é só sincronização entre dispositivos |
| Clientes | Guardados em IndexedDB (`clients` store), cadastro manual pelo técnico. Sem CNPJ |
| Ativos | Guardados em IndexedDB (`equipments` store), com FK real `clientId` |
| Relatórios | 3 tipos apenas: OAT, Termografia, Alinhamento a Laser. "Visita técnica/comercial" são categorias dentro de um OAT, não tipos próprios |
| PDF | Não há biblioteca de PDF — usa `window.print()` nativo do navegador sobre uma view HTML de impressão. Saída é local (download/impressão), nunca enviada a lugar nenhum |
| Numeração | Provisória offline (`PRED-OS-{ano}-PEND-xxxxxx`), promovida a oficial (`PRED-OS-{ano}-0001`) via transação Firestore idempotente quando online |
| Finalização | Campo `status` (`finalized`/rascunho). Sem lock — relatório finalizado continua editável, apenas marca `editedAfterFinalize` |
| Integrações existentes | Nenhuma API externa. Único "export" é um JSON manual para um app de Finanças separado, baixado pelo usuário — sem transmissão automática |

### Portal Pred.IO

| Item | Detalhe |
|---|---|
| Framework | Streamlit (Python), `app.py` como entrypoint |
| Autenticação | Login próprio (`auth.py`) — usuário/senha (SHA-256) contra a aba `Clientes`/`Usuarios` da planilha. Sessão persistida via query param `?sid=` + aba `Sessions`. Perfis: `cliente` vs `funcionario`/`admin` (área interna = páginas `page_sv_*.py`) |
| Banco | **Google Sheets** (gspread), planilha única (`SHEET_ID` fixo em `sheets.py`), ~20 abas (Clientes, Ativos, ComponentesAtivos, TechnicalReports, ReportTimeline, Chamados, BibliotecaTecnica, Chunks, Sessions, ClienteLogos, MaintenancePlans, Notificacoes, AcessoAuditoria etc.) |
| Storage | **Google Cloud Storage** (não é Google Drive, apesar do nome do arquivo `drive_storage.py`) — bucket `predio-biblioteca`, mesma service account da planilha, URLs assinadas de 10 anos |
| Clientes | Aba `Clientes`, chave `Client_Id` = `Empresa.strip().lower()`. Sem CNPJ |
| Ativos | Aba `Ativos`, FK real `Client_Id` + `Empresa` (redundante) |
| Relatórios | Aba `TechnicalReports` — já estruturado com GUT (Gravidade/Urgência/Tendência), severidade, status (`Rascunho`/`Publicado`), score de impacto no ativo |
| Histórico do ativo | Aba `ReportTimeline`, com flag `Visivel_Cliente` |
| Biblioteca técnica | Aba `BibliotecaTecnica` + `Chunks` (RAG), indexação de PDFs via `document_processor.py` |
| Assistente Técnico | Chamada direta à API Anthropic (`claude-haiku-4-5-20251001`) server-side, com fallback via webhook n8n |
| Segurança | `client_id` nunca vem do front-end; `security.py` centraliza checagem de posse (cliente só vê seus próprios ativos/relatórios/documentos); credenciais (`credentials.json`) só lidas server-side, corretamente no `.gitignore` e fora do git |

---

## 2. Mesmo backend?

**Resposta: C — bancos diferentes.**

- App Relatórios → Firestore (projeto `predio-despesas`), com IndexedDB local como fonte primária.
- Portal → Google Sheets + Google Cloud Storage.

Não há sobreposição de banco, storage nem formato de ID:
- `cliente_id` no App Relatórios = UUID gerado localmente (`uid()`), sem relação com o Portal.
- `cliente_id` no Portal = string derivada do nome da empresa (`empresa.strip().lower()`), não é UUID.
- `ativo_id` idem — formatos incompatíveis e sem nenhuma referência cruzada hoje.

Não é possível ligar os dois sistemas "por coincidência" de ID — qualquer integração precisa de um passo explícito de resolução/mapeamento de cliente e ativo (por nome + confirmação manual na primeira vez, não por comparação automática de ID).

---

## 3. Mapa de clientes

| App Relatórios | Portal | Observação |
|---|---|---|
| `client.id` (uid local) | `Client_Id` (slug do nome) | **Formatos incompatíveis** — não dá para unificar automaticamente |
| `client.nome` | `Empresa` | Nome livre nos dois; útil para matching manual assistido |
| `client.unidade` | `Planta` (na aba Ativos, não Clientes) | Portal amarra planta ao ativo, não ao cliente |
| `client.cidade` | — | Sem equivalente direto no Portal |
| `client.contato` / `telefone` / `email` | `Nome` / `Telefone` / `Email` (aba Clientes) | Equivalentes |
| `client.logo` (base64 embutido) | aba `ClienteLogos` (base64 separado) | Ambos base64, formatos de armazenamento diferentes |
| — (não existe) | — (não existe) | **Nenhum dos dois sistemas tem campo CNPJ hoje** |

Não existe hoje nenhum campo confiável para casar clientes automaticamente — a integração vai depender de um mapeamento inicial (por nome, revisado manualmente) que crie e persista a correspondência `app_relatorios.client.id ↔ portal.Client_Id`.

## 4. Mapa de ativos

| App Relatórios | Portal | Observação |
|---|---|---|
| `equipment.id` | `Id` (prefixo `AT`) | Formatos diferentes |
| `equipment.clientId` | `Client_Id` | FK real nos dois — mas valores incompatíveis (ver acima) |
| `equipment.nome` / `tag` | `Tag` | Equivalente |
| `equipment.setor` | `Planta` | Equivalente aproximado |
| `equipment.fabricante` | `Modelo`/`Tipo` (campos separados) | Portal não tem "fabricante" isolado — é parte de `Tipo`/`Modelo`/`Detalhes` |
| `equipment.modelo` | `Modelo` | Equivalente |
| `equipment.serie` | `Ns` | Equivalente |
| `equipment.modeloBomba` | `Modelo_Bomba_Oleo` | Equivalente exato (mesmo campo, nomes diferentes) |
| `equipment.nCoalescer` | `Num_Coalescer` | Equivalente exato |
| `equipment.painel` | `Modelo_Painel` | Equivalente exato |
| — | `Status`, `Score`, `Criticidade` | Só existem no Portal (usados pelo dashboard/GUT) |

Importante (regra de segurança pedida pelo usuário): dentro de um relatório do App Relatórios, os campos de equipamento **são texto livre**, não uma referência a `equipment.id`. Isso significa que, para a integração, **não dá para confiar apenas no nome do equipamento** — será necessário, no momento de publicar, resolver explicitamente qual `ativo_id` do Portal aquele relatório pertence (idealmente escolhendo o ativo cadastrado, com o texto livre como fallback/exibição).

## 5. Mapa de relatórios

Tipos hoje no App Relatórios: **OAT, Termografia, Alinhamento a Laser** (Visita técnica/comercial são subcategorias de OAT, não tipos próprios — divergente da lista genérica prevista no pedido original, que incluía "Vibração" como tipo separado; isso deve ser confirmado com quem opera o app antes da Etapa 2).

| Campo já estruturado no App Relatórios | Equivalente no Portal (`TechnicalReports`) |
|---|---|
| `type` (oat/termo/laser) | `Tipo_Servico` |
| `data.*` (medições por tipo) | Sem campo estruturado equivalente — Portal guarda resumo/texto, não medições brutas |
| `status` (finalized/rascunho) | `Status` (`Rascunho`/`Publicado`) — conceito parecido, mas o Portal já tem um terceiro estado implícito de "visível ao cliente" que o App não tem |
| severidade (NETA: Baixa/Média/Alta/Crítica, só em Termo) | `Severidade` + campos GUT completos (`Gut_Gravidade/Urgencia/Tendencia/Score/Prioridade`) |
| — (não existe GUT no App) | GUT calculado (`gut.py`) |
| `workOrderNumber` | Sem campo dedicado — poderia mapear para `Titulo` ou novo campo |
| fotos/assinaturas (base64 embutido) | `Arquivo_Url` (link para GCS) — Portal não embute binário, referencia por URL |
| PDF (gerado via print, local) | `Arquivo_Url` — Portal espera uma URL de arquivo já hospedado, não gera PDF do zero para o relatório técnico em si |

Diferença estrutural relevante: o Portal já modela GUT e severidade granular para priorização/dashboard; o App Relatórios não tem esse conceito. Isso não bloqueia a integração, mas indica que **o GUT deverá ser calculado no lado do Portal** (ou preenchido manualmente na publicação), não recebido pronto do App Relatórios — a menos que o App ganhe esses campos futuramente.

---

## 6. Diferenças-chave encontradas

1. **Fonte de verdade divergente**: App Relatórios é offline-first (IndexedDB), Firestore é só um espelho de sincronização entre dispositivos do mesmo técnico — não foi desenhado para ser lido por terceiros.
2. **Nenhum ID compatível** entre os sistemas hoje (cliente nem ativo).
3. **Equipamento em relatório é texto livre** no App — precisa de resolução explícita para virar `ativo_id` no Portal.
4. **Binário embutido vs. binário por URL**: App embute base64 no próprio documento; Portal referencia arquivos por URL assinada em GCS. Uma integração direta por Firestore exigiria extrair e re-hospedar esses binários — não é um simples "apontar para o mesmo Storage" porque **não existe Storage compartilhado**.
5. **Tipos de relatório divergem** do briefing original (sem "Vibração" como tipo próprio no App atual).
6. **Sem GUT nativo no App** — teria que ser calculado no destino.
7. Google Drive não é usado por nenhum dos dois sistemas atualmente (App não usa storage nenhum; Portal usa GCS, não Drive, apesar do nome do módulo `drive_storage.py`) — isso simplifica o item 9 do pedido original, já que não há uma migração de Drive a fazer, apenas decidir se o PDF final passa a ser gerado/hospedado pelo fluxo novo.

---

## 7. Arquitetura recomendada

Como os bancos são diferentes (situação C), a integração **não pode ser direta por Firestore/Sheets compartilhado** — precisa de uma **API intermediária**.

Modelo recomendado:

```
App Relatórios (Firestore predio-despesas)
        │  finalizar relatório
        ▼
  Cloud Function / endpoint autenticado
  (lê o doc de "relatorios" recém-sincronizado)
        │  POST /api/integrations/reports
        ▼
Portal Pred.IO — endpoint próprio (Streamlit não serve API nativamente;
precisa de um pequeno serviço HTTP separado, ou uma Cloud Function
que escreve direto nas abas via a mesma service account do Portal)
        │
        ├─ resolve cliente (mapa app_client_id → portal.Client_Id)
        ├─ resolve ativo (mapa app_equip_id → portal.Ativo_Id, com fallback manual)
        ├─ extrai binários base64 → sobe no GCS (bucket predio-biblioteca) → Arquivo_Url
        ├─ grava linha em TechnicalReports (Status inicial: Rascunho)
        ├─ grava evento em ReportTimeline
        └─ (opcional) calcula GUT inicial ou deixa para revisão manual no Portal
```

Pontos de decisão para a Etapa 2 (não decidir agora, só registrar as opções):
- **Onde roda a ponte**: Cloud Function acionada por Firestore trigger (mais simples, não depende do Streamlit estar de pé) vs. endpoint dentro do próprio Portal (exigiria expor um serviço HTTP adicional, já que Streamlit não é uma API REST).
- **Autenticação entre sistemas**: um secret compartilhado / service account dedicada, nunca a service account de produção do Portal exposta ao App Relatórios.
- **Publicação automática vs. sempre como rascunho**: recomendo que relatórios cheguem sempre como `Status=Rascunho` no Portal, exigindo publicação manual — preserva a regra de "rascunhos não aparecem para cliente" sem depender de o App saber disso.

---

## 8. Riscos

- **Nenhum ID cruzado hoje** — qualquer automação de matching cliente/ativo por nome precisa de confirmação humana na primeira ocorrência, senão risco de vincular relatório ao cliente/ativo errado.
- **Extração de binário do Firestore** pode esbarrar no limite de 1MB/doc (o próprio App já trata isso com `FS_DOC_SAFE_BYTES`) — relatórios grandes podem já estar truncados/só-locais e nunca chegar ao Firestore para a ponte ler.
- **Streamlit não é uma API** — decisão de arquitetura da ponte (Cloud Function vs. serviço HTTP dedicado) tem implicações de custo/operação que vale confirmar com o usuário antes de implementar.
- **Divergência de tipos de relatório** (sem "Vibração" nativo) pode exigir alinhamento de escopo antes da Etapa 2.
- Nenhum risco de segurança novo identificado nos dois sistemas isoladamente (credenciais corretamente fora do git, checagem de posse por cliente já existe no Portal).

---

## 9. Próxima etapa (não implementada agora)

Etapa 2 deverá, mediante aprovação:
1. Definir e congelar o contrato do payload `POST /api/integrations/reports`.
2. Decidir onde a ponte roda (Cloud Function vs. serviço dedicado).
3. Implementar o mapeamento inicial cliente/ativo (com revisão manual).
4. Implementar upload de binários do relatório para GCS.
5. Implementar escrita em `TechnicalReports` + `ReportTimeline` sempre como rascunho.

Arquivos que provavelmente precisarão ser tocados na Etapa 2:
- App Relatórios: `Pred.IO app relatorios.html` (adicionar chamada/trigger de publicação no fluxo `finalizeReport`).
- Portal: novo arquivo de endpoint/serviço de integração (ainda não existe); `sheets.py` (novas funções de escrita usadas pela ponte); possivelmente `drive_storage.py` (upload vindo de binário base64 em vez de upload de arquivo do usuário).
- Infraestrutura: nova Cloud Function ou novo serviço, fora do escopo dos dois repositórios atuais.
