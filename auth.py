"""Autenticação e controle de acesso."""
import streamlit as st
from sheets import load_sheet


def get_client_id(empresa: str) -> str:
    """Normaliza o nome da empresa como identificador de cliente."""
    return empresa.strip().lower()


def authenticate(email: str, password: str):
    """Valida credenciais. Retorna (empresa, telefone) ou (None, None)."""
    df = load_sheet("Clientes")
    if df.empty:
        return None, None
    required = {"Empresa", "Email", "Senha"}
    if not required.issubset(df.columns):
        st.error("Aba 'Clientes' sem colunas esperadas.")
        return None, None
    match = df[
        (df["Email"].str.strip().str.lower() == email.strip().lower()) &
        (df["Senha"].astype(str).str.strip() == password.strip())
    ]
    if match.empty:
        return None, None
    row = match.iloc[0]
    return str(row["Empresa"]).strip(), str(row.get("Telefone", "")).strip()


def login(empresa: str, telefone: str) -> None:
    """Salva sessão após login bem-sucedido."""
    st.session_state.update(
        logged_in=True,
        empresa=empresa,
        telefone=telefone,
        client_id=get_client_id(empresa),
        page="dashboard",
    )


def logout() -> None:
    """Encerra a sessão."""
    for key in ("logged_in", "empresa", "telefone", "client_id", "page",
                "chat_history"):
        st.session_state.pop(key, None)


def require_auth() -> bool:
    """Verifica autenticação. Redireciona para login se não autenticado."""
    if not st.session_state.get("logged_in"):
        st.session_state["page"] = "login"
        return False
    return True


def current_client_id() -> str:
    """Retorna o client_id da sessão — NUNCA aceitar do front-end."""
    return st.session_state.get("client_id", "")


def current_empresa() -> str:
    return st.session_state.get("empresa", "")


def current_email() -> str:
    return st.session_state.get("email_logado", "")
