"""Autenticação e controle de acesso."""
import secrets
import streamlit as st
from sheets import load_sheet


def get_client_id(empresa: str) -> str:
    return empresa.strip().lower()


def authenticate(email: str, password: str):
    """Valida credenciais contra aba 'Clientes' ou 'Usuarios'."""
    df = load_sheet("Clientes")
    if df.empty:
        df = load_sheet("Usuarios")
    if df.empty:
        return None, None
    required = {"Empresa", "Email", "Senha"}
    if not required.issubset(df.columns):
        st.error("Planilha sem as colunas: Empresa, Email, Senha.")
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
    """Salva sessão e gera token persistente na URL para sobreviver ao refresh."""
    client_id = get_client_id(empresa)
    email = st.session_state.get("email_logado", "")
    st.session_state.update(
        logged_in   = True,
        empresa     = empresa,
        email_logado= email,
        telefone    = telefone,
        client_id   = client_id,
    )
    token = secrets.token_urlsafe(32)
    try:
        from sheets import save_session
        save_session(token, empresa, email, telefone, client_id)
        st.query_params["sid"] = token
    except Exception:
        pass  # Se falhar, login ainda funciona — só não persiste no refresh


def logout() -> None:
    """Encerra sessão e invalida token."""
    try:
        sid = st.query_params.get("sid", "")
        if sid:
            from sheets import delete_session
            delete_session(sid)
        st.query_params.clear()
    except Exception:
        pass
    for key in list(st.session_state.keys()):
        st.session_state.pop(key, None)


def require_auth() -> bool:
    return st.session_state.get("logged_in", False)


def current_client_id() -> str:
    """Retorna o client_id da sessão — NUNCA aceitar do front-end."""
    return st.session_state.get("client_id", "")


def current_empresa() -> str:
    return st.session_state.get("empresa", "")


def current_email() -> str:
    return st.session_state.get("email_logado", "")
