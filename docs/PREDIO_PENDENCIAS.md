# PENDÊNCIAS — Portal Pred.IO
**Atualizado em:** 2026-06-28

---

## Prioridade Alta

- [ ] **Upload de PDF — storage definitivo**: upload em memória funciona mas limita a PDFs simples ≤15 MB. PDFs grandes ou com layout gráfico falham. Necessário ou storage externo pago (GCS com billing) ou ajuste de fluxo para PDFs pesados.
- [ ] **Indexação de documentos — validar com PDF real do cliente**: testar o fluxo completo (upload → extração → chunks → status "Indexado") com um documento real do cliente, não apenas mocks.
- [ ] **Assistente consultar Biblioteca Técnica real**: o motor já consulta chunks do Sheets; validar que um documento real indexado é encontrado e responde corretamente nas perguntas do cliente.
- [ ] **Assistente consultar Relatórios Técnicos reais**: validar que chunks de relatórios publicados são usados pelo Assistente para responder perguntas sobre o equipamento.
- [ ] **Segurança por `client_id` — auditoria completa**: revisar todas as queries do `sheets.py` para garantir que nenhuma retorna dados de outro cliente. Especialmente `get_documentos_tecnicos`, `get_chunks_documento`, `get_chunks_relatorio`.
- [ ] **Proteção de rascunhos e observações internas**: garantir que `obs_interna`, `Status=Rascunho` e campos internos nunca chegam ao portal do cliente em nenhum endpoint.
- [ ] **Créditos Anthropic**: adicionar créditos em console.anthropic.com → Plans & Billing para síntese web com Claude Haiku funcionar.
- [ ] **Remover `credentials_oneline.txt` e `credentials_b64.txt` do repositório** (ou garantir que estão no `.gitignore`): arquivos de credencial não devem estar versionados.

---

## Prioridade Média

- [ ] **Relatório Executivo Word — download funcional**: validar que `report_word_generator.py` gera .docx correto para o histórico do ativo e que o botão de download funciona no portal.
- [ ] **Auditoria do Assistente — painel de métricas**: expandir a página `page_sv_assistente.py` com métricas de uso (perguntas por dia, intenções mais comuns, taxa de resposta via web).
- [ ] **Dashboard Executivo Final**: completar `page_sv_dashboard.py` com visão consolidada de todos os clientes (ativos críticos, chamados abertos, manutenções vencidas).
- [ ] **Notificações internas — disparo automático**: implementar criação automática de notificações quando tarefa de manutenção vence, alerta é criado ou chamado é respondido.
- [ ] **PWA / Experiência Mobile**: testar instalação do app em iOS e Android, verificar bottom nav, sininho e banner de atualização.
- [ ] **Mock data — remoção progressiva**: à medida que dados reais são cadastrados, remover dependências de `_mock_chamados`, `_mock_mensagens`, `assistant_mock_data.py`, etc.

---

## Prioridade Baixa / Futuro

- [ ] **WhatsApp**: implementar envio via WhatsApp Business API apenas após etapa 6+ (homologação + varredura de segurança). `NOTIFICATION_EXTERNAL_SEND_ENABLED` deve permanecer `false` até lá.
- [ ] **E-mail**: mesmo controle que WhatsApp.
- [ ] **Busca na internet — expansão do allowlist**: adicionar domínios técnicos relevantes ao `ALLOWED_DOMAINS` conforme necessidade.
- [ ] **Monitoramento online real**: integração de dados ao vivo do painel Mypro Touch AD via Modbus. Apenas leitura nesta fase.
- [ ] **Integração Modbus / CLP**: requer projeto de segurança específico com intertravamentos, autenticação forte e auditoria.
- [ ] **App Store / Play Store**: publicação como app nativo após PWA estabilizado e homologado.
- [ ] **Lint / typecheck formal**: adicionar `flake8` ou `ruff` + `mypy` ao pipeline para evitar erros silenciosos.
- [ ] **CI/CD**: adicionar checagem automática de testes no push para `main`.

---

## Problemas Conhecidos Ativos

| Problema | Impacto | Status |
|----------|---------|--------|
| Anthropic sem crédito | Síntese web usa fallback de texto | Aguardando recarregar crédito |
| PDFs ≥5 MB com layout gráfico | Texto não extraído | Limitação do Render free tier (512 MB RAM) |
| GCS sem billing | Upload não vai para storage externo | Processamento em memória como workaround |
| Mock data ainda ativa | Assistente pode responder com dados fictícios se não houver dados reais | Remoção gradual conforme dados reais são cadastrados |
