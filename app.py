"""Portal do Cliente — Pred.IO  |  Entry point."""
import streamlit as st
from ui import (inject_global_css, inject_login_bg, render_client_topnav,
                render_supervisao_sidebar, load_image_b64,
                inject_floating_assistant)
from auth import is_staff, current_nome, current_perfil
from pwa import inject_pwa


def main() -> None:
    st.set_page_config(
        page_title="Portal de Confiabilidade Pred.IO",
        page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_css()
    inject_pwa()

    logo_b64 = load_image_b64("logo.jpg")
    bg_b64   = load_image_b64("bg.jpg")

    # Lê o token de sessão da URL (disponível durante toda a sessão)
    _sid = st.query_params.get("sid", "")

    # ── Restaura sessão a partir do token na URL (sobrevive ao refresh) ───────
    if not st.session_state.get("logged_in"):
        sid = _sid
        if sid:
            from sheets import get_session
            session = get_session(sid)
            if session:
                st.session_state.update(
                    logged_in    = True,
                    empresa      = session["empresa"],
                    email_logado = session["email"],
                    telefone     = session["telefone"],
                    client_id    = session["client_id"],
                    perfil       = session.get("perfil", "cliente"),
                    nome         = session.get("nome", session["empresa"]),
                )
                st.rerun()

    # ── Não autenticado → tela de login ───────────────────────────────────────
    if not st.session_state.get("logged_in"):
        inject_login_bg(bg_b64)
        import page_login
        page_login.render(logo_b64)
        return

    # ── Autenticado → bifurcar por perfil ────────────────────────────────────
    empresa  = st.session_state.get("empresa", "")
    telefone = st.session_state.get("telefone", "")
    nome     = current_nome()
    perfil   = current_perfil()

    # ── SUPERVISÃO PRED.IO (funcionario / admin) ──────────────────────────────
    if is_staff():
        render_supervisao_sidebar(logo_b64, nome, perfil)
        _render_supervisao()
        return

    # ── PORTAL DO CLIENTE ─────────────────────────────────────────────────────
    render_client_topnav(logo_b64, empresa, telefone)

    # Navegação via link do assistente flutuante (?portal_page=X na URL)
    if "portal_page" not in st.session_state:
        _nav = st.query_params.get("portal_page", "")
        if _nav:
            st.session_state["portal_page"] = _nav

    portal_page = st.session_state.get("portal_page", "farois")

    # Assistente flutuante — visível em todas as páginas do portal do cliente
    inject_floating_assistant(_sid)

    if portal_page == "farois":
        import page_farois
        page_farois.render(logo_b64)
    elif portal_page == "ativos":
        import page_ativos
        page_ativos.render()
    elif portal_page == "manutencao":
        import page_manutencao
        page_manutencao.render()
    elif portal_page == "relatorios":
        import page_relatorios
        page_relatorios.render()
    elif portal_page == "assistente":
        import page_assistente
        page_assistente.render()
    elif portal_page == "chamados":
        import page_chamados
        page_chamados.render()
    elif portal_page == "alertas":
        import page_alertas
        page_alertas.render()
    else:
        import page_farois
        page_farois.render(logo_b64)



def _render_supervisao() -> None:
    """Roteador interno da Supervisão Pred.IO."""
    from ui import render_sv_topnav
    render_sv_topnav()

    sv_view = st.session_state.get("sv_view", "dashboard")

    if sv_view == "dashboard":
        import page_sv_dashboard
        page_sv_dashboard.render()
    elif sv_view in ("chamados",):
        import page_sv_chamados
        page_sv_chamados.render()
    elif sv_view == "chamado_detalhe":
        import page_sv_chamado_detalhe
        page_sv_chamado_detalhe.render()
    elif sv_view in ("clientes", "cliente_historico", "cliente_novo"):
        import page_sv_clientes
        page_sv_clientes.render()
    elif sv_view in ("ativos_sv", "ativo_detalhe", "ativo_novo", "componente_novo"):
        import page_sv_ativos
        page_sv_ativos.render()
    elif sv_view == "manutencao_sv":
        import page_sv_manutencao
        page_sv_manutencao.render()
    elif sv_view == "alertas_sv":
        import page_sv_alertas
        page_sv_alertas.render()
    else:
        import page_sv_dashboard
        page_sv_dashboard.render()


if __name__ == "__main__":
    main()
