"""Assistente Técnico Pred.IO — chat com histórico."""
import streamlit as st
from auth import current_client_id, current_empresa, current_email
from assistant import call_assistant, is_critical
from sheets import salvar_log_assistente, get_historico_assistente
from ui import page_header, COLOR_NAVY, COLOR_BLUE, COLOR_CYAN, COLOR_CARD, COLOR_BORDER


AVISO_SEGURANCA = (
    "ℹ️ **Aviso:** As respostas são baseadas nos relatórios disponíveis no portal. "
    "Em caso de condição crítica de máquina ou risco operacional, acione imediatamente "
    "a equipe técnica da Pred.IO abrindo um **Chamado Técnico**."
)

AVISO_CRITICO = (
    "⚠️ **Situação crítica detectada.** Recomendamos abrir um chamado técnico "
    "imediatamente para suporte emergencial da equipe Pred.IO."
)


def render() -> None:
    page_header("🤖 Assistente Técnico Pred.IO",
                "Tire dúvidas sobre seus equipamentos e relatórios")

    client_id = current_client_id()  # NUNCA do front-end
    empresa   = current_empresa()
    email     = current_email()

    st.info(AVISO_SEGURANCA)

    # ── Inicializa histórico da sessão ────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # ── Formulário de pergunta ────────────────────────────────────────────────
    with st.form("chat_form", clear_on_submit=True):
        pergunta = st.text_area(
            "Sua pergunta",
            placeholder="Ex: Qual é o status do compressor da Planta RJ no último relatório?",
            height=90,
            label_visibility="collapsed",
        )
        col_btn, col_hist = st.columns([2, 3])
        with col_btn:
            enviar = st.form_submit_button("📨  Enviar pergunta", use_container_width=True)
        with col_hist:
            ver_hist = st.form_submit_button("📖  Ver histórico completo", use_container_width=True)

    if enviar and pergunta.strip():
        _processar_pergunta(pergunta.strip(), client_id, email, empresa)

    if ver_hist:
        _mostrar_historico_sheets(client_id)
        return

    # ── Exibe conversa da sessão atual ────────────────────────────────────────
    if not st.session_state["chat_history"]:
        st.markdown(
            f"<div style='text-align:center;padding:2rem;color:#94a3b8;'>"
            f"<div style='font-size:2.5rem;'>💬</div>"
            f"<p>Faça uma pergunta técnica sobre seus equipamentos ou relatórios.</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
        return

    for item in reversed(st.session_state["chat_history"]):
        _render_message("user",      item["pergunta"])
        _render_message("assistant", item["resposta"], item.get("fontes", ""))
        if item.get("critico"):
            if st.button("🔧 Abrir Chamado Técnico", key=f"chamado_{item['ts']}"):
                st.session_state["page"] = "chamados"
                st.rerun()
        st.markdown("---")


def _processar_pergunta(pergunta: str, client_id: str, email: str, empresa: str) -> None:
    with st.spinner("Consultando o Assistente Técnico Pred.IO…"):
        resposta, fontes = call_assistant(client_id, email, empresa, pergunta)

    critico = is_critical(pergunta)

    st.session_state["chat_history"].append({
        "pergunta": pergunta,
        "resposta": resposta,
        "fontes":   fontes,
        "critico":  critico,
        "ts":       str(len(st.session_state["chat_history"])),
    })

    salvar_log_assistente(client_id, email, pergunta, resposta, fontes)

    if critico:
        st.warning(AVISO_CRITICO)

    st.rerun()


def _render_message(role: str, text: str, fontes: str = "") -> None:
    if role == "user":
        st.markdown(
            f"<div style='background:{COLOR_NAVY};color:#fff;border-radius:12px 12px 4px 12px;"
            f"padding:12px 16px;margin:8px 0;max-width:80%;margin-left:auto;'>"
            f"<strong>Você</strong><br/>{text}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {COLOR_CYAN};border-radius:4px 12px 12px 12px;"
            f"padding:12px 16px;margin:8px 0;max-width:85%;'>"
            f"<strong style='color:{COLOR_NAVY};'>Assistente Pred.IO</strong><br/>{text}"
            + (f"<div style='margin-top:8px;font-size:0.78rem;color:#94a3b8;'>"
               f"📚 Fontes: {fontes}</div>" if fontes and fontes.lower() not in ("", "nan") else "")
            + "</div>",
            unsafe_allow_html=True,
        )


def _mostrar_historico_sheets(client_id: str) -> None:
    st.markdown(f"<h3 style='color:{COLOR_NAVY};'>Histórico de Perguntas</h3>",
                unsafe_allow_html=True)
    df = get_historico_assistente(client_id)
    if df.empty:
        st.info("Nenhum histórico encontrado.")
        return
    for _, row in df.iterrows():
        pergunta = str(row.get("Pergunta", "")).strip()
        resposta = str(row.get("Resposta", "")).strip()
        data_h   = str(row.get("Data_Hora", "")).strip()
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:10px;padding:12px 16px;margin-bottom:10px;'>"
            f"<p style='color:#94a3b8;font-size:0.75rem;margin:0;'>{data_h}</p>"
            f"<p style='font-weight:700;color:{COLOR_NAVY};margin:4px 0;'>❓ {pergunta}</p>"
            f"<p style='color:#475569;font-size:0.88rem;margin:0;'>{resposta[:300]}"
            f"{'…' if len(resposta) > 300 else ''}</p></div>",
            unsafe_allow_html=True,
        )
