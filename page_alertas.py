"""Central de Alertas — portal do cliente."""
import streamlit as st
from auth import current_client_id
from ui import page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED

# ── Mock de alertas ────────────────────────────────────────────────────────────
# Estrutura preparada para filtragem por client_id quando houver banco real.
_ALERTAS_MOCK = [
    {
        "id":         "alerta-001",
        "client_id":  "coca-cola",
        "tipo":       "manutencao_proxima",
        "categoria":  "manutencao",
        "titulo":     "Análise de óleo próxima do vencimento",
        "descricao":  "A Unidade Compressora Parafuso 200 VLD está a 320 horas da próxima análise de óleo.",
        "prioridade": "Média",
        "status":     "nao_lido",
        "data":       "21/06/2026",
        "link_page":  "manutencao",
    },
    {
        "id":         "alerta-002",
        "client_id":  "coca-cola",
        "tipo":       "ativo_critico",
        "categoria":  "ativos",
        "titulo":     "Bomba de Óleo M60P em condição crítica",
        "descricao":  "O componente Bomba de Óleo M60P apresenta score crítico e requer acompanhamento técnico.",
        "prioridade": "Alta",
        "status":     "nao_lido",
        "data":       "20/06/2026",
        "link_page":  "ativos",
    },
    {
        "id":         "alerta-003",
        "client_id":  "coca-cola",
        "tipo":       "relatorio_novo",
        "categoria":  "relatorios",
        "titulo":     "Novo relatório disponível",
        "descricao":  "Relatório de Análise Preditiva — Unidade Compressora 200 VLD — Junho/2026 publicado.",
        "prioridade": "Baixa",
        "status":     "lido",
        "data":       "17/06/2026",
        "link_page":  "relatorios",
    },
    {
        "id":         "alerta-004",
        "client_id":  "coca-cola",
        "tipo":       "chamado_respondido",
        "categoria":  "chamados",
        "titulo":     "Chamado respondido pela Pred.IO",
        "descricao":  "A equipe Pred.IO respondeu o chamado sobre aumento de vibração.",
        "prioridade": "Média",
        "status":     "nao_lido",
        "data":       "19/06/2026",
        "link_page":  "chamados",
    },
    {
        "id":         "alerta-005",
        "client_id":  "coca-cola",
        "tipo":       "termografia",
        "categoria":  "manutencao",
        "titulo":     "Termografia programada",
        "descricao":  "A próxima inspeção termográfica está programada para 17/10/2026.",
        "prioridade": "Baixa",
        "status":     "lido",
        "data":       "21/06/2026",
        "link_page":  "manutencao",
    },
]

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

# ── Configuração visual por prioridade ────────────────────────────────────────
_PRIO_CFG = {
    "Alta":  {
        "bg": "#FEF2F2", "border": "#FCA5A5", "dot": "#EF4444", "text": "#991B1B",
        "badge_bg": "#EF4444", "badge_tc": "#fff",
    },
    "Média": {
        "bg": "#FFFBEB", "border": "#FCD34D", "dot": "#F59E0B", "text": "#92400E",
        "badge_bg": "#F59E0B", "badge_tc": "#000",
    },
    "Baixa": {
        "bg": "#F0F9FF", "border": "#BAE6FD", "dot": "#38BDF8", "text": "#0C4A6E",
        "badge_bg": "#38BDF8", "badge_tc": "#fff",
    },
    "Lido":  {
        "bg": "#F8FAFC", "border": "#E2E8F0", "dot": "#94A3B8", "text": "#64748B",
        "badge_bg": "#94A3B8", "badge_tc": "#fff",
    },
}

_PRIO_ORDER = {"Alta": 0, "Média": 1, "Baixa": 2}


def _load_alertas(client_id: str) -> list:
    """Retorna alertas filtrados por client_id. Mock enquanto não houver banco real."""
    # TODO: substituir pela consulta real ao banco, filtrando por client_id
    return [a for a in _ALERTAS_MOCK if a.get("client_id") == client_id or not client_id]


def get_unread_count(client_id: str = "") -> int:
    """Contagem de não lidos — usada pelo sidebar para exibir o badge."""
    return sum(1 for a in _load_alertas(client_id) if a.get("status") == "nao_lido")


# ── Render principal ───────────────────────────────────────────────────────────

def render() -> None:
    page_header(
        "🔔 Central de Alertas",
        "Acompanhe notificações importantes sobre ativos, relatórios, manutenções e chamados.",
    )

    client_id = current_client_id()
    alertas   = _load_alertas(client_id)

    if not alertas:
        st.markdown(
            f"<div style='text-align:center;padding:3rem 1rem;color:{COLOR_MUTED};'>"
            f"<div style='font-size:3rem;margin-bottom:0.6rem;'>🔕</div>"
            f"<p style='font-size:1rem;'>Nenhum alerta no momento.</p></div>",
            unsafe_allow_html=True,
        )
        return

    # ── Resumo rápido ─────────────────────────────────────────────────────────
    nao_lidos = sum(1 for a in alertas if a.get("status") == "nao_lido")
    alta      = sum(1 for a in alertas if a.get("prioridade") == "Alta" and a.get("status") == "nao_lido")

    c1, c2, c3 = st.columns(3)
    for col, val, label, cor in [
        (c1, len(alertas),   "Total de alertas",   COLOR_NAVY),
        (c2, nao_lidos,      "Não lidos",           "#F59E0B"),
        (c3, alta,           "Alta prioridade",     "#EF4444"),
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

    # ── Filtros ───────────────────────────────────────────────────────────────
    if "alertas_filtro" not in st.session_state:
        st.session_state["alertas_filtro"] = "todos"

    filtro = st.session_state["alertas_filtro"]

    FILTROS = [
        ("todos",      "Todos"),
        ("nao_lido",   "Não lidos"),
        ("manutencao", "Manutenção"),
        ("ativos",     "Ativos"),
        ("relatorios", "Relatórios"),
        ("chamados",   "Chamados"),
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
        st.markdown(
            f"<div style='text-align:center;padding:2.5rem 1rem;color:{COLOR_MUTED};'>"
            f"<div style='font-size:2.5rem;margin-bottom:0.5rem;'>🔕</div>"
            f"<p>Nenhum alerta nesta categoria.</p></div>",
            unsafe_allow_html=True,
        )
        return

    # Ordena: não lidos + alta prioridade primeiro
    filtrados = sorted(
        filtrados,
        key=lambda a: (
            0 if a.get("status") == "nao_lido" else 1,
            _PRIO_ORDER.get(a.get("prioridade", "Baixa"), 3),
        ),
    )

    for alerta in filtrados:
        _render_alerta_card(alerta)


def _aplicar_filtro(alertas: list, filtro: str) -> list:
    if filtro == "todos":
        return alertas
    if filtro == "nao_lido":
        return [a for a in alertas if a.get("status") == "nao_lido"]
    return [a for a in alertas if a.get("categoria") == filtro]


def _render_alerta_card(alerta: dict) -> None:
    lido     = alerta.get("status") == "lido"
    prio     = alerta.get("prioridade", "Baixa")
    pcfg     = _PRIO_CFG.get("Lido" if lido else prio, _PRIO_CFG["Baixa"])
    tcfg     = _TIPO_CFG.get(alerta.get("tipo", ""), {"icone": "🔔", "label": "Notificação"})

    titulo    = alerta.get("titulo", "")
    descricao = alerta.get("descricao", "")
    data      = alerta.get("data", "")
    link_page = alerta.get("link_page", "")

    opacity    = "opacity:0.58;" if lido else ""
    peso_titulo = "500" if lido else "700"

    dot_html = (
        f"<span style='width:8px;height:8px;border-radius:50%;flex-shrink:0;"
        f"display:inline-block;background:{pcfg['dot']};margin-right:5px;'></span>"
        if not lido else ""
    )

    prio_badge = (
        f"<span style='background:{pcfg['badge_bg']};color:{pcfg['badge_tc']};"
        f"-webkit-text-fill-color:{pcfg['badge_tc']};"
        f"font-size:0.67rem;font-weight:700;padding:2px 8px;border-radius:10px;'>"
        f"{prio}</span>"
    )
    lido_badge = (
        f"<span style='background:#F1F5F9;color:#64748B;"
        f"-webkit-text-fill-color:#64748B;font-size:0.64rem;"
        f"padding:2px 7px;border-radius:8px;border:1px solid #E2E8F0;'>"
        f"{'Lido' if lido else 'Não lido'}</span>"
    )

    st.markdown(
        f"<div style='background:{pcfg['bg']};border:1px solid {pcfg['border']};"
        f"border-left:4px solid {pcfg['dot']};border-radius:12px;"
        f"padding:1rem 1.25rem;margin-bottom:0.6rem;{opacity}'>"
        f"<div style='display:flex;align-items:flex-start;gap:12px;'>"
        f"<span style='font-size:1.5rem;flex-shrink:0;margin-top:1px;'>{tcfg['icone']}</span>"
        f"<div style='flex:1;min-width:0;'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:flex-start;gap:8px;flex-wrap:wrap;margin-bottom:3px;'>"
        f"<div style='display:flex;align-items:center;'>"
        f"{dot_html}"
        f"<span style='font-size:0.92rem;font-weight:{peso_titulo};"
        f"color:{COLOR_NAVY};'>{titulo}</span>"
        f"</div>"
        f"<div style='display:flex;gap:5px;align-items:center;flex-shrink:0;'>"
        f"{prio_badge} {lido_badge}"
        f"</div></div>"
        f"<p style='font-size:0.75rem;font-weight:700;color:{pcfg['dot']};"
        f"-webkit-text-fill-color:{pcfg['dot']};margin:0 0 6px;'>{tcfg['label']}</p>"
        f"<p style='font-size:0.83rem;color:#475569;margin:0 0 8px;line-height:1.55;'>"
        f"{descricao}</p>"
        f"<p style='font-size:0.7rem;color:{COLOR_MUTED};margin:0;'>📅 {data}</p>"
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
        _prio_map = {"Alta": "Alta", "Média": "Média", "Baixa": "Baixa", "Crítica": "Crítica"}
        _cat_map  = {
            "manutencao_proxima": "Manutenção próxima",
            "manutencao_vencida": "Manutenção vencida",
            "ativo_critico":      "Falha operacional",
            "ativo_atencao":      "Dúvida técnica",
            "relatorio_novo":     "Relatório técnico",
            "chamado_respondido": "Dúvida técnica",
            "recomendacao":       "Recomendação por condição",
            "termografia":        "Termografia",
        }
        if st.button("🔧 Chamado", key=f"alerta_chamado_{alerta['id']}",
                     use_container_width=True):
            st.session_state["abrir_chamado_titulo"]    = alerta.get("titulo", "")
            st.session_state["abrir_chamado_descricao"] = alerta.get("descricao", "")
            st.session_state["abrir_chamado_categoria"] = _cat_map.get(
                alerta.get("tipo", ""), "Dúvida técnica")
            st.session_state["abrir_chamado_prioridade"] = _prio_map.get(
                alerta.get("prioridade", "Média"), "Média")
            st.session_state["abrir_chamado_origem"]    = "Alerta"
            st.session_state["abrir_chamado_alert_id"]  = alerta.get("id", "")
            st.session_state["portal_page"] = "chamados"
            st.rerun()

    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)
