"""Supervisão — Auditoria do Assistente Técnico Pred.IO."""
import json
import re
import streamlit as st

from auth import require_staff, current_nome
from sheets import (
    get_all_clientes, get_documentos_tecnicos,
    save_assistant_log, get_assistant_logs,
    update_log_avaliacao, save_assistant_faq, get_assistant_faq,
    buscar_chunks,
)
from ui import (
    sv_page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE,
)
from assistant_engine import query_assistant_audit

# ── Constantes ────────────────────────────────────────────────────────────────

_QUICK_QUESTIONS = [
    "O que é Mypro Touch AD?",
    "Como ligar o compressor?",
    "Como parar o compressor?",
    "Como limpar alarme?",
    "Qual a senha do painel?",
    "O que é Set Point Cut In?",
    "O que é Set Point Cut Out?",
    "Como alterar capacidade manualmente?",
    "Qual óleo MYCOM homologado atual?",
    "MYCOLD AB ainda é usado?",
    "Pode usar qualquer óleo ISO 68?",
    "Quando fazer análise de óleo?",
    "Quando trocar filtro coalescente?",
    "Com 20.000 horas preciso fazer overhaul?",
    "Qual temperatura de descarga para compressor parafuso?",
    "Qual temperatura de descarga para compressor alternativo?",
    "Ruído no rolamento indica troca?",
    "Por que fazer análise de vibração?",
    "O que é SSH?",
    "Termografia substitui análise de vibração?",
]

_FAQ_CATEGORIAS = [
    "Mypro Touch", "Mypro Touch AD", "Óleo",
    "Vibração", "Termografia", "Motor", "Rolamento",
    "SSH", "Manutenção", "Alarmes", "Segurança", "Overhaul por condição",
]

_AVALIACOES = [
    ("✅ Aprovada",            "Aprovada",             "#DCFCE7", "#15803D"),
    ("⚠️ Precisa melhorar",   "Precisa melhorar",     "#FEF9C3", "#B45309"),
    ("❌ Incorreta",           "Incorreta",            "#FEE2E2", "#DC2626"),
    ("❓ Sem base suficiente", "Sem base suficiente",  "#F5F3FF", "#7C3AED"),
]

_ORIGEM_COLOR = {
    "Biblioteca Técnica":    ("#DBEAFE", "#2563EB"),
    "Plano de Manutenção":   ("#DCFCE7", "#15803D"),
    "Relatório Técnico":     ("#E0F2FE", "#0891B2"),
    "Base Pred.IO":          ("#E2E8F0", "#0F1F3D"),
    "Sem base suficiente":   ("#FEE2E2", "#DC2626"),
    "Internet (complemento)":("#FEF9C3", "#B45309"),
}

_CONF_COLOR = {
    "Alta":   ("#DCFCE7", "#15803D"),
    "Média":  ("#DBEAFE", "#2563EB"),
    "Baixa":  ("#FEF9C3", "#B45309"),
}

_AVAL_COLOR = {
    "Não avaliada":        ("#F1F5F9", "#64748B"),
    "Aprovada":            ("#DCFCE7", "#15803D"),
    "Precisa melhorar":    ("#FEF9C3", "#B45309"),
    "Incorreta":           ("#FEE2E2", "#DC2626"),
    "Sem base suficiente": ("#F5F3FF", "#7C3AED"),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _badge(text: str, bg: str, color: str) -> str:
    return (
        f"<span style='background:{bg};color:{color};"
        f"border-radius:12px;padding:2px 10px;"
        f"font-size:0.72rem;font-weight:700;white-space:nowrap;'>{text}</span>"
    )


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _fmt_answer_html(text: str) -> str:
    return text.replace("\n\n", "<br><br>").replace("\n", "<br>")


# ── Render principal ──────────────────────────────────────────────────────────

def render() -> None:
    require_staff()
    sv_page_header(
        "🧪 Auditoria do Assistente Técnico",
        "Teste, valide e melhore as respostas do Assistente Pred.IO "
        "com base nos documentos indexados.",
    )

    tab_test, tab_logs, tab_faq, tab_metrics, tab_web = st.tabs([
        "🧪 Testar Assistente",
        "📋 Logs de Auditoria",
        "⭐ Perguntas Frequentes",
        "📊 Métricas",
        "🌐 Busca Web",
    ])

    with tab_test:
        _render_test_tab()

    with tab_logs:
        _render_logs_tab()

    with tab_faq:
        _render_faq_tab()

    with tab_metrics:
        _render_metrics_tab()

    with tab_web:
        _render_web_search_tab()


# ── Tab: Testar ───────────────────────────────────────────────────────────────

def _render_test_tab() -> None:
    df_clientes = get_all_clientes()
    client_options: list[tuple[str, str]] = [("", "— Todos os clientes —")]
    if not df_clientes.empty:
        for _, r in df_clientes.iterrows():
            emp = str(r.get("Empresa", "")).strip()
            cid = str(r.get("Client_Id", "")).strip()
            if emp and cid:
                client_options.append((cid, emp))

    col_form, col_result = st.columns([3, 7], gap="medium")

    with col_form:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:12px;padding:14px 16px;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='color:{COLOR_NAVY};font-size:0.78rem;font-weight:700;"
            f"letter-spacing:0.06em;margin:0 0 10px;'>CONTEXTO DO TESTE</p>",
            unsafe_allow_html=True,
        )

        sel_cli = st.selectbox(
            "Cliente",
            options=range(len(client_options)),
            format_func=lambda i: client_options[i][1],
            key="_aud_cli_idx",
        )
        selected_client_id = client_options[sel_cli][0]

        # Ativos
        ativo_options: list[tuple[str, str]] = [("", "— Qualquer ativo —")]
        try:
            if selected_client_id:
                from sheets import get_ativos
                df_atv = get_ativos(selected_client_id)
            else:
                from sheets import get_all_ativos_sv
                df_atv = get_all_ativos_sv()
            if not df_atv.empty:
                for _, r in df_atv.iterrows():
                    aid = str(r.get("Id", "")).strip()
                    anm = str(r.get("Nome", r.get("Ativo", aid))).strip()
                    if aid:
                        ativo_options.append((aid, anm or aid))
        except Exception:
            pass

        sel_atv = st.selectbox(
            "Ativo",
            options=range(len(ativo_options)),
            format_func=lambda i: ativo_options[i][1],
            key="_aud_atv_idx",
        )
        selected_ativo_id = ativo_options[sel_atv][0]

        # Documentos
        doc_options: list[tuple[str, str]] = [("", "— Qualquer documento —")]
        try:
            df_docs = get_documentos_tecnicos(
                client_id=selected_client_id or None,
                staff=True,
            )
            if not df_docs.empty:
                for _, r in df_docs.iterrows():
                    did  = str(r.get("Id",    "")).strip()
                    dtit = str(r.get("Titulo","")).strip()
                    dstat = str(r.get("Status_Indexacao", "")).strip()
                    if did:
                        lbl = dtit or did
                        if dstat:
                            lbl += f"  [{dstat}]"
                        doc_options.append((did, lbl))
        except Exception:
            pass

        sel_doc = st.selectbox(
            "Documento técnico",
            options=range(len(doc_options)),
            format_func=lambda i: doc_options[i][1],
            key="_aud_doc_idx",
        )
        selected_doc_id = doc_options[sel_doc][0]

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.78rem;"
            f"letter-spacing:0.06em;margin:12px 0 6px;'>INTERNET</p>",
            unsafe_allow_html=True,
        )
        use_web_search = st.checkbox(
            "Permitir busca na internet neste teste",
            key="_aud_web_search",
            help="Ativa busca web controlada mesmo que WEB_SEARCH_ENABLED=false no servidor.",
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with col_result:
        # Perguntas rápidas
        with st.expander("💡 Perguntas rápidas de teste", expanded=False):
            qq_cols = st.columns(2)
            for qi, qq in enumerate(_QUICK_QUESTIONS):
                with qq_cols[qi % 2]:
                    if st.button(qq, key=f"_aud_qq_{qi}", use_container_width=True):
                        st.session_state["_aud_q"] = qq
                        for _k in ("_aud_result", "_aud_log_id",
                                   "_aud_avaliacao", "_aud_faq_open"):
                            st.session_state.pop(_k, None)
                        st.rerun()

        pergunta = st.text_area(
            "Pergunta de teste",
            placeholder="Ex: O que é Mypro Touch AD? / Como ligar o compressor?",
            key="_aud_q",
            height=88,
        )

        if st.button(
            "🧪 Testar Assistente", type="primary",
            use_container_width=True, key="_aud_btn_testar",
        ):
            q = (pergunta or "").strip()
            if not q:
                st.warning("Digite uma pergunta antes de testar.")
            else:
                with st.spinner("Consultando Assistente Técnico Pred.IO…"):
                    result = query_assistant_audit(
                        client_id=selected_client_id,
                        pergunta=q,
                        ativo_id=selected_ativo_id,
                        use_web_search=use_web_search,
                    )
                    chunks_hits = buscar_chunks(
                        client_id=selected_client_id,
                        query=q,
                        top_n=3,
                    )
                    result["_chunks_display"] = chunks_hits

                    log_id = save_assistant_log(
                        usuario_id=current_nome(),
                        cliente_id=selected_client_id,
                        ativo_id=selected_ativo_id,
                        documento_id=selected_doc_id,
                        pergunta=q,
                        resposta=_strip_html(result["answer"])[:1000],
                        fonte="Pred.IO",
                        chunks_usados=json.dumps(
                            chunks_hits, ensure_ascii=False
                        )[:2000],
                        confidence=result["_confidence"],
                        origem_resposta=result["_origem_resposta"],
                    )
                    st.session_state["_aud_result"]   = result
                    st.session_state["_aud_log_id"]   = log_id
                    st.session_state.pop("_aud_avaliacao", None)
                    st.session_state.pop("_aud_faq_open",  None)

        # Resultado
        res = st.session_state.get("_aud_result")
        if res:
            _render_result(res)


def _render_result(result: dict) -> None:
    """Exibe resposta, metadados internos e botões de avaliação."""
    conf = result.get("_confidence", "Média")
    orig = result.get("_origem_resposta", "Base Pred.IO")
    conf_bg, conf_col = _CONF_COLOR.get(conf, ("#E2E8F0", "#64748B"))
    orig_bg, orig_col = _ORIGEM_COLOR.get(orig, ("#E2E8F0", "#64748B"))

    answer_html = _fmt_answer_html(result["answer"])

    st.markdown(
        "<hr style='border-color:#E2E8F0;margin:12px 0;'/>",
        unsafe_allow_html=True,
    )

    # ── Resposta ──────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-left:4px solid #2563EB;border-radius:12px;"
        f"padding:16px 20px;margin-bottom:8px;'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px;'>"
        f"<p style='font-size:0.76rem;font-weight:700;color:{COLOR_NAVY};"
        f"letter-spacing:0.06em;margin:0;'>RESPOSTA DO ASSISTENTE</p>"
        f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>"
        f"{_badge('Confiança: ' + conf, conf_bg, conf_col)}&nbsp;"
        f"{_badge(orig, orig_bg, orig_col)}"
        f"</div></div>"
        f"<div style='color:#1E293B;font-size:0.9rem;line-height:1.65;'>"
        f"{answer_html}</div>"
        f"<hr style='border-color:{COLOR_BORDER};margin:10px 0 6px;'/>"
        f"<p style='font-size:0.73rem;color:#94A3B8;margin:0;'>"
        f"<strong style='color:#64748B;'>Exibido ao cliente:</strong> "
        f"Fonte: Pred.IO</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Metadados internos ────────────────────────────────────────────────────
    docs           = result.get("related_documents", [])
    chunks_display = result.get("_chunks_display", [])
    intent         = result.get("_intent", "—")

    with st.expander("🔍 Metadados internos de auditoria", expanded=True):
        mc1, mc2 = st.columns(2)

        with mc1:
            st.markdown(
                f"<p style='font-size:0.74rem;font-weight:700;color:{COLOR_NAVY};"
                f"letter-spacing:0.06em;margin:0 0 3px;'>INTENT DETECTADA</p>"
                f"<code style='font-size:0.8rem;'>{intent}</code>"
                f"<p style='font-size:0.74rem;font-weight:700;color:{COLOR_NAVY};"
                f"letter-spacing:0.06em;margin:10px 0 4px;'>ORIGEM</p>"
                f"<p style='margin:0 0 10px;'>{_badge(orig, orig_bg, orig_col)}</p>"
                f"<p style='font-size:0.74rem;font-weight:700;color:{COLOR_NAVY};"
                f"letter-spacing:0.06em;margin:0 0 4px;'>CONFIANÇA</p>"
                f"<p style='margin:0;'>{_badge(conf, conf_bg, conf_col)}</p>",
                unsafe_allow_html=True,
            )

        with mc2:
            st.markdown(
                f"<p style='font-size:0.74rem;font-weight:700;color:{COLOR_NAVY};"
                f"letter-spacing:0.06em;margin:0 0 3px;'>FONTE (exibida ao cliente)</p>"
                f"<p style='font-size:0.85rem;color:#334155;margin:0 0 10px;'>Pred.IO</p>",
                unsafe_allow_html=True,
            )
            if docs:
                st.markdown(
                    f"<p style='font-size:0.74rem;font-weight:700;color:{COLOR_NAVY};"
                    f"letter-spacing:0.06em;margin:0 0 4px;'>DOCUMENTOS USADOS</p>",
                    unsafe_allow_html=True,
                )
                for d in docs:
                    st.markdown(
                        f"<p style='font-size:0.82rem;color:#2563EB;margin:0 0 4px;'>"
                        f"📄 {d.get('titulo', d.get('id', ''))}</p>",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    f"<p style='font-size:0.74rem;font-weight:700;color:{COLOR_NAVY};"
                    f"letter-spacing:0.06em;margin:0 0 4px;'>DOCUMENTOS</p>"
                    f"<p style='font-size:0.82rem;color:#94A3B8;margin:0;'>"
                    f"Nenhum documento indexado referenciado.</p>",
                    unsafe_allow_html=True,
                )

        # Chunks
        if chunks_display:
            st.markdown(
                f"<p style='font-size:0.74rem;font-weight:700;color:{COLOR_NAVY};"
                f"letter-spacing:0.06em;margin:10px 0 6px;'>"
                f"CHUNKS RELEVANTES ({len(chunks_display)})</p>",
                unsafe_allow_html=True,
            )
            for ci, ch in enumerate(chunks_display, 1):
                st.markdown(
                    f"<div style='background:#F8FAFF;border:1px solid #BFDBFE;"
                    f"border-radius:8px;padding:8px 12px;margin-bottom:6px;'>"
                    f"<p style='font-size:0.75rem;font-weight:700;color:{COLOR_NAVY};"
                    f"margin:0 0 3px;'>{ci}. {ch.get('t','(sem título)')}</p>"
                    f"<p style='font-size:0.74rem;color:#334155;margin:0;'>"
                    f"{ch.get('c','')[:300]}</p>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<p style='font-size:0.78rem;color:#94A3B8;margin:10px 0 0;'>"
                "Nenhum chunk indexado encontrado para esta pergunta. "
                "Indexe documentos na Biblioteca Técnica para enriquecer a base.</p>",
                unsafe_allow_html=True,
            )

    # Indicador discreto de busca web (sem mostrar as refs brutas)
    web_refs = result.get("web_refs", [])
    if web_refs:
        st.markdown(
            f"<p style='font-size:0.72rem;color:#94A3B8;margin:4px 0 0;'>"
            f"🌐 Complementado com {len(web_refs)} referência(s) pública(s) — "
            f"valide decisões críticas com a equipe Pred.IO.</p>",
            unsafe_allow_html=True,
        )

    # Ações sugeridas
    links = result.get("related_links", [])
    if links:
        with st.expander("🔗 Ações sugeridas pelo Assistente"):
            for lnk in links:
                st.markdown(
                    f"<p style='font-size:0.84rem;margin:4px 0;'>"
                    f"→ {lnk.get('label','')}</p>",
                    unsafe_allow_html=True,
                )

    # ── Avaliação ─────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:12px;padding:14px 16px;margin-top:8px;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='font-size:0.76rem;font-weight:700;color:{COLOR_NAVY};"
        f"letter-spacing:0.06em;margin:0 0 10px;'>AVALIAR RESPOSTA</p>",
        unsafe_allow_html=True,
    )

    current_aval = st.session_state.get("_aud_avaliacao")
    log_id       = st.session_state.get("_aud_log_id", "")

    aval_cols = st.columns(len(_AVALIACOES))
    for ci, (lbl, val, abg, acol) in enumerate(_AVALIACOES):
        with aval_cols[ci]:
            if st.button(
                lbl,
                key=f"_aud_aval_{val.replace(' ','_')}",
                use_container_width=True,
            ):
                if log_id:
                    update_log_avaliacao(log_id, val)
                st.session_state["_aud_avaliacao"] = val
                if val == "Aprovada":
                    st.session_state.setdefault("_aud_faq_open", True)
                st.rerun()

    if current_aval:
        abg_c, ac_c = _AVAL_COLOR.get(current_aval, ("#F1F5F9", "#64748B"))
        st.markdown(
            f"<p style='font-size:0.78rem;font-weight:700;color:{ac_c};"
            f"margin:8px 0 0;'>Avaliação registrada: {current_aval}</p>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # Copiar resposta
    with st.expander("📋 Copiar resposta (texto plano)"):
        st.code(_strip_html(result["answer"]), language=None)

    # FAQ
    if st.session_state.get("_aud_faq_open") and current_aval == "Aprovada":
        _render_faq_creation(result)


def _render_faq_creation(result: dict) -> None:
    """Painel inline para salvar a resposta como pergunta frequente."""
    st.markdown(
        "<div style='background:#ECFDF5;border:1px solid #86EFAC;"
        "border-radius:12px;padding:14px 16px;margin-top:8px;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size:0.82rem;font-weight:700;color:#15803D;"
        "margin:0 0 10px;'>⭐ CRIAR PERGUNTA FREQUENTE</p>",
        unsafe_allow_html=True,
    )

    faq_p = st.text_input(
        "Pergunta",
        value=st.session_state.get("_aud_q", ""),
        key="_aud_faq_new_p",
    )
    faq_r = st.text_area(
        "Resposta (edite se necessário)",
        value=_strip_html(result["answer"]),
        key="_aud_faq_new_r",
        height=110,
    )
    fc1, fc2 = st.columns(2)
    with fc1:
        faq_cat = st.selectbox("Categoria", _FAQ_CATEGORIAS, key="_aud_faq_new_cat")
    with fc2:
        faq_kw = st.text_input(
            "Palavras-chave",
            placeholder="alarme, reset, operador",
            key="_aud_faq_new_kw",
        )

    fb1, fb2 = st.columns([2, 1])
    with fb1:
        if st.button(
            "⭐ Salvar como Pergunta Frequente", type="primary",
            use_container_width=True, key="_aud_btn_save_faq",
        ):
            if faq_p.strip() and faq_r.strip():
                faq_id = save_assistant_faq(
                    pergunta=faq_p.strip(),
                    resposta=faq_r.strip(),
                    categoria=faq_cat,
                    palavras_chave=faq_kw.strip(),
                )
                st.success(f"✅ FAQ salva com ID: {faq_id}")
                st.session_state["_aud_faq_open"] = False
                st.rerun()
            else:
                st.warning("Preencha pergunta e resposta antes de salvar.")
    with fb2:
        if st.button("Cancelar", key="_aud_btn_cancel_faq", use_container_width=True):
            st.session_state["_aud_faq_open"] = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ── Tab: Logs ─────────────────────────────────────────────────────────────────

def _render_logs_tab() -> None:
    df = get_assistant_logs(limit=100)

    if df.empty:
        st.info(
            "Nenhum log registrado ainda. "
            "Use a aba 'Testar Assistente' para começar a auditar."
        )
        return

    AVAL_COL = "Avaliacao_Interna"

    def _cnt(val: str) -> int:
        if AVAL_COL not in df.columns:
            return 0
        return int((df[AVAL_COL].str.strip() == val).sum())

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total",             len(df))
    m2.metric("Aprovadas",         _cnt("Aprovada"))
    m3.metric("Precisa melhorar",  _cnt("Precisa melhorar"))
    m4.metric("Incorretas",        _cnt("Incorreta"))
    m5.metric("Sem base",          _cnt("Sem base suficiente"))

    st.markdown(
        "<hr style='border-color:#E2E8F0;margin:8px 0 10px;'/>",
        unsafe_allow_html=True,
    )

    # Filtros
    lf1, lf2 = st.columns(2)
    with lf1:
        f_aval = st.selectbox(
            "Filtrar por avaliação",
            ["Todas", "Não avaliada", "Aprovada",
             "Precisa melhorar", "Incorreta", "Sem base suficiente"],
            key="_aud_log_f_aval",
        )
    with lf2:
        f_cli = st.text_input(
            "Filtrar por cliente", key="_aud_log_f_cli",
            placeholder="ex: coca-cola",
        )

    df_show = df.copy()
    if AVAL_COL in df.columns and f_aval != "Todas":
        df_show = df_show[df_show[AVAL_COL].str.strip() == f_aval]
    if f_cli.strip() and "Cliente_Id" in df.columns:
        df_show = df_show[
            df_show["Cliente_Id"].str.lower().str.contains(
                f_cli.strip().lower(), na=False
            )
        ]

    if df_show.empty:
        st.info("Nenhum log com esses filtros.")
        return

    # Lista de logs
    for _, row in df_show.iterrows():
        pergunta_full  = str(row.get("Pergunta", "")).strip()
        pergunta_short = pergunta_full[:80] + ("…" if len(pergunta_full) > 80 else "")
        avaliacao      = str(row.get(AVAL_COL, "Não avaliada")).strip() or "Não avaliada"
        confidence     = str(row.get("Confidence", "")).strip()
        origem         = str(row.get("Origem_Resposta", "")).strip()
        log_id         = str(row.get("Id", "")).strip()
        created        = str(row.get("Created_At", "")).strip()
        cliente        = str(row.get("Cliente_Id", "")).strip() or "—"

        abg, acol = _AVAL_COLOR.get(avaliacao, ("#F1F5F9", "#64748B"))
        cbg, ccol = _CONF_COLOR.get(confidence, ("#E2E8F0", "#64748B"))

        prefix = (
            "✅" if avaliacao == "Aprovada" else
            "❌" if avaliacao == "Incorreta" else
            "⚠️" if avaliacao == "Precisa melhorar" else "📝"
        )

        with st.expander(f"{prefix} {pergunta_short}", expanded=False):
            lc1, lc2 = st.columns(2)
            with lc1:
                st.markdown(
                    f"<p style='font-size:0.75rem;color:#64748B;margin:0;'>"
                    f"<strong>ID:</strong> {log_id}</p>"
                    f"<p style='font-size:0.75rem;color:#64748B;margin:2px 0;'>"
                    f"<strong>Data:</strong> {created}</p>"
                    f"<p style='font-size:0.75rem;color:#64748B;margin:2px 0;'>"
                    f"<strong>Cliente:</strong> {cliente}</p>",
                    unsafe_allow_html=True,
                )
            with lc2:
                st.markdown(
                    f"<p style='font-size:0.75rem;margin:0;'>"
                    f"<strong>Avaliação:</strong> "
                    f"{_badge(avaliacao, abg, acol)}</p>"
                    f"<p style='font-size:0.75rem;margin:4px 0;'>"
                    f"<strong>Confiança:</strong> "
                    f"{_badge(confidence, cbg, ccol) if confidence else '—'}</p>"
                    f"<p style='font-size:0.75rem;margin:4px 0;'>"
                    f"<strong>Origem:</strong> {origem or '—'}</p>",
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"<p style='font-size:0.78rem;font-weight:700;color:{COLOR_NAVY};"
                f"margin:8px 0 4px;'>Pergunta</p>"
                f"<p style='font-size:0.84rem;color:#334155;margin:0;'>"
                f"{pergunta_full}</p>",
                unsafe_allow_html=True,
            )

            resposta = str(row.get("Resposta", "")).strip()
            if resposta:
                st.markdown(
                    f"<p style='font-size:0.78rem;font-weight:700;color:{COLOR_NAVY};"
                    f"margin:8px 0 4px;'>Resposta armazenada</p>"
                    f"<p style='font-size:0.84rem;color:#334155;margin:0;'>"
                    f"{resposta[:400]}{'…' if len(resposta) > 400 else ''}</p>",
                    unsafe_allow_html=True,
                )

            # Chunks do log
            chunks_json = str(row.get("Chunks_Usados", "")).strip()
            if chunks_json:
                try:
                    ch_list = json.loads(chunks_json)
                    if ch_list:
                        st.markdown(
                            f"<p style='font-size:0.75rem;font-weight:700;"
                            f"color:{COLOR_NAVY};margin:8px 0 4px;'>"
                            f"Chunks usados ({len(ch_list)})</p>",
                            unsafe_allow_html=True,
                        )
                        for chi in ch_list:
                            st.markdown(
                                f"<div style='background:#F8FAFF;"
                                f"border:1px solid #BFDBFE;border-radius:6px;"
                                f"padding:6px 10px;margin-bottom:4px;'>"
                                f"<p style='font-size:0.73rem;font-weight:700;"
                                f"color:{COLOR_NAVY};margin:0 0 2px;'>"
                                f"{chi.get('t','')}</p>"
                                f"<p style='font-size:0.72rem;color:#475569;margin:0;'>"
                                f"{chi.get('c','')[:180]}</p></div>",
                                unsafe_allow_html=True,
                            )
                except Exception:
                    pass

            # Atualizar avaliação diretamente no log
            if log_id:
                st.markdown(
                    "<p style='font-size:0.74rem;color:#94A3B8;"
                    "margin:10px 0 4px;'>Atualizar avaliação:</p>",
                    unsafe_allow_html=True,
                )
                upd_cols = st.columns(len(_AVALIACOES))
                for ui, (lbl, val, _bg, _col) in enumerate(_AVALIACOES):
                    with upd_cols[ui]:
                        safe_val = val.replace(" ", "_").replace("ê", "e")
                        if st.button(
                            lbl,
                            key=f"_aud_upd_{log_id}_{safe_val}",
                            use_container_width=True,
                        ):
                            if update_log_avaliacao(log_id, val):
                                st.success(f"Avaliação: {val}")
                                st.rerun()


# ── Tab: FAQ ──────────────────────────────────────────────────────────────────

def _render_faq_tab() -> None:
    df = get_assistant_faq()

    qf1, qf2 = st.columns(2)
    with qf1:
        f_status = st.selectbox(
            "Status", ["Todas", "Ativa", "Rascunho", "Arquivada"],
            key="_aud_faq_f_status",
        )
    with qf2:
        f_cat = st.selectbox(
            "Categoria", ["Todas"] + _FAQ_CATEGORIAS,
            key="_aud_faq_f_cat",
        )

    if not df.empty:
        df_show = df.copy()
        if f_status != "Todas" and "Status" in df.columns:
            df_show = df_show[df_show["Status"].str.strip() == f_status]
        if f_cat != "Todas" and "Categoria" in df.columns:
            df_show = df_show[df_show["Categoria"].str.strip() == f_cat]
    else:
        df_show = df

    if df_show.empty:
        st.info(
            "Nenhuma pergunta frequente cadastrada ainda. "
            "Aprove uma resposta no teste e clique em 'Criar Pergunta Frequente'."
        )
        return

    st.markdown(
        f"<p style='font-size:0.8rem;color:#64748B;margin:0 0 8px;'>"
        f"{len(df_show)} pergunta(s) frequente(s)</p>",
        unsafe_allow_html=True,
    )

    status_colors = {
        "Ativa":     ("#DCFCE7", "#15803D"),
        "Rascunho":  ("#FEF9C3", "#B45309"),
        "Arquivada": ("#F1F5F9", "#64748B"),
    }

    for _, row in df_show.iterrows():
        faq_id     = str(row.get("Id",           "")).strip()
        faq_p      = str(row.get("Pergunta",     "")).strip()
        faq_r      = str(row.get("Resposta",     "")).strip()
        faq_cat    = str(row.get("Categoria",    "")).strip()
        faq_kw     = str(row.get("Palavras_Chave", "")).strip()
        faq_status = str(row.get("Status", "Ativa")).strip()
        faq_dt     = str(row.get("Created_At",   "")).strip()

        sbg, scol = status_colors.get(faq_status, ("#F1F5F9", "#64748B"))

        with st.expander(
            f"⭐ {faq_p[:80]}{'…' if len(faq_p) > 80 else ''}",
            expanded=False,
        ):
            badges = _badge(faq_status, sbg, scol)
            if faq_cat:
                badges += f"&nbsp;{_badge(faq_cat, '#DBEAFE', '#2563EB')}"
            st.markdown(
                f"<div style='display:flex;gap:6px;margin-bottom:8px;'>"
                f"{badges}</div>"
                f"<p style='font-size:0.78rem;font-weight:700;color:{COLOR_NAVY};"
                f"margin:0 0 3px;'>Pergunta</p>"
                f"<p style='font-size:0.85rem;color:#334155;margin:0 0 8px;'>"
                f"{faq_p}</p>"
                f"<p style='font-size:0.78rem;font-weight:700;color:{COLOR_NAVY};"
                f"margin:0 0 3px;'>Resposta</p>"
                f"<p style='font-size:0.84rem;color:#334155;margin:0 0 8px;'>"
                f"{faq_r[:400]}{'…' if len(faq_r) > 400 else ''}</p>",
                unsafe_allow_html=True,
            )
            if faq_kw:
                st.markdown(
                    f"<p style='font-size:0.74rem;color:#64748B;margin:0;'>"
                    f"<strong>Palavras-chave:</strong> {faq_kw}</p>",
                    unsafe_allow_html=True,
                )
            if faq_dt:
                st.markdown(
                    f"<p style='font-size:0.73rem;color:#94A3B8;margin:4px 0 0;'>"
                    f"Criada em: {faq_dt}</p>",
                    unsafe_allow_html=True,
                )


# ── Tab: Métricas ─────────────────────────────────────────────────────────────

def _render_metrics_tab() -> None:
    df     = get_assistant_logs(limit=500)
    df_faq = get_assistant_faq()

    if df.empty:
        st.info(
            "Nenhum dado de auditoria ainda. "
            "Teste perguntas para começar a coletar métricas."
        )
        return

    AVAL_COL = "Avaliacao_Interna"
    ORIG_COL = "Origem_Resposta"
    total    = len(df)

    # Visão geral
    st.markdown(
        f"<p style='font-size:0.78rem;font-weight:700;color:{COLOR_NAVY};"
        f"letter-spacing:0.06em;margin:0 0 8px;'>VISÃO GERAL</p>",
        unsafe_allow_html=True,
    )
    g1, g2, g3, g4, g5 = st.columns(5)

    def _cnt(val: str) -> int:
        if AVAL_COL not in df.columns:
            return 0
        return int((df[AVAL_COL].str.strip() == val).sum())

    g1.metric("Total de perguntas", total)
    g2.metric("FAQs cadastradas",   len(df_faq) if not df_faq.empty else 0)
    g3.metric("Aprovadas",          _cnt("Aprovada"))
    g4.metric("Incorretas",         _cnt("Incorreta"))
    g5.metric("Sem base",           _cnt("Sem base suficiente"))

    st.markdown(
        "<hr style='border-color:#E2E8F0;margin:12px 0;'/>",
        unsafe_allow_html=True,
    )

    col_l, col_r = st.columns(2)

    with col_l:
        if ORIG_COL in df.columns:
            st.markdown(
                f"<p style='font-size:0.76rem;font-weight:700;color:{COLOR_NAVY};"
                f"letter-spacing:0.06em;margin:0 0 8px;'>ORIGEM DAS RESPOSTAS</p>",
                unsafe_allow_html=True,
            )
            for orig_val, count in df[ORIG_COL].value_counts().items():
                pct = round(100 * count / total) if total else 0
                obg, ocol = _ORIGEM_COLOR.get(
                    str(orig_val).strip(), ("#E2E8F0", "#64748B")
                )
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"align-items:center;margin-bottom:5px;'>"
                    f"{_badge(str(orig_val), obg, ocol)}"
                    f"<span style='font-size:0.8rem;color:#334155;'>"
                    f"{count} ({pct}%)</span></div>",
                    unsafe_allow_html=True,
                )

    with col_r:
        if AVAL_COL in df.columns:
            st.markdown(
                f"<p style='font-size:0.76rem;font-weight:700;color:{COLOR_NAVY};"
                f"letter-spacing:0.06em;margin:0 0 8px;'>AVALIAÇÕES</p>",
                unsafe_allow_html=True,
            )
            for av_val, count in df[AVAL_COL].value_counts().items():
                pct = round(100 * count / total) if total else 0
                abg, acol = _AVAL_COLOR.get(
                    str(av_val).strip(), ("#F1F5F9", "#64748B")
                )
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"align-items:center;margin-bottom:5px;'>"
                    f"{_badge(str(av_val), abg, acol)}"
                    f"<span style='font-size:0.8rem;color:#334155;'>"
                    f"{count} ({pct}%)</span></div>",
                    unsafe_allow_html=True,
                )

    # Perguntas mais repetidas
    if "Pergunta" in df.columns:
        st.markdown(
            "<hr style='border-color:#E2E8F0;margin:12px 0;'/>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='font-size:0.76rem;font-weight:700;color:{COLOR_NAVY};"
            f"letter-spacing:0.06em;margin:0 0 8px;'>PERGUNTAS MAIS REPETIDAS</p>",
            unsafe_allow_html=True,
        )
        for q_text, q_count in df["Pergunta"].value_counts().head(10).items():
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;margin-bottom:4px;'>"
                f"<span style='font-size:0.82rem;color:#334155;'>"
                f"{str(q_text)[:72]}</span>"
                f"<span style='font-size:0.8rem;font-weight:700;color:#2563EB;'>"
                f"{q_count}×</span></div>",
                unsafe_allow_html=True,
            )

    # Temas sem base suficiente
    if AVAL_COL in df.columns and "Pergunta" in df.columns:
        df_sem_base = df[df[AVAL_COL].str.strip() == "Sem base suficiente"]
        if not df_sem_base.empty:
            st.markdown(
                "<hr style='border-color:#E2E8F0;margin:12px 0;'/>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<p style='font-size:0.76rem;font-weight:700;color:#DC2626;"
                f"letter-spacing:0.06em;margin:0 0 6px;'>"
                f"TEMAS QUE PRECISAM DE MAIS BASE TÉCNICA</p>",
                unsafe_allow_html=True,
            )
            for q_text in df_sem_base["Pergunta"].unique()[:8]:
                st.markdown(
                    f"<p style='font-size:0.82rem;color:#DC2626;margin:0 0 3px;'>"
                    f"• {str(q_text)[:80]}</p>",
                    unsafe_allow_html=True,
                )


# ── Tab: Busca Web ────────────────────────────────────────────────────────────

def _render_web_search_tab() -> None:
    from web_search_service import (
        WEB_SEARCH_ENABLED, WEB_SEARCH_PROVIDER, WEB_SEARCH_MAX_RESULTS,
        WEB_SEARCH_API_KEY, ALLOWED_DOMAINS, is_enabled,
    )

    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
        f"margin:0 0 0.75rem;'>Configuração de Busca na Internet</p>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    ativada = is_enabled()
    c1.metric("Status",          "✅ Ativada" if ativada else "🔴 Desativada")
    c2.metric("Provider",        WEB_SEARCH_PROVIDER or "—")
    c3.metric("Máx. resultados", WEB_SEARCH_MAX_RESULTS)
    c4.metric("API Key",         "✅ Configurada" if WEB_SEARCH_API_KEY else "⚠️ Ausente")

    st.markdown(
        "<div style='background:#F8FAFF;border:1px solid #BFDBFE;border-radius:10px;"
        "padding:12px 16px;margin:12px 0;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='font-size:0.78rem;font-weight:700;color:{COLOR_NAVY};"
        f"margin:0 0 8px;'>VARIÁVEIS DE AMBIENTE NECESSÁRIAS</p>",
        unsafe_allow_html=True,
    )
    vars_info = [
        ("WEB_SEARCH_ENABLED",     str(WEB_SEARCH_ENABLED), "true | false  (padrão: false)"),
        ("WEB_SEARCH_PROVIDER",    WEB_SEARCH_PROVIDER,     "tavily | brave | duckduckgo"),
        ("WEB_SEARCH_API_KEY",     "****" if WEB_SEARCH_API_KEY else "(não configurada)", "Chave do provider"),
        ("WEB_SEARCH_MAX_RESULTS", str(WEB_SEARCH_MAX_RESULTS), "3 | 5 | 10  (padrão: 5)"),
    ]
    for var, val, desc in vars_info:
        st.markdown(
            f"<p style='font-size:0.78rem;margin:3px 0;'>"
            f"<code style='background:#E2E8F0;padding:1px 6px;border-radius:4px;'>{var}</code> = "
            f"<strong>{val}</strong>"
            f"<span style='color:#94A3B8;'> — {desc}</span></p>",
            unsafe_allow_html=True,
        )
    if not ativada:
        st.markdown(
            "<p style='color:#B45309;font-size:0.8rem;margin:8px 0 0;'>⚠️ "
            "Busca web desativada. Para ativar: defina <code>WEB_SEARCH_ENABLED=true</code> "
            "e <code>WEB_SEARCH_API_KEY</code> no painel Render → Environment.</p>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("🔒 Regras de segurança da busca web", expanded=False):
        st.markdown("""
**Dados que NUNCA saem do servidor:** cliente_id, números de série,
relatórios privados, observações internas, chamados, alertas.

**Decisões críticas que a internet NÃO autoriza:**
parada/partida de máquina, reset de alarme, troca de rolamento,
overhaul, alteração de set point, troca de óleo/componente crítico.

Para essas perguntas o Assistente sempre sugere: _abrir chamado técnico_.
""")

    with st.expander(f"✅ Domínios confiáveis ({len(ALLOWED_DOMAINS)})", expanded=False):
        from collections import defaultdict
        by_cat: dict = defaultdict(list)
        for dom, cat in ALLOWED_DOMAINS.items():
            by_cat[cat].append(dom)
        for cat, doms in sorted(by_cat.items()):
            st.markdown(
                f"<p style='font-size:0.78rem;font-weight:700;color:{COLOR_NAVY};"
                f"margin:6px 0 3px;'>{cat}</p>",
                unsafe_allow_html=True,
            )
            for d in doms:
                st.markdown(
                    f"<span style='font-size:0.77rem;color:#2563EB;margin-right:12px;'>{d}</span>",
                    unsafe_allow_html=True,
                )

    # ── Painel de diagnóstico ────────────────────────────────────────────────
    st.markdown(
        f"<hr style='border-color:#E2E8F0;margin:1rem 0;'/>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
        f"margin:0 0 0.75rem;'>🔬 Diagnóstico — Testar busca agora</p>",
        unsafe_allow_html=True,
    )
    q_teste = st.text_input(
        "Pergunta de teste",
        placeholder="Ex: viscosidade óleo Mobil SHC Gargoyle 220",
        key="_wstest_query",
    )
    if st.button("🔍 Executar busca", key="_wstest_btn"):
        from web_search_service import search as _ws
        from assistant_engine import _sintetizar_com_ia
        with st.spinner("Buscando e sintetizando…"):
            try:
                resultado = _ws(q_teste, client_id="teste", force=True)
            except Exception as exc:
                resultado = {"ok": False, "motivo_skip": str(exc), "resultados": []}
        if resultado.get("ok") and resultado.get("resultados"):
            refs = resultado["resultados"]
            contexto = "\n\n".join(
                f"[{i+1}] {r.get('titulo','')} ({r.get('dominio','')})\n{r.get('resumo','')[:400]}"
                for i, r in enumerate(refs[:4])
            )
            resposta = _sintetizar_com_ia(q_teste, contexto)
            st.success("✅ Resposta sintetizada:")
            st.markdown(resposta)
            st.caption(f"🌐 {len(refs)} fonte(s) consultada(s): {', '.join(r.get('dominio','') for r in refs[:3])}")
            erro_sint = st.session_state.pop("_sintetizar_erro", None)
            if erro_sint:
                st.error(f"⚠️ Erro interno na síntese: {erro_sint}")
        else:
            motivo = resultado.get("motivo_skip") or "Sem resultado"
            st.error(f"❌ {motivo}")

    st.markdown(
        f"<hr style='border-color:#E2E8F0;margin:1rem 0;'/>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
        f"margin:0 0 0.75rem;'>Logs de Busca Web</p>",
        unsafe_allow_html=True,
    )
    try:
        from sheets import get_web_search_logs
        df_wsl = get_web_search_logs(limit=50)
    except Exception:
        df_wsl = None

    if df_wsl is None or (hasattr(df_wsl, "empty") and df_wsl.empty):
        st.info("Nenhuma busca web registrada ainda.")
        return

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.8rem;margin:0 0 8px;'>{len(df_wsl)} busca(s)</p>",
        unsafe_allow_html=True,
    )
    for _, row in df_wsl.iterrows():
        cache = str(row.get("Cache_Hit", "")).strip()
        n_res = str(row.get("N_Resultados", "")).strip()
        erro  = str(row.get("Erro", "")).strip()
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:8px;padding:10px 14px;margin-bottom:6px;'>"
            f"<p style='font-weight:700;font-size:0.82rem;color:{COLOR_NAVY};margin:0 0 3px;'>{str(row.get('Pergunta_Original',''))[:80]}</p>"
            f"<p style='font-size:0.75rem;color:#64748B;margin:0 0 2px;'>Query limpa: {str(row.get('Query_Limpa',''))[:80]}</p>"
            f"<p style='font-size:0.75rem;color:#475569;margin:0;'>Domínios: {str(row.get('Dominios',''))[:80]} | Resultados: {n_res} | Cache: {cache}</p>"
            + (f"<p style='color:#DC2626;font-size:0.73rem;margin:2px 0 0;'>⚠️ {erro}</p>" if erro else "")
            + f"<p style='font-size:0.7rem;color:{COLOR_MUTED};margin:4px 0 0;'>{str(row.get('Created_At',''))}</p></div>",
            unsafe_allow_html=True,
        )
