"""Assistente Técnico Pred.IO — chat com IA controlada e histórico."""
import json
import streamlit as st
from auth import current_client_id, current_empresa, current_email
from ai_assistant import query_ai, is_critical_question
from sheets import salvar_log_assistente, get_historico_assistente
from ui import page_header, COLOR_NAVY, COLOR_BLUE, COLOR_CYAN, COLOR_CARD, COLOR_BORDER, COLOR_MUTED

_AVISO = (
    "ℹ️ As respostas são baseadas nos dados disponíveis no portal. "
    "Em caso de condição crítica ou risco operacional, acione a equipe Pred.IO abrindo um **Chamado Técnico**."
)

_CONF_CFG = {
    "alta":  ("#DCFCE7", "#15803D", "🟢 Alta"),
    "media": ("#FEF9C3", "#B45309", "🟡 Média"),
    "baixa": ("#FEE2E2", "#DC2626", "🔴 Baixa"),
}

_SUGESTOES = [
    "Quando é a próxima análise de vibração?",
    "Qual óleo usar no compressor?",
    "A bomba de óleo está crítica?",
    "Tem manual do compressor 200 VLD?",
    "Preciso fazer overhaul?",
]


def _sugestoes_para(ativo_nome: str) -> list:
    """Perguntas sugeridas com o ativo já embutido no texto — o contexto vai
    para o Assistente como parte da própria pergunta (query_ai recebe só
    texto livre, sempre escopado ao client_id da sessão)."""
    return [
        f"Qual a saúde do ativo {ativo_nome}?",
        f"Quais manutenções estão pendentes para o {ativo_nome}?",
        f"Existem alertas críticos no {ativo_nome}?",
        f"O que o último relatório do {ativo_nome} recomenda?",
        f"Preciso abrir chamado para o {ativo_nome}?",
    ]


def render() -> None:
    page_header("🤖 Assistente Técnico Pred.IO",
                "Tire dúvidas sobre seus equipamentos e relatórios")

    # SEGURANÇA: client_id sempre da sessão — nunca do front-end
    client_id = current_client_id()
    empresa   = current_empresa()
    email     = current_email()

    st.caption(_AVISO)

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # ── Contexto de ativo — vindo do botão "Perguntar ao Assistente" no
    # detalhe do ativo (page_ativos.py). Não some sozinho: fica até o
    # cliente perguntar algo ou tocar em "limpar contexto".
    ctx_ativo = st.session_state.get("assistente_ativo_contexto", "")
    if ctx_ativo:
        col_ctx, col_clear = st.columns([5, 1])
        with col_ctx:
            st.markdown(
                f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;"
                f"padding:8px 14px;margin-bottom:0.5rem;'>"
                f"<p style='margin:0;font-size:0.83rem;color:#1E40AF;'>"
                f"🔎 Perguntando sobre: <strong>{ctx_ativo}</strong></p>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_clear:
            if st.button("✕", key="_ast_clear_ctx", help="Limpar contexto do ativo"):
                st.session_state.pop("assistente_ativo_contexto", None)
                st.rerun()

    # ── Formulário de pergunta ────────────────────────────────────────────────
    with st.form("chat_form", clear_on_submit=True):
        pergunta = st.text_area(
            "Sua pergunta",
            placeholder="Ex: Qual o status do compressor? Quando é a próxima manutenção?",
            height=90,
            label_visibility="collapsed",
        )
        enviar = st.form_submit_button("📨 Enviar pergunta", use_container_width=True)

    if st.button("📖 Ver histórico completo", use_container_width=False):
        _mostrar_historico(client_id)
        return

    if enviar and pergunta.strip():
        _processar_pergunta(pergunta.strip(), client_id, email, empresa)

    # ── Conversa da sessão atual ──────────────────────────────────────────────
    if not st.session_state["chat_history"]:
        st.markdown(
            f"<div style='text-align:center;padding:2rem;color:{COLOR_MUTED};'>"
            f"<div style='font-size:2.5rem;'>💬</div>"
            f"<p>Faça uma pergunta técnica sobre seus equipamentos.</p></div>",
            unsafe_allow_html=True,
        )
        st.markdown("**Sugestões:**")
        sugestoes = _sugestoes_para(ctx_ativo) if ctx_ativo else _SUGESTOES
        for sug in sugestoes:
            if st.button(sug, key=f"sug_{hash(sug)}"):
                _processar_pergunta(sug, client_id, email, empresa)
        return

    for item in reversed(st.session_state["chat_history"]):
        _render_user_msg(item["pergunta"])
        _render_bot_msg(item)
        if item.get("critico"):
            if st.button("🔧 Abrir Chamado Técnico Urgente", key=f"crit_{item['ts']}",
                         type="primary"):
                st.session_state["portal_page"] = "chamados"
                st.rerun()


def _processar_pergunta(pergunta: str, client_id: str, email: str, empresa: str) -> None:
    with st.spinner("Consultando o Assistente Técnico Pred.IO…"):
        # IA chamada server-side — client_id da sessão, nunca do front-end
        result = query_ai(client_id, pergunta)

    critico = is_critical_question(pergunta)
    if critico and result.get("confidence") != "baixa":
        # Força chamado sugerido em perguntas críticas
        actions = result.get("suggested_actions", [])
        if not any(a.get("page") == "chamados" for a in actions):
            actions.append({"label": "🔧 Abrir Chamado Técnico", "page": "chamados"})
        result["suggested_actions"] = actions

    item = {
        "pergunta":   pergunta,
        "answer":     result.get("answer", ""),
        "confidence": result.get("confidence", "media"),
        "sources":    result.get("sources", []),
        "related_documents": result.get("related_documents", []),
        "related_reports":   result.get("related_reports", []),
        "suggested_actions": result.get("suggested_actions", []),
        "critico":    critico,
        "ts":         str(len(st.session_state["chat_history"])),
    }
    st.session_state["chat_history"].append(item)

    # Log seguro: nunca salva dados de outro cliente
    try:
        salvar_log_assistente(
            client_id=client_id,
            email=email,
            pergunta=pergunta,
            resposta=result.get("answer", ""),
            fontes=", ".join(s.get("titulo", "") for s in result.get("sources", [])),
            confidence=result.get("confidence", ""),
            sources_json=json.dumps(result.get("sources", []), ensure_ascii=False)[:2000],
        )
    except Exception:
        pass

    # Modo Admin "Ver como Cliente": registra em auditoria que um staff
    # consultou o Assistente em nome do cliente selecionado.
    try:
        from auth import is_admin_preview, current_email as _cur_email, current_perfil as _cur_perfil
        if is_admin_preview():
            from sheets import log_audit
            log_audit(_cur_email(), _cur_perfil(), client_id,
                      "admin_perguntou_assistente_cliente", recurso_tipo="assistente",
                      recurso_id=pergunta[:200])
    except Exception:
        pass

    st.rerun()


def _render_user_msg(texto: str) -> None:
    st.markdown(
        f"<div style='background:{COLOR_NAVY};color:#fff;border-radius:12px 12px 4px 12px;"
        f"padding:12px 16px;margin:8px 0;max-width:80%;margin-left:auto;'>"
        f"<strong>Você</strong><br>{texto}</div>",
        unsafe_allow_html=True,
    )


def _render_bot_msg(item: dict) -> None:
    answer     = item.get("answer", "")
    confidence = item.get("confidence", "media")
    sources    = item.get("sources", [])
    rel_docs   = item.get("related_documents", [])
    rel_reps   = item.get("related_reports", [])
    actions    = item.get("suggested_actions", [])

    conf_bg, conf_tc, conf_label = _CONF_CFG.get(confidence, _CONF_CFG["media"])
    conf_badge = (
        f"<span style='background:{conf_bg};color:{conf_tc};-webkit-text-fill-color:{conf_tc};"
        f"font-size:0.65rem;font-weight:700;padding:2px 9px;border-radius:10px;"
        f"border:1px solid {conf_tc}33;'>{conf_label} confiança</span>"
    )

    # Fontes consultadas
    sources_html = ""
    if sources:
        src_items = "".join(
            f"<li style='margin:2px 0;'><strong>{s.get('titulo','')}</strong>"
            + (f" <span style='color:{COLOR_MUTED};font-size:0.72rem;'>({s.get('tipo','')})</span>" if s.get("tipo") else "")
            + (f" — {s.get('secao','')}" if s.get("secao") else "")
            + "</li>"
            for s in sources
        )
        sources_html = (
            f"<div style='margin-top:10px;padding:8px 12px;background:#F8FAFC;"
            f"border:1px solid {COLOR_BORDER};border-radius:8px;font-size:0.78rem;'>"
            f"<p style='font-weight:700;color:{COLOR_NAVY};margin:0 0 4px;font-size:0.75rem;'>📚 Fontes consultadas:</p>"
            f"<ul style='margin:0;padding-left:1.2rem;color:#475569;'>{src_items}</ul></div>"
        )

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-left:4px solid {COLOR_CYAN};border-radius:4px 12px 12px 12px;"
        f"padding:12px 16px;margin:8px 0;max-width:88%;'>"
        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>"
        f"<strong style='color:{COLOR_NAVY};'>Assistente Pred.IO</strong>"
        f"{conf_badge}</div>"
        f"<div style='color:#1E293B;font-size:0.88rem;line-height:1.55;'>{answer}</div>"
        f"{sources_html}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Botões de ação
    all_actions = list(actions)
    # Adiciona botões para documentos relacionados
    for d in rel_docs[:2]:
        if not any(a.get("label", "").startswith("📚") for a in all_actions):
            all_actions.append({"label": "📚 Abrir Biblioteca", "page": "biblioteca"})
    for r in rel_reps[:1]:
        if not any(a.get("page") == "relatorios" for a in all_actions):
            all_actions.append({"label": "📋 Ver Relatórios", "page": "relatorios"})

    if all_actions:
        cols = st.columns(min(len(all_actions), 4))
        for i, action in enumerate(all_actions[:4]):
            with cols[i % len(cols)]:
                if st.button(action["label"], key=f"act_{item['ts']}_{i}",
                             use_container_width=True):
                    st.session_state["portal_page"] = action["page"]
                    st.rerun()


def _mostrar_historico(client_id: str) -> None:
    st.markdown(f"<h3 style='color:{COLOR_NAVY};margin:0 0 1rem;'>Histórico de Perguntas</h3>",
                unsafe_allow_html=True)
    df = get_historico_assistente(client_id)
    if df.empty:
        st.info("Nenhum histórico encontrado.")
        return
    for _, row in df.iterrows():
        pergunta   = str(row.get("Pergunta", "")).strip()
        resposta   = str(row.get("Resposta", "")).strip()
        confidence = str(row.get("Confidence", "")).strip()
        data_h     = str(row.get("Data_Hora", "")).strip()
        conf_bg, conf_tc, conf_label = _CONF_CFG.get(confidence, _CONF_CFG["media"])
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:10px;padding:12px 16px;margin-bottom:10px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
            f"<span style='color:{COLOR_MUTED};font-size:0.73rem;'>{data_h}</span>"
            f"<span style='background:{conf_bg};color:{conf_tc};-webkit-text-fill-color:{conf_tc};"
            f"font-size:0.65rem;font-weight:700;padding:1px 8px;border-radius:8px;"
            f"border:1px solid {conf_tc}33;'>{conf_label}</span></div>"
            f"<p style='font-weight:700;color:{COLOR_NAVY};margin:4px 0;'>❓ {pergunta}</p>"
            f"<p style='color:#475569;font-size:0.85rem;margin:0;'>"
            + (resposta[:300] + ("…" if len(resposta) > 300 else ""))
            + "</p></div>",
            unsafe_allow_html=True,
        )
