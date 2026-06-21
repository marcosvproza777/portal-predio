"""Google Sheets — conexão e operações de leitura/escrita."""
import base64
import json
import os
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


@st.cache_data(ttl=60, show_spinner=False)
def load_sheet(tab_name: str) -> pd.DataFrame:
    """Carrega uma aba e normaliza os nomes das colunas. Cache de 60s."""
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
    """Adiciona uma linha. Cria a aba se não existir. Invalida cache."""
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


# ── Funções de domínio ────────────────────────────────────────────────────────

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


def get_chamados(client_id: str) -> pd.DataFrame:
    df = load_sheet("Chamados")
    if df.empty:
        return df
    col = "Empresa" if "Empresa" in df.columns else (
          "Client_Id" if "Client_Id" in df.columns else None)
    if not col:
        return pd.DataFrame()
    return df[df[col].str.strip().str.lower() == client_id.lower()].reset_index(drop=True)


def get_historico_assistente(client_id: str, limit: int = 20) -> pd.DataFrame:
    df = load_sheet("AssistenteLogs")
    if df.empty:
        return df
    col = "Empresa" if "Empresa" in df.columns else (
          "Client_Id" if "Client_Id" in df.columns else None)
    if not col:
        return pd.DataFrame()
    df = df[df[col].str.strip().str.lower() == client_id.lower()]
    return df.tail(limit).iloc[::-1].reset_index(drop=True)


def salvar_log_assistente(client_id: str, email: str, pergunta: str,
                          resposta: str, fontes: str = "") -> None:
    append_row("AssistenteLogs", [
        client_id, email, pergunta, resposta, fontes,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    ])


def abrir_chamado(client_id: str, email: str, titulo: str, descricao: str,
                  planta: str, equipamento: str, prioridade: str) -> bool:
    return append_row("Chamados", [
        client_id, email, titulo, descricao, planta, equipamento,
        prioridade, "Aberto", datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    ])


def get_ativos(client_id: str) -> pd.DataFrame:
    df = load_sheet("Ativos")
    if df.empty:
        return df
    return df[df["Empresa"].str.strip().str.lower() == client_id.lower()].copy()


# ── Sessões persistentes ──────────────────────────────────────────────────────

def save_session(token: str, empresa: str, email: str,
                 telefone: str, client_id: str) -> None:
    expiry = (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y %H:%M:%S")
    append_row("Sessions", [
        token, empresa, email, telefone, client_id,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"), expiry, "1",
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
        "empresa":    str(row.get("Empresa",   "")).strip(),
        "email":      str(row.get("Email",     "")).strip(),
        "telefone":   str(row.get("Telefone",  "")).strip(),
        "client_id":  str(row.get("Client_Id", "")).strip(),
    }


def delete_session(token: str) -> None:
    """Invalida o token marcando coluna Ativo=0."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Sessions")
        cell = ws.find(token)
        if cell:
            ws.update_cell(cell.row, 8, "0")
        load_sheet.clear()
    except Exception:
        pass
