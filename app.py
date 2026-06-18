import base64
import unicodedata
import streamlit as st
import extra_streamlit_components as stx
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# ─── Constants ────────────────────────────────────────────────────────────────

SHEET_ID = "1cyDz6nuZ9ro7Inq-DNg9OH9d7GNn17WHZSIikkQ6hOA"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Brand palette extracted from logo
COLOR_NAVY  = "#1B2A6B"
COLOR_BLUE  = "#1565C0"
COLOR_CYAN  = "#29B6F6"
COLOR_BG    = "#F5F7FA"
COLOR_CARD  = "#FFFFFF"
COLOR_BORDER= "#DDE3F0"

# Tipos de laudo — ordem de exibição na Central de Laudos
# Chave: versão sem acentos em minúsculas; Valor: rótulo exibido
TIPOS_LAUDOS = [
    ("ordem de servico",       "Ordem de Serviço"),
    ("analise de vibracao",    "Análise de Vibração"),
    ("termografia",            "Termografia"),
    ("analise de oleo",        "Análise de Óleo"),
    ("alinhamento a laser",    "Alinhamento a Laser"),
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sem_acento(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


def get_status_cfg(raw: str) -> dict:
    """Aceita qualquer variação: 'bom', 'verde', 'atenção', 'amarelo', 'crítico', 'vermelho'."""
    s = _sem_acento(raw.strip())
    if s in ("bom", "verde"):
        return {"key": "Bom",     "label": "Bom",     "dot": "#22c55e", "bg": "#f0fdf4", "border": "#86efac"}
    if s in ("atencao", "amarelo"):
        return {"key": "Atenção", "label": "Atenção", "dot": "#f59e0b", "bg": "#fffbeb", "border": "#fcd34d"}
    if s in ("critico", "vermelho"):
        return {"key": "Crítico", "label": "Crítico", "dot": "#ef4444", "bg": "#fef2f2", "border": "#fca5a5"}
    return {"key": raw, "label": raw, "dot": "#94a3b8", "bg": "#f8fafc", "border": "#cbd5e1"}


def logo_base64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""


def inject_global_css():
    st.markdown(
        f"""
        <style>
        /* ── Page background ── */
        .stApp {{ background-color: {COLOR_BG}; }}

        /* ── Hide Streamlit chrome ── */
        #MainMenu, footer, header {{ visibility: hidden; }}

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {{
            background: {COLOR_NAVY} !important;
        }}
        [data-testid="stSidebar"] * {{
            color: #ffffff !important;
        }}
        [data-testid="stSidebar"] input {{
            background: rgba(255,255,255,0.92) !important;
            border: 1px solid rgba(255,255,255,0.4) !important;
            color: #000000 !important;
            border-radius: 6px;
        }}
        [data-testid="stSidebar"] input::placeholder {{
            color: #888888 !important;
        }}
        /* Olho do campo senha — todas as variações de seletor do Streamlit */
        [data-testid="stSidebar"] div[data-baseweb="input"] button,
        [data-testid="stSidebar"] div[data-baseweb="input"] button svg,
        [data-testid="stSidebar"] div[data-baseweb="input"] button path,
        [data-testid="stSidebar"] [data-testid="textInputRootElement"] button,
        [data-testid="stSidebar"] [data-testid="textInputRootElement"] button svg,
        [data-testid="stSidebar"] [data-testid="textInputRootElement"] button path {{
            color: #000000 !important;
            fill: #000000 !important;
            stroke: #000000 !important;
        }}
        /* Botão Entrar */
        [data-testid="stBaseButton-secondaryFormSubmit"],
        [data-testid="stSidebar"] .stButton > button {{
            background: {COLOR_CYAN} !important;
            color: #000000 !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 0.5rem 1rem !important;
            width: 100% !important;
        }}
        [data-testid="stBaseButton-secondaryFormSubmit"]:hover,
        [data-testid="stSidebar"] .stButton > button:hover {{
            background: #7dd3fc !important;
        }}

        /* ── Metric cards ── */
        [data-testid="stMetric"] {{
            background: {COLOR_CARD};
            border: 1px solid {COLOR_BORDER};
            border-radius: 10px;
            padding: 1rem 1.2rem;
        }}
        [data-testid="stMetricLabel"] {{ color: {COLOR_NAVY} !important; font-size: 0.8rem; }}
        [data-testid="stMetricValue"] {{ color: {COLOR_BLUE} !important; font-size: 1.8rem; font-weight: 700; }}

        /* ── Section headings ── */
        h1, h2, h3 {{ color: {COLOR_NAVY} !important; }}

        /* ── Divider ── */
        hr {{ border-color: {COLOR_BORDER}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ─── Google Sheets ─────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    import json, os
    try:
        creds = None

        # 1) Streamlit Cloud → st.secrets
        try:
            if "gcp_service_account" in st.secrets:
                info = dict(st.secrets["gcp_service_account"])
                info["private_key"] = info["private_key"].replace("\\n", "\n")
                creds = ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)
        except Exception:
            pass

        # 2a) Variável base64 (mais segura para env vars)
        if creds is None and os.environ.get("GCP_CREDENTIALS_B64"):
            raw = base64.b64decode(os.environ["GCP_CREDENTIALS_B64"]).decode("utf-8")
            info = json.loads(raw)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)

        # 2b) Variável JSON direta
        if creds is None and os.environ.get("GCP_CREDENTIALS_JSON"):
            info = json.loads(os.environ["GCP_CREDENTIALS_JSON"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)

        # 3) Secret File do Render (/etc/secrets/credentials.json)
        if creds is None and os.path.exists("/etc/secrets/credentials.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                "/etc/secrets/credentials.json", SCOPE
            )

        # 4) Arquivo local (desenvolvimento)
        if creds is None and os.path.exists("credentials.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)

        if creds is None:
            st.error("Credenciais não encontradas. Configure o Secret File no Render.")
            st.stop()

        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Planilha não encontrada. Verifique as permissões da service account.")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        st.stop()


def load_sheet(spreadsheet, tab_name: str) -> pd.DataFrame:
    try:
        ws = spreadsheet.worksheet(tab_name)
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        # Normalize column names: strip whitespace and title-case
        df.columns = [c.strip().title() for c in df.columns]
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Aba '{tab_name}' não encontrada na planilha.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar aba '{tab_name}': {e}")
        return pd.DataFrame()

# ─── Authentication ────────────────────────────────────────────────────────────

def authenticate(spreadsheet, email: str, password: str):
    df = load_sheet(spreadsheet, "Clientes")
    if df.empty:
        return None, None

    required = {"Empresa", "Email", "Senha", "Telefone"}
    if not required.issubset(df.columns):
        st.error(f"A aba 'Clientes' precisa das colunas: {required}")
        return None, None

    match = df[
        (df["Email"].str.strip().str.lower() == email.strip().lower()) &
        (df["Senha"].astype(str).str.strip() == password.strip())
    ]
    if match.empty:
        return None, None

    row = match.iloc[0]
    return str(row["Empresa"]).strip(), str(row["Telefone"]).strip()


def render_sidebar_login(spreadsheet, logo_b64: str):
    with st.sidebar:
        if logo_b64:
            st.markdown(
                f"<div style='text-align:center;padding:1.2rem 0 0.5rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' style='width:160px;border-radius:8px;'/>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            "<p style='text-align:center;font-size:0.8rem;opacity:0.7;margin-bottom:1.2rem;'>"
            "Análises Preditivas para a Indústria</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown("### Acesso ao Portal")

        with st.form("login_form"):
            email    = st.text_input("E-mail", placeholder="seu@email.com")
            password = st.text_input("Senha", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

    if submitted:
        if not email or not password:
            st.sidebar.warning("Preencha e-mail e senha.")
            return

        with st.spinner("Verificando credenciais…"):
            empresa, telefone = authenticate(spreadsheet, email, password)

        if empresa:
            st.session_state.update(logged_in=True, empresa=empresa, telefone=telefone)
            cm = stx.CookieManager(key="set_cookie")
            cm.set("predio_empresa",  empresa,  max_age=7*24*3600)
            cm.set("predio_telefone", telefone, max_age=7*24*3600)
            st.rerun()
        else:
            st.sidebar.error("E-mail ou senha incorretos.")


def render_sidebar_user(logo_b64: str):
    with st.sidebar:
        if logo_b64:
            st.markdown(
                f"<div style='text-align:center;padding:1.2rem 0 0.5rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' style='width:140px;border-radius:8px;'/>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("---")
        st.markdown(
            f"<p style='font-size:0.85rem;opacity:0.8;'>Bem-vindo,</p>"
            f"<p style='font-weight:700;font-size:1rem;margin-top:-8px;'>{st.session_state['empresa']}</p>",
            unsafe_allow_html=True,
        )
        if st.session_state.get("telefone"):
            st.markdown(
                f"<p style='font-size:0.8rem;opacity:0.6;'>📞 {st.session_state['telefone']}</p>",
                unsafe_allow_html=True,
            )
        st.markdown("---")
        if st.button("Sair", use_container_width=True):
            cm = stx.CookieManager(key="del_cookie")
            cm.delete("predio_empresa")
            cm.delete("predio_telefone")
            for key in ("logged_in", "empresa", "telefone"):
                st.session_state.pop(key, None)
            st.rerun()

# ─── Landing page ──────────────────────────────────────────────────────────────

def render_landing(logo_b64: str):
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
        if logo_b64:
            st.markdown(
                f"<div style='text-align:center;margin-bottom:1rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' style='width:280px;'/>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<h2 style='text-align:center;color:{COLOR_NAVY};margin-bottom:0.2rem;'>"
            f"Portal do Cliente</h2>"
            f"<p style='text-align:center;color:#64748b;font-size:0.95rem;'>"
            f"Monitoramento de Confiabilidade Industrial</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align:center;margin-top:2rem;color:#94a3b8;font-size:0.8rem;'>"
            f"Faça login na barra lateral para acessar seu painel.</p>",
            unsafe_allow_html=True,
        )

# ─── Asset card ───────────────────────────────────────────────────────────────

def render_asset_card(row: pd.Series):
    cfg  = get_status_cfg(str(row.get("Status", "")))
    tag  = str(row.get("Tag", "")).strip()
    equip= str(row.get("Equipamentos", "")).strip()
    ns   = str(row.get("Ns", "")).strip()
    det  = str(row.get("Detalhes", "")).strip()
    link = str(row.get("Link_Documento", "")).strip()
    tipo = str(row.get("Tipo", "")).strip()
    data = str(row.get("Data", "")).strip()

    dot, bg, border, label = cfg["dot"], cfg["bg"], cfg["border"], cfg["label"]
    badge_text = "#000" if dot == "#f59e0b" else "#fff"

    # Equipamento + número de série
    equip_display = equip
    if ns and ns.lower() not in ("", "nan"):
        equip_display += f" &nbsp;<span style='color:#94a3b8;font-size:0.8rem;'>Nº {ns}</span>"

    meta_parts = []
    if tipo and tipo.lower() not in ("", "nan"):
        meta_parts.append(f"📋 {tipo}")
    if data and data.lower() not in ("", "nan"):
        meta_parts.append(f"📅 {data}")
    meta_html = (
        f"<div style='margin:6px 0 4px;font-size:0.8rem;color:#64748b;'>"
        + "  &nbsp;|&nbsp;  ".join(meta_parts)
        + "</div>"
    ) if meta_parts else ""

    st.markdown(
        f"""<div style="background-color:{bg};border:1px solid {border};
                border-left:6px solid {dot};border-radius:10px;
                padding:16px 20px;margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
                <div>
                    <span style="font-size:1.05rem;font-weight:700;color:{COLOR_NAVY};">{tag}</span>
                    <span style="margin-left:8px;font-size:0.9rem;color:#475569;">— {equip_display}</span>
                </div>
                <span style="display:inline-block;background-color:{dot};color:{badge_text};
                             -webkit-text-fill-color:{badge_text};
                             font-size:0.78rem;font-weight:700;padding:4px 12px;border-radius:20px;">{label}</span>
            </div>
            {meta_html}
            <p style="margin:6px 0 0;color:#475569;font-size:0.87rem;line-height:1.6;">{det}</p>
        </div>""",
        unsafe_allow_html=True,
    )
    if link and link.lower() not in ("", "nan", "none"):
        st.link_button(f"📄 Ver Laudo — {tag}", link, use_container_width=False)


# ─── Resumo lateral ───────────────────────────────────────────────────────────

def render_summary(counts: dict):
    rows_html = ""
    for key, dot, icon in [("Bom", "#22c55e", "🟢"), ("Atenção", "#f59e0b", "🟡"), ("Crítico", "#ef4444", "🔴")]:
        n = counts.get(key, 0)
        rows_html += (
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:10px 14px;margin-bottom:8px;background:#fff;"
            f"border-left:4px solid {dot};border-radius:8px;'>"
            f"<span style='font-size:0.9rem;color:{COLOR_NAVY};font-weight:600;'>{icon} {key}</span>"
            f"<span style='font-size:1.4rem;font-weight:800;color:{dot};'>{n}</span>"
            f"</div>"
        )
    st.markdown(
        f"<div style='background:{COLOR_BG};border:1px solid {COLOR_BORDER};border-radius:10px;padding:16px;'>"
        f"<p style='font-size:0.75rem;font-weight:700;color:#94a3b8;letter-spacing:.08em;"
        f"margin:0 0 12px;text-transform:uppercase;'>Resumo de Status</p>"
        f"{rows_html}</div>",
        unsafe_allow_html=True,
    )


# ─── Dashboard ─────────────────────────────────────────────────────────────────

def render_dashboard(spreadsheet, empresa: str):
    st.markdown(
        f"<h1 style='color:{COLOR_NAVY};margin-bottom:0;'>Dashboard de Saúde de Ativos</h1>"
        f"<p style='color:#64748b;margin-top:4px;'>Empresa: <strong>{empresa}</strong></p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    df = load_sheet(spreadsheet, "Ativos")
    if df.empty:
        st.info("Nenhum dado encontrado na aba 'Ativos'.")
        return

    required = {"Empresa", "Tag", "Equipamentos", "Status", "Detalhes", "Link_Documento"}
    if not required.issubset(df.columns):
        st.error(f"A aba 'Ativos' precisa das colunas: {required}")
        return

    ativos = df[df["Empresa"].str.strip().str.lower() == empresa.lower()].copy()
    if ativos.empty:
        st.info("Nenhum ativo cadastrado para sua empresa.")
        return

    # Normaliza status para chave canônica
    ativos["_status_key"] = ativos["Status"].astype(str).apply(lambda v: get_status_cfg(v)["key"])

    # Prioridade: Crítico (0) > Atenção (1) > Bom (2)
    PRIORITY = {"Crítico": 0, "Atenção": 1, "Bom": 2}
    ativos["_priority"] = ativos["_status_key"].map(lambda k: PRIORITY.get(k, 99))

    has_ns = "Ns" in ativos.columns
    group_cols = ["Tag", "Ns"] if has_ns else ["Tag"]

    # ── Métricas: pior status por ativo único ──────────────────────────────────
    worst_per_asset = (
        ativos.sort_values("_priority")
        .groupby(group_cols, sort=False)["_status_key"]
        .first()
    )
    counts = worst_per_asset.value_counts().to_dict()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de Ativos", len(worst_per_asset))
    c2.metric("🟢 Bom",         counts.get("Bom",     0))
    c3.metric("🟡 Atenção",     counts.get("Atenção",  0))
    c4.metric("🔴 Crítico",     counts.get("Crítico", 0))

    # ── Faróis: todos os cards, agrupados por TAG + NS ─────────────────────────
    st.markdown(f"<h3 style='color:{COLOR_NAVY};margin-top:1.5rem;'>Faróis de Condição</h3>",
                unsafe_allow_html=True)

    # Ordenar grupos pelo pior status do ativo
    group_order = (
        ativos.sort_values("_priority")
        .groupby(group_cols, sort=False)
        .first()
        .reset_index()
    )
    group_order["_sort"] = pd.Categorical(
        group_order["_status_key"], categories=["Crítico", "Atenção", "Bom"], ordered=True
    )
    group_order = group_order.sort_values("_sort")[group_cols]

    col_cards, col_summary = st.columns([3, 1])
    with col_cards:
        for _, g in group_order.iterrows():
            # Filtrar todas as linhas deste ativo
            mask = ativos["Tag"].astype(str).str.strip() == str(g["Tag"]).strip()
            if has_ns:
                mask &= ativos["Ns"].astype(str).str.strip() == str(g["Ns"]).strip()
            grupo = ativos[mask].sort_values("_priority")

            # Cabeçalho do grupo
            primeiro = grupo.iloc[0]
            tag   = str(primeiro.get("Tag", "")).strip()
            equip = str(primeiro.get("Equipamentos", "")).strip()
            ns    = str(primeiro.get("Ns", "")).strip() if has_ns else ""
            pior  = get_status_cfg(str(primeiro.get("_status_key", "")))
            ns_html = f"&nbsp;<span style='color:#94a3b8;font-size:0.8rem;'>Nº {ns}</span>" if ns and ns.lower() not in ("", "nan") else ""

            st.markdown(
                f"<div style='margin:22px 0 6px;padding-bottom:8px;"
                f"border-bottom:2px solid {pior['dot']};'>"
                f"<span style='font-size:1.05rem;font-weight:800;color:{COLOR_NAVY};'>{tag}</span>"
                f"<span style='margin-left:8px;font-size:0.9rem;color:#475569;'>— {equip}</span>"
                f"{ns_html}</div>",
                unsafe_allow_html=True,
            )

            for _, row in grupo.iterrows():
                render_asset_card(row)

    with col_summary:
        render_summary(counts)

    # ── Central de Laudos: todos os relatórios, por tipo, ordenados por data ───
    laudos = ativos[
        ~ativos["Link_Documento"].astype(str).str.strip().str.lower().isin(["", "nan", "none"])
    ].copy()

    if laudos.empty:
        return

    if "Data" in laudos.columns:
        laudos["_data_dt"] = pd.to_datetime(
            laudos["Data"].astype(str).str.strip(), dayfirst=True, errors="coerce"
        )
        laudos = laudos.sort_values("_data_dt", ascending=False)

    st.markdown("---")
    st.markdown(f"<h3 style='color:{COLOR_NAVY};'>Central de Laudos</h3>", unsafe_allow_html=True)

    has_tipo = "Tipo" in laudos.columns
    rendered_idx = set()

    def _laudo_btn(row):
        """Label do botão: TAG · NS · data"""
        tag  = str(row.get("Tag", "")).strip()
        ns   = str(row.get("Ns", "")).strip() if has_ns else ""
        data = str(row.get("Data", "")).strip()
        parts = [tag]
        if ns and ns.lower() not in ("", "nan"):
            parts.append(f"Nº {ns}")
        label = " · ".join(parts)
        if data and data.lower() not in ("", "nan"):
            label += f" · {data}"
        return f"📄 {label}"

    if has_tipo:
        for tipo_key, tipo_label in TIPOS_LAUDOS:
            grupo = laudos[
                laudos["Tipo"].astype(str).apply(lambda v: _sem_acento(v.strip())) == tipo_key
            ]
            if grupo.empty:
                continue
            st.markdown(
                f"<h4 style='color:{COLOR_BLUE};margin-top:1rem;margin-bottom:6px;'>{tipo_label}</h4>",
                unsafe_allow_html=True,
            )
            cols = st.columns(3)
            for i, (idx, row) in enumerate(grupo.iterrows()):
                cols[i % 3].link_button(_laudo_btn(row), str(row.get("Link_Documento", "")), use_container_width=True)
                rendered_idx.add(idx)

        outros = laudos[~laudos.index.isin(rendered_idx)]
        if not outros.empty:
            st.markdown(
                f"<h4 style='color:{COLOR_BLUE};margin-top:1rem;margin-bottom:6px;'>Outros</h4>",
                unsafe_allow_html=True,
            )
            cols = st.columns(3)
            for i, (_, row) in enumerate(outros.iterrows()):
                cols[i % 3].link_button(_laudo_btn(row), str(row.get("Link_Documento", "")), use_container_width=True)
    else:
        cols = st.columns(3)
        for i, (_, row) in enumerate(laudos.iterrows()):
            cols[i % 3].link_button(_laudo_btn(row), str(row.get("Link_Documento", "")), use_container_width=True)

# ─── Entry point ───────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Portal do Cliente — Pred.IO",
        page_icon="⚙️",
        layout="wide",
    )

    inject_global_css()

    # ── Restaurar sessão a partir de cookie ────────────────────────────────────
    cm = stx.CookieManager(key="read_cookie")
    if not st.session_state.get("logged_in"):
        empresa_cookie = cm.get("predio_empresa")
        if empresa_cookie:
            st.session_state["logged_in"]  = True
            st.session_state["empresa"]    = empresa_cookie
            st.session_state["telefone"]   = cm.get("predio_telefone") or ""

    logo_b64    = logo_base64("logo.jpg")
    spreadsheet = get_spreadsheet()

    if not st.session_state.get("logged_in"):
        render_landing(logo_b64)
        render_sidebar_login(spreadsheet, logo_b64)
    else:
        render_sidebar_user(logo_b64)
        render_dashboard(spreadsheet, st.session_state["empresa"])


if __name__ == "__main__":
    main()
