"""Supervisão Pred.IO — Dashboard."""
import pandas as pd
import streamlit as st
from auth import require_staff
from sheets import get_all_chamados
from ui import (sv_metric_card, sv_page_header,
                COLOR_NAVY, COLOR_BORDER, COLOR_CARD,
                STATUS_CFG, PRIORIDADE_CFG)


def render() -> None:
    require_staff()
    sv_page_header("Dashboard", "Visão geral dos chamados e atividade dos clientes")

    df = get_all_chamados()

    # ── Métricas ──────────────────────────────────────────────────────────────
    total        = len(df)
    abertos      = _count(df, "Status",    "Aberto")
    criticos     = _count(df, "Prioridade","Crítica")
    em_andamento = _count(df, "Status",    "Em andamento")
    aguardando   = _count(df, "Status",    "Aguardando cliente")

    hoje = pd.Timestamp("today").strftime("%Y-%m")
    concluidos_mes  = 0
    clientes_ativos = 0
    if not df.empty and "Data_Abertura" in df.columns:
        df["_dt"] = pd.to_datetime(df["Data_Abertura"], dayfirst=True, errors="coerce")
        concluidos_mes = len(df[
            (df["Status"].str.lower().str.strip() == "concluído") &
            (df["_dt"].dt.to_period("M").astype(str) == hoje)
        ])
        clientes_ativos = df[
            df["Status"].str.lower().str.strip().isin(
                ["aberto", "em andamento", "em análise", "aguardando cliente"])
        ]["Empresa"].nunique()

    c1, c2, c3 = st.columns(3)
    with c1:
        sv_metric_card("🔧", "Chamados Abertos",   abertos,      "#3B82F6",
                       f"{total} no total")
    with c2:
        sv_metric_card("🔴", "Críticos Ativos",    criticos,     "#EF4444",
                       "Atenção imediata" if criticos else "Nenhum crítico")
    with c3:
        sv_metric_card("⚡", "Em Andamento",       em_andamento, "#0F1F3D")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        sv_metric_card("⏳", "Aguardando Cliente", aguardando,      "#D97706")
    with c5:
        sv_metric_card("✅", "Concluídos no Mês",  concluidos_mes,  "#10B981")
    with c6:
        sv_metric_card("👥", "Clientes Ativos",    clientes_ativos, "#6366F1")

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── Chamados recentes ─────────────────────────────────────────────────────
    st.markdown(
        f"<h3 style='color:{COLOR_NAVY};font-size:1.1rem;font-weight:700;margin:0 0 0.75rem;'>"
        f"Últimas Solicitações</h3>",
        unsafe_allow_html=True,
    )

    recentes = df.head(10) if not df.empty else df
    if recentes.empty:
        st.info("Nenhum chamado encontrado.")
        return

    for idx, (_, row) in enumerate(recentes.iterrows()):
        _render_chamado_card(row, idx)


def _count(df: pd.DataFrame, col: str, valor: str) -> int:
    if df.empty or col not in df.columns:
        return 0
    return len(df[df[col].str.strip().str.lower() == valor.lower()])


def _render_chamado_card(row, idx: int) -> None:
    chamado_id  = str(row.get("Id",           "")).strip()
    titulo      = str(row.get("Titulo",       "Sem título")).strip()
    empresa     = str(row.get("Empresa",      "")).strip()
    planta      = str(row.get("Planta",       "")).strip()
    equipamento = str(row.get("Equipamento",  "")).strip()
    descricao   = str(row.get("Descricao",    "")).strip()
    prioridade  = str(row.get("Prioridade",   "Baixa")).strip()
    status      = str(row.get("Status",       "Aberto")).strip()
    data_ab     = str(row.get("Data_Abertura","")).strip()[:16]
    responsavel = str(row.get("Responsavel",  "")).strip()

    pr_bg, pr_tc = PRIORIDADE_CFG.get(prioridade.lower(), ("#94A3B8", "#fff"))
    st_bg, st_tc = STATUS_CFG.get(status.lower(), ("#94A3B8", "#fff"))

    meta = []
    if empresa:     meta.append(f"🏢 {empresa}")
    if planta:      meta.append(f"🏭 {planta}")
    if equipamento: meta.append(f"⚙️ {equipamento}")
    if data_ab:     meta.append(f"📅 {data_ab}")
    if responsavel: meta.append(f"👤 {responsavel}")
    meta_str = "   ·   ".join(meta)

    # Card + botão dentro do mesmo container
    with st.container():
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:5px solid {pr_bg};border-radius:12px;"
            f"padding:14px 18px 10px;margin-bottom:4px;'>"

            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:flex-start;flex-wrap:wrap;gap:6px;margin-bottom:6px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;'>{titulo}</span>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>"
            f"<span style='background:{pr_bg};color:{pr_tc};-webkit-text-fill-color:{pr_tc};"
            f"font-size:0.72rem;font-weight:700;padding:3px 12px;border-radius:20px;'>{prioridade}</span>"
            f"<span style='background:{st_bg};color:{st_tc};-webkit-text-fill-color:{st_tc};"
            f"font-size:0.72rem;font-weight:700;padding:3px 12px;border-radius:20px;'>{status}</span>"
            f"</div></div>"

            f"<p style='color:#64748B;font-size:0.8rem;margin:0 0 6px;'>{meta_str}</p>"

            + (f"<p style='color:#475569;font-size:0.85rem;margin:0;"
               f"background:#F8FAFC;border-radius:6px;padding:8px 10px;'>"
               f"{descricao[:200]}{'…' if len(descricao) > 200 else ''}</p>"
               if descricao else "")

            + "</div>",
            unsafe_allow_html=True,
        )

        col_esp, col_btn = st.columns([3, 1])
        with col_btn:
            if st.button("👁️ Ver chamado", key=f"dash_ver_{idx}",
                         use_container_width=True, type="primary"):
                st.session_state["sv_view"]       = "chamado_detalhe"
                st.session_state["sv_chamado_id"] = chamado_id
                st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
