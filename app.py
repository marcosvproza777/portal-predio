"""Portal do Cliente — Pred.IO  |  Entry point."""
import version  # grava static/version.txt uma vez por inicialização do servidor
import streamlit as st
from ui import (inject_global_css, inject_login_bg, render_client_topnav,
                render_supervisao_sidebar, render_admin_preview_banner, load_image_b64,
                inject_floating_assistant, remove_floating_assistant)
from auth import (is_staff, current_nome, current_perfil,
                  is_admin_preview, current_client_id, current_empresa)
from pwa import inject_pwa, inject_mobile_css, inject_bottom_nav, remove_bottom_nav


def main() -> None:
    try:
        from PIL import Image as _PILImage
        _favicon = _PILImage.open("logo.jpg")
    except Exception:
        _favicon = "⚙️"
    st.set_page_config(
        page_title="Portal de Confiabilidade Pred.IO",
        page_icon=_favicon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_css()
    inject_mobile_css()   # CSS responsivo global (mobile-first)
    inject_pwa()          # manifest + ícones + botão "Baixe o app"

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
            else:
                # Token salvo no navegador é inválido/expirado/revogado —
                # limpa o localStorage e não tenta de novo nesta navegação.
                from session_persist import inject_session_clear
                inject_session_clear()
                st.query_params["nosess"] = "1"
        elif not st.query_params.get("nosess"):
            # Sem ?sid= na URL e ainda não verificamos o navegador nesta
            # navegação — checa localStorage antes de mostrar login, para
            # não pedir login de novo em quem já tem sessão válida no
            # mesmo dispositivo (só fecha e reabre o navegador).
            from session_persist import inject_session_restore_check, render_loading_screen
            render_loading_screen()
            inject_session_restore_check()
            st.stop()

    # ── Não autenticado → tela de login ───────────────────────────────────────
    if not st.session_state.get("logged_in"):
        remove_floating_assistant()
        remove_bottom_nav()
        st.session_state.pop("_clogo_loaded", None)
        st.session_state.pop("client_logo_b64", None)
        if st.query_params.get("loggedout"):
            from session_persist import inject_session_clear
            inject_session_clear()
            st.query_params.pop("loggedout", None)
        inject_login_bg(bg_b64)
        import page_login
        page_login.render(logo_b64)
        return

    # ── Autenticado → bifurcar por perfil ────────────────────────────────────
    empresa  = st.session_state.get("empresa", "")
    telefone = st.session_state.get("telefone", "")

    # Mantém o localStorage sincronizado com o token de sessão válido atual
    # — sobrevive a fechar/reabrir o navegador no mesmo dispositivo.
    from session_persist import inject_session_save
    inject_session_save(_sid)
    nome     = current_nome()
    perfil   = current_perfil()

    # ── SUPERVISÃO PRED.IO (funcionario / admin) ──────────────────────────────
    if is_staff() and not is_admin_preview():
        render_supervisao_sidebar(logo_b64, nome, perfil)
        _render_supervisao()
        return

    # ── PORTAL DO CLIENTE ─────────────────────────────────────────────────────
    # (staff em modo "Ver como Cliente" cai aqui também — current_client_id()/
    # current_empresa() já retornam os dados do cliente selecionado, não os
    # da própria sessão do staff — ver auth.py)
    if is_admin_preview():
        render_admin_preview_banner()

    # Carrega logo do cliente uma vez por sessão (ou por preview — ver
    # enter_admin_preview, que limpa esse cache ao trocar de cliente)
    if not st.session_state.get("_clogo_loaded"):
        try:
            from sheets import get_client_logo as _gcl
            st.session_state["client_logo_b64"] = _gcl(current_client_id())
        except Exception:
            st.session_state["client_logo_b64"] = ""
        st.session_state["_clogo_loaded"] = True

    render_client_topnav(logo_b64, current_empresa(), telefone,
                         client_logo_b64=st.session_state.get("client_logo_b64", ""))

    # Navegação via link do assistente flutuante (?portal_page=X na URL)
    # Sanitiza para aceitar apenas páginas do cliente — impede injeção de rotas
    from security import sanitize_portal_page
    _nav = sanitize_portal_page(st.query_params.get("portal_page", ""))
    if _nav:
        st.session_state["portal_page"] = _nav

    portal_page = st.session_state.get("portal_page", "dashboard")

    # Menu inferior mobile (escondido em desktop via CSS media query)
    inject_bottom_nav(portal_page)

    # Assistente flutuante — visível em todas as páginas do portal do cliente
    # client_id vem da sessão do servidor (ou do preview, se staff) — NUNCA do front-end
    inject_floating_assistant(_sid, current_client_id())

    # Botões de navegação suave (ocultos via CSS, acionados pelo JS do assistente flutuante)
    # Quando o JS clica neles, Streamlit dispara rerun via WebSocket (sem reload de página)
    for _pnk in ["dashboard","farois","ativos","manutencao","relatorios","chamados","alertas","biblioteca","assistente","preferencias","notificacoes"]:
        if st.button(f"▸{_pnk}", key=f"__pnav_{_pnk}__"):
            st.session_state["portal_page"] = _pnk
            st.rerun()

    if portal_page == "dashboard":
        import page_dashboard
        page_dashboard.render()
    elif portal_page == "farois":
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
    elif portal_page == "biblioteca":
        import page_biblioteca
        page_biblioteca.render()
    elif portal_page == "preferencias":
        import page_preferencias_notificacao
        page_preferencias_notificacao.render()
    elif portal_page == "notificacoes":
        import page_notificacoes_portal
        page_notificacoes_portal.render()
    else:
        import page_farois
        page_farois.render(logo_b64)



def _render_supervisao() -> None:
    """Roteador interno da Supervisão Pred.IO."""
    from ui import render_sv_topnav, SV_NAV_ITEMS
    # A Supervisão não tem bottom nav próprio (usa o pill nav horizontal do
    # topnav) — mas o bottom nav do Portal do Cliente é injetado direto no
    # DOM do navegador (fora do ciclo de rerender do Streamlit) e só é
    # removido no logout. Se o staff usou "Ver como Cliente" e voltou pra
    # Supervisão, o bottom nav do cliente continua na tela: os ícones
    # buscam botões ocultos "▸ativos"/"▸manutencao" (esquema do cliente),
    # que não existem aqui (aqui é "▸sv_ativos_sv" etc.) — cliques não
    # fazem nada. Remover sempre ao entrar na Supervisão evita esse resíduo.
    remove_bottom_nav()
    render_sv_topnav()

    # Botões ocultos via CSS (aria-label^="▸") — acionados pelo pill nav do topnav
    for _snk, _sni, _snl in SV_NAV_ITEMS:
        if st.button(f"▸sv_{_snk}", key=f"__svnav_{_snk}__"):
            st.session_state["sv_view"] = _snk
            st.session_state.pop("sv_chamado_id", None)
            st.rerun()

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
    elif sv_view == "notificacoes_sv":
        import page_sv_notificacoes
        page_sv_notificacoes.render()
    elif sv_view == "biblioteca_sv":
        import page_sv_biblioteca
        page_sv_biblioteca.render()
    elif sv_view in ("relatorios_sv", "relatorio_novo", "relatorio_editar", "relatorios_cliente_detalhe"):
        import page_sv_relatorios
        page_sv_relatorios.render()
    elif sv_view == "assistente_sv":
        import page_sv_assistente
        page_sv_assistente.render()
    elif sv_view == "homologacao":
        import page_sv_homologacao
        page_sv_homologacao.render()
    elif sv_view == "relatorio_executivo":
        import page_sv_relatorio_executivo
        page_sv_relatorio_executivo.render()
    else:
        import page_sv_dashboard
        page_sv_dashboard.render()


if __name__ == "__main__":
    main()
