"""Componentes de UI compartilhados — cores, CSS, logo, navegação."""
import base64
import streamlit as st

# ── Paleta ────────────────────────────────────────────────────────────────────
COLOR_NAVY    = "#0F1F3D"
COLOR_BLUE    = "#2563EB"
COLOR_CYAN    = "#38BDF8"
COLOR_BG      = "#F1F5F9"
COLOR_CARD    = "#FFFFFF"
COLOR_BORDER  = "#E2E8F0"
COLOR_MUTED   = "#64748B"

TIPOS_LAUDOS = [
    ("ordem de servico",    "Ordem de Serviço"),
    ("analise de vibracao", "Análise de Vibração"),
    ("termografia",         "Termografia"),
    ("analise de oleo",     "Análise de Óleo"),
    ("alinhamento a laser", "Alinhamento a Laser"),
]

PRIORIDADES = ["Baixa", "Média", "Alta", "Crítica"]


def load_image_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""


def inject_global_css() -> None:
    st.markdown(f"""<style>
    /* ── Base ── */
    .stApp {{ background-color: {COLOR_BG}; }}
    #MainMenu, footer {{ visibility: hidden; }}
    /* Esconde barra de ferramentas sem remover do DOM (preserva toggle da sidebar) */
    [data-testid="stToolbar"] {{ visibility: hidden !important; }}
    /* Botoes de navegacao suave do assistente (aria-label comeca com ▸) */
    button[aria-label^="▸"],
    [data-testid="stButton"]:has(button[aria-label^="▸"]) {{
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }}
    header[data-testid="stHeader"] {{ background: transparent !important; }}
    /* Garante que o botão de abrir/fechar sidebar seja sempre visível
       (visibility:hidden no pai pode ser sobrescrito pelo filho; display:none não) */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarExpandButton"],
    [data-testid="collapsedControl"] {{
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        background: {COLOR_NAVY} !important;
        border-radius: 50% !important;
        color: #fff !important;
        -webkit-text-fill-color: #fff !important;
    }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(160deg, #0A1628 0%, #1B2A6B 100%) !important;
        border-right: none !important;
    }}
    [data-testid="stSidebar"] * {{ color: #E2E8F0 !important; }}
    [data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.12) !important; }}

    /* ── Abas (tabs) ── */
    [data-testid="stTabs"] > div:first-child {{
        background: {COLOR_CARD};
        border-bottom: 2px solid {COLOR_BORDER};
        padding: 0 0.5rem;
        border-radius: 10px 10px 0 0;
    }}
    button[data-baseweb="tab"] {{
        font-size: 0.875rem !important;
        font-weight: 600 !important;
        color: {COLOR_MUTED} !important;
        padding: 0.875rem 1.4rem !important;
        border-radius: 0 !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        margin-bottom: -2px !important;
    }}
    button[data-baseweb="tab"]:hover {{
        color: {COLOR_NAVY} !important;
        background: {COLOR_BG} !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"],
    button[data-baseweb="tab"][aria-selected="true"] p {{
        color: {COLOR_NAVY} !important;
        font-weight: 700 !important;
        border-bottom-color: {COLOR_NAVY} !important;
        background: transparent !important;
    }}

    /* ── Botão primário (Entrar, Enviar) ── */
    [data-testid="stBaseButton-secondaryFormSubmit"],
    [data-testid="stBaseButton-primary"] {{
        background: linear-gradient(135deg, {COLOR_BLUE} 0%, #1D4ED8 100%) !important;
        color: #fff !important; -webkit-text-fill-color: #fff !important;
        font-weight: 700 !important; border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 14px rgba(37,99,235,0.35) !important;
    }}
    [data-testid="stBaseButton-secondaryFormSubmit"]:hover,
    [data-testid="stBaseButton-primary"]:hover {{
        background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important;
        box-shadow: 0 6px 20px rgba(37,99,235,0.45) !important;
    }}

    /* ── Botão secundário (Sair e ações no portal) ── */
    [data-testid="stBaseButton-secondary"] {{
        background: rgba(15,31,61,0.06) !important;
        color: #0F1F3D !important; -webkit-text-fill-color: #0F1F3D !important;
        border: 1px solid rgba(15,31,61,0.20) !important;
        border-radius: 8px !important; font-weight: 600 !important;
    }}
    [data-testid="stBaseButton-secondary"]:hover {{
        background: rgba(239,68,68,0.08) !important;
        border-color: rgba(239,68,68,0.45) !important;
        color: #DC2626 !important; -webkit-text-fill-color: #DC2626 !important;
    }}
    /* Sidebar — botões de navegação (secundário = inativo) */
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {{
        background: rgba(255,255,255,0.06) !important;
        color: rgba(226,232,240,0.80) !important;
        -webkit-text-fill-color: rgba(226,232,240,0.80) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        transition: background 0.15s !important;
    }}
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{
        background: rgba(255,255,255,0.13) !important;
        color: #E2E8F0 !important;
        -webkit-text-fill-color: #E2E8F0 !important;
    }}
    /* Sidebar — botão nav ativo (primary) */
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {{
        background: rgba(37,99,235,0.38) !important;
        border: 1px solid rgba(56,189,248,0.55) !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-weight: 700 !important;
        text-align: left !important;
        justify-content: flex-start !important;
    }}
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {{
        background: rgba(37,99,235,0.50) !important;
    }}

    /* ── Metric cards ── */
    [data-testid="stMetric"] {{
        background: {COLOR_CARD};
        border: 1px solid {COLOR_BORDER};
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        box-shadow: 0 1px 4px rgba(15,31,61,0.06);
    }}
    [data-testid="stMetricLabel"] {{
        color: {COLOR_MUTED} !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    [data-testid="stMetricValue"] {{
        color: {COLOR_NAVY} !important;
        font-size: 2.1rem !important;
        font-weight: 800 !important;
    }}

    /* ── Inputs ── */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb] {{
        border-radius: 8px !important;
    }}

    h1, h2, h3 {{ color: {COLOR_NAVY} !important; }}
    hr {{ border-color: {COLOR_BORDER} !important; opacity: 1 !important; }}

    /* ── Expander ── */
    [data-testid="stExpander"] {{
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 10px !important;
        background: {COLOR_CARD} !important;
    }}

    /* ── Portal cliente — topnav horizontal ─────────────────────────────── */
    /* Usa .portal-nav-marker como âncora CSS para targetar apenas o bloco
       de colunas do topnav, sem afetar outros st.columns na página.          */
    [data-testid="stMarkdown"]:has(.portal-nav-marker)
        + [data-testid="stHorizontalBlock"] {{
        gap: 0 !important;
        padding: 0.05rem 0 0;
        align-items: stretch !important;
    }}
    /* Botões inativos do topnav */
    [data-testid="stMarkdown"]:has(.portal-nav-marker)
        + [data-testid="stHorizontalBlock"] [data-testid="stBaseButton-secondary"] {{
        background: transparent !important;
        border: none !important;
        border-bottom: 2.5px solid transparent !important;
        border-radius: 0 !important;
        color: {COLOR_MUTED} !important;
        -webkit-text-fill-color: {COLOR_MUTED} !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        padding: 0.52rem 0.2rem 0.38rem !important;
        box-shadow: none !important;
        letter-spacing: 0.01em !important;
        height: 100% !important;
        transition: color 0.12s, border-color 0.12s !important;
    }}
    [data-testid="stMarkdown"]:has(.portal-nav-marker)
        + [data-testid="stHorizontalBlock"] [data-testid="stBaseButton-secondary"]:hover {{
        color: {COLOR_NAVY} !important;
        -webkit-text-fill-color: {COLOR_NAVY} !important;
        background: rgba(15,31,61,0.03) !important;
        border-bottom-color: {COLOR_BORDER} !important;
        box-shadow: none !important;
    }}
    /* Botão Sair — último item: hover vermelho */
    [data-testid="stMarkdown"]:has(.portal-nav-marker)
        + [data-testid="stHorizontalBlock"]
        [data-testid="column"]:last-child [data-testid="stBaseButton-secondary"]:hover {{
        color: #DC2626 !important;
        -webkit-text-fill-color: #DC2626 !important;
        background: rgba(239,68,68,0.05) !important;
        border-bottom-color: transparent !important;
    }}
    </style>""", unsafe_allow_html=True)


def inject_login_bg(bg_b64: str) -> None:
    if not bg_b64:
        return
    st.markdown(f"""<style>
    .stApp {{
        background-image: url('data:image/jpeg;base64,{bg_b64}') !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }}
    .stApp::before {{
        content: '';
        position: fixed; inset: 0;
        background: rgba(10,22,40,0.60);
        pointer-events: none; z-index: 0;
    }}
    section.main > div {{ position: relative; z-index: 1; }}
    </style>""", unsafe_allow_html=True)


def render_sidebar(logo_b64: str, empresa: str, telefone: str) -> None:
    from auth import logout
    portal_page = st.session_state.get("portal_page", "farois")

    with st.sidebar:
        # ── Logo + título ─────────────────────────────────────────────────────
        if logo_b64:
            st.markdown(
                f"<div style='text-align:center;padding:1.5rem 0 0.75rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' "
                f"style='width:110px;border-radius:10px;"
                f"box-shadow:0 4px 16px rgba(0,0,0,0.40);'/></div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div style='text-align:center;padding:0 0.5rem 0.5rem;'>"
            "<p style='font-size:0.82rem;font-weight:700;color:#E2E8F0;margin:0;line-height:1.3;'>"
            "Portal de Confiabilidade</p>"
            "<p style='font-size:1.1rem;font-weight:900;color:#38BDF8;margin:0;'>"
            "Pred.IO</p>"
            "<p style='font-size:0.6rem;font-weight:700;letter-spacing:0.16em;"
            "text-transform:uppercase;color:rgba(255,255,255,0.32);margin:5px 0 0;'>"
            "Área do Cliente</p>"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.12);margin:0.9rem 0 0.8rem;'/>",
            unsafe_allow_html=True,
        )

        # ── Avatar + empresa ──────────────────────────────────────────────────
        iniciais = "".join(w[0].upper() for w in empresa.split()[:2]) if empresa else "?"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;padding:0 0.4rem 0.85rem;'>"
            f"<div style='width:36px;height:36px;border-radius:50%;flex-shrink:0;"
            f"background:linear-gradient(135deg,#38BDF8,#2563EB);"
            f"display:flex;align-items:center;justify-content:center;"
            f"font-weight:800;font-size:0.88rem;color:#fff;'>{iniciais}</div>"
            f"<div style='min-width:0;'>"
            f"<p style='margin:0;font-size:0.62rem;opacity:0.50;'>Empresa</p>"
            f"<p style='margin:0;font-weight:700;font-size:0.88rem;white-space:nowrap;"
            f"overflow:hidden;text-overflow:ellipsis;'>{empresa}</p>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.12);margin:0 0 0.6rem;'/>",
            unsafe_allow_html=True,
        )

        # ── Navegação ─────────────────────────────────────────────────────────
        st.markdown(
            "<p style='font-size:0.6rem;font-weight:700;letter-spacing:0.16em;"
            "text-transform:uppercase;color:rgba(255,255,255,0.32);"
            "padding:0 0.25rem;margin:0 0 0.35rem;'>Navegação</p>",
            unsafe_allow_html=True,
        )

        # Badge de alertas não lidos (lazy import para evitar circular)
        _alerta_unread = 0
        try:
            from page_alertas import get_unread_count as _gwc
            _alerta_unread = _gwc(st.session_state.get("client_id", ""))
        except Exception:
            pass

        for key, icon, label in PORTAL_NAV_ITEMS:
            is_active = (
                portal_page == key
                or (key == "ativos" and portal_page == "ativo_detalhe")
            )
            btn_type = "primary" if is_active else "secondary"
            # Mostra contador de não lidos no item Alertas
            display_label = label
            if key == "alertas" and _alerta_unread > 0:
                display_label = f"{label}  ·  {_alerta_unread}"
            if st.button(
                f"{icon}  {display_label}",
                key=f"portal_nav_{key}",
                use_container_width=True,
                type=btn_type,
            ):
                st.session_state["portal_page"] = key
                st.session_state.pop("portal_ativo_id", None)
                st.rerun()

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.12);margin:0.9rem 0 0.6rem;'/>",
            unsafe_allow_html=True,
        )

        if st.button("⬅️  Sair da conta", use_container_width=True, key="portal_logout"):
            logout()
            st.rerun()


# Alias para compatibilidade
def render_sidebar_nav(logo_b64: str, empresa: str, telefone: str,
                       current_page: str = "") -> None:
    render_sidebar(logo_b64, empresa, telefone)


def render_client_topnav(logo_b64: str, empresa: str, telefone: str,
                         client_logo_b64: str = "") -> None:
    """Barra de navegação horizontal premium — substitui a sidebar no portal do cliente."""
    from auth import logout
    portal_page = st.session_state.get("portal_page", "farois")

    _alerta_unread = 0
    try:
        from page_alertas import get_unread_count as _gwc
        _alerta_unread = _gwc(st.session_state.get("client_id", ""))
    except Exception:
        pass

    _notif_unread = 0
    try:
        from notifications import get_unread_count as _gnc
        _notif_unread = _gnc(st.session_state.get("client_id", ""))
    except Exception:
        pass

    iniciais = "".join(w[0].upper() for w in empresa.split()[:2]) if empresa else "?"
    logo_html = (
        f"<img src='data:image/jpeg;base64,{logo_b64}' "
        f"style='width:38px;height:38px;border-radius:9px;object-fit:cover;"
        f"box-shadow:0 4px 16px rgba(0,0,0,0.50);flex-shrink:0;'/>"
        if logo_b64 else ""
    )

    # Esconde sidebar — não utilizada no portal do cliente
    st.markdown(
        "<style>"
        "[data-testid='stSidebar']{display:none!important;}"
        "[data-testid='stSidebarCollapseButton']{display:none!important;}"
        "[data-testid='stSidebarExpandButton']{display:none!important;}"
        "[data-testid='collapsedControl']{display:none!important;}"
        ".stSidebarResizeHandle{display:none!important;}"
        "</style>",
        unsafe_allow_html=True,
    )

    # ── Brand card ─────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#071122 0%,#0D1A38 55%,#182F5E 100%);"
        f"border-radius:14px;padding:0.85rem 1.5rem;margin-bottom:4px;"
        f"display:flex;align-items:center;justify-content:space-between;"
        f"box-shadow:0 4px 28px rgba(7,17,34,0.30);'>"
        f"<div style='display:flex;align-items:center;gap:13px;'>"
        f"{logo_html}"
        f"<div>"
        f"<p style='margin:0 0 3px;font-size:0.5rem;letter-spacing:.22em;"
        f"text-transform:uppercase;color:rgba(255,255,255,0.30);font-weight:700;line-height:1;'>"
        f"Portal de Confiabilidade</p>"
        f"<p style='margin:0;font-size:1.1rem;font-weight:900;color:#38BDF8;"
        f"letter-spacing:-.025em;line-height:1;'>Pred.IO</p>"
        f"</div></div>"
        f"<div style='display:flex;align-items:center;gap:10px;'>"
        f"<div style='text-align:right;'>"
        f"<p style='margin:0;font-size:0.85rem;font-weight:700;color:#E2E8F0;line-height:1;'>"
        f"{empresa}</p>"
        f"</div>"
        f"<div style='width:34px;height:34px;border-radius:50%;flex-shrink:0;"
        f"background:linear-gradient(135deg,#38BDF8,#2563EB);"
        f"display:flex;align-items:center;justify-content:center;"
        f"font-weight:800;font-size:0.82rem;color:#fff;"
        f"box-shadow:0 2px 8px rgba(37,99,235,0.40);'>{iniciais}</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Marcador CSS — âncora para estilizar as colunas de nav abaixo ──────────
    # No mobile: barra de nav scrollável horizontalmente (bottom nav substitui)
    st.markdown(
        "<div class='portal-nav-marker'></div>"
        "<style>"
        "@media(max-width:768px){"
        "div.portal-nav-marker+div[data-testid='stHorizontalBlock'],"
        "div.portal-nav-marker~div[data-testid='stHorizontalBlock']{"
        "overflow-x:auto!important;-webkit-overflow-scrolling:touch!important;"
        "scrollbar-width:none!important;flex-wrap:nowrap!important;"
        "padding-bottom:4px;gap:4px!important;}"
        "div.portal-nav-marker+div[data-testid='stHorizontalBlock']::-webkit-scrollbar{"
        "display:none!important;}"
        "div.portal-nav-marker+div[data-testid='stHorizontalBlock']"
        " [data-testid='column']{min-width:52px!important;max-width:80px!important;}"
        "}"
        "</style>",
        unsafe_allow_html=True,
    )

    # ── Navegação + logout ─────────────────────────────────────────────────────
    nav_cols = st.columns([1] * len(PORTAL_NAV_ITEMS) + [0.7])

    for col, (key, icon, label) in zip(nav_cols[:-1], PORTAL_NAV_ITEMS):
        is_active = (
            portal_page == key
            or (key == "ativos" and portal_page == "ativo_detalhe")
        )
        disp = label
        if key == "notificacoes" and _notif_unread > 0:
            disp = f"{label} · {_notif_unread}"
        elif key == "alertas" and _alerta_unread > 0:
            disp = f"{label} · {_alerta_unread}"
        with col:
            if is_active:
                st.markdown(
                    f"<div style='text-align:center;padding:0.52rem 2px 0.38rem;"
                    f"border-bottom:2.5px solid {COLOR_BLUE};'>"
                    f"<span style='font-size:0.78rem;font-weight:700;"
                    f"color:{COLOR_NAVY};-webkit-text-fill-color:{COLOR_NAVY};"
                    f"white-space:nowrap;line-height:1.5;'>"
                    f"{icon}&thinsp;{disp}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                if st.button(
                    f"{icon}  {disp}",
                    key=f"portal_tnav_{key}",
                    use_container_width=True,
                ):
                    st.session_state["portal_page"] = key
                    st.session_state.pop("portal_ativo_id", None)
                    st.rerun()

    with nav_cols[-1]:
        if st.button("⬅️ Sair", key="portal_tnav_logout", use_container_width=True):
            logout()
            st.rerun()

    if client_logo_b64:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:14px;"
            f"background:rgba(15,31,61,0.55);border:1px solid rgba(30,58,138,0.28);"
            f"border-radius:10px;padding:10px 16px;margin:6px 0 8px;'>"
            f"<img src='data:image/jpeg;base64,{client_logo_b64}' "
            f"style='height:50px;width:50px;object-fit:contain;border-radius:8px;"
            f"background:#fff;padding:4px;box-shadow:0 2px 10px rgba(0,0,0,0.35);flex-shrink:0;'/>"
            f"<div style='min-width:0;'>"
            f"<p style='margin:0 0 2px;font-size:0.45rem;letter-spacing:.2em;"
            f"text-transform:uppercase;color:rgba(255,255,255,0.35);line-height:1;'>"
            f"Portal personalizado para</p>"
            f"<p style='margin:0;font-size:0.9rem;font-weight:700;color:#E2E8F0;"
            f"line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
            f"{empresa}</p>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<hr style='border:none;border-top:1.5px solid {COLOR_BORDER};"
        f"margin:0 0 1.5rem;'/>",
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"<h2 style='color:{COLOR_NAVY};margin:0.5rem 0 0;font-size:1.55rem;"
        f"font-weight:800;'>{title}</h2>"
        + (f"<p style='color:{COLOR_MUTED};margin:4px 0 0;font-size:0.88rem;'>"
           f"{subtitle}</p>" if subtitle else ""),
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:0.75rem 0 1rem;'/>",
        unsafe_allow_html=True,
    )


def empty_state(message: str) -> None:
    st.markdown(
        f"<div style='text-align:center;padding:3rem 1rem;color:{COLOR_MUTED};'>"
        f"<div style='font-size:3rem;margin-bottom:0.8rem;'>📭</div>"
        f"<p style='font-size:1rem;'>{message}</p></div>",
        unsafe_allow_html=True,
    )


def badge(label: str, color: str, text_color: str = "#fff") -> str:
    return (
        f"<span style='background:{color};color:{text_color};"
        f"-webkit-text-fill-color:{text_color};font-size:0.72rem;"
        f"font-weight:700;padding:3px 12px;border-radius:20px;"
        f"white-space:nowrap;'>{label}</span>"
    )


STATUS_CFG = {
    "aberto":              ("#3B82F6", "#fff"),
    "em análise":          ("#6366F1", "#fff"),
    "em andamento":        ("#0F1F3D", "#fff"),
    "aguardando cliente":  ("#D97706", "#fff"),
    "concluído":           ("#10B981", "#fff"),
    "cancelado":           ("#94A3B8", "#fff"),
    "reaberto":            ("#EC4899", "#fff"),
    "resolvido":           ("#10B981", "#fff"),
    "fechado":             ("#94A3B8", "#fff"),
}

PRIORIDADE_CFG = {
    "baixa":   ("#64748B", "#fff"),
    "média":   ("#F59E0B", "#000"),
    "alta":    ("#F97316", "#fff"),
    "crítica": ("#EF4444", "#fff"),
}

# ── Portal do Cliente — navegação ────────────────────────────────────────────

PORTAL_NAV_ITEMS = [
    ("dashboard",    "📊", "Dashboard"),
    ("ativos",       "⚙️",  "Ativos"),
    ("manutencao",   "📅", "Manutenção"),
    ("relatorios",   "📁", "Relatórios"),
    ("biblioteca",   "📚", "Biblioteca"),
    ("chamados",     "🔧", "Chamados"),
    ("notificacoes", "🔔", "Avisos"),
    ("alertas",      "⚠️",  "Alertas"),
    ("assistente",   "🤖", "Assistente"),
    ("preferencias", "📱", "Config."),
]

# ── Supervisão — constantes e componentes ─────────────────────────────────────

SV_NAV_ITEMS = [
    ("dashboard",        "🏠", "Dashboard"),
    ("chamados",         "🔧", "Chamados"),
    ("clientes",         "👥", "Clientes"),
    ("ativos_sv",        "⚙️",  "Ativos"),
    ("manutencao_sv",    "📅", "Manutenção"),
    ("alertas_sv",       "🔔", "Alertas"),
    ("notificacoes_sv",  "📨", "Avisos"),
    ("relatorios_sv",    "📁", "Relatórios"),
    ("biblioteca_sv",    "📚", "Biblioteca"),
    ("assistente_sv",    "🧪", "Assistente"),
    ("homologacao",      "🔬", "Homologação"),
]

SV_NAV_SOON = [
    ("configuracoes",    "🔩", "Configurações"),
]


def render_supervisao_sidebar(logo_b64: str, nome: str, perfil: str) -> None:
    from auth import logout
    with st.sidebar:
        # Logo
        if logo_b64:
            st.markdown(
                f"<div style='text-align:center;padding:1.5rem 0 1rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' "
                f"style='width:120px;border-radius:10px;"
                f"box-shadow:0 4px 16px rgba(0,0,0,0.40);'/></div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div style='text-align:center;font-size:0.62rem;font-weight:700;"
            "letter-spacing:0.18em;text-transform:uppercase;"
            "color:rgba(255,255,255,0.35);margin-bottom:1rem;'>"
            "Supervisão Pred.IO</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.10);margin:0 0 1rem;'/>",
            unsafe_allow_html=True,
        )

        # Usuário
        iniciais = "".join(w[0].upper() for w in nome.split()[:2]) if nome else "?"
        perfil_badge_color = "#10B981" if perfil == "admin" else "#38BDF8"
        perfil_label       = "Admin" if perfil == "admin" else "Funcionário"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;padding:0 0.5rem 1rem;'>"
            f"<div style='width:38px;height:38px;border-radius:50%;flex-shrink:0;"
            f"background:linear-gradient(135deg,#38BDF8,#2563EB);"
            f"display:flex;align-items:center;justify-content:center;"
            f"font-weight:800;font-size:0.9rem;color:#fff;'>{iniciais}</div>"
            f"<div>"
            f"<p style='margin:0;font-weight:700;font-size:0.9rem;color:#F1F5F9;'>{nome}</p>"
            f"<span style='background:{perfil_badge_color};color:#fff;-webkit-text-fill-color:#fff;"
            f"font-size:0.65rem;font-weight:700;padding:1px 8px;border-radius:10px;'>"
            f"{perfil_label}</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.10);margin:0 0 0.75rem;'/>",
            unsafe_allow_html=True,
        )

        # Navegação
        st.markdown(
            "<p style='font-size:0.65rem;font-weight:700;letter-spacing:0.14em;"
            "text-transform:uppercase;color:rgba(255,255,255,0.35);"
            "padding:0 0.5rem;margin:0 0 0.5rem;'>Menu</p>",
            unsafe_allow_html=True,
        )

        sv_view = st.session_state.get("sv_view", "dashboard")
        for key, icon, label in SV_NAV_ITEMS:
            is_active = (
                sv_view == key
                or (key == "chamados" and sv_view == "chamado_detalhe")
                or (key == "clientes" and sv_view in ("cliente_historico", "cliente_novo"))
                or (key == "ativos_sv" and sv_view in ("ativo_detalhe", "ativo_novo", "componente_novo"))
                or (key == "relatorios_sv" and sv_view in ("relatorio_novo", "relatorio_editar"))
            )
            prefix = "▶" if is_active else "   "
            if st.button(f"{prefix} {icon}  {label}", key=f"sv_nav_{key}",
                         use_container_width=True):
                st.session_state["sv_view"] = key
                st.session_state.pop("sv_chamado_id", None)
                st.rerun()

        st.markdown(
            "<p style='font-size:0.65rem;font-weight:700;letter-spacing:0.14em;"
            "text-transform:uppercase;color:rgba(255,255,255,0.20);"
            "padding:0 0.5rem;margin:1rem 0 0.5rem;'>Em breve</p>",
            unsafe_allow_html=True,
        )
        for key, icon, label in SV_NAV_SOON:
            st.markdown(
                f"<div style='padding:8px 12px;margin-bottom:2px;opacity:0.35;'>"
                f"<span style='color:#94A3B8;font-size:0.88rem;'>{icon} &nbsp; {label}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.10);margin:1rem 0;'/>",
            unsafe_allow_html=True,
        )

        if st.button("⬅️  Sair da conta", use_container_width=True, key="sv_logout"):
            logout()
            st.rerun()


def render_sv_topnav() -> None:
    """Barra de navegação horizontal — sempre visível na Supervisão."""
    import streamlit.components.v1 as components
    from auth import logout, current_nome, current_perfil

    sv_view      = st.session_state.get("sv_view", "dashboard")
    nome         = current_nome()
    perfil       = current_perfil()
    iniciais     = "".join(w[0].upper() for w in nome.split()[:2]) if nome else "?"
    perfil_label = "Admin" if perfil == "admin" else "Funcionário"

    # ── Linha 1: Logo + título | Usuário + Sair ───────────────────────────
    logo_col, user_col = st.columns([2, 2])

    with logo_col:
        _logo = load_image_b64("logo.jpg")
        if _logo:
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:10px;padding-top:4px;'>"
                f"<img src='data:image/jpeg;base64,{_logo}' "
                f"style='height:44px;object-fit:contain;' />"
                f"<span style='font-size:0.68rem;font-weight:700;letter-spacing:0.14em;"
                f"text-transform:uppercase;color:{COLOR_MUTED};'>Supervisão</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    with user_col:
        u_info, u_btn = st.columns([3, 1])
        with u_info:
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;justify-content:flex-end;'>"
                f"<div>"
                f"<p style='margin:0;font-size:0.78rem;font-weight:700;"
                f"color:{COLOR_NAVY};text-align:right;'>{nome}</p>"
                f"<p style='margin:0;font-size:0.68rem;color:{COLOR_MUTED};text-align:right;'>"
                f"{perfil_label}</p>"
                f"</div>"
                f"<div style='width:30px;height:30px;border-radius:50%;flex-shrink:0;"
                f"background:linear-gradient(135deg,#38BDF8,#2563EB);"
                f"display:flex;align-items:center;justify-content:center;"
                f"font-weight:800;font-size:0.78rem;color:#fff;'>{iniciais}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with u_btn:
            if st.button("Sair", key="sv_tnav_logout", use_container_width=True):
                logout()
                st.rerun()

    # ── Botões ocultos: acionados pelo iframe para navegar via WebSocket ──
    for _nk, _ni, _nl in SV_NAV_ITEMS:
        if st.button(f"▸sv_{_nk}", key=f"__svnav_{_nk}__"):
            st.session_state["sv_view"] = _nk
            st.session_state.pop("sv_chamado_id", None)
            st.rerun()

    # ── Linha 2: Pill nav horizontal (iframe full-width) ──────────────────
    _active_map = {
        "chamado_detalhe":   "chamados",
        "cliente_historico": "clientes",
        "cliente_novo":      "clientes",
        "ativo_detalhe":     "ativos_sv",
        "ativo_novo":        "ativos_sv",
        "componente_novo":   "ativos_sv",
        "relatorio_novo":    "relatorios_sv",
        "relatorio_editar":  "relatorios_sv",
    }
    _active = _active_map.get(sv_view, sv_view)
    _arrow  = "▸"

    _pills = "".join(
        f'<button class="pill{" active" if _active == k else ""}" data-key="{k}">'
        f'{ic} {lb}</button>'
        for k, ic, lb in SV_NAV_ITEMS
    )

    _iframe = f"""<!DOCTYPE html>
<html><head><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:transparent;overflow:hidden;font-family:system-ui,sans-serif;}}
#nav{{display:flex;gap:6px;padding:4px 0;overflow-x:auto;overflow-y:hidden;}}
#nav::-webkit-scrollbar{{height:3px}}
#nav::-webkit-scrollbar-track{{background:transparent}}
#nav::-webkit-scrollbar-thumb{{background:rgba(15,31,61,0.22);border-radius:3px}}
.pill{{font-size:0.8rem;font-weight:600;white-space:nowrap;
  padding:6px 13px;border-radius:20px;
  display:inline-flex;align-items:center;gap:5px;
  border:1px solid rgba(15,31,61,0.15);cursor:pointer;
  background:rgba(15,31,61,0.06);color:#334155;
  transition:background 0.15s,color 0.15s;}}
.pill.active{{background:linear-gradient(135deg,#1565C0,#2563EB);
  color:#fff;border-color:transparent;cursor:default;}}
.pill:not(.active):hover{{background:rgba(21,101,192,0.13);color:#1E3A8A;}}
</style></head><body>
<div id="nav">{_pills}</div>
<script>
document.querySelectorAll('.pill:not(.active)').forEach(function(b){{
  b.addEventListener('click',function(){{
    var k=this.getAttribute('data-key');
    try{{
      var sb=window.parent.document.querySelector('button[aria-label="{_arrow}sv_'+k+'"]');
      if(sb)sb.click();
    }}catch(e){{}}
  }});
}});
</script>
</body></html>"""

    components.html(_iframe, height=46, scrolling=False)

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:4px 0 1rem;'/>",
        unsafe_allow_html=True,
    )


def remove_floating_assistant() -> None:
    """Remove o assistente flutuante do DOM (chamado na tela de login / logout)."""
    import streamlit.components.v1 as _comp
    _comp.html("""<!DOCTYPE html><html><head></head><body style="margin:0">
<script>
(function(){
  var p=window.parent; if(!p||p===window)return;
  var pd=p.document;
  ['pred-fab','pred-chat','pred-styles'].forEach(function(id){
    var el=pd.getElementById(id); if(el)el.remove();
  });
  // Reseta guard para que o assistente seja reinjetado no proximo login
  try{ delete p.predNavTo; }catch(e){ p.predNavTo=undefined; }
})();
</script>
</body></html>""", height=0)


def inject_floating_assistant(sid: str = "", client_id: str = "") -> None:
    """Injeta o Assistente Tecnico Pred.IO como botao flutuante no portal.

    Usa components.html() + injecao no parent.document.
    Dados do cliente (ativos, manutencoes, relatorios etc.) sao buscados
    server-side via assistant_engine.get_client_context() e embutidos no JS
    como PRED_CONTEXT — o client_id nunca e exposto ao front-end.

    SECURITY:
      - client_id vem da sessao/autenticacao, NUNCA do front-end.
      - PRED_CONTEXT contem apenas dados autorizados para o cliente logado.
      - Documentos internos nao aparecem para cliente.
      - Dados da Supervisao Pred.IO nao aparecem aqui.

    FUTURE API: POST /api/assistant/technical-query
      Quando a IA real for integrada, o JS fara fetch() para esse endpoint
      em vez de usar PRED_CONTEXT local. O endpoint chamara query_assistant()
      de assistant_engine.py com o client_id da sessao do servidor.
    """
    import json as _json
    import streamlit.components.v1 as _comp
    from assistant_engine import get_client_context

    # Busca dados autorizados server-side. client_id ja validado pela sessao.
    try:
        _ctx = get_client_context(client_id) if client_id else {}
    except Exception:
        _ctx = {}

    _ctx_json = _json.dumps(_ctx, ensure_ascii=False)

    # --- icones SVG em branco ---
    ROBOT_SVG = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='30' height='30' viewBox='0 0 32 32' fill='none'>"
        "<circle cx='16' cy='2' r='2' fill='white'/>"
        "<rect x='15' y='4' width='2' height='4' rx='1' fill='white'/>"
        "<rect x='5' y='8' width='22' height='13' rx='3' stroke='white' stroke-width='2' fill='none'/>"
        "<circle cx='11' cy='14' r='2.5' fill='white'/>"
        "<circle cx='21' cy='14' r='2.5' fill='white'/>"
        "<circle cx='12' cy='14.9' r='1' fill='#1E3A8A'/>"
        "<circle cx='22' cy='14.9' r='1' fill='#1E3A8A'/>"
        "<path d='M11 18.5 Q16 21.5 21 18.5' stroke='white' stroke-width='1.8' fill='none' stroke-linecap='round'/>"
        "<rect x='4' y='22' width='24' height='9' rx='3' stroke='white' stroke-width='2' fill='none'/>"
        "<rect x='0' y='23' width='4' height='5' rx='2' stroke='white' stroke-width='1.6' fill='none'/>"
        "<rect x='28' y='23' width='4' height='5' rx='2' stroke='white' stroke-width='1.6' fill='none'/>"
        "<circle cx='11' cy='26.5' r='1.3' fill='white'/>"
        "<circle cx='16' cy='26.5' r='1.3' fill='white'/>"
        "<circle cx='21' cy='26.5' r='1.3' fill='white'/>"
        "</svg>"
    )
    ROBOT_SM = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 32 32' fill='none'>"
        "<circle cx='16' cy='2' r='2' fill='white'/>"
        "<rect x='15' y='4' width='2' height='4' rx='1' fill='white'/>"
        "<rect x='5' y='8' width='22' height='13' rx='3' stroke='white' stroke-width='2.2' fill='none'/>"
        "<circle cx='11' cy='14' r='2.5' fill='white'/>"
        "<circle cx='21' cy='14' r='2.5' fill='white'/>"
        "<circle cx='12' cy='14.9' r='1' fill='#38BDF8'/>"
        "<circle cx='22' cy='14.9' r='1' fill='#38BDF8'/>"
        "<path d='M11 18.5 Q16 21.5 21 18.5' stroke='white' stroke-width='2' fill='none' stroke-linecap='round'/>"
        "<rect x='4' y='22' width='24' height='9' rx='3' stroke='white' stroke-width='2.2' fill='none'/>"
        "<rect x='0' y='23' width='4' height='5' rx='2' stroke='white' stroke-width='1.8' fill='none'/>"
        "<rect x='28' y='23' width='4' height='5' rx='2' stroke='white' stroke-width='1.8' fill='none'/>"
        "<circle cx='11' cy='26.5' r='1.3' fill='white'/>"
        "<circle cx='16' cy='26.5' r='1.3' fill='white'/>"
        "<circle cx='21' cy='26.5' r='1.3' fill='white'/>"
        "</svg>"
    )
    CLOSE_SVG = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='26' height='26' viewBox='0 0 24 24'"
        " fill='none' stroke='white' stroke-width='2.5' stroke-linecap='round'>"
        "<line x1='6' y1='6' x2='18' y2='18'/>"
        "<line x1='18' y1='6' x2='6' y2='18'/>"
        "</svg>"
    )

    def _js(s):
        return s.replace("'", "\\'")

    # CSS e estrutura HTML usam {{ }} por ser f-string com JS
    html_top = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;overflow:hidden;background:transparent;">
<script>
(function () {{
  var p = window.parent;
  if (!p || p === window) return;
  var pd = p.document;
  // Injeta funcao de navegacao suave no contexto do window pai
  if (!p.predNavTo) {{
    var _ns=pd.createElement('script');
    _ns.textContent=(
      // Esconde botoes de nav suave pelo texto (fallback para :has() nao suportado)
      '(function(){{'+
        'function _hideNavBtns(){{'+
          'var bs=document.querySelectorAll("button");'+
          'for(var i=0;i<bs.length;i++){{'+
            'if(bs[i].textContent.trim().charAt(0)==="▸"){{'+
              'var el=bs[i];'+
              'while(el&&el.getAttribute&&el.getAttribute("data-testid")!=="stButton")el=el.parentElement;'+
              'if(el)el.style.display="none"; else bs[i].style.display="none";'+
            '}}'+
          '}}'+
        '}}'+
        '_hideNavBtns();'+
        'var _mo=new MutationObserver(_hideNavBtns);'+
        '_mo.observe(document.body,{{childList:true,subtree:true}});'+
      '}})();'+
      // Funcao de navegacao: clica no botao oculto ou cai em URL
      'window.predNavTo=function(page){{'+
        'var btns=document.querySelectorAll("button");'+
        'for(var i=0;i<btns.length;i++){{'+
          'if(btns[i].textContent.trim()==="▸"+page){{btns[i].click();return;}}'+
        '}}'+
        'var s=new URLSearchParams(window.location.search).get("sid")||"";'+
        'window.location.href="?portal_page="+page+(s?"&sid="+s:"");'+
      '}};'
    );
    (pd.head||pd.body).appendChild(_ns);
  }}
  if (pd.getElementById('pred-fab')) return;

  var sty = pd.createElement('style');
  sty.id = 'pred-styles';
  sty.textContent = [
    '#pred-fab{{position:fixed;bottom:24px;right:24px;width:58px;height:58px;border-radius:50%;',
    'background:linear-gradient(135deg,#0F1F3D 0%,#1E3A8A 55%,#2563EB 100%);',
    'box-shadow:0 4px 20px rgba(15,31,61,.5),0 0 0 2px rgba(56,189,248,.3);',
    'display:flex;align-items:center;justify-content:center;cursor:pointer;',
    'z-index:999998;border:none;outline:none;transition:transform .2s,box-shadow .2s;',
    '-webkit-tap-highlight-color:transparent;touch-action:manipulation;}}',
    '#pred-fab:hover{{transform:scale(1.09);box-shadow:0 6px 28px rgba(37,99,235,.6),0 0 0 3px rgba(56,189,248,.45);}}',
    '#pred-chat{{position:fixed;bottom:94px;right:24px;width:360px;max-height:520px;',
    'background:#fff;border:1px solid #E2E8F0;border-radius:16px;',
    'box-shadow:0 12px 48px rgba(15,31,61,.18),0 2px 8px rgba(0,0,0,.08);',
    'z-index:999999;display:none;flex-direction:column;overflow:hidden;',
    'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}}',
    '#pred-chat.pred-open{{display:flex;}}',
    '#pred-chat-header{{background:linear-gradient(135deg,#0F1F3D 0%,#1E3A8A 65%,#2563EB 100%);',
    'color:#fff;padding:13px 14px;border-radius:16px 16px 0 0;',
    'display:flex;align-items:center;gap:10px;flex-shrink:0;}}',
    '#pred-hdr-avatar{{width:36px;height:36px;border-radius:50%;',
    'background:linear-gradient(135deg,#38BDF8,#2563EB);',
    'display:flex;align-items:center;justify-content:center;flex-shrink:0;}}',
    '#pred-hdr-info{{flex:1;min-width:0;}}',
    '#pred-hdr-info strong{{display:block;font-size:.85rem;font-weight:700;color:#fff;-webkit-text-fill-color:#fff;}}',
    '#pred-hdr-info span{{font-size:.67rem;color:#94A3B8;-webkit-text-fill-color:#94A3B8;}}',
    '#pred-hdr-btns{{display:flex;gap:4px;flex-shrink:0;}}',
    '#pred-hdr-btns button{{background:rgba(255,255,255,.12);border:none;color:#CBD5E1;',
    '-webkit-text-fill-color:#CBD5E1;width:28px;height:28px;border-radius:6px;cursor:pointer;',
    'font-size:15px;display:flex;align-items:center;justify-content:center;transition:background .15s;}}',
    '#pred-hdr-btns button:hover{{background:rgba(255,255,255,.22);}}',
    '#pred-chat-msgs{{flex:1;overflow-y:auto;padding:12px 12px 4px;',
    'display:flex;flex-direction:column;gap:8px;min-height:0;}}',
    '.pred-msg{{max-width:90%;font-size:.82rem;line-height:1.5;border-radius:12px;padding:10px 14px;}}',
    '.pred-bot{{background:#F1F5F9;color:#0F172A;border-radius:4px 12px 12px 12px;align-self:flex-start;}}',
    '.pred-usr{{background:linear-gradient(135deg,#1E3A8A,#2563EB);color:#fff;',
    '-webkit-text-fill-color:#fff;border-radius:12px 4px 12px 12px;align-self:flex-end;}}',
    '.pred-disc{{font-size:.67rem;color:#94A3B8;margin-top:4px;font-style:italic;align-self:flex-start;max-width:90%;}}',
    '.pred-act{{display:inline-block;margin-top:8px;padding:6px 14px;',
    'background:linear-gradient(135deg,#0F1F3D,#2563EB);color:#fff!important;',
    '-webkit-text-fill-color:#fff!important;border-radius:8px;font-size:.75rem;',
    'font-weight:600;cursor:pointer;border:none;transition:opacity .15s;}}',
    '.pred-act:hover{{opacity:.88;}}',
    '#pred-sugg{{padding:8px 12px;display:flex;flex-wrap:wrap;gap:5px;border-top:1px solid #F1F5F9;flex-shrink:0;}}',
    '.pred-chip{{background:#EFF6FF;border:1px solid #BFDBFE;color:#1E40AF;-webkit-text-fill-color:#1E40AF;',
    'font-size:.71rem;padding:4px 10px;border-radius:20px;cursor:pointer;white-space:nowrap;',
    'transition:background .15s;font-weight:500;}}',
    '.pred-chip:hover{{background:#DBEAFE;}}',
    '#pred-input-area{{display:flex;align-items:center;gap:8px;padding:10px 12px;',
    'border-top:1px solid #E2E8F0;flex-shrink:0;}}',
    '#pred-input{{flex:1;border:1px solid #CBD5E1;border-radius:8px;padding:8px 11px;',
    'font-size:.82rem;outline:none;color:#0F172A;background:#fff;transition:border-color .15s;}}',
    '#pred-input:focus{{border-color:#2563EB;}}',
    '#pred-send{{width:36px;height:36px;border-radius:8px;',
    'background:linear-gradient(135deg,#0F1F3D,#2563EB);border:none;',
    'color:#fff;cursor:pointer;font-size:16px;display:flex;align-items:center;',
    'justify-content:center;flex-shrink:0;transition:opacity .15s;}}',
    '#pred-send:hover{{opacity:.88;}}',
    '.pred-typing{{display:flex;gap:4px;padding:10px 14px;background:#F1F5F9;',
    'border-radius:4px 12px 12px 12px;align-self:flex-start;width:fit-content;}}',
    '.pred-typing span{{width:6px;height:6px;background:#94A3B8;border-radius:50%;',
    'animation:predBounce 1.2s ease-in-out infinite;}}',
    '.pred-typing span:nth-child(1){{animation-delay:0s;}}',
    '.pred-typing span:nth-child(2){{animation-delay:.2s;}}',
    '.pred-typing span:nth-child(3){{animation-delay:.4s;}}',
    '@keyframes predBounce{{0%,60%,100%{{transform:translateY(0);opacity:.5;}}30%{{transform:translateY(-4px);opacity:1;}}}}',
    '@media(max-width:768px){{',
    '#pred-fab{{bottom:72px;right:16px;width:56px;height:56px;}}',
    '#pred-chat{{width:calc(100vw - 16px);left:8px;right:8px;',
    'bottom:140px;max-height:62vh;}}}}',
  ].join('');
  pd.head.appendChild(sty);

  var ROBOT = '{_js(ROBOT_SVG)}';
  var ROBOT_SM = '{_js(ROBOT_SM)}';
  var CLOSE = '{_js(CLOSE_SVG)}';

  var fab = pd.createElement('button');
  fab.id = 'pred-fab'; fab.title = 'Assistente Tecnico Pred.IO';
  fab.innerHTML = ROBOT;
  pd.body.appendChild(fab);

  var chat = pd.createElement('div');
  chat.id = 'pred-chat'; chat.setAttribute('role','dialog');
  chat.innerHTML = [
    '<div id="pred-chat-header">',
    '<div id="pred-hdr-avatar">' + ROBOT_SM + '</div>',
    '<div id="pred-hdr-info">',
    '<strong>Assistente Tecnico Pred.IO</strong>',
    '<span>Ativos &middot; Manutencao &middot; Chamados &middot; Documentos</span>',
    '</div>',
    '<div id="pred-hdr-btns">',
    '<button id="pred-min-btn" title="Minimizar">&#8722;</button>',
    '<button id="pred-close-btn" title="Fechar">&#215;</button>',
    '</div></div>',
    '<div id="pred-chat-msgs"></div>',
    '<div id="pred-sugg">',
    '<span class="pred-chip" data-q="Quais sao as proximas manutencoes?">📅 Manutencao</span>',
    '<span class="pred-chip" data-q="Quais relatorios foram publicados?">📋 Relatorios</span>',
    '<span class="pred-chip" data-q="Tem manual tecnico do compressor?">📚 Manual tecnico</span>',
    '<span class="pred-chip" data-q="Quero abrir um chamado tecnico">🔧 Chamado</span>',
    '</div>',
    '<div id="pred-input-area">',
    '<input type="text" id="pred-input" placeholder="Digite sua duvida..." autocomplete="off"/>',
    '<button id="pred-send" title="Enviar">&#10148;</button>',
    '</div>'
  ].join('');
  pd.body.appendChild(chat);

  var _open=false, _init=false, _sid='{sid}', _tc=0;

"""

    # PRED_CONTEXT e injetado aqui como JSON puro, fora do f-string para nao conflitar com {{ }}
    html_ctx = "  var PRED_CONTEXT = __CTX_JSON__;\n\n".replace("__CTX_JSON__", _ctx_json)

    html_bot = f"""  function predToggle(){{ _open ? predClose() : predOpen(); }}

  function predOpen(){{
    _open=true; chat.classList.add('pred-open'); fab.innerHTML=CLOSE;
    try{{localStorage.setItem('pred_open','1');}}catch(e){{}}
    if(!_init){{
      _init=true;
      addBot('<strong>Ola! Sou o Assistente Tecnico Pred.IO.</strong><br><br>Posso ajudar com ativos monitorados, plano de manutencao, relatorios tecnicos, chamados e documentos disponiveis.', null, []);
    }}
    scroll();
  }}
  function predMin(){{ _open=false; chat.classList.remove('pred-open'); fab.innerHTML=ROBOT; }}
  function predClose(){{ predMin(); try{{localStorage.removeItem('pred_open');}}catch(e){{}} }}

  function predQuick(t){{
    var inp=pd.getElementById('pred-input');
    if(inp)inp.value=t; predSend();
  }}

  function predSend(){{
    var inp=pd.getElementById('pred-input');
    var t=(inp?inp.value:'').trim(); if(!t)return;
    inp.value=''; addUser(t);
    var sg=pd.getElementById('pred-sugg'); if(sg)sg.style.display='none';
    var tid=showTyping();
    // Simula latencia de API — quando endpoint real estiver pronto,
    // substituir este setTimeout por fetch('/api/assistant/technical-query', ...)
    setTimeout(function(){{
      hideTyping(tid);
      var r = getResp(t);
      addBot(r.text, null, r.actions);
    }}, 500 + Math.floor(Math.random() * 400));
  }}

  function addUser(t){{
    var m=pd.getElementById('pred-chat-msgs'); if(!m)return;
    var d=pd.createElement('div'); d.className='pred-msg pred-usr'; d.textContent=t;
    m.appendChild(d); scroll();
  }}

  function addBot(html,disc,actions){{
    var m=pd.getElementById('pred-chat-msgs'); if(!m)return;
    var wrap=pd.createElement('div');
    wrap.style.cssText='max-width:92%;align-self:flex-start;';
    var d=pd.createElement('div'); d.className='pred-msg pred-bot'; d.innerHTML=html; wrap.appendChild(d);
    if(disc){{
      var dd=pd.createElement('div'); dd.className='pred-disc'; dd.innerHTML='<em>'+disc+'</em>'; wrap.appendChild(dd);
    }}
    var acts=actions||[];
    if(acts.length){{
      var row=pd.createElement('div');
      row.style.cssText='display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;padding-left:2px;';
      acts.forEach(function(a){{
        var btn=pd.createElement('button'); btn.className='pred-act';
        btn.textContent=a.label;
        btn.onclick=function(){{ navTo(a.page); }};
        row.appendChild(btn);
      }});
      wrap.appendChild(row);
    }}
    m.appendChild(wrap); scroll();
  }}

  function showTyping(){{
    var m=pd.getElementById('pred-chat-msgs'); if(!m)return null;
    var id='pty'+(++_tc);
    var d=pd.createElement('div'); d.className='pred-typing'; d.id=id;
    d.innerHTML='<span></span><span></span><span></span>';
    m.appendChild(d); scroll(); return id;
  }}
  function hideTyping(id){{var el=pd.getElementById(id);if(el)el.remove();}}

  function scroll(){{
    setTimeout(function(){{
      var m=pd.getElementById('pred-chat-msgs'); if(m)m.scrollTop=m.scrollHeight;
    }},20);
  }}

  function navTo(page){{
    // Navegacao suave: clica no botao Streamlit oculto (sem reload de pagina)
    try{{
      if(p.predNavTo){{ p.predNavTo(page); return; }}
    }}catch(e){{}}
    // Fallback: navegacao por URL
    var params=new URLSearchParams((p.location.search||'').replace(/^\?/,''));
    params.set('portal_page',page);
    if(_sid) params.set('sid',_sid);
    try{{ p.location.href='?'+params.toString(); }}catch(_){{}}
  }}

  /* ── Motor de intenção JS — espelha assistant_engine.py ─────────────────
     Usa PRED_CONTEXT embutido server-side (dados autorizados do cliente).
     Quando POST /api/assistant/technical-query estiver ativo, este bloco
     sera substituido por um fetch() para o endpoint Python. */
  function getResp(q) {{
    var ctx = PRED_CONTEXT;
    var ql  = q.toLowerCase();

    /* Normaliza texto para busca sem acentos */
    var norm = function(s) {{
      return (s||'').toLowerCase()
        .replace(/[ãâàáä]/g,'a').replace(/[êèéë]/g,'e')
        .replace(/[îìíï]/g,'i').replace(/[õôòóö]/g,'o')
        .replace(/[ûùúü]/g,'u').replace(/ç/g,'c');
    }};
    /* Normaliza ql para que todos os regex funcionem sem acento */
    ql = norm(ql);

    /* Busca em chunks indexados — retorna hit ou null */
    var searchChunks = function(extraWords) {{
      var qn = norm(ql);
      var baseWords = qn.split(/ +/).filter(function(w) {{ return w.length > 2; }});
      var words = baseWords.concat((extraWords || []).map(norm));
      if (!words.length) return null;
      var best = null, bestScore = 0;
      (ctx.documentos || []).forEach(function(doc) {{
        (doc.chunks || []).forEach(function(chunk) {{
          var hay = norm([chunk.titulo_secao, chunk.conteudo, chunk.palavras_chave].join(' '));
          var score = words.filter(function(w) {{ return hay.indexOf(w) >= 0; }}).length;
          if (score > bestScore) {{
            bestScore = score;
            best = {{ docTitulo: doc.titulo, docId: doc.id, docUrl: doc.arquivo_url || '', secao: chunk.titulo_secao || '', conteudo: chunk.conteudo || '', pagina: chunk.pagina_inicio || '' }};
          }}
        }});
      }});
      return bestScore > 0 ? best : null;
    }};

    /* Formata resposta com atribuicao de fonte */
    var fmtChunk = function(hit) {{
      var src = 'Com base no documento <strong>' + hit.docTitulo + '</strong>';
      if (hit.secao) src += ' (Secao: ' + hit.secao + ')';
      if (hit.pagina) src += ' &mdash; pag. ' + hit.pagina;
      var urlLink = (hit.docUrl && hit.docUrl.indexOf('/mock/') < 0)
        ? '<br><a href="' + hit.docUrl + '" target="_blank" style="color:#2563EB;font-weight:600;font-size:.78rem;">📂 Abrir documento</a>'
        : '';
      return src + ', encontrei:<br><br>' + hit.conteudo + urlLink;
    }};

    /* MYCOLD AB / MYCOLD PAO */
    if (/mycold|oleo.*mycom|mycom.*oleo/.test(ql)) {{
      if (/ab.*68|ab68|mycold ab/.test(ql)) {{
        return {{ text: 'O <strong>MYCOLD AB 68</strong> foi descontinuado. No Portal Pred.IO, a referencia atual deve ser <strong>MYCOLD PAO</strong>. O MYCOLD AB 68 pode aparecer apenas como referencia historica/inativa, nunca como oleo atual.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Ver Tabela de Oleos', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      return {{ text: 'Com base na Tabela de Oleos Homologados MAYEKAWA/MYCOM, o oleo MYCOM homologado atual na base Pred.IO e <strong>MYCOLD PAO</strong> (ISO VG 68, PAO sintetico, NH3/R22, 53 cSt @ 40°C). A referencia antiga MYCOLD AB 68 foi descontinuada.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Ver Tabela de Oleos Homologados', page:'biblioteca'}}] }};
    }}

    /* OLEO HOMOLOGADO (Tabela MAYEKAWA) */
    if (/homologado|tabela.*oleo|reflo|rab 68|gargoyle|eal arctic|icematic|capella|pao|poe|oleo.*r134a|oleo.*nh3|oleo.*amonia|qualquer.*oleo|qual.*oleo usar/.test(ql)) {{
      if (/qualquer/.test(ql)) {{
        return {{ text: 'Nao. A viscosidade ISO VG 68 e apenas um dos criterios. A selecao do oleo deve considerar o fluido refrigerante, a classe do lubrificante (PAO, POE, mineral), a aplicacao, a condicao operacional e a tabela homologada MAYEKAWA/MYCOM.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Ver Tabela de Oleos Homologados', page:'biblioteca'}}] }};
      }}
      if (/r134a|r404a|hfc/.test(ql)) {{
        return {{ text: 'Para R134a/R404a, os oleos homologados na base Pred.IO sao POE ISO VG 68: <strong>MOBIL EAL ARCTIC 68</strong>, <strong>ICEMATIC SW 68</strong> e <strong>CAPELLA HFC 68</strong>. Validar conforme fluido, equipamento e orientacao tecnica.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Ver Tabela de Oleos Homologados', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/amonia|nh3/.test(ql)) {{
        return {{ text: 'Para Amonia/NH3, os oleos homologados na base Pred.IO incluem (ISO VG 68): REFLO 68A, RAB 68, R 200, MOBIL GARGOYLE ARCTIC SHC 226 E, MOBIL GARGOYLE ARCTIC EH, ESSO REFRIGERATION 68, CAPELLA 68 e <strong>MYCOLD PAO</strong>.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Ver Tabela de Oleos Homologados', page:'biblioteca'}}] }};
      }}
      var oleos = (ctx.oleos_homologados || []).filter(function(o) {{ return o.status === 'Homologado'; }});
      if (oleos.length) {{
        var nomes = oleos.map(function(o) {{ return o.nome; }}).join(', ');
        return {{ text: 'Os oleos homologados na base Pred.IO (ISO VG 68) sao: <strong>' + nomes + '</strong>. A selecao depende do fluido refrigerante, classe e validacao tecnica.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Ver Tabela de Oleos Homologados', page:'biblioteca'}}] }};
      }}
      return {{ text: 'Consulte a Tabela de Oleos Homologados MAYEKAWA/MYCOM na Biblioteca Tecnica ou abra um chamado para validacao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Ver Tabela de Oleos', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* REVISAO CONDICAO — 20.000 horas, overhaul, desmontagem, kit revisao */
    if (/20\.?000.*hora|20000.*hora|bienal|desmontagem|desmontar|kit revis|revis.o geral|revisao geral|overhaul|preciso revisar/.test(ql)) {{
      return {{ text: 'No Portal Pred.IO, 20.000 horas e referencia tecnica, nao gatilho automatico de desmontagem ou overhaul. A decisao deve considerar a saude real da maquina: analise de vibracao, analise de oleo, termografia, historico operacional, tendencia de score, falhas recorrentes e avaliacao tecnica Pred.IO.<br><br><strong>20.000 horas e referencia tecnica, nao gatilho automatico de overhaul. A decisao depende da saude real da maquina.</strong><br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}, {{label:'📚 Ver Manual', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado Tecnico', page:'chamados'}}] }};
    }}

    /* MYPRO TOUCH / MYPRO TOUCH AD */
    if (/mypro.touch|painel mypro|login.*mypro|senha.*mypro|senha.*painel|login.*painel|level 1|level 2|nivel 1|nivel 2|como ligar.*compressor|como parar.*compressor|tecla partida|tecla parar|set point|cut in|cut out|alterar.*capacidade|capacidade manual|limpar alarme|resetar alarme|reset.*alarme|alarme.*voltou|alarme.*varias|alarme.*recorrente|alarme vermelho|alarme azul|estado.*compressor|onde.*vejo.*alarme|onde.*ver.*alarme|registrar.*falha|o que.*registrar/.test(ql)) {{
      if (/level 2|nivel 2|supervisor|xyz|2222/.test(ql)) {{
        return {{ text: 'Na base Pred.IO, o acesso <strong>Level 2 — Supervisor/Administrador</strong> do painel Mypro Touch e:<br><br>Login: <code>XYZ</code> / Senha: <code>2222</code><br><br>⚠️ Use apenas se voce for operador autorizado.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/level 1|nivel 1|operador.*login|login.*operador|abc|1111/.test(ql)) {{
        return {{ text: 'Na base Pred.IO, o acesso <strong>Level 1 — Operador</strong> do painel Mypro Touch e:<br><br>Login: <code>ABC</code> / Senha: <code>1111</code><br><br>⚠️ Use apenas se voce for operador autorizado.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/login|senha|level|nivel|acesso/.test(ql)) {{
        return {{ text: 'Na base Pred.IO, os acessos do painel <strong>Mypro Touch</strong> sao:<br><br>&bull; <strong>Level 1 — Operador:</strong> Login: <code>ABC</code> / Senha: <code>1111</code><br>&bull; <strong>Level 2 — Supervisor/Administrador:</strong> Login: <code>XYZ</code> / Senha: <code>2222</code><br><br>⚠️ Use apenas se voce for operador autorizado.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/ligar|partir|partida/.test(ql)) {{
        return {{ text: 'No painel <strong>Mypro Touch</strong>, pressione a tecla <strong>PARTIDA</strong> por alguns segundos ate que ela fique verde. Acompanhe a janela <em>Condicao Atual</em> &rarr; <em>Estado do Compressor</em>: indica <em>Preparar para Partir</em> e depois <em>Compressor Ligado</em>.<br><br>⚠️ Use apenas se voce for operador autorizado.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/parar|parada|desligar/.test(ql)) {{
        return {{ text: 'No painel <strong>Mypro Touch</strong>, pressione a tecla <strong>PARAR</strong> por alguns instantes ate que o <em>Estado do Compressor</em> apresente <em>Recolhimento do Sistema</em>.<br><br>⚠️ Use apenas se voce for operador autorizado.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/voltou|varias vezes|recorrente/.test(ql)) {{
        return {{ text: 'Alarme recorrente nao deve ser tratado apenas com reset. Registre as condicoes operacionais, verifique a tendencia, correlacione com pressoes, temperaturas, oleo, vibracao e historico, e <strong>abra um chamado tecnico</strong> para analise da equipe Pred.IO.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado Tecnico', page:'chamados'}}] }};
      }}
      if (/limpar alarme|resetar|reset.*alarme|limpar falha/.test(ql)) {{
        return {{ text: 'No painel <strong>Mypro Touch</strong>, primeiro resolva a causa da falha. Depois, acione o botao de limpeza ou reconhecimento. Nao e recomendado limpar alarme sem tratar a causa — isso pode mascarar uma condicao insegura.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/alarme azul|azul/.test(ql)) {{
        return {{ text: 'Na base Pred.IO, alarme em <strong>azul</strong> indica condicao reconhecida apos a tratativa. Ainda assim, garanta que a causa foi resolvida.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/alarme vermelho|vermelho/.test(ql)) {{
        return {{ text: 'Falha em <strong>vermelho</strong> no painel Mypro Touch indica uma falha ativa que exige atencao. A causa deve ser solucionada antes de reconhecer ou limpar.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/cut in/.test(ql)) {{
        return {{ text: 'Na base Pred.IO, <strong>SET POINT CUT IN</strong> define a pressao em que o compressor <strong>liga automaticamente</strong>.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/cut out/.test(ql)) {{
        return {{ text: 'Na base Pred.IO, <strong>SET POINT CUT OUT</strong> define a pressao em que o compressor <strong>desliga automaticamente</strong> por baixa pressao.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/set point.*1|#1/.test(ql)) {{
        return {{ text: 'Na base Pred.IO, <strong>Set Point #1</strong> e referencia para <strong>-10 °C</strong>.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/set point.*2|#2/.test(ql)) {{
        return {{ text: 'Na base Pred.IO, <strong>Set Point #2</strong> e referencia para <strong>-40 °C</strong>.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/alterar.*set|mudar.*set|como.*alterar.*set/.test(ql)) {{
        return {{ text: 'Para alterar set point no painel <strong>Mypro Touch</strong>: clique no icone de usuario, informe login e senha, clique em <em>LOG ON</em>, aguarde a luz verde e acesse os campos de set point.<br><br>⚠️ Use apenas se voce for operador autorizado. Parametros incorretos podem causar instabilidade e danos.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/alterar.*capacidade|capacidade manual/.test(ql)) {{
        return {{ text: 'Para alterar capacidade no painel <strong>Mypro Touch</strong>: acesse <em>MENU &gt; CONTROLE</em> e altere o limite desejado.<br><br>⚠️ Use apenas se voce for operador autorizado. Nao altere sem validacao tecnica.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/o que.*registrar|registrar.*falha|registrar.*quando/.test(ql)) {{
        return {{ text: 'Quando ocorrer uma falha no painel <strong>Mypro Touch</strong>, registrar:<br>&bull; Data, hora, ativo e modelo<br>&bull; Horimetro e estado do compressor<br>&bull; Alarme/falha exibida<br>&bull; Pressao de succao, descarga e oleo<br>&bull; Temperatura de descarga e do oleo<br>&bull; Corrente, capacidade e frequencia<br>&bull; Vibracao e condicoes do processo<br>&bull; Acao realizada e responsavel<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/onde.*alarme|onde.*falha|estado.*compressor|condicao atual/.test(ql)) {{
        return {{ text: 'No painel <strong>Mypro Touch</strong>, alarmes e falhas aparecem na janela <em>Alarmes/Falhas</em>. Falhas ativas em <strong>vermelho</strong>, reconhecidas em <strong>azul</strong>. Para ver se o compressor esta ligado, verifique a janela <em>Condicao Atual</em>.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/mypro touch ad|touch ad/.test(ql)) {{
        return {{ text: 'O <strong>Mypro Touch AD</strong> e uma nomenclatura utilizada na base Pred.IO para painel/interface de operacao MYCOM conforme o projeto da unidade. Deve ser tratado como variacao do painel Mypro Touch.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      return {{ text: 'O <strong>Mypro Touch</strong> e um painel/interface de operacao utilizado em unidades MYCOM, que permite visualizar o estado do compressor, alarmes, falhas, set points e comandos operacionais conforme a configuracao do sistema.<br><br>Para partida, parada, reset de alarme, set point ou capacidade: use apenas se voce for operador autorizado.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* COMUNICACAO / MONITORAMENTO REMOTO */
    if (/modbus|comunicacao.*ethernet|ethernet.*industrial|expor.*painel|painel.*internet|monitoramento.*pode|portal.*pode.*buscar|portal.*pode.*comandar|quais.*dados.*portal|comando remoto|partida remota|parada remota/.test(ql)) {{
      if (/modbus/.test(ql)) {{
        return {{ text: 'Modbus e um protocolo de comunicacao industrial que pode permitir leitura de dados do painel ou controlador. Para o Portal Pred.IO, recomenda-se iniciar com leitura e monitoramento de variaveis, sem comandos de escrita.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/ethernet/.test(ql)) {{
        return {{ text: 'Comunicacao Ethernet e uma forma de conexao em rede que pode permitir integracao entre painel, CLP, supervisorio ou portal. Deve ser feita com rede segura, permissoes e validacao tecnica.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/expor.*painel|painel.*internet/.test(ql)) {{
        return {{ text: 'Nao e recomendado expor o painel industrial diretamente na internet. O acesso deve ser protegido por rede segura, VPN, firewall, credenciais e politica de acesso.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/pode.*comandar|partida remota|parada remota|comando remoto/.test(ql)) {{
        return {{ text: 'Nao nesta fase. O Portal Pred.IO prioriza monitoramento, alertas e historico tecnico. Comandos remotos so devem ser considerados em fase futura, com autenticacao forte, intertravamentos, auditoria e validacao de seguranca operacional.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/quais.*dados|dados.*portal/.test(ql)) {{
        return {{ text: 'O Portal Pred.IO deve priorizar dados de leitura: estado do compressor, alarmes, falhas, pressoes, temperaturas, corrente, capacidade, frequencia, horimetro, niveis, vibracao e historico de eventos.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      return {{ text: 'Sim, desde que exista comunicacao configurada e segura. O Portal Pred.IO prioriza leitura de dados como estado do compressor, alarmes, pressoes, temperaturas, horimetro e variaveis operacionais disponiveis no painel Mypro Touch ou Mypro Touch AD.<br><br><strong>Fonte: Pred.IO</strong>' }};
    }}

    /* MYCOM MANUAL — temperatura de descarga por tipo, pressoes, compressor types */
    if (/mycom|chiller|sistema chiller|fluxostato|soft.starter|compressor parafuso|compressor alternativo|temperatura.*descarga|descarga.*normal|pressao.*descarga|pressao de descarga|pressao.*succao|pressao de succao|pressao.*oleo|oleo.*baix|maquina.*pressao|filtro coalescente|alinhamento|inspec.o di.ria|inspec.o semanal|inspec.o mensal|inspec.o trimestral|inspec.o semestral|inspec.o anual|5\.?000 hora|10\.?000 hora|quando trocar filtro|quando conferir|quando fazer analise|analise de oleo|amostra.*oleo|o que.*unidade compressora|diferenca.*parafuso|dados.*importantes/.test(ql)) {{
      if (/parafuso.*descarga|descarga.*parafuso|temperatura.*parafuso/.test(ql)) {{
        if (/120/.test(ql)) {{ return {{ text: 'Para compressor <strong>parafuso</strong>, a referencia Pred.IO e ate 90 °C. Uma leitura de 120 °C exige avaliacao tecnica imediata: verificar arrefecimento, pressao, oleo, filtros e carga operacional.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }}; }}
        if (/95/.test(ql)) {{ return {{ text: 'Para compressor <strong>parafuso</strong>, a referencia Pred.IO e ate 90 °C. Uma leitura de 95 °C deve ser tratada como atencao e avaliada com pressao, oleo e carga operacional.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }}; }}
        return {{ text: 'Para compressor <strong>parafuso</strong>, a referencia Pred.IO e temperatura de descarga <strong>ate 90 °C</strong>. Leituras acima devem ser avaliadas tecnicamente.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}] }};
      }}
      if (/alternativo.*descarga|descarga.*alternativo|temperatura.*alternativo/.test(ql)) {{
        return {{ text: 'Para compressor <strong>alternativo</strong>, a referencia Pred.IO e <strong>80 °C a 140 °C</strong>. A interpretacao deve considerar fluido, carga, pressao, oleo e historico operacional.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}] }};
      }}
      if (/temperatura.*descarga|descarga.*normal/.test(ql)) {{
        return {{ text: 'A temperatura de descarga depende do tipo de compressor:<br>&bull; <strong>Compressor alternativo:</strong> referencia Pred.IO de 80 °C a 140 °C<br>&bull; <strong>Compressor parafuso:</strong> referencia Pred.IO ate 90 °C<br><br>A avaliacao deve considerar fluido, carga, pressao, oleo e historico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}] }};
      }}
      if (/descarga.*alta|alta.*descarga/.test(ql)) {{
        return {{ text: 'Pressao de descarga alta pode estar relacionada a: falta de agua de arrefecimento, temperatura elevada da agua, condensador sujo, excesso de refrigerante, ar no sistema ou oleo no condensador.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/descarga.*baixa|baixa.*descarga/.test(ql)) {{
        return {{ text: 'Pressao de descarga baixa pode estar associada a: excesso de agua de arrefecimento, restriction na tubulacao, valvula de expansao muito aberta, falta de refrigerante ou vazamento interno.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}] }};
      }}
      if (/suc.*alta|alta.*suc/.test(ql)) {{
        return {{ text: 'Pressao de succao alta pode indicar: excesso de abertura da valvula de expansao, aumento de carga termica ou queda de capacidade do compressor.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}] }};
      }}
      if (/suc.*baixa|baixa.*suc/.test(ql)) {{
        return {{ text: 'Pressao de succao baixa pode estar relacionada a: valvula de expansao fechada, falta de refrigerante, oleo no evaporador, evaporador congelado ou filtro de succao obstruido.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/pressao.*oleo|oleo.*baixo|oleo.*baixa/.test(ql)) {{
        return {{ text: 'Pressao de oleo abaixo do esperado pode estar relacionada a: viscosidade reduzida, filtro obstruido, oleo deteriorado ou bomba de oleo defeituosa. Se persistir ou houver alarme, abrir chamado tecnico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado Tecnico', page:'chamados'}}] }};
      }}
      if (/diferenca.*parafuso|parafuso.*alternativo|tipo.*compressor/.test(ql)) {{
        return {{ text: 'O compressor <strong>parafuso</strong> realiza compressao por rotores. O compressor <strong>alternativo</strong> realiza compressao por pistoes e cilindros.<br><br>Temperatura de descarga de referencia Pred.IO:<br>&bull; Alternativo: 80 °C a 140 °C<br>&bull; Parafuso: ate 90 °C<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}] }};
      }}
      if (/o que.*unidade compressora|unidade compressora mycom/.test(ql)) {{
        return {{ text: 'Uma unidade compressora MYCOM e um conjunto industrial para refrigeracao ou processo, composto por compressor, motor, sistema de lubrificacao, separador de oleo, painel de controle, sensores, valvulas, instrumentos e dispositivos de seguranca.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}] }};
      }}
      var hitMycom = searchChunks(['mycom', 'chiller', 'compressor', 'oleo', 'pressao']);
      if (hitMycom) {{ return {{ text: fmtChunk(hitMycom), actions: [{{label:'📚 Abrir Manual MYCOM', page:'biblioteca'}}] }}; }}
      return {{ text: 'Encontrei o <strong>Manual Operacional MYCOM - Sistema Chiller</strong> na base Pred.IO. Consulte a Biblioteca Tecnica para detalhes.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Biblioteca Tecnica', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* META — sobre o proprio Assistente Tecnico */
    if (/assistente.*substitui|substitui.*tecnico|assistente.*pode.*decidir|assistente.*pode.*parar|pode.*decidir.*parar/.test(ql)) {{
      if (/substitui/.test(ql)) {{
        return {{ text: 'Nao. O Assistente Tecnico Pred.IO ajuda a consultar informacoes tecnicas, explicar alarmes e orientar proximos passos, mas nao substitui avaliacao tecnica presencial, laudo especializado ou decisao operacional de seguranca.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      return {{ text: 'Nao. O Assistente Tecnico Pred.IO nao executa comando na maquina. Ele pode orientar, indicar condicao de atencao ou sugerir abertura de chamado, mas a decisao de parada ou intervencao deve ser tomada por operador autorizado.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* OLEO — especificacao generica */
    if (/qual.*leo|leo.*usar|especifica.*leo|recomend.*leo|viscosidade|lubrificante recomend/.test(ql)) {{
      var spec = ctx.especificacoes && ctx.especificacoes.oleo;
      if (spec) {{
        return {{ text: 'O oleo recomendado para esta unidade e: <strong>' + spec + '</strong>.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Ver Manual', page:'biblioteca'}}] }};
      }}
      var hitOleo = searchChunks(['oleo', 'lubrificante', 'viscosidade', 'vdl', 'sintetico']);
      if (hitOleo) {{
        return {{ text: fmtChunk(hitOleo), actions: [{{label:'📚 Ver Manual Completo', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      return {{ text: 'Para selecao de oleo, consulte a Tabela de Oleos Homologados MAYEKAWA/MYCOM na Biblioteca Tecnica. O oleo MYCOM homologado atual na base Pred.IO e <strong>MYCOLD PAO</strong>.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📚 Abrir Biblioteca Tecnica', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* SSH — SUPERAQUECIMENTO DE SUCCAO */
    if (/ssh|superaquecimento|succao.*superaquec|ssh.*alto|ssh.*baixo|calcular.*ssh|formula.*ssh|retorno.*liquido|liquido.*compressor|succao.*liquido|valvula.*expansao.*ssh/.test(ql)) {{
      if (/o que.*ssh|ssh.*significa|o que.*superaquecimento/.test(ql)) {{
        return {{ text: 'SSH significa <strong>Superaquecimento de Succao</strong>. E a diferenca entre a temperatura real do gas na succao e a temperatura de saturacao correspondente a pressao de succao. Indica quanto o vapor foi aquecido apos evaporar completamente.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/por que.*ssh|ssh.*import/.test(ql)) {{
        return {{ text: 'O SSH (Superaquecimento de Succao) protege o compressor contra retorno de liquido e influencia temperatura de descarga, eficiencia e condicao operacional. SSH muito baixo indica risco de liquido na succao; SSH muito alto indica evaporador faminto ou pouca alimentacao de refrigerante.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/ssh.*alto.*descarga|descarga.*ssh.*alto/.test(ql)) {{
        return {{ text: 'Sim. SSH elevado (Superaquecimento de Succao alto) pode elevar a temperatura do gas de entrada no compressor e contribuir para aumento da temperatura de descarga, principalmente com alta taxa de compressao ou pressao de descarga elevada.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/ssh.*alto|alto.*ssh/.test(ql)) {{
        return {{ text: 'SSH alto (Superaquecimento de Succao alto) pode indicar pouca alimentacao de refrigerante, valvula de expansao muito fechada, filtro ou linha obstruida, baixa carga de refrigerante, carga termica baixa ou restricao no evaporador. Tambem pode aumentar temperatura de descarga e consumo de energia. Se persistir, abrir chamado tecnico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/ssh.*baixo|baixo.*ssh|retorno.*liquido|liquido.*compressor/.test(ql)) {{
        return {{ text: 'SSH baixo (Superaquecimento de Succao baixo) pode indicar risco de retorno de liquido para o compressor. Liquido na succao pode causar danos mecanicos, diluicao do oleo e falha no compressor. Tratar como condicao critica e abrir chamado tecnico imediatamente.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado Tecnico', page:'chamados'}}] }};
      }}
      if (/calcular.*ssh|formula.*ssh|como.*calcular.*ssh/.test(ql)) {{
        return {{ text: 'O SSH pode ser calculado pela diferenca entre a temperatura medida na linha de succao e a temperatura de saturacao correspondente a pressao de succao.<br><br><strong>Formula: SSH = Temperatura real da succao - Temperatura de saturacao da succao</strong><br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/onde.*medir.*ssh|medir.*superaquecimento/.test(ql)) {{
        return {{ text: 'Medir pressao de succao para obter a temperatura de saturacao e medir a temperatura real da linha de succao com instrumento adequado, em ponto representativo proximo ao compressor.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/o que fazer.*ssh|ssh.*o que fazer|ssh.*alto.*fazer|ssh.*baixo.*fazer/.test(ql)) {{
        return {{ text: 'Verificar carga de refrigerante, alimentacao do evaporador, valvula de expansao, filtro e linha de liquido, subresfriamento, carga termica, pressao de succao e temperatura de descarga. Se persistir, abrir chamado tecnico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/ssh.*sozinho|analisar.*ssh.*sozinho/.test(ql)) {{
        return {{ text: 'Nao. SSH deve ser analisado junto com pressao de succao, pressao de descarga, temperatura de descarga, subresfriamento, carga termica, condicao do evaporador, fluido refrigerante, analise de oleo e historico operacional.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      return {{ text: 'SSH e o <strong>Superaquecimento de Succao</strong>: diferenca entre a temperatura real do gas na succao e a temperatura de saturacao correspondente. SSH alto pode indicar pouca alimentacao; SSH baixo pode indicar risco de retorno de liquido. Em ambos, avaliar pressao, valvula, carga, temperatura e abrir chamado tecnico se persistir.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* MOTOR ELETRICO */
    if (/motor.*ruido|ruido.*motor|motor.*aquecendo|motor.*quente|motor.*corrente|motor.*vibra|vibra.*motor|motor.*inversor|inversor.*motor|motor.*barulho|barulho.*motor|o que verificar.*motor|verificar.*motor|motor.*inspecao/.test(ql)) {{
      if (/ruido.*motor|motor.*ruido|o que.*ruido.*motor|ruido.*anormal.*motor/.test(ql)) {{
        return {{ text: 'Ruido anormal no motor pode estar relacionado a rolamento com desgaste, falta ou excesso de lubrificacao, desalinhamento, desbalanceamento, folga mecanica, base frouxa, problema no acoplamento, atrito interno, ventilador danificado ou anomalia eletrica. Recomenda-se analise de vibracao, inspecao de temperatura, inspecao visual e correlacao com corrente eletrica antes de qualquer decisao de troca.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/motor.*aquecendo|motor.*aquec|aquecimento.*motor|motor.*quente/.test(ql)) {{
        return {{ text: 'Aquecimento no motor pode estar relacionado a sobrecarga, ventilacao deficiente, sujeira nas aletas, rolamento com falha, lubrificacao inadequada, desalinhamento, tensao eletrica irregular, corrente elevada, harmonicos, problema no inversor ou ambiente com temperatura elevada. Verificar corrente, tensao, temperatura, vibracao, ventilacao e condicao dos rolamentos.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/corrente.*alta.*motor|motor.*corrente.*alta/.test(ql)) {{
        return {{ text: 'Corrente alta no motor pode estar relacionada a sobrecarga, travamento parcial, rolamento danificado, desalinhamento, acoplamento forcado, compressor com carga elevada, pressao de descarga alta ou problema eletrico. Avaliar corrente, vibracao, temperatura e condicao operacional.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/motor.*inversor|inversor.*motor|inversor.*frequencia/.test(ql)) {{
        return {{ text: 'Motores acionados por inversor de frequencia podem apresentar variacoes de rotacao, harmonicos, aquecimento adicional, corrente distorcida e possiveis efeitos nos rolamentos. A analise deve considerar frequencia de operacao, carga, temperatura, corrente, vibracao e historico do inversor.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/o que verificar.*motor|verificar.*motor.*inspecao|inspecao.*motor/.test(ql)) {{
        return {{ text: 'Verificar temperatura, corrente, tensao, ruido, vibracao, ventilacao, limpeza, estado dos rolamentos, acoplamento, base, cabos, terminais, aterramento, condicao do inversor e historico de alarmes. Se houver alteracao de tendencia, abrir chamado ou antecipar analise preditiva.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      return {{ text: 'Problemas em motor eletrico devem ser investigados correlacionando ruido, corrente, temperatura, vibracao, lubrificacao, alinhamento, base e acoplamento. Recomenda-se analise de vibracao e, em caso de duvida critica, abrir chamado tecnico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* ROLAMENTO */
    if (/rolamento|mancal|graxa.*rolamento|rolamento.*graxa|ruido.*rolamento|rolamento.*ruido|rolamento.*troca|troca.*rolamento|rolamento.*quente|rolamento.*falhando|falha.*rolamento|rolamento.*sinais|rolamento.*lubrifica|lubrifica.*rolamento|excesso.*graxa|falta.*graxa|graxa.*errada|graxa.*incompativel|misturar.*graxa/.test(ql)) {{
      if (/sinais.*falha.*rolamento|falha.*rolamento.*sinais|o que.*indica.*rolamento/.test(ql)) {{
        return {{ text: 'Sinais comuns de possivel falha de rolamento incluem ruido anormal, vibracao elevada, aumento de temperatura, alteracao de tendencia, cheiro de aquecimento, graxa escurecida, picos em alta frequencia, impactos no espectro de vibracao e recorrencia de alarmes. A confirmacao deve ser feita por analise de vibracao, termografia e inspecao tecnica.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/rolamento.*troca.*ruido|ruido.*indica.*troca|troca.*automatica.*rolamento/.test(ql)) {{
        return {{ text: 'Nao necessariamente. Ruido no rolamento e um sinal de alerta, mas nao deve gerar troca automatica. A decisao deve ser baseada em analise de vibracao, tendencia historica, temperatura, lubrificacao, condicao operacional, termografia e inspecao tecnica. Se o ruido for acompanhado de vibracao alta ou aquecimento, abrir chamado tecnico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/lubrificar.*rolamento.*ruido|posso.*lubrificar.*ruido|ruido.*lubrificar/.test(ql)) {{
        return {{ text: 'Nao automaticamente. Lubrificar apenas porque ha ruido pode mascarar uma falha ou piorar o problema se houver excesso de graxa. Verificar plano de lubrificacao, tipo de graxa, quantidade, intervalo, temperatura, vibracao e condicao do rolamento.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/excesso.*graxa|graxa.*demais|graxa.*excesso/.test(ql)) {{
        return {{ text: 'Sim. Excesso de graxa pode causar aumento de temperatura, agitacao do lubrificante, vazamento, esforco adicional e degradacao da graxa. A lubrificacao deve seguir quantidade e periodicidade corretas.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/falta.*graxa|graxa.*pouca|pouca.*graxa/.test(ql)) {{
        return {{ text: 'Sim. Falta de lubrificacao aumenta atrito, temperatura, desgaste e pode gerar ruido, vibracao e falha prematura. Correlacionar com temperatura, vibracao e historico de lubrificacao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/graxa.*errada|graxa.*incompativel|misturar.*graxa|graxa.*incorreta/.test(ql)) {{
        return {{ text: 'Sim. Graxa incompativel ou inadequada pode alterar viscosidade, separacao de oleo, resistencia a temperatura, estabilidade e protecao contra desgaste. Evite misturar graxas sem validacao tecnica.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/rolamento.*inicial.*falha|falha.*inicial.*rolamento|como saber.*rolamento.*falhando/.test(ql)) {{
        return {{ text: 'Falhas iniciais de rolamento podem aparecer primeiro em alta frequencia, envelope, ultrassom, aumento discreto de temperatura ou pequenas alteracoes de tendencia. A analise de vibracao periodica detecta esses sinais antes da falha funcional.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/quando.*trocar.*rolamento|troca.*rolamento.*tempo|troca.*rolamento.*horim/.test(ql)) {{
        return {{ text: 'Na filosofia Pred.IO, a troca de rolamento deve ser preferencialmente por condicao, considerando analise de vibracao, termografia, ruido, temperatura, historico de lubrificacao, criticidade do ativo e tendencia. Tempo e calendario orientam inspecao, mas nao devem ser o unico criterio de troca.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/ruido.*metalico.*rolamento|rolamento.*metalico|metalico.*rolamento/.test(ql)) {{
        return {{ text: 'Ruido metalico em rolamento deve ser tratado como condicao de atencao. Pode indicar falha avancada, falta de lubrificacao, dano interno, folga, contaminacao ou contato indevido. Recomenda-se abrir chamado tecnico e realizar analise de vibracao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado Tecnico', page:'chamados'}}] }};
      }}
      if (/rolamento.*quente|rolamento.*aquecido|rolamento.*aquecendo|aquecimento.*rolamento/.test(ql)) {{
        return {{ text: 'Rolamento aquecido e sinal de atencao. Pode vir de excesso de graxa, falta de graxa, desalinhamento, sobrecarga, corrente eletrica, ventilacao deficiente ou falha interna. Considerar temperatura, vibracao, ruido e tendencia. Nao trocar automaticamente sem diagnostico tecnico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      return {{ text: 'Problemas em rolamento devem ser avaliados com analise de vibracao, termografia, historico de lubrificacao e inspecao tecnica. A recomendacao Pred.IO e nao decidir troca sem diagnostico. Em caso de ruido forte, aquecimento rapido ou vibracao crescente, abrir chamado tecnico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* ANALISE DE VIBRACAO */
    if (/analise.*vibracao|vibracao.*analise|espectro.*vibr|vibr.*espectro|tendencia.*vibr|vibr.*tendencia|o que.*envelope|envelope.*vibr|vibracao.*evita|desbalanceament|desalinhament|ressonanci|alinhamento.*laser|alinhar.*laser|base.*frouxa|quando.*antecipar.*vibracao|apos.*alinhar.*vibracao|apos.*lubrificar.*vibracao/.test(ql)) {{
      if (/por que.*analise.*vibracao|para que.*vibracao|vibracao.*serve/.test(ql)) {{
        return {{ text: 'A analise de vibracao detecta falhas mecanicas em estagio inicial: desalinhamento, desbalanceamento, folga, falhas de rolamento, problemas de acoplamento, base frouxa e ressonancia. Ajuda a planejar manutencao antes da quebra e evita troca desnecessaria de pecas.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}] }};
      }}
      if (/vibracao.*evita.*parada|vibracao.*previne/.test(ql)) {{
        return {{ text: 'A analise de vibracao reduz o risco de parada inesperada, pois permite acompanhar tendencia e detectar sinais de degradacao antes da falha funcional. Nao elimina todos os riscos, mas melhora a confiabilidade e o planejamento da manutencao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}] }};
      }}
      if (/quando.*antecipar.*vibracao|antecipar.*analise.*vibracao/.test(ql)) {{
        return {{ text: 'Antecipar analise de vibracao quando houver ruido anormal, aumento de temperatura, vibracao perceptivel, alarme recorrente, falha de rolamento suspeita, alteracao de corrente, intervencao recente, troca de acoplamento, alinhamento recente, lubrificacao anormal ou mudanca de operacao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/o que.*espectro|espectro.*mostra|analise.*espectral/.test(ql)) {{
        return {{ text: 'A analise espectral separa as frequencias presentes na vibracao. Isso identifica padroes de desbalanceamento, desalinhamento, folga, engrenamento, falhas de rolamento, rotacao, harmonicos e outros defeitos.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/o que.*envelope|envelope.*vibracao/.test(ql)) {{
        return {{ text: 'Envelope e uma tecnica para destacar impactos de alta frequencia, muito util para detectar falhas iniciais em rolamentos. Ela identifica defeitos antes que aparecam claramente na vibracao global.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/tendencia.*vibracao|o que.*tendencia.*vibr/.test(ql)) {{
        return {{ text: 'Tendencia e o acompanhamento da evolucao da vibracao ao longo do tempo. Mais importante do que uma leitura isolada e observar se a vibracao esta aumentando, estabilizando ou reduzindo apos manutencao.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/frequencia.*analise.*vibracao|de quanto.*vibracao/.test(ql)) {{
        return {{ text: 'No plano Pred.IO, a analise de vibracao pode ser realizada a cada 2 meses como rotina preditiva. A frequencia pode ser antecipada para ativos criticos, maquinas com historico de falha, alarmes recorrentes, vibracao elevada ou operacao severa.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}] }};
      }}
      if (/apos.*alinhar.*vibracao|vibracao.*apos.*alinhamento|depois.*alinhar.*vibracao/.test(ql)) {{
        return {{ text: 'Sim. Apos alinhamento, a analise de vibracao confirma se a condicao melhorou e se ainda existem outras causas, como desbalanceamento, folga, base frouxa, rolamento ou ressonancia.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/apos.*lubrificar.*vibracao|vibracao.*apos.*lubrificacao|depois.*lubrificar.*vibracao/.test(ql)) {{
        return {{ text: 'Sim. O acompanhamento apos lubrificacao ajuda a confirmar se houve melhora. Se a vibracao ou ruido permanecer, pode haver falha interna, excesso de graxa, graxa inadequada, desalinhamento ou outro problema.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/vibracao.*substitui.*oleo|oleo.*substitui.*vibracao/.test(ql)) {{
        return {{ text: 'Nao. A analise de vibracao e a analise de oleo se complementam. A vibracao avalia condicao mecanica dinamica; a analise de oleo avalia lubrificante, contaminacao e desgaste interno. A melhor decisao vem da correlacao entre vibracao, oleo, termografia e operacao.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/vibracao.*substitui.*termografia|termografia.*substitui.*vibracao/.test(ql)) {{
        return {{ text: 'Nao. A vibracao identifica comportamento dinamico e mecanico; a termografia identifica aquecimento anormal. Em motores, rolamentos e paineis, as duas tecnicas juntas aumentam a confiabilidade do diagnostico.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/desalinhamento.*sinal|sinal.*desalinhamento|o que.*indica.*desalinhamento/.test(ql)) {{
        return {{ text: 'Sinais comuns de desalinhamento incluem vibracao elevada, aquecimento em mancais e rolamentos, desgaste em acoplamento, ruido, falhas recorrentes de rolamento e aumento de carga no motor. Confirmacao por analise de vibracao e alinhamento a laser.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/desbalanceamento.*causa|causa.*desbalanceamento|o que.*desbalanceamento/.test(ql)) {{
        return {{ text: 'Desbalanceamento pode ser causado por acumulo de sujeira, desgaste, perda de material, montagem incorreta, polia ou rotor danificado, ventilador quebrado ou alteracao no conjunto rotativo. Avaliar por analise de vibracao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/base.*frouxa.*vibra|vibra.*base.*frouxa|fundacao.*vibra/.test(ql)) {{
        return {{ text: 'Sim. Base frouxa, fundacao inadequada, parafusos soltos ou pe manco podem amplificar vibracao e gerar falhas recorrentes. Recomenda-se inspecao mecanica, reaperto controlado e analise de vibracao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/o que.*ressonancia|ressonancia.*causa/.test(ql)) {{
        return {{ text: 'Ressonancia ocorre quando uma frequencia de excitacao coincide com uma frequencia natural da estrutura ou maquina, amplificando vibracao mesmo sem falha direta no componente. A analise de vibracao ajuda a identificar essa condicao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/quando.*alinhamento.*laser|alinhamento.*laser.*quando|quando.*alinhar/.test(ql)) {{
        return {{ text: 'Alinhamento a laser deve ser realizado apos montagem, intervencao em motor ou compressor, troca de acoplamento, manutencao em base, vibracao por desalinhamento ou conforme plano de manutencao. Para unidade MYCOM, conferencia de alinhamento aparece como rotina associada a inspecao semestral ou 5.000 horas.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      return {{ text: 'A analise de vibracao e ferramenta preditiva essencial para detectar falhas em estagio inicial, acompanhar tendencias e evitar paradas inesperadas. No plano Pred.IO, e prevista como rotina a cada 2 meses e deve ser antecipada em caso de ruido, alarme, intervencao ou alteracao operacional.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* TERMOGRAFIA */
    if (/termografia|imagem.*termica|termica.*imagem|infravermelho|ponto.*quente|quente.*ponto|delta.*t|o que.*termografia|por que.*termografia|quando.*termografia|termografia.*motor|termografia.*rolamento|termografia.*painel|termografia.*compressor/.test(ql)) {{
      if (/o que.*termografia/.test(ql)) {{
        return {{ text: 'Termografia e uma tecnica preditiva que usa imagem termica para identificar aquecimento anormal em componentes eletricos, mecanicos e operacionais. Detecta pontos quentes, sobrecarga, mau contato, atrito, falha de rolamento, problema de lubrificacao, desequilibrio eletrico e anomalias termicas antes de uma falha funcional.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/por que.*termografia|termografia.*serve|termografia.*ajuda.*por/.test(ql)) {{
        return {{ text: 'A termografia identifica aquecimentos anormais que podem indicar falha eletrica, mau contato, sobrecarga, rolamento aquecido, lubrificacao inadequada, desalinhamento, problema em painel, conexao frouxa ou componente em degradacao. Permite agir antes de parada inesperada ou dano maior.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}] }};
      }}
      if (/termografia.*substitui.*vibracao|vibracao.*substitui.*termografia/.test(ql)) {{
        return {{ text: 'Nao. A termografia identifica aquecimento anormal; a analise de vibracao identifica comportamento dinamico e mecanico como desalinhamento, desbalanceamento, folgas e falhas de rolamento. As duas tecnicas se complementam.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/termografia.*substitui.*oleo|oleo.*substitui.*termografia/.test(ql)) {{
        return {{ text: 'Nao. A termografia avalia temperatura e aquecimento anormal. A analise de oleo avalia condicao do lubrificante, contaminacao, particulas, agua, oxidacao e metais de desgaste. Em unidade compressora, as duas analises devem ser correlacionadas.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/quando.*termografia|frequencia.*termografia|de quanto.*termografia/.test(ql)) {{
        return {{ text: 'No plano Pred.IO, a termografia pode ser realizada a cada 4 meses como rotina preditiva. Tambem deve ser antecipada quando houver aquecimento anormal, corrente elevada, ruido, vibracao, alarme recorrente, falha eletrica, cheiro de aquecimento ou alteracao operacional.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}] }};
      }}
      if (/termografia.*motor|motor.*termografia/.test(ql)) {{
        return {{ text: 'A termografia pode mostrar aquecimento anormal no corpo do motor, rolamentos, mancais, tampa, ventilacao, caixa de ligacao, cabos e conexoes. Correlacionar com corrente eletrica, carga, vibracao, limpeza, ventilacao e historico operacional.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/termografia.*rolamento|rolamento.*termografia/.test(ql)) {{
        return {{ text: 'Rolamento quente na termografia e sinal de atencao, mas a decisao de troca deve considerar analise de vibracao, ruido, lubrificacao, tendencia de temperatura, carga, alinhamento e criticidade do ativo. Nao indicar troca automaticamente apenas pela termografia.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/termografia.*painel|painel.*termografia/.test(ql)) {{
        return {{ text: 'A termografia verifica aquecimento anormal em conexoes, barramentos, disjuntores, contatores, fusibles, bornes, cabos, inversores, soft-starters, reles e componentes eletricos. Pontos quentes podem indicar mau contato, sobrecarga, desequilibrio de fase ou componente em degradacao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/ponto.*quente.*conexao|conexao.*ponto.*quente|termografia.*conexao/.test(ql)) {{
        return {{ text: 'Ponto quente em conexao eletrica pode indicar mau contato, aperto inadequado, oxidacao, sobrecarga ou desequilibrio. Deve ser tratado com prioridade conforme intensidade, carga, criticidade e tendencia. A intervencao deve ser feita por equipe autorizada.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/inversor.*termografia|soft.starter.*termografia|termografia.*inversor|termografia.*soft.starter/.test(ql)) {{
        return {{ text: 'Inversores e soft-starters geram calor em operacao, mas aquecimento excessivo pode indicar sobrecarga, ventilacao obstruida, filtros sujos, ambiente quente ou falha interna. A avaliacao deve considerar carga, ventilacao, corrente, alarmes e historico termico. Intervencao apenas por equipe autorizada.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/termografia.*compressor|compressor.*termografia|onde.*termografia.*unidade/.test(ql)) {{
        return {{ text: 'Na unidade compressora, a termografia pode ser aplicada em motor, mancais, rolamentos, acoplamento, compressor, sistema de oleo, bomba de oleo, filtros, tubulacoes, painel eletrico, inversor, soft-starter, conexoes e pontos com suspeita de aquecimento anormal.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/termografia.*ssh|ssh.*termografia|succao.*termografia|termografia.*succao/.test(ql)) {{
        return {{ text: 'A termografia pode apoiar a inspecao termica da linha de succao, mas o SSH (Superaquecimento de Succao) deve ser calculado pela diferenca entre a temperatura real de succao e a temperatura de saturacao correspondente a pressao de succao. A termografia e apoio, nao substituto do calculo.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      if (/o que.*delta.*t|delta.*t.*termografia|delta t/.test(ql)) {{
        return {{ text: '<strong>Delta T</strong> e a diferenca de temperatura entre dois pontos comparaveis, como uma fase e outra, um rolamento e outro, ou o componente analisado e uma referencia semelhante. Ajuda a identificar anomalias termicas relativas na termografia.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/erro.*termografia|o que.*gera.*erro.*termografia/.test(ql)) {{
        return {{ text: 'Erros na termografia podem ocorrer por emissividade incorreta, reflexo de superficies metalicas, foco inadequado, distancia, angulo de medicao, vento, carga baixa, equipamento fora de operacao, sujeira, isolamento termico ou interpretacao sem comparacao adequada.<br><br><strong>Fonte: Pred.IO</strong>' }};
      }}
      if (/relatorio.*termografia|o que.*relatorio.*termografia/.test(ql)) {{
        return {{ text: 'Um relatorio de termografia deve conter ativo, componente, data, condicao operacional, carga e corrente quando aplicavel, imagem termica, imagem visual, temperatura medida, referencia comparativa, Delta T, criticidade, provavel causa, recomendacao tecnica e prazo sugerido para acao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📋 Ver Relatorios', page:'relatorios'}}] }};
      }}
      if (/termografia.*ponto.*quente.*o que|o que fazer.*termografia/.test(ql)) {{
        return {{ text: 'Registrar imagem, temperatura, localizacao, condicao operacional, carga, corrente e historico. Classificar criticidade, correlacionar com vibracao, eletrica ou oleo conforme o caso, e abrir chamado tecnico se houver risco ou tendencia de piora.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      return {{ text: 'A termografia identifica aquecimento anormal em componentes eletricos, mecanicos e operacionais. No plano Pred.IO, e prevista como rotina preditiva a cada 4 meses e deve ser antecipada em caso de aquecimento, alarme, corrente elevada ou alteracao operacional. Sempre correlacionar com carga, corrente, vibracao, oleo e historico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* MANUTENCAO */
    if (/manuten|plano|preventiva|preditiva|vibra|termografia|hor.metro|filtro|inspec|lubrifica|pr.xima|proxima|vencimento|analise de|analise d/.test(ql)) {{
      if (/como.*vibra.*ajuda|vibra.*ajuda/.test(ql)) {{
        return {{ text: 'A analise de vibracao ajuda a identificar tendencias de desalinhamento, desbalanceamento, folgas, falhas em rolamentos, problemas de acoplamento, base frouxa e alteracoes mecanicas. No Portal Pred.IO, e prevista como rotina preditiva a cada 2 meses.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}] }};
      }}
      if (/como.*termografia.*ajuda|termografia.*ajuda/.test(ql)) {{
        return {{ text: 'A termografia ajuda a identificar aquecimento anormal em motor, paineis, conexoes eletricas, rolamentos, mancais e componentes criticos. No Portal Pred.IO, e prevista como rotina preditiva a cada 4 meses.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}] }};
      }}
      var mans = ctx.manutencoes || [];
      if (!mans.length) {{
        return {{ text: 'Nao encontrei planos de manutencao cadastrados. Recomendo abrir um chamado tecnico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      var itens = mans.map(function(m) {{
        var prazo = m.vencimento_data || (m.vencimento_horas ? m.vencimento_horas + ' horas' : 'a definir');
        return '&bull; ' + m.acao + ' &mdash; ' + prazo;
      }}).join('<br>');
      return {{ text: '<strong>📅 Proximas manutencoes programadas:</strong><br><br>' + itens + '<br><br>Acesse o plano completo para ver checklists e intervalos detalhados.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📅 Ver Plano de Manutencao', page:'manutencao'}}] }};
    }}

    /* RELATORIOS */
    if (/relat|laudo|resultado|publicado/.test(ql)) {{
      var rels = ctx.relatorios || [];
      if (!rels.length) {{
        return {{ text: 'Nenhum relatorio tecnico publicado ainda para sua operacao.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📋 Ver Relatorios', page:'relatorios'}}] }};
      }}
      var rlist = rels.map(function(r) {{ return '&bull; ' + r.titulo + ' &mdash; ' + r.data; }}).join('<br>');
      return {{ text: '<strong>📋 Relatorios tecnicos recentes:</strong><br><br>' + rlist + '<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'📋 Ver Relatorios Tecnicos', page:'relatorios'}}] }};
    }}

    /* DOCUMENTOS / MANUAIS */
    if (/manual|datasheet|documento|especifica|cat.logo|biblioteca|pdf|procedimento|guia|instru/.test(ql)) {{
      var docs = ctx.documentos || [];
      if (!docs.length) {{
        return {{ text: 'Nao encontrei manual tecnico cadastrado. Recomendo solicitar o documento pela area de Chamados Tecnicos.', actions: [{{label:'🔧 Abrir Chamado', page:'chamados'}}, {{label:'📚 Abrir Biblioteca', page:'biblioteca'}}] }};
      }}
      var hitDoc = searchChunks([]);
      if (hitDoc) {{
        return {{ text: fmtChunk(hitDoc), actions: [{{label:'📚 Abrir Biblioteca Tecnica', page:'biblioteca'}}] }};
      }}
      var qn2 = norm(ql);
      var words2 = qn2.split(/ +/).filter(function(w) {{ return w.length > 2; }});
      var matched = docs.filter(function(d) {{
        var hay = norm([d.titulo, d.modelo, d.fabricante, d.tipo_documento, d.palavras_chave, d.resumo, d.ativo].join(' '));
        return words2.some(function(w) {{ return hay.indexOf(w) >= 0; }});
      }});
      var show = matched.length ? matched : docs;
      var prefix2 = matched.length
        ? 'Encontrei ' + (matched.length === 1 ? 'o documento tecnico vinculado ao seu ativo' : matched.length + ' documentos disponiveis') + ':'
        : 'Documentacao tecnica disponivel na Biblioteca:';
      var dlist = show.map(function(d) {{
        var lnk = (d.arquivo_url && d.arquivo_url.indexOf('/mock/') < 0)
          ? ' <a href="' + d.arquivo_url + '" target="_blank" style="color:#2563EB;font-size:.75rem;font-weight:600;">📂 Abrir</a>'
          : '';
        return '&bull; <strong>' + d.titulo + '</strong>'
          + (d.tipo_documento ? ' <span style="font-size:.75rem;color:#64748B;">(' + d.tipo_documento + ')</span>' : '')
          + (d.modelo ? ' &mdash; ' + d.modelo : '')
          + lnk;
      }}).join('<br>');
      return {{ text: '<strong>📚 ' + prefix2 + '</strong><br><br>' + dlist + '<br><br>Acesse a Biblioteca Tecnica para visualizar e baixar.', actions: [{{label:'📚 Abrir Biblioteca Tecnica', page:'biblioteca'}}] }};
    }}

    /* STATUS ATIVO — score, atencao, critico */
    if (/status|condi|sa.de|score|cr.tico|aten|bomba|compressor|motor|ativo|equipamento|falha|alarme|sensor/.test(ql)) {{
      if (/score.*saude|saude.*ativo|o que.*score|o que e score/.test(ql)) {{
        return {{ text: 'Score de saude e uma representacao resumida da condicao do ativo, calculada a partir de dados como vibracao, oleo, termografia, alarmes, chamados, manutencao, historico operacional e criticidade. Nao substitui laudo tecnico, mas ajuda a priorizar acompanhamento.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'⚙️ Ver Ativos', page:'ativos'}}] }};
      }}
      if (/em atencao|o que.*atencao|atencao significa/.test(ql)) {{
        return {{ text: 'Ativo em <strong>atencao</strong> indica que ha sinais de acompanhamento necessario, como tendencia de piora, manutencao proxima, alerta recorrente, anomalia em oleo, vibracao ou temperatura. Nao significa parada imediata, mas exige monitoramento e analise.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'⚙️ Ver Ativos', page:'ativos'}}] }};
      }}
      if (/ativo.*critico|o que.*critico|critico significa/.test(ql)) {{
        return {{ text: 'Ativo <strong>critico</strong> indica condicao com maior prioridade tecnica: risco de falha, componente com score baixo, alarme critico ou tendencia acelerada de degradacao. Recomenda-se abertura ou acompanhamento de chamado tecnico.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'⚙️ Ver Ativos', page:'ativos'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
      }}
      var ativos = ctx.ativos || [];
      if (!ativos.length) {{
        return {{ text: 'Nenhum ativo monitorado cadastrado ainda para sua operacao.', actions: [{{label:'⚙️ Ver Ativos', page:'ativos'}}] }};
      }}
      var av = ativos[0];
      var criticos = (av.componentes || []).filter(function(c) {{ return c.status === 'Critico' || c.status === 'Crítico'; }});
      var txt = '<strong>⚙️ Status dos ativos monitorados:</strong><br><br>A <strong>' + av.nome + '</strong> esta com status <strong>' + av.status + '</strong> e score de saude <strong>' + av.score + '/100</strong>.';
      if (criticos.length) {{
        txt += '<br><br>Componente(s) critico(s): ' + criticos.map(function(c){{return '<strong>'+c.nome+'</strong>';}}).join(', ') + '.';
      }}
      return {{ text: txt, actions: [{{label:'⚙️ Ver Ativos Monitorados', page:'ativos'}}] }};
    }}

    /* CHAMADOS */
    if (/chamado|abrir chamado|solicita|atendimento|suporte|problema|defeito|urgente|t.cnico|quando abrir/.test(ql)) {{
      var chams = ctx.chamados || [];
      var txt2 = 'Voce pode abrir ou acompanhar solicitacoes pela area de Chamados Tecnicos.';
      if (chams.length) {{ txt2 += ' Chamado em aberto: <strong>' + chams[0].titulo + '</strong> (' + chams[0].status + ').'; }}
      return {{ text: '<strong>🔧 Chamados Tecnicos:</strong><br><br>' + txt2, actions: [{{label:'🔧 Abrir Chamados Tecnicos', page:'chamados'}}] }};
    }}

    /* ALERTAS */
    if (/alerta|aviso|notifica|ponto de aten/.test(ql)) {{
      var als = ctx.alertas || [];
      if (!als.length) {{
        return {{ text: 'Nenhum alerta ativo no momento para sua operacao.', actions: [{{label:'🔔 Ver Alertas', page:'alertas'}}] }};
      }}
      var alist = als.map(function(a){{return '&bull; '+a.titulo+' ('+a.prioridade+')';}}).join('<br>');
      return {{ text: '<strong>🔔 Alertas ativos:</strong><br><br>' + alist, actions: [{{label:'🔔 Ver Alertas', page:'alertas'}}] }};
    }}

    /* Busca generica em chunks antes do fallback */
    var hitGeral = searchChunks([]);
    if (hitGeral) {{
      return {{ text: fmtChunk(hitGeral), actions: [{{label:'📚 Ver Manual', page:'biblioteca'}}, {{label:'🔧 Abrir Chamado', page:'chamados'}}] }};
    }}

    /* Fallback */
    return {{ text: 'Nao encontrei informacao suficiente na base Pred.IO para responder com seguranca. Recomendo abrir um chamado tecnico para avaliacao da equipe Pred.IO.<br><br><strong>Fonte: Pred.IO</strong>', actions: [{{label:'🔧 Abrir Chamado Tecnico', page:'chamados'}}] }};
  }}

  fab.addEventListener('click', predToggle);
  pd.getElementById('pred-min-btn').addEventListener('click', predMin);
  pd.getElementById('pred-close-btn').addEventListener('click', predClose);
  pd.getElementById('pred-send').addEventListener('click', predSend);
  pd.getElementById('pred-input').addEventListener('keydown', function(e){{
    if(e.key==='Enter') predSend();
  }});
  pd.querySelectorAll('.pred-chip').forEach(function(chip){{
    chip.addEventListener('click', function(){{ predQuick(this.dataset.q); }});
  }});
  try{{if(localStorage.getItem('pred_open')==='1')setTimeout(predOpen,150);}}catch(e){{}}
}})();
</script>
</body></html>"""

    html = html_top + html_ctx + html_bot
    _comp.html(html, height=0)


def sv_badge(label: str, cfg: dict) -> str:
    """Badge colorido usando dict de configuração de status ou prioridade."""
    bg, tc = cfg.get(label.lower(), ("#94A3B8", "#fff"))
    return (
        f"<span style='background:{bg};color:{tc};-webkit-text-fill-color:{tc};"
        f"font-size:0.72rem;font-weight:700;padding:3px 12px;border-radius:20px;"
        f"white-space:nowrap;'>{label}</span>"
    )


def sv_metric_card(icon: str, title: str, value, color: str = COLOR_BLUE,
                   subtitle: str = "") -> None:
    """Card de métrica premium para dashboard de supervisão."""
    st.markdown(
        f"<div style='background:#fff;border:1px solid #E2E8F0;border-radius:14px;"
        f"padding:1.25rem 1.5rem;box-shadow:0 1px 4px rgba(15,31,61,0.06);"
        f"border-top:4px solid {color};'>"
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;'>"
        f"<span style='font-size:1.5rem;'>{icon}</span>"
        f"<span style='color:#64748B;font-size:0.75rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:0.06em;'>{title}</span>"
        f"</div>"
        f"<p style='color:{COLOR_NAVY};font-size:2rem;font-weight:800;margin:0;'>{value}</p>"
        + (f"<p style='color:#94A3B8;font-size:0.75rem;margin:4px 0 0;'>{subtitle}</p>"
           if subtitle else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def sv_page_header(title: str, subtitle: str = "", back_label: str = "",
                   back_view: str = "") -> None:
    """Cabeçalho de página da supervisão com botão voltar opcional."""
    if back_label and back_view:
        if st.button(f"← {back_label}", key="sv_back_btn"):
            st.session_state["sv_view"] = back_view
            st.session_state.pop("sv_chamado_id", None)
            st.rerun()
    st.markdown(
        f"<h2 style='color:{COLOR_NAVY};margin:0.25rem 0 0;font-size:1.5rem;"
        f"font-weight:800;'>{title}</h2>"
        + (f"<p style='color:#64748B;margin:4px 0 0;font-size:0.88rem;'>{subtitle}</p>"
           if subtitle else ""),
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:0.75rem 0 1rem;'/>",
        unsafe_allow_html=True,
    )
