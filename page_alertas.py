"""Central de Alertas — portal do cliente."""
import streamlit as st
from auth import current_client_id
from ui import (page_header, empty_state, status_badge, COLOR_NAVY, COLOR_CARD, COLOR_BORDER,
                COLOR_MUTED, COLOR_WARNING, COLOR_DANGER, COLOR_NEUTRAL)
from gut import calculate_gut, gut_acao_recomendada, GUT_DISCLAIMER

# ── Configuração visual por tipo ───────────────────────────────────────────────
_TIPO_CFG = {
    "manutencao_proxima": {"icone": "🔧", "label": "Manutenção próxima do vencimento"},
    "manutencao_vencida": {"icone": "🚨", "label": "Manutenção vencida"},
    "ativo_critico":      {"icone": "🔴", "label": "Ativo crítico"},
    "ativo_atencao":      {"icone": "🟡", "label": "Ativo em atenção"},
    "relatorio_novo":     {"icone": "📁", "label": "Novo relatório publicado"},
    "chamado_respondido": {"icone": "💬", "label": "Chamado respondido pela Pred.IO"},
    "aguardando_cliente": {"icone": "⏳", "label": "Aguardando retorno do cliente"},
    "recomendacao":       {"icone": "💡", "label": "Recomendação técnica"},
    "termografia":        {"icone": "🌡️", "label": "Termografia programada"},
}

# ── Configuração visual por prioridade — alinhada ao Design System ────────────
_PRIO_CFG = {
    "Alta":  {
        "bg": "#FFF7ED", "border": "#FED7AA", "dot": "#F97316", "text": "#9A3412",
        "badge_bg": "#F97316", "badge_tc": "#fff",
    },
    "Média": {
        "bg": "#FFFBEB", "border": "#FCD34D", "dot": COLOR_WARNING, "text": "#92400E",
        "badge_bg": COLOR_WARNING, "badge_tc": "#000",
    },
    "Baixa": {
        "bg": "#F0F9FF", "border": "#BAE6FD", "dot": "#38BDF8", "text": "#0C4A6E",
        "badge_bg": "#38BDF8", "badge_tc": "#fff",
    },
    "Lido":  {
        "bg": "#F8FAFC", "border": "#E2E8F0", "dot": COLOR_NEUTRAL, "text": "#64748B",
        "badge_bg": COLOR_NEUTRAL, "badge_tc": "#fff",
    },
}

_PRIO_ORDER = {"Alta": 0, "Média": 1, "Baixa": 2}


def _load_alertas(client_id: str) -> list:
    """Alertas reais do cliente (aba AlertasSV, criados pela Supervisão).
    SEGURANÇA: get_alertas_sv(client_id) já filtra pelo cliente da sessão."""
    if not client_id:
        return []
    try:
        from sheets import get_alertas_sv
        df = get_alertas_sv(client_id)
        if df.empty:
            return []
        alertas = []
        for _, row in df.iterrows():
            ativo_id = str(row.get("Ativo_Id", "")).strip()
            alertas.append({
                "id":            str(row.get("Id", "")).strip(),
                "client_id":     client_id,
                "titulo":        str(row.get("Titulo", "")).strip(),
                "descricao":     str(row.get("Descricao", "")).strip(),
                "prioridade":    str(row.get("Prioridade", "Média")).strip(),
                "data":          str(row.get("Criado_Em", "")).strip(),
                "ativo_id":      ativo_id,
                "link_page":     "ativos" if ativo_id else "",
                "gut_gravidade": row.get("Gut_Gravidade"),
                "gut_urgencia":  row.get("Gut_Urgencia"),
                "gut_tendencia": row.get("Gut_Tendencia"),
            })
        return alertas
    except Exception:
        return []


@st.cache_data(ttl=15, show_spinner=False)
def get_unread_count(client_id: str = "") -> int:
    """Contagem de alertas com prioridade GUT Crítica — usada no badge do
    topnav ("Alertas · N"). Não há rastreio de lido/não-lido em AlertasSV;
    o badge sinaliza o que precisa de atenção agora (GUT Crítica).
    Cache curto (15s) porque antes recalculava do zero em toda navegação —
    chave inclui client_id, sem risco de misturar clientes."""
    alertas = _load_alertas(client_id)
    criticos = 0
    for a in alertas:
        r = calculate_gut(a.get("gut_gravidade"), a.get("gut_urgencia"), a.get("gut_tendencia"))
        if r and r["prioridade"] == "Crítica":
            criticos += 1
    return criticos


# ── Render principal ───────────────────────────────────────────────────────────

def render() -> None:
    page_header(
        "🔔 Central de Alertas",
        "Acompanhe notificações importantes sobre ativos, relatórios, manutenções e chamados.",
    )

    client_id = current_client_id()
    alertas   = _load_alertas(client_id)

    if not alertas:
        empty_state("Nenhum alerta no momento.", icon="🔕")
        return

    st.caption(f"ℹ️ {GUT_DISCLAIMER}")

    # ── Resumo rápido ─────────────────────────────────────────────────────────
    for a in alertas:
        r = calculate_gut(a.get("gut_gravidade"), a.get("gut_urgencia"), a.get("gut_tendencia"))
        a["_gut"] = r

    criticos = sum(1 for a in alertas if a["_gut"] and a["_gut"]["prioridade"] == "Crítica")
    altos    = sum(1 for a in alertas if a["_gut"] and a["_gut"]["prioridade"] == "Alta")

    c1, c2, c3 = st.columns(3)
    for col, val, label, cor in [
        (c1, len(alertas), "Total de alertas",  COLOR_NAVY),
        (c2, criticos,     "Críticos (GUT)",    COLOR_DANGER),
        (c3, altos,        "Alta prioridade (GUT)", "#F97316"),
    ]:
        with col:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-top:3px solid {cor};border-radius:10px;padding:0.85rem 1rem;'>"
                f"<p style='font-size:0.68rem;color:{COLOR_MUTED};text-transform:uppercase;"
                f"letter-spacing:.06em;margin:0 0 4px;'>{label}</p>"
                f"<p style='font-size:1.6rem;font-weight:900;color:{cor};"
                f"-webkit-text-fill-color:{cor};margin:0;'>{val}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Filtros — por prioridade GUT ─────────────────────────────────────────
    if "alertas_filtro" not in st.session_state:
        st.session_state["alertas_filtro"] = "todos"

    filtro = st.session_state["alertas_filtro"]

    FILTROS = [
        ("todos",     "Todos"),
        ("Crítica",   "Crítica"),
        ("Alta",      "Alta"),
        ("Moderada",  "Moderada"),
        ("Baixa",     "Baixa"),
    ]

    cols_f = st.columns(len(FILTROS))
    for col, (key, label) in zip(cols_f, FILTROS):
        cnt   = len(_aplicar_filtro(alertas, key))
        label_btn = f"{label} ({cnt})" if cnt > 0 else label
        with col:
            if st.button(
                label_btn,
                key=f"filtro_alerta_{key}",
                use_container_width=True,
                type="primary" if filtro == key else "secondary",
            ):
                st.session_state["alertas_filtro"] = key
                st.rerun()

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    # ── Lista filtrada ─────────────────────────────────────────────────────────
    filtrados = _aplicar_filtro(alertas, filtro)

    if not filtrados:
        empty_state("Nenhum alerta nesta categoria.", icon="🔕")
        return

    # Ordena: prioridade GUT (Crítica→Alta→Moderada→Baixa→sem GUT), depois prioridade do alerta
    _GUT_RANK = {"Crítica": 0, "Alta": 1, "Moderada": 2, "Baixa": 3}
    filtrados = sorted(
        filtrados,
        key=lambda a: (
            _GUT_RANK.get(a["_gut"]["prioridade"], 4) if a["_gut"] else 4,
            _PRIO_ORDER.get(a.get("prioridade", "Baixa"), 3),
        ),
    )

    for alerta in filtrados:
        _render_alerta_card(alerta)


def _aplicar_filtro(alertas: list, filtro: str) -> list:
    if filtro == "todos":
        return alertas
    return [a for a in alertas if a.get("_gut") and a["_gut"]["prioridade"] == filtro]


def _render_alerta_card(alerta: dict) -> None:
    prio = alerta.get("prioridade", "Baixa")
    pcfg = _PRIO_CFG.get(prio, _PRIO_CFG["Baixa"])
    gut_r = alerta.get("_gut") or calculate_gut(
        alerta.get("gut_gravidade"), alerta.get("gut_urgencia"), alerta.get("gut_tendencia"))

    titulo    = alerta.get("titulo", "") or "Alerta"
    descricao = alerta.get("descricao", "")
    data      = alerta.get("data", "")
    link_page = alerta.get("link_page", "")

    dot_html = (
        f"<span style='width:8px;height:8px;border-radius:50%;flex-shrink:0;"
        f"display:inline-block;background:{pcfg['dot']};margin-right:5px;'></span>"
    )

    prio_badge = (
        f"<span style='background:{pcfg['badge_bg']};color:{pcfg['badge_tc']};"
        f"-webkit-text-fill-color:{pcfg['badge_tc']};"
        f"font-size:0.67rem;font-weight:700;padding:2px 8px;border-radius:10px;'>"
        f"{prio}</span>"
    )
    gut_badge = (
        f"{status_badge(gut_r['prioridade'], 'gut')}"
        f"<span style='font-size:0.62rem;color:{COLOR_MUTED};margin-left:2px;'>GUT {gut_r['score']}</span>"
        if gut_r else ""
    )

    st.markdown(
        f"<div style='background:{pcfg['bg']};border:1px solid {pcfg['border']};"
        f"border-left:4px solid {pcfg['dot']};border-radius:12px;"
        f"padding:1rem 1.25rem;margin-bottom:0.6rem;'>"
        f"<div style='display:flex;align-items:flex-start;gap:12px;'>"
        f"<span style='font-size:1.5rem;flex-shrink:0;margin-top:1px;'>🔔</span>"
        f"<div style='flex:1;min-width:0;'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:flex-start;gap:8px;flex-wrap:wrap;margin-bottom:3px;'>"
        f"<div style='display:flex;align-items:center;'>"
        f"{dot_html}"
        f"<span style='font-size:0.92rem;font-weight:700;"
        f"color:{COLOR_NAVY};'>{titulo}</span>"
        f"</div>"
        f"<div style='display:flex;gap:5px;align-items:center;flex-shrink:0;'>"
        f"{prio_badge} {gut_badge}"
        f"</div></div>"
        f"<p style='font-size:0.83rem;color:#475569;margin:0 0 8px;line-height:1.55;'>"
        f"{descricao}</p>"
        + (f"<p style='color:#92400E;font-size:0.75rem;background:#FFFBEB;"
           f"border-radius:6px;padding:4px 8px;margin:0 0 8px;'>"
           f"🎯 Ação recomendada: {gut_acao_recomendada(gut_r['prioridade'])}</p>"
           if gut_r else "")
        + f"<p style='font-size:0.7rem;color:{COLOR_MUTED};margin:0;'>📅 {data}</p>"
        f"</div></div></div>",
        unsafe_allow_html=True,
    )

    btn_cols = st.columns([1, 1, 4])
    if link_page:
        with btn_cols[0]:
            if st.button("Abrir →", key=f"alerta_open_{alerta['id']}",
                         use_container_width=True):
                st.session_state["portal_page"] = link_page
                st.session_state.pop("portal_ativo_id", None)
                st.rerun()

    # Botão "Abrir chamado" — pré-preenche o formulário de chamado com dados do alerta
    with btn_cols[1]:
        if st.button("🔧 Chamado", key=f"alerta_chamado_{alerta['id']}",
                     use_container_width=True):
            st.session_state["abrir_chamado_titulo"]    = alerta.get("titulo", "")
            st.session_state["abrir_chamado_descricao"] = alerta.get("descricao", "")
            st.session_state["abrir_chamado_categoria"] = "Dúvida técnica"
            st.session_state["abrir_chamado_prioridade"] = prio if prio in (
                "Baixa", "Média", "Alta", "Crítica") else "Média"
            st.session_state["abrir_chamado_origem"]    = "Alerta"
            st.session_state["abrir_chamado_ativo_id"]  = alerta.get("ativo_id", "")
            st.session_state["abrir_chamado_alert_id"]  = alerta.get("id", "")
            st.session_state["portal_page"] = "chamados"
            st.rerun()

    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)
