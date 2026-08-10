"""Supervisão — Biblioteca Técnica (cadastro de documentos técnicos)."""
import streamlit as st
from auth import require_staff, current_email, current_perfil
from sheets import (
    get_all_clientes, get_documentos_tecnicos,
    add_documento_tecnico, update_documento_tecnico, delete_documento_tecnico,
    delete_chunks_documento, log_audit, ativo_pertence_cliente,
)
from ui import (
    sv_page_header, empty_state, COLOR_NAVY, COLOR_CARD, COLOR_BORDER,
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
        empty_state("Nenhum documento cadastrado. Use o formulário acima para adicionar.", icon="📚")
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
        empty_state("Nenhum documento encontrado com os filtros aplicados.", icon="📚")
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

        arquivo_upload = st.file_uploader(
            "Enviar PDF do PC",
            type=["pdf"],
            key="bib_arquivo_upload",
            help="Envie o arquivo PDF diretamente. Ele será indexado automaticamente após o cadastro.",
        )
        _file_bytes = arquivo_upload.read() if arquivo_upload else None
        _file_name  = arquivo_upload.name   if arquivo_upload else ""

        st.markdown(
            f"<p style='color:#64748B;font-size:0.78rem;margin:4px 0 8px;'>"
            f"OU informe a URL do arquivo (Google Drive, site, etc.)</p>",
            unsafe_allow_html=True,
        )

        c9, c10 = st.columns(2)
        with c9:
            arquivo_url = st.text_input(
                "URL do arquivo",
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
        if not _file_bytes and not arquivo_url.strip():
            st.warning("Envie um arquivo PDF ou informe a URL do arquivo.")
            return
        _MAX_PDF_MB = 15
        if _file_bytes and len(_file_bytes) > _MAX_PDF_MB * 1024 * 1024:
            st.warning(f"Arquivo muito grande ({len(_file_bytes)//1024//1024} MB). Limite: {_MAX_PDF_MB} MB.")
            return

        # Deriva client_id da empresa selecionada (nunca do front-end direto)
        client_id = ""
        if empresa_sel != "— nenhum —" and not df_cli.empty and "Cliente_Id" in df_cli.columns:
            m = df_cli[df_cli["Empresa"].str.strip() == empresa_sel.strip()]
            client_id = str(m.iloc[0]["Cliente_Id"]).strip().lower() if not m.empty else empresa_sel.strip().lower()
        elif empresa_sel != "— nenhum —":
            client_id = empresa_sel.strip().lower()

        if ativo_id.strip() and client_id and not ativo_pertence_cliente(ativo_id.strip(), client_id):
            st.warning("O Ativo ID informado não pertence ao cliente selecionado.")
            return

        # Arquivo enviado do PC tem prioridade sobre URL
        _usar_upload = bool(_file_bytes)
        _nome_final  = (arquivo_nome.strip()
                        or (_file_name if _usar_upload else arquivo_url.strip().split("/")[-1]))

        # Arquivo de upload processado direto em memória (sem storage externo)
        _url_final = arquivo_url.strip() if not _usar_upload else ""

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
            "arquivo_url":         _url_final,
            "arquivo_nome":        _nome_final,
            "resumo":              resumo.strip(),
            "palavras_chave":      palavras_chave.strip(),
            "visibilidade":        visibilidade,
            "status":              status,
            "observacoes_internas": obs_internas.strip(),
            "origem_arquivo":      "upload" if _usar_upload else "url",
        })

        if doc_id:
            log_audit(current_email(), current_perfil(), client_id,
                      "documento_criado", recurso_tipo="documento_tecnico", recurso_id=doc_id)
            if _usar_upload:
                _erro_upload_doc = None
                with st.spinner("Enviando arquivo…"):
                    try:
                        from drive_storage import upload_document_pdf
                        storage_path = upload_document_pdf(
                            _file_bytes, client_id, ativo_id.strip(), doc_id, _nome_final,
                        )
                        update_documento_tecnico(doc_id, {
                            "Storage_Path": storage_path,
                            "Arquivo_Nome": _nome_final,
                            "Arquivo_Url":  "",
                        })
                    except Exception as exc:
                        _erro_upload_doc = str(exc)

                if _erro_upload_doc:
                    st.toast(f"⚠️ Falha ao salvar o arquivo: {_erro_upload_doc}", icon="⚠️")
                else:
                    with st.spinner("Indexando documento…"):
                        from document_processor import processar_documento_from_bytes
                        result = processar_documento_from_bytes(
                            doc_id=doc_id,
                            cliente_id=client_id,
                            ativo_id=ativo_id.strip(),
                            componente_id=componente_id.strip(),
                            file_bytes=_file_bytes,
                            arquivo_nome=_nome_final,
                        )
                    if result["ok"]:
                        log_audit(current_email(), current_perfil(), client_id,
                                  "documento_processado", recurso_tipo="documento_tecnico", recurso_id=doc_id)
                        st.toast(
                            f"✅ Arquivo salvo e indexado — "
                            f"{result['n_chunks']} chunks, {result['n_paginas']} página(s).",
                            icon="✅",
                        )
                    else:
                        log_audit(current_email(), current_perfil(), client_id,
                                  "falha_indexacao", recurso_tipo="documento_tecnico",
                                  recurso_id=doc_id, resultado="falha")
                        _msg_erro = result["erro"]
                        if "Texto não extraído" in _msg_erro:
                            _msg_erro = ("Este PDF parece ser escaneado e não possui texto extraível. "
                                         "Será necessário OCR para indexação pela IA.")
                        st.toast(
                            f"⚠️ Arquivo salvo no storage, mas indexação falhou: {_msg_erro}",
                            icon="⚠️",
                        )
            else:
                st.toast("✅ Documento cadastrado com sucesso.", icon="✅")
            st.rerun()
        else:
            st.error("Erro ao cadastrar. Verifique as credenciais do Google Sheets.")


def _render_form_edicao(doc_id: str, row) -> None:
    """Edição de um documento já cadastrado — mesmo padrão de
    page_sv_ativos.py's _render_edit_ativo() (expander + form
    pré-preenchido, chamando a função de update já existente)."""
    df_cli = get_all_clientes()
    empresas = (
        sorted(df_cli["Empresa"].dropna().unique().tolist())
        if not df_cli.empty and "Empresa" in df_cli.columns
        else []
    )

    cliente_atual_id = str(row.get("Cliente_Id", "")).strip().lower()
    empresa_atual = "— nenhum —"
    if cliente_atual_id and not df_cli.empty and "Cliente_Id" in df_cli.columns:
        m = df_cli[df_cli["Cliente_Id"].str.strip().str.lower() == cliente_atual_id]
        if not m.empty:
            empresa_atual = str(m.iloc[0]["Empresa"]).strip()

    cli_opcoes = ["— nenhum —"] + empresas
    _safe_idx = lambda opts, val: opts.index(val) if val in opts else 0

    with st.form(f"form_edit_doc_{doc_id}"):
        c1, c2 = st.columns(2)
        with c1:
            novo_titulo = st.text_input("Título *", value=str(row.get("Titulo", "")).strip())
        with c2:
            novo_tipo = st.selectbox(
                "Tipo de documento *", _TIPOS_DOC,
                index=_safe_idx(_TIPOS_DOC, str(row.get("Tipo_Documento", "")).strip()),
            )

        c3, c4 = st.columns(2)
        with c3:
            novo_fab = st.text_input("Fabricante", value=str(row.get("Fabricante", "")).strip())
        with c4:
            novo_modelo = st.text_input("Modelo", value=str(row.get("Modelo", "")).strip())

        c5, c6 = st.columns(2)
        with c5:
            nova_vis = st.selectbox(
                "Visibilidade *", _VISIBILIDADE_OPTS,
                index=_safe_idx(_VISIBILIDADE_OPTS, str(row.get("Visibilidade", "")).strip()),
            )
        with c6:
            nova_empresa_sel = st.selectbox(
                "Cliente (se vinculado)", cli_opcoes, index=_safe_idx(cli_opcoes, empresa_atual),
            )

        c7, c8 = st.columns(2)
        with c7:
            novo_ativo_id = st.text_input("Ativo ID (opcional)", value=str(row.get("Ativo_Id", "")).strip())
        with c8:
            novo_status = st.selectbox(
                "Status", _STATUS_OPTS,
                index=_safe_idx(_STATUS_OPTS, str(row.get("Status", "")).strip() or "Ativo"),
            )

        novo_resumo = st.text_area(
            "Resumo", value=str(row.get("Resumo", "")).strip(), height=75,
        )
        novas_palavras = st.text_input(
            "Palavras-chave (separadas por vírgula)",
            value=str(row.get("Palavras_Chave", "")).strip(),
        )

        uso_ia_atual = str(row.get("Uso_Pela_Ia", "")).strip().lower()
        uso_ia_opts = ["Permitido (padrão)", "Bloqueado para o Assistente"]
        novo_uso_ia = st.selectbox(
            "Uso pelo Assistente IA", uso_ia_opts,
            index=1 if uso_ia_atual == "false" else 0,
        )

        st.markdown(
            f"<p style='font-size:0.78rem;color:{COLOR_MUTED};margin:10px 0 4px;'>"
            f"Substituir arquivo (opcional) — envia um PDF novo, remove os chunks "
            f"antigos e marca o documento para reprocessar.</p>",
            unsafe_allow_html=True,
        )
        novo_arquivo = st.file_uploader("Novo PDF", type=["pdf"], key=f"_edit_file_{doc_id}")
        _novo_bytes = novo_arquivo.read() if novo_arquivo else None
        _novo_nome = novo_arquivo.name if novo_arquivo else ""

        salvar = st.form_submit_button("💾 Salvar alterações", type="primary", use_container_width=True)

    if not salvar:
        return

    if not novo_titulo.strip():
        st.warning("O título do documento é obrigatório.")
        return

    novo_client_id = ""
    if nova_empresa_sel != "— nenhum —" and not df_cli.empty and "Cliente_Id" in df_cli.columns:
        m = df_cli[df_cli["Empresa"].str.strip() == nova_empresa_sel.strip()]
        novo_client_id = str(m.iloc[0]["Cliente_Id"]).strip().lower() if not m.empty else nova_empresa_sel.strip().lower()
    elif nova_empresa_sel != "— nenhum —":
        novo_client_id = nova_empresa_sel.strip().lower()

    if novo_ativo_id.strip() and novo_client_id and not ativo_pertence_cliente(novo_ativo_id.strip(), novo_client_id):
        st.warning("O Ativo ID informado não pertence ao cliente selecionado.")
        return

    campos = {
        "Titulo":         novo_titulo.strip(),
        "Tipo_Documento": novo_tipo,
        "Fabricante":     novo_fab.strip(),
        "Modelo":         novo_modelo.strip(),
        "Visibilidade":   nova_vis,
        "Cliente_Id":     novo_client_id,
        "Ativo_Id":       novo_ativo_id.strip(),
        "Status":         novo_status,
        "Resumo":         novo_resumo.strip(),
        "Palavras_Chave": novas_palavras.strip(),
        "Uso_Pela_Ia":    "false" if novo_uso_ia == uso_ia_opts[1] else "",
    }

    if _novo_bytes:
        try:
            from drive_storage import upload_document_pdf
            novo_storage_path = upload_document_pdf(_novo_bytes, novo_client_id, novo_ativo_id.strip(), doc_id, _novo_nome)
            delete_chunks_documento(doc_id)
            campos.update({
                "Storage_Path":       novo_storage_path,
                "Arquivo_Nome":       _novo_nome,
                "Arquivo_Url":        "",
                "Indexado_Para_Ia":   "Não indexado",
                "Erro_Indexacao":     "",
                "Quantidade_Paginas": "",
            })
        except Exception as exc:
            st.error(f"Falha ao enviar o novo arquivo: {exc}")
            return

    if update_documento_tecnico(doc_id, campos):
        log_audit(current_email(), current_perfil(), novo_client_id,
                  "arquivo_substituido" if _novo_bytes else "documento_editado",
                  recurso_tipo="documento_tecnico", recurso_id=doc_id)
        st.session_state.pop(f"_edit_open_{doc_id}", None)
        st.toast("✅ Documento atualizado.", icon="✅")
        st.rerun()
    else:
        st.error("Erro ao salvar as alterações.")


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
    storage_path = str(row.get("Storage_Path", "")).strip()
    # Storage privado tem prioridade — gera link assinado de curta duração
    # sob demanda (nunca reaproveita entre reruns); Arquivo_Url só é usado
    # para documentos cadastrados antes deste mecanismo existir.
    if storage_path and storage_path.lower() not in ("", "nan"):
        try:
            from drive_storage import get_document_pdf_url
            arq_url = get_document_pdf_url(storage_path)
        except Exception:
            pass  # mantém arq_url original (Arquivo_Url) se o storage_path for inválido
    vis       = str(row.get("Visibilidade",   "")).strip()
    status    = str(row.get("Status",         "")).strip()
    obs       = str(row.get("Observacoes_Internas", "")).strip()
    st_idx    = str(row.get("Indexado_Para_Ia", "")).strip() or STATUS_NAO_INDEXADO
    dt_idx    = str(row.get("Data_Indexacao",  "")).strip()
    n_pags    = str(row.get("Quantidade_Paginas", "")).strip()
    erro_idx  = str(row.get("Erro_Indexacao",  "")).strip()

    # Arquivo prometido na planilha (Storage_Path) mas ausente de verdade
    # no storage — nunca deve deixar processar/reprocessar um PDF que não
    # existe.
    arquivo_ausente = bool(storage_path) and storage_path.startswith("biblioteca/")
    if arquivo_ausente:
        try:
            from drive_storage import document_pdf_exists
            arquivo_ausente = not document_pdf_exists(storage_path)
        except Exception:
            arquivo_ausente = False

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
            + (
                "<p style='color:#DC2626;font-size:0.75rem;margin:6px 0 0;'>"
                "⚠️ Arquivo não encontrado no storage. Substitua ou envie novamente o PDF "
                "(veja Editar).</p>" if arquivo_ausente else ""
            )
            + "</div>",
            unsafe_allow_html=True,
        )

        # Botões processar / reprocessar e testar
        if doc_id:
            col_proc, col_test, _ = st.columns([3, 3, 4])
            with col_proc:
                if arquivo_ausente:
                    st.button("⚙️ Processar documento", key=f"proc_{doc_id}_x",
                              disabled=True, use_container_width=True,
                              help="Arquivo ausente no storage — substitua o arquivo antes de processar.")
                elif arq_url:
                    btn_label = "🔄 Reprocessar" if st_idx == STATUS_INDEXADO else "⚙️ Processar documento"
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
                            log_audit(current_email(), current_perfil(), cliente,
                                      "documento_reprocessado" if st_idx == STATUS_INDEXADO else "documento_processado",
                                      recurso_tipo="documento_tecnico", recurso_id=doc_id)
                            st.success(
                                f"✅ Indexado: {result['n_chunks']} chunks, "
                                f"{result['n_paginas']} páginas."
                            )
                            st.rerun()
                        else:
                            log_audit(current_email(), current_perfil(), cliente,
                                      "falha_indexacao", recurso_tipo="documento_tecnico",
                                      recurso_id=doc_id, resultado="falha")
                            _msg_erro = result["erro"]
                            if "Texto não extraído" in _msg_erro:
                                _msg_erro = ("Este PDF parece ser escaneado e não possui texto extraível. "
                                             "Será necessário OCR para indexação pela IA.")
                            st.error(f"❌ {_msg_erro}")
                elif st_idx != STATUS_INDEXADO:
                    if st.button("📤 Reindexar arquivo", key=f"reup_{doc_id}", use_container_width=True):
                        st.session_state[f"_reup_open_{doc_id}"] = not st.session_state.get(f"_reup_open_{doc_id}", False)

            with col_test:
                if st_idx == STATUS_INDEXADO:
                    if st.button("🔍 Testar no Assistente", key=f"test_{doc_id}", use_container_width=True):
                        st.session_state[f"_test_open_{doc_id}"] = not st.session_state.get(f"_test_open_{doc_id}", False)

            col_edit, col_arq, _sp = st.columns([3, 3, 4])
            with col_edit:
                if st.button("✏️ Editar", key=f"edit_{doc_id}", use_container_width=True):
                    st.session_state[f"_edit_open_{doc_id}"] = not st.session_state.get(f"_edit_open_{doc_id}", False)
            with col_arq:
                if status != "Arquivado":
                    if st.button("📦 Arquivar", key=f"arq_{doc_id}", use_container_width=True):
                        if update_documento_tecnico(doc_id, {"Status": "Arquivado"}):
                            log_audit(current_email(), current_perfil(), cliente,
                                      "documento_arquivado", recurso_tipo="documento_tecnico", recurso_id=doc_id)
                            st.toast("📦 Documento arquivado.")
                            st.rerun()

            if st.session_state.get(f"_edit_open_{doc_id}"):
                with st.container():
                    st.markdown(
                        "<div style='background:#F8FAFC;border:1px solid #CBD5E1;"
                        "border-radius:10px;padding:12px 16px;margin:6px 0 8px;'>",
                        unsafe_allow_html=True,
                    )
                    _render_form_edicao(doc_id, row)
                    st.markdown("</div>", unsafe_allow_html=True)

            # Painel de re-upload (documentos enviados via upload com indexação pendente ou falhou)
            if not arq_url and st.session_state.get(f"_reup_open_{doc_id}") and st_idx != STATUS_INDEXADO:
                with st.container():
                    st.markdown(
                        "<div style='background:#FFF7ED;border:1px solid #FED7AA;"
                        "border-radius:10px;padding:12px 16px;margin:6px 0 8px;'>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        "<p style='font-size:0.8rem;color:#92400E;margin:0 0 8px;'>"
                        "📤 O arquivo original do upload não fica armazenado. "
                        "Selecione o arquivo novamente para reprocessar.</p>",
                        unsafe_allow_html=True,
                    )
                    reup_file = st.file_uploader(
                        "Arquivo PDF",
                        type=["pdf"],
                        key=f"_reup_file_{doc_id}",
                        label_visibility="collapsed",
                    )
                    if reup_file:
                        if st.button("⚙️ Processar agora", key=f"_reup_proc_{doc_id}", type="primary"):
                            with st.spinner("Reprocessando…"):
                                from document_processor import processar_documento_from_bytes
                                result = processar_documento_from_bytes(
                                    doc_id=doc_id,
                                    cliente_id=cliente,
                                    ativo_id=ativo_id,
                                    componente_id=comp_id,
                                    file_bytes=reup_file.read(),
                                    arquivo_nome=reup_file.name or arq_nome,
                                )
                            if result["ok"]:
                                st.success(f"✅ Indexado: {result['n_chunks']} chunks, {result['n_paginas']} páginas.")
                                st.session_state.pop(f"_reup_open_{doc_id}", None)
                                st.rerun()
                            else:
                                st.error(f"❌ {result['erro']}")
                    st.markdown("</div>", unsafe_allow_html=True)

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
