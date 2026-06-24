"""Chamados Técnicos — portal do cliente (Pred.IO)."""
import streamlit as st
from auth import current_client_id, current_email, current_empresa, current_nome
from sheets import (
    abrir_chamado, abrir_chamado_v2, get_chamados, get_chamados_v2,
    get_chamado_v2_by_id, update_chamado,
    get_mensagens_visiveis_cliente, add_mensagem,
    get_ativos,
)
from ui import (
    page_header, empty_state,
    COLOR_NAVY, COLOR_BLUE, COLOR_CARD, COLOR_BORDER, COLOR_MUTED,
    PRIORIDADES, PRIORIDADE_CFG, STATUS_CFG, badge,
)

_CATEGORIAS = [
    "Dúvida técnica",
    "Alarme",
    "Falha operacional",
    "Manutenção vencida",
    "Manutenção próxima",
    "Relatório técnico",
    "Recomendação por condição",
    "Óleo e lubrificação",
    "Vibração",
    "Termografia",
    "Painel Mypro Touch",
    "Painel Mypro Touch AD",
    "Motor elétrico",
    "Rolamento",
    "Overhaul por condição",
    "Outro",
]

_STATUS_OPTS = [
    "Aberto", "Em análise", "Em andamento",
    "Aguardando cliente", "Concluído", "Cancelado", "Reaberto",
]

_STATUS_ABERTO_BADGE = ("#EF4444", "#FEF2F2", "#FCA5A5", "#991B1B")
_STATUS_ANALY_BADGE  = ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E")
_STATUS_DONE_BADGE   = ("#10B981", "#F0FDF4", "#86EFAC", "#065F46")
_STATUS_CFG2 = {
    "aberto":              ("#EF4444", "#FEF2F2", "#FCA5A5", "#991B1B"),
    "em análise":          ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E"),
    "em analise":          ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E"),
    "em andamento":        ("#3B82F6", "#EFF6FF", "#BFDBFE", "#1E40AF"),
    "aguardando cliente":  ("#8B5CF6", "#F5F3FF", "#C4B5FD", "#4C1D95"),
    "concluído":           ("#10B981", "#F0FDF4", "#86EFAC", "#065F46"),
    "concluido":           ("#10B981", "#F0FDF4", "#86EFAC", "#065F46"),
    "cancelado":           ("#64748B", "#F8FAFC", "#CBD5E1", "#475569"),
    "reaberto":            ("#EF4444", "#FEF2F2", "#FCA5A5", "#991B1B"),
}
_PRIO_CFG2 = {
    "crítica": ("#7C3AED", "#F5F3FF", "#C4B5FD", "#4C1D95"),
    "critica": ("#7C3AED", "#F5F3FF", "#C4B5FD", "#4C1D95"),
    "alta":    ("#EF4444", "#FEF2F2", "#FCA5A5", "#991B1B"),
    "média":   ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E"),
    "media":   ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E"),
    "baixa":   ("#64748B", "#F8FAFC", "#CBD5E1", "#475569"),
}
_STATUS_DEFAULT = ("#64748B", "#F8FAFC", "#CBD5E1", "#475569")
_PRIO_DEFAULT   = ("#64748B", "#F8FAFC", "#CBD5E1", "#475569")

_ORIGEM_ICON = {
    "Portal do Cliente":    "🖥️",
    "Assistente Técnico":   "🤖",
    "Alerta":               "🔔",
    "Relatório Técnico":    "📁",
    "Plano de Manutenção":  "📅",
    "Supervisão Pred.IO":   "⚙️",
}


def render() -> None:
    page_header("🔧 Chamados Técnicos", "Solicite suporte técnico da equipe Pred.IO")

    client_id = current_client_id()  # SEMPRE da sessão
    email     = current_email()

    # Pre-fill proveniente de alertas / relatórios / manutenção / assistente
    pre = _get_prefill()

    tab_lista, tab_novo = st.tabs(["📋 Meus Chamados", "➕ Novo Chamado"])

    with tab_lista:
        _render_lista(client_id)

    with tab_novo:
        _render_form_novo(client_id, email, pre)


# ── Pre-fill helpers ──────────────────────────────────────────────────────────

def _get_prefill() -> dict:
    """Lê session_state para pre-fill quando chamado de outra tela."""
    p = {}
    for k in ("abrir_chamado_titulo", "abrir_chamado_descricao", "abrir_chamado_categoria",
              "abrir_chamado_prioridade", "abrir_chamado_origem",
              "abrir_chamado_ativo_id", "abrir_chamado_report_id",
              "abrir_chamado_alert_id", "abrir_chamado_task_id",
              "abrir_chamado_componente"):
        if k in st.session_state:
            p[k.replace("abrir_chamado_", "")] = st.session_state[k]
    return p


def _clear_prefill() -> None:
    for k in list(st.session_state.keys()):
        if k.startswith("abrir_chamado_"):
            del st.session_state[k]


# ── NOVO CHAMADO ──────────────────────────────────────────────────────────────

def _render_form_novo(client_id: str, email: str, pre: dict) -> None:
    st.caption(
        "⚠️ Em caso de parada de máquina ou emergência, use **Prioridade Crítica** "
        "— resposta em até 1 hora."
    )

    # Banner de origem (se veio de alerta/relatório/manutenção)
    if pre.get("titulo"):
        origem_icon = _ORIGEM_ICON.get(pre.get("origem", ""), "🔗")
        st.markdown(
            f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
            f"border-radius:8px;padding:0.65rem 1rem;margin-bottom:0.75rem;'>"
            f"<p style='font-size:0.8rem;color:#1E40AF;margin:0;'>"
            f"{origem_icon} Chamado pré-preenchido a partir de: "
            f"<strong>{pre.get('origem', 'Pred.IO')}</strong></p></div>",
            unsafe_allow_html=True,
        )

    # Seleção de ativo
    ativo_opts = ["— Nenhum / não sei —"]
    ativo_ids  = [""]
    try:
        df_at = get_ativos(client_id)
        if not df_at.empty and "Id" in df_at.columns:
            for _, ar in df_at.iterrows():
                tag = str(ar.get("Tag", "") or ar.get("Nome", "")).strip()
                aid = str(ar.get("Id", "")).strip()
                if tag and aid:
                    ativo_opts.append(f"{tag} ({aid})")
                    ativo_ids.append(aid)
    except Exception:
        pass

    pre_ativo_id = pre.get("ativo_id", "")
    pre_ativo_idx = 0
    if pre_ativo_id and pre_ativo_id in ativo_ids:
        pre_ativo_idx = ativo_ids.index(pre_ativo_id)

    col1, col2 = st.columns(2)
    with col1:
        at_sel  = st.selectbox("Equipamento / Ativo", ativo_opts, index=pre_ativo_idx,
                               key="_ch_at_sel")
        at_id   = ativo_ids[ativo_opts.index(at_sel)] if at_sel in ativo_opts else ""
        comp    = st.text_input("Componente (opcional)",
                                value=pre.get("componente", ""),
                                placeholder="ex: Bomba de óleo, motor, filtro")
    with col2:
        pre_cat_idx = _CATEGORIAS.index(pre.get("categoria", "Dúvida técnica")) \
                      if pre.get("categoria") in _CATEGORIAS else 0
        categoria = st.selectbox("Categoria *", _CATEGORIAS, index=pre_cat_idx,
                                 key="_ch_cat_sel")

        pre_prio = pre.get("prioridade", "Média")
        if pre_prio not in PRIORIDADES:
            pre_prio = "Média"
        prioridade = st.selectbox("Prioridade sugerida", PRIORIDADES,
                                  index=PRIORIDADES.index(pre_prio),
                                  key="_ch_prio_sel")

    titulo = st.text_input(
        "Título do chamado *",
        value=pre.get("titulo", ""),
        placeholder="Ex: Vibração excessiva na unidade compressora",
        key="_ch_titulo",
    )
    descricao = st.text_area(
        "Descrição detalhada *",
        value=pre.get("descricao", ""),
        placeholder="Descreva o problema, sintomas observados e histórico recente…",
        height=130, key="_ch_desc",
    )

    # Contexto vinculado (read-only, para transparência)
    report_id = pre.get("report_id", "")
    alert_id  = pre.get("alert_id", "")
    task_id   = pre.get("task_id", "")
    origem    = pre.get("origem", "Portal do Cliente")

    vinculos = []
    if report_id: vinculos.append(f"📁 Relatório: {report_id}")
    if alert_id:  vinculos.append(f"🔔 Alerta: {alert_id}")
    if task_id:   vinculos.append(f"📅 Tarefa: {task_id}")
    if vinculos:
        st.markdown(
            f"<p style='font-size:0.78rem;color:{COLOR_MUTED};margin:0.25rem 0 0.75rem;'>"
            f"🔗 Vínculos: {' · '.join(vinculos)}</p>",
            unsafe_allow_html=True,
        )

    col_sub, col_can = st.columns([3, 1])
    with col_sub:
        submitted = st.button("📨 Abrir Chamado", type="primary",
                              use_container_width=True, key="_ch_submit")
    with col_can:
        if pre.get("titulo"):
            if st.button("✕ Cancelar", use_container_width=True, key="_ch_cancel"):
                _clear_prefill()
                st.rerun()

    if submitted:
        if not titulo.strip() or not descricao.strip():
            st.warning("Preencha pelo menos o título e a descrição.")
            return

        chamado_id = abrir_chamado_v2({
            "client_id":           client_id,
            "usuario_id":          email,
            "empresa":             current_empresa(),
            "email":               email,
            "ativo_id":            at_id,
            "componente_id":       comp.strip(),
            "report_id":           report_id,
            "maintenance_task_id": task_id,
            "alert_id":            alert_id,
            "titulo":              titulo.strip(),
            "descricao":           descricao.strip(),
            "categoria":           categoria,
            "prioridade":          prioridade,
            "origem":              origem,
            "planta":              "",
            "equipamento":         at_sel if at_id else "",
        })

        if chamado_id:
            st.success(
                f"✅ Chamado **#{chamado_id}** aberto! "
                "Nossa equipe entrará em contato em breve."
            )
            _clear_prefill()
        else:
            # Fallback para função legada
            ok = abrir_chamado(
                client_id  = client_id,
                empresa    = current_empresa(),
                email      = email,
                titulo     = titulo.strip(),
                descricao  = descricao.strip(),
                planta     = "",
                equipamento= at_sel if at_id else "",
                prioridade = prioridade,
            )
            if ok:
                st.success("✅ Chamado aberto com sucesso!")
                _clear_prefill()
            else:
                st.error("Erro ao abrir o chamado. Tente novamente.")


# ── LISTA DE CHAMADOS ─────────────────────────────────────────────────────────

def _render_lista(client_id: str) -> None:
    # Tenta V2 primeiro
    df = get_chamados_v2(client_id=client_id)
    if df.empty:
        df = get_chamados(client_id)

    if df.empty:
        empty_state("Nenhum chamado encontrado.")
        st.markdown(
            f"<p style='text-align:center;color:{COLOR_MUTED};font-size:0.85rem;'>"
            f"Use a aba <b>➕ Novo Chamado</b> para abrir uma solicitação.</p>",
            unsafe_allow_html=True,
        )
        return

    # Filtros simples
    c1, c2 = st.columns(2)
    with c1:
        f_status = st.selectbox("Filtrar por status",
                                ["Todos"] + _STATUS_OPTS, key="_ch_fst")
    with c2:
        f_prio = st.selectbox("Filtrar por prioridade",
                              ["Todas", "Crítica", "Alta", "Média", "Baixa"],
                              key="_ch_fpr")

    if f_status != "Todos":
        df = df[df["Status"].str.strip() == f_status]
    if f_prio != "Todas":
        df = df[df["Prioridade"].str.strip() == f_prio]

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.85rem;margin:0.25rem 0 0.75rem;'>"
        f"{len(df)} chamado(s)</p>",
        unsafe_allow_html=True,
    )

    for _, row in df.iterrows():
        _render_card_cliente(row, client_id)


def _render_card_cliente(row, client_id: str) -> None:
    chamado_id = str(row.get("Id", "")).strip()
    titulo     = str(row.get("Titulo",      "")).strip() or "Sem título"
    descricao  = str(row.get("Descricao",   "")).strip()
    prioridade = str(row.get("Prioridade",  "Média")).strip()
    status     = str(row.get("Status",      "Aberto")).strip()
    categoria  = str(row.get("Categoria",   "")).strip()
    origem     = str(row.get("Origem",      "")).strip()
    ativo_id   = str(row.get("Ativo_Id",    "")).strip()
    data_ab    = str(row.get("Aberto_Em",
                    row.get("Data_Abertura", ""))).strip()[:16]

    sc, sb, sbo, st_ = _STATUS_CFG2.get(status.lower(), _STATUS_DEFAULT)
    pc, pb, pbo, pt  = _PRIO_CFG2.get(prioridade.lower(), _PRIO_DEFAULT)

    meta = []
    if data_ab:   meta.append(f"📅 {data_ab}")
    if ativo_id:  meta.append(f"⚙️ {ativo_id}")
    if categoria: meta.append(f"🏷️ {categoria}")
    if origem:    meta.append(f"{_ORIGEM_ICON.get(origem,'🔗')} {origem}")
    if chamado_id: meta.append(f"#{chamado_id}")

    meta_html = "  ·  ".join(
        f"<span style='color:{COLOR_MUTED};font-size:0.77rem;'>{m}</span>" for m in meta
    )

    label = f"{'🔴' if prioridade=='Crítica' else '🟡' if prioridade=='Alta' else '🔵'} {titulo}"
    with st.expander(label, expanded=False):
        st.markdown(
            f"<div style='display:flex;gap:7px;flex-wrap:wrap;margin-bottom:7px;'>"
            f"<span style='background:{sb};color:{st_};-webkit-text-fill-color:{st_};"
            f"border:1px solid {sbo};font-size:0.68rem;font-weight:700;"
            f"padding:2px 10px;border-radius:10px;'>{status}</span>"
            f"<span style='background:{pb};color:{pt};-webkit-text-fill-color:{pt};"
            f"border:1px solid {pbo};font-size:0.68rem;font-weight:700;"
            f"padding:2px 10px;border-radius:10px;'>{prioridade}</span>"
            f"</div>"
            f"<div style='margin-bottom:7px;'>{meta_html}</div>"
            + (f"<p style='color:#475569;font-size:0.86rem;background:#F8FAFC;"
               f"border-radius:8px;padding:9px 12px;margin:0 0 8px;line-height:1.5;'>"
               f"{descricao[:300]}{'…' if len(descricao)>300 else ''}</p>"
               if descricao else ""),
            unsafe_allow_html=True,
        )

        if chamado_id:
            _render_thread_cliente(chamado_id, client_id, current_email())


def _render_thread_cliente(chamado_id: str, client_id: str, email: str) -> None:
    # Passa client_id para validar ownership — defesa em profundidade
    msgs = get_mensagens_visiveis_cliente(chamado_id, client_id=client_id)
    # Audit log: registro de acesso a thread de chamado
    try:
        from security import log_acesso_permitido
        log_acesso_permitido("visualizar_chamado", "chamado", chamado_id, client_id)
    except Exception:
        pass

    if not msgs.empty:
        st.markdown(
            f"<p style='color:{COLOR_NAVY};font-size:0.78rem;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:.06em;margin:8px 0 6px;'>"
            "Histórico do chamado</p>",
            unsafe_allow_html=True,
        )
        for _, m in msgs.iterrows():
            autor_tipo = str(m.get("Autor_Tipo",   "")).strip()
            autor      = str(m.get("Autor",        "")).strip()
            mensagem   = str(m.get("Mensagem",     "")).strip()
            tipo       = str(m.get("Tipo_Mensagem","")).strip()
            data       = str(m.get("Data",         "")).strip()[:16]

            if tipo in ("alteracao_status", "alteracao_prioridade",
                        "atribuicao_responsavel", "encerramento", "reabertura"):
                st.markdown(
                    f"<div style='text-align:center;margin:5px 0;'>"
                    f"<span style='background:#F1F5F9;border:1px solid #E2E8F0;"
                    f"border-radius:20px;padding:3px 12px;font-size:0.72rem;color:#64748B;'>"
                    f"🔄 {mensagem} · {data}</span></div>",
                    unsafe_allow_html=True,
                )
            elif autor_tipo in ("funcionario", "predio") or tipo == "resposta_predio":
                st.markdown(
                    f"<div style='display:flex;justify-content:flex-end;margin:5px 0;'>"
                    f"<div style='max-width:80%;background:#0F1F3D;"
                    f"border-radius:12px 12px 2px 12px;padding:9px 13px;'>"
                    f"<div style='font-size:0.7rem;color:#93C5FD;font-weight:700;"
                    f"margin-bottom:3px;'>⚙️ Equipe Pred.IO</div>"
                    f"<p style='color:#E2E8F0;font-size:0.86rem;margin:0;'>{mensagem}</p>"
                    f"<div style='font-size:0.68rem;color:#64748B;margin-top:4px;'>{data}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='display:flex;justify-content:flex-start;margin:5px 0;'>"
                    f"<div style='max-width:80%;background:#EFF6FF;"
                    f"border:1px solid #BFDBFE;border-radius:12px 12px 12px 2px;"
                    f"padding:9px 13px;'>"
                    f"<div style='font-size:0.7rem;color:#2563EB;font-weight:700;"
                    f"margin-bottom:3px;'>👤 Você</div>"
                    f"<p style='color:#1e293b;font-size:0.86rem;margin:0;'>{mensagem}</p>"
                    f"<div style='font-size:0.68rem;color:#94a3b8;margin-top:4px;'>{data}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

    with st.form(f"reply_ch_{chamado_id}", clear_on_submit=True):
        resposta = st.text_area(
            "Complementar ou responder",
            placeholder="Adicione informações, atualizações ou dúvidas…",
            height=75, label_visibility="collapsed",
        )
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            enviar = st.form_submit_button("📨 Enviar", use_container_width=True)
        with col_info:
            st.markdown(
                "<p style='color:#94a3b8;font-size:0.73rem;padding-top:9px;'>"
                "Visível para a equipe Pred.IO</p>",
                unsafe_allow_html=True,
            )
    if enviar and resposta.strip():
        ok = add_mensagem(
            chamado_id    = chamado_id,
            autor         = email,
            autor_tipo    = "cliente",
            mensagem      = resposta.strip(),
            visivel_cliente = True,
            tipo_mensagem = "mensagem_cliente",
        )
        if ok:
            st.success("Mensagem enviada!")
            st.rerun()
        else:
            st.error("Erro ao enviar. Tente novamente.")
