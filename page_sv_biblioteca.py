"""Supervisão — Biblioteca Técnica (cadastro de documentos técnicos)."""
import streamlit as st
from auth import require_staff
from sheets import (
    get_all_clientes, get_documentos_tecnicos,
    add_documento_tecnico, delete_documento_tecnico,
)
from ui import (
    sv_page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER,
    COLOR_MUTED, COLOR_BLUE,
)
from document_processor import STATUS_INDEXADO, STATUS_FALHOU, STATUS_PROCESSANDO, STATUS_NAO_INDEXADO

_TIPOS_DOC = [
    "Manual técnico", "Datasheet", "Catálogo do fabricante",
    "Especificação de óleo", "Procedimento de manutenção",
    "Instrução de segurança", "FAQ técnico", "Outro",
]

_VISIBILIDADE_OPTS = [
    "Vinculado a cliente específico",
    "Público para clientes autorizados",
    "Vinculado a ativo específico",
    "Apenas equipe Pred.IO",
]

_STATUS_OPTS = ["Ativo", "Em revisão", "Arquivado"]

_VIS_BADGE = {
    "Vinculado a cliente específico":    ("#2563EB22", "#2563EB"),
    "Público para clientes autorizados": ("#16A34A22", "#16A34A"),
    "Vinculado a ativo específico":      ("#F59E0B22", "#B45309"),
    "Apenas equipe Pred.IO":             ("#EF444422", "#EF4444"),
}

_STATUS_BADGE = {
    "Ativo":      ("#16A34A22", "#16A34A"),
    "Em revisão": ("#F59E0B22", "#B45309"),
    "Arquivado":  ("#94A3B822", "#64748B"),
}

_IDX_BADGE = {
    STATUS_INDEXADO:     ("#DCFCE7", "#15803D"),
    STATUS_FALHOU:       ("#FEE2E2", "#DC2626"),
    STATUS_PROCESSANDO:  ("#FEF9C3", "#B45309"),
    STATUS_NAO_INDEXADO: ("#F1F5F9", "#64748B"),
    "":                  ("#F1F5F9", "#64748B"),
}


def render() -> None:
    require_staff()
    sv_page_header(
        "📚 Biblioteca Técnica",
        "Cadastre manuais, catálogos, datasheets e documentos técnicos "
        "usados pelo Assistente Pred.IO.",
    )

    # ── Formulário ────────────────────────────────────────────────────────────
    with st.expander("➕ Cadastrar novo documento", expanded=False):
        _render_form_cadastro()

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0 1.5rem;'/>",
        unsafe_allow_html=True,
    )

    # ── Filtros de lista ──────────────────────────────────────────────────────
    f1, f2, f3 = st.columns(3)
    with f1:
        filtro_tipo = st.selectbox(
            "Filtrar por tipo", ["Todos"] + _TIPOS_DOC, key="_svbib_ftipo"
        )
    with f2:
        filtro_vis = st.selectbox(
            "Filtrar por visibilidade",
            ["Todos"] + _VISIBILIDADE_OPTS,
            key="_svbib_fvis",
        )
    with f3:
        filtro_txt = st.text_input("Buscar", placeholder="título, fabricante, modelo…", key="_svbib_fbusca")

    # ── Lista ─────────────────────────────────────────────────────────────────
    df = get_documentos_tecnicos(staff=True)

    if df.empty:
        st.info("Nenhum documento cadastrado. Use o formulário acima para adicionar.")
        return

    if filtro_tipo != "Todos":
        df = df[df["Tipo_Documento"].str.strip() == filtro_tipo]
    if filtro_vis != "Todos":
        df = df[df["Visibilidade"].str.strip() == filtro_vis]
    if filtro_txt.strip():
        txt = filtro_txt.strip().lower()
        mask = (
            df["Titulo"].str.lower().str.contains(txt, na=False)
            | df["Fabricante"].str.lower().str.contains(txt, na=False)
            | df["Modelo"].str.lower().str.contains(txt, na=False)
            | df["Palavras_Chave"].str.lower().str.contains(txt, na=False)
        )
        df = df[mask]

    if df.empty:
        st.info("Nenhum documento encontrado com os filtros aplicados.")
        return

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.8rem;margin:0 0 0.75rem;'>"
        f"{len(df)} documento(s) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    for _, row in df.iterrows():
        _render_card(row)


def _render_form_cadastro() -> None:
    df_cli = get_all_clientes()
    empresas = (
        sorted(df_cli["Empresa"].dropna().unique().tolist())
        if not df_cli.empty and "Empresa" in df_cli.columns
        else []
    )

    with st.form("form_add_doc_bib", clear_on_submit=True):
        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0 0 0.75rem;'>Informações do documento</p>",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            titulo = st.text_input("Título *", placeholder="Ex: Manual Técnico - Compressor 200 VLD")
        with c2:
            tipo_doc = st.selectbox("Tipo de documento *", _TIPOS_DOC)

        c3, c4 = st.columns(2)
        with c3:
            fabricante = st.text_input("Fabricante", placeholder="Ex: WEG, Atlas Copco…")
        with c4:
            modelo = st.text_input("Modelo", placeholder="Ex: 200 VLD, 350 CV…")

        numero_serie = st.text_input("Número de série / Rev.", placeholder="Opcional")

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0.75rem 0 0.5rem;'>Vinculação</p>",
            unsafe_allow_html=True,
        )

        c5, c6 = st.columns(2)
        with c5:
            visibilidade = st.selectbox("Visibilidade *", _VISIBILIDADE_OPTS)
        with c6:
            cli_opcoes = ["— nenhum —"] + empresas
            empresa_sel = st.selectbox("Cliente (se vinculado)", cli_opcoes)

        c7, c8 = st.columns(2)
        with c7:
            ativo_id = st.text_input("Ativo ID (opcional)", placeholder="Ex: ativo-001")
        with c8:
            componente_id = st.text_input("Componente ID (opcional)", placeholder="Ex: comp-001")

        planta_id = st.text_input("Planta ID (opcional)")

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0.75rem 0 0.5rem;'>Arquivo</p>",
            unsafe_allow_html=True,
        )

        c9, c10 = st.columns(2)
        with c9:
            arquivo_url = st.text_input(
                "URL do arquivo *",
                placeholder="https://drive.google.com/… ou /docs/manual.pdf",
            )
        with c10:
            arquivo_nome = st.text_input(
                "Nome do arquivo", placeholder="manual-compressor-200vld.pdf"
            )

        resumo = st.text_area(
            "Resumo",
            placeholder="Descreva o conteúdo e finalidade deste documento…",
            height=75,
        )
        palavras_chave = st.text_input(
            "Palavras-chave (separadas por vírgula)",
            placeholder="compressor, manual, 200 VLD, manutenção…",
        )

        c11, c12 = st.columns(2)
        with c11:
            status = st.selectbox("Status", _STATUS_OPTS)
        obs_internas = st.text_area(
            "Observações internas (não aparece para cliente)",
            height=60,
        )

        submitted = st.form_submit_button(
            "📚 Cadastrar documento", type="primary", use_container_width=True
        )

    if submitted:
        if not titulo.strip():
            st.warning("O título do documento é obrigatório.")
            return
        if not arquivo_url.strip():
            st.warning("A URL do arquivo é obrigatória.")
            return

        # Deriva client_id da empresa selecionada (nunca do front-end direto)
        client_id = ""
        if empresa_sel != "— nenhum —" and not df_cli.empty and "Cliente_Id" in df_cli.columns:
            m = df_cli[df_cli["Empresa"].str.strip() == empresa_sel.strip()]
            client_id = str(m.iloc[0]["Cliente_Id"]).strip().lower() if not m.empty else empresa_sel.strip().lower()
        elif empresa_sel != "— nenhum —":
            client_id = empresa_sel.strip().lower()

        doc_id = add_documento_tecnico({
            "titulo":              titulo.strip(),
            "tipo_documento":      tipo_doc,
            "cliente_id":          client_id,
            "planta_id":           planta_id.strip(),
            "ativo_id":            ativo_id.strip(),
            "componente_id":       componente_id.strip(),
            "fabricante":          fabricante.strip(),
            "modelo":              modelo.strip(),
            "numero_serie":        numero_serie.strip(),
            "arquivo_url":         arquivo_url.strip(),
            "arquivo_nome":        arquivo_nome.strip() or arquivo_url.split("/")[-1],
            "resumo":              resumo.strip(),
            "palavras_chave":      palavras_chave.strip(),
            "visibilidade":        visibilidade,
            "status":              status,
            "observacoes_internas": obs_internas.strip(),
        })

        if doc_id:
            st.success(f"✅ Documento cadastrado com ID {doc_id}.")
            st.rerun()
        else:
            st.error("Erro ao cadastrar. Verifique as credenciais do Google Sheets.")


def _render_card(row) -> None:
    doc_id    = str(row.get("Id",             "")).strip()
    titulo    = str(row.get("Titulo",         "")).strip()
    tipo      = str(row.get("Tipo_Documento", "")).strip()
    cliente   = str(row.get("Cliente_Id",     "")).strip()
    ativo_id  = str(row.get("Ativo_Id",       "")).strip()
    comp_id   = str(row.get("Componente_Id",  "")).strip()
    fab       = str(row.get("Fabricante",     "")).strip()
    modelo    = str(row.get("Modelo",         "")).strip()
    resumo    = str(row.get("Resumo",         "")).strip()
    arq_nome  = str(row.get("Arquivo_Nome",   "")).strip()
    arq_url   = str(row.get("Arquivo_Url",    "")).strip()
    vis       = str(row.get("Visibilidade",   "")).strip()
    status    = str(row.get("Status",         "")).strip()
    obs       = str(row.get("Observacoes_Internas", "")).strip()
    st_idx    = str(row.get("Status_Indexacao", "")).strip() or STATUS_NAO_INDEXADO
    dt_idx    = str(row.get("Data_Indexacao",  "")).strip()
    n_pags    = str(row.get("Quantidade_Paginas", "")).strip()
    erro_idx  = str(row.get("Erro_Indexacao",  "")).strip()

    vis_bg, vis_tc   = _VIS_BADGE.get(vis,    ("#E2E8F022", "#64748B"))
    stat_bg, stat_tc = _STATUS_BADGE.get(status, ("#E2E8F022", "#64748B"))
    idx_bg, idx_tc   = _IDX_BADGE.get(st_idx, ("#F1F5F9", "#64748B"))

    col_info, col_del = st.columns([10, 0.7])
    with col_info:
        meta_parts = []
        if fab:    meta_parts.append(f"🏭 {fab}")
        if modelo: meta_parts.append(f"⚙️ {modelo}")
        if cliente: meta_parts.append(f"👤 {cliente}")
        meta_html = " &nbsp;·&nbsp; ".join(meta_parts)

        link_html = (
            f"<a href='{arq_url}' target='_blank' "
            f"style='font-size:0.72rem;color:{COLOR_BLUE};-webkit-text-fill-color:{COLOR_BLUE};'>"
            f"🔗 {arq_nome or arq_url}</a>"
            if arq_url else ""
        )

        obs_html = (
            f"<p style='color:#F97316;font-size:0.72rem;margin:4px 0 0;'>"
            f"📌 Obs. internas: {obs}</p>"
            if obs else ""
        )

        idx_detail = ""
        if st_idx == STATUS_INDEXADO and dt_idx:
            idx_detail = f" &nbsp;·&nbsp; {n_pags + ' pág.' if n_pags else ''} &nbsp;·&nbsp; {dt_idx}"
        elif st_idx == STATUS_FALHOU and erro_idx:
            idx_detail = f" &nbsp;·&nbsp; Erro: {erro_idx[:80]}"

        idx_html = (
            f"<span style='background:{idx_bg};color:{idx_tc};-webkit-text-fill-color:{idx_tc};"
            f"font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:10px;"
            f"border:1px solid {idx_tc}33;'>{st_idx}</span>"
            f"<span style='color:{COLOR_MUTED};font-size:0.65rem;'>{idx_detail}</span>"
        )

        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:10px;padding:12px 16px;margin-bottom:4px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-start;"
            f"flex-wrap:wrap;gap:6px;margin-bottom:6px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;'>{titulo}</span>"
            f"<div style='display:flex;gap:5px;flex-wrap:wrap;'>"
            f"<span style='background:{vis_bg};color:{vis_tc};-webkit-text-fill-color:{vis_tc};"
            f"font-size:0.68rem;font-weight:700;padding:2px 10px;border-radius:10px;"
            f"border:1px solid {vis_tc}44;'>{vis}</span>"
            f"<span style='background:{stat_bg};color:{stat_tc};-webkit-text-fill-color:{stat_tc};"
            f"font-size:0.68rem;font-weight:700;padding:2px 10px;border-radius:10px;"
            f"border:1px solid {stat_tc}44;'>{status}</span>"
            f"<span style='background:#EFF6FF;color:{COLOR_BLUE};-webkit-text-fill-color:{COLOR_BLUE};"
            f"font-size:0.68rem;font-weight:700;padding:2px 10px;border-radius:10px;"
            f"border:1px solid #BFDBFE;'>📄 {tipo}</span>"
            f"</div></div>"
            + (f"<p style='color:{COLOR_MUTED};font-size:0.77rem;margin:0 0 4px;'>{meta_html}</p>" if meta_html else "")
            + (f"<p style='color:#475569;font-size:0.8rem;margin:0 0 4px;'>{resumo}</p>" if resumo else "")
            + (f"<p style='font-size:0.72rem;margin:0 0 4px;'>{link_html}</p>" if link_html else "")
            + f"<div style='margin-top:6px;display:flex;align-items:center;gap:6px;'>{idx_html}</div>"
            + obs_html
            + "</div>",
            unsafe_allow_html=True,
        )

        # Botões processar / reprocessar e testar
        if doc_id and arq_url:
            btn_label = "🔄 Reprocessar" if st_idx == STATUS_INDEXADO else "⚙️ Processar documento"
            col_proc, col_test, _ = st.columns([3, 3, 4])
            with col_proc:
                if st.button(btn_label, key=f"proc_{doc_id}", use_container_width=True):
                    with st.spinner("Processando…"):
                        from document_processor import processar_documento
                        result = processar_documento(
                            doc_id=doc_id,
                            cliente_id=cliente,
                            ativo_id=ativo_id,
                            componente_id=comp_id,
                            arquivo_url=arq_url,
                            arquivo_nome=arq_nome,
                        )
                    if result["ok"]:
                        st.success(
                            f"✅ Indexado: {result['n_chunks']} chunks, "
                            f"{result['n_paginas']} páginas."
                        )
                        st.rerun()
                    else:
                        st.error(f"❌ {result['erro']}")

            with col_test:
                if st_idx == STATUS_INDEXADO:
                    if st.button("🔍 Testar no Assistente", key=f"test_{doc_id}", use_container_width=True):
                        st.session_state[f"_test_open_{doc_id}"] = not st.session_state.get(f"_test_open_{doc_id}", False)

            # Painel de teste — busca nos chunks indexados
            if st.session_state.get(f"_test_open_{doc_id}") and st_idx == STATUS_INDEXADO:
                with st.container():
                    st.markdown(
                        f"<div style='background:#F8FAFF;border:1px solid #BFDBFE;"
                        f"border-radius:10px;padding:12px 16px;margin:6px 0 8px;'>",
                        unsafe_allow_html=True,
                    )
                    q = st.text_input(
                        "Pergunta de teste",
                        placeholder="Ex: como resetar alarme? / set point de temperatura",
                        key=f"_test_q_{doc_id}",
                    )
                    if q.strip():
                        from sheets import buscar_chunks
                        hits = buscar_chunks(cliente or "", q.strip(), top_n=3)
                        if hits:
                            st.markdown(
                                f"<p style='color:#15803D;font-size:0.78rem;font-weight:700;"
                                f"margin:4px 0;'>✅ {len(hits)} chunk(s) encontrado(s):</p>",
                                unsafe_allow_html=True,
                            )
                            for i, h in enumerate(hits, 1):
                                st.markdown(
                                    f"<div style='background:#fff;border:1px solid #E2E8F0;"
                                    f"border-radius:8px;padding:10px 12px;margin-bottom:6px;'>"
                                    f"<p style='font-weight:700;font-size:0.78rem;color:#0F1F3D;"
                                    f"margin:0 0 4px;'>{i}. {h.get('t','(sem título)')}</p>"
                                    f"<p style='font-size:0.76rem;color:#334155;margin:0;'>"
                                    f"{h.get('c','')[:300]}</p>"
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.markdown(
                                "<p style='color:#B45309;font-size:0.78rem;'>"
                                "⚠️ Nenhum chunk correspondente. Tente termos diferentes.</p>",
                                unsafe_allow_html=True,
                            )
                    st.markdown("</div>", unsafe_allow_html=True)

    with col_del:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        if st.button("🗑️", key=f"del_doc_{doc_id}", help="Remover", use_container_width=True):
            if delete_documento_tecnico(doc_id):
                st.toast("🗑️ Documento removido.")
                st.rerun()
            else:
                st.toast("⚠️ Não foi possível remover.")
