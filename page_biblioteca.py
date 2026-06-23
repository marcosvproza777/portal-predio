"""Portal do Cliente — Biblioteca Técnica (somente documentos autorizados)."""
import streamlit as st
from auth import current_client_id, require_auth
from sheets import get_documentos_tecnicos
from assistant_mock_data import get_mock_context
from ui import COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE, COLOR_CYAN

_TIPOS_DOC = [
    "Manual técnico", "Datasheet", "Catálogo do fabricante",
    "Especificação de óleo", "Procedimento de manutenção",
    "Instrução de segurança", "FAQ técnico", "Outro",
]

_TIPO_ICON = {
    "Manual técnico":           "📖",
    "Datasheet":                "📋",
    "Catálogo do fabricante":   "🗂️",
    "Especificação de óleo":    "🛢️",
    "Procedimento de manutenção": "🔧",
    "Instrução de segurança":   "⚠️",
    "FAQ técnico":              "❓",
    "Outro":                    "📄",
}


def render() -> None:
    if not require_auth():
        st.stop()

    # SEGURANÇA: client_id sempre da sessão — nunca do front-end
    client_id = current_client_id()

    st.markdown(
        f"<h2 style='color:{COLOR_NAVY};font-size:1.4rem;font-weight:800;margin:0 0 4px;'>"
        f"📚 Biblioteca Técnica</h2>"
        f"<p style='color:{COLOR_MUTED};font-size:0.85rem;margin:0 0 1.5rem;'>"
        f"Consulte manuais e documentos técnicos disponíveis para seus ativos monitorados.</p>",
        unsafe_allow_html=True,
    )

    # ── Busca documentos autorizados ──────────────────────────────────────────
    docs = _carregar_documentos(client_id)

    if not docs:
        st.info(
            "Nenhum documento técnico disponível no momento. "
            "Caso precise de um manual ou documento, abra um chamado técnico."
        )
        if st.button("🔧 Abrir chamado técnico"):
            st.session_state["portal_page"] = "chamados"
            st.rerun()
        return

    # ── Filtros ───────────────────────────────────────────────────────────────
    f1, f2 = st.columns([2, 3])
    with f1:
        filtro_tipo = st.selectbox(
            "Tipo de documento", ["Todos"] + _TIPOS_DOC, key="_bib_ftipo"
        )
    with f2:
        busca = st.text_input(
            "Buscar", placeholder="título, fabricante, modelo, palavra-chave…",
            key="_bib_busca",
        )

    # ── Aplica filtros ────────────────────────────────────────────────────────
    exibir = docs
    if filtro_tipo != "Todos":
        exibir = [d for d in exibir if d.get("tipo_documento") == filtro_tipo]
    if busca.strip():
        txt = busca.strip().lower()
        exibir = [
            d for d in exibir
            if any(
                txt in str(d.get(f, "")).lower()
                for f in ["titulo", "fabricante", "modelo", "resumo", "palavras_chave", "ativo"]
            )
        ]

    if not exibir:
        st.info("Nenhum documento encontrado com os filtros aplicados.")
        return

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.8rem;margin:0 0 1rem;'>"
        f"{len(exibir)} documento(s) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    for doc in exibir:
        _render_doc_card(doc)


def _carregar_documentos(client_id: str) -> list[dict]:
    """
    Tenta carregar do Sheets; cai para mock se sheets estiver vazio ou indisponível.

    SEGURANÇA:
      - client_id da sessão
      - get_documentos_tecnicos() filtra "Apenas equipe Pred.IO" e outros clientes
      - Observacoes_Internas nunca incluídas (removidas na camada sheets)
    """
    try:
        df = get_documentos_tecnicos(client_id=client_id, staff=False)
        if not df.empty:
            return df.to_dict("records")
    except Exception:
        pass

    # Fallback: mock (sem documentos internos — já filtrados no mock)
    ctx = get_mock_context(client_id)
    return ctx.get("documentos", [])


def _render_doc_card(doc: dict) -> None:
    titulo    = str(doc.get("Titulo",         doc.get("titulo",         ""))).strip()
    tipo      = str(doc.get("Tipo_Documento", doc.get("tipo_documento", ""))).strip()
    fabricante = str(doc.get("Fabricante",    doc.get("fabricante",     ""))).strip()
    modelo    = str(doc.get("Modelo",         doc.get("modelo",         ""))).strip()
    ativo     = str(doc.get("Ativo_Id",       doc.get("ativo",          ""))).strip()
    resumo    = str(doc.get("Resumo",         doc.get("resumo",         ""))).strip()
    arq_url   = str(doc.get("Arquivo_Url",    doc.get("arquivo_url",    ""))).strip()
    arq_nome  = str(doc.get("Arquivo_Nome",   doc.get("arquivo_nome",   ""))).strip()

    icon = _TIPO_ICON.get(tipo, "📄")

    meta = []
    if fabricante: meta.append(f"🏭 {fabricante}")
    if modelo:     meta.append(f"⚙️ {modelo}")
    if ativo:      meta.append(f"📍 {ativo}")
    meta_txt = " · ".join(meta)

    col_txt, col_btn = st.columns([8, 2])
    with col_txt:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {COLOR_BLUE};border-radius:10px;"
            f"padding:12px 16px;margin-bottom:6px;'>"
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
            f"<span style='font-size:1.15rem;'>{icon}</span>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;'>{titulo}</span>"
            f"<span style='background:#EFF6FF;color:{COLOR_BLUE};-webkit-text-fill-color:{COLOR_BLUE};"
            f"font-size:0.68rem;font-weight:700;padding:2px 9px;border-radius:10px;"
            f"border:1px solid #BFDBFE;margin-left:4px;'>{tipo}</span>"
            f"</div>"
            + (f"<p style='color:{COLOR_MUTED};font-size:0.75rem;margin:0 0 4px;'>{meta_txt}</p>"
               if meta_txt else "")
            + (f"<p style='color:#475569;font-size:0.8rem;margin:0;'>{resumo}</p>"
               if resumo else "")
            + "</div>",
            unsafe_allow_html=True,
        )

    with col_btn:
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        if arq_url and not arq_url.startswith("/mock/"):
            st.link_button(
                "📂 Abrir",
                arq_url,
                use_container_width=True,
            )
        elif arq_url:
            # URL de mock — não existe arquivo real
            st.button(
                "📂 Abrir",
                key=f"bib_open_{doc.get('id', titulo[:10])}",
                use_container_width=True,
                disabled=True,
                help="Arquivo de demonstração — sem PDF real cadastrado.",
            )
