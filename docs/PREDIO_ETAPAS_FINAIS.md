# ETAPAS FINAIS — Portal Pred.IO
**Atualizado em:** 2026-06-28

---

## Foco da Etapa Atual (em andamento)

Antes de avançar para as etapas finais, estão sendo concluídas:

1. ✅ Corrigir upload de PDF (em memória, sem storage externo)
2. ✅ Processar e indexar documentos (PyPDF2 + pdfplumber ≤5 MB)
3. ✅ Assistente consultar Biblioteca Técnica (chunks de documentos)
4. ✅ Assistente consultar Relatórios Técnicos (chunks de relatórios)
5. 🔄 Validar com documento real do cliente (pendente)
6. ✅ Busca web controlada via Tavily com síntese via Claude (pendente crédito)
7. ✅ Chamados com delete, confirmação e detalhamento

**Somente após validar 5 e 6**, avançar para as etapas abaixo.

---

## Etapa 1 — Chamados Técnicos Integrados ✅ (concluída)

- [x] CRUD completo de chamados
- [x] Detalhamento de chamado com mensagens
- [x] Botão de lixeira com confirmação na supervisão
- [x] Origem, categoria, prioridade, status, responsável
- [x] Filtros avançados na supervisão
- [x] Abertura de chamado pelo cliente e pela supervisão

---

## Etapa 2 — Dashboard Executivo Final 🔄 (parcialmente implementado)

- [x] Dashboard do cliente com faróis de condição
- [ ] Dashboard da supervisão com visão consolidada de todos os clientes
- [ ] Métricas: ativos críticos, chamados abertos, manutenções vencidas, score geral

---

## Etapa 3 — Segurança, Permissões e Isolamento por `client_id` 🔄 (base implementada)

- [x] `client_id` sempre da sessão — nunca do front-end
- [x] Isolamento por cliente em todas as queries principais
- [ ] Auditoria completa de todos os endpoints do `sheets.py`
- [ ] Validar que obs_interna e rascunhos nunca chegam ao cliente
- [ ] Testes de penetração básicos (cliente A não vê dados do cliente B)

---

## Etapa 4 — Preferências de Notificação 🔄 (parcialmente implementado)

- [x] Página de preferências de notificação (por canal: portal, e-mail, WhatsApp)
- [x] Notificações internas do portal (lidas/não lidas)
- [ ] Disparo automático de notificação quando evento ocorre (manutenção vence, chamado respondido, alerta criado)
- [ ] Central de templates de notificação
- [ ] Fila de notificações + modo teste
- [ ] Preview de mensagem antes de enviar

---

## Etapa 5 — PWA / Experiência Mobile 🔄 (base implementada)

- [x] Manifest PWA (`manifest.json` via `pwa.py`)
- [x] Bottom navigation mobile
- [x] Sininho de notificações mobile
- [x] Banner de atualização automática por deploy
- [ ] Testar instalação em iOS Safari e Android Chrome
- [ ] Validar experiência touch em todas as páginas
- [ ] Ícones e splash screen nos tamanhos corretos

---

## Etapa 6 — Homologação com Cliente Teste

- [ ] Selecionar cliente real para homologação
- [ ] Cadastrar ativos, componentes, horímetros
- [ ] Cadastrar e indexar pelo menos 1 documento técnico real
- [ ] Publicar pelo menos 1 relatório técnico real
- [ ] Testar fluxo completo do Assistente com dados reais
- [ ] Validar isolamento: cliente A não vê dados do cliente B

### Etapa 6.5 — Relatório Executivo Word do Histórico do Ativo

- [x] `report_word_generator.py` implementado com python-docx
- [ ] Validar download do .docx com dados reais do ativo
- [ ] Formatar capa, sumário, seções e tabelas conforme padrão Pred.IO
- [ ] Integrar com histórico de manutenções, alertas, chamados e análises preditivas

### Etapa 6.6 — Assistente Técnico alimentado pela Biblioteca + Relatórios

- [x] Motor consulta chunks de documentos e relatórios do cliente
- [ ] Validar com documento real indexado (perguntas e respostas corretas)
- [ ] Ajustar pontuação de relevância para priorizar chunks do cliente
- [ ] Garantir que Assistente nunca inventa especificação técnica sem fonte cadastrada

### Etapa 6.7 — Central de Templates, Preview, Fila e Modo Teste de Notificações

- [ ] Interface na supervisão para criar e editar templates de notificação
- [ ] Preview de mensagem renderizada
- [ ] Fila de notificações pendentes
- [ ] Modo teste: enviar apenas para e-mail/WhatsApp interno da Pred.IO
- [ ] Log de auditoria de envios

### Etapa 6.8 — Varredura Geral do Código antes de WhatsApp/E-mail

- [ ] Revisar todos os módulos de notificação
- [ ] Garantir que `NOTIFICATION_EXTERNAL_SEND_ENABLED=false` não pode ser ignorado
- [ ] Revisar sanitização de dados antes de envio externo
- [ ] Revisar isolamento por `client_id` em todos os endpoints
- [ ] Remover todos os `TODO`, `mock` e dados de demonstração antes de produção

---

## Etapa 7 — E-mail e WhatsApp (bloqueada até etapa 6.8)

- [ ] Integração com provedor de e-mail transacional (SendGrid, Resend, etc.)
- [ ] Integração com WhatsApp Business API (Twilio, Z-API, etc.)
- [ ] `NOTIFICATION_EXTERNAL_SEND_ENABLED` = `true` somente após varredura completa
- [ ] Templates aprovados pelo cliente antes do envio em produção

---

## Etapa 8 — Monitoramento Online Real (futuro)

- [ ] Definir protocolo: Modbus RTU ou TCP/IP
- [ ] Implementar gateway de dados (servidor intermediário ou edge device)
- [ ] Receber dados ao vivo no Portal Pred.IO (somente leitura nesta fase)
- [ ] Exibir nos Faróis com timestamp ao vivo
- [ ] Comandos remotos: apenas em fase posterior com projeto de segurança validado
