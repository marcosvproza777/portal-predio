"""Componentes de UI compartilhados — cores, CSS, logo, navegação."""
import base64
import streamlit as st

# ── Paleta ────────────────────────────────────────────────────────────────────
COLOR_NAVY   = "#1B2A6B"
COLOR_BLUE   = "#1565C0"
COLOR_CYAN   = "#29B6F6"
COLOR_BG     = "#F5F7FA"
COLOR_CARD   = "#FFFFFF"
COLOR_BORDER = "#DDE3F0"

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
    .stApp {{ background-color: {COLOR_BG}; }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    [data-testid="stSidebarCollapseButton"] {{ display: none !important; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{ background: {COLOR_NAVY} !important; }}
    [data-testid="stSidebar"] * {{ color: #ffffff !important; }}
    [data-testid="stSidebar"] input {{
        background: rgba(255,255,255,0.92) !important;
        color: #000 !important; border-radius: 6px;
    }}

    /* Botão primário (Entrar, Enviar…) */
    [data-testid="stBaseButton-secondaryFormSubmit"],
    [data-testid="stBaseButton-primary"] {{
        background: {COLOR_CYAN} !important; color: #000 !important;
        font-weight: 700 !important; border: none !important;
        border-radius: 6px !important;
    }}
    [data-testid="stBaseButton-secondaryFormSubmit"]:hover,
    [data-testid="stBaseButton-primary"]:hover {{
        background: #7dd3fc !important;
    }}

    /* Botão secundário (Sair) */
    [data-testid="stBaseButton-secondary"] {{
        background: {COLOR_NAVY} !important; color: #fff !important;
        border: none !important; border-radius: 6px !important; font-weight: 600 !important;
    }}
    [data-testid="stBaseButton-secondary"]:hover {{ background: {COLOR_BLUE} !important; }}

    /* Metric cards */
    [data-testid="stMetric"] {{
        background: {COLOR_CARD}; border: 1px solid {COLOR_BORDER};
        border-radius: 10px; padding: 1rem 1.2rem;
    }}
    [data-testid="stMetricLabel"] {{ color: {COLOR_NAVY} !important; font-size: 0.8rem; }}
    [data-testid="stMetricValue"] {{ color: {COLOR_BLUE} !important; font-size: 1.8rem; font-weight: 700; }}

    h1, h2, h3 {{ color: {COLOR_NAVY} !important; }}
    hr {{ border-color: {COLOR_BORDER}; }}

    /* Nav pills */
    .nav-pill {{
        display: inline-block; padding: 8px 18px; margin: 3px 4px;
        border-radius: 20px; cursor: pointer; font-size: 0.88rem;
        font-weight: 600; border: 1.5px solid {COLOR_BORDER};
        background: {COLOR_CARD}; color: {COLOR_NAVY};
        text-decoration: none;
    }}
    .nav-pill.active {{
        background: {COLOR_NAVY}; color: #fff; border-color: {COLOR_NAVY};
    }}
    </style>""", unsafe_allow_html=True)


def inject_login_bg(bg_b64: str) -> None:
    if not bg_b64:
        return
    st.markdown(f"""<style>
    .stApp {{
        background-image: url('data:image/jpeg;base64,{bg_b64}') !important;
        background-size: cover !important; background-position: center !important;
        background-attachment: fixed !important;
    }}
    .stApp::before {{
        content: ''; position: fixed; inset: 0;
        background: rgba(245,247,250,0.80); pointer-events: none; z-index: 0;
    }}
    section.main > div {{ position: relative; z-index: 1; }}
    </style>""", unsafe_allow_html=True)


def render_sidebar_nav(logo_b64: str, empresa: str, telefone: str,
                       current_page: str) -> None:
    """Sidebar com logo, info do usuário e navegação."""
    from auth import logout

    nav_items = [
        ("dashboard",   "🏠  Dashboard"),
        ("farois",      "🚦  Faróis de Condição"),
        ("relatorios",  "📁  Meus Relatórios"),
        ("assistente",  "🤖  Assistente Técnico"),
        ("chamados",    "🔧  Chamados Técnicos"),
    ]
    with st.sidebar:
        if logo_b64:
            st.markdown(
                f"<div style='text-align:center;padding:1rem 0 0.5rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' "
                f"style='width:140px;border-radius:8px;'/></div>",
                unsafe_allow_html=True,
            )
        st.markdown("---")
        st.markdown(
            f"<p style='font-size:0.82rem;opacity:0.75;margin:0;'>Bem-vindo,</p>"
            f"<p style='font-weight:700;font-size:0.95rem;margin:2px 0 4px;'>{empresa}</p>",
            unsafe_allow_html=True,
        )
        if telefone:
            st.markdown(
                f"<p style='font-size:0.75rem;opacity:0.6;'>📞 {telefone}</p>",
                unsafe_allow_html=True,
            )
        st.markdown("---")
        for page_key, label in nav_items:
            is_active = current_page == page_key
            bg = "rgba(255,255,255,0.18)" if is_active else "transparent"
            border = "2px solid rgba(255,255,255,0.5)" if is_active else "2px solid transparent"
            if st.button(label, use_container_width=True, key=f"nav_{page_key}"):
                st.session_state["page"] = page_key
                st.rerun()
        st.markdown("---")
        if st.button("⬅️  Sair", use_container_width=True, key="nav_logout"):
            logout()
            st.rerun()


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"<h1 style='color:{COLOR_NAVY};margin-bottom:0;'>{title}</h1>"
        + (f"<p style='color:#64748b;margin-top:4px;'>{subtitle}</p>" if subtitle else ""),
        unsafe_allow_html=True,
    )
    st.markdown("---")


def empty_state(message: str) -> None:
    st.markdown(
        f"<div style='text-align:center;padding:3rem 1rem;color:#94a3b8;'>"
        f"<div style='font-size:2.5rem;margin-bottom:0.8rem;'>📭</div>"
        f"<p style='font-size:1rem;'>{message}</p></div>",
        unsafe_allow_html=True,
    )


def badge(label: str, color: str, text_color: str = "#fff") -> str:
    return (f"<span style='background:{color};color:{text_color};"
            f"-webkit-text-fill-color:{text_color};font-size:0.75rem;"
            f"font-weight:700;padding:3px 12px;border-radius:20px;'>{label}</span>")


STATUS_CFG = {
    "aberto":      ("#f59e0b", "#000"),
    "em andamento":("#3b82f6", "#fff"),
    "resolvido":   ("#22c55e", "#fff"),
    "fechado":     ("#94a3b8", "#fff"),
}

PRIORIDADE_CFG = {
    "baixa":    ("#22c55e", "#fff"),
    "média":    ("#f59e0b", "#000"),
    "alta":     ("#ef4444", "#fff"),
    "crítica":  ("#7c3aed", "#fff"),
}
