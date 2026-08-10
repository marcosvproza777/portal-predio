"""Assistente Técnico Pred.IO — chat com IA controlada e histórico."""
import json
import streamlit as st
from auth import current_client_id, current_empresa, current_email
from ai_assistant import query_ai, is_critical_question
from sheets import salvar_log_assistente, get_historico_assistente
from ui import page_header, COLOR_NAVY, COLOR_BLUE, COLOR_CYAN, COLOR_CARD, COLOR_BORDER, COLOR_MUTED
import assistant_lookup

_KEY_CUR_REPORT = "assistente_current_report_id"
_KEY_CUR_DOC = "assistente_current_document_id"

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
        if item.get("lookup"):
            _render_lookup_msg(item, client_id, email)
        else:
            _render_bot_msg(item)
        if item.get("critico"):
            if st.button("🔧 Abrir Chamado Técnico Urgente", key=f"crit_{item['ts']}",
                         type="primary"):
                st.session_state["portal_page"] = "chamados"
                st.rerun()


def _processar_pergunta(pergunta: str, client_id: str, email: str, empresa: str) -> None:
    # Antes de acionar a IA genérica, verifica se a pergunta é sobre
    # localizar/exibir/resumir um Relatório Técnico ou documento da
    # Biblioteca — se for, resolve aqui e nem chama query_ai(). Se não for
    # (retorna None), segue o fluxo normal sem nenhuma mudança.
    current_report_id = st.session_state.get(_KEY_CUR_REPORT, "")
    current_document_id = st.session_state.get(_KEY_CUR_DOC, "")
    with st.spinner("Consultando o Assistente Técnico Pred.IO…"):
        lookup = assistant_lookup.rotear_pergunta(pergunta, client_id, current_report_id, current_document_id)
    if lookup is not None:
        _registrar_lookup(pergunta, lookup, client_id, email)
        st.rerun()
        return

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


def _registrar_lookup(pergunta: str, lookup: dict, client_id: str, email: str) -> None:
    """Adiciona ao histórico da sessão um resultado de
    assistant_lookup.rotear_pergunta() (card/lista/resumo/etc.) e atualiza
    current_report_id/current_document_id — SEMPRE os valores que vieram
    já revalidados dentro de rotear_pergunta(), nunca um id "solto"."""
    if "current_report_id" in lookup:
        st.session_state[_KEY_CUR_REPORT] = lookup["current_report_id"]
    if "current_document_id" in lookup:
        st.session_state[_KEY_CUR_DOC] = lookup["current_document_id"]

    item = {
        "pergunta": pergunta,
        "lookup": lookup,
        "critico": False,
        "ts": str(len(st.session_state["chat_history"])),
    }
    st.session_state["chat_history"].append(item)
    _log_lookup(pergunta, lookup, client_id, email)


def _log_lookup(pergunta: str, lookup: dict, client_id: str, email: str) -> None:
    tipo = lookup.get("tipo", "")
    if tipo in ("relatorio_card",):
        report_ids = lookup["item"]["id"]
    elif tipo == "resumo_consolidado":
        report_ids = ",".join(lookup.get("relatorios", []))
    elif tipo in ("lista_relatorios", "ambiguo") and lookup.get("itens"):
        report_ids = ",".join(i["id"] for i in lookup["itens"] if "tipo_servico" in i)
    else:
        report_ids = lookup.get("current_report_id", "")

    if tipo in ("documento_card",):
        document_ids = lookup["item"]["id"]
    elif tipo in ("lista_documentos", "ambiguo") and lookup.get("itens"):
        document_ids = ",".join(i["id"] for i in lookup["itens"] if "tipo_documento" in i)
    else:
        document_ids = lookup.get("current_document_id", "")

    resposta = lookup.get("texto") or lookup.get("mensagem") or f"[{tipo}]"
    try:
        salvar_log_assistente(
            client_id=client_id, email=email, pergunta=pergunta,
            resposta=resposta[:2000], fontes="Pred.IO", confidence="",
            report_ids_usados=report_ids, document_ids_usados=document_ids,
            current_report_id=st.session_state.get(_KEY_CUR_REPORT, ""),
            current_document_id=st.session_state.get(_KEY_CUR_DOC, ""),
        )
    except Exception:
        pass


def _resolver_pdf_url(storage_path: str, arquivo_url: str, is_doc: bool, forcar_download: bool = False) -> str:
    """Gera um link fresco (nunca reaproveitado entre reruns) a partir do
    storage privado quando disponível; cai para Arquivo_Url (documentos
    antigos, sem storage) quando não. Nunca propaga exceção — chamador só
    usa o resultado como string, podendo estar vazio."""
    if storage_path:
        try:
            from drive_storage import get_document_pdf_url, get_report_pdf_url
            fn = get_document_pdf_url if is_doc else get_report_pdf_url
            return fn(storage_path, forcar_download=forcar_download)
        except Exception:
            pass
    return arquivo_url or ""


def _acionar_resumo_relatorio(report_id: str, client_id: str, email: str) -> None:
    with st.spinner("Gerando resumo…"):
        r = assistant_lookup.summarize_technical_report(report_id, client_id)
    lookup = {"tipo": "resumo", "texto": r["resumo"] if r["ok"] else r["erro"]}
    if r["ok"]:
        lookup["current_report_id"] = report_id
    _registrar_lookup(f"Resumir relatório {report_id}", lookup, client_id, email)
    st.rerun()


def _acionar_resumo_documento(document_id: str, client_id: str, email: str) -> None:
    with st.spinner("Gerando resumo…"):
        r = assistant_lookup.summarize_technical_document(document_id, client_id)
    lookup = {"tipo": "resumo", "texto": r["resumo"] if r["ok"] else r["erro"]}
    if r["ok"]:
        lookup["current_document_id"] = document_id
    _registrar_lookup(f"Resumir documento {document_id}", lookup, client_id, email)
    st.rerun()


def _render_report_card(item: dict, key_prefix: str, client_id: str, email: str) -> None:
    titulo   = item.get("titulo", "")
    tipo_srv = item.get("tipo_servico", "")
    sev      = item.get("severidade", "")
    data     = item.get("data", "")
    ativo    = item.get("ativo_nome") or item.get("ativo_id", "")
    resumo   = item.get("resumo", "")
    recos    = item.get("recomendacoes", "")

    sev_l = sev.strip().lower()
    sev_bg, sev_tc = {
        "crítica": ("#FEE2E2", "#DC2626"), "critica": ("#FEE2E2", "#DC2626"),
        "alta": ("#FFEDD5", "#C2410C"),
        "moderada": ("#FEF9C3", "#B45309"), "normal": ("#DCFCE7", "#15803D"),
        "baixa": ("#DCFCE7", "#15803D"),
    }.get(sev_l, ("#F1F5F9", "#64748B"))

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-left:4px solid {COLOR_BLUE};border-radius:4px 12px 12px 12px;"
        f"padding:12px 16px;margin:8px 0;max-width:88%;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap;'>"
        f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;'>📋 {titulo}</span>"
        + (f"<span style='background:{sev_bg};color:{sev_tc};-webkit-text-fill-color:{sev_tc};"
           f"font-size:0.65rem;font-weight:700;padding:2px 9px;border-radius:10px;'>{sev}</span>" if sev else "")
        + "</div>"
        + (f"<p style='color:{COLOR_MUTED};font-size:0.78rem;margin:4px 0;'>"
           f"{tipo_srv}{' · ' + data if data else ''}{' · ' + ativo if ativo else ''}</p>")
        + (f"<p style='color:#475569;font-size:0.83rem;margin:4px 0;'>{resumo}</p>" if resumo else "")
        + (f"<p style='color:#475569;font-size:0.8rem;margin:4px 0;'><strong>Recomendações:</strong> {recos}</p>" if recos else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    url_abrir = _resolver_pdf_url(item.get("storage_path", ""), item.get("arquivo_url", ""), is_doc=False)
    url_baixar = _resolver_pdf_url(item.get("storage_path", ""), item.get("arquivo_url", ""), is_doc=False, forcar_download=True)
    cols = st.columns(4)
    with cols[0]:
        if url_abrir:
            st.link_button("👁️ Abrir", url_abrir, use_container_width=True)
        else:
            st.button("👁️ Abrir", key=f"{key_prefix}_abrir_x", disabled=True, use_container_width=True)
    with cols[1]:
        if url_baixar:
            st.link_button("⬇️ Baixar", url_baixar, use_container_width=True)
        else:
            st.button("⬇️ Baixar", key=f"{key_prefix}_baixar_x", disabled=True, use_container_width=True)
    with cols[2]:
        if st.button("📝 Resumir", key=f"{key_prefix}_resumir", use_container_width=True):
            _acionar_resumo_relatorio(item["id"], client_id, email)
    with cols[3]:
        if item.get("ativo_id"):
            if st.button("🔧 Ver ativo", key=f"{key_prefix}_ativo", use_container_width=True):
                st.session_state["ativo_detalhe_id"] = item["ativo_id"]
                st.session_state["portal_page"] = "ativos"
                st.rerun()


def _render_document_card(item: dict, key_prefix: str, client_id: str, email: str) -> None:
    titulo = item.get("titulo", "")
    tipo   = item.get("tipo_documento", "")
    fab    = item.get("fabricante", "")
    modelo = item.get("modelo", "")
    ativo  = item.get("ativo_nome") or item.get("ativo_id", "")
    resumo = item.get("resumo", "")
    idx    = item.get("status_indexacao", "")

    meta = [m for m in (fab, modelo, ativo) if m]

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-left:4px solid {COLOR_CYAN};border-radius:4px 12px 12px 12px;"
        f"padding:12px 16px;margin:8px 0;max-width:88%;'>"
        f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;'>📚 {titulo}</span>"
        + (f"<p style='color:{COLOR_MUTED};font-size:0.78rem;margin:4px 0;'>{tipo}{' · ' + ' · '.join(meta) if meta else ''}</p>")
        + (f"<p style='color:#475569;font-size:0.83rem;margin:4px 0;'>{resumo}</p>" if resumo else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    url_abrir = _resolver_pdf_url(item.get("storage_path", ""), item.get("arquivo_url", ""), is_doc=True)
    url_baixar = _resolver_pdf_url(item.get("storage_path", ""), item.get("arquivo_url", ""), is_doc=True, forcar_download=True)
    cols = st.columns(4)
    with cols[0]:
        if url_abrir:
            st.link_button("👁️ Abrir", url_abrir, use_container_width=True)
        else:
            st.button("👁️ Abrir", key=f"{key_prefix}_abrir_x", disabled=True, use_container_width=True)
    with cols[1]:
        if url_baixar:
            st.link_button("⬇️ Baixar", url_baixar, use_container_width=True)
        else:
            st.button("⬇️ Baixar", key=f"{key_prefix}_baixar_x", disabled=True, use_container_width=True)
    with cols[2]:
        if idx == "Indexado":
            if st.button("📝 Resumir", key=f"{key_prefix}_resumir", use_container_width=True):
                _acionar_resumo_documento(item["id"], client_id, email)
        else:
            st.button("📝 Resumir", key=f"{key_prefix}_resumir_x", disabled=True, use_container_width=True,
                      help="Documento ainda não indexado")
    with cols[3]:
        if st.button("💬 Perguntar sobre este", key=f"{key_prefix}_perguntar", use_container_width=True):
            st.session_state[_KEY_CUR_DOC] = item["id"]
            st.toast("Pode perguntar sobre este documento agora.", icon="💬")


def _render_lookup_msg(item: dict, client_id: str, email: str) -> None:
    lookup = item["lookup"]
    tipo = lookup.get("tipo", "")
    ts = item["ts"]

    if tipo == "relatorio_card":
        _render_report_card(lookup["item"], f"rc_{ts}", client_id, email)
    elif tipo == "documento_card":
        _render_document_card(lookup["item"], f"dc_{ts}", client_id, email)
    elif tipo == "lista_relatorios":
        st.markdown(
            f"<p style='color:{COLOR_MUTED};font-size:0.8rem;margin:4px 0;'>"
            f"Encontrei {len(lookup['itens'])} relatório(s):</p>", unsafe_allow_html=True,
        )
        for i, r in enumerate(lookup["itens"]):
            _render_report_card(r, f"lr_{ts}_{i}", client_id, email)
    elif tipo == "lista_documentos":
        st.markdown(
            f"<p style='color:{COLOR_MUTED};font-size:0.8rem;margin:4px 0;'>"
            f"Encontrei {len(lookup['itens'])} documento(s):</p>", unsafe_allow_html=True,
        )
        for i, d in enumerate(lookup["itens"]):
            _render_document_card(d, f"ld_{ts}_{i}", client_id, email)
    elif tipo == "ambiguo":
        _render_texto_msg(lookup.get("mensagem", ""))
        for i, r in enumerate(lookup.get("itens", [])):
            if "tipo_servico" in r:
                _render_report_card(r, f"amb_{ts}_{i}", client_id, email)
            else:
                _render_document_card(r, f"amb_{ts}_{i}", client_id, email)
    elif tipo in ("resumo", "resumo_consolidado", "cruzamento"):
        _render_texto_msg(lookup.get("texto", ""))
    elif tipo == "nao_encontrado":
        _render_texto_msg(lookup.get("mensagem", ""))


def _render_texto_msg(texto: str) -> None:
    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-left:4px solid {COLOR_CYAN};border-radius:4px 12px 12px 12px;"
        f"padding:12px 16px;margin:8px 0;max-width:88%;'>"
        f"<strong style='color:{COLOR_NAVY};'>Assistente Pred.IO</strong>"
        f"<div style='color:#1E293B;font-size:0.88rem;line-height:1.55;margin-top:6px;"
        f"white-space:pre-wrap;'>{texto}</div></div>",
        unsafe_allow_html=True,
    )


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
        data_h     = str(row.get("Data", "")).strip()
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
