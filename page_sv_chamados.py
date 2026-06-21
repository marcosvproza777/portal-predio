"""Supervisão Pred.IO — Lista de Chamados Técnicos."""
import streamlit as st
from auth import require_staff
from sheets import get_all_chamados
from ui import (sv_page_header, COLOR_NAVY, COLOR_BORDER, COLOR_CARD,
                STATUS_CFG, PRIORIDADE_CFG)

_TODOS_STATUS = [
    "Todos", "Aberto", "Em análise", "Em andamento",
    "Aguardando cliente", "Concluído", "Cancelado", "Reaberto",
]
_TODAS_PRIO = ["Todas", "Crítica", "Alta", "Média", "Baixa"]


def render() -> None:
    require_staff()
    sv_page_header(
        "🔧 Chamados Técnicos",
        "Todas as solicitações de clientes — filtre, pesquise e gerencie",
    )

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            f_cliente    = st.text_input("Cliente", placeholder="Nome da empresa")
            f_equipamento= st.text_input("Equipamento", placeholder="Ex: Bomba B-204")
        with c2:
            f_status     = st.selectbox("Status", _TODOS_STATUS)
            f_planta     = st.text_input("Planta", placeholder="Ex: Jacarepaguá")
        with c3:
            f_prioridade = st.selectbox("Prioridade", _TODAS_PRIO)
            f_responsavel= st.text_input("Responsável", placeholder="Nome do técnico")

        c4, c5, c6 = st.columns(3)
        with c4:
            f_texto  = st.text_input("🔎 Busca por texto", placeholder="Título, descrição, equipamento…")
        with c5:
            f_data_ini = st.date_input("Data início", value=None)
        with c6:
            f_data_fim = st.date_input("Data fim", value=None)

    filtros = {
        "cliente":     f_cliente.strip()     or None,
        "status":      None if f_status     == "Todos"  else f_status,
        "prioridade":  None if f_prioridade == "Todas"  else f_prioridade,
        "planta":      f_planta.strip()      or None,
        "equipamento": f_equipamento.strip() or None,
        "responsavel": f_responsavel.strip() or None,
        "texto":       f_texto.strip()       or None,
        "data_ini":    str(f_data_ini)       if f_data_ini else None,
        "data_fim":    str(f_data_fim)       if f_data_fim else None,
    }
    filtros_ativos = {k: v for k, v in filtros.items() if v}

    df = get_all_chamados(filtros_ativos if filtros_ativos else None)

    st.markdown(
        f"<p style='color:#64748B;font-size:0.85rem;margin:0.5rem 0;'>"
        f"{len(df)} chamado(s) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("Nenhum chamado encontrado com os filtros aplicados.")
        return

    # ── Listagem ──────────────────────────────────────────────────────────────
    for _, row in df.iterrows():
        _render_card(row)


def _render_card(row) -> None:
    chamado_id  = str(row.get("Id",           "")).strip()
    titulo      = str(row.get("Titulo",       "Sem título")).strip()
    empresa     = str(row.get("Empresa",      "")).strip()
    planta      = str(row.get("Planta",       "")).strip()
    equipamento = str(row.get("Equipamento",  "")).strip()
    descricao   = str(row.get("Descricao",    "")).strip()
    prioridade  = str(row.get("Prioridade",   "Baixa")).strip()
    status      = str(row.get("Status",       "Aberto")).strip()
    data_ab     = str(row.get("Data_Abertura","")).strip()[:16]
    data_up     = str(row.get("Data_Atualizacao","")).strip()[:16]
    responsavel = str(row.get("Responsavel",  "")).strip()

    pr_bg, pr_tc = PRIORIDADE_CFG.get(prioridade.lower(), ("#94A3B8", "#fff"))
    st_bg, st_tc = STATUS_CFG.get(status.lower(), ("#94A3B8", "#fff"))

    pr_pill = (f"<span style='background:{pr_bg};color:{pr_tc};"
               f"-webkit-text-fill-color:{pr_tc};font-size:0.72rem;font-weight:700;"
               f"padding:3px 12px;border-radius:20px;white-space:nowrap;'>{prioridade}</span>")
    st_pill = (f"<span style='background:{st_bg};color:{st_tc};"
               f"-webkit-text-fill-color:{st_tc};font-size:0.72rem;font-weight:700;"
               f"padding:3px 12px;border-radius:20px;white-space:nowrap;'>{status}</span>")
    id_pill = (f"<span style='background:#F1F5F9;color:#64748B;"
               f"-webkit-text-fill-color:#64748B;font-size:0.7rem;font-weight:600;"
               f"padding:2px 10px;border-radius:20px;'>{chamado_id}</span>"
               if chamado_id else "")

    meta = []
    if empresa:     meta.append(f"🏢 {empresa}")
    if planta:      meta.append(f"🏭 {planta}")
    if equipamento: meta.append(f"⚙️ {equipamento}")
    meta_html = "  ·  ".join(
        f"<span style='color:#64748B;font-size:0.78rem;'>{m}</span>" for m in meta
    )

    datas_html = ""
    if data_ab:
        datas_html += f"<span style='color:#94A3B8;font-size:0.75rem;'>📅 Aberto {data_ab}</span>"
    if data_up:
        datas_html += f"<span style='color:#94A3B8;font-size:0.75rem;margin-left:12px;'>🔄 {data_up}</span>"
    if responsavel:
        datas_html += f"<span style='color:#94A3B8;font-size:0.75rem;margin-left:12px;'>👤 {responsavel}</span>"

    col_info, col_btn = st.columns([8, 1])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:5px solid {pr_bg};border-radius:10px;"
            f"padding:14px 18px;margin-bottom:8px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"flex-wrap:wrap;gap:6px;margin-bottom:6px;'>"
            f"<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;'>{titulo}</span>"
            f"{id_pill}</div>"
            f"<div style='display:flex;gap:6px;'>{pr_pill} {st_pill}</div>"
            f"</div>"
            f"<div style='margin-bottom:5px;'>{meta_html}</div>"
            + (f"<p style='color:#475569;font-size:0.83rem;margin:4px 0;'>"
               f"{descricao[:180]}{'…' if len(descricao) > 180 else ''}</p>"
               if descricao else "")
            + (f"<div style='margin-top:6px;'>{datas_html}</div>" if datas_html else "")
            + "</div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        if st.button("Ver →", key=f"sv_ver_{chamado_id}_{id(row)}",
                     use_container_width=True):
            st.session_state["sv_view"]       = "chamado_detalhe"
            st.session_state["sv_chamado_id"] = chamado_id
            st.rerun()
