"""Supervisão Pred.IO — Ativos Monitorados (cadastro e gestão)."""
import unicodedata
import streamlit as st
from auth import require_staff
from sheets import (get_all_ativos_sv, cadastrar_ativo_sv,
                    get_componentes_sv, cadastrar_componente_sv,
                    get_all_clientes, get_all_chamados,
                    delete_ativo_sv)
from ui import (sv_page_header, sv_metric_card,
                COLOR_NAVY, COLOR_BLUE, COLOR_BG, COLOR_CARD, COLOR_BORDER, COLOR_MUTED)

# ── Routing keys ──────────────────────────────────────────────────────────────
_SV_ATIVO_ID  = "sv_ativo_id"
_SV_ATIVO_NOM = "sv_ativo_nome"
_SV_CLIE_ID   = "sv_ativo_cliente_id"

# ── Status e criticidade ──────────────────────────────────────────────────────
_STATUS = {
    "bom":               {"color": "#10B981", "bg": "#F0FDF4", "border": "#86EFAC", "text": "#065F46", "icon": "🟢"},
    "atencao":           {"color": "#F59E0B", "bg": "#FFFBEB", "border": "#FCD34D", "text": "#92400E", "icon": "🟡"},
    "critico":           {"color": "#EF4444", "bg": "#FEF2F2", "border": "#FCA5A5", "text": "#991B1B", "icon": "🔴"},
    "em acompanhamento": {"color": "#38BDF8", "bg": "#F0F9FF", "border": "#BAE6FD", "text": "#0C4A6E", "icon": "🔵"},
}
_STATUS_DEFAULT = {"color": "#94A3B8", "bg": "#F8FAFC", "border": "#CBD5E1", "text": "#475569", "icon": "⚪"}

_CRITICIDADE = {
    "alta":    {"color": "#EF4444", "bg": "#FEF2F2", "border": "#FCA5A5", "text": "#991B1B"},
    "critica": {"color": "#7C3AED", "bg": "#F5F3FF", "border": "#C4B5FD", "text": "#4C1D95"},
    "media":   {"color": "#F59E0B", "bg": "#FFFBEB", "border": "#FCD34D", "text": "#92400E"},
    "baixa":   {"color": "#10B981", "bg": "#F0FDF4", "border": "#86EFAC", "text": "#065F46"},
}
_CRIT_DEFAULT = {"color": "#94A3B8", "bg": "#F8FAFC", "border": "#CBD5E1", "text": "#475569"}

# ── Mock data (fallback enquanto Ativos sheet estiver vazia) ──────────────────
_MOCK_ATIVOS = [
    {
        "Id":                   "AT-2026-001",
        "Empresa":              "Coca-Cola",
        "Client_Id":            "coca-cola",
        "Planta":               "Sala de Compressores",
        "Tag":                  "Unidade Compressora Parafuso",
        "Tipo":                 "Compressor de parafuso",
        "Modelo":               "200 VLD",
        "Ns":                   "CP-2026-001",
        "Mb":                   "MB-01",
        "Inversor":             "Sim",
        "Analise_Oleo":         "Sim",
        "Status":               "Atenção",
        "Score":                "72",
        "Criticidade":          "Média",
        "Detalhes":             (
            "A unidade compressora apresenta redução gradual do score de saúde, "
            "com indicadores de óleo em atenção e componente Bomba de Óleo M60P em condição crítica."
        ),
        "Observacoes_Internas": (
            "Última visita técnica em 17/06/2026. Próxima coleta de óleo programada para 30/06/2026."
        ),
        "Data":                 "17/06/2026",
        "Criado_Em":            "01/06/2026 09:00:00",
    },
]

_MOCK_COMPONENTES = [
    {
        "Id":        "COMP-2026-001",
        "Ativo_Id":  "AT-2026-001",
        "Nome":      "Motor WEG 350 CV",
        "Tipo":      "Motor elétrico",
        "Modelo":    "WEG 350 CV",
        "Ns":        "MT-2026-014",
        "Mb":        "MB-02",
        "Inversor":  "Sim",
        "Status":    "Bom",
        "Score":     "91",
        "Criticidade": "Baixa",
        "Detalhes":  "Motor em condição estável. Opera com inversor de frequência.",
        "Data":      "15/06/2026",
        "Criado_Em": "01/06/2026 09:05:00",
    },
    {
        "Id":        "COMP-2026-002",
        "Ativo_Id":  "AT-2026-001",
        "Nome":      "Bomba de Óleo M60P",
        "Tipo":      "Bomba de óleo",
        "Modelo":    "M60P",
        "Ns":        "BO-2026-008",
        "Mb":        "MB-03",
        "Inversor":  "Não",
        "Status":    "Crítico",
        "Score":     "48",
        "Criticidade": "Alta",
        "Detalhes":  "Score crítico. Verificar vibração, pressão e vazão.",
        "Data":      "18/06/2026",
        "Criado_Em": "01/06/2026 09:10:00",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _norm(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower().strip())
        if unicodedata.category(c) != "Mn"
    )


def _scfg(status: str) -> dict:
    return _STATUS.get(_norm(status), _STATUS_DEFAULT)


def _ccfg(crit: str) -> dict:
    return _CRITICIDADE.get(_norm(crit), _CRIT_DEFAULT)


def _score_color(score) -> str:
    try:
        s = int(float(str(score)))
    except (ValueError, TypeError):
        return "#94A3B8"
    return "#10B981" if s >= 85 else "#F59E0B" if s >= 60 else "#EF4444"


def _lbl(title: str, value: str) -> str:
    return (
        f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:0 0 2px;"
        f"text-transform:uppercase;letter-spacing:.06em;'>{title}</p>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;margin:0 0 14px;'>"
        f"{value or '—'}</p>"
    )


def _load_ativos(filtros: dict | None = None):
    import pandas as pd
    df = get_all_ativos_sv(filtros)
    # Use mock when sheet is empty OR when it has old-format data (Id column empty/absent)
    use_mock = df.empty or (
        "Id" in df.columns and df["Id"].astype(str).str.strip().eq("").all()
    )
    if use_mock:
        df_mock = pd.DataFrame(_MOCK_ATIVOS)
        if filtros:
            if filtros.get("cliente"):
                df_mock = df_mock[
                    df_mock["Empresa"].str.lower().str.contains(
                        filtros["cliente"].lower(), na=False)]
            if filtros.get("status") and filtros["status"] != "Todos":
                df_mock = df_mock[
                    df_mock["Status"].str.lower() == filtros["status"].lower()]
            if filtros.get("criticidade") and filtros["criticidade"] != "Todas":
                df_mock = df_mock[
                    df_mock["Criticidade"].str.lower() == filtros["criticidade"].lower()]
        return df_mock, True
    return df, False


def _load_componentes(ativo_id: str):
    import pandas as pd
    df = get_componentes_sv(ativo_id)
    if df.empty:
        rows = [c for c in _MOCK_COMPONENTES if c["Ativo_Id"] == ativo_id]
        return pd.DataFrame(rows), True
    return df, False


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def render() -> None:
    require_staff()
    sv_view = st.session_state.get("sv_view", "ativos_sv")
    if sv_view == "ativo_detalhe":
        _render_detalhe()
    elif sv_view == "ativo_novo":
        _render_form_novo_ativo()
    elif sv_view == "componente_novo":
        _render_form_novo_componente()
    else:
        _render_lista()


# ═══════════════════════════════════════════════════════════════════════════════
# TELA LISTA
# ═══════════════════════════════════════════════════════════════════════════════
def _render_lista() -> None:
    sv_page_header(
        "⚙️ Ativos Monitorados",
        "Cadastre e acompanhe os ativos monitorados nos clientes Pred.IO.",
    )

    # ── Formulário sempre visível no topo ─────────────────────────────────────
    _form_novo_ativo_content(inline=True)

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.5rem 0;'/>",
        unsafe_allow_html=True,
    )

    # ── Filtros ────────────────────────────────────────────────────────────────
    col_cli, col_sta, col_cri = st.columns([2.5, 1.5, 1.5])
    with col_cli:
        busca = st.text_input("Buscar cliente ou planta",
                              placeholder="Ex: Coca-Cola, Sala de Compressores",
                              label_visibility="collapsed")
    with col_sta:
        status_f = st.selectbox("Status", ["Todos", "Bom", "Atenção", "Crítico", "Em acompanhamento"],
                                label_visibility="collapsed")
    with col_cri:
        crit_f = st.selectbox("Criticidade", ["Todas", "Baixa", "Média", "Alta", "Crítica"],
                              label_visibility="collapsed")

    filtros = {
        "cliente":     busca.strip() if busca else "",
        "status":      "" if status_f == "Todos" else status_f,
        "criticidade": "" if crit_f == "Todas" else crit_f,
    }

    df, usando_mock = _load_ativos(filtros)

    if usando_mock:
        st.caption("Exibindo dados de demonstração. Cadastre ativos reais para substituir.")

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.85rem;margin:0.5rem 0 1rem;'>"
        f"{len(df)} ativo(s) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("Nenhum ativo encontrado com os filtros selecionados.")
        return

    for _, row in df.iterrows():
        _render_card_ativo(row)


def _render_card_ativo(row) -> None:
    ativo_id  = str(row.get("Id", "")).strip()
    empresa   = str(row.get("Empresa", "")).strip()
    planta    = str(row.get("Planta", "")).strip()
    nome      = str(row.get("Tag", "")).strip() or str(row.get("Nome", "")).strip()
    tipo      = str(row.get("Tipo", "")).strip()
    modelo    = str(row.get("Modelo", "")).strip()
    ns        = str(row.get("Ns", "") or row.get("Numero_Serie", "")).strip()
    mb        = str(row.get("Mb", "")).strip()
    status    = str(row.get("Status", "")).strip()
    score_raw = str(row.get("Score", "0")).strip()
    crit      = str(row.get("Criticidade", "")).strip()
    data      = str(row.get("Data", "")).strip()

    try:
        score = int(float(score_raw))
    except (ValueError, TypeError):
        score = 0

    cfg  = _scfg(status)
    ccfg = _ccfg(crit)
    sc   = _score_color(score)

    col_info, col_ver, col_del = st.columns([8, 0.9, 0.7])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:5px solid {cfg['color']};border-radius:12px;"
            f"padding:14px 18px 12px;margin-bottom:4px;"
            f"box-shadow:0 1px 4px rgba(15,31,61,0.05);'>"

            # Linha 1: nome + empresa + status + criticidade
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:5px;'>"
            f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap;'>"
            f"<span style='font-weight:800;color:{COLOR_NAVY};font-size:0.98rem;'>{nome}</span>"
            f"<span style='background:#EFF6FF;color:#1E40AF;-webkit-text-fill-color:#1E40AF;"
            f"font-size:0.7rem;font-weight:700;padding:2px 10px;border-radius:12px;border:1px solid #BFDBFE;'>"
            f"🏢 {empresa}</span>"
            f"</div>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>"
            f"<span style='background:{cfg['bg']};color:{cfg['text']};-webkit-text-fill-color:{cfg['text']};"
            f"border:1px solid {cfg['border']};font-size:0.7rem;font-weight:700;"
            f"padding:2px 12px;border-radius:20px;'>{cfg['icon']} {status}</span>"
            f"<span style='background:{ccfg['bg']};color:{ccfg['text']};-webkit-text-fill-color:{ccfg['text']};"
            f"border:1px solid {ccfg['border']};font-size:0.7rem;font-weight:700;"
            f"padding:2px 12px;border-radius:20px;'>{crit}</span>"
            f"</div></div>"

            # Linha 2: meta
            f"<p style='color:{COLOR_MUTED};font-size:0.78rem;margin:0 0 8px;'>"
            f"🏭 {planta}"
            + (f"  ·  {tipo}" if tipo else "")
            + (f"  ·  Modelo: {modelo}" if modelo else "")
            + (f"  ·  NS: {ns}" if ns else "")
            + (f"  ·  {mb}" if mb else "")
            + (f"  ·  📅 {data}" if data else "")
            + f"</p>"

            # Score bar
            f"<div style='display:flex;justify-content:space-between;margin-bottom:3px;'>"
            f"<span style='font-size:0.67rem;font-weight:700;color:{COLOR_MUTED};"
            f"text-transform:uppercase;letter-spacing:.06em;'>Score de Saúde</span>"
            f"<span style='font-size:0.82rem;font-weight:800;color:{sc};'>{score}/100</span>"
            f"</div>"
            f"<div style='background:#E2E8F0;border-radius:5px;height:6px;overflow:hidden;'>"
            f"<div style='height:100%;border-radius:5px;background:{sc};width:{score}%;'></div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_ver:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        if st.button("Ver →", key=f"sv_at_ver_{ativo_id}", use_container_width=True):
            st.session_state["sv_view"]      = "ativo_detalhe"
            st.session_state[_SV_ATIVO_ID]   = ativo_id
            st.session_state[_SV_ATIVO_NOM]  = nome
            st.session_state[_SV_CLIE_ID]    = str(row.get("Client_Id", empresa.lower())).strip()
            st.rerun()
    with col_del:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        if st.button("🗑️", key=f"sv_at_del_{ativo_id}", use_container_width=True,
                     help="Excluir este ativo"):
            ok = delete_ativo_sv(ativo_id)
            if ok:
                st.toast(f"🗑️ Ativo '{nome}' removido.", icon="🗑️")
                st.rerun()
            else:
                st.toast("⚠️ Dado de demonstração — cadastre o ativo real para deletar.", icon="⚠️")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TELA DETALHE
# ═══════════════════════════════════════════════════════════════════════════════
def _render_detalhe() -> None:
    import pandas as pd

    ativo_id  = st.session_state.get(_SV_ATIVO_ID, "")
    client_id = st.session_state.get(_SV_CLIE_ID, "")

    # Carregar ativo
    df_all, usando_mock = _load_ativos()
    if not df_all.empty and "Id" in df_all.columns:
        match = df_all[df_all["Id"].astype(str).str.strip() == ativo_id]
        row = match.iloc[0] if not match.empty else None
    else:
        row = None

    if row is None:
        st.warning("Ativo não encontrado.")
        if st.button("← Voltar"):
            st.session_state["sv_view"] = "ativos_sv"
            st.rerun()
        return

    nome    = str(row.get("Tag",    "")).strip() or str(row.get("Nome", "")).strip()
    empresa = str(row.get("Empresa","")).strip()
    planta  = str(row.get("Planta", "")).strip()
    tipo    = str(row.get("Tipo",   "")).strip()
    modelo  = str(row.get("Modelo", "")).strip()
    ns      = str(row.get("Ns",     "") or row.get("Numero_Serie", "")).strip()
    mb      = str(row.get("Mb",     "")).strip()
    inversor= str(row.get("Inversor","")).strip()
    anal_ol = str(row.get("Analise_Oleo","")).strip()
    status  = str(row.get("Status", "")).strip()
    score_r = str(row.get("Score",  "0")).strip()
    crit    = str(row.get("Criticidade","")).strip()
    detalhes= str(row.get("Detalhes","")).strip()
    obs_int = str(row.get("Observacoes_Internas","")).strip()
    data    = str(row.get("Data",   "")).strip()

    try:
        score = int(float(score_r))
    except (ValueError, TypeError):
        score = 0

    cfg  = _scfg(status)
    ccfg = _ccfg(crit)
    sc   = _score_color(score)

    sv_page_header(
        f"⚙️ {nome}",
        subtitle=f"{empresa}  ·  {planta}",
        back_label="Ativos Monitorados",
        back_view="ativos_sv",
    )

    if usando_mock:
        st.caption("Dados de demonstração.")

    # ── Métricas ──────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        sv_metric_card(cfg["icon"], "Status", status, cfg["color"])
    with c2:
        sv_metric_card("📊", "Score de Saúde", f"{score}/100", sc)
    with c3:
        sv_metric_card("⚠️", "Criticidade", crit, ccfg["color"])

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Dados técnicos ────────────────────────────────────────────────────────
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0 0 0.75rem;'>"
        f"📋 Dados do Ativo</p>",
        unsafe_allow_html=True,
    )
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.markdown(_lbl("Cliente", empresa) + _lbl("Planta", planta), unsafe_allow_html=True)
    with g2:
        st.markdown(_lbl("Tipo", tipo) + _lbl("Modelo", modelo), unsafe_allow_html=True)
    with g3:
        st.markdown(_lbl("Número de Série", ns) + _lbl("MB", mb), unsafe_allow_html=True)
    with g4:
        st.markdown(
            _lbl("Inversor de Freq.", inversor)
            + _lbl("Análise de Óleo", anal_ol)
            + _lbl("Última Atualização", data),
            unsafe_allow_html=True,
        )

    # Recomendação
    if detalhes:
        st.markdown(
            f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
            f"border-left:5px solid {COLOR_BLUE};border-radius:0 12px 12px 0;"
            f"padding:0.9rem 1.2rem;margin:0.5rem 0 1rem;'>"
            f"<p style='font-size:0.67rem;font-weight:700;color:{COLOR_MUTED};"
            f"text-transform:uppercase;letter-spacing:.06em;margin:0 0 4px;'>Recomendação Técnica</p>"
            f"<p style='color:#1E3A8A;font-size:0.88rem;margin:0;line-height:1.65;'>{detalhes}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Observações internas (staff only)
    if obs_int:
        st.markdown(
            f"<div style='background:#FFFBEB;border:1px solid #FCD34D;"
            f"border-left:5px solid #F59E0B;border-radius:0 12px 12px 0;"
            f"padding:0.9rem 1.2rem;margin-bottom:1rem;'>"
            f"<p style='font-size:0.67rem;font-weight:700;color:#92400E;"
            f"text-transform:uppercase;letter-spacing:.06em;margin:0 0 4px;'>"
            f"🔒 Observações Internas (staff only)</p>"
            f"<p style='color:#78350F;font-size:0.88rem;margin:0;line-height:1.65;'>{obs_int}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Componentes ───────────────────────────────────────────────────────────
    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:0.5rem 0 1rem;'/>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"margin-bottom:0.75rem;'>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0;'>"
        f"⚙️ Componentes Vinculados</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    col_add, _ = st.columns([1.5, 5])
    with col_add:
        if st.button("➕ Adicionar componente", use_container_width=True):
            st.session_state["sv_view"]    = "componente_novo"
            st.session_state[_SV_ATIVO_ID] = ativo_id
            st.session_state[_SV_ATIVO_NOM]= nome
            st.rerun()

    df_comp, comp_mock = _load_componentes(ativo_id)

    if df_comp.empty:
        st.info("Nenhum componente vinculado ainda. Clique em '+ Adicionar componente'.")
    else:
        for _, comp in df_comp.iterrows():
            _render_componente_card(comp)

    # ── Histórico Técnico Interno ─────────────────────────────────────────────
    if usando_mock:
        from page_ativos import _HISTORICO_MOCK_COMPRESSOR, _render_historico_tecnico
        st.markdown(
            f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0;'/>"
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0 0 0.3rem;'>"
            f"🕐 Histórico Técnico Interno</p>"
            f"<p style='color:{COLOR_MUTED};font-size:0.78rem;margin:0 0 0.75rem;'>"
            f"Visão completa — inclui obs. internas e eventos não visíveis ao cliente.</p>",
            unsafe_allow_html=True,
        )
        _render_historico_tecnico(
            _HISTORICO_MOCK_COMPRESSOR,
            ativo_id=ativo_id,
            is_staff=True,
            prefix="sv_",
        )

    # ── Plano de manutenção ───────────────────────────────────────────────────
    if usando_mock:
        from page_ativos import _PLANO_MOCK_COMPRESSOR, _render_plano_manutencao
        st.markdown(
            f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0;'/>"
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0 0 0.75rem;'>"
            f"📅 Plano de Manutenção</p>",
            unsafe_allow_html=True,
        )
        _render_plano_manutencao(_PLANO_MOCK_COMPRESSOR)

    # ── Chamados do cliente ───────────────────────────────────────────────────
    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0;'/>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0 0 0.75rem;'>"
        f"🔧 Chamados do Cliente</p>",
        unsafe_allow_html=True,
    )

    df_cham = get_all_chamados({"cliente": empresa})
    if df_cham.empty or "Empresa" not in df_cham.columns:
        st.info("Nenhum chamado registrado para este cliente.")
    else:
        recentes = df_cham.head(5)
        for _, crow in recentes.iterrows():
            _render_chamado_mini(crow)

    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)


def _render_componente_card(comp) -> None:
    nome    = str(comp.get("Nome",    "")).strip()
    tipo    = str(comp.get("Tipo",    "")).strip()
    modelo  = str(comp.get("Modelo",  "")).strip()
    ns      = str(comp.get("Ns", "") or comp.get("Numero_Serie","")).strip()
    mb      = str(comp.get("Mb",      "")).strip()
    inversor= str(comp.get("Inversor","")).strip()
    status  = str(comp.get("Status",  "")).strip()
    score_r = str(comp.get("Score",   "0")).strip()
    crit    = str(comp.get("Criticidade","")).strip()
    data    = str(comp.get("Data",    "")).strip()
    rec     = str(comp.get("Detalhes","")).strip()

    try:
        score = int(float(score_r))
    except (ValueError, TypeError):
        score = 0

    cfg = _scfg(status)
    sc  = _score_color(score)

    st.markdown(
        f"<div style='background:{COLOR_BG};border:1px solid {cfg['border']};"
        f"border-left:4px solid {cfg['color']};border-radius:10px;"
        f"padding:12px 16px;margin-bottom:8px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"flex-wrap:wrap;gap:6px;margin-bottom:4px;'>"
        f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;'>{nome}</span>"
        f"<div style='display:flex;gap:5px;'>"
        f"<span style='background:{cfg['bg']};color:{cfg['text']};-webkit-text-fill-color:{cfg['text']};"
        f"border:1px solid {cfg['border']};font-size:0.68rem;font-weight:700;"
        f"padding:2px 10px;border-radius:20px;'>{cfg['icon']} {status}</span>"
        f"</div></div>"
        f"<p style='color:{COLOR_MUTED};font-size:0.78rem;margin:0 0 4px;'>"
        f"{tipo}"
        + (f"  ·  Modelo: {modelo}" if modelo else "")
        + (f"  ·  NS: {ns}" if ns else "")
        + (f"  ·  {mb}" if mb else "")
        + (f"  ·  ⚡ Inversor: {inversor}" if inversor else "")
        + (f"  ·  📅 {data}" if data else "")
        + f"</p>"
        f"<div style='display:flex;justify-content:space-between;margin-bottom:3px;'>"
        f"<span style='font-size:0.65rem;color:{COLOR_MUTED};font-weight:700;"
        f"text-transform:uppercase;letter-spacing:.06em;'>Score</span>"
        f"<span style='font-size:0.8rem;font-weight:800;color:{sc};'>{score}/100</span>"
        f"</div>"
        f"<div style='background:#E2E8F0;border-radius:5px;height:5px;overflow:hidden;'>"
        f"<div style='height:100%;border-radius:5px;background:{sc};width:{score}%;'></div>"
        f"</div>"
        + (f"<p style='color:#475569;font-size:0.8rem;margin:8px 0 0;'>{rec}</p>" if rec else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_chamado_mini(row) -> None:
    titulo    = str(row.get("Titulo",     "Sem título")).strip()
    planta    = str(row.get("Planta",     "")).strip()
    equip     = str(row.get("Equipamento","")).strip()
    prioridade= str(row.get("Prioridade", "Baixa")).strip()
    status    = str(row.get("Status",     "")).strip()
    data_ab   = str(row.get("Data_Abertura","")).strip()[:10]

    pr_colors = {"crítica": "#EF4444", "alta": "#F97316", "média": "#F59E0B", "baixa": "#64748B"}
    pr_c = pr_colors.get(prioridade.lower(), "#94A3B8")

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-left:3px solid {pr_c};border-radius:8px;"
        f"padding:10px 14px;margin-bottom:6px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"flex-wrap:wrap;gap:4px;'>"
        f"<span style='font-weight:600;color:{COLOR_NAVY};font-size:0.88rem;'>{titulo}</span>"
        f"<span style='background:{pr_c};color:#fff;-webkit-text-fill-color:#fff;"
        f"font-size:0.68rem;font-weight:700;padding:1px 10px;border-radius:20px;'>{prioridade}</span>"
        f"</div>"
        f"<p style='color:{COLOR_MUTED};font-size:0.76rem;margin:3px 0 0;'>"
        + (f"🏭 {planta}  " if planta else "")
        + (f"⚙️ {equip}  " if equip else "")
        + (f"📅 {data_ab}  " if data_ab else "")
        + (f"· {status}" if status else "")
        + "</p></div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULÁRIO — NOVO ATIVO (conteúdo reutilizável)
# ═══════════════════════════════════════════════════════════════════════════════
def _form_novo_ativo_content(inline: bool = False) -> None:
    """Campos e lógica de submit do formulário de novo ativo.
    inline=True → usado direto na lista; sucesso fecha o painel sem trocar de view."""

    df_cli = get_all_clientes()
    if not df_cli.empty and "Empresa" in df_cli.columns:
        empresas = sorted(df_cli["Empresa"].dropna().unique().tolist())
    else:
        empresas = ["Coca-Cola", "Sibele Alimentos"]
    opcoes_empresas = ["Selecione o cliente..."] + empresas

    form_key = "form_novo_ativo_inline" if inline else "form_novo_ativo"

    with st.form(form_key, clear_on_submit=False):
        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0 0 0.75rem;'>1. Cliente e Localização</p>",
            unsafe_allow_html=True,
        )
        col_e, col_p = st.columns(2)
        with col_e:
            empresa_sel = st.selectbox("Cliente *", opcoes_empresas)
        with col_p:
            planta = st.text_input("Planta *", placeholder="Ex: Sala de Compressores")

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0.75rem 0 0.75rem;'>2. Identificação do Ativo</p>",
            unsafe_allow_html=True,
        )
        col_n, col_t = st.columns(2)
        with col_n:
            nome = st.text_input("Nome do ativo *", placeholder="Ex: Unidade Compressora Parafuso")
        with col_t:
            tipo = st.text_input("Tipo do ativo", placeholder="Ex: Compressor de parafuso")

        col_m, col_ns, col_mb = st.columns(3)
        with col_m:
            modelo = st.text_input("Modelo", placeholder="Ex: 200 VLD")
        with col_ns:
            numero_serie = st.text_input("Número de série", placeholder="Ex: CP-2026-001")
        with col_mb:
            mb = st.text_input("MB", placeholder="Ex: MB-01")

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0.75rem 0 0.75rem;'>3. Configuração Técnica</p>",
            unsafe_allow_html=True,
        )
        col_i, col_o = st.columns(2)
        with col_i:
            inversor = st.selectbox(
                "Inversor de frequência",
                ["Sim", "Não", "Não aplicável", "Não informado"],
            )
        with col_o:
            analise_oleo = st.selectbox(
                "Análise de óleo aplicável",
                ["Sim", "Não"],
            )

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0.75rem 0 0.75rem;'>4. Componentes Específicos</p>",
            unsafe_allow_html=True,
        )
        col_bo, col_co = st.columns(2)
        with col_bo:
            modelo_bomba_oleo = st.text_input(
                "Modelo da bomba de óleo",
                placeholder="Ex: Atlas Copco OFM22",
            )
        with col_co:
            num_coalescer = st.text_input(
                "Número do coalescer",
                placeholder="Ex: 1614905400",
            )
        col_pa, col_ho = st.columns(2)
        with col_pa:
            modelo_painel = st.text_input(
                "Modelo do painel",
                placeholder="Ex: WD300",
            )
        with col_ho:
            horimetro_atual = st.number_input(
                "Horímetro atual (h)",
                min_value=0,
                value=0,
                step=10,
                help="Horímetro do equipamento no momento do cadastro.",
            )

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0.75rem 0 0.75rem;'>5. Status e Saúde</p>",
            unsafe_allow_html=True,
        )
        col_s, col_c, col_d = st.columns(3)
        with col_s:
            status = st.selectbox(
                "Status *",
                ["Bom", "Atenção", "Crítico", "Em acompanhamento"],
            )
        with col_c:
            criticidade = st.selectbox(
                "Criticidade",
                ["Baixa", "Média", "Alta", "Crítica"],
                index=1,
            )
        with col_d:
            ultima_atu = st.text_input("Última atualização", placeholder="DD/MM/AAAA")

        score = st.slider("Score de saúde (0-100)", 0, 100, 80)

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0.75rem 0 0.75rem;'>6. Notas Técnicas</p>",
            unsafe_allow_html=True,
        )
        recomendacao = st.text_area(
            "Recomendação técnica",
            placeholder="Descreva o status atual e recomendações de acompanhamento...",
            height=100,
        )
        obs_internas = st.text_area(
            "Observações internas (staff only — não visível ao cliente)",
            placeholder="Próxima visita, pendências, histórico de atendimento...",
            height=80,
        )

        submitted = st.form_submit_button("💾 Cadastrar ativo", type="primary",
                                          use_container_width=True)

    if submitted:
        erros = []
        if empresa_sel == "Selecione o cliente...":
            erros.append("Selecione o cliente.")
        if not planta.strip():
            erros.append("Informe a planta.")
        if not nome.strip():
            erros.append("Informe o nome do ativo.")
        if erros:
            for e in erros:
                st.warning(e)
            return

        from auth import get_client_id
        dados = {
            "empresa":                empresa_sel.strip(),
            "client_id":              get_client_id(empresa_sel.strip()),
            "planta":                 planta.strip(),
            "nome":                   nome.strip(),
            "tipo":                   tipo.strip(),
            "modelo":                 modelo.strip(),
            "numero_serie":           numero_serie.strip(),
            "mb":                     mb.strip(),
            "inversor_frequencia":    inversor,
            "analise_oleo_aplicavel": analise_oleo,
            "modelo_bomba_oleo":      modelo_bomba_oleo.strip(),
            "num_coalescer":          num_coalescer.strip(),
            "modelo_painel":          modelo_painel.strip(),
            "horimetro_atual":        horimetro_atual,
            "status":                 status,
            "score_saude":            str(score),
            "criticidade":            criticidade,
            "recomendacao":           recomendacao.strip(),
            "observacoes_internas":   obs_internas.strip(),
            "ultima_atualizacao":     ultima_atu.strip(),
        }

        ativo_id = cadastrar_ativo_sv(dados)
        if ativo_id:
            st.success(f"✅ Ativo cadastrado com sucesso! ID: {ativo_id}")
            st.balloons()
            if inline:
                st.session_state.pop("sv_show_form_ativo", None)
            else:
                st.session_state["sv_view"] = "ativos_sv"
            st.rerun()
        else:
            st.error(
                "Erro ao cadastrar o ativo. Verifique se a aba 'Ativos' existe na planilha "
                "e se as credenciais têm permissão de escrita."
            )


def _render_form_novo_ativo() -> None:
    sv_page_header(
        "➕ Novo Ativo",
        subtitle="Cadastre um ativo principal monitorado.",
        back_label="Ativos Monitorados",
        back_view="ativos_sv",
    )
    _form_novo_ativo_content(inline=False)


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULÁRIO — NOVO COMPONENTE
# ═══════════════════════════════════════════════════════════════════════════════
def _render_form_novo_componente() -> None:
    ativo_id  = st.session_state.get(_SV_ATIVO_ID, "")
    ativo_nom = st.session_state.get(_SV_ATIVO_NOM, "Ativo")

    sv_page_header(
        "➕ Novo Componente",
        subtitle=f"Vinculado a: {ativo_nom}",
        back_label=ativo_nom,
        back_view="ativo_detalhe",
    )

    if not ativo_id:
        st.warning("Ativo não identificado. Volte e tente novamente.")
        return

    st.markdown(
        f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
        f"border-radius:8px;padding:10px 14px;margin-bottom:1rem;'>"
        f"<p style='color:#1E40AF;font-size:0.85rem;margin:0;'>"
        f"⚙️ Componente será vinculado ao ativo: <strong>{ativo_nom}</strong> (ID: {ativo_id})</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    with st.form("form_novo_componente", clear_on_submit=False):
        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0 0 0.75rem;'>Identificação do Componente</p>",
            unsafe_allow_html=True,
        )
        col_n, col_t = st.columns(2)
        with col_n:
            nome = st.text_input("Nome do componente *", placeholder="Ex: Motor WEG 350 CV")
        with col_t:
            tipo = st.text_input("Tipo *", placeholder="Ex: Motor elétrico")

        col_m, col_ns, col_mb = st.columns(3)
        with col_m:
            modelo = st.text_input("Modelo", placeholder="Ex: WEG 350 CV")
        with col_ns:
            numero_serie = st.text_input("Número de série", placeholder="Ex: MT-2026-014")
        with col_mb:
            mb = st.text_input("MB", placeholder="Ex: MB-02")

        col_i, col_s, col_c, col_d = st.columns(4)
        with col_i:
            inversor = st.selectbox(
                "Inversor de frequência",
                ["Sim", "Não", "Não aplicável", "Não informado"],
            )
        with col_s:
            status = st.selectbox(
                "Status *",
                ["Bom", "Atenção", "Crítico", "Em acompanhamento"],
            )
        with col_c:
            criticidade = st.selectbox(
                "Criticidade",
                ["Baixa", "Média", "Alta", "Crítica"],
            )
        with col_d:
            ultima_atu = st.text_input("Última atualização", placeholder="DD/MM/AAAA")

        score = st.slider("Score de saúde (0-100)", 0, 100, 85)

        recomendacao = st.text_area(
            "Recomendação técnica",
            placeholder="Estado atual do componente e recomendações...",
            height=90,
        )

        submitted = st.form_submit_button("💾 Cadastrar componente", type="primary",
                                          use_container_width=True)

    if submitted:
        if not nome.strip() or not tipo.strip():
            st.warning("Nome e tipo do componente são obrigatórios.")
            return

        dados = {
            "ativo_id":            ativo_id,
            "nome":                nome.strip(),
            "tipo":                tipo.strip(),
            "modelo":              modelo.strip(),
            "numero_serie":        numero_serie.strip(),
            "mb":                  mb.strip(),
            "inversor_frequencia": inversor,
            "status":              status,
            "score_saude":         str(score),
            "criticidade":         criticidade,
            "recomendacao":        recomendacao.strip(),
            "ultima_atualizacao":  ultima_atu.strip(),
        }

        ok = cadastrar_componente_sv(dados)
        if ok:
            st.success(f"✅ Componente '{nome}' cadastrado e vinculado ao ativo!")
            st.session_state["sv_view"] = "ativo_detalhe"
            st.rerun()
        else:
            st.error(
                "Erro ao cadastrar componente. Verifique se a aba 'ComponentesAtivos' "
                "existe na planilha e se há permissão de escrita."
            )
