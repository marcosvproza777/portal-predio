"""Supervisão Pred.IO — Lista de Chamados Técnicos."""
import streamlit as st
from auth import require_staff
from sheets import get_all_chamados, delete_chamado
from ui import (sv_page_header, COLOR_NAVY, COLOR_BORDER, COLOR_CARD,
                COLOR_MUTED, STATUS_CFG, PRIORIDADE_CFG)

_TODOS_STATUS = [
    "Todos", "Aberto", "Em análise", "Em andamento",
    "Aguardando cliente", "Concluído", "Cancelado", "Reaberto",
]
_TODAS_PRIO = ["Todas", "Crítica", "Alta", "Média", "Baixa"]
_TODAS_ORIGENS = [
    "Todas", "Portal do Cliente", "Assistente Técnico",
    "Alerta", "Relatório Técnico", "Plano de Manutenção", "Supervisão Pred.IO",
]
_TODAS_CAT = [
    "Todas", "Dúvida técnica", "Alarme", "Falha operacional",
    "Manutenção vencida", "Manutenção próxima", "Relatório técnico",
    "Recomendação por condição", "Óleo e lubrificação",
    "Vibração", "Termografia", "Painel Mypro Touch", "Painel Mypro Touch AD",
    "Motor elétrico", "Rolamento", "Overhaul por condição", "Outro",
]
_ORIGEM_ICON = {
    "Portal do Cliente":    "🖥️",
    "Assistente Técnico":   "🤖",
    "Alerta":               "🔔",
    "Relatório Técnico":    "📁",
    "Plano de Manutenção":  "📅",
    "Supervisão Pred.IO":   "⚙️",
}


def render() -> None:
    require_staff()
    sv_page_header(
        "🔧 Chamados Técnicos",
        "Todas as solicitações — filtre, pesquise e abra o chamado para responder",
    )

    # ── Novo chamado pela supervisão ──────────────────────────────────────────
    if st.button("➕ Abrir chamado (supervisão)", key="_svch_novo"):
        st.session_state["sv_view"]       = "chamado_detalhe"
        st.session_state["sv_chamado_id"] = "__novo__"
        st.rerun()

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            f_cliente  = st.text_input("Cliente", placeholder="Nome da empresa")
            f_ativo    = st.text_input("Ativo ID", placeholder="Ex: AT-2026-001")
        with c2:
            f_status   = st.selectbox("Status", _TODOS_STATUS)
            f_cat      = st.selectbox("Categoria", _TODAS_CAT)
        with c3:
            f_prioridade  = st.selectbox("Prioridade", _TODAS_PRIO)
            f_origem      = st.selectbox("Origem", _TODAS_ORIGENS)

        c4, c5, c6 = st.columns(3)
        with c4:
            f_texto    = st.text_input("🔎 Busca livre", placeholder="Título, descrição…")
            f_responsavel = st.text_input("Responsável", placeholder="Nome do técnico")
        with c5:
            f_data_ini = st.date_input("Data início", value=None)
        with c6:
            f_data_fim = st.date_input("Data fim", value=None)

    filtros = {
        "cliente":     f_cliente.strip() or None,
        "ativo":       f_ativo.strip() or None,
        "status":      None if f_status      == "Todos"  else f_status,
        "categoria":   None if f_cat         == "Todas"  else f_cat,
        "prioridade":  None if f_prioridade  == "Todas"  else f_prioridade,
        "origem":      None if f_origem      == "Todas"  else f_origem,
        "responsavel": f_responsavel.strip() or None,
        "texto":       f_texto.strip() or None,
        "data_ini":    str(f_data_ini) if f_data_ini else None,
        "data_fim":    str(f_data_fim) if f_data_fim else None,
    }
    filtros_ativos = {k: v for k, v in filtros.items() if v}

    df = get_all_chamados(filtros_ativos if filtros_ativos else None)

    # Aplicar filtros extras que get_all_chamados pode não suportar ainda
    if filtros_ativos.get("ativo") and not df.empty and "Ativo_Id" in df.columns:
        av = filtros_ativos["ativo"].lower()
        df = df[df["Ativo_Id"].str.strip().str.lower().str.contains(av, na=False)]
    if filtros_ativos.get("categoria") and not df.empty and "Categoria" in df.columns:
        df = df[df["Categoria"].str.strip() == filtros_ativos["categoria"]]
    if filtros_ativos.get("origem") and not df.empty and "Origem" in df.columns:
        df = df[df["Origem"].str.strip() == filtros_ativos["origem"]]

    # ── Métricas rápidas ──────────────────────────────────────────────────────
    if not df.empty:
        n_aberto  = len(df[df.get("Status", df.columns[0]).str.strip() == "Aberto"]) \
                    if "Status" in df.columns else 0
        n_critico = len(df[df.get("Prioridade", df.columns[0]).str.strip() == "Crítica"]) \
                    if "Prioridade" in df.columns else 0
        mc = st.columns(3)
        for col, (label, val, cor) in zip(mc, [
            ("Total", len(df), COLOR_NAVY),
            ("Abertos", n_aberto, "#EF4444"),
            ("Críticos", n_critico, "#7C3AED"),
        ]):
            with col:
                st.markdown(
                    f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                    f"border-left:3px solid {cor};border-radius:8px;"
                    f"padding:0.6rem 1rem;text-align:center;margin-bottom:0.5rem;'>"
                    f"<p style='font-size:0.65rem;color:{COLOR_MUTED};margin:0 0 2px;"
                    f"text-transform:uppercase;'>{label}</p>"
                    f"<p style='font-size:1.4rem;font-weight:900;color:{cor};margin:0;'>{val}</p>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.85rem;margin:0.25rem 0 0.75rem;'>"
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
    ativo_id    = str(row.get("Ativo_Id",        "")).strip()
    categoria   = str(row.get("Categoria",       "")).strip()
    origem      = str(row.get("Origem",          "")).strip()
    descricao   = str(row.get("Descricao",       "")).strip()
    prioridade  = str(row.get("Prioridade",      "Baixa")).strip()
    status      = str(row.get("Status",          "Aberto")).strip()
    data_ab     = str(row.get("Aberto_Em",
                    row.get("Data_Abertura",   ""))).strip()[:16]
    data_up     = str(row.get("Atualizado_Em",
                    row.get("Data_Atualizacao",""))).strip()[:16]
    responsavel = str(row.get("Responsavel",     "")).strip()
    report_id   = str(row.get("Report_Id",       "")).strip()
    task_id     = str(row.get("Maintenance_Task_Id", "")).strip()
    alert_id    = str(row.get("Alert_Id",        "")).strip()

    pr_bg, pr_tc = PRIORIDADE_CFG.get(prioridade.lower(), ("#94A3B8", "#fff"))
    st_bg, st_tc = STATUS_CFG.get(status.lower(), ("#94A3B8", "#fff"))

    meta = []
    if empresa:    meta.append(f"🏢 {empresa}")
    if ativo_id:   meta.append(f"⚙️ {ativo_id}")
    if categoria:  meta.append(f"🏷️ {categoria}")
    if origem:     meta.append(f"{_ORIGEM_ICON.get(origem,'🔗')} {origem}")
    meta_str = "   ·   ".join(meta)

    vinculos = []
    if report_id: vinculos.append(f"📁 {report_id}")
    if task_id:   vinculos.append(f"📅 {task_id}")
    if alert_id:  vinculos.append(f"🔔 {alert_id}")

    rodape = []
    if chamado_id:  rodape.append(f"#{chamado_id}")
    if data_ab:     rodape.append(f"Aberto {data_ab}")
    if data_up:     rodape.append(f"Atualizado {data_up}")
    if responsavel: rodape.append(f"👤 {responsavel}")
    else:           rodape.append("Sem responsável")
    if vinculos:    rodape.append("🔗 " + " · ".join(vinculos))
    rodape_str = "  ·  ".join(rodape)

    with st.container():
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:5px solid {pr_bg};border-radius:12px;"
            f"padding:14px 18px 10px;margin-bottom:4px;'>"
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
            + (f"<p style='color:#64748B;font-size:0.82rem;margin:0 0 6px;'>{meta_str}</p>"
               if meta_str else "")
            + (f"<p style='color:#475569;font-size:0.85rem;margin:0 0 8px;"
               f"background:#F8FAFC;border-radius:6px;padding:8px 10px;line-height:1.5;'>"
               f"{descricao[:220]}{'…' if len(descricao) > 220 else ''}</p>"
               if descricao else "")
            + f"<p style='color:#94A3B8;font-size:0.75rem;margin:0;'>{rodape_str}</p>"
            + "</div>",
            unsafe_allow_html=True,
        )

        col_esp, col_btn, col_del = st.columns([3, 1, 0.4])
        with col_btn:
            if st.button("👁️ Ver chamado", key=f"sv_ver_{idx}",
                         use_container_width=True, type="primary"):
                st.session_state["sv_view"]       = "chamado_detalhe"
                st.session_state["sv_chamado_id"] = chamado_id
                st.rerun()
        with col_del:
            confirmar = st.session_state.get(f"_del_ch_{chamado_id}", False)
            if not confirmar:
                if st.button("🗑️", key=f"sv_del1_{idx}", help="Excluir chamado",
                             use_container_width=True):
                    st.session_state[f"_del_ch_{chamado_id}"] = True
                    st.rerun()
            else:
                if st.button("✅ Confirmar", key=f"sv_del2_{idx}",
                             use_container_width=True, type="primary"):
                    ok, erro = delete_chamado(chamado_id)
                    if ok:
                        st.session_state.pop(f"_del_ch_{chamado_id}", None)
                        st.toast("🗑️ Chamado excluído.")
                        st.rerun()
                    else:
                        st.error(f"❌ Não foi possível excluir: {erro}")
                if st.button("✖ Cancelar", key=f"sv_del3_{idx}",
                             use_container_width=True):
                    st.session_state.pop(f"_del_ch_{chamado_id}", None)
                    st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
