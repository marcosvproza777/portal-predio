"""Portal do Cliente — Pred.IO  |  Entry point & router."""
import streamlit as st

from ui import inject_global_css, inject_login_bg, render_sidebar_nav, load_image_b64


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

    # ── Roteamento ────────────────────────────────────────────────────────────
    page = st.session_state.get("page", "login")

    if not st.session_state.get("logged_in"):
        # Qualquer página redireciona para login se não autenticado
        inject_login_bg(bg_b64)
        import page_login
        page_login.render(logo_b64)
        return

    # Usuário autenticado — renderiza nav + página
    empresa  = st.session_state.get("empresa", "")
    telefone = st.session_state.get("telefone", "")
    render_sidebar_nav(logo_b64, empresa, telefone, page)

    if page == "dashboard":
        import page_dashboard
        page_dashboard.render(logo_b64)

    elif page == "farois":
        import page_farois
        page_farois.render(logo_b64)

    elif page == "relatorios":
        import page_relatorios
        page_relatorios.render()

    elif page == "assistente":
        import page_assistente
        page_assistente.render()

    elif page == "chamados":
        import page_chamados
        page_chamados.render()

    else:
        st.session_state["page"] = "dashboard"
        st.rerun()


if __name__ == "__main__":
    main()
