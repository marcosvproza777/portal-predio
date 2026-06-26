"""Meus Relatórios — listagem com filtros, download de PDF."""
import streamlit as st
from auth import current_client_id
from sheets import get_relatorios, get_technical_reports, get_relatorios_executivos_publicados
from ui import (page_header, COLOR_NAVY, COLOR_BLUE,
                COLOR_CARD, COLOR_BORDER, COLOR_MUTED, TIPOS_LAUDOS)

_SEV_COLOR = {
    "normal":   ("#10B981", "#F0FDF4", "#86EFAC", "#065F46"),
    "atenção":  ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E"),
    "atencao":  ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E"),
    "crítico":  ("#EF4444", "#FEF2F2", "#FCA5A5", "#991B1B"),
    "critico":  ("#EF4444", "#FEF2F2", "#FCA5A5", "#991B1B"),
    "urgente":  ("#7C3AED", "#F5F3FF", "#C4B5FD", "#4C1D95"),
}


def render() -> None:
    page_header("📁 Meus Relatórios", "Acesse e baixe seus laudos técnicos")

    client_id = current_client_id()  # SEMPRE da sessão

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            tipo_opts = ["Todos"] + [label for _, label in TIPOS_LAUDOS]
            tipo_sel  = st.selectbox("Tipo de Serviço", tipo_opts)
        with c2:
            import datetime
            mes_opts = ["Todos"] + [str(m) for m in range(1, 13)]
            mes_sel  = st.selectbox("Mês", mes_opts)
        with c3:
            ano_atual = datetime.datetime.now().year
            ano_opts  = ["Todos"] + [str(a) for a in range(ano_atual, ano_atual - 6, -1)]
            ano_sel   = st.selectbox("Ano", ano_opts)

        c4, c5 = st.columns(2)
        with c4:
            planta_sel = st.text_input("Planta", placeholder="Ex: Planta RJ")
        with c5:
            equip_sel  = st.text_input("Equipamento", placeholder="Ex: Bomba B-204")

    filtros = {
        "tipo":        None if tipo_sel == "Todos" else tipo_sel,
        "mes":         None if mes_sel  == "Todos" else mes_sel,
        "ano":         None if ano_sel  == "Todos" else ano_sel,
        "planta":      planta_sel.strip() or None,
        "equipamento": equip_sel.strip() or None,
    }

    # ── Busca — client_id vem da sessão, nunca do front-end ──────────────────
    # Audit log: acesso à página de relatórios
    try:
        from security import log_acesso_permitido
        log_acesso_permitido("visualizar_relatorios", "pagina", "relatorios", client_id)
    except Exception:
        pass

    import pandas as pd

    # Carrega relatórios da aba legacy "Relatorios"
    df_legacy = get_relatorios(client_id, {k: v for k, v in filtros.items() if v})

    # Carrega relatórios publicados da nova aba "TechnicalReports"
    try:
        df_tech = get_technical_reports(client_id=client_id, staff=False)
    except Exception:
        df_tech = pd.DataFrame()

    # Carrega relatórios executivos publicados — SOMENTE status=Publicado, sem obs_interna
    try:
        df_exec = get_relatorios_executivos_publicados(client_id)
    except Exception:
        df_exec = pd.DataFrame()

    # Audit log — acesso permitido
    try:
        from security import log_acesso_permitido
        log_acesso_permitido("visualizar_relatorios_executivos", "relatorio_executivo", "lista", client_id)
    except Exception:
        pass

    total = len(df_legacy) + (len(df_tech) if not df_tech.empty else 0) + (len(df_exec) if not df_exec.empty else 0)
    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.85rem;margin-bottom:0.5rem;'>"
        f"{total} relatório(s) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    if df_legacy.empty and (df_tech is None or df_tech.empty) and (df_exec is None or df_exec.empty):
        st.info("Nenhum relatório disponível no momento. Entre em contato com a equipe Pred.IO.")
        return

    # ── Relatórios Executivos do Ativo — aparecem em destaque no topo ────────
    if df_exec is not None and not df_exec.empty:
        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;"
            f"margin:0.5rem 0 0.3rem;'>📄 Relatórios Executivos de Confiabilidade</p>",
            unsafe_allow_html=True,
        )
        for _, row in df_exec.iterrows():
            _render_card_executivo(row)
        st.markdown(f"<hr style='border-color:{COLOR_BORDER};margin:0.75rem 0;'/>",
                    unsafe_allow_html=True)

    # Relatórios técnicos publicados — aparecem antes dos legados
    if df_tech is not None and not df_tech.empty:
        for _, row in df_tech.iterrows():
            _render_card_tech(row)

    # Relatórios legados
    if not df_legacy.empty:
        for _, row in df_legacy.iterrows():
            _render_card_legacy(row)


def _render_card_tech(row) -> None:
    titulo     = str(row.get("Titulo",         "")).strip() or "Sem título"
    tipo       = str(row.get("Tipo_Servico",   "")).strip()
    sev        = str(row.get("Severidade",     "Normal")).strip()
    data       = str(row.get("Data_Relatorio", "")).strip()
    planta     = str(row.get("Planta",         "")).strip()
    equipamento= str(row.get("Equipamento",    "")).strip()
    resumo     = str(row.get("Resumo",         "")).strip()
    recomend   = str(row.get("Recomendacoes",  "")).strip()
    url        = str(row.get("Arquivo_Url",    "")).strip()

    sc, sb, sbo, st_ = _SEV_COLOR.get(sev.strip().lower(), ("#94A3B8","#F8FAFC","#CBD5E1","#475569"))

    meta = []
    if tipo:        meta.append(f"📋 {tipo}")
    if data:        meta.append(f"📅 {data}")
    if planta:      meta.append(f"🏭 {planta}")
    if equipamento: meta.append(f"⚙️ {equipamento}")
    meta_html = "  ·  ".join(
        f"<span style='color:{COLOR_MUTED};font-size:0.8rem;'>{m}</span>" for m in meta
    )

    col_info, col_btn = st.columns([5, 1])
    with col_info:
        rep_id = str(row.get("Id", "")).strip()
        at_id  = str(row.get("Ativo_Id", "")).strip()
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:5px solid {sc};border-radius:10px;"
            f"padding:14px 18px;margin-bottom:8px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-start;"
            f"flex-wrap:wrap;gap:6px;margin-bottom:5px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;'>{titulo}</span>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>"
            f"<span style='background:{sb};color:{st_};-webkit-text-fill-color:{st_};"
            f"border:1px solid {sbo};font-size:0.68rem;font-weight:700;"
            f"padding:2px 10px;border-radius:12px;'>{sev}</span>"
            f"<span style='background:#F0FDF4;color:#065F46;-webkit-text-fill-color:#065F46;"
            f"border:1px solid #86EFAC;font-size:0.68rem;font-weight:700;"
            f"padding:2px 10px;border-radius:12px;'>Disponível</span>"
            f"</div></div>"
            f"<div style='margin-bottom:6px;'>{meta_html}</div>"
            + (f"<p style='color:#475569;font-size:0.83rem;margin:0 0 4px;'>{resumo}</p>"
               if resumo and resumo.lower() not in ("", "nan") else "")
            + (f"<p style='color:#1E40AF;font-size:0.8rem;margin:4px 0 0;"
               f"background:#EFF6FF;border-radius:6px;padding:5px 10px;'>"
               f"💡 {recomend[:200]}{'…' if len(recomend)>200 else ''}</p>"
               if recomend and recomend.lower() not in ("", "nan") else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        # Botão "Abrir chamado sobre este relatório"
        if st.button("🔧 Abrir chamado", key=f"relch_{rep_id or titulo[:20]}",
                     use_container_width=False):
            desc_parts = [f"Relatório: {titulo}"]
            if resumo and resumo.lower() not in ("", "nan"):
                desc_parts.append(f"Resumo: {resumo[:300]}")
            if recomend and recomend.lower() not in ("", "nan"):
                desc_parts.append(f"Recomendações: {recomend[:300]}")
            st.session_state["abrir_chamado_titulo"]    = f"Dúvida sobre relatório: {titulo}"
            st.session_state["abrir_chamado_descricao"] = "\n\n".join(desc_parts)
            st.session_state["abrir_chamado_categoria"] = "Relatório técnico"
            st.session_state["abrir_chamado_origem"]    = "Relatório Técnico"
            st.session_state["abrir_chamado_report_id"] = rep_id
            st.session_state["abrir_chamado_ativo_id"]  = at_id
            st.session_state["abrir_chamado_prioridade"]= (
                "Alta" if sev.lower() in ("urgente", "crítico", "critico") else "Média")
            st.session_state["portal_page"] = "chamados"
            st.rerun()
    with col_btn:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        if url and url.lower() not in ("", "nan", "none"):
            st.link_button("📄 Baixar", url, use_container_width=True)
        else:
            st.markdown(
                "<p style='color:#94a3b8;font-size:0.75rem;text-align:center;'>Indisponível</p>",
                unsafe_allow_html=True,
            )


def _render_card_executivo(row) -> None:
    """Card de relatório executivo publicado no Portal do Cliente.
    Nunca exibe obs_interna (já removida por get_relatorios_executivos_publicados).
    """
    titulo    = str(row.get("Titulo",               "Relatório Executivo")).strip()
    periodo_i = str(row.get("Periodo_Inicio",        "")).strip()
    periodo_f = str(row.get("Periodo_Fim",           "")).strip()
    publicado = str(row.get("Publicado_Em",          "")).strip()
    resumo_ex = str(row.get("Resumo_Executivo",      "")).strip()
    url_rev   = str(row.get("Arquivo_Revisado_Url",  "")).strip()
    versao    = str(row.get("Versao",                "1")).strip()

    periodo_str = f"{periodo_i} a {periodo_f}" if periodo_i and periodo_f else "—"
    pub_str = (f"  ·  <span style='color:{COLOR_MUTED};font-size:0.8rem;'>Publicado em: {publicado}</span>"
               if publicado else "")
    resumo_html = (
        f"<p style='color:#065F46;font-size:0.83rem;margin:4px 0 0;"
        f"background:#DCFCE7;border-radius:6px;padding:5px 10px;'>"
        f"📝 {resumo_ex[:300]}{'…' if len(resumo_ex)>300 else ''}</p>"
        if resumo_ex and resumo_ex.lower() not in ("", "nan") else ""
    )

    col_info, col_btn = st.columns([5, 1])
    with col_info:
        st.markdown(
            f"<div style='background:#F0FDF4;border:1px solid #86EFAC;"
            f"border-left:5px solid #10B981;border-radius:10px;"
            f"padding:14px 18px;margin-bottom:8px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-start;"
            f"flex-wrap:wrap;gap:6px;margin-bottom:5px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;'>{titulo}</span>"
            f"<span style='background:#10B98122;color:#065F46;-webkit-text-fill-color:#065F46;"
            f"border:1px solid #86EFAC;font-size:0.68rem;font-weight:700;"
            f"padding:2px 10px;border-radius:12px;'>Publicado</span>"
            f"</div>"
            f"<div style='margin-bottom:6px;'>"
            f"<span style='color:{COLOR_MUTED};font-size:0.8rem;'>📋 Relatório Executivo de Confiabilidade</span>"
            f"  ·  <span style='color:{COLOR_MUTED};font-size:0.8rem;'>📅 Período: {periodo_str}</span>"
            f"{pub_str}"
            f"  ·  <span style='color:{COLOR_MUTED};font-size:0.8rem;'>Versão: {versao}</span>"
            f"</div>"
            f"{resumo_html}"
            f"<p style='color:{COLOR_MUTED};font-size:0.75rem;margin:6px 0 0;'>Fonte: Pred.IO</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        if url_rev and url_rev.lower() not in ("", "nan", "none"):
            st.link_button("⬇️ Baixar", url_rev, use_container_width=True)
        else:
            st.markdown(
                "<p style='color:#94a3b8;font-size:0.75rem;text-align:center;margin-top:8px;'>"
                "Disponível<br>em breve</p>",
                unsafe_allow_html=True,
            )


def _render_card_legacy(row) -> None:
    titulo  = str(row.get("Titulo",         "")).strip() or "Sem título"
    tipo    = str(row.get("Tipo_Servico",   "")).strip()
    data    = str(row.get("Data_Relatorio", "")).strip()
    planta  = str(row.get("Planta",         "")).strip()
    equip   = str(row.get("Equipamento",    "")).strip()
    resumo  = str(row.get("Resumo",         "")).strip()
    url     = str(row.get("Arquivo_Url",    "")).strip()
    status  = str(row.get("Status",         "Disponível")).strip()

    status_color = "#22c55e" if status.lower() == "disponível" else "#94a3b8"

    meta = []
    if tipo:   meta.append(f"📋 {tipo}")
    if data:   meta.append(f"📅 {data}")
    if planta: meta.append(f"🏭 {planta}")
    if equip:  meta.append(f"⚙️ {equip}")
    meta_html = "  ·  ".join(
        f"<span style='color:{COLOR_MUTED};font-size:0.8rem;'>{m}</span>" for m in meta
    )

    col_info, col_btn = st.columns([5, 1])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:5px solid {COLOR_BLUE};border-radius:10px;"
            f"padding:14px 18px;margin-bottom:8px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;'>{titulo}</span>"
            f"<span style='background:{status_color};color:#fff;-webkit-text-fill-color:#fff;"
            f"font-size:0.72rem;font-weight:700;padding:2px 10px;border-radius:12px;'>{status}</span>"
            f"</div>"
            f"<div style='margin-top:6px;'>{meta_html}</div>"
            + (f"<p style='color:#475569;font-size:0.83rem;margin:8px 0 0;'>{resumo}</p>"
               if resumo and resumo.lower() not in ("", "nan") else "")
            + "</div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        if url and url.lower() not in ("", "nan", "none"):
            st.link_button("📄 Baixar", url, use_container_width=True)
        else:
            st.markdown(
                "<p style='color:#94a3b8;font-size:0.75rem;text-align:center;'>Indisponível</p>",
                unsafe_allow_html=True,
            )
