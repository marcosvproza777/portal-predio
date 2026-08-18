"""Autenticação e controle de acesso — Pred.IO."""
import hashlib
import re
import secrets
import streamlit as st
from sheets import load_sheet


def _hash(senha: str) -> str:
    """SHA-256 da senha. Senhas são sempre armazenadas como hash."""
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def _find_user(df, login: str):
    """Busca linha por e-mail ou telefone. Retorna Series ou None."""
    valor = login.strip().lower()
    if "Email" in df.columns:
        m = df[df["Email"].str.strip().str.lower() == valor]
        if not m.empty:
            return m.iloc[0]
    if "Telefone" in df.columns:
        digs = re.sub(r"[^\d]", "", login)
        if digs:
            df2 = df.copy()
            df2["_tel"] = df2["Telefone"].astype(str).str.replace(r"[^\d]", "", regex=True)
            m = df2[df2["_tel"] == digs]
            if not m.empty:
                return m.iloc[0]
    return None


def get_client_id(empresa: str) -> str:
    return empresa.strip().lower()


def checar_email(email: str) -> tuple:
    """Verifica se e-mail existe. Retorna (existe, primeiro_acesso, nome)."""
    from sheets import verificar_email
    existe, primeiro, row = verificar_email(email)
    nome = ""
    if row:
        empresa = str(row.get("Empresa", "")).strip()
        nome = str(row.get("Nome", empresa)).strip() or empresa
    return existe, primeiro, nome


def definir_senha(email: str, nova_senha: str) -> tuple:
    """Define senha no primeiro acesso. Retorna (ok, empresa, telefone, perfil, nome)."""
    from sheets import verificar_email, set_user_senha
    existe, primeiro, row = verificar_email(email)
    if not existe or not primeiro or row is None:
        return False, None, None, None, None
    if not set_user_senha(email.strip().lower(), _hash(nova_senha)):
        return False, None, None, None, None
    empresa  = str(row.get("Empresa", "")).strip()
    telefone = str(row.get("Telefone", "")).strip()
    perfil   = str(row.get("Perfil", "cliente")).strip().lower() or "cliente"
    nome     = str(row.get("Nome", empresa)).strip() or empresa
    return True, empresa, telefone, perfil, nome


def authenticate(login: str, password: str):
    """Valida por e-mail ou telefone + senha (hash SHA-256 ou plaintext legado).
    Retorna (empresa, telefone, perfil, nome) ou (None,)*4.
    """
    df = load_sheet("Clientes")
    if df.empty:
        df = load_sheet("Usuarios")
    if df.empty:
        return None, None, None, None
    if "Empresa" not in df.columns or "Senha" not in df.columns:
        st.error("Planilha sem as colunas obrigatórias: Empresa, Senha.")
        return None, None, None, None

    row = _find_user(df, login)
    if row is None:
        return None, None, None, None

    stored = str(row.get("Senha", "")).strip()
    if not stored:
        return None, None, None, None  # senha não definida → primeiro acesso

    pwd      = password.strip()
    pwd_hash = _hash(pwd)
    if stored == pwd_hash:
        pass
    elif len(stored) != 64 and stored == pwd:
        # Legado plaintext → re-hashear silenciosamente
        try:
            from sheets import set_user_senha
            set_user_senha(login.strip(), pwd_hash)
        except Exception:
            pass
    else:
        return None, None, None, None

    empresa  = str(row.get("Empresa", "")).strip()
    telefone = str(row.get("Telefone", "")).strip()
    perfil   = str(row.get("Perfil", "cliente")).strip().lower() or "cliente"
    nome     = str(row.get("Nome", empresa)).strip() or empresa
    return empresa, telefone, perfil, nome


def login(empresa: str, telefone: str,
          perfil: str = "cliente", nome: str = "") -> None:
    """Salva sessão e gera token persistente na URL para sobreviver ao refresh."""
    client_id = get_client_id(empresa)
    email     = st.session_state.get("email_logado", "")
    nome      = nome or empresa
    st.session_state.update(
        logged_in    = True,
        empresa      = empresa,
        email_logado = email,
        telefone     = telefone,
        client_id    = client_id,
        perfil       = perfil,
        nome         = nome,
    )
    token = secrets.token_urlsafe(32)
    try:
        from sheets import save_session
        save_session(token, empresa, email, telefone, client_id, perfil, nome)
        st.query_params["sid"] = token
        st.query_params.pop("nosess", None)
    except Exception:
        pass


def logout() -> None:
    """Encerra sessão, invalida token e sinaliza para limpar a persistência
    local (localStorage) — impede entrada automática após o logout."""
    try:
        sid = st.query_params.get("sid", "")
        if sid:
            from sheets import delete_session
            delete_session(sid)
        st.query_params.clear()
        st.query_params["loggedout"] = "1"
    except Exception:
        pass
    for key in list(st.session_state.keys()):
        st.session_state.pop(key, None)


def require_auth() -> bool:
    return st.session_state.get("logged_in", False)


def is_staff() -> bool:
    """True se o usuário logado for funcionario ou admin."""
    return current_perfil() in ("funcionario", "admin")


def require_staff() -> None:
    """Para a execução imediatamente se o usuário não for staff."""
    if not is_staff():
        st.error("🔒 Acesso restrito à equipe Pred.IO.")
        st.stop()


def current_client_id() -> str:
    """Retorna o client_id EFETIVO da sessão — NUNCA aceitar do front-end.

    Se um usuário staff (admin/funcionário) estiver no modo "Ver como
    Cliente" (admin_preview_client_id em session_state), retorna o
    client_id do cliente selecionado em vez do client_id real da sessão
    do staff (que normalmente é vazio). Essa chave só pode ser gravada
    por enter_admin_preview(), chamado de dentro de uma tela já protegida
    por require_staff() — nunca vem de query param ou input do cliente.
    O `is_staff()` aqui é defesa extra: mesmo que a chave existisse por
    algum motivo numa sessão de cliente comum, ela é ignorada.
    """
    preview_cid = st.session_state.get("admin_preview_client_id", "")
    if preview_cid and is_staff():
        return preview_cid
    return st.session_state.get("client_id", "")


def current_empresa() -> str:
    if is_admin_preview():
        return st.session_state.get("admin_preview_client_empresa", "")
    return st.session_state.get("empresa", "")


# ── Modo Admin — "Ver como Cliente" ─────────────────────────────────────────

# Chaves de session_state com dado ESPECÍFICO do cliente sendo visualizado
# (nunca válidas para outro cliente) — precisam ser limpas em toda troca de
# contexto (entrar OU sair do preview), senão o próximo cliente visualizado
# herda estado do anterior. BUG CORRIGIDO: só o cache de logo
# (_clogo_loaded/client_logo_b64) era limpo aqui; o histórico e o contexto
# do Assistente Técnico (page_assistente.py) não eram — trocar de "Ver como
# Cliente" de um cliente para outro (ou voltar à Supervisão e entrar de novo)
# fazia o chat mostrar a conversa e os relatórios do cliente visto
# anteriormente, um vazamento de dado entre clientes.
_CHAVES_ESTADO_POR_CLIENTE = (
    "_clogo_loaded", "client_logo_b64",
    # Assistente Técnico (page_assistente.py)
    "chat_history",
    "assistente_current_report_id", "assistente_current_document_id",
    "assistente_chat_id", "assistente_confirmar_apagar_chat",
    "assistente_ativo_contexto", "assistente_ativo_id_contexto",
)


def enter_admin_preview(client_id: str, client_empresa: str) -> bool:
    """Ativa o modo de visualização 'Ver como Cliente' para o staff logado.

    Só pode ser chamado a partir de uma tela da Supervisão (já protegida
    por require_staff()). client_id vem sempre de uma seleção feita ali
    dentro — nunca de input livre ou parâmetro de URL.
    """
    if not is_staff():
        return False
    st.session_state["admin_preview_client_id"]     = client_id.strip().lower()
    st.session_state["admin_preview_client_empresa"] = client_empresa
    st.session_state["admin_preview_admin_email"]    = current_email()
    st.session_state["admin_preview_admin_nome"]     = current_nome()
    # Força recarregar o logo do cliente certo e limpa qualquer estado do
    # Assistente Técnico do cliente visto anteriormente (ver comentário em
    # _CHAVES_ESTADO_POR_CLIENTE) — sem isso, o cliente novo herdaria o chat.
    for k in _CHAVES_ESTADO_POR_CLIENTE:
        st.session_state.pop(k, None)
    st.session_state["portal_page"] = "dashboard"
    return True


def exit_admin_preview() -> None:
    """Sai do modo 'Ver como Cliente', voltando para a Supervisão normal."""
    for k in ("admin_preview_client_id", "admin_preview_client_empresa",
              "admin_preview_admin_email", "admin_preview_admin_nome",
              *_CHAVES_ESTADO_POR_CLIENTE):
        st.session_state.pop(k, None)


def is_admin_preview() -> bool:
    """True se um staff estiver visualizando o portal como um cliente."""
    return is_staff() and bool(st.session_state.get("admin_preview_client_id"))


def current_email() -> str:
    return st.session_state.get("email_logado", "")


def current_perfil() -> str:
    return st.session_state.get("perfil", "cliente")


def current_nome() -> str:
    nome = st.session_state.get("nome", "")
    return nome or current_empresa()
