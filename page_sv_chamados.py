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
        "Todas as solicitações — filtre, pesquise e abra o chamado para responder",
    )

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            f_cliente     = st.text_input("Cliente",     placeholder="Nome da empresa")
            f_equipamento = st.text_input("Equipamento", placeholder="Ex: Bomba B-204")
        with c2:
            f_status  = st.selectbox("Status",     _TODOS_STATUS)
            f_planta  = st.text_input("Planta",    placeholder="Ex: Jacarepaguá")
        with c3:
            f_prioridade  = st.selectbox("Prioridade", _TODAS_PRIO)
            f_responsavel = st.text_input("Responsável", placeholder="Nome do técnico")

        c4, c5, c6 = st.columns(3)
        with c4:
            f_texto    = st.text_input("🔎 Busca livre",
                                       placeholder="Título, descrição, equipamento…")
        with c5:
            f_data_ini = st.date_input("Data início", value=None)
        with c6:
            f_data_fim = st.date_input("Data fim",    value=None)

    filtros = {
        "cliente":     f_cliente.strip()      or None,
        "status":      None if f_status      == "Todos"  else f_status,
        "prioridade":  None if f_prioridade  == "Todas"  else f_prioridade,
        "planta":      f_planta.strip()       or None,
        "equipamento": f_equipamento.strip()  or None,
        "responsavel": f_responsavel.strip()  or None,
        "texto":       f_texto.strip()        or None,
        "data_ini":    str(f_data_ini)        if f_data_ini else None,
        "data_fim":    str(f_data_fim)        if f_data_fim else None,
    }
    filtros_ativos = {k: v for k, v in filtros.items() if v}

    df = get_all_chamados(filtros_ativos if filtros_ativos else None)

    st.markdown(
        f"<p style='color:#64748B;font-size:0.85rem;margin:0.5rem 0 1rem;'>"
        f"{len(df)} chamado(s) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("Nenhum chamado encontrado com os filtros aplicados.")
        return

    for idx, (_, row) in enumerate(df.iterrows()):
        _render_card(row, idx)


def _render_card(row, idx: int) -> None:
    chamado_id  = str(row.get("Id",              "")).strip()
    titulo      = str(row.get("Titulo",          "Sem título")).strip()
    empresa     = str(row.get("Empresa",         "")).strip()
    planta      = str(row.get("Planta",          "")).strip()
    equipamento = str(row.get("Equipamento",     "")).strip()
    descricao   = str(row.get("Descricao",       "")).strip()
    prioridade  = str(row.get("Prioridade",      "Baixa")).strip()
    status      = str(row.get("Status",          "Aberto")).strip()
    data_ab     = str(row.get("Data_Abertura",   "")).strip()[:16]
    data_up     = str(row.get("Data_Atualizacao","")).strip()[:16]
    responsavel = str(row.get("Responsavel",     "")).strip()

    pr_bg, pr_tc = PRIORIDADE_CFG.get(prioridade.lower(), ("#94A3B8", "#fff"))
    st_bg, st_tc = STATUS_CFG.get(status.lower(), ("#94A3B8", "#fff"))

    meta = []
    if empresa:     meta.append(f"🏢 {empresa}")
    if planta:      meta.append(f"🏭 {planta}")
    if equipamento: meta.append(f"⚙️ {equipamento}")
    meta_str = "   ·   ".join(meta)

    rodape = []
    if chamado_id:  rodape.append(f"#{chamado_id}")
    if data_ab:     rodape.append(f"Aberto {data_ab}")
    if data_up:     rodape.append(f"Atualizado {data_up}")
    if responsavel: rodape.append(f"👤 {responsavel}")
    else:           rodape.append("Sem responsável")
    rodape_str = "  ·  ".join(rodape)

    with st.container():
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:5px solid {pr_bg};border-radius:12px;"
            f"padding:14px 18px 10px;margin-bottom:4px;'>"

            # Linha 1: título + badges
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:6px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;"
            f"line-height:1.3;'>{titulo}</span>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;flex-shrink:0;'>"
            f"<span style='background:{pr_bg};color:{pr_tc};-webkit-text-fill-color:{pr_tc};"
            f"font-size:0.72rem;font-weight:700;padding:3px 12px;border-radius:20px;'>"
            f"{prioridade}</span>"
            f"<span style='background:{st_bg};color:{st_tc};-webkit-text-fill-color:{st_tc};"
            f"font-size:0.72rem;font-weight:700;padding:3px 12px;border-radius:20px;'>"
            f"{status}</span>"
            f"</div></div>"

            # Linha 2: empresa / planta / equipamento
            + (f"<p style='color:#64748B;font-size:0.82rem;margin:0 0 6px;'>{meta_str}</p>"
               if meta_str else "")

            # Descrição resumida
            + (f"<p style='color:#475569;font-size:0.85rem;margin:0 0 8px;"
               f"background:#F8FAFC;border-radius:6px;padding:8px 10px;line-height:1.5;'>"
               f"{descricao[:220]}{'…' if len(descricao) > 220 else ''}</p>"
               if descricao else "")

            # Rodapé: ID / datas / responsável
            + f"<p style='color:#94A3B8;font-size:0.75rem;margin:0;'>{rodape_str}</p>"

            + "</div>",
            unsafe_allow_html=True,
        )

        # Botão visível abaixo do card
        col_esp, col_btn = st.columns([3, 1])
        with col_btn:
            if st.button("👁️ Ver chamado", key=f"sv_ver_{idx}",
                         use_container_width=True, type="primary"):
                st.session_state["sv_view"]       = "chamado_detalhe"
                st.session_state["sv_chamado_id"] = chamado_id
                st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
