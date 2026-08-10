"""Localização de Relatórios Técnicos e documentos da Biblioteca Técnica por
texto natural, para uso pelo Assistente Técnico no chat — "quero o último
relatório de termografia", "resuma esse manual", etc.

Módulo sem Streamlit — funções puras sobre dados já carregados via
sheets.py, mesmo estilo de comparativo.py/executive_summary.py.

SEGURANÇA: toda função que recebe client_id assume que ele já veio da
sessão (current_client_id()) ou de uma seleção de staff já autenticada —
nunca de texto livre do usuário. As funções de localização sempre usam os
getters já filtrados de sheets.py (get_technical_reports(staff=False),
get_documentos_tecnicos(staff=False)) — nunca leem a planilha direto.
"""
from __future__ import annotations

import datetime as _dt
import re
import unicodedata

import pandas as pd

import sheets

# ── Normalização de texto ─────────────────────────────────────────────────────


def _norm(s: str) -> str:
    """minúsculas, sem acento, sem espaço duplicado."""
    s = unicodedata.normalize("NFD", str(s or "").lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokens(s: str) -> set[str]:
    return {t for t in _norm(s).split() if len(t) > 2}


# ── Tipo de relatório (texto natural → Tipo_Servico real) ────────────────────

# Aliases conhecidos — a chave é o que o USUÁRIO pode escrever (já
# normalizado), o valor é uma substring que deve aparecer no Tipo_Servico
# real (também normalizado) para considerar match. Isso é resiliente a
# valores de Tipo_Servico que não estão fixos num enum (ex.: "Ordem de
# Assistência (OAT)" veio da integração com o App Relatórios, não do
# _TIPOS_SERVICO da Supervisão) — sempre checa contra os valores REAIS que
# existem nos relatórios do cliente, nunca um enum fixo hardcoded.
_ALIASES_TIPO = {
    "termografia": ["termografia", "termico", "térmico"],
    "termico": ["termografia", "termico", "térmico"],
    "vibracao": ["vibracao", "vibração"],
    "vibracional": ["vibracao", "vibração"],
    "alinhamento": ["alinhamento"],
    "oat": ["oat", "ordem de assistencia", "ordem de assistência"],
    "assistencia": ["oat", "ordem de assistencia", "ordem de assistência"],
    "oleo": ["oleo", "óleo"],
    "executivo": ["executivo"],
    "visita": ["visita tecnica", "visita técnica"],
    "predativa": ["preditiva"],
    "preditiva": ["preditiva"],
    "inspecao": ["inspecao", "inspeção"],
}


def normalizar_tipo_relatorio(client_id: str, texto: str) -> str | None:
    """Tenta mapear um trecho de texto natural ("termografia", "relatório
    de vibração") para um valor REAL de Tipo_Servico já usado nos
    relatórios publicados deste cliente. Retorna None se não achar nada
    parecido — quem chama deve então tratar como "sem filtro de tipo",
    nunca inventar um tipo que não existe.
    """
    texto_n = _norm(texto)
    if not texto_n:
        return None

    df = sheets.get_technical_reports(client_id=client_id, staff=False)
    if df.empty or "Tipo_Servico" not in df.columns:
        return None
    tipos_reais = sorted({t for t in df["Tipo_Servico"].astype(str).tolist() if t.strip()})
    if not tipos_reais:
        return None

    # 1) match direto: o texto (ou um alias dele) aparece dentro do tipo real
    candidatos_texto = [texto_n]
    for chave, aliases in _ALIASES_TIPO.items():
        if chave in texto_n:
            candidatos_texto.extend(aliases)

    for tipo_real in tipos_reais:
        tipo_n = _norm(tipo_real)
        if any(c in tipo_n or tipo_n in c for c in candidatos_texto):
            return tipo_real

    return None


# ── Ativo (texto natural → Ativo_Id) ──────────────────────────────────────────


def resolver_ativo_por_nome(client_id: str, texto: str) -> list[dict]:
    """Resolve um trecho de texto ("Motor Principal", "Compressor 01",
    "MYCOM") para os ativos do cliente cujo nome/tag combina.

    Retorna lista de {"id", "nome"} — 0 (nada encontrado), 1 (uso direto,
    sem ambiguidade) ou N (ambíguo — quem chama deve perguntar qual, nunca
    escolher um sozinho).
    """
    texto_n = _norm(texto)
    if not texto_n:
        return []

    df = sheets.get_all_ativos_sv()
    if df.empty or "Client_Id" not in df.columns:
        return []
    df = df[df["Client_Id"].astype(str).str.strip().str.lower() == client_id.strip().lower()]
    if df.empty:
        return []

    id_col   = "Id" if "Id" in df.columns else df.columns[0]
    nome_col = "Tag" if "Tag" in df.columns else id_col

    termos = _tokens(texto_n)
    candidatos = []
    for _, row in df.iterrows():
        nome = str(row.get(nome_col, "")).strip()
        nome_n = _norm(nome)
        if not nome_n:
            continue
        if texto_n in nome_n or nome_n in texto_n:
            candidatos.append({"id": str(row.get(id_col, "")).strip(), "nome": nome})
            continue
        nome_tokens = _tokens(nome_n)
        if termos and nome_tokens and (termos & nome_tokens):
            candidatos.append({"id": str(row.get(id_col, "")).strip(), "nome": nome})

    # dedup preservando ordem
    vistos = set()
    unicos = []
    for c in candidatos:
        if c["id"] not in vistos:
            vistos.add(c["id"])
            unicos.append(c)
    return unicos


# ── Período (texto natural → intervalo de datas) ──────────────────────────────

_MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}


def parse_periodo_natural(texto: str) -> tuple[_dt.date, _dt.date] | None:
    """Converte frases como "este mês", "mês passado", "julho",
    "julho de 2026", "últimos 30 dias" num intervalo (ini, fim).

    Retorna None para "último"/"mais recente" (não é um período — significa
    "ordene por data e pegue o primeiro", tratado por quem chama) ou quando
    nenhum padrão de data é reconhecido no texto (quem chama então não
    filtra por período)."""
    texto_n = _norm(texto)
    hoje = _dt.date.today()

    if "este mes" in texto_n or "esse mes" in texto_n:
        return hoje.replace(day=1), hoje
    if "mes passado" in texto_n or "ultimo mes" in texto_n:
        primeiro_atual = hoje.replace(day=1)
        ultimo_anterior = primeiro_atual - _dt.timedelta(days=1)
        return ultimo_anterior.replace(day=1), ultimo_anterior

    m = re.search(r"ultimos?\s+(\d+)\s+dias", texto_n)
    if m:
        dias = int(m.group(1))
        return hoje - _dt.timedelta(days=dias), hoje

    for nome_mes, num_mes in _MESES.items():
        if nome_mes in texto_n:
            ano = hoje.year
            m_ano = re.search(r"(20\d{2})", texto_n)
            if m_ano:
                ano = int(m_ano.group(1))
            ini = _dt.date(ano, num_mes, 1)
            fim = (_dt.date(ano + 1, 1, 1) if num_mes == 12 else _dt.date(ano, num_mes + 1, 1)) - _dt.timedelta(days=1)
            return ini, fim

    return None


# ── Nome do ativo (Ativo_Id → Tag, para exibição em cards) ───────────────────


def _nome_ativo(ativo_id: str) -> str:
    if not ativo_id:
        return ""
    df = sheets.get_all_ativos_sv()
    if df.empty or "Id" not in df.columns:
        return ativo_id
    match = df[df["Id"].astype(str).str.strip() == ativo_id.strip()]
    if match.empty:
        return ativo_id
    return str(match.iloc[0].get("Tag", ativo_id)).strip() or ativo_id


# ── Localização de Relatórios Técnicos ────────────────────────────────────────


def localizar_relatorios(
    client_id: str,
    tipo: str | None = None,
    ativo_id: str | None = None,
    periodo: tuple[_dt.date, _dt.date] | None = None,
    limit: int = 10,
) -> list[dict]:
    """Localiza relatórios técnicos PUBLICADOS do cliente, com filtros
    opcionais. Usa sheets.get_technical_reports(staff=False) — já
    client-isolado e restrito a Status=='Publicado', já ordenado por data
    decrescente (o mais recente primeiro, cobrindo "último relatório").

    Retorna lista de dicts com campos prontos para o card do chat."""
    df = sheets.get_technical_reports(client_id=client_id, staff=False)
    if df.empty:
        return []

    if tipo:
        df = df[df["Tipo_Servico"].astype(str).str.strip() == tipo.strip()]
    if ativo_id:
        df = df[df["Ativo_Id"].astype(str).str.strip() == ativo_id.strip()]
    if periodo:
        ini, fim = periodo
        _dt_col = pd.to_datetime(df["Data_Relatorio"].astype(str), dayfirst=True, errors="coerce")
        df = df[(_dt_col.dt.date >= ini) & (_dt_col.dt.date <= fim)]

    df = df.head(limit)

    resultados = []
    for _, row in df.iterrows():
        resultados.append({
            "id": str(row.get("Id", "")).strip(),
            "titulo": str(row.get("Titulo", "")).strip(),
            "tipo_servico": str(row.get("Tipo_Servico", "")).strip(),
            "severidade": str(row.get("Severidade", "")).strip(),
            "data": str(row.get("Data_Relatorio", "")).strip(),
            "ativo_id": str(row.get("Ativo_Id", "")).strip(),
            "ativo_nome": _nome_ativo(str(row.get("Ativo_Id", "")).strip()),
            "resumo": str(row.get("Resumo", "")).strip(),
            "recomendacoes": str(row.get("Recomendacoes", "")).strip(),
            "storage_path": str(row.get("Storage_Path", "")).strip(),
            "arquivo_url": str(row.get("Arquivo_Url", "")).strip(),
            "gut_prioridade": str(row.get("Gut_Prioridade", "")).strip(),
        })
    return resultados


# ── Localização de Documentos da Biblioteca Técnica ───────────────────────────


# Palavras de comando/genéricas demais para servir como termo distintivo de
# busca — "quero o manual X" não deve casar com QUALQUER título que contenha
# "manual". Tipo de documento já é filtrado separadamente (tipo_documento);
# aqui interessa o que diferencia UM documento dos outros.
_STOPWORDS_BUSCA_DOC = {
    "quero", "quer", "queria", "voce", "você", "por", "favor", "pode",
    "mostre", "mostrar", "abra", "abrir", "localize", "localizar",
    "encontre", "encontrar", "cade", "cadê", "onde", "esta", "está",
    "tem", "tem algum", "algum", "alguma", "sobre", "para", "com",
    "manual", "documento", "biblioteca", "tecnica", "técnica",
    "catalogo", "catálogo", "datasheet", "ficha",
}


def localizar_documentos(
    client_id: str,
    texto: str | None = None,
    fabricante: str | None = None,
    modelo: str | None = None,
    ativo_id: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Localiza documentos da Biblioteca Técnica autorizados para o cliente,
    com filtros opcionais. Usa sheets.get_documentos_tecnicos(staff=False) —
    já filtra Status=='Ativo', Visibilidade e Cliente_Id (público ou do
    próprio cliente); nunca expõe documentos internos ou de outro cliente.
    """
    df = sheets.get_documentos_tecnicos(client_id=client_id, staff=False)
    if df.empty:
        return []

    if texto:
        termos = _tokens(texto) - _STOPWORDS_BUSCA_DOC
        texto_n = _norm(texto)
        texto_desp = texto_n.replace(" ", "")

        def _haystack(row) -> str:
            return _norm(
                str(row.get("Titulo", "")) + " " +
                str(row.get("Fabricante", "")) + " " +
                str(row.get("Modelo", "")) + " " +
                str(row.get("Palavras_Chave", ""))
            )

        def _bate_estrito(row) -> bool:
            haystack = _haystack(row)
            if texto_n and texto_n in haystack:
                return True
            return bool(termos & _tokens(haystack))

        def _bate_tolerante(row) -> bool:
            # Sem espaço: cobre nomes de produto grafados junto no cadastro
            # ("Myprotouch") mas separado na fala do usuário ("Mypro
            # Touch") — substring/token exato falharia nesse caso. Mais
            # permissivo (>=50% dos termos), por isso só usado quando a
            # busca estrita não encontra nada.
            haystack = _haystack(row)
            haystack_desp = haystack.replace(" ", "")
            if texto_desp and texto_desp in haystack_desp:
                return True
            if not termos:
                return False
            hits = sum(1 for t in termos if t in haystack or t in haystack_desp)
            return hits >= max(1, len(termos) // 2)

        if termos or texto_n:
            df_estrito = df[df.apply(_bate_estrito, axis=1)]
            df = df_estrito if not df_estrito.empty else df[df.apply(_bate_tolerante, axis=1)]
    if fabricante:
        df = df[df["Fabricante"].astype(str).str.strip().str.lower() == fabricante.strip().lower()]
    if modelo:
        df = df[df["Modelo"].astype(str).str.strip().str.lower() == modelo.strip().lower()]
    if ativo_id:
        df = df[df["Ativo_Id"].astype(str).str.strip() == ativo_id.strip()]

    if "Created_At" in df.columns:
        _dt_col = pd.to_datetime(df["Created_At"].astype(str), dayfirst=True, errors="coerce")
        df = df.assign(_dt=_dt_col).sort_values("_dt", ascending=False).drop(columns=["_dt"])

    df = df.head(limit)

    resultados = []
    for _, row in df.iterrows():
        resultados.append({
            "id": str(row.get("Id", "")).strip(),
            "titulo": str(row.get("Titulo", "")).strip(),
            "tipo_documento": str(row.get("Tipo_Documento", "")).strip(),
            "fabricante": str(row.get("Fabricante", "")).strip(),
            "modelo": str(row.get("Modelo", "")).strip(),
            "ativo_id": str(row.get("Ativo_Id", "")).strip(),
            "ativo_nome": _nome_ativo(str(row.get("Ativo_Id", "")).strip()),
            "resumo": str(row.get("Resumo", "")).strip(),
            "storage_path": str(row.get("Storage_Path", "")).strip(),
            "arquivo_url": str(row.get("Arquivo_Url", "")).strip(),
            "status_indexacao": str(row.get("Indexado_Para_Ia", "")).strip(),
        })
    return resultados


# ── Resumo de Relatórios e Documentos (com/sem Claude) ────────────────────────

_TIPOS_RESUMO_VALIDOS = {"curto", "detalhado", "gerencia", "operador", "manutencao"}

_PROMPTS_RESUMO = {
    "curto": "Resuma em até 4 linhas, direto ao ponto, para leitura rápida no chat.",
    "detalhado": "Faça um resumo técnico completo, cobrindo achados, causas e recomendações.",
    "gerencia": "Resuma em linguagem executiva, focando impacto, risco e prioridade — sem jargão técnico excessivo.",
    "operador": "Resuma em linguagem prática e direta para o operador do equipamento em campo — o que ele precisa saber e fazer.",
    "manutencao": "Resuma com foco técnico de manutenção — o que verificar, peças/ajustes envolvidos e prazos recomendados.",
}


def _chamar_claude_resumo(system_prompt: str, conteudo: str, tipo_resumo: str) -> str | None:
    """Chama a Claude para gerar um resumo. Retorna None se
    ANTHROPIC_API_KEY não estiver configurada ou a chamada falhar — quem
    chama deve então usar o fallback estruturado (mesmo padrão de
    ai_assistant.query_ai/_fallback_engine)."""
    import os
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        instrucao = _PROMPTS_RESUMO.get(tipo_resumo, _PROMPTS_RESUMO["curto"])
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": f"{conteudo}\n\n---\nINSTRUÇÃO: {instrucao}"}],
        )
        return message.content[0].text.strip()
    except Exception:
        return None


_SYSTEM_PROMPT_RESUMO = """\
Você é o Assistente Técnico Pred.IO. Resuma SOMENTE com base no conteúdo
fornecido nesta mensagem — nunca invente dado técnico, especificação,
prazo ou recomendação que não esteja no conteúdo. A fonte é sempre
"Pred.IO". Responda em português, texto simples (sem markdown de título),
pronto para exibição direta no chat."""


def summarize_technical_report(report_id: str, client_id: str, tipo_resumo: str = "curto") -> dict:
    """Resume um relatório técnico publicado. SEMPRE revalida
    Cliente_Id/Status no backend — nunca confia que o report_id já foi
    validado antes de chegar aqui.

    Retorna {"ok": bool, "resumo": str, "erro": str|None}."""
    if tipo_resumo not in _TIPOS_RESUMO_VALIDOS:
        tipo_resumo = "curto"

    rep = sheets.get_technical_report_by_id(report_id)
    if not rep:
        return {"ok": False, "resumo": "", "erro": "Relatório não encontrado."}
    if rep.get("Cliente_Id", "").strip().lower() != (client_id or "").strip().lower():
        return {"ok": False, "resumo": "", "erro": "Relatório não encontrado."}
    if rep.get("Status", "").strip() != "Publicado":
        return {"ok": False, "resumo": "", "erro": "Relatório não encontrado."}

    partes = [
        f"Título: {rep.get('Titulo','')}",
        f"Tipo: {rep.get('Tipo_Servico','')}",
        f"Severidade: {rep.get('Severidade','')}",
        f"Data: {rep.get('Data_Relatorio','')}",
    ]
    if rep.get("Resumo"):
        partes.append(f"Resumo estruturado: {rep['Resumo']}")
    if rep.get("Recomendacoes"):
        partes.append(f"Recomendações: {rep['Recomendacoes']}")
    if rep.get("Conclusao"):
        partes.append(f"Conclusão: {rep['Conclusao']}")

    chunks_df = sheets.get_chunks_relatorio(report_id, client_id)
    tem_chunks = not chunks_df.empty
    if tem_chunks:
        partes.append("Conteúdo indexado do PDF:")
        for _, ch in chunks_df.iterrows():
            conteudo = str(ch.get("Conteudo", "")).strip()
            if conteudo:
                partes.append(f"[{ch.get('Titulo_Secao','')}]: {conteudo}")

    tem_conteudo_estruturado = any(rep.get(k) for k in ("Resumo", "Recomendacoes", "Conclusao"))
    if not tem_conteudo_estruturado and not tem_chunks:
        return {
            "ok": False, "resumo": "",
            "erro": "Este relatório ainda não está indexado — não há conteúdo suficiente para resumir.",
        }

    conteudo = "\n".join(partes)
    resumo_ia = _chamar_claude_resumo(_SYSTEM_PROMPT_RESUMO, conteudo, tipo_resumo)
    if resumo_ia:
        return {"ok": True, "resumo": resumo_ia, "erro": None}

    # Fallback sem IA: concatena os campos estruturados disponíveis
    fallback_partes = [p for p in partes if not p.startswith("Conteúdo indexado") and ":" in p]
    return {"ok": True, "resumo": " | ".join(fallback_partes), "erro": None}


def summarize_technical_document(document_id: str, client_id: str, tipo_resumo: str = "curto") -> dict:
    """Resume um documento da Biblioteca Técnica. SEMPRE revalida acesso via
    get_documentos_tecnicos(staff=False) — o mesmo filtro de
    Status/Visibilidade/Cliente_Id usado para exibir a lista ao cliente.

    Retorna {"ok": bool, "resumo": str, "erro": str|None}."""
    if tipo_resumo not in _TIPOS_RESUMO_VALIDOS:
        tipo_resumo = "curto"

    df = sheets.get_documentos_tecnicos(client_id=client_id, staff=False)
    if df.empty or "Id" not in df.columns:
        return {"ok": False, "resumo": "", "erro": "Documento não encontrado."}
    match = df[df["Id"].astype(str).str.strip() == document_id.strip()]
    if match.empty:
        return {"ok": False, "resumo": "", "erro": "Documento não encontrado."}
    doc = match.iloc[0]

    partes = [
        f"Título: {doc.get('Titulo','')}",
        f"Tipo: {doc.get('Tipo_Documento','')}",
    ]
    if doc.get("Fabricante"):
        partes.append(f"Fabricante: {doc['Fabricante']}")
    if doc.get("Modelo"):
        partes.append(f"Modelo: {doc['Modelo']}")
    if doc.get("Resumo"):
        partes.append(f"Resumo cadastrado: {doc['Resumo']}")

    chunks_df = sheets.get_chunks_documento(document_id)
    tem_chunks = not chunks_df.empty
    if tem_chunks:
        partes.append("Conteúdo indexado do documento:")
        for _, ch in chunks_df.iterrows():
            conteudo = str(ch.get("Conteudo", "")).strip()
            if conteudo:
                partes.append(f"[{ch.get('Titulo_Secao','')}]: {conteudo}")

    tem_resumo_cadastrado = bool(str(doc.get("Resumo", "")).strip())
    if not tem_resumo_cadastrado and not tem_chunks:
        return {
            "ok": False, "resumo": "",
            "erro": ("Encontrei o documento, mas ele ainda não está indexado para consulta pela IA. "
                     "Você pode abrir o documento normalmente. A equipe Pred.IO precisa processá-lo "
                     "para habilitar resumo e perguntas técnicas."),
        }

    conteudo = "\n".join(partes)
    resumo_ia = _chamar_claude_resumo(_SYSTEM_PROMPT_RESUMO, conteudo, tipo_resumo)
    if resumo_ia:
        return {"ok": True, "resumo": resumo_ia, "erro": None}

    fallback_partes = [p for p in partes if not p.startswith("Conteúdo indexado") and ":" in p]
    return {"ok": True, "resumo": " | ".join(fallback_partes), "erro": None}


# ── Orquestração — roteamento de perguntas do chat ────────────────────────────
#
# rotear_pergunta() é chamado ANTES de ai_assistant.query_ai(). Se a
# pergunta for sobre localizar/exibir/resumir um Relatório Técnico ou
# documento da Biblioteca, resolve aqui e retorna um dict pronto para a UI
# do chat. Caso contrário retorna None — quem chama segue para
# ai_assistant.query_ai() sem nenhuma mudança nesse caminho (esse já cobre
# perguntas de conteúdo genéricas sobre relatórios/documentos publicados,
# ver ai_assistant._build_context_str).

_KW_REL = {
    "relatorio", "relatorios", "termografia", "vibracao", "oat",
    "assistencia", "laudo", "inspecao", "preditiva",
}
_KW_DOC = {
    "manual", "documento", "documentos", "biblioteca", "datasheet",
    "catalogo", "procedimento",
}
_KW_RESUMIR = {"resuma", "resumo", "resumir", "resume"}
_KW_PRONOME = {
    "esse", "essa", "este", "esta", "aquele", "aquela",
    "desse", "dessa", "isso", "ele", "ela",
}
_KW_LOCALIZAR = {
    "quero", "mostre", "mostrar", "abra", "abrir", "localize", "localizar",
    "encontre", "encontrar", "cade", "cadê", "ultimo", "ultimos", "recente",
    "quais",
}
# Nota: "qual" (singular) foi deliberadamente deixado de fora — é comum
# demais em perguntas de conteúdo genéricas ("qual foi a recomendação?",
# "qual o modelo?") que devem cair no fluxo normal do Assistente, não
# virar uma busca de entidade. "quais" (plural) é mais específico de
# listagem e por isso ficou.
_KW_CONTEUDO = [
    "fala sobre", "falam sobre", "menciona", "mencionam", "algo sobre",
    "trata de", "aborda", "abordam",
]

_STOPWORDS_BUSCA_CONTEUDO = _STOPWORDS_BUSCA_DOC | _KW_REL | _KW_LOCALIZAR | {
    "falam", "fala", "mencionam", "menciona", "algo", "trata",
    "aborda", "abordam", "que", "os", "as", "dos", "das",
}


def _extrair_assunto(texto: str) -> str:
    """Extrai o "assunto" de uma pergunta de busca por conteúdo — "quais
    relatórios falam sobre desalinhamento?" -> "desalinhamento". Sem
    "sobre", cai para os termos que sobram depois de remover palavras de
    comando/genéricas."""
    m = re.search(r"sobre\s+(.+?)[\?\.!]*$", texto, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    termos = [t for t in _tokens(texto) if t not in _STOPWORDS_BUSCA_CONTEUDO]
    return " ".join(termos)


def _resumir_relatorio_atual(report_id: str, client_id: str) -> dict:
    r = summarize_technical_report(report_id, client_id)
    if not r["ok"]:
        return {"tipo": "nao_encontrado", "mensagem": r["erro"]}
    return {"tipo": "resumo", "texto": r["resumo"], "current_report_id": report_id}


def _resumir_documento_atual(document_id: str, client_id: str) -> dict:
    r = summarize_technical_document(document_id, client_id)
    if not r["ok"]:
        return {"tipo": "nao_encontrado", "mensagem": r["erro"]}
    return {"tipo": "resumo", "texto": r["resumo"], "current_document_id": document_id}


def _resolver_e_resumir_relatorios(reps: list[dict], client_id: str, periodo) -> dict:
    if not reps:
        return {"tipo": "nao_encontrado", "mensagem": "Não encontrei nenhum relatório publicado com esses critérios."}
    if len(reps) == 1:
        return _resumir_relatorio_atual(reps[0]["id"], client_id)
    if periodo:
        return _resumo_consolidado_relatorios(reps, client_id)
    return {"tipo": "ambiguo", "itens": reps, "mensagem": "Encontrei mais de um relatório. Qual você quer resumir?"}


def _resolver_e_resumir_documentos(docs: list[dict], client_id: str) -> dict:
    if not docs:
        return {"tipo": "nao_encontrado", "mensagem": "Não encontrei nenhum documento com essa descrição."}
    if len(docs) == 1:
        return _resumir_documento_atual(docs[0]["id"], client_id)
    return {"tipo": "ambiguo", "itens": docs, "mensagem": "Encontrei mais de um documento. Qual você quer resumir?"}


def _resumo_consolidado_relatorios(reps: list[dict], client_id: str) -> dict:
    """Resumo único cobrindo vários relatórios (ex.: "resuma os relatórios
    dos últimos 30 dias"). Reaproveita _chamar_claude_resumo com o
    conteúdo de todos concatenado; sem Claude configurada, cai para a
    lista estruturada mesma (nunca inventa uma síntese sem base)."""
    partes = []
    for r in reps:
        bloco = [
            f"- {r['titulo']} ({r.get('tipo_servico','')}, {r.get('data','')}, "
            f"{r.get('ativo_nome') or r.get('ativo_id','')})"
        ]
        if r.get("resumo"):
            bloco.append(f"  Resumo: {r['resumo']}")
        if r.get("recomendacoes"):
            bloco.append(f"  Recomendações: {r['recomendacoes']}")
        partes.append("\n".join(bloco))
    conteudo = "\n".join(partes)
    resumo_ia = _chamar_claude_resumo(_SYSTEM_PROMPT_RESUMO, conteudo, "curto")
    texto = resumo_ia or conteudo
    return {"tipo": "resumo_consolidado", "texto": texto, "relatorios": [r["id"] for r in reps]}


def _cruzar_relatorio_documento(client_id: str, pergunta: str, current_report_id: str) -> dict:
    """Cruza um relatório (o atual da sessão, ou o mais recente publicado)
    com o conteúdo da Biblioteca Técnica sobre o mesmo assunto. Sempre
    revalida current_report_id; sem um válido, usa o relatório mais
    recente publicado do cliente."""
    rep = None
    if current_report_id:
        r = summarize_technical_report(current_report_id, client_id, tipo_resumo="detalhado")
        if r["ok"]:
            rep = {"id": current_report_id, "resumo": r["resumo"]}
    if rep is None:
        reps = localizar_relatorios(client_id, limit=1)
        if reps:
            r = summarize_technical_report(reps[0]["id"], client_id, tipo_resumo="detalhado")
            if r["ok"]:
                rep = {"id": reps[0]["id"], "resumo": r["resumo"]}
    if rep is None:
        return {
            "tipo": "nao_encontrado",
            "mensagem": "Não encontrei nenhum relatório publicado para cruzar com a Biblioteca Técnica.",
        }

    assunto = _extrair_assunto(pergunta) or rep["resumo"][:60]
    hits = sheets.buscar_chunks_documentos(client_id, assunto, top_n=5)
    if not hits:
        return {
            "tipo": "resumo",
            "texto": f"{rep['resumo']}\n\nNão encontrei nenhum documento da Biblioteca Técnica sobre esse assunto para comparar.",
            "current_report_id": rep["id"],
        }

    conteudo = (
        f"RELATÓRIO TÉCNICO:\n{rep['resumo']}\n\n"
        f"BIBLIOTECA TÉCNICA — trechos relacionados:\n" +
        "\n".join(f"- {h['conteudo']}" for h in hits)
    )
    resumo_ia = _chamar_claude_resumo(_SYSTEM_PROMPT_RESUMO, conteudo, "detalhado")
    texto = resumo_ia or conteudo
    return {"tipo": "cruzamento", "texto": texto, "current_report_id": rep["id"]}


def rotear_pergunta(
    pergunta: str,
    client_id: str,
    current_report_id: str = "",
    current_document_id: str = "",
) -> dict | None:
    """Detecta se a pergunta é sobre localizar/exibir/resumir um Relatório
    Técnico ou documento da Biblioteca Técnica; se sim, resolve e retorna
    um dict pronto para a UI do chat. Caso contrário, retorna None — quem
    chama (page_assistente.py) segue para ai_assistant.query_ai() sem
    nenhuma mudança nesse caminho.

    SEGURANÇA: client_id sempre da sessão. current_report_id/
    current_document_id são SEMPRE revalidados aqui (via
    summarize_technical_report/document, que checam Cliente_Id/Status de
    novo) antes de qualquer uso — nunca confia que o valor guardado em
    st.session_state ainda é válido ou pertence a este cliente.
    """
    if not client_id or not pergunta or not pergunta.strip():
        return None

    q = _norm(pergunta)
    tk = _tokens(pergunta)

    quer_resumir = bool(_KW_RESUMIR & tk)
    quer_localizar = bool(_KW_LOCALIZAR & tk)
    quer_conteudo = any(kw in q for kw in _KW_CONTEUDO)

    # Gate principal: só entra no fluxo de localizar/resumir com um verbo
    # de ação claro — só mencionar "relatório"/"manual" numa frase (ex.:
    # "o relatório de vibração está atrasado?") não deve virar um card,
    # cai no fluxo normal do Assistente.
    if not (quer_resumir or quer_localizar or quer_conteudo):
        return None

    is_rel = bool(_KW_REL & tk) or bool(normalizar_tipo_relatorio(client_id, pergunta))
    is_doc = bool(_KW_DOC & tk)
    tem_pronome = bool(_KW_PRONOME & tk)

    periodo = parse_periodo_natural(pergunta)
    tipo_rel = normalizar_tipo_relatorio(client_id, pergunta) if is_rel else None
    ativo_candidatos = resolver_ativo_por_nome(client_id, pergunta)
    ativo_id = ativo_candidatos[0]["id"] if len(ativo_candidatos) == 1 else None

    # Cruzamento relatório + biblioteca — pergunta menciona as duas fontes
    # juntas (não é simplesmente "resuma esse relatório/manual").
    if is_rel and is_doc and not (quer_resumir and tem_pronome):
        return _cruzar_relatorio_documento(client_id, pergunta, current_report_id)

    # "Resuma esse relatório/manual" — usa o item atual da sessão, sem
    # tipo/ativo/período novo mencionado (senão seria um alvo novo).
    if quer_resumir and tem_pronome and not tipo_rel and not ativo_id and not periodo:
        if is_doc and current_document_id:
            return _resumir_documento_atual(current_document_id, client_id)
        if current_report_id:
            return _resumir_relatorio_atual(current_report_id, client_id)
        if current_document_id:
            return _resumir_documento_atual(current_document_id, client_id)
        return {
            "tipo": "nao_encontrado",
            "mensagem": "Não identifiquei qual relatório ou documento você quer resumir. "
                        "Pode dizer o tipo, o ativo ou o nome do documento?",
        }

    # "Resuma o relatório de vibração / o manual X" (alvo novo) ou "resuma
    # os relatórios dos últimos 30 dias" (resumo consolidado).
    if quer_resumir and (is_doc or is_rel):
        if is_doc and not is_rel:
            docs = localizar_documentos(client_id, texto=pergunta, ativo_id=ativo_id, limit=5)
            return _resolver_e_resumir_documentos(docs, client_id)
        reps = localizar_relatorios(client_id, tipo=tipo_rel, ativo_id=ativo_id, periodo=periodo, limit=10)
        return _resolver_e_resumir_relatorios(reps, client_id, periodo)

    # Busca por conteúdo — "quais relatórios falam sobre desalinhamento?"
    if quer_conteudo:
        assunto = _extrair_assunto(pergunta)
        if not assunto:
            return None
        if is_doc and not is_rel:
            hits = sheets.buscar_chunks_documentos(client_id, assunto, top_n=8)
            ids_ordenados = list(dict.fromkeys(h["documento_id"] for h in hits))
            por_id = {d["id"]: d for d in localizar_documentos(client_id, limit=50)}
            itens = [por_id[i] for i in ids_ordenados if i in por_id]
            if not itens:
                return {"tipo": "nao_encontrado", "mensagem": f'Não encontrei documentos que mencionem "{assunto}".'}
            return {"tipo": "lista_documentos", "itens": itens[:5]}

        hits = sheets.buscar_chunks_relatorios(client_id, assunto, top_n=8)
        ids_ordenados = list(dict.fromkeys(h["report_id"] for h in hits))
        por_id = {r["id"]: r for r in localizar_relatorios(client_id, limit=50)}
        itens = [por_id[i] for i in ids_ordenados if i in por_id]
        if not itens:
            return {"tipo": "nao_encontrado", "mensagem": f'Não encontrei relatórios que mencionem "{assunto}".'}
        return {"tipo": "lista_relatorios", "itens": itens[:5]}

    # Localizar/mostrar — sem pedido de resumo.
    if quer_localizar:
        if is_doc and not is_rel:
            docs = localizar_documentos(client_id, texto=pergunta, ativo_id=ativo_id, limit=5)
            if not docs:
                return {
                    "tipo": "nao_encontrado",
                    "mensagem": "Não encontrei nenhum documento com essa descrição na Biblioteca Técnica.",
                }
            if len(docs) == 1:
                return {"tipo": "documento_card", "item": docs[0], "current_document_id": docs[0]["id"]}
            return {"tipo": "lista_documentos", "itens": docs}

        reps = localizar_relatorios(client_id, tipo=tipo_rel, ativo_id=ativo_id, periodo=periodo, limit=5)
        if not reps:
            return {"tipo": "nao_encontrado", "mensagem": "Não encontrei nenhum relatório publicado com esses critérios."}
        if len(reps) == 1:
            return {"tipo": "relatorio_card", "item": reps[0], "current_report_id": reps[0]["id"]}
        return {"tipo": "lista_relatorios", "itens": reps}

    return None
