"""Supervisão Pred.IO — Clientes e Histórico."""
import streamlit as st
from auth import require_staff
from sheets import get_all_clientes, get_historico_cliente, get_all_chamados
from ui import (sv_page_header, sv_metric_card, COLOR_NAVY, COLOR_BLUE,
                COLOR_BORDER, COLOR_CARD, STATUS_CFG, PRIORIDADE_CFG)


def render() -> None:
    require_staff()
    sv_view = st.session_state.get("sv_view", "clientes")

    if sv_view == "cliente_historico":
        render_historico()
    else:
        _render_lista()


def _render_lista() -> None:
    sv_page_header("👥 Clientes", "Histórico e status por empresa")

    clientes = get_all_clientes()
    df_todos = get_all_chamados()

    if clientes.empty and df_todos.empty:
        st.info("Nenhum cliente encontrado.")
        return

    # Derivar lista de clientes dos chamados se a sheet Clientes estiver vazia
    if clientes.empty and not df_todos.empty and "Empresa" in df_todos.columns:
        empresas = (
            df_todos[["Empresa", "Client_Id", "Email"]]
            .drop_duplicates(subset=["Empresa"])
            .reset_index(drop=True)
        )
    else:
        empresas = clientes

    if empresas.empty:
        st.info("Nenhum cliente encontrado.")
        return

    st.markdown(
        f"<p style='color:#64748B;font-size:0.85rem;margin:0 0 1rem;'>"
        f"{len(empresas)} cliente(s) cadastrado(s)</p>",
        unsafe_allow_html=True,
    )

    for _, row in empresas.iterrows():
        empresa    = str(row.get("Empresa",   "")).strip()
        client_id  = str(row.get("Client_Id", empresa.lower())).strip()
        email      = str(row.get("Email",     "")).strip()

        # Métricas do cliente
        if not df_todos.empty and "Empresa" in df_todos.columns:
            df_cli  = df_todos[df_todos["Empresa"].str.strip().str.lower() == empresa.lower()]
            total   = len(df_cli)
            abertos = len(df_cli[df_cli.get("Status", "").str.lower().str.strip() == "aberto"]) \
                      if "Status" in df_cli.columns else 0
            criticos= len(df_cli[df_cli.get("Prioridade", "").str.lower().str.strip() == "crítica"]) \
                      if "Prioridade" in df_cli.columns else 0
        else:
            total = abertos = criticos = 0

        resumo = []
        if total:     resumo.append(f"<strong>{total}</strong> chamado(s)")
        if abertos:   resumo.append(f"<strong style='color:#3B82F6;'>{abertos}</strong> aberto(s)")
        if criticos:  resumo.append(f"<strong style='color:#EF4444;'>{criticos}</strong> crítico(s)")
        if email:     resumo.append(f"✉️ {email}")
        resumo_html = "  ·  ".join(
            f"<span style='font-size:0.8rem;color:#475569;'>{r}</span>" for r in resumo
        )

        col_info, col_btn = st.columns([7, 1])
        with col_info:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-left:4px solid {COLOR_BLUE};border-radius:10px;"
                f"padding:14px 18px;margin-bottom:8px;'>"
                f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;'>"
                f"🏢 {empresa}</span>"
                f"<div style='margin-top:5px;'>{resumo_html}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            if st.button("Histórico →", key=f"sv_cli_{client_id}_{id(row)}",
                         use_container_width=True):
                st.session_state["sv_view"]      = "cliente_historico"
                st.session_state["sv_cliente_id"]= client_id
                st.session_state["sv_cliente_nome"] = empresa
                st.rerun()


def render_historico() -> None:
    client_id = st.session_state.get("sv_cliente_id", "")
    empresa   = st.session_state.get("sv_cliente_nome", client_id)

    sv_page_header(
        f"📋 {empresa}",
        subtitle="Histórico completo do cliente",
        back_label="Clientes",
        back_view="clientes",
    )

    if not client_id:
        st.warning("Cliente não identificado.")
        return

    historico = get_historico_cliente(client_id)
    chamados   = historico.get("chamados",   None)
    relatorios = historico.get("relatorios", None)

    import pandas as pd
    if chamados is None:
        chamados = pd.DataFrame()
    if relatorios is None:
        relatorios = pd.DataFrame()

    # ── Métricas ──────────────────────────────────────────────────────────────
    total_cham  = len(chamados)
    abertos     = 0
    criticos    = 0
    concluidos  = 0
    ultimo_cham = "—"

    if not chamados.empty:
        if "Status" in chamados.columns:
            status_lower = chamados["Status"].str.strip().str.lower()
            abertos    = len(chamados[status_lower == "aberto"])
            concluidos = len(chamados[status_lower == "concluído"])
        if "Prioridade" in chamados.columns:
            criticos = len(chamados[chamados["Prioridade"].str.strip().str.lower() == "crítica"])
        if "Data_Abertura" in chamados.columns:
            ultimo_cham = chamados.iloc[0].get("Data_Abertura", "—")
            ultimo_cham = str(ultimo_cham)[:10] if ultimo_cham else "—"

    total_rel   = len(relatorios)
    ultimo_rel  = "—"
    if not relatorios.empty and "Data_Relatorio" in relatorios.columns:
        ultimo_rel = str(relatorios.iloc[0].get("Data_Relatorio", "—"))[:10]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sv_metric_card("🔧", "Total de Chamados", total_cham, "#3B82F6")
    with c2:
        sv_metric_card("🔴", "Chamados Críticos", criticos, "#EF4444")
    with c3:
        sv_metric_card("✅", "Concluídos", concluidos, "#10B981")
    with c4:
        sv_metric_card("📁", "Relatórios", total_rel, "#6366F1")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Tabs: Chamados / Relatórios ───────────────────────────────────────────
    tab_cham, tab_rel = st.tabs(["🔧 Chamados", "📁 Relatórios"])

    with tab_cham:
        if chamados.empty:
            st.info("Nenhum chamado registrado para este cliente.")
        else:
            for _, row in chamados.iterrows():
                _render_chamado_mini(row)

    with tab_rel:
        if relatorios.empty:
            st.info("Nenhum relatório registrado para este cliente.")
        else:
            for _, row in relatorios.iterrows():
                _render_relatorio_mini(row)


def _render_chamado_mini(row) -> None:
    chamado_id  = str(row.get("Id",          "")).strip()
    titulo      = str(row.get("Titulo",      "Sem título")).strip()
    planta      = str(row.get("Planta",      "")).strip()
    equipamento = str(row.get("Equipamento", "")).strip()
    prioridade  = str(row.get("Prioridade",  "Baixa")).strip()
    status      = str(row.get("Status",      "Aberto")).strip()
    data_ab     = str(row.get("Data_Abertura","")).strip()[:10]

    pr_bg, pr_tc = PRIORIDADE_CFG.get(prioridade.lower(), ("#94A3B8", "#fff"))
    st_bg, st_tc = STATUS_CFG.get(status.lower(), ("#94A3B8", "#fff"))

    col_info, col_btn = st.columns([7, 1])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {pr_bg};border-radius:8px;"
            f"padding:10px 14px;margin-bottom:6px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"flex-wrap:wrap;gap:6px;'>"
            f"<span style='font-weight:600;color:{COLOR_NAVY};font-size:0.9rem;'>{titulo}</span>"
            f"<div style='display:flex;gap:5px;'>"
            f"<span style='background:{pr_bg};color:{pr_tc};-webkit-text-fill-color:{pr_tc};"
            f"font-size:0.7rem;font-weight:700;padding:2px 10px;border-radius:20px;'>{prioridade}</span>"
            f"<span style='background:{st_bg};color:{st_tc};-webkit-text-fill-color:{st_tc};"
            f"font-size:0.7rem;font-weight:700;padding:2px 10px;border-radius:20px;'>{status}</span>"
            f"</div></div>"
            f"<div style='margin-top:4px;font-size:0.78rem;color:#64748B;'>"
            + (f"🏭 {planta}  " if planta else "")
            + (f"⚙️ {equipamento}  " if equipamento else "")
            + (f"📅 {data_ab}" if data_ab else "")
            + "</div></div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if chamado_id and st.button("Ver →", key=f"cli_cham_{chamado_id}_{id(row)}",
                                    use_container_width=True):
            st.session_state["sv_view"]       = "chamado_detalhe"
            st.session_state["sv_chamado_id"] = chamado_id
            st.rerun()


def _render_relatorio_mini(row) -> None:
    titulo  = str(row.get("Titulo",         "")).strip() or "Relatório"
    tipo    = str(row.get("Tipo_Servico",   "")).strip()
    data    = str(row.get("Data_Relatorio", "")).strip()[:10]
    planta  = str(row.get("Planta",         "")).strip()
    equip   = str(row.get("Equipamento",    "")).strip()
    url     = str(row.get("Arquivo_Url",    "")).strip()
    status  = str(row.get("Status",         "Disponível")).strip()

    status_color = "#22c55e" if status.lower() == "disponível" else "#94a3b8"

    col_info, col_btn = st.columns([7, 1])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {COLOR_BLUE};border-radius:8px;"
            f"padding:10px 14px;margin-bottom:6px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='font-weight:600;color:{COLOR_NAVY};font-size:0.9rem;'>{titulo}</span>"
            f"<span style='background:{status_color};color:#fff;-webkit-text-fill-color:#fff;"
            f"font-size:0.7rem;font-weight:700;padding:2px 10px;border-radius:12px;'>{status}</span>"
            f"</div>"
            f"<div style='font-size:0.78rem;color:#64748B;margin-top:4px;'>"
            + (f"📋 {tipo}  " if tipo else "")
            + (f"📅 {data}  " if data else "")
            + (f"🏭 {planta}  " if planta else "")
            + (f"⚙️ {equip}" if equip else "")
            + "</div></div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if url and url.lower() not in ("", "nan", "none"):
            st.link_button("📄", url, use_container_width=True)
