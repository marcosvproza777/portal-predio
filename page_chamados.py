"""Chamados Técnicos — abertura e listagem."""
import streamlit as st
from auth import current_client_id, current_email
from sheets import abrir_chamado, get_chamados
from ui import (page_header, empty_state, COLOR_NAVY, COLOR_BLUE,
                COLOR_CARD, COLOR_BORDER, PRIORIDADES, PRIORIDADE_CFG, STATUS_CFG, badge)


def render() -> None:
    page_header("🔧 Chamados Técnicos", "Solicite suporte técnico da equipe Pred.IO")

    client_id = current_client_id()
    email     = current_email()

    tab_novo, tab_lista = st.tabs(["➕ Novo Chamado", "📋 Meus Chamados"])

    with tab_novo:
        _form_novo_chamado(client_id, email)

    with tab_lista:
        _listar_chamados(client_id)


def _form_novo_chamado(client_id: str, email: str) -> None:
    st.markdown(
        f"<div style='background:#fff3cd;border:1px solid #ffc107;border-radius:8px;"
        f"padding:12px 16px;margin-bottom:1rem;font-size:0.88rem;color:#856404;'>"
        f"⚠️ Em caso de parada de máquina, risco à segurança ou emergência operacional, "
        f"use <strong>Prioridade Crítica</strong>. Nossa equipe entrará em contato "
        f"em até 1 hora.</div>",
        unsafe_allow_html=True,
    )

    with st.form("form_chamado", clear_on_submit=True):
        titulo = st.text_input("Título do chamado *",
                               placeholder="Ex: Vibração excessiva na bomba B-204")
        descricao = st.text_area("Descrição detalhada *",
                                 placeholder="Descreva o problema, sintomas observados e histórico recente…",
                                 height=130)
        c1, c2 = st.columns(2)
        with c1:
            planta = st.text_input("Planta", placeholder="Ex: Planta RJ")
        with c2:
            equipamento = st.text_input("Equipamento", placeholder="Ex: Bomba B-204")
        prioridade = st.selectbox("Prioridade", PRIORIDADES)

        submitted = st.form_submit_button("📨 Abrir Chamado", use_container_width=True)

    if submitted:
        if not titulo.strip() or not descricao.strip():
            st.warning("Preencha pelo menos o título e a descrição.")
            return
        ok = abrir_chamado(
            client_id=client_id,
            email=email,
            titulo=titulo.strip(),
            descricao=descricao.strip(),
            planta=planta.strip(),
            equipamento=equipamento.strip(),
            prioridade=prioridade,
        )
        if ok:
            st.success("✅ Chamado aberto com sucesso! Nossa equipe entrará em contato em breve.")
        else:
            st.error("Erro ao abrir o chamado. Tente novamente ou entre em contato por e-mail.")


def _listar_chamados(client_id: str) -> None:
    df = get_chamados(client_id)
    if df.empty:
        empty_state("Nenhum chamado encontrado.")
        return

    st.markdown(
        f"<p style='color:#64748b;font-size:0.85rem;'>{len(df)} chamado(s) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    for _, row in df.iterrows():
        titulo     = str(row.get("Titulo",       "")).strip() or "Sem título"
        descricao  = str(row.get("Descricao",    "")).strip()
        planta     = str(row.get("Planta",       "")).strip()
        equipamento= str(row.get("Equipamento",  "")).strip()
        prioridade = str(row.get("Prioridade",   "Baixa")).strip()
        status     = str(row.get("Status",       "Aberto")).strip()
        data_ab    = str(row.get("Data_Abertura","")).strip()

        st_color, st_text = STATUS_CFG.get(status.lower(), ("#94a3b8", "#fff"))
        pr_color, pr_text = PRIORIDADE_CFG.get(prioridade.lower(), ("#94a3b8", "#fff"))

        meta = []
        if data_ab:    meta.append(f"📅 {data_ab}")
        if planta:     meta.append(f"🏭 {planta}")
        if equipamento:meta.append(f"⚙️ {equipamento}")
        meta_html = "  ·  ".join(
            f"<span style='color:#64748b;font-size:0.78rem;'>{m}</span>" for m in meta
        )

        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:5px solid {pr_color};border-radius:10px;"
            f"padding:14px 18px;margin-bottom:10px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};'>{titulo}</span>"
            f"<div>{badge(prioridade, pr_color, pr_text)} {badge(status, st_color, st_text)}</div>"
            f"</div>"
            f"<div style='margin:6px 0;'>{meta_html}</div>"
            + (f"<p style='color:#475569;font-size:0.83rem;margin:6px 0 0;'>"
               f"{descricao[:200]}{'…' if len(descricao) > 200 else ''}</p>"
               if descricao else "")
            + "</div>",
            unsafe_allow_html=True,
        )
