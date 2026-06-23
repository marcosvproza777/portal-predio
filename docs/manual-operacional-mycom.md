# Manual Operacional MYCOM - Sistema Chiller

## 1. Identificação

| Campo           | Valor                                       |
|----------------|---------------------------------------------|
| Nome            | Manual Operacional MYCOM - Sistema Chiller  |
| Tipo            | Manual operacional                          |
| Fabricante      | MYCOM                                       |
| Equipamento     | Sistema Chiller / Compressor MYCOM          |
| Arquivo         | `OPERACIONAL - Cópia.pdf`                   |
| Páginas (ref.)  | 17 páginas                                  |
| Visibilidade    | Público para clientes autorizados           |
| Status          | Ativo                                       |
| Uso pela IA     | Sim                                         |
| ID no mock      | `doc-mycom-001`                             |

---

## 2. Como foi cadastrado

O documento foi registrado em `assistant_mock_data.py` dentro de `_DEFAULT_CONTEXT["documentos"]`
como `doc-mycom-001`. O arquivo PDF (`OPERACIONAL - Cópia.pdf`) deve ser armazenado em storage
seguro e o caminho/URL registrado no campo `arquivo_url`.

O processamento do texto (extração de chunks) está preparado em `document_processor.py` com as
funções `_MOCK_TEXTO_MYCOM_OPERACIONAL` e `_MOCK_CHUNKS_MYCOM_OPERACIONAL`. Quando o supervisor
clicar em "Processar documento" na Biblioteca Técnica, o sistema:
1. Localiza o arquivo PDF pelo `arquivo_url`
2. Extrai o texto com `extrair_texto_pdf()`
3. Cria os chunks com `criar_chunks()`
4. Salva em `DocumentoChunks` no Sheets
5. Atualiza `Status_Indexacao` para `Indexado`

---

## 3. Principais seções

| Seção | Conteúdo |
|-------|----------|
| Identificação | Nome e propósito do manual |
| Índice | Estrutura do documento |
| Defeitos — Motor | Causas/correções para motor que não parte, ronca, para logo |
| Defeitos — Pressão alta | Causas: água insuficiente, ar no condensador, excesso de refrigerante |
| Defeitos — Pressão de descarga baixa | Causas: válvula de expansão, falta de refrigerante |
| Defeitos — Pressão de sucção | Causas: válvula de expansão, evaporador congelado, filtros |
| Defeitos — Ruído/vibração/superaquecimento | Alinhamento, bomba de óleo, martelamento |
| Defeitos — Consumo anormal de óleo | Retorno de líquido, viscosidade, bomba defeituosa |
| Parâmetros — Pressão de alta | NH3/R-22: 8–13,5 kg/cm² |
| Parâmetros — Pressão de óleo | Lado de baixa + 1,2 a 2 kg/cm² |
| Parâmetros — Temperatura de descarga | NH3/R-22: 80–140°C; R-12: 40–90°C |
| Painel elétrico | Inversor de frequência, soft-starter, alarmes, chiller |
| Fluxostato | Chave de controle de fluxo, segurança |
| Condensador a placa | Tratamento químico da água da torre |
| Inspeção diária | Registro de pressão, temperatura, corrente, voltagem |
| Inspeção semanal | Sistema de gás, sistema de óleo, selo de vedação |
| Inspeção mensal | Trips de segurança, controle de capacidade |
| Inspeção trimestral | Instrumentos, rolamentos do motor, megagem |
| Inspeção semestral / 5.000h | Análise de óleo, substituição de filtros, alinhamento 0,06mm |
| Inspeção anual / 10.000h | Calibração de instrumentos, PSV, estanqueidade, filtro coalescente |
| Referência 20.000h | Ver regra especial abaixo |

---

## 4. Chunks criados

O documento possui **21 chunks** indexados (numerados de 1 a 21), correspondendo às seções
principais do manual. Os chunks são buscados pelo assistente via `_buscar_chunk_mycom()` em
`assistant_engine.py`.

---

## 5. Como o assistente usa o conteúdo

O assistente consulta os chunks do manual quando o cliente perguntar sobre:
- Operação do chiller / compressor MYCOM
- Pressão de descarga, sucção, óleo
- Temperatura de descarga, selo mecânico
- Painel elétrico, inversor de frequência, soft-starter
- Fluxostato, condensador a placa
- Inspeções diária/semanal/mensal/trimestral/semestral/anual
- Intervalos de 5.000h e 10.000h
- Filtros de óleo, filtro coalescente, alinhamento, calibração

---

## 6. Regra especial: 20.000 horas

> **20.000 horas é referência técnica, não gatilho automático de overhaul.
> A decisão depende da saúde real da máquina.**

O manual cita a inspeção bienal ou 20.000 horas como referência. No Portal Pred.IO:

- A revisão de 20.000 horas **NÃO** cria tarefa automática de manutenção.
- A tarefa `pm-revisao-geral` existe apenas como **Decisão por condição**.
- A tarefa `pm-kit-revisao` existe apenas como **Decisão por condição**.
- O assistente **nunca** recomenda overhaul, desmontagem ou kit revisão automaticamente por horímetro.
- A decisão deve considerar: vibração, análise de óleo, termografia, histórico, score de saúde, falhas recorrentes, avaliação técnica.

---

## 7. Regra especial: revisão geral / desmontagem / kit revisão

Esses itens aparecem no plano de manutenção sob a categoria **Recomendações por Condição**,
com `tipo = "condicao"` e `status = "Depende de análise preditiva"`.

A mensagem ao cliente é:
> A revisão geral do compressor não é indicada automaticamente apenas por horímetro.
> A decisão deve ser baseada na condição real da máquina, considerando relatórios preditivos,
> análise de óleo, vibração, termografia, histórico operacional e avaliação técnica.

---

## 8. Regras de segurança

- Chunks só são retornados para clientes autorizados (via `cliente_id` da sessão).
- O documento tem visibilidade `"Público para clientes autorizados"` — não aparece para clientes de outros ativos.
- Observações internas nunca entram no contexto da IA.
- Documentos internos da Pred.IO não são exibidos para clientes.
- Links de arquivo são protegidos — nunca expostos diretamente ao front-end sem autenticação.

---

## 9. Como vincular o manual a clientes/ativos

Em produção, o documento pode ser vinculado por:
- `Cliente_Id`: para um cliente específico
- `Ativo_Id`: para um ativo específico
- `Visibilidade = "Público para clientes autorizados"`: disponível para todos os clientes autorizados

A Supervisão Pred.IO permite configurar esses vínculos na tela `/supervisao/biblioteca`.

---

## 10. Como atualizar o manual no futuro

1. Fazer upload do novo PDF no storage.
2. Atualizar `arquivo_url` no registro do documento.
3. Clicar em "Reprocessar documento" na Supervisão → Biblioteca Técnica.
4. O sistema extrai o novo texto, remove chunks antigos e cria novos chunks.
5. O assistente passa a usar o novo conteúdo automaticamente.

---

## 11. Tarefas do plano de manutenção derivadas deste manual

| ID | Nome | Tipo | Periodicidade |
|----|------|------|---------------|
| `pm-insp-diaria` | Inspeção diária — Leitura operacional | Calendário | Diária |
| `pm-insp-semanal` | Inspeção semanal — Sistema de gás e óleo | Calendário | Semanal |
| `pm-insp-mensal` | Inspeção mensal — Trips e capacidade | Calendário | Mensal |
| `pm-insp-trimestral` | Inspeção trimestral — Instrumentação e motor | Calendário | Trimestral |
| `pm-vibracao` | Análise de vibração | Calendário | A cada 2 meses |
| `pm-termografia` | Termografia | Calendário | A cada 4 meses |
| `pm-semestral-align` | Alinhamento motor x compressor | Horímetro | 5.000h |
| `pm-anual-calib` | Calibração de instrumentos e PSV | Horímetro | 10.000h |
| `pm-revisao-geral` | Revisão geral / desmontagem | Condição | Depende de análise preditiva |
| `pm-kit-revisao` | Substituição do kit revisão | Condição | Depende de análise preditiva |

**Não existe tarefa automática de 20.000 horas no plano.**
