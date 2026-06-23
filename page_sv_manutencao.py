"""Supervisão — Planos de Manutenção (gestão interna)."""
import streamlit as st
from auth import require_staff
from page_ativos import (
    _PLANO_MOCK_COMPRESSOR, _HORIMETRO_ATUAL_MOCK,
    _pm_calc_status, _pm_scfg, _pm_pcolor, _norm,
    _render_tarefa_card, _render_plano_manutencao,
)
from ui import (
    sv_page_header,
    COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE,
)

# ── Constantes do formulário ──────────────────────────────────────────────────
_CATEGORIAS = [
    "Análise de óleo", "Filtros", "Lubrificação", "Alinhamento",
    "Inspeção", "Termografia", "Vibração", "Overhaul", "Rolamentos", "Outros",
]
_TIPOS = [
    "Preventiva por horímetro", "Preventiva por calendário",
    "Preditiva por condição", "Corretiva planejada", "Inspeção técnica",
]
_LAUDOS = ["vibração", "óleo", "termografia", "inspeção"]
_STATUS_OPTS = [
    "Em dia", "Próximo do vencimento", "Vencido",
    "Depende de análise preditiva", "Concluído",
]
_PRIO_OPTS = ["Baixa", "Média", "Alta", "Crítica"]

# ── Mock de ativos com plano ──────────────────────────────────────────────────
_MOCK_ATIVOS_PLANO = [
    {
        "id":          "AT-2026-001",
        "nome":        "Unidade Compressora Parafuso 200 VLD",
        "empresa":     "Coca-Cola",
        "planta":      "Sala de Compressores",
        "tag":         "CCP-001",
        "horimetro":   _HORIMETRO_ATUAL_MOCK,
        "plano":       _PLANO_MOCK_COMPRESSOR,
    },
]


def _get_h(ativo: dict) -> int:
    """Retorna horímetro atual do ativo — usa session_state se já editado."""
    ativo_id = ativo.get("id", ativo.get("nome", ""))
    return st.session_state.get(f"h_sv_{ativo_id}", ativo.get("horimetro", 0))


def _ativo_com_h(ativo: dict) -> dict:
    """Retorna cópia do ativo com horimetro_atual injetado em todas as tarefas."""
    h = _get_h(ativo)
    plano_com_h = [{**t, "horimetro_atual": h} for t in ativo.get("plano", [])]
    return {**ativo, "horimetro": h, "plano": plano_com_h}


def render() -> None:
    require_staff()
    sv_page_header(
        "📅 Planos de Manutenção",
        "Cadastre e gerencie planos preventivos e preditivos por cliente e ativo.",
    )

    tab_plano, tab_form, tab_venc = st.tabs([
        "📋 Plano Atual",
        "➕ Cadastrar Tarefa",
        "⚠️ Tarefas Vencidas / Próximas",
    ])

    with tab_plano:
        _render_tab_plano()

    with tab_form:
        _render_tab_form()

    with tab_venc:
        _render_tab_urgentes()


# ─────────────────────────────────────────────────────────────────────────────
def _render_tab_plano() -> None:
    # Usa horímetros editados (session_state) para o resumo de status
    _render_resumo([_ativo_com_h(a) for a in _MOCK_ATIVOS_PLANO])
    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    for ativo in _MOCK_ATIVOS_PLANO:
        _render_ativo_section(ativo)


def _render_resumo(ativos: list) -> None:
    all_t = [t for a in ativos for t in a.get("plano", [])]
    statuses = [_pm_calc_status(t) for t in all_t]
    total   = len(all_t)
    em_dia  = sum(1 for s in statuses if _norm(s) == "em dia")
    proximo = sum(1 for s in statuses if _norm(s) == "proximo do vencimento")
    vencido = sum(1 for s in statuses if _norm(s) == "vencido")
    aguarda = sum(1 for s in statuses if "analise" in _norm(s))

    for col, label, valor, cor in zip(
        st.columns(4),
        ["Total de Tarefas", "Em Dia", "Próximo Vencimento", "Aguarda Análise"],
        [total, em_dia, proximo, aguarda],
        [COLOR_NAVY, "#10B981", "#F59E0B", "#38BDF8"],
    ):
        with col:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-top:3px solid {cor};border-radius:10px;padding:0.9rem 1rem;'>"
                f"<p style='font-size:0.68rem;color:{COLOR_MUTED};text-transform:uppercase;"
                f"letter-spacing:.06em;margin:0 0 4px;'>{label}</p>"
                f"<p style='font-size:1.6rem;font-weight:900;color:{cor};"
                f"-webkit-text-fill-color:{cor};margin:0;'>{valor}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _render_ativo_section(ativo: dict) -> None:
    ativo_id = ativo.get("id", ativo.get("nome", ""))
    nome     = ativo.get("nome", "Equipamento")
    empresa  = ativo.get("empresa", "")
    planta   = ativo.get("planta", "")
    tag      = ativo.get("tag", "")
    plano    = ativo.get("plano", [])
    h_default = ativo.get("horimetro", 0)

    with st.expander(f"⚙️  {nome}  —  {empresa}", expanded=True):
        meta = []
        if tag:     meta.append(f"🏷 {tag}")
        if empresa: meta.append(f"🏢 {empresa}")
        if planta:  meta.append(f"🏭 {planta}")
        if meta:
            st.markdown(
                f"<p style='font-size:0.78rem;color:{COLOR_MUTED};margin:0 0 0.5rem;'>"
                f"{'   ·   '.join(meta)}</p>",
                unsafe_allow_html=True,
            )

        col_h, _ = st.columns([2, 5])
        with col_h:
            h = st.number_input(
                "⏱ Horímetro atual (h)",
                min_value=0,
                value=h_default,
                step=10,
                key=f"h_sv_{ativo_id}",
                help="Altere para recalcular automaticamente os status do plano de manutenção.",
            )

        # Injeta horímetro atualizado em todas as tarefas do plano
        plano_com_h = [{**t, "horimetro_atual": h} for t in plano]

        horimetro  = [t for t in plano_com_h if t.get("tipo") == "horimetro"]
        calendario = [t for t in plano_com_h if t.get("tipo") == "calendario"]
        condicao   = [t for t in plano_com_h if t.get("tipo") == "condicao"]

        labels = []
        if horimetro:  labels.append(f"⏱ Horímetro ({len(horimetro)})")
        if calendario: labels.append(f"📆 Calendário ({len(calendario)})")
        if condicao:   labels.append(f"🔍 Condição ({len(condicao)})")
        labels.append("📋 Todas")

        tabs = st.tabs(labels)
        idx = 0

        if horimetro:
            with tabs[idx]:
                for t in sorted(horimetro, key=lambda x: (
                        x.get("vencimento_horas", 9999) - x.get("horimetro_atual", 0))):
                    _render_sv_card(t)
            idx += 1

        if calendario:
            with tabs[idx]:
                for t in calendario:
                    _render_sv_card(t)
            idx += 1

        if condicao:
            with tabs[idx]:
                st.markdown(
                    f"<p style='font-size:0.75rem;color:#3B82F6;background:#EFF6FF;"
                    f"border-radius:8px;padding:6px 10px;margin-bottom:8px;'>"
                    f"🔍 Estas intervenções dependem de laudos técnicos — não são automáticas "
                    f"por horímetro.</p>",
                    unsafe_allow_html=True,
                )
                for t in condicao:
                    _render_sv_card(t)
            idx += 1

        with tabs[idx]:
            _render_plano_manutencao(plano_com_h)


def _render_sv_card(t: dict, prefix: str = "sv") -> None:
    tid  = t.get("id", t.get("nome", ""))
    nome = t.get("nome", "")
    tipo = t.get("tipo", "")

    col_info, col_btn = st.columns([7, 2])
    with col_info:
        _render_tarefa_card(t)
    with col_btn:
        st.markdown("<div style='height:0.35rem'></div>", unsafe_allow_html=True)
        if st.button("✅ Concluir", key=f"{prefix}_ok_{tid}", use_container_width=True, type="primary"):
            st.toast(f"'{nome}' marcada como concluída.", icon="✅")
        if tipo in ("horimetro", "calendario"):
            if st.button("⏩ Adiar", key=f"{prefix}_adiar_{tid}", use_container_width=True):
                st.toast(f"'{nome}' adiada. Atualize o vencimento manualmente.", icon="⏩")
    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
def _render_tab_form() -> None:
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;margin:0 0 1rem;'>"
        f"➕ Nova Tarefa de Manutenção</p>",
        unsafe_allow_html=True,
    )

    with st.form("form_nova_tarefa", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            cliente_id  = st.text_input("Cliente ID *", placeholder="ex: coca-cola")
            ativo_id    = st.text_input("Ativo ID *",   placeholder="ex: AT-2026-001")
            comp_id     = st.text_input("Componente ID (opcional)")
            nome_tarefa = st.text_input("Nome da Tarefa *", placeholder="ex: Análise de óleo")
        with c2:
            categoria  = st.selectbox("Categoria *", _CATEGORIAS)
            tipo_sel   = st.selectbox("Tipo *", _TIPOS)
            prioridade = st.selectbox("Prioridade *", _PRIO_OPTS)
            status_sel = st.selectbox("Status inicial", _STATUS_OPTS)

        st.markdown("---")
        c3, c4, c5 = st.columns(3)
        with c3:
            period_horas = st.number_input("Periodicidade (horas)", min_value=0, value=0, step=500)
            prox_horas   = st.number_input("Próx. execução (horímetro)", min_value=0, value=0, step=100)
            h_base       = st.number_input("Horímetro base (h)", min_value=0, value=0, step=100)
        with c4:
            period_dias  = st.number_input("Periodicidade (dias)", min_value=0, value=0, step=30)
            prox_data    = st.date_input("Próx. execução (data)", value=None)
        with c5:
            dep_laudo    = st.radio("Depende de laudo técnico?", ["Não", "Sim"], horizontal=True)
            laudos_base  = st.multiselect("Tipos de laudo base", _LAUDOS,
                                          disabled=(dep_laudo == "Não"))

        descricao = st.text_area("Descrição da tarefa", height=90,
                                 placeholder="Descreva o procedimento e critérios da tarefa...")
        obs_int   = st.text_area("Observações internas (não visíveis ao cliente)", height=60)

        submetido = st.form_submit_button("💾 Cadastrar Tarefa", use_container_width=True,
                                          type="primary")

    if submetido:
        erros = []
        if not cliente_id.strip():  erros.append("Cliente ID é obrigatório.")
        if not ativo_id.strip():    erros.append("Ativo ID é obrigatório.")
        if not nome_tarefa.strip(): erros.append("Nome da Tarefa é obrigatório.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            st.success(
                f"✅ Tarefa **{nome_tarefa}** cadastrada com sucesso para o ativo **{ativo_id}**. "
                f"(Integração com Google Sheets em breve — dados mockados por enquanto.)"
            )
            st.info(
                "📋 Campos recebidos: cliente_id, ativo_id, nome, categoria, tipo, "
                "prioridade, status, periodicidade, próx. execução, depende_laudo, obs_internas."
            )


# ─────────────────────────────────────────────────────────────────────────────
def _render_tab_urgentes() -> None:
    all_tarefas = [
        (a, t, _pm_calc_status(t))
        for a in [_ativo_com_h(a) for a in _MOCK_ATIVOS_PLANO]
        for t in a.get("plano", [])
        if t.get("tipo") != "condicao"
    ]

    vencidas = [(a, t, s) for a, t, s in all_tarefas if _norm(s) == "vencido"]
    proximas = [(a, t, s) for a, t, s in all_tarefas if _norm(s) == "proximo do vencimento"]

    if not vencidas and not proximas:
        st.success("✅ Nenhuma tarefa vencida ou próxima do vencimento no momento.")
        return

    if vencidas:
        st.markdown(
            f"<p style='font-weight:700;color:#991B1B;font-size:0.9rem;margin:0 0 0.5rem;'>"
            f"🔴 Tarefas Vencidas ({len(vencidas)})</p>",
            unsafe_allow_html=True,
        )
        for a, t, s in vencidas:
            st.markdown(
                f"<span style='font-size:0.72rem;color:{COLOR_MUTED};'>"
                f"⚙️ {a['nome']}</span>",
                unsafe_allow_html=True,
            )
            _render_sv_card(t, prefix="sv_venc")

    if proximas:
        st.markdown(
            f"<p style='font-weight:700;color:#92400E;font-size:0.9rem;margin:0.75rem 0 0.5rem;'>"
            f"🟡 Próximas do Vencimento ({len(proximas)})</p>",
            unsafe_allow_html=True,
        )
        for a, t, s in proximas:
            st.markdown(
                f"<span style='font-size:0.72rem;color:{COLOR_MUTED};'>"
                f"⚙️ {a['nome']}</span>",
                unsafe_allow_html=True,
            )
            _render_sv_card(t, prefix="sv_prox")
