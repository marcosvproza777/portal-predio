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
from oauth2client.service_account import ServiceAccountCredentials

SHEET_ID = "1cyDz6nuZ9ro7Inq-DNg9OH9d7GNn17WHZSIikkQ6hOA"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    try:
        creds = None
        try:
            if "gcp_service_account" in st.secrets:
                info = dict(st.secrets["gcp_service_account"])
                info["private_key"] = info["private_key"].replace("\\n", "\n")
                creds = ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)
        except Exception:
            pass
        if creds is None and os.environ.get("GCP_CREDENTIALS_B64"):
            raw = base64.b64decode(os.environ["GCP_CREDENTIALS_B64"]).decode("utf-8")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(raw), SCOPE)
        if creds is None and os.environ.get("GCP_CREDENTIALS_JSON"):
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                json.loads(os.environ["GCP_CREDENTIALS_JSON"]), SCOPE)
        if creds is None and os.path.exists("/etc/secrets/credentials.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                "/etc/secrets/credentials.json", SCOPE)
        if creds is None and os.path.exists("credentials.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
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
        records = ws.get_all_records()
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
            ws = ss.add_worksheet(title=tab_name, rows=1000, cols=20)
        ws.append_row(values, value_input_option="USER_ENTERED")
        load_sheet.clear()
        return True
    except Exception:
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


def get_mensagens_visiveis_cliente(chamado_id: str) -> pd.DataFrame:
    """Mensagens visíveis ao cliente (Visivel_Cliente = 1)."""
    df = get_mensagens_chamado(chamado_id)
    if df.empty or "Visivel_Cliente" not in df.columns:
        return df
    return df[df["Visivel_Cliente"].astype(str).str.strip() == "1"].reset_index(drop=True)


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

def get_historico_assistente(client_id: str, limit: int = 20) -> pd.DataFrame:
    df = load_sheet("AssistenteLogs")
    if df.empty:
        return df
    for col_candidate in ("Empresa", "Client_Id"):
        if col_candidate in df.columns:
            df = df[df[col_candidate].str.strip().str.lower() == client_id.lower()]
            return df.tail(limit).iloc[::-1].reset_index(drop=True)
    return pd.DataFrame()


def salvar_log_assistente(client_id: str, email: str, pergunta: str,
                          resposta: str, fontes: str = "") -> None:
    append_row("AssistenteLogs", [
        client_id, email, pergunta, resposta, fontes,
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
            whatsapp = str(r.get("Whatsapp", "")).strip()
            uid      = str(r.get("Id",       "")).strip() or f"pref_{client_id}_{len(contacts)}"
            contacts.append({
                "id":           uid,
                "usuario_id":   str(r.get("Usuario_Id", "")).strip(),
                "nome":         str(r.get("Nome",       "")).strip() or str(r.get("Usuario_Id", "")).strip(),
                "email":        email,
                "whatsapp":     whatsapp,
                "tem_email":    bool(email    and str(r.get("Receber_Email",    "false")).strip().lower() == "true"),
                "tem_whatsapp": bool(whatsapp and str(r.get("Receber_Whatsapp", "false")).strip().lower() == "true"),
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
