"""Google Sheets — conexão e operações de leitura/escrita."""
import base64
import json
import os
import re
import uuid
from datetime import datetime, timedelta

import gspread
import pandas as pd
import streamlit as st

SHEET_ID = "1cyDz6nuZ9ro7Inq-DNg9OH9d7GNn17WHZSIikkQ6hOA"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def _build_creds():
    """Retorna credenciais google-auth (gspread 6.x). Tenta todas as fontes."""
    from google.oauth2.service_account import Credentials as _SA

    # 1. st.secrets
    try:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            return _SA.from_service_account_info(info, scopes=SCOPE)
    except Exception:
        pass

    # 2. env var base64
    try:
        import base64, json as _json
        raw_b64 = os.environ.get("GCP_CREDENTIALS_B64", "")
        if raw_b64:
            raw = base64.b64decode(raw_b64).decode("utf-8")
            return _SA.from_service_account_info(_json.loads(raw), scopes=SCOPE)
    except Exception:
        pass

    # 3. env var JSON string
    try:
        import json as _json
        raw_j = os.environ.get("GCP_CREDENTIALS_JSON", "")
        if raw_j:
            return _SA.from_service_account_info(_json.loads(raw_j), scopes=SCOPE)
    except Exception:
        pass

    # 4. arquivo em disco
    for path in ("/etc/secrets/credentials.json", "credentials.json"):
        try:
            if os.path.exists(path):
                return _SA.from_service_account_file(path, scopes=SCOPE)
        except Exception:
            pass

    return None


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    try:
        creds = _build_creds()
        if creds is None:
            st.error("Credenciais não encontradas. Configure GCP_CREDENTIALS_B64 no Render.")
            st.stop()
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Planilha não encontrada.")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        st.stop()


@st.cache_data(ttl=30, show_spinner=False)
def load_sheet(tab_name: str) -> pd.DataFrame:
    """Carrega uma aba e normaliza os nomes das colunas. Cache de 30 s."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet(tab_name)
        try:
            records = ws.get_all_records()
        except Exception:
            # Fallback para abas com headers duplicados/vazios (ex.: Ativos corrompida).
            # Lê valores brutos, descarta colunas sem nome e filtra só linhas com dados
            # nos índices válidos (ignora linhas com dados deslocados para colunas extras).
            all_values = ws.get_all_values()
            if not all_values:
                return pd.DataFrame()
            raw_headers = all_values[0]
            valid = [(i, h) for i, h in enumerate(raw_headers) if h.strip()]
            if not valid:
                return pd.DataFrame()
            indices, names = zip(*valid)
            rows = []
            for row in all_values[1:]:
                cells = [row[i] if i < len(row) else "" for i in indices]
                if any(c.strip() for c in cells):
                    rows.append(dict(zip(names, cells)))
            records = rows
        df = pd.DataFrame(records)
        if not df.empty:
            df.columns = [c.strip().title() for c in df.columns]
        return df
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def append_row(tab_name: str, values: list) -> bool:
    """Adiciona uma linha ao final da aba. Cria a aba se não existir."""
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title=tab_name, rows=1000, cols=max(len(values), 26))
        ws.append_row(values, value_input_option="USER_ENTERED")
        load_sheet.clear()
        try:
            st.session_state.pop("_sheets_last_error", None)
        except Exception:
            pass
        return True
    except Exception as _e:
        try:
            st.session_state["_sheets_last_error"] = str(_e)
        except Exception:
            pass
        import logging
        logging.error("append_row(%s): %s", tab_name, _e)
        return False


# ── Helpers internos ──────────────────────────────────────────────────────────

def _gerar_id(prefixo: str = "CH") -> str:
    """Gera ID único legível: CH-20260621-A3F8D2"""
    suffix = str(uuid.uuid4()).replace("-", "")[:6].upper()
    date_part = datetime.now().strftime("%Y%m%d")
    return f"{prefixo}-{date_part}-{suffix}"


def _mock_chamados() -> pd.DataFrame:
    """Dados de teste quando a planilha Chamados está vazia."""
    return pd.DataFrame([
        {
            "Id": "CH-20260618-C03001",
            "Empresa": "Coca-Cola",
            "Client_Id": "coca-cola",
            "Email": "joao@cocacola.com",
            "Titulo": "Ruído anormal após partida",
            "Descricao": "Cliente informa ruído anormal e oscilação operacional.",
            "Planta": "Jacarepaguá",
            "Equipamento": "Compressor C-03",
            "Prioridade": "Crítica",
            "Status": "Em andamento",
            "Responsavel": "Marcos",
            "Data_Abertura": "18/06/2026 07:45:00",
            "Data_Atualizacao": "20/06/2026 11:00:00",
            "Data_Encerramento": "",
        },
        {
            "Id": "CH-20260619-M10002",
            "Empresa": "Sibele Alimentos",
            "Client_Id": "sibele alimentos",
            "Email": "maria@sibele.com",
            "Titulo": "Solicitação de análise de óleo",
            "Descricao": "Cliente solicita avaliação do último resultado da análise de óleo.",
            "Planta": "Rio de Janeiro",
            "Equipamento": "Motor M-10",
            "Prioridade": "Média",
            "Status": "Em análise",
            "Responsavel": "Marcos",
            "Data_Abertura": "19/06/2026 14:30:00",
            "Data_Atualizacao": "19/06/2026 16:00:00",
            "Data_Encerramento": "",
        },
        {
            "Id": "CH-20260620-B204003",
            "Empresa": "Coca-Cola",
            "Client_Id": "coca-cola",
            "Email": "joao@cocacola.com",
            "Titulo": "Aumento de vibração",
            "Descricao": "Cliente relata aumento de vibração após última partida.",
            "Planta": "Jacarepaguá",
            "Equipamento": "Bomba B-204",
            "Prioridade": "Alta",
            "Status": "Aberto",
            "Responsavel": "",
            "Data_Abertura": "20/06/2026 09:15:00",
            "Data_Atualizacao": "",
            "Data_Encerramento": "",
        },
    ])


def _mock_mensagens(chamado_id: str) -> pd.DataFrame:
    """Mensagens de teste por chamado."""
    mocks = {
        "CH-20260618-C03001": [
            {
                "Id": "MSG-00001",
                "Id_Chamado": "CH-20260618-C03001",
                "Autor": "joao@cocacola.com",
                "Autor_Tipo": "cliente",
                "Mensagem": (
                    "Urgente: o Compressor C-03 apresentou ruído anormal após a partida "
                    "desta manhã. Há oscilação na operação e o operador relatou cheiro de "
                    "queimado na área. Paramos a máquina preventivamente."
                ),
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "mensagem_cliente",
                "Data": "18/06/2026 07:45:00",
            },
            {
                "Id": "MSG-00002",
                "Id_Chamado": "CH-20260618-C03001",
                "Autor": "sistema",
                "Autor_Tipo": "sistema",
                "Mensagem": "Status alterado: Aberto → Em andamento",
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "alteracao_status",
                "Data": "18/06/2026 08:00:00",
            },
            {
                "Id": "MSG-00003",
                "Id_Chamado": "CH-20260618-C03001",
                "Autor": "Marcos",
                "Autor_Tipo": "funcionario",
                "Mensagem": (
                    "João, recebemos o chamado com prioridade crítica. Nossa equipe está "
                    "sendo mobilizada. Por favor mantenha a máquina desligada por segurança. "
                    "Nosso técnico chegará à planta até as 14h de hoje."
                ),
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "resposta_predio",
                "Data": "18/06/2026 08:05:00",
            },
            {
                "Id": "MSG-00004",
                "Id_Chamado": "CH-20260618-C03001",
                "Autor": "Marcos",
                "Autor_Tipo": "funcionario",
                "Mensagem": (
                    "VERIFICAR: histórico indica última manutenção há 210 dias — "
                    "acima do limite de 180 dias. Solicitar ao cliente o log do painel "
                    "de controle antes de enviar técnico."
                ),
                "Visivel_Cliente": "0",
                "Tipo_Mensagem": "observacao_interna",
                "Data": "18/06/2026 08:10:00",
            },
        ],
        "CH-20260619-M10002": [
            {
                "Id": "MSG-00005",
                "Id_Chamado": "CH-20260619-M10002",
                "Autor": "maria@sibele.com",
                "Autor_Tipo": "cliente",
                "Mensagem": (
                    "Solicitamos avaliação do resultado da última análise de óleo do "
                    "Motor M-10. O relatório chegou mas gostaríamos de uma explicação "
                    "técnica dos resultados."
                ),
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "mensagem_cliente",
                "Data": "19/06/2026 14:30:00",
            },
            {
                "Id": "MSG-00006",
                "Id_Chamado": "CH-20260619-M10002",
                "Autor": "Marcos",
                "Autor_Tipo": "funcionario",
                "Mensagem": (
                    "Olá Maria. Recebemos sua solicitação e já estamos analisando os "
                    "resultados do Motor M-10. Identificamos que o índice de viscosidade "
                    "está no limite superior. Retornaremos com o parecer técnico completo "
                    "até amanhã."
                ),
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "resposta_predio",
                "Data": "19/06/2026 16:00:00",
            },
            {
                "Id": "MSG-00007",
                "Id_Chamado": "CH-20260619-M10002",
                "Autor": "Marcos",
                "Autor_Tipo": "funcionario",
                "Mensagem": (
                    "Nota interna: verificar se a última troca de óleo foi dentro do prazo. "
                    "O histórico indica 180 dias desde a última manutenção — acima do "
                    "recomendado para esse equipamento. Confirmar com o relatório anterior."
                ),
                "Visivel_Cliente": "0",
                "Tipo_Mensagem": "observacao_interna",
                "Data": "19/06/2026 16:05:00",
            },
        ],
        "CH-20260620-B204003": [
            {
                "Id": "MSG-00008",
                "Id_Chamado": "CH-20260620-B204003",
                "Autor": "joao@cocacola.com",
                "Autor_Tipo": "cliente",
                "Mensagem": (
                    "Bom dia. Após a última partida da Bomba B-204, notamos aumento "
                    "significativo na vibração. Verificamos na semana passada e estava "
                    "normal. Preciso de uma análise urgente."
                ),
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "mensagem_cliente",
                "Data": "20/06/2026 09:15:00",
            },
        ],
    }
    rows = mocks.get(chamado_id, [])
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ── Autenticação — verificação de e-mail e gravação de senha ─────────────────

def _digits(s: str) -> str:
    """Extrai apenas dígitos de uma string (para comparação de telefones)."""
    return re.sub(r"[^\d]", "", s)


def _match_row(df: pd.DataFrame, login: str):
    """Busca uma linha por e-mail OU telefone. Retorna Series ou None."""
    valor = login.strip().lower()
    if "Email" in df.columns:
        m = df[df["Email"].str.strip().str.lower() == valor]
        if not m.empty:
            return m.iloc[0]
    if "Telefone" in df.columns:
        digs = _digits(login)
        if digs:
            df2 = df.copy()
            df2["_tel"] = df2["Telefone"].astype(str).apply(_digits)
            m = df2[df2["_tel"] == digs]
            if not m.empty:
                return m.iloc[0]
    return None


def verificar_email(login: str) -> tuple:
    """Verifica se e-mail ou telefone existe na planilha.
    Retorna (existe: bool, primeiro_acesso: bool, dados: dict | None).
    Primeiro acesso = coluna Senha vazia ou com valor 'PRIMEIRO_ACESSO'.
    """
    for tab in ("Clientes", "Usuarios"):
        df = load_sheet(tab)
        if df.empty:
            continue
        row = _match_row(df, login)
        if row is None:
            continue
        senha    = str(row.get("Senha", "")).strip()
        primeiro = senha == "" or senha.upper() == "PRIMEIRO_ACESSO"
        return True, primeiro, row.to_dict()
    return False, False, None


def set_user_senha(login: str, senha_hash: str) -> bool:
    """Grava o hash da senha buscando por e-mail ou telefone. Retorna True se OK."""
    valor = login.strip().lower()
    digs  = _digits(login)
    for tab in ("Clientes", "Usuarios"):
        try:
            ss      = get_spreadsheet()
            ws      = ss.worksheet(tab)
            raw     = ws.row_values(1)
            headers = [h.strip().title() for h in raw]
            if "Senha" not in headers:
                continue
            senha_col = headers.index("Senha") + 1

            # Tenta por e-mail
            if "Email" in headers:
                email_col = headers.index("Email") + 1
                for row_num, v in enumerate(ws.col_values(email_col), start=1):
                    if row_num == 1:
                        continue
                    if v.strip().lower() == valor:
                        ws.update_cell(row_num, senha_col, senha_hash)
                        load_sheet.clear()
                        return True

            # Tenta por telefone
            if "Telefone" in headers and digs:
                tel_col = headers.index("Telefone") + 1
                for row_num, v in enumerate(ws.col_values(tel_col), start=1):
                    if row_num == 1:
                        continue
                    if _digits(v) == digs:
                        ws.update_cell(row_num, senha_col, senha_hash)
                        load_sheet.clear()
                        return True
        except Exception:
            continue
    return False


# ── Relatórios ────────────────────────────────────────────────────────────────

def get_relatorios(client_id: str, filtros: dict | None = None) -> pd.DataFrame:
    """Retorna relatórios do cliente. Filtra SEMPRE por client_id no servidor."""
    df = load_sheet("Relatorios")
    if df.empty:
        return df
    for col in ("Empresa", "Tipo_Servico", "Planta", "Equipamento", "Mes", "Ano",
                "Data_Relatorio", "Arquivo_Url", "Titulo", "Status"):
        if col not in df.columns:
            df[col] = ""
    df = df[df["Empresa"].str.strip().str.lower() == client_id.lower()].copy()
    if filtros:
        if filtros.get("tipo"):
            df = df[df["Tipo_Servico"].str.strip().str.lower() == filtros["tipo"].lower()]
        if filtros.get("planta"):
            df = df[df["Planta"].str.strip().str.lower() == filtros["planta"].lower()]
        if filtros.get("equipamento"):
            df = df[df["Equipamento"].str.lower().str.contains(
                filtros["equipamento"].lower(), na=False)]
        if filtros.get("mes"):
            df = df[df["Mes"].astype(str) == str(filtros["mes"])]
        if filtros.get("ano"):
            df = df[df["Ano"].astype(str) == str(filtros["ano"])]
    if "Data_Relatorio" in df.columns:
        df["_dt"] = pd.to_datetime(
            df["Data_Relatorio"].astype(str), dayfirst=True, errors="coerce")
        df = df.sort_values("_dt", ascending=False).drop(columns=["_dt"])
    return df.reset_index(drop=True)


# ── Ativos ────────────────────────────────────────────────────────────────────

def get_ativos(client_id: str) -> pd.DataFrame:
    df = load_sheet("Ativos")
    if df.empty:
        return df
    if "Empresa" not in df.columns:
        return df.copy()
    return df[df["Empresa"].str.strip().str.lower() == client_id.lower()].copy()


# ── Delete genérico ──────────────────────────────────────────────────────────

def delete_row_by_id(tab_name: str, id_col: str, row_id: str) -> bool:
    """Remove uma linha de uma aba pelo valor do campo id_col."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet(tab_name)
        headers = ws.row_values(1)
        if id_col not in headers:
            return False
        col_idx = headers.index(id_col) + 1
        all_vals = ws.col_values(col_idx)
        for row_num, v in enumerate(all_vals, start=1):
            if row_num == 1:
                continue
            if str(v).strip() == str(row_id).strip():
                ws.delete_rows(row_num)
                load_sheet.clear()
                return True
        return False
    except Exception:
        return False


def delete_ativo_sv(ativo_id: str) -> bool:
    return delete_row_by_id("Ativos", "Id", ativo_id)


def delete_usuario(email: str) -> bool:
    """Remove usuário da aba Usuarios ou Clientes pelo e-mail."""
    valor = email.strip().lower()
    try:
        ss = get_spreadsheet()
        for tab in ("Usuarios", "Clientes"):
            try:
                ws = ss.worksheet(tab)
                headers = ws.row_values(1)
                if "Email" not in headers:
                    continue
                email_col = headers.index("Email") + 1
                for row_num, v in enumerate(ws.col_values(email_col), start=1):
                    if row_num == 1:
                        continue
                    if str(v).strip().lower() == valor:
                        ws.delete_rows(row_num)
                        load_sheet.clear()
                        return True
            except Exception:
                continue
        return False
    except Exception:
        return False


# ── Alertas de Supervisão (Pontos de Atenção manuais) ────────────────────────

_HEADERS_ALERTAS_SV = ["Id", "Client_Id", "Empresa", "Titulo", "Descricao", "Prioridade", "Criado_Em", "Whatsapp"]


def get_alertas_sv(client_id: str | None = None) -> pd.DataFrame:
    """Alertas criados pela supervisão. Filtra por client_id se fornecido."""
    df = load_sheet("AlertasSV")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_ALERTAS_SV:
        if col not in df.columns:
            df[col] = ""
    if client_id:
        df = df[df["Client_Id"].str.strip().str.lower() == client_id.strip().lower()]
    return df.reset_index(drop=True)


def add_alerta_sv(client_id: str, empresa: str, titulo: str,
                  descricao: str, prioridade: str, whatsapp: str = "") -> bool:
    """Adiciona um alerta manual de supervisão."""
    _ensure_tab_headers("AlertasSV", _HEADERS_ALERTAS_SV)
    alerta_id = _gerar_id("ALS")
    return append_row("AlertasSV", [
        alerta_id, client_id.strip().lower(), empresa,
        titulo, descricao, prioridade,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        whatsapp.strip(),
    ])


def delete_alerta_sv(alerta_id: str) -> bool:
    return delete_row_by_id("AlertasSV", "Id", alerta_id)


# ── Biblioteca Técnica ────────────────────────────────────────────────────────

_HEADERS_BIBLIOTECA = [
    "Id", "Titulo", "Tipo_Documento", "Cliente_Id", "Planta_Id",
    "Ativo_Id", "Componente_Id", "Fabricante", "Modelo", "Numero_Serie",
    "Arquivo_Url", "Arquivo_Nome", "Resumo", "Palavras_Chave",
    "Visibilidade", "Status", "Observacoes_Internas",
    "Texto_Extraido", "Embedding_Id", "Data_Indexacao",
    "Status_Indexacao", "Erro_Indexacao", "Quantidade_Paginas", "Origem_Arquivo",
    "Created_At", "Updated_At",
]

_HEADERS_CHUNKS = [
    "Id", "Documento_Id", "Cliente_Id", "Ativo_Id", "Componente_Id",
    "Chunk_Index", "Pagina_Inicio", "Pagina_Fim", "Titulo_Secao",
    "Conteudo", "Palavras_Chave", "Created_At", "Updated_At",
]

_VIS_INTERNO = "Apenas equipe Pred.IO"


def get_documentos_tecnicos(
    client_id: str | None = None,
    staff: bool = False,
) -> pd.DataFrame:
    """Retorna documentos da Biblioteca Técnica.

    SEGURANÇA:
      - client_id SEMPRE da sessão, nunca do front-end.
      - Para clientes (staff=False): exclui documentos internos e de outros clientes.
      - Para staff (staff=True): retorna todos os documentos.
      - Nunca inclui Observacoes_Internas na resposta ao cliente (chamador deve omitir).
    """
    df = load_sheet("BibliotecaTecnica")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_BIBLIOTECA:
        if col not in df.columns:
            df[col] = ""

    if staff:
        return df.reset_index(drop=True)

    # Filtros de segurança para clientes
    df = df[df["Status"].str.strip() == "Ativo"]
    df = df[df["Visibilidade"].str.strip() != _VIS_INTERNO]

    if client_id:
        cid = client_id.strip().lower()
        mask_publico  = df["Visibilidade"].str.strip() == "Público para clientes autorizados"
        mask_cliente  = df["Cliente_Id"].str.strip().str.lower() == cid
        df = df[mask_publico | mask_cliente]

    # Nunca expõe observações internas para clientes
    if "Observacoes_Internas" in df.columns:
        df = df.drop(columns=["Observacoes_Internas"])

    return df.reset_index(drop=True)


def add_documento_tecnico(dados: dict) -> str | None:
    """Cadastra novo documento técnico. Retorna o Id criado ou None em caso de erro."""
    _ensure_tab_headers("BibliotecaTecnica", _HEADERS_BIBLIOTECA)
    doc_id = _gerar_id("DOC")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("BibliotecaTecnica", [
        doc_id,
        dados.get("titulo",               ""),
        dados.get("tipo_documento",        ""),
        dados.get("cliente_id",            ""),
        dados.get("planta_id",             ""),
        dados.get("ativo_id",              ""),
        dados.get("componente_id",         ""),
        dados.get("fabricante",            ""),
        dados.get("modelo",                ""),
        dados.get("numero_serie",          ""),
        dados.get("arquivo_url",           ""),
        dados.get("arquivo_nome",          ""),
        dados.get("resumo",                ""),
        dados.get("palavras_chave",        ""),
        dados.get("visibilidade",          "Vinculado a cliente específico"),
        dados.get("status",                "Ativo"),
        dados.get("observacoes_internas",  ""),
        "",  # Texto_Extraido
        "",  # Embedding_Id
        "",  # Data_Indexacao
        "Não indexado",  # Status_Indexacao
        "",  # Erro_Indexacao
        "",  # Quantidade_Paginas
        dados.get("origem_arquivo", ""),  # Origem_Arquivo
        now, now,
    ])
    return doc_id if ok else None


def delete_documento_tecnico(doc_id: str) -> bool:
    return delete_row_by_id("BibliotecaTecnica", "Id", doc_id)


def update_status_indexacao(
    doc_id: str,
    status: str,
    texto_extraido: str = "",
    quantidade_paginas: int = 0,
    erro: str = "",
) -> bool:
    """Atualiza campos de indexação de um documento na BibliotecaTecnica."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("BibliotecaTecnica")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        all_ids = ws.col_values(id_col)
        for row_num, v in enumerate(all_ids, start=1):
            if row_num == 1:
                continue
            if str(v).strip() == doc_id.strip():
                now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                updates = {
                    "Status_Indexacao":  status,
                    "Erro_Indexacao":    erro,
                    "Data_Indexacao":    now,
                    "Updated_At":        now,
                }
                if texto_extraido:
                    updates["Texto_Extraido"] = texto_extraido[:5000]
                if quantidade_paginas:
                    updates["Quantidade_Paginas"] = str(quantidade_paginas)
                for col_name, value in updates.items():
                    if col_name in headers:
                        ws.update_cell(row_num, headers.index(col_name) + 1, value)
                load_sheet.clear()
                return True
        return False
    except Exception:
        return False


# ── DocumentoChunks ───────────────────────────────────────────────────────────

def get_chunks_documento(doc_id: str) -> pd.DataFrame:
    """Retorna todos os chunks de um documento."""
    df = load_sheet("DocumentoChunks")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_CHUNKS:
        if col not in df.columns:
            df[col] = ""
    df = df[df["Documento_Id"].str.strip() == doc_id.strip()]
    return df.reset_index(drop=True)


def add_chunks_lote(chunks: list[dict]) -> bool:
    """Salva uma lista de chunks. Retorna True se bem-sucedido."""
    if not chunks:
        return True
    _ensure_tab_headers("DocumentoChunks", _HEADERS_CHUNKS)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    rows = []
    for c in chunks:
        rows.append([
            _gerar_id("CHK"),
            c.get("documento_id",  ""),
            c.get("cliente_id",    ""),
            c.get("ativo_id",      ""),
            c.get("componente_id", ""),
            str(c.get("chunk_index",   "")),
            str(c.get("pagina_inicio", "")),
            str(c.get("pagina_fim",    "")),
            c.get("titulo_secao",  ""),
            c.get("conteudo",      ""),
            c.get("palavras_chave",""),
            now, now,
        ])
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("DocumentoChunks")
        ws.append_rows(rows, value_input_option="USER_ENTERED")
        load_sheet.clear()
        return True
    except Exception:
        return False


def get_chunks_para_assistente(client_id: str, limit: int = 60) -> list[dict]:
    """Retorna chunks indexados acessíveis ao cliente para busca no assistente JS.

    SEGURANÇA: client_id deve vir da sessão, nunca do front-end.
    Retorna apenas campos mínimos (sem doc_id, client_id completo etc.)
    para reduzir o payload JS injetado na página.
    """
    df = load_sheet("DocumentoChunks")
    if df.empty:
        return []
    for col in _HEADERS_CHUNKS:
        if col not in df.columns:
            df[col] = ""
    cid = (client_id or "").strip().lower()
    mask = (
        df["Cliente_Id"].str.strip().str.lower() == cid
    ) | (
        df["Cliente_Id"].str.strip() == ""
    )
    df = df[mask].head(limit)
    result = []
    for _, row in df.iterrows():
        conteudo = str(row.get("Conteudo", "")).strip()
        if not conteudo:
            continue
        result.append({
            "t": str(row.get("Titulo_Secao",  "")).strip()[:80],
            "c": conteudo[:500],
            "k": str(row.get("Palavras_Chave","")).strip()[:200],
        })
    return result


def buscar_chunks(client_id: str, query: str, top_n: int = 5) -> list[dict]:
    """Busca textual simples nos chunks indexados de um cliente.

    Retorna até top_n chunks com maior sobreposição de termos com a query.
    Usado pela área de supervisão no botão 'Testar no Assistente'.
    """
    import unicodedata
    import re as _re

    def _norm(s: str) -> str:
        n = unicodedata.normalize("NFD", s.lower())
        return _re.sub(r"[̀-ͯ]", "", n)

    chunks = get_chunks_para_assistente(client_id, limit=200)
    if not chunks:
        return []
    terms = [t for t in _norm(query).split() if len(t) > 2]
    if not terms:
        return chunks[:top_n]
    scored = []
    for ch in chunks:
        haystack = _norm(ch.get("t", "") + " " + ch.get("c", "") + " " + ch.get("k", ""))
        score = sum(1 for t in terms if t in haystack)
        if score > 0:
            scored.append((score, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [ch for _, ch in scored[:top_n]]


# ── AssistantLogs ─────────────────────────────────────────────────────────────

_HEADERS_LOGS = [
    "Id", "Usuario_Id", "Cliente_Id", "Ativo_Id", "Documento_Id",
    "Pergunta", "Resposta", "Fonte", "Chunks_Usados", "Confidence",
    "Origem_Resposta", "Avaliacao_Interna", "Observacao_Interna", "Created_At",
]


def save_assistant_log(
    usuario_id: str,
    cliente_id: str,
    ativo_id: str,
    documento_id: str,
    pergunta: str,
    resposta: str,
    fonte: str,
    chunks_usados: str,
    confidence: str,
    origem_resposta: str,
) -> str:
    """Salva log de interação do assistente na aba AssistantLogs."""
    log_id = _gerar_id("LOG")
    agora  = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("AssistantLogs")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(
                title="AssistantLogs", rows=2000, cols=len(_HEADERS_LOGS)
            )
            ws.append_row(_HEADERS_LOGS, value_input_option="USER_ENTERED")
        ws.append_row(
            [log_id, usuario_id, cliente_id, ativo_id, documento_id,
             pergunta, resposta, fonte, chunks_usados, confidence,
             origem_resposta, "Não avaliada", "", agora],
            value_input_option="USER_ENTERED",
        )
        load_sheet.clear()
    except Exception as _e:
        import logging
        logging.error("save_assistant_log: %s", _e)
    return log_id


def get_assistant_logs(limit: int = 100) -> pd.DataFrame:
    """Retorna logs do assistente (apenas para staff)."""
    df = load_sheet("AssistantLogs")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_LOGS:
        t = col.title()
        if t not in df.columns:
            df[t] = ""
    return df.iloc[-limit:].iloc[::-1].reset_index(drop=True)


def update_log_avaliacao(log_id: str, avaliacao: str, observacao: str = "") -> bool:
    """Atualiza avaliação interna de um log do assistente."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("AssistantLogs")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col_idx = headers.index("Id") + 1
        cell = ws.find(log_id, in_column=id_col_idx)
        if not cell:
            return False
        row_idx = cell.row
        if "Avaliacao_Interna" in headers:
            ws.update_cell(row_idx, headers.index("Avaliacao_Interna") + 1, avaliacao)
        if observacao and "Observacao_Interna" in headers:
            ws.update_cell(row_idx, headers.index("Observacao_Interna") + 1, observacao)
        load_sheet.clear()
        return True
    except Exception:
        return False


# ── AssistantFaq ──────────────────────────────────────────────────────────────

_HEADERS_FAQ = [
    "Id", "Pergunta", "Resposta", "Fonte", "Categoria", "Palavras_Chave",
    "Ativo_Id", "Documento_Id", "Status", "Created_At", "Updated_At",
]


def save_assistant_faq(
    pergunta: str,
    resposta: str,
    categoria: str,
    palavras_chave: str,
    ativo_id: str = "",
    documento_id: str = "",
) -> str:
    """Salva nova pergunta frequente na aba AssistantFaq."""
    faq_id = _gerar_id("FAQ")
    agora  = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("AssistantFaq")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(
                title="AssistantFaq", rows=1000, cols=len(_HEADERS_FAQ)
            )
            ws.append_row(_HEADERS_FAQ, value_input_option="USER_ENTERED")
        ws.append_row(
            [faq_id, pergunta, resposta, "Pred.IO", categoria, palavras_chave,
             ativo_id, documento_id, "Ativa", agora, agora],
            value_input_option="USER_ENTERED",
        )
        load_sheet.clear()
    except Exception as _e:
        import logging
        logging.error("save_assistant_faq: %s", _e)
    return faq_id


def get_assistant_faq(status: str = "") -> pd.DataFrame:
    """Retorna perguntas frequentes do assistente."""
    df = load_sheet("AssistantFaq")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_FAQ:
        t = col.title()
        if t not in df.columns:
            df[t] = ""
    if status:
        df = df[df["Status"].str.strip() == status]
    return df.reset_index(drop=True)


def delete_chunks_documento(doc_id: str) -> bool:
    """Remove todos os chunks de um documento (antes de reprocessar)."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("DocumentoChunks")
        headers = ws.row_values(1)
        if "Documento_Id" not in headers:
            return True
        col_idx = headers.index("Documento_Id") + 1
        all_vals = ws.col_values(col_idx)
        to_delete = [
            i + 1 for i, v in enumerate(all_vals)
            if i > 0 and str(v).strip() == doc_id.strip()
        ]
        for row_num in reversed(to_delete):
            ws.delete_rows(row_num)
        load_sheet.clear()
        return True
    except Exception:
        return False


# ── Horímetros ───────────────────────────────────────────────────────────────

def get_horimetro(ativo_id: str) -> int | None:
    """Retorna o horímetro persistido de um ativo. None se não houver registro."""
    df = load_sheet("Horimetros")
    if df.empty or "Ativo_Id" not in df.columns:
        return None
    match = df[df["Ativo_Id"].astype(str).str.strip() == str(ativo_id).strip()]
    if match.empty:
        return None
    try:
        return int(float(str(match.iloc[-1]["Horimetro"])))
    except Exception:
        return None


def save_horimetro(ativo_id: str, horimetro: int) -> bool:
    """Salva ou atualiza o horímetro de um ativo na aba Horimetros."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("Horimetros")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title="Horimetros", rows=1000, cols=5)
            ws.append_row(
                ["Ativo_Id", "Horimetro", "Atualizado_Em"],
                value_input_option="USER_ENTERED",
            )
        headers = ws.row_values(1)
        if not headers or "Ativo_Id" not in headers:
            ws.insert_row(
                ["Ativo_Id", "Horimetro", "Atualizado_Em"],
                index=1,
                value_input_option="USER_ENTERED",
            )
            headers = ws.row_values(1)

        id_col = headers.index("Ativo_Id") + 1
        h_col  = headers.index("Horimetro") + 1
        dt_col = headers.index("Atualizado_Em") + 1

        all_ids = ws.col_values(id_col)
        for row_num, v in enumerate(all_ids, start=1):
            if row_num == 1:
                continue
            if str(v).strip() == str(ativo_id).strip():
                ws.update_cell(row_num, h_col,  str(horimetro))
                ws.update_cell(row_num, dt_col, agora)
                load_sheet.clear()
                return True

        ws.append_row([ativo_id, horimetro, agora], value_input_option="USER_ENTERED")
        load_sheet.clear()
        return True
    except Exception:
        return False


# ── Chamados (cliente) ────────────────────────────────────────────────────────

def abrir_chamado(client_id: str, email: str, titulo: str, descricao: str,
                  planta: str, equipamento: str, prioridade: str,
                  empresa: str = "") -> bool:
    """Abre um novo chamado. Gera ID único."""
    chamado_id = _gerar_id("CH")
    empresa    = empresa or client_id
    return append_row("Chamados", [
        chamado_id, empresa, client_id, email, titulo, descricao,
        planta, equipamento, prioridade, "Aberto", "",
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "", "",
    ])


def get_chamados(client_id: str) -> pd.DataFrame:
    """Chamados do cliente — filtra por Client_Id da sessão."""
    df = load_sheet("Chamados")
    if df.empty:
        return df
    # Nova schema: coluna Client_Id
    if "Client_Id" in df.columns:
        return df[
            df["Client_Id"].str.strip().str.lower() == client_id.lower()
        ].reset_index(drop=True)
    # Schema antiga: coluna Empresa continha o client_id
    for col in ("Empresa", "Cliente"):
        if col in df.columns:
            return df[
                df[col].str.strip().str.lower() == client_id.lower()
            ].reset_index(drop=True)
    return pd.DataFrame()


# ── Chamados (supervisão) ─────────────────────────────────────────────────────

def get_all_chamados(filtros: dict | None = None) -> pd.DataFrame:
    """Retorna todos os chamados sem filtro de cliente (apenas para staff)."""
    df = load_sheet("Chamados")
    if df.empty:
        df = _mock_chamados()

    for col in ("Id", "Empresa", "Client_Id", "Email", "Titulo", "Descricao",
                "Planta", "Equipamento", "Prioridade", "Status", "Responsavel",
                "Data_Abertura", "Data_Atualizacao", "Data_Encerramento"):
        if col not in df.columns:
            df[col] = ""

    if filtros:
        if filtros.get("cliente"):
            df = df[df["Empresa"].str.strip().str.lower().str.contains(
                filtros["cliente"].lower(), na=False)]
        if filtros.get("planta"):
            df = df[df["Planta"].str.strip().str.lower().str.contains(
                filtros["planta"].lower(), na=False)]
        if filtros.get("equipamento"):
            df = df[df["Equipamento"].str.lower().str.contains(
                filtros["equipamento"].lower(), na=False)]
        if filtros.get("status"):
            df = df[df["Status"].str.strip().str.lower() == filtros["status"].lower()]
        if filtros.get("prioridade"):
            df = df[df["Prioridade"].str.strip().str.lower() == filtros["prioridade"].lower()]
        if filtros.get("responsavel"):
            r = filtros["responsavel"].lower()
            mask = (
                df["Responsavel"].str.strip().str.lower().str.contains(r, na=False) |
                (df["Responsavel"].str.strip() == "") & (r in ("sem responsável", "nenhum"))
            )
            df = df[mask]
        if filtros.get("texto"):
            t = filtros["texto"].lower()
            mask = (
                df["Titulo"].str.lower().str.contains(t, na=False) |
                df["Descricao"].str.lower().str.contains(t, na=False) |
                df["Equipamento"].str.lower().str.contains(t, na=False) |
                df["Empresa"].str.lower().str.contains(t, na=False)
            )
            df = df[mask]
        if filtros.get("data_ini"):
            df["_dt"] = pd.to_datetime(df["Data_Abertura"], dayfirst=True, errors="coerce")
            df = df[df["_dt"] >= pd.to_datetime(filtros["data_ini"])]
            df = df.drop(columns=["_dt"])
        if filtros.get("data_fim"):
            df["_dt"] = pd.to_datetime(df["Data_Abertura"], dayfirst=True, errors="coerce")
            df = df[df["_dt"] <= pd.to_datetime(filtros["data_fim"])]
            df = df.drop(columns=["_dt"])

    # Ordenar: mais recentes primeiro
    df["_dt"] = pd.to_datetime(df["Data_Abertura"], dayfirst=True, errors="coerce")
    df = df.sort_values("_dt", ascending=False).drop(columns=["_dt"])
    return df.reset_index(drop=True)


def get_chamado_by_id(chamado_id: str) -> dict | None:
    """Retorna um chamado específico pelo Id."""
    df = load_sheet("Chamados")
    if df.empty:
        df = _mock_chamados()
    if "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == str(chamado_id).strip()]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def update_chamado(chamado_id: str, campos: dict) -> bool:
    """Atualiza campos de um chamado existente."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Chamados")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(chamado_id, in_column=id_col)
        if not cell:
            return False
        row_idx = cell.row
        campos  = dict(campos)
        campos["Data_Atualizacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        for campo, valor in campos.items():
            if campo in headers:
                col_idx = headers.index(campo) + 1
                ws.update_cell(row_idx, col_idx, str(valor))
        load_sheet.clear()
        return True
    except Exception:
        return False


# ── Mensagens de chamado ──────────────────────────────────────────────────────

def get_mensagens_chamado(chamado_id: str) -> pd.DataFrame:
    """Todas as mensagens de um chamado (incluindo internas — só para staff)."""
    df = load_sheet("ChamadoMensagens")
    if df.empty:
        return _mock_mensagens(chamado_id)
    if "Id_Chamado" not in df.columns:
        return pd.DataFrame()
    df = df[df["Id_Chamado"].astype(str).str.strip() == str(chamado_id).strip()].copy()
    if df.empty:
        return df
    df["_dt"] = pd.to_datetime(df.get("Data", pd.Series(dtype=str)),
                               dayfirst=True, errors="coerce")
    return df.sort_values("_dt", ascending=True).drop(columns=["_dt"]).reset_index(drop=True)


def get_mensagens_visiveis_cliente(chamado_id: str,
                                   client_id: str = "") -> pd.DataFrame:
    """
    Mensagens visíveis ao cliente (Visivel_Cliente = 1).

    SEGURANÇA:
    - Se client_id fornecido, valida ownership do chamado antes de retornar.
    - Nunca retorna mensagens com Visivel_Cliente != "1".
    - Nunca retorna observações internas (Tipo_Mensagem == observacao_interna).
    """
    # Validação de ownership: chamado deve pertencer ao cliente
    if client_id:
        row = get_chamado_v2_by_id(chamado_id, client_id=client_id)
        if row is None:
            return pd.DataFrame()  # chamado não pertence ao cliente — retorna vazio

    df = get_mensagens_chamado(chamado_id)
    if df.empty:
        return df

    # Filtro 1: apenas mensagens com Visivel_Cliente = 1
    if "Visivel_Cliente" in df.columns:
        df = df[df["Visivel_Cliente"].astype(str).str.strip() == "1"]

    # Filtro 2: nunca exibir observações internas mesmo que Visivel_Cliente = 1 (defesa)
    if "Tipo_Mensagem" in df.columns:
        df = df[df["Tipo_Mensagem"].str.strip().str.lower() != "observacao_interna"]

    return df.reset_index(drop=True)


def add_mensagem(chamado_id: str, autor: str, autor_tipo: str,
                 mensagem: str, visivel_cliente: bool,
                 tipo_mensagem: str) -> bool:
    """Adiciona uma mensagem ao chamado."""
    msg_id = _gerar_id("MSG")
    return append_row("ChamadoMensagens", [
        msg_id, chamado_id, autor, autor_tipo, mensagem,
        "1" if visivel_cliente else "0", tipo_mensagem,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    ])


# ── Clientes (supervisão) ─────────────────────────────────────────────────────

def get_all_clientes() -> pd.DataFrame:
    """Lista de clientes distintos — para área de supervisão."""
    df = load_sheet("Clientes")
    if df.empty:
        df = load_sheet("Usuarios")

    if not df.empty:
        if "Perfil" in df.columns:
            df = df[df["Perfil"].str.strip().str.lower() == "cliente"]
        cols_needed = [c for c in ("Empresa", "Client_Id", "Email", "Nome", "Telefone", "Perfil") if c in df.columns]
        df = df[cols_needed].drop_duplicates().reset_index(drop=True)
        if "Client_Id" not in df.columns and "Empresa" in df.columns:
            df["Client_Id"] = df["Empresa"].str.strip().str.lower()
        return df

    # Fallback: derivar de chamados
    df_cham = load_sheet("Chamados")
    if df_cham.empty:
        df_cham = _mock_chamados()
    if "Empresa" in df_cham.columns:
        clientes = (
            df_cham[["Empresa", "Client_Id", "Email"]]
            .drop_duplicates(subset=["Client_Id"])
            .reset_index(drop=True)
        )
        return clientes
    return pd.DataFrame()


@st.cache_data(ttl=30)
def get_usuarios_staff() -> list:
    """Retorna lista de dicts com nome, email, perfil e empresa dos usuários não-cliente."""
    df = load_sheet("Usuarios")
    if df.empty or "Perfil" not in df.columns:
        return []
    mask = df["Perfil"].str.strip().str.lower().isin(["funcionario", "admin"])
    df_staff = df[mask].copy()
    resultado = []
    for _, row in df_staff.iterrows():
        resultado.append({
            "nome":    str(row.get("Nome",    "")).strip(),
            "email":   str(row.get("Email",   "")).strip(),
            "perfil":  str(row.get("Perfil",  "")).strip().lower(),
            "empresa": str(row.get("Empresa", "")).strip(),
        })
    return resultado


@st.cache_data(ttl=30)
def get_contagem_usuarios_global() -> dict:
    """Retorna {"cliente": N, "funcionario": M, "admin": K} com totais globais do sistema."""
    df = load_sheet("Usuarios")
    if df.empty or "Perfil" not in df.columns:
        return {"cliente": 0, "funcionario": 0, "admin": 0}
    contagem: dict = {"cliente": 0, "funcionario": 0, "admin": 0}
    for perfil in df["Perfil"].str.strip().str.lower():
        if perfil in contagem:
            contagem[perfil] += 1
    return contagem


def cadastrar_usuario(empresa: str, email: str, telefone: str,
                      perfil: str, nome: str, senha_hash: str = "") -> bool:
    """Adiciona um novo usuário na aba Usuarios."""
    return append_row("Usuarios", [empresa, email, senha_hash, telefone, perfil, nome])


def get_historico_cliente(client_id: str) -> dict:
    """Histórico completo de um cliente: chamados + relatórios."""
    chamados   = get_chamados(client_id)
    relatorios = get_relatorios(client_id)
    if chamados.empty:
        # tenta no mock
        mock = _mock_chamados()
        chamados = mock[mock["Client_Id"].str.lower() == client_id.lower()].copy()
    return {
        "chamados":   chamados,
        "relatorios": relatorios,
    }


# ── Assistente / logs ─────────────────────────────────────────────────────────

_HEADERS_LOGS = [
    "Client_Id", "Email", "Pergunta", "Resposta", "Fontes",
    "Confidence", "Sources_Json", "Data_Hora",
]


def get_historico_assistente(client_id: str, limit: int = 20) -> pd.DataFrame:
    df = load_sheet("AssistenteLogs")
    if df.empty:
        return df
    # Garante colunas mínimas
    for col in ("Confidence", "Sources_Json"):
        if col not in df.columns:
            df[col] = ""
    for col_candidate in ("Client_Id", "Empresa"):
        if col_candidate in df.columns:
            df = df[df[col_candidate].str.strip().str.lower() == client_id.lower()]
            return df.tail(limit).iloc[::-1].reset_index(drop=True)
    return pd.DataFrame()


def salvar_log_assistente(
    client_id: str,
    email: str,
    pergunta: str,
    resposta: str,
    fontes: str = "",
    confidence: str = "",
    sources_json: str = "",
) -> None:
    append_row("AssistenteLogs", [
        client_id, email, pergunta, resposta, fontes,
        confidence, sources_json,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    ])


# ── Ativos (supervisão) ──────────────────────────────────────────────────────

def get_all_ativos_sv(filtros: dict | None = None) -> pd.DataFrame:
    """Todos os ativos — sem filtro de cliente. Somente staff deve chamar."""
    df = load_sheet("Ativos")
    if df.empty:
        return df
    for col in ("Id", "Empresa", "Client_Id", "Planta", "Tag", "Tipo", "Modelo",
                "Ns", "Mb", "Inversor", "Analise_Oleo", "Status", "Score",
                "Criticidade", "Detalhes", "Observacoes_Internas", "Data", "Criado_Em"):
        if col not in df.columns:
            df[col] = ""
    if filtros:
        if filtros.get("cliente"):
            df = df[df["Empresa"].str.strip().str.lower().str.contains(
                filtros["cliente"].lower(), na=False)]
        if filtros.get("planta"):
            df = df[df["Planta"].str.strip().str.lower().str.contains(
                filtros["planta"].lower(), na=False)]
        if filtros.get("status"):
            df = df[df["Status"].str.strip().str.lower() == filtros["status"].lower()]
        if filtros.get("criticidade"):
            df = df[df["Criticidade"].str.strip().str.lower() == filtros["criticidade"].lower()]
    return df.reset_index(drop=True)


_HEADERS_ATIVOS = [
    "Id", "Empresa", "Client_Id", "Planta", "Tag", "Tipo", "Modelo",
    "Ns", "Mb", "Inversor", "Analise_Oleo", "Status", "Score",
    "Criticidade", "Detalhes", "Observacoes_Internas", "Data", "Criado_Em",
    "Modelo_Bomba_Oleo", "Num_Coalescer", "Modelo_Painel", "Horimetro",
]

_HEADERS_COMPONENTES = [
    "Id", "Ativo_Id", "Nome", "Tipo", "Modelo", "Ns", "Mb",
    "Inversor", "Status", "Score", "Criticidade", "Detalhes", "Data", "Criado_Em",
]


def _ensure_tab_headers(tab_name: str, headers: list) -> None:
    """Garante que a aba existe e tem cabeçalhos. Cria se necessário."""
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title=tab_name, rows=1000, cols=len(headers) + 2)
            ws.append_row(headers, value_input_option="USER_ENTERED")
            load_sheet.clear()
            return
        # Tab existe — verificar se tem cabeçalhos
        first_row = ws.row_values(1)
        if not first_row or first_row[0].strip() == "":
            ws.insert_row(headers, index=1, value_input_option="USER_ENTERED")
            load_sheet.clear()
    except Exception:
        pass


def cadastrar_ativo_sv(dados: dict) -> str | None:
    """Cadastra ativo principal. Retorna o ID gerado ou None em falha."""
    _ensure_tab_headers("Ativos", _HEADERS_ATIVOS)
    ativo_id = _gerar_id("AT")
    ok = append_row("Ativos", [
        ativo_id,
        dados.get("empresa", ""),
        dados.get("client_id", ""),
        dados.get("planta", ""),
        dados.get("nome", ""),
        dados.get("tipo", ""),
        dados.get("modelo", ""),
        dados.get("numero_serie", ""),
        dados.get("mb", ""),
        dados.get("inversor_frequencia", ""),
        dados.get("analise_oleo_aplicavel", "Não"),
        dados.get("status", ""),
        dados.get("score_saude", ""),
        dados.get("criticidade", ""),
        dados.get("recomendacao", ""),
        dados.get("observacoes_internas", ""),
        dados.get("ultima_atualizacao", datetime.now().strftime("%d/%m/%Y")),
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        dados.get("modelo_bomba_oleo", ""),
        dados.get("num_coalescer", ""),
        dados.get("modelo_painel", ""),
        str(dados.get("horimetro_atual", "")),
    ])
    return ativo_id if ok else None


def get_componentes_sv(ativo_id: str) -> pd.DataFrame:
    """Componentes vinculados a um ativo. Somente staff deve chamar."""
    df = load_sheet("ComponentesAtivos")
    if df.empty:
        return df
    if "Ativo_Id" not in df.columns:
        return pd.DataFrame()
    return df[
        df["Ativo_Id"].astype(str).str.strip() == str(ativo_id).strip()
    ].reset_index(drop=True)


def cadastrar_componente_sv(dados: dict) -> bool:
    """Cadastra componente vinculado a um ativo principal."""
    _ensure_tab_headers("ComponentesAtivos", _HEADERS_COMPONENTES)
    comp_id = _gerar_id("COMP")
    return append_row("ComponentesAtivos", [
        comp_id,
        dados.get("ativo_id", ""),
        dados.get("nome", ""),
        dados.get("tipo", ""),
        dados.get("modelo", ""),
        dados.get("numero_serie", ""),
        dados.get("mb", ""),
        dados.get("inversor_frequencia", ""),
        dados.get("status", ""),
        dados.get("score_saude", ""),
        dados.get("criticidade", ""),
        dados.get("recomendacao", ""),
        dados.get("ultima_atualizacao", datetime.now().strftime("%d/%m/%Y")),
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    ])


# ── Chamados de suporte ───────────────────────────────────────────────────────

def get_chamados_sv(client_id: str) -> pd.DataFrame:
    """Alias para compatibilidade."""
    return get_chamados(client_id)


def abrir_chamado_sv(client_id: str, email: str, titulo: str, descricao: str,
                     planta: str, equipamento: str, prioridade: str) -> bool:
    """Alias legado."""
    return abrir_chamado(client_id, email, titulo, descricao, planta, equipamento, prioridade)


# ── Sessões persistentes ──────────────────────────────────────────────────────

_HEADERS_SESSIONS = [
    "Token", "Empresa", "Email", "Telefone", "Client_Id",
    "Criado_Em", "Expira_Em", "Ativo", "Perfil", "Nome",
]


def _ensure_sessions_tab() -> None:
    """Garante que a aba Sessions existe com cabeçalhos corretos na linha 1."""
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("Sessions")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title="Sessions", rows=10000, cols=12)
            ws.append_row(_HEADERS_SESSIONS, value_input_option="USER_ENTERED")
            load_sheet.clear()
            return
        first = ws.row_values(1)
        if not first or first[0].strip() != "Token":
            ws.insert_row(_HEADERS_SESSIONS, index=1, value_input_option="USER_ENTERED")
            load_sheet.clear()
    except Exception:
        pass


def save_session(token: str, empresa: str, email: str,
                 telefone: str, client_id: str,
                 perfil: str = "cliente", nome: str = "") -> None:
    _ensure_sessions_tab()
    expiry = (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y %H:%M:%S")
    append_row("Sessions", [
        token, empresa, email, telefone, client_id,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"), expiry, "1",
        perfil, nome or empresa,
    ])


def get_session(token: str) -> dict | None:
    df = load_sheet("Sessions")
    if df.empty or "Token" not in df.columns:
        return None
    match = df[df["Token"].astype(str).str.strip() == token.strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    if str(row.get("Ativo", "1")).strip() != "1":
        return None
    try:
        expiry = datetime.strptime(
            str(row.get("Expira_Em", "")).strip(), "%d/%m/%Y %H:%M:%S")
        if datetime.now() > expiry:
            return None
    except Exception:
        pass
    return {
        "empresa":   str(row.get("Empresa",   "")).strip(),
        "email":     str(row.get("Email",     "")).strip(),
        "telefone":  str(row.get("Telefone",  "")).strip(),
        "client_id": str(row.get("Client_Id", "")).strip(),
        "perfil":    str(row.get("Perfil",    "cliente")).strip().lower() or "cliente",
        "nome":      str(row.get("Nome",      "")).strip(),
    }


# ── Notificações do Portal (internas) ────────────────────────────────────────

_HEADERS_PORTAL_NOTIF = [
    "Id", "Cliente_Id", "Usuario_Id",
    "Ativo_Id", "Report_Id", "Ticket_Id",
    "MaintenanceTask_Id", "Alert_Id", "Document_Id",
    "Tipo_Evento", "Titulo", "Mensagem", "Prioridade",
    "Canal", "Status", "Link_Page", "Link_Id",
    "Lida_Em", "Created_At", "Updated_At",
]

_HEADERS_EVENT_PREFS = [
    "Id", "Cliente_Id", "Evento",
    "Canal_Portal", "Canal_Email", "Canal_Whatsapp",
    "Prioridade_Minima", "Frequencia", "Ativo",
    "Created_At", "Updated_At",
]


def add_portal_notification(dados: dict) -> str | None:
    """
    Cria notificação interna do portal.
    SEGURANÇA: client_id SEMPRE da sessão, nunca do front-end.
    Canal E-mail e WhatsApp são registrados mas NÃO enviados nesta etapa.
    """
    if not dados.get("cliente_id"):
        return None
    _ensure_tab_headers("NotificacoesPortal", _HEADERS_PORTAL_NOTIF)
    notif_id = _gerar_id("NP")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("NotificacoesPortal", [
        notif_id,
        dados.get("cliente_id",         ""),
        dados.get("usuario_id",         ""),
        dados.get("ativo_id",           ""),
        dados.get("report_id",          ""),
        dados.get("ticket_id",          ""),
        dados.get("maintenance_task_id",""),
        dados.get("alert_id",           ""),
        dados.get("document_id",        ""),
        dados.get("tipo_evento",        ""),
        dados.get("titulo",             ""),
        dados.get("mensagem",           ""),
        dados.get("prioridade",         "Média"),
        dados.get("canal",              "Portal"),
        "Não lida",
        dados.get("link_page",          ""),
        dados.get("link_id",            ""),
        "",    # Lida_Em
        now,
        now,
    ])
    return notif_id if ok else None


def get_portal_notifications(
    client_id: str,
    apenas_nao_lidas: bool = False,
    limit: int = 50,
) -> pd.DataFrame:
    """
    Retorna notificações do portal para o cliente.
    SEGURANÇA: client_id sempre da sessão — filtra por Cliente_Id.
    """
    if not client_id:
        return pd.DataFrame()
    df = load_sheet("NotificacoesPortal")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_PORTAL_NOTIF:
        if col not in df.columns:
            df[col] = ""
    df = df[
        df["Cliente_Id"].astype(str).str.strip().str.lower()
        == client_id.strip().lower()
    ].copy()
    if apenas_nao_lidas:
        df = df[df["Status"].str.strip() == "Não lida"]
    dt_col = "Created_At"
    if dt_col in df.columns:
        df["_dt"] = pd.to_datetime(df[dt_col].astype(str), dayfirst=True, errors="coerce")
        df = df.sort_values("_dt", ascending=False).drop(columns=["_dt"])
    return df.head(limit).reset_index(drop=True)


def count_portal_notifications_unread(client_id: str) -> int:
    """Conta notificações não lidas do portal para o cliente."""
    if not client_id:
        return 0
    df = get_portal_notifications(client_id, apenas_nao_lidas=True)
    return len(df)


def mark_portal_notification_read(notif_id: str, client_id: str) -> bool:
    """
    Marca notificação como lida.
    SEGURANÇA: valida que a notificação pertence ao client_id.
    """
    if not notif_id or not client_id:
        return False
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("NotificacoesPortal")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(notif_id, in_column=id_col)
        if not cell:
            return False
        # Valida ownership
        row_vals = ws.row_values(cell.row)
        cid_idx  = headers.index("Cliente_Id") if "Cliente_Id" in headers else -1
        if cid_idx >= 0:
            row_cid = (row_vals[cid_idx] if cid_idx < len(row_vals) else "").strip().lower()
            if row_cid != client_id.strip().lower():
                return False  # não pertence ao cliente
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        def _c(name): return headers.index(name) + 1 if name in headers else 0
        ws.update_cell(cell.row, _c("Status"),  "Lida")
        ws.update_cell(cell.row, _c("Lida_Em"), now)
        ws.update_cell(cell.row, _c("Updated_At"), now)
        load_sheet.clear()
        return True
    except Exception:
        return False


def mark_all_portal_notifications_read(client_id: str) -> int:
    """Marca todas as notificações não lidas do cliente como lidas. Retorna contagem."""
    df = get_portal_notifications(client_id, apenas_nao_lidas=True)
    count = 0
    for _, row in df.iterrows():
        nid = str(row.get("Id", "")).strip()
        if nid and mark_portal_notification_read(nid, client_id):
            count += 1
    return count


# ── Preferências por Evento ───────────────────────────────────────────────────

def get_event_preferences(client_id: str) -> pd.DataFrame:
    """
    Retorna preferências por evento do cliente.
    SEGURANÇA: client_id da sessão — filtra por Cliente_Id.
    """
    if not client_id:
        return pd.DataFrame()
    df = load_sheet("PreferenciasEvento")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_EVENT_PREFS:
        if col not in df.columns:
            df[col] = ""
    return df[
        df["Cliente_Id"].astype(str).str.strip().str.lower()
        == client_id.strip().lower()
    ].reset_index(drop=True)


def upsert_event_preference(client_id: str, evento: str, dados: dict) -> bool:
    """
    Cria ou atualiza preferência de evento.
    SEGURANÇA: client_id sempre da sessão.
    """
    if not client_id or not evento:
        return False
    _ensure_tab_headers("PreferenciasEvento", _HEADERS_EVENT_PREFS)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("PreferenciasEvento")
        headers = ws.row_values(1)
        # Busca linha existente para este client_id + evento
        all_vals = ws.get_all_values()
        row_num  = None
        cid_idx  = headers.index("Cliente_Id") if "Cliente_Id" in headers else -1
        ev_idx   = headers.index("Evento")     if "Evento"     in headers else -1
        if cid_idx >= 0 and ev_idx >= 0:
            for i, row in enumerate(all_vals[1:], start=2):
                cid_v = row[cid_idx].strip().lower() if cid_idx < len(row) else ""
                ev_v  = row[ev_idx].strip()           if ev_idx  < len(row) else ""
                if cid_v == client_id.strip().lower() and ev_v == evento:
                    row_num = i
                    break

        pref_id = dados.get("id", "") or _gerar_id("EP")
        row_vals = [
            pref_id,
            client_id,
            evento,
            str(dados.get("canal_portal",    True)).lower(),
            str(dados.get("canal_email",      False)).lower(),
            str(dados.get("canal_whatsapp",   False)).lower(),
            dados.get("prioridade_minima", "Baixa"),
            dados.get("frequencia",        "Imediata"),
            str(dados.get("ativo",         True)).lower(),
            dados.get("created_at", now),
            now,
        ]
        if row_num:
            end_col = chr(64 + len(_HEADERS_EVENT_PREFS))
            ws.update(f"A{row_num}:{end_col}{row_num}", [row_vals],
                      value_input_option="USER_ENTERED")
        else:
            ws.append_row(row_vals, value_input_option="USER_ENTERED")
        load_sheet.clear()
        return True
    except Exception:
        return False


def init_default_event_preferences(client_id: str) -> bool:
    """
    Inicializa preferências padrão para novo cliente.
    Apenas cria se não existirem preferências ainda.
    """
    if not client_id:
        return False
    existing = get_event_preferences(client_id)
    if not existing.empty:
        return True  # já tem preferências

    from notifications import _DEFAULT_EVENT_PREFS
    ok = True
    for evento, pref in _DEFAULT_EVENT_PREFS.items():
        r = upsert_event_preference(client_id, evento, pref)
        if not r:
            ok = False
    return ok


# ── Notificações Externas ─────────────────────────────────────────────────────

_HEADERS_NOTIFICACOES = [
    "Id", "Cliente_Id", "Cliente_Nome", "Usuario_Id", "Usuario_Nome",
    "Email_Destinatario", "Whatsapp_Destinatario", "Evento_Tipo", "Canal",
    "Titulo", "Mensagem", "Link_Portal", "Status", "Tentativas",
    "Erro", "Enviado_Por", "Enviado_Em", "Created_At", "Updated_At",
]

_HEADERS_PREFS_NOTIF = [
    "Id", "Usuario_Id", "Cliente_Id", "Nome", "Email", "Whatsapp",
    "Receber_Email", "Receber_Whatsapp", "Receber_Relatorios",
    "Receber_Alertas_Criticos", "Receber_Manutencao", "Receber_Chamados",
    "Ativo", "Created_At", "Updated_At",
    # Etapa 6.7 — campos de consentimento
    "Consentimento_Email", "Consentimento_Whatsapp",
    "Consentimento_Data", "Consentimento_Origem",
    "Telefone_Whatsapp",
]

# Mapeamento: tipo de evento → campo de preferência que o habilita
_EVENTO_PREF_MAP: dict = {
    "report_published":             "Receber_Relatorios",
    "technical_document_available": "Receber_Relatorios",
    "critical_alarm":               "Receber_Alertas_Criticos",
    "asset_critical":               "Receber_Alertas_Criticos",
    "maintenance_due":              "Receber_Manutencao",
    "maintenance_overdue":          "Receber_Manutencao",
    "ticket_replied":               "Receber_Chamados",
    "ticket_waiting_customer":      "Receber_Chamados",
}


def get_notificacoes(client_id: str = "") -> pd.DataFrame:
    """Carrega notificações externas. Staff chama sem filtro; cliente passa o próprio client_id."""
    df = load_sheet("NotificacoesExternas")
    if df.empty:
        return pd.DataFrame()
    if client_id:
        df = df[
            df["Cliente_Id"].astype(str).str.strip().str.lower()
            == client_id.strip().lower()
        ]
    return df.reset_index(drop=True)


def add_notificacao(dados: dict) -> str | None:
    """Registra uma notificação externa. Retorna ID ou None."""
    _ensure_tab_headers("NotificacoesExternas", _HEADERS_NOTIFICACOES)
    notif_id = _gerar_id("NOTIF")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("NotificacoesExternas", [
        notif_id,
        dados.get("cliente_id",            ""),
        dados.get("cliente_nome",          ""),
        dados.get("usuario_id",            ""),
        dados.get("usuario_nome",          ""),
        dados.get("email_destinatario",    ""),
        dados.get("whatsapp_destinatario", ""),
        dados.get("evento_tipo",           ""),
        dados.get("canal",                 ""),
        dados.get("titulo",                ""),
        dados.get("mensagem",              ""),
        dados.get("link_portal",           ""),
        dados.get("status",                "Pendente"),
        "0",
        "",
        dados.get("enviado_por",           ""),
        dados.get("enviado_em",            ""),
        now,
        now,
    ])
    return notif_id if ok else None


def update_notificacao_status(
    notif_id: str,
    status: str,
    enviado_em: str = "",
    erro: str = "",
) -> bool:
    """Atualiza o status de uma notificação externa. Retorna True em caso de sucesso."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("NotificacoesExternas")
        headers = ws.row_values(1)
        cell = ws.find(notif_id)
        if not cell:
            return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        row = cell.row

        def _col(name: str) -> int:
            return headers.index(name) + 1 if name in headers else 0

        ws.update_cell(row, _col("Status"),     status)
        ws.update_cell(row, _col("Updated_At"), now)
        if enviado_em:
            ws.update_cell(row, _col("Enviado_Em"), enviado_em)
        if erro:
            ws.update_cell(row, _col("Erro"), erro)
        if status == "Enviado":
            tc = _col("Tentativas")
            if tc:
                try:
                    current_t = int(ws.cell(row, tc).value or 0)
                    ws.update_cell(row, tc, str(current_t + 1))
                    ws.update_cell(row, _col("Enviado_Em"), enviado_em or now)
                except Exception:
                    pass
        load_sheet.clear()
        return True
    except Exception:
        return False


def get_preferencias_notificacao(usuario_id: str = "", client_id: str = "") -> pd.DataFrame:
    """Carrega preferências de notificação. Filtra por usuario_id ou client_id."""
    df = load_sheet("PreferenciasNotificacao")
    if df.empty:
        return pd.DataFrame()
    if usuario_id:
        df = df[df["Usuario_Id"].astype(str).str.strip() == usuario_id.strip()]
    elif client_id:
        df = df[
            df["Cliente_Id"].astype(str).str.strip().str.lower()
            == client_id.strip().lower()
        ]
    return df.reset_index(drop=True)


def get_contatos_notificacao(client_id: str) -> list:
    """Retorna contatos disponíveis para notificação de um cliente.

    Prioriza PreferenciasNotificacao; fallback para dados básicos do cliente.
    SECURITY: client_id deve vir de fonte confiável (sessão/staff), nunca do front-end.
    """
    contacts: list = []

    df = get_preferencias_notificacao(client_id=client_id)
    if not df.empty:
        for _, r in df.iterrows():
            if str(r.get("Ativo", "true")).strip().lower() == "false":
                continue
            email    = str(r.get("Email",    "")).strip()
            whatsapp = str(r.get("Whatsapp", r.get("Telefone_Whatsapp", ""))).strip()
            uid      = str(r.get("Id",       "")).strip() or f"pref_{client_id}_{len(contacts)}"
            consent_email = str(r.get("Consentimento_Email",    "true")).strip().lower()
            consent_wa    = str(r.get("Consentimento_Whatsapp", "true")).strip().lower()
            contacts.append({
                "id":                    uid,
                "usuario_id":            str(r.get("Usuario_Id", "")).strip(),
                "nome":                  str(r.get("Nome",       "")).strip() or str(r.get("Usuario_Id", "")).strip(),
                "email":                 email,
                "whatsapp":              whatsapp,
                "telefone_whatsapp":     whatsapp,
                "tem_email":             bool(email    and str(r.get("Receber_Email",    "false")).strip().lower() == "true"),
                "tem_whatsapp":          bool(whatsapp and str(r.get("Receber_Whatsapp", "false")).strip().lower() == "true"),
                "consentimento_email":   consent_email in ("true", "1", "sim", "yes"),
                "consentimento_whatsapp": consent_wa in ("true", "1", "sim", "yes"),
                "consentimento_data":    str(r.get("Consentimento_Data",   "")).strip(),
                "consentimento_origem":  str(r.get("Consentimento_Origem", "")).strip(),
                "ativo":                 True,
            })

    if contacts:
        return contacts

    # Fallback: dados básicos do cliente na aba Clientes/Usuarios
    try:
        df_cli = get_all_clientes()
        if not df_cli.empty and "Empresa" in df_cli.columns:
            match = df_cli[
                df_cli["Empresa"].str.strip().str.lower() == client_id.strip().lower()
            ]
            if match.empty and "Client_Id" in df_cli.columns:
                match = df_cli[
                    df_cli["Client_Id"].astype(str).str.strip().str.lower() == client_id.strip().lower()
                ]
            if not match.empty:
                r        = match.iloc[0]
                email    = str(r.get("Email",    "")).strip()
                telefone = str(r.get("Telefone", "")).strip()
                nome_emp = str(r.get("Empresa",  client_id)).strip()
                if email or telefone:
                    contacts.append({
                        "id":           f"cli_{client_id}",
                        "usuario_id":    email or client_id,
                        "nome":         f"Contato principal — {nome_emp}",
                        "email":         email,
                        "whatsapp":      telefone,
                        "tem_email":     bool(email),
                        "tem_whatsapp":  bool(telefone),
                    })
    except Exception:
        pass

    return contacts


def upsert_preferencias_notificacao(dados: dict) -> bool:
    """Cria ou atualiza preferências de notificação de um usuário."""
    _ensure_tab_headers("PreferenciasNotificacao", _HEADERS_PREFS_NOTIF)
    usuario_id = dados.get("usuario_id", "")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("PreferenciasNotificacao")
        try:
            cell = ws.find(usuario_id)
        except Exception:
            cell = None

        row_vals = [
            dados.get("id", "") or _gerar_id("PREF"),
            usuario_id,
            dados.get("cliente_id", ""),
            dados.get("nome", ""),
            dados.get("email", ""),
            dados.get("whatsapp", ""),
            str(dados.get("receber_email",            False)).lower(),
            str(dados.get("receber_whatsapp",         False)).lower(),
            str(dados.get("receber_relatorios",       True)).lower(),
            str(dados.get("receber_alertas_criticos", True)).lower(),
            str(dados.get("receber_manutencao",       True)).lower(),
            str(dados.get("receber_chamados",         True)).lower(),
            "true",
            dados.get("created_at", now),
            now,
        ]

        if cell:
            end_col = chr(64 + len(_HEADERS_PREFS_NOTIF))
            ws.update(
                f"A{cell.row}:{end_col}{cell.row}",
                [row_vals],
                value_input_option="USER_ENTERED",
            )
        else:
            ws.append_row(row_vals, value_input_option="USER_ENTERED")

        load_sheet.clear()
        return True
    except Exception:
        return False


def notify_event(
    client_id: str,
    evento_tipo: str,
    titulo: str,
    mensagem: str,
    link_portal: str,
) -> list:
    """Cria registros de notificação externa conforme preferências do cliente.

    Nesta versão cria registros como Pendente.
    Integração futura: POST /api/notifications/dispatch → n8n, e-mail ou API WhatsApp.

    SECURITY:
    - client_id SEMPRE vem da sessão/autenticação, nunca do frontend.
    - mensagem deve ser resumo apenas; nunca incluir conteúdo técnico sensível completo.
    - WhatsApp recebe apenas resumo + link seguro.
    - Observações internas da Pred.IO nunca são incluídas.
    - Links devem apontar para o portal autenticado (não expõem dados diretamente).
    """
    prefs_df = get_preferencias_notificacao(client_id=client_id)
    if prefs_df.empty:
        return []

    pref_key = _EVENTO_PREF_MAP.get(evento_tipo)
    created: list = []

    for _, pref in prefs_df.iterrows():
        if str(pref.get("Ativo", "true")).lower() != "true":
            continue
        if pref_key and str(pref.get(pref_key, "false")).lower() != "true":
            continue

        uid = str(pref.get("Usuario_Id", "")).strip()

        if str(pref.get("Receber_Email", "false")).lower() == "true":
            nid = add_notificacao({
                "cliente_id":  client_id,
                "usuario_id":  uid,
                "evento_tipo": evento_tipo,
                "canal":       "E-mail",
                "titulo":      titulo,
                "mensagem":    mensagem,
                "link_portal": link_portal,
            })
            if nid:
                created.append(nid)

        if str(pref.get("Receber_Whatsapp", "false")).lower() == "true":
            # WhatsApp: apenas resumo + link — nunca conteúdo técnico completo
            resumo_wa = f"{titulo}. Acesse o portal: {link_portal}"
            nid = add_notificacao({
                "cliente_id":  client_id,
                "usuario_id":  uid,
                "evento_tipo": evento_tipo,
                "canal":       "WhatsApp",
                "titulo":      titulo,
                "mensagem":    resumo_wa,
                "link_portal": link_portal,
            })
            if nid:
                created.append(nid)

    return created


# ── Relatórios Técnicos ──────────────────────────────────────────────────────

_HEADERS_TECH_REPORTS = [
    "Id", "Cliente_Id", "Ativo_Id", "Titulo", "Tipo_Servico", "Severidade",
    "Data_Relatorio", "Planta", "Equipamento", "Resumo", "Recomendacoes",
    "Arquivo_Url", "Score_Impacto", "Status", "Obs_Interna",
    "Created_By", "Created_At", "Updated_At",
]

_TIPO_SERVICO_TO_TIMELINE = {
    "análise de vibração": "analise_vibracao",
    "analise de vibracao": "analise_vibracao",
    "análise de óleo":     "analise_oleo",
    "analise de oleo":     "analise_oleo",
    "termografia":         "termografia",
}

_SCORE_DELTA_MAP = {
    "urgente": -25,
    "crítico": -15,
    "critico": -15,
    "atenção": -7,
    "atencao": -7,
    "normal":   2,
}


def _calc_new_score(current: int, severidade: str) -> int:
    delta = _SCORE_DELTA_MAP.get(severidade.strip().lower(), 0)
    return max(5, min(100, current + delta))


def add_technical_report(dados: dict, created_by: str = "") -> str | None:
    """Cria relatório técnico em rascunho. cliente_id DEVE vir da sessão."""
    if not dados.get("cliente_id"):
        return None
    _ensure_tab_headers("TechnicalReports", _HEADERS_TECH_REPORTS)
    rep_id = _gerar_id("REP")
    now    = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("TechnicalReports", [
        rep_id,
        dados.get("cliente_id", ""),
        dados.get("ativo_id", ""),
        dados.get("titulo", ""),
        dados.get("tipo_servico", ""),
        dados.get("severidade", "Normal"),
        dados.get("data_relatorio", datetime.now().strftime("%d/%m/%Y")),
        dados.get("planta", ""),
        dados.get("equipamento", ""),
        dados.get("resumo", ""),
        dados.get("recomendacoes", ""),
        dados.get("arquivo_url", ""),
        "",
        "Rascunho",
        dados.get("obs_interna", ""),
        created_by,
        now,
        now,
    ])
    return rep_id if ok else None


def get_technical_reports(
    client_id: str = "",
    status: str = "",
    ativo_id: str = "",
    staff: bool = True,
) -> pd.DataFrame:
    """Retorna relatórios técnicos.
    staff=False → somente publicados do cliente (requer client_id).
    """
    df = load_sheet("TechnicalReports")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_TECH_REPORTS:
        if col not in df.columns:
            df[col] = ""
    if not staff:
        if not client_id:
            return pd.DataFrame()
        df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
        df = df[df["Status"].str.strip() == "Publicado"]
    else:
        if client_id:
            df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
        if status:
            df = df[df["Status"].str.strip() == status]
        if ativo_id:
            df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]
    df = df.copy()
    df["_dt"] = pd.to_datetime(df["Data_Relatorio"].astype(str), dayfirst=True, errors="coerce")
    df = df.sort_values("_dt", ascending=False).drop(columns=["_dt"])
    return df.reset_index(drop=True)


def get_technical_report_by_id(report_id: str) -> dict | None:
    """Retorna dict com campos do relatório ou None."""
    df = load_sheet("TechnicalReports")
    if df.empty or "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == report_id.strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    return {col: str(row.get(col, "")).strip() for col in _HEADERS_TECH_REPORTS}


def update_technical_report(report_id: str, campos: dict) -> bool:
    """Atualiza campos de um relatório técnico."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("TechnicalReports")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(report_id, in_column=id_col)
        if not cell:
            return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        campos.setdefault("Updated_At", now)
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        load_sheet.clear()
        return True
    except Exception:
        return False


def _get_ativo_score(ativo_id: str) -> int | None:
    """Lê Score atual de um ativo pelo Id."""
    df = load_sheet("Ativos")
    if df.empty or "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == ativo_id.strip()]
    if match.empty:
        return None
    try:
        return int(float(str(match.iloc[0].get("Score", "75"))))
    except Exception:
        return None


def _update_ativo_score(ativo_id: str, new_score: int) -> bool:
    """Atualiza Score do ativo na aba Ativos."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Ativos")
        headers = ws.row_values(1)
        if "Id" not in headers or "Score" not in headers:
            return False
        id_col    = headers.index("Id") + 1
        score_col = headers.index("Score") + 1
        cell = ws.find(ativo_id, in_column=id_col)
        if not cell:
            return False
        ws.update_cell(cell.row, score_col, str(new_score))
        load_sheet.clear()
        return True
    except Exception:
        return False


def publish_technical_report(report_id: str, published_by: str = "") -> dict:
    """Publica relatório: atualiza status, score, timeline, alertas, notificações.

    SEGURANÇA: Obs_Interna nunca é enviada ao cliente.
    Retorna dict com ações executadas.
    """
    rep = get_technical_report_by_id(report_id)
    if not rep:
        return {"ok": False, "erro": "Relatório não encontrado."}
    if rep.get("Status") == "Publicado":
        return {"ok": False, "erro": "Relatório já publicado."}

    severidade   = rep.get("Severidade", "Normal")
    ativo_id     = rep.get("Ativo_Id", "").strip()
    cliente_id   = rep.get("Cliente_Id", "").strip()
    titulo       = rep.get("Titulo", "")
    data_rel     = rep.get("Data_Relatorio", datetime.now().strftime("%d/%m/%Y"))
    tipo_servico = rep.get("Tipo_Servico", "")
    planta       = rep.get("Planta", "")
    equipamento  = rep.get("Equipamento", "")

    actions: dict = {
        "ok": True,
        "score_delta": 0,
        "score_atualizado": False,
        "timeline": False,
        "alerta": False,
        "notificado": False,
    }

    campos_upd: dict = {
        "Status": "Publicado",
    }
    if published_by:
        campos_upd["Created_By"] = published_by

    # Atualiza score do ativo
    if ativo_id:
        current = _get_ativo_score(ativo_id) or 75
        new_sc  = _calc_new_score(current, severidade)
        delta   = new_sc - current
        if _update_ativo_score(ativo_id, new_sc):
            campos_upd["Score_Impacto"] = str(delta)
            actions["score_delta"]       = delta
            actions["score_atualizado"]  = True

    update_technical_report(report_id, campos_upd)

    # Evento na timeline
    ev_tipo_key = tipo_servico.strip().lower()
    ev_tipo = _TIPO_SERVICO_TO_TIMELINE.get(ev_tipo_key, "relatorio_publicado")
    descr   = f"{tipo_servico} — {titulo}."
    if equipamento:
        descr += f" Equipamento: {equipamento}."
    if actions["score_delta"]:
        descr += f" Score impactado em {actions['score_delta']:+d} pontos."
    add_report_timeline_event({
        "ativo_id":        ativo_id or cliente_id,
        "cliente_id":      cliente_id,
        "tipo":            ev_tipo,
        "titulo":          f"Relatório publicado: {titulo}",
        "descricao":       descr,
        "data":            data_rel,
        "origem":          "Relatórios Técnicos",
        "report_id":       report_id,
        "visivel_cliente": "true",
        "obs_interna":     "",
    })
    actions["timeline"] = True

    # Alerta interno se Crítico ou Urgente
    sev_lower = severidade.strip().lower()
    if sev_lower in ("crítico", "critico", "urgente"):
        prio_alerta = "Urgente" if sev_lower == "urgente" else "Alta"
        msg_al = (
            f"Relatório '{titulo}' publicado com severidade {severidade}."
            + (f" Equipamento: {equipamento}." if equipamento else "")
            + f" Cliente: {cliente_id}."
        )
        try:
            df_cli  = get_all_clientes()
            empresa = ""
            if not df_cli.empty:
                cid_col = "Client_Id" if "Client_Id" in df_cli.columns else "Cliente_Id"
                if cid_col in df_cli.columns:
                    m = df_cli[
                        df_cli[cid_col].astype(str).str.strip().str.lower()
                        == cliente_id.lower()
                    ]
                    empresa = str(m.iloc[0].get("Empresa", "")) if not m.empty else ""
        except Exception:
            empresa = ""
        add_alerta_sv(
            client_id  = cliente_id,
            empresa    = empresa or cliente_id,
            titulo     = f"Relatório {severidade}: {titulo}",
            descricao  = msg_al,
            prioridade = prio_alerta,
        )
        actions["alerta"] = True

    # Notificação externa
    try:
        msg_nf = f"Novo relatório técnico disponível: {titulo} ({data_rel})."
        if planta:
            msg_nf += f" Planta: {planta}."
        notifs = notify_event(
            client_id   = cliente_id,
            evento_tipo = "report_published",
            titulo      = f"Novo relatório: {titulo}",
            mensagem    = msg_nf,
            link_portal = "/",
        )
        actions["notificado"] = len(notifs) > 0
    except Exception:
        pass

    return actions


def archive_technical_report(report_id: str) -> bool:
    """Arquiva um relatório técnico publicado."""
    return update_technical_report(report_id, {"Status": "Arquivado"})


def delete_technical_report(report_id: str) -> bool:
    """Remove relatório somente se ainda for Rascunho."""
    rep = get_technical_report_by_id(report_id)
    if not rep or rep.get("Status") != "Rascunho":
        return False
    return delete_row_by_id("TechnicalReports", "Id", report_id)


# ── Timeline de Relatórios ───────────────────────────────────────────────────

_HEADERS_REPORT_TIMELINE = [
    "Id", "Ativo_Id", "Cliente_Id", "Tipo", "Titulo", "Descricao",
    "Data", "Origem", "Report_Id", "Visivel_Cliente", "Obs_Interna", "Created_At",
]


def add_report_timeline_event(dados: dict) -> str | None:
    """Adiciona evento à timeline de relatórios."""
    _ensure_tab_headers("ReportTimeline", _HEADERS_REPORT_TIMELINE)
    ev_id = _gerar_id("TL")
    now   = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("ReportTimeline", [
        ev_id,
        dados.get("ativo_id",        ""),
        dados.get("cliente_id",      ""),
        dados.get("tipo",            "relatorio_publicado"),
        dados.get("titulo",          ""),
        dados.get("descricao",       ""),
        dados.get("data",            datetime.now().strftime("%d/%m/%Y")),
        dados.get("origem",          "Relatórios Técnicos"),
        dados.get("report_id",       ""),
        dados.get("visivel_cliente", "true"),
        dados.get("obs_interna",     ""),
        now,
    ])
    return ev_id if ok else None


def get_report_timeline_events(
    ativo_id: str = "",
    cliente_id: str = "",
    staff: bool = True,
) -> pd.DataFrame:
    """Retorna eventos da timeline de relatórios."""
    df = load_sheet("ReportTimeline")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_REPORT_TIMELINE:
        if col not in df.columns:
            df[col] = ""
    if ativo_id:
        df = df[df["Ativo_Id"].astype(str).str.strip() == ativo_id.strip()]
    if cliente_id:
        df = df[df["Cliente_Id"].astype(str).str.strip().str.lower() == cliente_id.strip().lower()]
    if not staff:
        df = df[df["Visivel_Cliente"].astype(str).str.strip().str.lower() != "false"]
        if "Obs_Interna" in df.columns:
            df = df.drop(columns=["Obs_Interna"])
    df = df.copy()

    def _dtkey(d: str) -> tuple:
        try:
            p = str(d).split("/")
            return (int(p[2]), int(p[1]), int(p[0]))
        except Exception:
            return (0, 0, 0)

    df["_s"] = df["Data"].apply(_dtkey)
    df = df.sort_values("_s", ascending=False).drop(columns=["_s"])
    return df.reset_index(drop=True)


# ── Planos e Tarefas de Manutenção ──────────────────────────────────────────

_HEADERS_MAINT_PLANS = [
    "Id", "Cliente_Id", "Ativo_Id", "Nome", "Descricao", "Status", "Created_At", "Updated_At",
]

_HEADERS_MAINT_TASKS = [
    "Id", "Cliente_Id", "Ativo_Id", "Componente_Id", "Plano_Id", "Nome_Tarefa",
    "Categoria", "Tipo_Manutencao", "Periodicidade_Dias", "Periodicidade_Horas",
    "Ultima_Execucao_Data", "Ultima_Execucao_Horimetro",
    "Proxima_Execucao_Data", "Proxima_Execucao_Horimetro",
    "Status", "Prioridade", "Depende_Relatorio", "Origem",
    "Descricao", "Recomendacao", "Obs_Interna", "Created_At", "Updated_At",
]

_HEADERS_MAINT_EXEC = [
    "Id", "Cliente_Id", "Ativo_Id", "Task_Id", "Executado_Em", "Horimetro_Execucao",
    "Responsavel", "Descricao_Execucao", "Evidencias", "Arquivo_Url", "Obs_Interna", "Created_At",
]


def calc_task_status(task: dict, horimetro_atual: int = 0) -> str:
    """Calcula status dinâmico de uma tarefa de manutenção (sem chamada ao Sheets).

    Funciona com o formato do Sheets (campos Title_Case):
    Tipo_Manutencao, Proxima_Execucao_Data, Proxima_Execucao_Horimetro,
    Periodicidade_Dias, Periodicidade_Horas, Ultima_Execucao_Data, Ultima_Execucao_Horimetro.

    Regras:
    - Condição → "Depende de análise preditiva" (sempre)
    - Calendário: diff dias → Vencida (<0) / Próxima do vencimento (≤15) / Em dia
    - Horímetro: diff horas → Vencida (h≥prox) / Próxima do vencimento (h≥prox-500) / Em dia
    """
    from datetime import datetime as _dt, timedelta as _td

    tipo = str(task.get("Tipo_Manutencao", "")).strip()
    if not tipo:
        # fallback para formato mock (lowercase)
        tipo_mock = str(task.get("tipo", "")).strip()
        if tipo_mock == "condicao":
            return "Depende de análise preditiva"
        if tipo_mock == "calendario":
            tipo = "Calendário"
        elif tipo_mock == "horimetro":
            tipo = "Horímetro"

    if tipo in ("Condição", "Condicao"):
        return "Depende de análise preditiva"

    if tipo in ("Calendário", "Calendario"):
        prox = str(task.get("Proxima_Execucao_Data", "")).strip()
        if not prox or prox in ("", "nan"):
            ultima = str(task.get("Ultima_Execucao_Data", "")).strip()
            period = 0
            try:
                period = int(float(str(task.get("Periodicidade_Dias", 0) or 0)))
            except Exception:
                pass
            if ultima and period:
                try:
                    prox = (_dt.strptime(ultima, "%d/%m/%Y") + _td(days=period)).strftime("%d/%m/%Y")
                except Exception:
                    return "Em dia"
            else:
                return "Em dia"
        try:
            diff = (_dt.strptime(prox, "%d/%m/%Y") - _dt.now()).days
            if diff < 0:
                return "Vencida"
            if diff <= 15:
                return "Próxima do vencimento"
            return "Em dia"
        except Exception:
            return "Em dia"

    if tipo in ("Horímetro", "Horimetro"):
        prox_h = str(task.get("Proxima_Execucao_Horimetro", "")).strip()
        if not prox_h or prox_h in ("", "nan"):
            ultima_h = str(task.get("Ultima_Execucao_Horimetro", "")).strip()
            period_h = 0
            try:
                period_h = int(float(str(task.get("Periodicidade_Horas", 0) or 0)))
            except Exception:
                pass
            if period_h:
                try:
                    base = int(float(ultima_h)) if ultima_h and ultima_h not in ("", "nan") else 0
                    prox_h = str(base + period_h)
                except Exception:
                    return "Em dia"
            else:
                return "Em dia"
        try:
            ph = int(float(prox_h))
            if horimetro_atual >= ph:
                return "Vencida"
            if horimetro_atual >= ph - 500:
                return "Próxima do vencimento"
            return "Em dia"
        except Exception:
            return "Em dia"

    return "Em dia"


def get_maintenance_plans(
    client_id: str = "",
    ativo_id: str = "",
    status: str = "",
    staff: bool = True,
) -> pd.DataFrame:
    """Retorna planos de manutenção. staff=False → somente do próprio cliente."""
    df = load_sheet("MaintenancePlans")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_MAINT_PLANS:
        if col not in df.columns:
            df[col] = ""
    if not staff:
        if not client_id:
            return pd.DataFrame()
        df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
    else:
        if client_id:
            df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
    if ativo_id:
        df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]
    if status:
        df = df[df["Status"].str.strip() == status]
    return df.reset_index(drop=True)


def add_maintenance_plan(dados: dict, created_by: str = "") -> str | None:
    """Cria plano de manutenção. cliente_id DEVE vir da sessão do supervisor."""
    if not dados.get("cliente_id"):
        return None
    _ensure_tab_headers("MaintenancePlans", _HEADERS_MAINT_PLANS)
    plan_id = _gerar_id("PLAN")
    now     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("MaintenancePlans", [
        plan_id,
        dados.get("cliente_id", ""),
        dados.get("ativo_id", ""),
        dados.get("nome", ""),
        dados.get("descricao", ""),
        dados.get("status", "Ativo"),
        now,
        now,
    ])
    return plan_id if ok else None


def update_maintenance_plan(plan_id: str, campos: dict) -> bool:
    """Atualiza campos de um plano de manutenção."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("MaintenancePlans")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        cell = ws.find(plan_id, in_column=headers.index("Id") + 1)
        if not cell:
            return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        campos.setdefault("Updated_At", now)
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        load_sheet.clear()
        return True
    except Exception:
        return False


def get_maintenance_tasks(
    client_id: str = "",
    plan_id: str = "",
    ativo_id: str = "",
    tipo: str = "",
    staff: bool = True,
) -> pd.DataFrame:
    """Retorna tarefas de manutenção. staff=False → somente do cliente, sem Obs_Interna."""
    df = load_sheet("MaintenanceTasks")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_MAINT_TASKS:
        if col not in df.columns:
            df[col] = ""
    if not staff:
        if not client_id:
            return pd.DataFrame()
        df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
        # Nunca expõe obs_interna ao cliente
        if "Obs_Interna" in df.columns:
            df = df.drop(columns=["Obs_Interna"])
    else:
        if client_id:
            df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
    if plan_id:
        df = df[df["Plano_Id"].str.strip() == plan_id.strip()]
    if ativo_id:
        df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]
    if tipo:
        df = df[df["Tipo_Manutencao"].str.strip() == tipo.strip()]
    return df.reset_index(drop=True)


def get_maintenance_task_by_id(task_id: str) -> dict | None:
    """Retorna dict da tarefa ou None."""
    df = load_sheet("MaintenanceTasks")
    if df.empty or "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == task_id.strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    return {col: str(row.get(col, "")).strip() for col in df.columns}


def add_maintenance_task(dados: dict, created_by: str = "") -> str | None:
    """Cria tarefa de manutenção. cliente_id DEVE vir da sessão do supervisor.

    SEGURANÇA:
    - Tarefas por Condição NUNCA têm próxima_execucao automática.
    - 20.000h não cria tarefa automática de overhaul.
    - Obs_Interna nunca é exibida ao cliente.
    """
    if not dados.get("cliente_id"):
        return None
    _ensure_tab_headers("MaintenanceTasks", _HEADERS_MAINT_TASKS)
    task_id = _gerar_id("TASK")
    now     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    tipo    = dados.get("tipo_manutencao", "Calendário")
    # Condição: status fixo "Depende de análise preditiva", sem proxima execucao
    status_inicial = (
        "Depende de análise preditiva" if tipo == "Condição"
        else dados.get("status", "Em dia")
    )
    ok = append_row("MaintenanceTasks", [
        task_id,
        dados.get("cliente_id", ""),
        dados.get("ativo_id", ""),
        dados.get("componente_id", ""),
        dados.get("plano_id", ""),
        dados.get("nome_tarefa", ""),
        dados.get("categoria", ""),
        tipo,
        str(dados.get("periodicidade_dias", "") or ""),
        str(dados.get("periodicidade_horas", "") or ""),
        dados.get("ultima_execucao_data", ""),
        str(dados.get("ultima_execucao_horimetro", "") or ""),
        dados.get("proxima_execucao_data", ""),
        str(dados.get("proxima_execucao_horimetro", "") or ""),
        status_inicial,
        dados.get("prioridade", "Média"),
        "Sim" if dados.get("depende_relatorio") else "Não",
        dados.get("origem", "Cadastro manual"),
        dados.get("descricao", ""),
        dados.get("recomendacao", ""),
        dados.get("obs_interna", ""),
        now,
        now,
    ])
    return task_id if ok else None


def update_maintenance_task(task_id: str, campos: dict) -> bool:
    """Atualiza campos de uma tarefa de manutenção."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("MaintenanceTasks")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        cell = ws.find(task_id, in_column=headers.index("Id") + 1)
        if not cell:
            return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        campos.setdefault("Updated_At", now)
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        load_sheet.clear()
        return True
    except Exception:
        return False


def delete_maintenance_task(task_id: str) -> bool:
    """Remove tarefa de manutenção."""
    return delete_row_by_id("MaintenanceTasks", "Id", task_id)


def get_maintenance_executions(
    client_id: str = "",
    task_id: str = "",
    ativo_id: str = "",
    limit: int = 50,
) -> pd.DataFrame:
    """Retorna execuções de manutenção."""
    df = load_sheet("MaintenanceExecutions")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_MAINT_EXEC:
        if col not in df.columns:
            df[col] = ""
    if client_id:
        df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
    if ativo_id:
        df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]
    if task_id:
        df = df[df["Task_Id"].str.strip() == task_id.strip()]
    return df.iloc[-limit:].iloc[::-1].reset_index(drop=True)


def add_maintenance_execution(dados: dict) -> str | None:
    """Registra execução de uma tarefa de manutenção."""
    _ensure_tab_headers("MaintenanceExecutions", _HEADERS_MAINT_EXEC)
    exec_id = _gerar_id("EXEC")
    now     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("MaintenanceExecutions", [
        exec_id,
        dados.get("cliente_id", ""),
        dados.get("ativo_id", ""),
        dados.get("task_id", ""),
        dados.get("executado_em", now[:10].replace("-", "/")),
        str(dados.get("horimetro_execucao", "") or ""),
        dados.get("responsavel", ""),
        dados.get("descricao_execucao", ""),
        dados.get("evidencias", ""),
        dados.get("arquivo_url", ""),
        dados.get("obs_interna", ""),
        now,
    ])
    return exec_id if ok else None


def complete_maintenance_task(task_id: str, exec_dados: dict, executed_by: str = "") -> dict:
    """Conclui tarefa: registra execução, atualiza próxima execução, cria evento na timeline.

    SEGURANÇA:
    - Obs_Interna nunca é enviada ao cliente.
    - Não conclui automaticamente tarefas por Condição sem avaliação técnica.
    - 20.000h não dispara overhaul automático.
    """
    from datetime import timedelta as _td, datetime as _dt

    task = get_maintenance_task_by_id(task_id)
    if not task:
        return {"ok": False, "erro": "Tarefa não encontrada."}

    tipo        = str(task.get("Tipo_Manutencao", "")).strip()
    nome        = str(task.get("Nome_Tarefa", "")).strip()
    cliente_id  = str(task.get("Cliente_Id", "")).strip()
    ativo_id    = str(task.get("Ativo_Id", "")).strip()
    period_dias = 0
    period_h    = 0
    try:
        period_dias = int(float(str(task.get("Periodicidade_Dias", 0) or 0)))
    except Exception:
        pass
    try:
        period_h = int(float(str(task.get("Periodicidade_Horas", 0) or 0)))
    except Exception:
        pass

    data_exec = exec_dados.get("executado_em", _dt.now().strftime("%d/%m/%Y"))
    h_exec    = exec_dados.get("horimetro_execucao", "")

    # 1. Registro de execução
    exec_id = add_maintenance_execution({
        "cliente_id":         cliente_id,
        "ativo_id":           ativo_id,
        "task_id":            task_id,
        "executado_em":       data_exec,
        "horimetro_execucao": h_exec,
        "responsavel":        executed_by,
        "descricao_execucao": exec_dados.get("descricao", ""),
        "evidencias":         exec_dados.get("evidencias", ""),
        "arquivo_url":        exec_dados.get("arquivo_url", ""),
        "obs_interna":        exec_dados.get("obs_interna", ""),
    })

    # 2. Calcula próxima execução e atualiza tarefa
    upd: dict = {
        "Ultima_Execucao_Data":      data_exec,
        "Ultima_Execucao_Horimetro": str(h_exec or ""),
    }

    if tipo in ("Calendário", "Calendario") and period_dias:
        try:
            prox = (_dt.strptime(data_exec, "%d/%m/%Y") + _td(days=period_dias)).strftime("%d/%m/%Y")
            upd["Proxima_Execucao_Data"] = prox
        except Exception:
            pass

    elif tipo in ("Horímetro", "Horimetro") and period_h and h_exec:
        try:
            prox_h = int(float(str(h_exec))) + period_h
            upd["Proxima_Execucao_Horimetro"] = str(prox_h)
        except Exception:
            pass

    update_maintenance_task(task_id, upd)

    # 3. Evento na timeline
    descr_tl = (
        f"Tarefa '{nome}' concluída em {data_exec}"
        + (f" com horímetro {h_exec}h." if h_exec else ".")
        + (f" Responsável: {executed_by}." if executed_by else "")
    )
    add_report_timeline_event({
        "ativo_id":        ativo_id or cliente_id,
        "cliente_id":      cliente_id,
        "tipo":            "manutencao_concluida",
        "titulo":          f"Manutenção concluída: {nome}",
        "descricao":       descr_tl,
        "data":            data_exec,
        "origem":          "Plano de Manutenção",
        "report_id":       "",
        "visivel_cliente": "true",
        "obs_interna":     exec_dados.get("obs_interna", ""),
    })

    return {"ok": True, "exec_id": exec_id}


def generate_maintenance_alerts(client_id: str = "", ativo_id: str = "") -> int:
    """Escaneia tarefas e gera alertas internos para próximas do vencimento / vencidas.

    SEGURANÇA:
    - Tarefas por Condição nunca geram alerta automático.
    - 20.000h não gera alerta de overhaul.
    - Sem WhatsApp / e-mail.
    """
    df = get_maintenance_tasks(client_id=client_id, ativo_id=ativo_id, staff=True)
    if df.empty:
        return 0

    count = 0
    for _, row in df.iterrows():
        task     = row.to_dict()
        tipo     = str(task.get("Tipo_Manutencao", "")).strip()
        if tipo in ("Condição", "Condicao"):
            continue   # condição nunca vira alerta automático

        aid      = str(task.get("Ativo_Id", "")).strip()
        cid      = str(task.get("Cliente_Id", "")).strip()
        h_atual  = get_horimetro(aid) or 0
        status   = calc_task_status(task, h_atual)

        if status not in ("Próxima do vencimento", "Vencida"):
            continue

        nome    = str(task.get("Nome_Tarefa", "")).strip()
        prio    = "Urgente" if status == "Vencida" else "Alta"
        titulo  = f"{'Manutenção vencida' if status == 'Vencida' else 'Manutenção próxima'}: {nome}"
        msg     = f"Tarefa '{nome}' está com status '{status}'."
        if aid:
            msg += f" Ativo: {aid}."

        # Empresa para o alerta
        empresa = cid
        try:
            df_cli = get_all_clientes()
            cid_col = "Client_Id" if "Client_Id" in df_cli.columns else "Cliente_Id"
            if cid_col in df_cli.columns:
                m = df_cli[
                    df_cli[cid_col].astype(str).str.strip().str.lower() == cid.lower()
                ]
                empresa = str(m.iloc[0].get("Empresa", cid)) if not m.empty else cid
        except Exception:
            pass

        add_alerta_sv(
            client_id  = cid,
            empresa    = empresa,
            titulo     = titulo,
            descricao  = msg,
            prioridade = prio,
        )
        count += 1

    return count


# ── Chamados V2 — campos estendidos ──────────────────────────────────────────

_HEADERS_CHAMADOS_V2 = [
    "Id", "Client_Id", "Usuario_Id", "Empresa", "Email",
    "Ativo_Id", "Componente_Id", "Report_Id", "Maintenance_Task_Id", "Alert_Id",
    "Titulo", "Descricao", "Categoria", "Prioridade", "Status", "Origem",
    "Responsavel", "Planta", "Equipamento",
    "Aberto_Em", "Atualizado_Em", "Concluido_Em",
    # legado — mantidos para compatibilidade
    "Data_Abertura", "Data_Atualizacao", "Data_Encerramento",
]


def _ensure_chamados_v2_cols() -> None:
    """Garante que colunas V2 existam no sheet Chamados sem apagar dados."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Chamados")
        headers = ws.row_values(1)
        needed  = ["Ativo_Id", "Componente_Id", "Report_Id",
                   "Maintenance_Task_Id", "Alert_Id", "Categoria", "Origem"]
        for col in needed:
            if col not in headers:
                ws.update_cell(1, len(headers) + 1, col)
                headers.append(col)
    except Exception:
        pass


def abrir_chamado_v2(dados: dict) -> str | None:
    """
    Abre chamado técnico com todos os campos da V2.
    Retorna o chamado_id gerado ou None em caso de erro.
    SEGURANÇA: client_id deve vir SEMPRE da sessão antes de chamar esta função.
    """
    _ensure_chamados_v2_cols()
    chamado_id = _gerar_id("CH")
    agora      = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("Chamados", [
        chamado_id,
        dados.get("client_id", ""),
        dados.get("usuario_id", ""),
        dados.get("empresa", dados.get("client_id", "")),
        dados.get("email", ""),
        dados.get("ativo_id", ""),
        dados.get("componente_id", ""),
        dados.get("report_id", ""),
        dados.get("maintenance_task_id", ""),
        dados.get("alert_id", ""),
        dados.get("titulo", ""),
        dados.get("descricao", ""),
        dados.get("categoria", "Dúvida técnica"),
        dados.get("prioridade", "Média"),
        "Aberto",
        dados.get("origem", "Portal do Cliente"),
        "",   # responsavel
        dados.get("planta", ""),
        dados.get("equipamento", ""),
        agora, agora, "",   # Aberto_Em, Atualizado_Em, Concluido_Em
        agora, agora, "",   # legado: Data_Abertura, Data_Atualizacao, Data_Encerramento
    ])
    if ok:
        # Cria evento no histórico técnico do ativo
        ativo_id  = dados.get("ativo_id", "")
        client_id = dados.get("client_id", "")
        titulo    = dados.get("titulo", "")
        if ativo_id:
            try:
                add_report_timeline_event({
                    "ativo_id":       ativo_id,
                    "cliente_id":     client_id,
                    "tipo":           "chamado_aberto",
                    "titulo":         f"Chamado aberto: {titulo}",
                    "descricao":      f"Chamado técnico #{chamado_id} aberto para o ativo.",
                    "data":           agora[:10],
                    "origem":         "Chamados Técnicos",
                    "report_id":      dados.get("report_id", ""),
                    "visivel_cliente": True,
                })
            except Exception:
                pass
        load_sheet.clear()
        return chamado_id
    return None


def get_chamados_v2(client_id: str, status: str = "", ativo_id: str = "") -> pd.DataFrame:
    """
    Chamados do cliente com colunas V2.
    SEGURANÇA: client_id vem da sessão — nunca do front-end.
    """
    df = load_sheet("Chamados")
    if df.empty:
        return df
    # Garante colunas mínimas
    for col in ("Client_Id", "Id", "Titulo", "Status", "Prioridade", "Categoria",
                "Origem", "Ativo_Id", "Descricao", "Aberto_Em", "Atualizado_Em"):
        if col not in df.columns:
            df[col] = ""
    # Filtro por cliente — SEMPRE
    cid_col = "Client_Id" if "Client_Id" in df.columns else "Empresa"
    df = df[df[cid_col].str.strip().str.lower() == client_id.strip().lower()]
    if status:
        df = df[df["Status"].str.strip().str.lower() == status.lower()]
    if ativo_id:
        df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]
    df["_dt"] = pd.to_datetime(df.get("Aberto_Em", pd.Series(dtype=str)), dayfirst=True, errors="coerce")
    return df.sort_values("_dt", ascending=False).drop(columns=["_dt"]).reset_index(drop=True)


def get_chamado_v2_by_id(chamado_id: str, client_id: str = "") -> dict | None:
    """
    Retorna chamado pelo Id.
    Se client_id fornecido, valida que o chamado pertence ao cliente.
    SEGURANÇA: client_id sempre da sessão.
    """
    df = load_sheet("Chamados")
    if df.empty:
        df = _mock_chamados()
    if "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == str(chamado_id).strip()]
    if match.empty:
        return None
    row = match.iloc[0].to_dict()
    # Validação de ownership
    if client_id:
        cid_col = "Client_Id" if "Client_Id" in row else "Empresa"
        if str(row.get(cid_col, "")).strip().lower() != client_id.strip().lower():
            return None  # cliente não pode ver chamado de outro cliente
    return row


def concluir_chamado(chamado_id: str, concluded_by: str = "") -> bool:
    """
    Conclui um chamado: atualiza status, data e cria evento no histórico do ativo.
    """
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = update_chamado(chamado_id, {
        "Status":            "Concluído",
        "Concluido_Em":      agora,
        "Data_Encerramento": agora,
    })
    if ok:
        # Busca ativo_id do chamado para criar evento
        chamado = get_chamado_by_id(chamado_id)
        if chamado:
            ativo_id  = str(chamado.get("Ativo_Id", "")).strip()
            client_id = str(chamado.get("Client_Id",
                           chamado.get("Empresa", ""))).strip()
            titulo    = str(chamado.get("Titulo", "")).strip()
            if ativo_id:
                try:
                    add_report_timeline_event({
                        "ativo_id":       ativo_id,
                        "cliente_id":     client_id,
                        "tipo":           "chamado_concluido",
                        "titulo":         f"Chamado concluído: {titulo}",
                        "descricao":      f"Chamado técnico #{chamado_id} concluído por {concluded_by or 'Pred.IO'}.",
                        "data":           agora[:10],
                        "origem":         "Chamados Técnicos",
                        "visivel_cliente": True,
                    })
                except Exception:
                    pass
    return ok


def responder_chamado(chamado_id: str, mensagem: str, autor: str,
                      novo_status: str = "") -> bool:
    """
    Registra resposta visível ao cliente + atualiza status se informado.
    Cria evento no histórico do ativo quando há ativo vinculado.
    """
    ok = add_mensagem(
        chamado_id    = chamado_id,
        autor         = autor,
        autor_tipo    = "funcionario",
        mensagem      = mensagem,
        visivel_cliente = True,
        tipo_mensagem = "resposta_predio",
    )
    if ok and novo_status:
        chamado    = get_chamado_by_id(chamado_id)
        status_ant = str(chamado.get("Status", "")) if chamado else ""
        update_chamado(chamado_id, {"Status": novo_status})
        if chamado and status_ant and status_ant != novo_status:
            add_mensagem(
                chamado_id    = chamado_id,
                autor         = "sistema",
                autor_tipo    = "sistema",
                mensagem      = f"Status alterado: {status_ant} → {novo_status}",
                visivel_cliente = True,
                tipo_mensagem = "alteracao_status",
            )
        # Evento no histórico do ativo quando respondido
        if chamado:
            ativo_id  = str(chamado.get("Ativo_Id", "")).strip()
            client_id = str(chamado.get("Client_Id",
                           chamado.get("Empresa", ""))).strip()
            titulo    = str(chamado.get("Titulo", "")).strip()
            if ativo_id:
                try:
                    add_report_timeline_event({
                        "ativo_id":       ativo_id,
                        "cliente_id":     client_id,
                        "tipo":           "chamado_respondido",
                        "titulo":         f"Chamado respondido: {titulo}",
                        "descricao":      f"Pred.IO respondeu o chamado #{chamado_id}.",
                        "data":           datetime.now().strftime("%d/%m/%Y"),
                        "origem":         "Chamados Técnicos",
                        "visivel_cliente": True,
                    })
                except Exception:
                    pass
    return ok


def get_chamados_resumo_assistente(client_id: str, ativo_id: str = "") -> list[dict]:
    """
    Resumo de chamados para o Assistente Técnico.
    Nunca retorna observações internas.
    SEGURANÇA: client_id sempre da sessão.
    """
    df = get_chamados_v2(client_id=client_id, ativo_id=ativo_id)
    if df.empty:
        # Fallback para função legada
        df = get_chamados(client_id)
    if df.empty:
        return []
    result = []
    for _, r in df.iterrows():
        result.append({
            "id":         str(r.get("Id", "")).strip(),
            "titulo":     str(r.get("Titulo", "")).strip(),
            "status":     str(r.get("Status", "")).strip(),
            "prioridade": str(r.get("Prioridade", "")).strip(),
            "categoria":  str(r.get("Categoria", "")).strip(),
            "ativo_id":   str(r.get("Ativo_Id", "")).strip(),
            "aberto_em":  str(r.get("Aberto_Em", r.get("Data_Abertura", ""))).strip(),
        })
    return result


def delete_session(token: str) -> None:
    """Invalida o token marcando coluna Ativo=0."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Sessions")
        headers = ws.row_values(1)
        ativo_col = headers.index("Ativo") + 1 if "Ativo" in headers else 8
        cell = ws.find(token)
        if cell:
            ws.update_cell(cell.row, ativo_col, "0")
        load_sheet.clear()
    except Exception:
        pass


# ── Logos de clientes ─────────────────────────────────────────────────────────

_HEADERS_CLIENTE_LOGOS = ["Client_Id", "Logo_B64", "Updated_At"]


def _ensure_logos_tab() -> None:
    try:
        ss = get_spreadsheet()
        try:
            ss.worksheet("ClienteLogos")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title="ClienteLogos", rows=500, cols=3)
            ws.append_row(_HEADERS_CLIENTE_LOGOS, value_input_option="USER_ENTERED")
            load_sheet.clear()
    except Exception:
        pass


def get_client_logo(client_id: str) -> str:
    """Retorna o Logo_B64 do cliente ou string vazia."""
    df = load_sheet("ClienteLogos")
    if df.empty or "Client_Id" not in df.columns:
        return ""
    match = df[df["Client_Id"].str.strip().str.lower() == client_id.lower()]
    if match.empty:
        return ""
    return str(match.iloc[0].get("Logo_B64", "")).strip()


def save_client_logo(client_id: str, logo_b64: str) -> bool:
    """Salva ou atualiza a logo de um cliente (upsert por Client_Id)."""
    try:
        _ensure_logos_tab()
        ss = get_spreadsheet()
        ws = ss.worksheet("ClienteLogos")
        all_values = ws.get_all_values()
        if len(all_values) > 1:
            headers = [h.strip().title() for h in all_values[0]]
            cid_col  = headers.index("Client_Id") if "Client_Id" in headers else 0
            logo_col = (headers.index("Logo_B64") + 1) if "Logo_B64" in headers else 2
            upd_col  = (headers.index("Updated_At") + 1) if "Updated_At" in headers else 3
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) > cid_col and row[cid_col].strip().lower() == client_id.lower():
                    ws.update_cell(i, logo_col, logo_b64)
                    ws.update_cell(i, upd_col, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                    load_sheet.clear()
                    return True
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ws.append_row([client_id, logo_b64, now], value_input_option="USER_ENTERED")
        load_sheet.clear()
        return True
    except Exception:
        return False


# ── Edição de registros existentes ───────────────────────────────────────────

def update_usuario(email: str, campos: dict) -> bool:
    """Atualiza campos de um usuário/cliente pelo e-mail (busca em Usuarios e Clientes)."""
    try:
        ss = get_spreadsheet()
        for tab in ("Usuarios", "Clientes"):
            try:
                ws = ss.worksheet(tab)
            except gspread.exceptions.WorksheetNotFound:
                continue
            headers = ws.row_values(1)
            if "Email" not in headers:
                continue
            email_col = headers.index("Email") + 1
            cell = ws.find(email.strip().lower(), in_column=email_col)
            if not cell:
                continue
            row_idx = cell.row
            for campo, valor in campos.items():
                if campo in headers:
                    ws.update_cell(row_idx, headers.index(campo) + 1, str(valor))
            load_sheet.clear()
            return True
        return False
    except Exception:
        return False


def update_ativo(ativo_id: str, campos: dict) -> bool:
    """Atualiza campos de um ativo existente pelo Id."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Ativos")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell = ws.find(ativo_id, in_column=id_col)
        if not cell:
            return False
        row_idx = cell.row
        campos = dict(campos)
        campos["Data"] = datetime.now().strftime("%d/%m/%Y")
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(row_idx, headers.index(campo) + 1, str(valor))
        load_sheet.clear()
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# RELATÓRIOS EXECUTIVOS — aba RelatoriosExecutivos
# ═══════════════════════════════════════════════════════════════════════════════

_HEADERS_RELATORIOS_EXEC = [
    "Id", "Client_Id", "Ativo_Id", "Titulo", "Status",
    "Gerado_Em", "Atualizado_Em", "Publicado_Em", "Gerado_Por",
    "Periodo_Inicio", "Periodo_Fim",
    "Versao", "Resumo_Executivo", "Obs_Interna",
    "Arquivo_Revisado_Url", "Arquivo_Revisado_Nome",
]


@st.cache_data(ttl=30)
def get_relatorios_executivos(client_id: str, ativo_id: str = "") -> pd.DataFrame:
    """
    Retorna relatórios executivos do cliente.
    SEGURANÇA: client_id vem sempre da sessão.
    """
    try:
        df = load_sheet("RelatoriosExecutivos")
    except Exception:
        return pd.DataFrame(columns=_HEADERS_RELATORIOS_EXEC)

    if df.empty:
        return df

    for col in _HEADERS_RELATORIOS_EXEC:
        if col not in df.columns:
            df[col] = ""

    df = df[df["Client_Id"].str.strip().str.lower() == client_id.strip().lower()]

    if ativo_id:
        df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]

    df["_dt"] = pd.to_datetime(df.get("Gerado_Em", pd.Series(dtype=str)), dayfirst=True, errors="coerce")
    return df.sort_values("_dt", ascending=False).drop(columns=["_dt"]).reset_index(drop=True)


def add_relatorio_executivo(
    client_id: str,
    ativo_id: str,
    titulo: str,
    gerado_por: str = "",
    periodo_inicio: str = "",
    periodo_fim: str = "",
    obs_interna: str = "",
) -> str | None:
    """
    Registra um novo relatório executivo (status inicial: Rascunho gerado).
    Retorna o Id gerado ou None em caso de erro.
    SEGURANÇA: client_id sempre da sessão.
    """
    relatorio_id = str(uuid.uuid4())[:8].upper()
    agora        = datetime.now().strftime("%d/%m/%Y %H:%M")

    row = {
        "Id":             relatorio_id,
        "Client_Id":      client_id,
        "Ativo_Id":       ativo_id,
        "Titulo":         titulo,
        "Status":         "Rascunho gerado",
        "Gerado_Em":      agora,
        "Atualizado_Em":  agora,
        "Gerado_Por":     gerado_por,
        "Periodo_Inicio": periodo_inicio,
        "Periodo_Fim":    periodo_fim,
        "Versao":         "1",
        "Obs_Interna":    obs_interna,
    }

    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("RelatoriosExecutivos")
        except Exception:
            ws = ss.add_worksheet("RelatoriosExecutivos", rows=1000, cols=len(_HEADERS_RELATORIOS_EXEC))
            ws.append_row(_HEADERS_RELATORIOS_EXEC)

        headers = ws.row_values(1)
        if not headers:
            ws.append_row(_HEADERS_RELATORIOS_EXEC)
            headers = _HEADERS_RELATORIOS_EXEC

        new_row = [str(row.get(h, "")) for h in headers]
        ws.append_row(new_row)
        load_sheet.clear()
        return relatorio_id
    except Exception:
        return None


def update_relatorio_executivo(relatorio_id: str, client_id: str, **campos) -> bool:
    """
    Atualiza campos de um relatório executivo.
    client_id é validado para garantir que o supervisor só edita relatórios do cliente correto.
    SEGURANÇA: client_id sempre da sessão.
    """
    try:
        ss      = get_spreadsheet()
        ws      = ss.worksheet("RelatoriosExecutivos")
        headers = ws.row_values(1)

        if "Id" not in headers:
            return False

        id_col  = headers.index("Id") + 1
        cell    = ws.find(relatorio_id, in_column=id_col)
        if not cell:
            return False

        row_idx = cell.row

        # Valida client_id antes de gravar
        if "Client_Id" in headers:
            cid_col_idx = headers.index("Client_Id") + 1
            existing_cid = ws.cell(row_idx, cid_col_idx).value or ""
            if existing_cid.strip().lower() != client_id.strip().lower():
                return False

        campos["Atualizado_Em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(row_idx, headers.index(campo) + 1, str(valor))
            else:
                # Coluna nova — adiciona ao cabeçalho e grava na linha
                try:
                    next_col = len(headers) + 1
                    ws.update_cell(1, next_col, campo)
                    ws.update_cell(row_idx, next_col, str(valor))
                    headers.append(campo)
                except Exception:
                    pass

        load_sheet.clear()
        return True
    except Exception:
        return False


@st.cache_data(ttl=60)
def get_relatorios_executivos_publicados(client_id: str, ativo_id: str = "") -> pd.DataFrame:
    """
    Retorna SOMENTE relatórios executivos publicados do cliente.
    Usado pelo Portal do Cliente — NUNCA retorna rascunhos ou obs_interna.
    SEGURANÇA: client_id vem sempre da sessão.
    """
    df = get_relatorios_executivos(client_id, ativo_id=ativo_id)
    if df.empty:
        return df

    # Filtra apenas publicados
    df = df[df["Status"].str.strip().str.lower() == "publicado"].copy()

    if df.empty:
        return df

    # Garante campos extras
    for col in ("Resumo_Executivo", "Arquivo_Revisado_Url", "Arquivo_Revisado_Nome", "Publicado_Em"):
        if col not in df.columns:
            df[col] = ""

    # Remove campos internos — nunca expõe ao cliente
    for col_int in ("Obs_Interna", "Gerado_Por"):
        if col_int in df.columns:
            df = df.drop(columns=[col_int])

    return df.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CHUNKS DE RELATÓRIOS TÉCNICOS — aba TechnicalReportChunks
# ═══════════════════════════════════════════════════════════════════════════════

_HEADERS_REPORT_CHUNKS = [
    "Id", "Report_Id", "Client_Id", "Ativo_Id",
    "Chunk_Index", "Titulo_Secao", "Conteudo", "Palavras_Chave", "Indexado_Em",
]


def index_relatorio_tecnico(report_id: str, client_id: str, ativo_id: str, dados: dict) -> bool:
    """
    Cria/atualiza chunks do relatório técnico na aba TechnicalReportChunks.
    Extrai Resumo e Recomendacoes como chunks para uso pelo assistente.

    SEGURANÇA: Obs_Interna nunca é indexada.
    """
    if not report_id or not client_id:
        return False

    _ensure_tab_headers("TechnicalReportChunks", _HEADERS_REPORT_CHUNKS)

    agora     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    titulo    = str(dados.get("Titulo",         "")).strip()
    tipo      = str(dados.get("Tipo_Servico",   "")).strip()
    sev       = str(dados.get("Severidade",     "")).strip()
    data_rel  = str(dados.get("Data_Relatorio", "")).strip()
    equip     = str(dados.get("Equipamento",    "")).strip() or ativo_id
    resumo    = str(dados.get("Resumo",         "")).strip()
    recomend  = str(dados.get("Recomendacoes",  "")).strip()

    chunks_to_insert: list[list] = []

    # Chunk 0 — ficha técnica
    meta_conteudo = (
        f"Relatório: {titulo}. "
        f"Tipo: {tipo}. Severidade: {sev}. Data: {data_rel}. Equipamento/Ativo: {equip}."
    )
    chunks_to_insert.append([
        _gerar_id("RCK"), report_id, client_id.strip().lower(), ativo_id,
        "0", "Ficha técnica", meta_conteudo, f"{titulo},{tipo},{sev}", agora,
    ])

    if resumo:
        chunks_to_insert.append([
            _gerar_id("RCK"), report_id, client_id.strip().lower(), ativo_id,
            "1", "Resumo", resumo, f"resumo,{sev},{tipo}", agora,
        ])

    if recomend:
        chunks_to_insert.append([
            _gerar_id("RCK"), report_id, client_id.strip().lower(), ativo_id,
            "2", "Recomendações", recomend, f"recomendacoes,acao,{tipo}", agora,
        ])

    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("TechnicalReportChunks")
        except Exception:
            ws = ss.add_worksheet("TechnicalReportChunks", rows=2000, cols=len(_HEADERS_REPORT_CHUNKS))
            ws.append_row(_HEADERS_REPORT_CHUNKS)

        headers = ws.row_values(1)
        if not headers:
            ws.append_row(_HEADERS_REPORT_CHUNKS)

        # Remove chunks antigos para este report_id
        all_values = ws.get_all_values()
        if len(all_values) > 1:
            hdrs = all_values[0]
            if "Report_Id" in hdrs:
                rid_col = hdrs.index("Report_Id")
                rows_to_delete = [
                    i + 2  # 1-based, +1 for header
                    for i, row in enumerate(all_values[1:])
                    if len(row) > rid_col and row[rid_col].strip() == report_id
                ]
                for row_num in reversed(rows_to_delete):
                    ws.delete_rows(row_num)

        for chunk_row in chunks_to_insert:
            ws.append_row(chunk_row)

        load_sheet.clear()
        return True
    except Exception:
        return False


@st.cache_data(ttl=60)
def get_chunks_relatorio(report_id: str, client_id: str = "") -> pd.DataFrame:
    """
    Retorna chunks do relatório técnico indexado.
    SEGURANÇA: filtra por client_id se fornecido.
    """
    df = load_sheet("TechnicalReportChunks")
    if df.empty:
        return pd.DataFrame()

    for col in _HEADERS_REPORT_CHUNKS:
        if col not in df.columns:
            df[col] = ""

    df = df[df["Report_Id"].str.strip() == report_id.strip()]

    if client_id:
        df = df[df["Client_Id"].str.strip().str.lower() == client_id.strip().lower()]

    return df.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ETAPA 6.7 — TEMPLATES DE NOTIFICAÇÃO  (aba NotificationTemplates)
# ═══════════════════════════════════════════════════════════════════════════════

_HEADERS_NOTIF_TEMPLATES = [
    "Id", "Nome", "Tipo_Evento", "Canal", "Assunto", "Corpo",
    "Variaveis_Permitidas", "Status", "Created_At", "Updated_At",
]


@st.cache_data(ttl=60)
def get_notification_templates(status: str = "") -> pd.DataFrame:
    """Retorna templates de notificação. status='' → todos; status='Ativo' → apenas ativos."""
    df = load_sheet("NotificationTemplates")
    if df.empty:
        return pd.DataFrame(columns=_HEADERS_NOTIF_TEMPLATES)
    for col in _HEADERS_NOTIF_TEMPLATES:
        if col not in df.columns:
            df[col] = ""
    if status:
        df = df[df["Status"].str.strip() == status]
    return df.reset_index(drop=True)


def get_notification_template_by_id(template_id: str) -> dict | None:
    """Retorna template por ID ou None."""
    df = load_sheet("NotificationTemplates")
    if df.empty or "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == template_id.strip()]
    if match.empty:
        return None
    return {col: str(match.iloc[0].get(col, "")).strip() for col in _HEADERS_NOTIF_TEMPLATES}


def add_notification_template(dados: dict) -> bool:
    """Cria um novo template de notificação."""
    _ensure_tab_headers("NotificationTemplates", _HEADERS_NOTIF_TEMPLATES)
    tpl_id = _gerar_id("TPL")
    now    = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("NotificationTemplates", [
        tpl_id,
        dados.get("nome",                 ""),
        dados.get("tipo_evento",          ""),
        dados.get("canal",                ""),
        dados.get("assunto",              ""),
        dados.get("corpo",                ""),
        dados.get("variaveis_permitidas", ""),
        dados.get("status",               "Rascunho"),
        now, now,
    ])
    if ok:
        get_notification_templates.clear()
    return ok


def update_notification_template(template_id: str, campos: dict) -> bool:
    """Atualiza campos de um template de notificação."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("NotificationTemplates")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(template_id, in_column=id_col)
        if not cell:
            return False
        campos["Updated_At"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        load_sheet.clear()
        get_notification_templates.clear()
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ETAPA 6.7 — FILA DE NOTIFICAÇÕES  (aba NotificationQueue)
# ═══════════════════════════════════════════════════════════════════════════════

_HEADERS_NOTIF_QUEUE = [
    "Id", "Client_Id", "Contato_Id", "Notification_Id", "Template_Id",
    "Tipo_Evento", "Canal", "Destinatario", "Assunto", "Corpo_Renderizado",
    "Link_Portal", "Prioridade", "Status", "Modo", "Erro_Validacao",
    "Created_At", "Updated_At",
]


def add_notification_queue_item(dados: dict) -> str:
    """
    Enfileira uma notificação em modo=Teste.
    SEGURANÇA: modo sempre 'Teste' nesta etapa. Nunca envia mensagem real.
    """
    _ensure_tab_headers("NotificationQueue", _HEADERS_NOTIF_QUEUE)
    item_id = _gerar_id("NQ")
    now     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("NotificationQueue", [
        item_id,
        dados.get("client_id",          ""),
        dados.get("contato_id",         ""),
        dados.get("notification_id",    ""),
        dados.get("template_id",        ""),
        dados.get("tipo_evento",        ""),
        dados.get("canal",              ""),
        dados.get("destinatario",       ""),
        dados.get("assunto",            ""),
        dados.get("corpo_renderizado",  ""),
        dados.get("link_portal",        ""),
        dados.get("prioridade",         "Média"),
        dados.get("status",             "Simulado"),
        "Teste",  # modo sempre Teste nesta etapa
        dados.get("erro_validacao",     ""),
        now, now,
    ])
    return item_id if ok else ""


@st.cache_data(ttl=30)
def get_notification_queue(client_id: str = "", status: str = "", limit: int = 100) -> pd.DataFrame:
    """
    Retorna fila de notificações.
    SEGURANÇA: staff chama sem client_id; por cliente, filtra pelo client_id.
    """
    df = load_sheet("NotificationQueue")
    if df.empty:
        return pd.DataFrame(columns=_HEADERS_NOTIF_QUEUE)
    for col in _HEADERS_NOTIF_QUEUE:
        if col not in df.columns:
            df[col] = ""
    if client_id:
        df = df[df["Client_Id"].str.strip().str.lower() == client_id.strip().lower()]
    if status:
        df = df[df["Status"].str.strip() == status]
    return df.tail(limit).reset_index(drop=True)


def update_notification_queue_status(item_id: str, new_status: str) -> bool:
    """Atualiza status de item da fila."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("NotificationQueue")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(item_id, in_column=id_col)
        if not cell:
            return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if "Status" in headers:
            ws.update_cell(cell.row, headers.index("Status") + 1, new_status)
        if "Updated_At" in headers:
            ws.update_cell(cell.row, headers.index("Updated_At") + 1, now)
        load_sheet.clear()
        get_notification_queue.clear()
        return True
    except Exception:
        return False
