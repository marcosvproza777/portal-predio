"""Google Sheets — conexão e operações de leitura/escrita."""
import base64
import json
import os
from datetime import datetime

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


def load_sheet(tab_name: str) -> pd.DataFrame:
    """Carrega uma aba e normaliza os nomes das colunas."""
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
        return True
    except Exception:
        return False


# ── Funções de domínio ────────────────────────────────────────────────────────

def get_relatorios(client_id: str, filtros: dict | None = None) -> pd.DataFrame:
    """Retorna relatórios do cliente. Filtra SEMPRE por client_id no servidor."""
    df = load_sheet("Relatorios")
    if df.empty:
        return df
    req = {"Empresa", "Tipo_Servico", "Planta", "Equipamento", "Mes", "Ano",
           "Data_Relatorio", "Arquivo_Url", "Titulo", "Status"}
    for col in req:
        if col not in df.columns:
            df[col] = ""
    # Filtro de segurança — sempre por client_id
    df = df[df["Empresa"].str.strip().str.lower() == client_id.lower()].copy()
    if filtros:
        if filtros.get("tipo"):
            df = df[df["Tipo_Servico"].str.strip().str.lower() == filtros["tipo"].lower()]
        if filtros.get("planta"):
            df = df[df["Planta"].str.strip().str.lower() == filtros["planta"].lower()]
        if filtros.get("equipamento"):
            mask = df["Equipamento"].str.lower().str.contains(
                filtros["equipamento"].lower(), na=False)
            df = df[mask]
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
    """Retorna chamados do cliente filtrados por client_id."""
    df = load_sheet("Chamados")
    if df.empty:
        return df
    return df[df["Empresa"].str.strip().str.lower() == client_id.lower()].reset_index(drop=True)


def get_historico_assistente(client_id: str, limit: int = 20) -> pd.DataFrame:
    """Retorna histórico do assistente filtrado por client_id."""
    df = load_sheet("AssistenteLogs")
    if df.empty:
        return df
    df = df[df["Empresa"].str.strip().str.lower() == client_id.lower()]
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
    """Retorna ativos (faróis) do cliente."""
    df = load_sheet("Ativos")
    if df.empty:
        return df
    return df[df["Empresa"].str.strip().str.lower() == client_id.lower()].copy()
