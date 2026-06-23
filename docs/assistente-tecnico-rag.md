# Assistente Técnico Pred.IO — Preparação RAG

## Visão Geral

Este documento descreve a infraestrutura de extração de texto e chunking implementada
para permitir que o Assistente Técnico Pred.IO consulte o conteúdo real dos manuais técnicos.

---

## Estrutura de Dados

### BibliotecaTecnica (Google Sheets)

Campos de indexação adicionados:

| Campo            | Valores possíveis                              |
|-----------------|------------------------------------------------|
| Status_Indexacao | Não indexado / Em processamento / Indexado / Falhou |
| Erro_Indexacao   | Mensagem de erro se Status = Falhou            |
| Quantidade_Paginas | Número de páginas extraídas                  |
| Origem_Arquivo   | URL ou caminho de origem                       |
| Texto_Extraido   | Primeiros 5.000 chars do texto extraído        |
| Data_Indexacao   | Timestamp da última indexação                  |

### DocumentoChunks (Google Sheets)

| Campo         | Descrição                                 |
|--------------|-------------------------------------------|
| Id            | ID único do chunk (CHK-xxx)               |
| Documento_Id  | ID do documento pai (DOC-xxx)             |
| Cliente_Id    | cliente_id do documento (segurança)       |
| Ativo_Id      | ativo vinculado ao documento              |
| Componente_Id | componente vinculado (se aplicável)       |
| Chunk_Index   | Posição do chunk no documento (1-N)       |
| Pagina_Inicio | Página inicial do conteúdo               |
| Pagina_Fim    | Página final do conteúdo                 |
| Titulo_Secao  | Título da seção/capítulo                  |
| Conteudo      | Texto do chunk (máx ~500 palavras)        |
| Palavras_Chave | Palavras-chave da seção                  |
| Created_At    | Timestamp de criação                      |
| Updated_At    | Timestamp de atualização                  |

---

## Fluxo de Indexação

```
Supervisão → página Biblioteca Técnica
  → botão "Processar documento" (por card)
  → document_processor.processar_documento(doc_id, ...)
      ├── extrair_texto_pdf(url, nome)
      │     ├── Tenta pdfplumber
      │     ├── Tenta PyPDF2
      │     └── Fallback: mock estruturado (_get_mock_for_url)
      ├── criar_chunks(doc_id, ..., texto)
      │     └── Usa chunks mock se texto = mock; senão divide por ~500 palavras
      ├── sheets.delete_chunks_documento(doc_id)  ← remove chunks anteriores
      ├── sheets.add_chunks_lote(chunks)           ← salva novos chunks
      └── sheets.update_status_indexacao(doc_id, "Indexado", ...)
```

---

## Mock Estruturado — Manual 200 VLD

O manual "Unidade Compressora Parafuso 200 VLD" tem 5 chunks mock:

| Chunk | Seção                                  | Palavras-chave principais       |
|-------|----------------------------------------|---------------------------------|
| 1     | Sistema de Lubrificação                | óleo, VDL 46, temperatura, pressão |
| 2     | Especificações de Óleo e Intervalos    | troca 2.000h, VDL 46, análise 500h |
| 3     | Manutenção dos Filtros                 | filtro ar, filtro óleo, 1.000h |
| 4     | Critérios para Overhaul                | overhaul, vibração, termografia, histórico |
| 5     | Segurança e Operação                   | pressão máxima, alarme, válvula |

---

## Busca por Conteúdo no Assistente

### Assistente flutuante (JS, `getResp()` em `ui.py`)

```javascript
searchChunks(extraWords)  // busca em ctx.documentos[].chunks[]
fmtChunk(hit)             // formata: "Com base no documento X (Seção: Y), encontrei: ..."
```

Prioridade de busca:
1. `oleo` → `searchChunks(['oleo', 'lubrificante', 'vdl', ...])`
2. `overhaul` → `searchChunks(['overhaul', 'revisao', 'horimetro', ...])`
3. `documentos` → `searchChunks([])` (palavras da pergunta)
4. Fallback genérico → `searchChunks([])` antes do fallback final

### Assistente página dedicada (Python, `ai_assistant.py`)

O contexto completo incluindo todos os chunks é enviado para a IA no prompt.
A IA cita a fonte (seção, página) na resposta.

---

## Badges de Status no Portal

### Portal do Cliente (`page_biblioteca.py`)
- 🤖 **Disponível para consulta IA** (verde): `Status_Indexacao = "Indexado"`
- 📥 **Disponível apenas para download** (cinza): demais status

### Supervisão (`page_sv_biblioteca.py`)
- Badge colorido: Indexado (verde) / Falhou (vermelho) / Em processamento (amarelo) / Não indexado (cinza)
- Data + número de páginas quando indexado
- Mensagem de erro quando falhou
- Botão "⚙️ Processar documento" / "🔄 Reprocessar"

---

## Segurança

- Chunks só são retornados para docs autorizados ao `client_id` da sessão
- `get_chunks_documento(doc_id)` não filtra por cliente diretamente — a segurança
  vem do fato de que o `doc_id` já passou pelo filtro de `get_documentos_tecnicos(client_id, staff=False)`
- Documentos `"Apenas equipe Pred.IO"` nunca geram chunks visíveis ao cliente
- Nenhuma chave de API no front-end
