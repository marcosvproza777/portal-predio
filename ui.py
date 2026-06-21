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
    #MainMenu, footer, header {{ visibility: hidden; }}
    [data-testid="stSidebarCollapseButton"] {{ display: none !important; }}

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

    /* ── Botão secundário (Sair) ── */
    [data-testid="stBaseButton-secondary"] {{
        background: rgba(255,255,255,0.10) !important;
        color: #fff !important; -webkit-text-fill-color: #fff !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        border-radius: 8px !important; font-weight: 600 !important;
    }}
    [data-testid="stBaseButton-secondary"]:hover {{
        background: rgba(239,68,68,0.75) !important;
        border-color: transparent !important;
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
    with st.sidebar:
        # Logo
        if logo_b64:
            st.markdown(
                f"<div style='text-align:center;padding:1.5rem 0 1rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' "
                f"style='width:130px;border-radius:10px;"
                f"box-shadow:0 4px 16px rgba(0,0,0,0.30);'/></div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.12);margin:0 0 1rem;'/>",
            unsafe_allow_html=True,
        )

        # Avatar + nome da empresa
        iniciais = "".join(w[0].upper() for w in empresa.split()[:2]) if empresa else "?"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;padding:0 0.5rem 1rem;'>"
            f"<div style='width:42px;height:42px;border-radius:50%;"
            f"background:linear-gradient(135deg,#38BDF8,#2563EB);"
            f"display:flex;align-items:center;justify-content:center;"
            f"font-weight:800;font-size:1rem;color:#fff;flex-shrink:0;'>{iniciais}</div>"
            f"<div>"
            f"<p style='margin:0;font-size:0.7rem;opacity:0.6;'>Empresa</p>"
            f"<p style='margin:0;font-weight:700;font-size:0.95rem;line-height:1.2;'>{empresa}</p>"
            f"{'<p style=\"margin:2px 0 0;font-size:0.72rem;opacity:0.6;\">📞 ' + telefone + '</p>' if telefone else ''}"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.12);margin:0 0 1rem;'/>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<p style='font-size:0.68rem;opacity:0.4;text-align:center;margin:0 0 0.75rem;'>"
            "Portal do Cliente · Pred.IO</p>",
            unsafe_allow_html=True,
        )

        if st.button("⬅️  Sair da conta", use_container_width=True, key="nav_logout"):
            logout()
            st.rerun()


# Alias para compatibilidade
def render_sidebar_nav(logo_b64: str, empresa: str, telefone: str,
                       current_page: str = "") -> None:
    render_sidebar(logo_b64, empresa, telefone)


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

# ── Supervisão — constantes e componentes ─────────────────────────────────────

SV_NAV_ITEMS = [
    ("dashboard",        "🏠", "Dashboard"),
    ("chamados",         "🔧", "Chamados"),
    ("clientes",         "👥", "Clientes"),
]

SV_NAV_SOON = [
    ("relatorios_sv",    "📊", "Relatórios"),
    ("configuracoes",    "⚙️",  "Configurações"),
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
            is_active = sv_view == key or (key == "chamados" and sv_view == "chamado_detalhe")
            bg = "rgba(56,189,248,0.15)" if is_active else "transparent"
            border = "2px solid #38BDF8" if is_active else "2px solid transparent"
            txt_color = "#38BDF8" if is_active else "#CBD5E1"
            st.markdown(
                f"<div style='background:{bg};border-left:{border};border-radius:0 8px 8px 0;"
                f"padding:8px 12px;margin-bottom:2px;cursor:pointer;'>"
                f"<span style='color:{txt_color};font-size:0.88rem;font-weight:600;'>"
                f"{icon} &nbsp; {label}</span></div>",
                unsafe_allow_html=True,
            )
            if st.button(label, key=f"sv_nav_{key}", use_container_width=True,
                         label_visibility="collapsed"):
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
