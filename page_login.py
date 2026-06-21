"""Tela de login — Pred.IO."""
import streamlit as st
from auth import authenticate, login
from ui import COLOR_NAVY, COLOR_BLUE, COLOR_CYAN


def render(logo_b64: str) -> None:
    # Input styling override para tema escuro do fundo
    st.markdown("""<style>
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
    </style>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.05, 1])
    with col:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

        # Logo
        if logo_b64:
            st.markdown(
                f"<div style='text-align:center;margin-bottom:1.5rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' "
                f"style='width:200px;max-width:90%;border-radius:12px;"
                f"box-shadow:0 8px 32px rgba(0,0,0,0.40);'/></div>",
                unsafe_allow_html=True,
            )

        # Card do formulário
        st.markdown(
            f"""<div style='background:rgba(255,255,255,0.96);
                border-radius:20px;padding:2.5rem 2.5rem 1.5rem;
                box-shadow:0 20px 60px rgba(0,0,0,0.30);
                border:1px solid rgba(255,255,255,0.60);'>
              <h1 style='color:{COLOR_NAVY};text-align:center;margin:0 0 0.3rem;
                  font-size:1.9rem;font-weight:800;letter-spacing:-0.02em;'>
                  Portal do Cliente</h1>
              <p style='color:#64748B;text-align:center;font-size:0.88rem;margin:0 0 2rem;'>
                  Pred.IO — Análises Preditivas para a Indústria</p>
            </div>""",
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # Formulário de login
        with st.form("login_form"):
            st.markdown(
                f"<p style='color:#fff;font-weight:600;font-size:0.85rem;"
                f"margin:0 0 0.3rem;letter-spacing:0.04em;text-shadow:0 1px 4px rgba(0,0,0,0.4);'>"
                f"E-MAIL</p>",
                unsafe_allow_html=True,
            )
            email = st.text_input(
                "E-mail", placeholder="seu@empresa.com.br",
                label_visibility="collapsed",
            )
            st.markdown(
                f"<p style='color:#fff;font-weight:600;font-size:0.85rem;"
                f"margin:0.8rem 0 0.3rem;letter-spacing:0.04em;text-shadow:0 1px 4px rgba(0,0,0,0.4);'>"
                f"SENHA</p>",
                unsafe_allow_html=True,
            )
            password = st.text_input(
                "Senha", type="password", placeholder="••••••••",
                label_visibility="collapsed",
            )
            st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🔐  Entrar no Portal", use_container_width=True)

        if submitted:
            if not email or not password:
                st.warning("Preencha e-mail e senha.")
                return
            with st.spinner("Verificando credenciais…"):
                empresa, telefone = authenticate(email, password)
            if empresa:
                st.session_state["email_logado"] = email.strip().lower()
                login(empresa, telefone)
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos. Verifique e tente novamente.")

        st.markdown(
            "<p style='text-align:center;font-size:0.72rem;color:rgba(255,255,255,0.5);"
            "margin-top:1rem;text-shadow:0 1px 3px rgba(0,0,0,0.3);'>"
            "Acesso restrito · Pred.IO © 2026</p>",
            unsafe_allow_html=True,
        )
