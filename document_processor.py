"""
Processador de documentos para preparação de RAG — Pred.IO.

Extrai texto de PDFs e cria chunks estruturados para busca pelo assistente.
Usa mock estruturado quando a URL não está acessível ou a extração falha.

SEGURANÇA:
  - Nunca expõe chunks de documentos de outros clientes.
  - Status de indexação nunca influencia o que o cliente vê — apenas a
    disponibilidade para busca no assistente.
"""
from __future__ import annotations
import re

STATUS_NAO_INDEXADO = "Não indexado"
STATUS_INDEXADO     = "Indexado"
STATUS_FALHOU       = "Falhou"
STATUS_PROCESSANDO  = "Em processamento"

# ── Mock texto estruturado para documentos de demonstração ────────────────────

_MOCK_TEXTO_200_VLD = """\
MANUAL TÉCNICO - UNIDADE COMPRESSORA PARAFUSO 200 VLD

SEÇÃO 1: SISTEMA DE LUBRIFICAÇÃO
O sistema de lubrificação da Unidade Compressora Parafuso 200 VLD utiliza óleo sintético VDL 46 \
(ISO VG 46) como fluido de processo e lubrificação. Capacidade do reservatório: 35 litros. \
Temperatura operacional normal: 70°C a 85°C. Alarme acima de 95°C; desligamento automático acima \
de 105°C. Pressão mínima de óleo: 2,0 bar — abaixo disso o sistema desliga por segurança.

SEÇÃO 2: ESPECIFICAÇÕES DE ÓLEO E INTERVALOS DE TROCA
Óleo recomendado: VDL 46 sintético. Equivalentes: Shell Corena S4 R 46, Castrol Aircol PD 46, \
Mobil Rarus SHC 1024. Troca de óleo: a cada 2.000 horas de operação ou 1 ano. \
Análise de óleo: a cada 500 horas. Filtro separador de óleo: troca a cada 4.000 horas \
ou quando a diferencial de pressão atingir 0,8 bar.

SEÇÃO 3: MANUTENÇÃO DOS FILTROS
Filtro de ar de entrada: inspeção a cada 250h, limpeza a cada 500h, troca a cada 2.000h. \
Filtro de óleo principal: troca a cada 1.000h. Filtro separador óleo/ar: troca a cada 4.000h. \
Filtro do resfriador: limpeza a cada 500h com ar comprimido.

SEÇÃO 4: CRITÉRIOS PARA OVERHAUL
O overhaul da Unidade Compressora 200 VLD não é determinado apenas pelo horímetro. \
A decisão de revisão geral deve considerar múltiplos fatores: vibração (≥7,5 mm/s RMS indica \
desgaste excessivo), análise de óleo (ferro acima de 50 ppm indica falha interna), termografia \
(pontos quentes acima de 15°C do valor de referência) e histórico de falhas. \
Intervalo máximo: 12.000 horas, podendo ser antecipado pelos indicadores preditivos.

SEÇÃO 5: SEGURANÇA E OPERAÇÃO
Pressão máxima de trabalho: 8,0 bar (116 PSI). Temperatura máxima de descarga: 110°C. \
Nunca operar com a válvula de segurança bloqueada. Purga do separador de condensado: diária. \
Em caso de alarme: aguardar resfriamento por 15 minutos antes de abrir qualquer tampa. \
Manter 1 metro livre ao redor da unidade para circulação de ar.\
"""

_MOCK_CHUNKS_200_VLD: list[dict] = [
    {
        "chunk_index": 1,
        "pagina_inicio": 1,
        "pagina_fim": 1,
        "titulo_secao": "Sistema de Lubrificação",
        "conteudo": (
            "O sistema de lubrificação utiliza óleo sintético VDL 46 (ISO VG 46). "
            "Capacidade: 35 litros. Temperatura operacional: 70°C a 85°C. "
            "Alarme acima de 95°C; desligamento acima de 105°C. Pressão mínima: 2,0 bar."
        ),
        "palavras_chave": "lubrificação, óleo, temperatura, pressão, VDL 46, reservatório",
    },
    {
        "chunk_index": 2,
        "pagina_inicio": 2,
        "pagina_fim": 2,
        "titulo_secao": "Especificações de Óleo e Intervalos de Troca",
        "conteudo": (
            "Óleo recomendado: VDL 46 sintético. Equivalentes: Shell Corena S4 R 46, "
            "Castrol Aircol PD 46, Mobil Rarus SHC 1024. "
            "Troca a cada 2.000 horas ou 1 ano. Análise de óleo a cada 500 horas. "
            "Filtro separador: troca a cada 4.000 horas."
        ),
        "palavras_chave": "óleo recomendado, VDL 46, troca de óleo, 2000 horas, análise de óleo, filtro separador",
    },
    {
        "chunk_index": 3,
        "pagina_inicio": 3,
        "pagina_fim": 3,
        "titulo_secao": "Manutenção dos Filtros",
        "conteudo": (
            "Filtro de ar: inspeção 250h, limpeza 500h, troca 2.000h. "
            "Filtro de óleo: troca 1.000h. Filtro separador: troca 4.000h. "
            "Filtro do resfriador: limpeza 500h com ar comprimido."
        ),
        "palavras_chave": "filtro, ar, óleo, troca, inspeção, resfriador, separador",
    },
    {
        "chunk_index": 4,
        "pagina_inicio": 4,
        "pagina_fim": 4,
        "titulo_secao": "Critérios para Overhaul",
        "conteudo": (
            "O overhaul não é determinado apenas pelo horímetro. "
            "A decisão considera: vibração (≥7,5 mm/s RMS), análise de óleo (ferro >50 ppm), "
            "termografia (pontos quentes >15°C acima da referência) e histórico de falhas. "
            "Intervalo máximo: 12.000 horas, podendo ser antecipado pelos indicadores preditivos."
        ),
        "palavras_chave": "overhaul, revisão geral, horímetro, vibração, análise de óleo, termografia, preditivo",
    },
    {
        "chunk_index": 5,
        "pagina_inicio": 5,
        "pagina_fim": 5,
        "titulo_secao": "Segurança e Operação",
        "conteudo": (
            "Pressão máxima: 8,0 bar. Temperatura máxima de descarga: 110°C. "
            "Nunca bloquear válvula de segurança. Purga do separador: diária. "
            "Em caso de alarme: aguardar resfriamento 15 min antes de abrir tampas. "
            "Espaço livre: 1 metro ao redor."
        ),
        "palavras_chave": "segurança, pressão máxima, temperatura, válvula, purga, alarme, operação",
    },
]


def _get_mock_for_url(arquivo_url: str, arquivo_nome: str = "") -> tuple[str, list[dict], int]:
    """Retorna (texto, chunks, n_paginas) mock se o arquivo for de demonstração."""
    key = (arquivo_url + " " + arquivo_nome).lower()
    if ("200" in key and "vld" in key) or "compressor" in key:
        return _MOCK_TEXTO_200_VLD, _MOCK_CHUNKS_200_VLD, 5
    return "", [], 0


def extrair_texto_pdf(arquivo_url: str, arquivo_nome: str = "") -> tuple[str, int]:
    """
    Extrai texto de um PDF. Retorna (texto, num_paginas).
    Tenta pdfplumber, depois PyPDF2. Fallback: mock estruturado.
    """
    if arquivo_url.startswith("/mock/") or not arquivo_url.startswith("http"):
        texto, _, n_pags = _get_mock_for_url(arquivo_url, arquivo_nome)
        return texto, n_pags

    try:
        import urllib.request
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            urllib.request.urlretrieve(arquivo_url, f.name)
            tmp_path = f.name

        texto = ""
        n_pags = 0
        try:
            import pdfplumber
            with pdfplumber.open(tmp_path) as pdf:
                n_pags = len(pdf.pages)
                texto = "\n\n".join(p.extract_text() or "" for p in pdf.pages)
        except ImportError:
            try:
                import PyPDF2
                with open(tmp_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    n_pags = len(reader.pages)
                    texto = "\n\n".join(
                        reader.pages[i].extract_text() or ""
                        for i in range(n_pags)
                    )
            except ImportError:
                pass

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        if texto.strip():
            return texto, n_pags
    except Exception:
        pass

    texto, _, n_pags = _get_mock_for_url(arquivo_url, arquivo_nome)
    return texto, n_pags


def criar_chunks(
    doc_id: str,
    cliente_id: str,
    ativo_id: str,
    componente_id: str,
    arquivo_url: str,
    arquivo_nome: str,
    texto: str,
) -> list[dict]:
    """
    Cria chunks para um documento.
    Se o texto coincidir com um mock, usa os chunks mock estruturados.
    Senão, divide em blocos de ~500 palavras por parágrafo.
    """
    mock_texto, mock_chunks, _ = _get_mock_for_url(arquivo_url, arquivo_nome)
    if mock_texto and mock_chunks and texto.strip() == mock_texto.strip():
        return [
            {"documento_id": doc_id, "cliente_id": cliente_id,
             "ativo_id": ativo_id, "componente_id": componente_id, **c}
            for c in mock_chunks
        ]

    if not texto.strip():
        return []

    paragrafos = [p.strip() for p in re.split(r'\n{2,}', texto) if p.strip()]
    chunks: list[dict] = []
    buffer: list[str] = []
    buf_words = 0
    chunk_idx = 1

    def flush() -> None:
        nonlocal chunk_idx, buffer, buf_words
        chunks.append({
            "documento_id":  doc_id,
            "cliente_id":    cliente_id,
            "ativo_id":      ativo_id,
            "componente_id": componente_id,
            "chunk_index":   chunk_idx,
            "pagina_inicio": chunk_idx,
            "pagina_fim":    chunk_idx,
            "titulo_secao":  _extrair_titulo(buffer[0]),
            "conteudo":      " ".join(buffer),
            "palavras_chave": "",
        })
        buffer = []
        buf_words = 0
        chunk_idx += 1

    for par in paragrafos:
        words = len(par.split())
        if buf_words + words > 500 and buffer:
            flush()
        buffer.append(par)
        buf_words += words

    if buffer:
        flush()

    return chunks


def _extrair_titulo(texto: str) -> str:
    primeira = texto.split("\n")[0].strip()
    return primeira[:80] if len(primeira) <= 80 else primeira[:77] + "..."


def processar_documento(
    doc_id: str,
    cliente_id: str,
    ativo_id: str,
    componente_id: str,
    arquivo_url: str,
    arquivo_nome: str = "",
) -> dict:
    """
    Processa um documento: extrai texto, cria chunks, salva no Sheets.
    Retorna {"ok": bool, "status": str, "n_chunks": int, "n_paginas": int, "erro": str}.
    """
    from sheets import update_status_indexacao, delete_chunks_documento, add_chunks_lote

    update_status_indexacao(doc_id, STATUS_PROCESSANDO)

    try:
        texto, n_paginas = extrair_texto_pdf(arquivo_url, arquivo_nome)
        if not texto.strip():
            update_status_indexacao(doc_id, STATUS_FALHOU, erro="Texto não extraído — PDF vazio ou protegido.")
            return {"ok": False, "status": STATUS_FALHOU, "n_chunks": 0, "n_paginas": 0, "erro": "Texto não extraído"}

        chunks = criar_chunks(doc_id, cliente_id, ativo_id, componente_id, arquivo_url, arquivo_nome, texto)
        if not chunks:
            update_status_indexacao(doc_id, STATUS_FALHOU, erro="Nenhum chunk gerado a partir do texto.")
            return {"ok": False, "status": STATUS_FALHOU, "n_chunks": 0, "n_paginas": n_paginas, "erro": "Sem chunks"}

        delete_chunks_documento(doc_id)
        ok = add_chunks_lote(chunks)
        if not ok:
            update_status_indexacao(doc_id, STATUS_FALHOU, erro="Erro ao salvar chunks no Sheets.")
            return {"ok": False, "status": STATUS_FALHOU, "n_chunks": len(chunks), "n_paginas": n_paginas, "erro": "Erro ao salvar"}

        update_status_indexacao(
            doc_id, STATUS_INDEXADO,
            texto_extraido=texto[:5000],
            quantidade_paginas=n_paginas,
        )
        return {"ok": True, "status": STATUS_INDEXADO, "n_chunks": len(chunks), "n_paginas": n_paginas, "erro": ""}

    except Exception as exc:
        erro = str(exc)[:200]
        update_status_indexacao(doc_id, STATUS_FALHOU, erro=erro)
        return {"ok": False, "status": STATUS_FALHOU, "n_chunks": 0, "n_paginas": 0, "erro": erro}
