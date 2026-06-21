"""Tela de login — Pred.IO (fluxo: e-mail → primeiro acesso ou senha)."""
import html as _html
import streamlit as st
from auth import authenticate, login, checar_email, definir_senha
from ui import COLOR_NAVY

_CSS = """<style>
.stTextInput input {
    background: rgba(255,255,255,0.95) !important;
    border: 2px solid rgba(255,255,255,0.3) !important;
    border-radius: 10px !important;
    color: #0F1F3D !important;
    font-size: 1rem !important;
    padding: 0.6rem 1rem !important;
}
.stTextInput input:focus {
    border-color: #38BDF8 !important;
    box-shadow: 0 0 0 3px rgba(56,189,248,0.20) !important;
}
[data-testid="stBaseButton-secondaryFormSubmit"] {
    background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
    color: #fff !important; -webkit-text-fill-color: #fff !important;
    font-weight: 700 !important; font-size: 1rem !important;
    border-radius: 10px !important; border: none !important;
    box-shadow: 0 4px 20px rgba(37,99,235,0.50) !important;
    padding: 0.65rem !important;
}
[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background: linear-gradient(135deg, #1D4ED8, #1E40AF) !important;
    box-shadow: 0 6px 24px rgba(37,99,235,0.60) !important;
    transform: translateY(-1px);
}
[data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    border: none !important;
    color: rgba(255,255,255,0.7) !important;
    font-size: 0.82rem !important;
    padding: 0.2rem 0 !important;
    box-shadow: none !important;
}
[data-testid="stBaseButton-secondary"]:hover {
    color: #fff !important;
    background: transparent !important;
    text-decoration: underline !important;
}
</style>"""


def render(logo_b64: str) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.05, 1])
    with col:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

        if logo_b64:
            st.markdown(
                f"<div style='text-align:center;margin-bottom:1.5rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' "
                f"style='width:200px;max-width:90%;border-radius:12px;"
                f"box-shadow:0 8px 32px rgba(0,0,0,0.40);'/></div>",
                unsafe_allow_html=True,
            )

        step = st.session_state.get("lx_step", "email")

        if step == "email":
            _step_email()
        elif step == "primeiro_acesso":
            _step_primeiro_acesso()
        else:
            _step_senha()

        st.markdown(
            "<p style='text-align:center;font-size:0.72rem;"
            "color:rgba(255,255,255,0.5);margin-top:1rem;"
            "text-shadow:0 1px 3px rgba(0,0,0,0.3);'>"
            "Acesso restrito · Pred.IO © 2026</p>",
            unsafe_allow_html=True,
        )


# ── helpers ───────────────────────────────────────────────────────────────────

def _card(title: str, subtitle: str) -> None:
    st.markdown(
        f"<div style='background:rgba(255,255,255,0.96);border-radius:20px;"
        f"padding:2.5rem 2.5rem 1.5rem;"
        f"box-shadow:0 20px 60px rgba(0,0,0,0.30);"
        f"border:1px solid rgba(255,255,255,0.60);'>"
        f"<h1 style='color:{COLOR_NAVY};text-align:center;margin:0 0 0.3rem;"
        f"font-size:1.9rem;font-weight:800;letter-spacing:-0.02em;'>{title}</h1>"
        f"<p style='color:#64748B;text-align:center;font-size:0.88rem;"
        f"margin:0 0 2rem;'>{subtitle}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


def _lbl(text: str, top: str = "0") -> None:
    st.markdown(
        f"<p style='color:#fff;font-weight:600;font-size:0.85rem;"
        f"margin:{top} 0 0.3rem;letter-spacing:0.04em;"
        f"text-shadow:0 1px 4px rgba(0,0,0,0.4);'>{text}</p>",
        unsafe_allow_html=True,
    )


def _voltar_email() -> None:
    if st.button("← Trocar e-mail", key="btn_voltar"):
        for k in ("lx_step", "lx_email"):
            st.session_state.pop(k, None)
        st.rerun()


def _fazer_login(empresa, telefone, perfil, nome) -> None:
    email = st.session_state.get("lx_email", "")
    st.session_state["email_logado"] = email
    login(empresa, telefone, perfil, nome)
    for k in ("lx_step", "lx_email"):
        st.session_state.pop(k, None)
    st.rerun()


# ── etapas ────────────────────────────────────────────────────────────────────

def _step_email() -> None:
    _card("Portal do Cliente", "Pred.IO — Análises Preditivas para a Indústria")

    with st.form("form_lx_email"):
        _lbl("E-MAIL")
        email = st.text_input("E-mail", placeholder="seu@empresa.com.br",
                              label_visibility="collapsed")
        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Continuar  →", use_container_width=True)

    if submitted:
        email = email.strip().lower()
        if not email:
            st.warning("Digite seu e-mail.")
            return
        with st.spinner("Verificando…"):
            existe, primeiro_acesso = checar_email(email)
        if not existe:
            st.error("E-mail não encontrado. Verifique com a equipe Pred.IO.")
            return
        st.session_state["lx_email"] = email
        st.session_state["lx_step"]  = "primeiro_acesso" if primeiro_acesso else "senha"
        st.rerun()


def _step_primeiro_acesso() -> None:
    email = st.session_state.get("lx_email", "")
    _voltar_email()

    _card(
        "Primeiro Acesso",
        f"Crie sua senha para <b style='color:{COLOR_NAVY};'>"
        f"{_html.escape(email)}</b>",
    )

    with st.form("form_lx_pa"):
        _lbl("CRIE SUA SENHA")
        senha = st.text_input("Nova senha", type="password",
                              placeholder="Mínimo 6 caracteres",
                              label_visibility="collapsed")
        _lbl("CONFIRME A SENHA", top="0.8rem")
        confirma = st.text_input("Confirmar senha", type="password",
                                 placeholder="Repita a senha escolhida",
                                 label_visibility="collapsed")
        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🔐  Criar senha e entrar",
                                         use_container_width=True)

    if submitted:
        if not senha:
            st.warning("Digite uma senha.")
            return
        if len(senha) < 6:
            st.error("A senha deve ter pelo menos 6 caracteres.")
            return
        if senha != confirma:
            st.error("As senhas não conferem. Tente novamente.")
            return
        with st.spinner("Salvando sua senha…"):
            ok, empresa, telefone, perfil, nome = definir_senha(email, senha)
        if not ok:
            st.error("Não foi possível salvar a senha. Tente novamente.")
            return
        _fazer_login(empresa, telefone, perfil, nome)


def _step_senha() -> None:
    email = st.session_state.get("lx_email", "")
    _voltar_email()

    _card(
        "Bem-vindo de volta",
        f"<span style='color:#64748B;'>{_html.escape(email)}</span>",
    )

    with st.form("form_lx_senha"):
        _lbl("SENHA")
        password = st.text_input("Senha", type="password", placeholder="••••••••",
                                 label_visibility="collapsed")
        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🔐  Entrar no Portal",
                                         use_container_width=True)

    if submitted:
        if not password:
            st.warning("Digite sua senha.")
            return
        with st.spinner("Verificando credenciais…"):
            empresa, telefone, perfil, nome = authenticate(email, password)
        if empresa:
            _fazer_login(empresa, telefone, perfil, nome)
        else:
            st.error("Senha incorreta. Tente novamente.")
