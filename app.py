"""Portal do Cliente — Pred.IO  |  Entry point."""
import streamlit as st
from ui import inject_global_css, inject_login_bg, render_sidebar, load_image_b64


def main() -> None:
    st.set_page_config(
        page_title="Portal do Cliente — Pred.IO",
        page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_css()

    logo_b64 = load_image_b64("logo.jpg")
    bg_b64   = load_image_b64("bg.jpg")

    # ── Restaura sessão a partir do token na URL (sobrevive ao refresh) ───────
    if not st.session_state.get("logged_in"):
        sid = st.query_params.get("sid", "")
        if sid:
            from sheets import get_session
            session = get_session(sid)
            if session:
                st.session_state.update(
                    logged_in   = True,
                    empresa     = session["empresa"],
                    email_logado= session["email"],
                    telefone    = session["telefone"],
                    client_id   = session["client_id"],
                )
                st.rerun()

    # ── Não autenticado → tela de login ───────────────────────────────────────
    if not st.session_state.get("logged_in"):
        inject_login_bg(bg_b64)
        import page_login
        page_login.render(logo_b64)
        return

    # ── Autenticado → portal com abas ─────────────────────────────────────────
    empresa  = st.session_state.get("empresa", "")
    telefone = st.session_state.get("telefone", "")
    render_sidebar(logo_b64, empresa, telefone)

    # Logo no topo do conteúdo principal
    if logo_b64:
        col_logo, col_info = st.columns([1, 9])
        with col_logo:
            st.markdown(
                f"<div style='padding:0.4rem 0;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' "
                f"style='width:72px;border-radius:8px;box-shadow:0 2px 8px rgba(15,31,61,0.12);'/>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_info:
            st.markdown(
                f"<p style='color:#0F1F3D;font-weight:700;font-size:0.95rem;margin:0.6rem 0 0;'>"
                f"Portal do Cliente · Pred.IO</p>"
                f"<p style='color:#64748B;font-size:0.78rem;margin:0;'>{empresa}</p>",
                unsafe_allow_html=True,
            )
        st.markdown(
            "<hr style='border-color:#E2E8F0;margin:0.6rem 0 0;'/>",
            unsafe_allow_html=True,
        )

    # Painel de Condição de Ativos é a primeira aba (padrão ao entrar)
    tab_farois, tab_rel, tab_assist, tab_cham = st.tabs([
        "🏭  Painel de Ativos",
        "📁  Meus Relatórios",
        "🤖  Assistente Técnico",
        "🔧  Chamados Técnicos",
    ])

    with tab_farois:
        import page_farois
        page_farois.render(logo_b64)

    with tab_rel:
        import page_relatorios
        page_relatorios.render()

    with tab_assist:
        import page_assistente
        page_assistente.render()

    with tab_cham:
        import page_chamados
        page_chamados.render()


if __name__ == "__main__":
    main()
