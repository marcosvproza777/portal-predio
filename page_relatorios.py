"""Meus Relatórios — listagem com filtros, download de PDF."""
import streamlit as st
from auth import current_client_id
from sheets import get_relatorios
from ui import (page_header, empty_state, COLOR_NAVY, COLOR_BLUE,
                COLOR_CARD, COLOR_BORDER, TIPOS_LAUDOS)


def render() -> None:
    page_header("📁 Meus Relatórios", "Acesse e baixe seus laudos técnicos")

    client_id = current_client_id()  # SEMPRE da sessão

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            tipo_opts = ["Todos"] + [label for _, label in TIPOS_LAUDOS]
            tipo_sel  = st.selectbox("Tipo de Serviço", tipo_opts)
        with c2:
            mes_opts = ["Todos"] + [str(m) for m in range(1, 13)]
            mes_sel  = st.selectbox("Mês", mes_opts)
        with c3:
            import datetime
            ano_atual = datetime.datetime.now().year
            ano_opts  = ["Todos"] + [str(a) for a in range(ano_atual, ano_atual - 6, -1)]
            ano_sel   = st.selectbox("Ano", ano_opts)

        c4, c5 = st.columns(2)
        with c4:
            planta_sel = st.text_input("Planta", placeholder="Ex: Planta RJ")
        with c5:
            equip_sel  = st.text_input("Equipamento", placeholder="Ex: Bomba B-204")

    filtros = {
        "tipo":       None if tipo_sel == "Todos" else tipo_sel,
        "mes":        None if mes_sel  == "Todos" else mes_sel,
        "ano":        None if ano_sel  == "Todos" else ano_sel,
        "planta":     planta_sel.strip() or None,
        "equipamento": equip_sel.strip() or None,
    }

    # ── Busca — client_id vem da sessão, nunca do front-end ──────────────────
    df = get_relatorios(client_id, {k: v for k, v in filtros.items() if v})

    st.markdown(
        f"<p style='color:#64748b;font-size:0.85rem;margin-bottom:0.5rem;'>"
        f"{len(df)} relatório(s) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info(
            "Nenhum relatório encontrado. "
            "Para aparecer aqui, adicione uma linha na aba **Relatorios** da planilha "
            "com a coluna **Empresa** igual ao nome da sua empresa cadastrada no login."
        )
        return

    # ── Listagem ──────────────────────────────────────────────────────────────
    for _, row in df.iterrows():
        _render_card(row)


def _render_card(row) -> None:
    titulo  = str(row.get("Titulo",         "")).strip() or "Sem título"
    tipo    = str(row.get("Tipo_Servico",   "")).strip()
    data    = str(row.get("Data_Relatorio", "")).strip()
    planta  = str(row.get("Planta",         "")).strip()
    equip   = str(row.get("Equipamento",    "")).strip()
    resumo  = str(row.get("Resumo",         "")).strip()
    url     = str(row.get("Arquivo_Url",    "")).strip()
    status  = str(row.get("Status",         "Disponível")).strip()

    status_color = "#22c55e" if status.lower() == "disponível" else "#94a3b8"

    col_info, col_btn = st.columns([5, 1])
    with col_info:
        meta = []
        if tipo:   meta.append(f"📋 {tipo}")
        if data:   meta.append(f"📅 {data}")
        if planta: meta.append(f"🏭 {planta}")
        if equip:  meta.append(f"⚙️ {equip}")
        meta_html = "  ·  ".join(
            f"<span style='color:#64748b;font-size:0.8rem;'>{m}</span>" for m in meta
        )
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
