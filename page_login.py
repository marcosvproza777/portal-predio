"""Tela de login."""
import streamlit as st
from auth import authenticate, login
from ui import COLOR_NAVY, COLOR_BLUE, COLOR_CYAN, COLOR_BORDER


def render(logo_b64: str) -> None:
    st.markdown(f"""<style>
    .stTextInput input {{
        background: #fff !important; border: 2px solid {COLOR_BORDER} !important;
        border-radius: 8px !important; color: #1e293b !important; font-size:1rem !important;
    }}
    .stTextInput input:focus {{ border-color: {COLOR_BLUE} !important; }}
    </style>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)

        logo_html = (
            f"<div style='text-align:center;margin-bottom:1.4rem;'>"
            f"<img src='data:image/jpeg;base64,{logo_b64}' style='width:210px;max-width:100%;'/>"
            f"</div>"
        ) if logo_b64 else ""

        st.markdown(
            f"""<div style='background:rgba(255,255,255,0.97);border:1px solid {COLOR_BORDER};
                border-radius:18px;padding:2.5rem 2.5rem 1.5rem;
                box-shadow:0 8px 40px rgba(27,42,107,0.18);'>
              {logo_html}
              <h1 style='color:{COLOR_NAVY};text-align:center;margin:0 0 0.2rem;
                  font-size:1.8rem;font-weight:800;'>Portal do Cliente</h1>
              <p style='color:#475569;text-align:center;font-size:0.9rem;margin:0 0 1.8rem;'>
                  Pred.IO — Análises Preditivas para a Indústria</p>
            </div>""",
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            st.markdown(
                f"<p style='color:{COLOR_NAVY};font-weight:700;font-size:0.95rem;"
                f"margin:0.8rem 0 0.2rem;'>E-mail</p>",
                unsafe_allow_html=True,
            )
            email = st.text_input("E-mail", placeholder="seu@email.com",
                                  label_visibility="collapsed")
            st.markdown(
                f"<p style='color:{COLOR_NAVY};font-weight:700;font-size:0.95rem;"
                f"margin:0.6rem 0 0.2rem;'>Senha</p>",
                unsafe_allow_html=True,
            )
            password = st.text_input("Senha", type="password", placeholder="••••••••",
                                     label_visibility="collapsed")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🔐  Entrar", use_container_width=True)

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
                st.error("E-mail ou senha incorretos.")
