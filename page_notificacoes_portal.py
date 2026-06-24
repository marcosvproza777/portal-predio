"""Portal do Cliente — Central de Notificações do Portal."""
import streamlit as st
from auth import current_client_id
from ui import page_header, COLOR_NAVY, COLOR_BLUE, COLOR_BORDER, COLOR_MUTED, COLOR_CARD

_PRIO_COR = {
    "Baixa":   ("#6366F1", "#EEF2FF", "#C7D2FE"),
    "Média":   ("#F59E0B", "#FFFBEB", "#FCD34D"),
    "Media":   ("#F59E0B", "#FFFBEB", "#FCD34D"),
    "Alta":    ("#EF4444", "#FEF2F2", "#FCA5A5"),
    "Crítica": ("#7C3AED", "#F5F3FF", "#C4B5FD"),
    "Critica": ("#7C3AED", "#F5F3FF", "#C4B5FD"),
}

_EVENTO_ICON = {
    "relatorio_publicado":      "📄",
    "relatorio_critico":        "🚨",
    "ativo_atencao":            "🟡",
    "ativo_critico":            "🔴",
    "manutencao_proxima":       "📅",
    "manutencao_vencida":       "🔴",
    "chamado_aberto":           "🔧",
    "chamado_respondido":       "💬",
    "chamado_aguardando_cliente": "⏳",
    "alerta_critico":           "🚨",
    "recomendacao_por_condicao": "💡",
    "documento_publicado":      "📚",
}

_PAGE_ROUTE = {
    "relatorios": "relatorios",
    "ativos":     "ativos",
    "manutencao": "manutencao",
    "chamados":   "chamados",
    "alertas":    "alertas",
    "biblioteca": "biblioteca",
}


def render() -> None:
    if not st.session_state.get("logged_in"):
        st.error("🔒 Faça login para acessar esta página.")
        st.stop()

    page_header(
        "🔔 Minhas Notificações",
        "Avisos, alertas e atualizações do seu portal Pred.IO.",
    )

    client_id = current_client_id()   # SEMPRE da sessão

    from notifications import get_portal_notifications, get_unread_count, mark_all_read

    unread = get_unread_count(client_id)

    # ── Resumo + ações globais ────────────────────────────────────────────────
    col_m, col_btn = st.columns([7, 2])
    with col_m:
        if unread > 0:
            st.markdown(
                f"<p style='font-size:0.9rem;color:{COLOR_NAVY};margin:0;'>"
                f"Você tem <strong style='color:#EF4444;'>{unread} notificação(ões) não lida(s)</strong>.</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<p style='font-size:0.9rem;color:{COLOR_MUTED};margin:0;'>"
                "Nenhuma notificação não lida.</p>",
                unsafe_allow_html=True,
            )
    with col_btn:
        if unread > 0 and st.button(
            "✅ Marcar todas como lidas",
            use_container_width=True,
            key="_np_mark_all",
        ):
            n = mark_all_read(client_id)
            st.toast(f"✅ {n} notificação(ões) marcada(s) como lida(s).", icon="🔔")
            st.rerun()

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:0.75rem 0 1rem;'/>",
        unsafe_allow_html=True,
    )

    # ── Filtros ───────────────────────────────────────────────────────────────
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_leitura = st.radio(
            "Exibir",
            ["Todas", "Não lidas", "Lidas"],
            horizontal=True,
            key="_np_filtro_leitura",
        )
    with col_f2:
        filtro_prio = st.selectbox(
            "Prioridade",
            ["Todas", "Crítica", "Alta", "Média", "Baixa"],
            key="_np_filtro_prio",
        )

    apenas_nao_lidas = (filtro_leitura == "Não lidas")
    notifs = get_portal_notifications(client_id, apenas_nao_lidas=apenas_nao_lidas, limit=60)

    # Filtro pós busca
    if filtro_leitura == "Lidas":
        notifs = [n for n in notifs if n["status"].lower() == "lida"]
    if filtro_prio != "Todas":
        notifs = [n for n in notifs if n["prioridade"].strip() == filtro_prio]

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.8rem;margin:0 0 0.75rem;'>"
        f"{len(notifs)} notificação(ões) exibida(s)</p>",
        unsafe_allow_html=True,
    )

    if not notifs:
        st.info("Nenhuma notificação encontrada com os filtros selecionados.")
        _render_configurar_link()
        return

    for notif in notifs:
        _render_notif_card(notif, client_id)

    _render_configurar_link()


def _render_notif_card(notif: dict, client_id: str) -> None:
    from notifications import mark_as_read

    nid       = notif["id"]
    evento    = notif["tipo_evento"]
    titulo    = notif["titulo"]
    mensagem  = notif["mensagem"]
    prio      = notif["prioridade"]
    status    = notif["status"].lower()
    link_page = notif["link_page"]
    link_id   = notif["link_id"]
    criado_em = notif["created_at"][:16] if notif["created_at"] else ""
    lida_em   = notif["lida_em"]

    icon   = _EVENTO_ICON.get(evento, "🔔")
    is_new = status not in ("lida", "read")

    tc, bg, bord = _PRIO_COR.get(prio, ("#64748B", "#F8FAFC", "#CBD5E1"))

    left_color = tc if is_new else "#CBD5E1"
    bg_card    = bg if is_new else COLOR_CARD
    alpha_text = f"color:{COLOR_NAVY};" if is_new else f"color:{COLOR_MUTED};"

    col_card, col_btn = st.columns([10, 1.5])

    with col_card:
        badge_new = (
            f"<span style='background:#EF4444;color:#fff;-webkit-text-fill-color:#fff;"
            f"font-size:0.65rem;font-weight:700;padding:1px 8px;border-radius:20px;"
            f"margin-left:6px;'>NOVA</span>"
            if is_new else ""
        )
        badge_prio = (
            f"<span style='background:{bg};color:{tc};-webkit-text-fill-color:{tc};"
            f"border:1px solid {bord};font-size:0.65rem;font-weight:700;"
            f"padding:1px 8px;border-radius:20px;margin-left:4px;'>{prio}</span>"
        )

        st.markdown(
            f"<div style='background:{bg_card};border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {left_color};border-radius:10px;"
            f"padding:12px 16px;margin-bottom:6px;'>"
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:flex-start;flex-wrap:wrap;gap:4px;margin-bottom:4px;'>"
            f"<span style='font-weight:700;{alpha_text}font-size:0.9rem;'>"
            f"{icon} {titulo}{badge_new}</span>"
            f"<div>{badge_prio}</div>"
            f"</div>"
            f"<p style='{alpha_text}font-size:0.83rem;margin:0 0 6px;'>{mensagem}</p>"
            f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>📅 {criado_em}"
            + (f"  ·  Lida em: {lida_em[:16]}" if lida_em else "")
            + "</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    with col_btn:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if is_new:
            if st.button(
                "✓",
                key=f"_np_ler_{nid}",
                use_container_width=True,
                help="Marcar como lida",
            ):
                mark_as_read(nid, client_id)
                st.toast("✅ Marcada como lida.", icon="🔔")
                st.rerun()
        else:
            st.markdown(
                f"<p style='color:{COLOR_MUTED};font-size:0.7rem;"
                f"text-align:center;margin:0;'>✓ lida</p>",
                unsafe_allow_html=True,
            )

        # Botão navegar para página relacionada
        route = _PAGE_ROUTE.get(link_page, "")
        if route:
            if st.button(
                "→",
                key=f"_np_nav_{nid}",
                use_container_width=True,
                help=f"Ir para: {link_page}",
            ):
                mark_as_read(nid, client_id)
                if link_id:
                    st.session_state[f"_nav_id_{route}"] = link_id
                st.session_state["portal_page"] = route
                st.rerun()


def _render_configurar_link() -> None:
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:10px;padding:12px 16px;'>"
        f"<p style='margin:0;font-size:0.83rem;color:{COLOR_MUTED};'>"
        f"⚙️ Configure quais eventos geram notificações em "
        f"<strong>Preferências de Notificação</strong>.</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button(
        "⚙️ Configurar notificações",
        key="_np_goto_prefs",
        use_container_width=False,
    ):
        st.session_state["portal_page"] = "preferencias"
        st.rerun()
