# REGRAS FIXAS — Portal Pred.IO
> Estas regras não podem ser quebradas em nenhuma circunstância.  
> Qualquer alteração de código que viole uma dessas regras deve ser recusada.

---

## Interface e Navegação

- **Não criar sidebar no portal do cliente.** A navegação do cliente é via topnav + bottom nav mobile + botão flutuante do Assistente.
- **Assistente Técnico deve ser botão flutuante**, não uma página separada acessível por menu.
- **Não usar o nome "Mypro Touch+"** — esse produto não existe. Usar somente "Mypro Touch" e "Mypro Touch AD".

---

## Segurança de Dados

- **`client_id` SEMPRE vem da sessão do servidor** — nunca aceitar `client_id` livre do front-end, URL ou formulário.
- **Cliente só vê dados do próprio `client_id`** — isolamento absoluto por cliente.
- **Não mostrar observações internas (`obs_interna`) ao cliente.**
- **Não mostrar rascunhos ao cliente** — apenas documentos/relatórios publicados.
- **Não expor chunks brutos ao cliente** — o Assistente apresenta respostas sintetizadas.
- **Não expor logs internos ao cliente.**
- **Não expor chaves de API (`ANTHROPIC_API_KEY`, `WEB_SEARCH_API_KEY`, credenciais GCS) no front-end.**
- **Não expor dados de outro cliente** — qualquer query no Sheets deve filtrar por `client_id`.
- **Fonte exibida ao cliente: sempre "Pred.IO"** — nunca mencionar URLs, PDFs de terceiros ou sites externos nas respostas do Assistente.

---

## Comunicação Externa

- **Não enviar WhatsApp** — `NOTIFICATION_EXTERNAL_SEND_ENABLED=false` permanece até varredura completa de segurança.
- **Não enviar e-mail** — mesmo motivo: aguardar homologação e varredura (etapa 6+).
- **Não chamar busca web diretamente do front-end** — sempre via `web_search_service.py` no servidor.
- **Não enviar dados internos do cliente para a internet** — queries web são sanitizadas removendo `client_id`, IDs internos e dados sensíveis antes de qualquer chamada externa.
- **Internet não autoriza decisão crítica sozinha** — resposta web é sempre complemento, nunca substitui avaliação técnica.

---

## Operações Remotas

- **Não criar comando remoto** — o Portal Pred.IO não executa partida, parada, reset de alarme, alteração de set point nem qualquer operação remota no equipamento.
- **IA não executa comando operacional** — o Assistente Técnico orienta procedimentos; a execução é sempre presencial por operador autorizado.
- **Não criar monitoramento online real** nesta fase — apenas leitura de dados históricos do Sheets.

---

## Conhecimento Técnico Fixo (Regras de Domínio)

- **MYCOLD AB 68 foi descontinuado** — nunca recomendar como óleo atual. Redirecionar sempre para MYCOLD PAO.
- **Referência atual de óleo MYCOM: MYCOLD PAO** (PAO sintético, NH3/R22, ISO VG 68, 53 cSt @ 40°C).
- **20.000 horas NÃO é gatilho automático de overhaul** — é referência técnica. A decisão depende da saúde real da máquina (vibração, análise de óleo, termografia, histórico, score).
- **Overhaul depende de análise preditiva** — nunca sugerir overhaul automático por horímetro.
- **Troca de rolamento não é automática por ruído** — ruído indica análise de vibração, termografia e avaliação técnica.
- **Termografia não substitui análise de vibração** — são complementares.
- **Análise de óleo não é substituída por termografia** — são complementares.
- **Compressor alternativo:** temperatura de descarga referência 80°C a 140°C.
- **Compressor parafuso:** temperatura de descarga referência até 90°C.
- **Reset de alarme:** identificar e eliminar a causa raiz ANTES de resetar.
- **Alarme recorrente:** abrir chamado técnico, não resetar repetidamente.

---

## Arquitetura

- **Não alterar login sem necessidade explícita.**
- **Não alterar permissões sem necessidade explícita.**
- **Não rodar migração destrutiva** na planilha sem aprovação explícita.
- **Não apagar arquivos** do projeto sem aprovação explícita.
- **Não fazer commit automático** — apenas quando o usuário solicitar explicitamente.
