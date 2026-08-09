"""Supervisão — Planos de Manutenção Inteligente (gestão interna Pred.IO)."""
import datetime
import streamlit as st
from auth import require_staff, current_nome

from page_ativos import (
    _PLANO_MOCK_COMPRESSOR, _HORIMETRO_ATUAL_MOCK,
    _pm_calc_status, _pm_scfg, _pm_pcolor, _norm,
    _render_tarefa_card, _render_plano_manutencao,
)
from ui import (
    sv_page_header, status_badge, status_color, sv_metric_card, empty_state, app_alert,
    COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE,
)
from sheets import (
    get_all_clientes, get_ativos,
    get_horimetro, save_horimetro,
    get_maintenance_plans, add_maintenance_plan, update_maintenance_plan,
    get_maintenance_tasks, get_maintenance_task_by_id,
    add_maintenance_task, update_maintenance_task, delete_maintenance_task,
    get_maintenance_executions,
    complete_maintenance_task,
    generate_maintenance_alerts,
    calc_task_status,
    update_maintenance_task_gut,
)
from gut import calculate_gut, GUT_DISCLAIMER

# ── Constantes ────────────────────────────────────────────────────────────────
_TIPOS_MAN = ["Calendário", "Horímetro", "Condição"]

_CATEGORIAS = [
    "Operação", "Inspeção", "Segurança e controle", "Instrumentação e motor",
    "Lubrificação", "Filtragem", "Alinhamento", "Preditiva",
    "Inspeção geral", "Intervenção pesada", "Motor / Rolamento", "Outros",
]

_PRIORIDADES = ["Baixa", "Média", "Alta", "Crítica"]

_ORIGENS = [
    "Manual técnico", "Pred.IO", "Relatório técnico",
    "Análise de óleo", "Análise de vibração", "Termografia",
    "Chamado técnico", "Cadastro manual",
]

_NOTE_CONDICAO = (
    "⚠️ Intervenções pesadas (overhaul, desmontagem, troca de rolamento, kit revisão) "
    "não devem ser automáticas por horímetro. "
    "20.000h é referência técnica — a decisão depende da saúde real da máquina, "
    "análise de vibração, análise de óleo, termografia e avaliação técnica Pred.IO."
)



def _do_save_horimetro(ativo_id: str) -> None:
    key    = f"h_sv_{ativo_id}"
    h_novo = st.session_state.get(key, 0)
    ok     = save_horimetro(ativo_id, h_novo)
    if ok:
        st.toast(f"Horímetro salvo: {h_novo:,} h", icon="✅")


def _get_h(ativo_id: str, default: int = 0) -> int:
    key = f"h_sv_{ativo_id}"
    if key in st.session_state:
        return st.session_state[key]
    h = get_horimetro(ativo_id)
    return h if h is not None else default


# ── Entry point ───────────────────────────────────────────────────────────────

def render() -> None:
    require_staff()
    sv_page_header(
        "📅 Plano de Manutenção Inteligente",
        "Gerencie planos, tarefas, execuções e alertas de manutenção por cliente e ativo.",
    )

    tab_planos, tab_tarefas, tab_exec, tab_alertas, tab_mock = st.tabs([
        "📋 Planos",
        "➕ Tarefas",
        "✅ Executar",
        "⚠️ Alertas",
        "🔍 Modelo MYCOM",
    ])

    with tab_planos:
        _render_tab_planos()
    with tab_tarefas:
        _render_tab_tarefas()
    with tab_exec:
        _render_tab_executar()
    with tab_alertas:
        _render_tab_alertas()
    with tab_mock:
        _render_tab_mock()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PLANOS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_tab_planos() -> None:
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;margin:0 0 0.75rem;'>"
        f"📋 Planos de Manutenção Cadastrados</p>",
        unsafe_allow_html=True,
    )

    # ── Formulário de novo plano ──────────────────────────────────────────────
    with st.expander("➕ Criar novo plano", expanded=False):
        _render_form_novo_plano()

    # ── Lista de planos ───────────────────────────────────────────────────────
    try:
        df_cli = get_all_clientes()
        cli_opts = ["Todos os clientes"] + [
            str(r.get("Empresa", "")).strip()
            for _, r in df_cli.iterrows()
            if str(r.get("Empresa", "")).strip()
        ]
    except Exception:
        cli_opts = ["Todos os clientes"]

    c1, c2 = st.columns(2)
    with c1:
        cli_sel = st.selectbox("Filtrar por cliente", cli_opts, key="_svman_pl_cli")
    with c2:
        st_opts = ["Todos", "Ativo", "Pausado", "Arquivado"]
        st_sel  = st.selectbox("Status do plano", st_opts, key="_svman_pl_st")

    cid_filter = ""
    if cli_sel != "Todos os clientes":
        try:
            cid_filter = str(
                df_cli[df_cli["Empresa"].str.strip() == cli_sel]
                .iloc[0].get("Client_Id", cli_sel)
            ).strip()
        except Exception:
            cid_filter = cli_sel

    df_plans = get_maintenance_plans(
        client_id = cid_filter,
        status    = "" if st_sel == "Todos" else st_sel,
    )

    if df_plans.empty:
        empty_state("Nenhum plano cadastrado. Use '➕ Criar novo plano' acima.", icon="📅")
        return

    for _, row in df_plans.iterrows():
        _render_plan_card(row)


def _render_form_novo_plano() -> None:
    try:
        df_cli = get_all_clientes()
        cli_rows = [
            (str(r.get("Empresa", "")).strip(),
             str(r.get("Client_Id", r.get("Cliente_Id", ""))).strip())
            for _, r in df_cli.iterrows()
            if str(r.get("Empresa", "")).strip()
        ]
    except Exception:
        cli_rows = []

    with st.form("form_novo_plano", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            if cli_rows:
                opts   = [f"{e} ({c})" for e, c in cli_rows]
                ids    = [c for _, c in cli_rows]
                sel    = st.selectbox("Cliente *", opts, key="_svman_plnov_cli")
                sel_id = ids[opts.index(sel)] if sel in opts else ""
            else:
                sel_id = st.text_input("Cliente ID *", key="_svman_plnov_cid")
        with c2:
            ativo_id_in = st.text_input("Ativo ID (opcional)", key="_svman_plnov_aid")

        nome_plan = st.text_input("Nome do Plano *", placeholder="ex: Plano Compressor 200 VLD")
        desc_plan = st.text_area("Descrição", height=70)
        sub       = st.form_submit_button("💾 Criar Plano", type="primary", use_container_width=True)

    if sub:
        if not sel_id or not nome_plan.strip():
            st.error("Preencha cliente e nome do plano.")
        else:
            plan_id = add_maintenance_plan({
                "cliente_id": sel_id,
                "ativo_id":   ativo_id_in.strip(),
                "nome":       nome_plan.strip(),
                "descricao":  desc_plan.strip(),
                "status":     "Ativo",
            }, created_by=current_nome())
            if plan_id:
                st.success(f"✅ Plano criado! ID: {plan_id}")
                from sheets import load_sheet as _ls; _ls.clear()
            else:
                st.error("Erro ao criar plano.")


def _render_plan_card(row) -> None:
    plan_id   = str(row.get("Id", "")).strip()
    nome      = str(row.get("Nome", "")).strip() or "Sem nome"
    cli_id    = str(row.get("Cliente_Id", "")).strip()
    ativo_id  = str(row.get("Ativo_Id", "")).strip()
    status    = str(row.get("Status", "Ativo")).strip()
    descricao = str(row.get("Descricao", "")).strip()

    st_color = "#10B981" if status == "Ativo" else "#F59E0B" if status == "Pausado" else "#94A3B8"

    # Count tasks
    df_tasks = get_maintenance_tasks(client_id=cli_id, plan_id=plan_id)
    n_tasks  = len(df_tasks) if not df_tasks.empty else 0

    col_info, col_btns = st.columns([7, 2])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {st_color};border-radius:10px;padding:0.8rem 1rem;"
            f"margin-bottom:4px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};'>{nome}</span>"
            f"<span style='background:{st_color};color:#fff;-webkit-text-fill-color:#fff;"
            f"font-size:0.68rem;font-weight:700;padding:2px 10px;border-radius:10px;'>{status}</span>"
            f"</div>"
            f"<p style='color:{COLOR_MUTED};font-size:0.78rem;margin:3px 0 0;'>"
            f"👤 {cli_id}" + (f"  ·  ⚙️ {ativo_id}" if ativo_id else "")
            + f"  ·  📋 {n_tasks} tarefa(s)</p>"
            + (f"<p style='color:{COLOR_MUTED};font-size:0.77rem;margin:3px 0 0;'>{descricao[:100]}…</p>"
               if descricao else "")
            + "</div>",
            unsafe_allow_html=True,
        )
    with col_btns:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if status == "Ativo":
            if st.button("⏸ Pausar", key=f"_svman_pause_{plan_id}", use_container_width=True):
                update_maintenance_plan(plan_id, {"Status": "Pausado"})
                from sheets import load_sheet as _ls; _ls.clear()
                st.rerun()
        else:
            if st.button("▶ Ativar", key=f"_svman_ativ_{plan_id}", use_container_width=True):
                update_maintenance_plan(plan_id, {"Status": "Ativo"})
                from sheets import load_sheet as _ls; _ls.clear()
                st.rerun()

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TAREFAS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_tab_tarefas() -> None:
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;margin:0 0 0.75rem;'>"
        f"➕ Cadastrar / Gerenciar Tarefas</p>",
        unsafe_allow_html=True,
    )

    # Nota sobre condição
    st.markdown(
        f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
        f"border-radius:8px;padding:0.6rem 1rem;margin-bottom:1rem;'>"
        f"<p style='font-size:0.78rem;color:#1E40AF;margin:0;'>{_NOTE_CONDICAO}</p></div>",
        unsafe_allow_html=True,
    )

    col_form, col_list = st.columns([1, 1])

    with col_form:
        _render_form_nova_tarefa()

    with col_list:
        _render_lista_tarefas_sv()


def _render_form_nova_tarefa() -> None:
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;margin:0 0 0.5rem;'>Nova Tarefa</p>",
        unsafe_allow_html=True,
    )

    try:
        df_cli = get_all_clientes()
        cli_rows = [
            (str(r.get("Empresa", "")).strip(),
             str(r.get("Client_Id", r.get("Cliente_Id", ""))).strip())
            for _, r in df_cli.iterrows()
            if str(r.get("Empresa", "")).strip()
        ]
    except Exception:
        cli_rows = []

    # Selects context
    if cli_rows:
        opts   = [f"{e} ({c})" for e, c in cli_rows]
        ids    = [c for _, c in cli_rows]
        sel    = st.selectbox("Cliente *", opts, key="_svman_tk_cli")
        sel_cid= ids[opts.index(sel)] if sel in opts else ""
    else:
        sel_cid = st.text_input("Cliente ID *", key="_svman_tk_cid")

    # Load ativos para o cliente
    ativo_opts = ["— Nenhum —"]
    ativo_ids  = [""]
    if sel_cid:
        try:
            df_at = get_ativos(sel_cid)
            if not df_at.empty and "Id" in df_at.columns:
                for _, ar in df_at.iterrows():
                    tag = str(ar.get("Tag", "") or ar.get("Nome", "")).strip()
                    aid = str(ar.get("Id", "")).strip()
                    if tag and aid:
                        ativo_opts.append(f"{tag} ({aid})")
                        ativo_ids.append(aid)
        except Exception:
            pass

    at_sel = st.selectbox("Ativo", ativo_opts, key="_svman_tk_at")
    at_id  = ativo_ids[ativo_opts.index(at_sel)] if at_sel in ativo_opts else ""

    # Load planos
    plan_opts = ["— Sem plano —"]
    plan_ids  = [""]
    if sel_cid:
        df_pl = get_maintenance_plans(client_id=sel_cid, status="Ativo")
        if not df_pl.empty:
            for _, pr in df_pl.iterrows():
                pid = str(pr.get("Id", "")).strip()
                pnm = str(pr.get("Nome", "")).strip()
                if pid:
                    plan_opts.append(f"{pnm} ({pid})")
                    plan_ids.append(pid)

    pl_sel = st.selectbox("Plano", plan_opts, key="_svman_tk_pl")
    pl_id  = plan_ids[plan_opts.index(pl_sel)] if pl_sel in plan_opts else ""

    nome_tk  = st.text_input("Nome da Tarefa *", key="_svman_tk_nome")
    cat_sel  = st.selectbox("Categoria *", _CATEGORIAS, key="_svman_tk_cat")
    tipo_sel = st.selectbox("Tipo *", _TIPOS_MAN, key="_svman_tk_tipo")
    prio_sel = st.selectbox("Prioridade", _PRIORIDADES, index=1, key="_svman_tk_prio")
    orig_sel = st.selectbox("Origem", _ORIGENS, index=7, key="_svman_tk_orig")

    # Campos condicionais por tipo
    period_dias = 0
    period_h    = 0
    prox_data   = ""
    prox_h      = 0
    dep_rel     = False

    if tipo_sel == "Calendário":
        period_dias = st.number_input("Periodicidade (dias) *", min_value=1, value=30,
                                      step=1, key="_svman_tk_pdias")
        prox_dt = st.date_input("Próxima execução *", value=datetime.date.today(),
                                key="_svman_tk_pdata", format="DD/MM/YYYY")
        prox_data = prox_dt.strftime("%d/%m/%Y") if prox_dt else ""

    elif tipo_sel == "Horímetro":
        period_h = st.number_input("Periodicidade (horas) *", min_value=100, value=5000,
                                   step=100, key="_svman_tk_ph")
        prox_h   = st.number_input("Próxima execução (horímetro) *", min_value=0, value=5000,
                                   step=100, key="_svman_tk_prox_h")

    elif tipo_sel == "Condição":
        st.info("🔍 Tarefa por Condição: ficará como 'Depende de análise preditiva' até indicação técnica.")
        dep_rel = st.checkbox("Depende de relatório técnico", value=True, key="_svman_tk_dep")

    descricao = st.text_area("Descrição da tarefa", height=90, key="_svman_tk_desc")
    recomend  = st.text_area("Recomendação técnica (opcional)", height=60, key="_svman_tk_rec")

    with st.expander("🔒 Obs. interna (não visível ao cliente)"):
        obs_int = st.text_area("Obs. interna", height=50, key="_svman_tk_obs")

    if st.button("💾 Cadastrar Tarefa", key="_svman_tk_save", type="primary",
                 use_container_width=True):
        if not sel_cid:
            st.error("Selecione um cliente.")
        elif not nome_tk.strip():
            st.error("Informe o nome da tarefa.")
        else:
            task_id = add_maintenance_task({
                "cliente_id":               sel_cid,
                "ativo_id":                 at_id,
                "plano_id":                 pl_id,
                "nome_tarefa":              nome_tk.strip(),
                "categoria":                cat_sel,
                "tipo_manutencao":          tipo_sel,
                "periodicidade_dias":       str(period_dias) if period_dias else "",
                "periodicidade_horas":      str(period_h) if period_h else "",
                "proxima_execucao_data":    prox_data,
                "proxima_execucao_horimetro": str(prox_h) if prox_h else "",
                "prioridade":               prio_sel,
                "depende_relatorio":        dep_rel,
                "origem":                   orig_sel,
                "descricao":                descricao.strip(),
                "recomendacao":             recomend.strip(),
                "obs_interna":              obs_int.strip(),
            }, created_by=current_nome())
            if task_id:
                st.success(f"✅ Tarefa cadastrada! ID: {task_id}")
                from sheets import load_sheet as _ls; _ls.clear()
            else:
                st.error("Erro ao cadastrar tarefa.")


def _render_lista_tarefas_sv() -> None:
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;margin:0 0 0.5rem;'>Tarefas cadastradas</p>",
        unsafe_allow_html=True,
    )
    try:
        df_cli = get_all_clientes()
        cli_opts = ["Todos"] + [
            str(r.get("Empresa", "")).strip()
            for _, r in df_cli.iterrows()
            if str(r.get("Empresa", "")).strip()
        ]
    except Exception:
        cli_opts = ["Todos"]
        df_cli   = None

    c1, c2, c3 = st.columns(3)
    with c1:
        cli_f = st.selectbox("Cliente", cli_opts, key="_svman_tklst_cli")
    with c2:
        tipo_f = st.selectbox("Tipo", ["Todos"] + _TIPOS_MAN, key="_svman_tklst_tipo")
    with c3:
        status_f = st.selectbox(
            "Status", ["Todas", "Vencidas", "Próximas", "Por condição", "Em dia"],
            key="_svman_tklst_status",
        )

    c4, c5 = st.columns(2)
    with c4:
        gut_f = st.selectbox(
            "Prioridade GUT", ["Todas", "Crítica", "Alta", "Moderada", "Baixa"],
            key="_svman_tklst_gut",
        )
    with c5:
        ativo_f = st.text_input(
            "Filtrar por Ativo (Id)", key="_svman_tklst_ativo",
            placeholder="Ex: AT-2026-001",
        ).strip()

    cid_f = ""
    if cli_f != "Todos" and df_cli is not None:
        try:
            cid_f = str(
                df_cli[df_cli["Empresa"].str.strip() == cli_f].iloc[0]
                .get("Client_Id", cli_f)
            ).strip()
        except Exception:
            cid_f = cli_f

    df_tasks = get_maintenance_tasks(
        client_id = cid_f,
        tipo      = "" if tipo_f == "Todos" else tipo_f,
    )

    if df_tasks.empty:
        empty_state("Nenhuma tarefa cadastrada com os filtros selecionados.", icon="🛠️")
        return

    # ── Enriquece com status e prioridade GUT para filtrar/ordenar ────────────
    _STATUS_FILTRO_MAP = {
        "vencidas": "vencida", "próximas": "próxima do vencimento",
        "por condição": "depende de análise preditiva", "em dia": "em dia",
    }
    enriched = []
    for _, row in df_tasks.iterrows():
        aid    = str(row.get("Ativo_Id", "")).strip()
        h_at   = _get_h(aid) if aid else 0
        status = calc_task_status(row.to_dict(), h_at)
        gut_r  = calculate_gut(row.get("Gut_Gravidade"), row.get("Gut_Urgencia"), row.get("Gut_Tendencia"))
        enriched.append({
            "row": row, "ativo_id": aid, "status_key": _norm(status),
            "gut_prioridade": gut_r["prioridade"] if gut_r else "",
        })

    if status_f != "Todas":
        sf = _STATUS_FILTRO_MAP.get(_norm(status_f), _norm(status_f))
        enriched = [e for e in enriched if e["status_key"] == sf]
    if gut_f != "Todas":
        enriched = [e for e in enriched if e["gut_prioridade"] == gut_f]
    if ativo_f:
        enriched = [e for e in enriched if e["ativo_id"] == ativo_f]

    if not enriched:
        empty_state("Nenhuma tarefa encontrada com os filtros selecionados.", icon="🛠️")
        return

    # Ordenação padrão: GUT Crítica → GUT Alta → vencidas → (ordem original)
    _GUT_RANK = {"Crítica": 0, "Alta": 1, "Moderada": 2, "Baixa": 3}
    enriched.sort(key=lambda e: (
        _GUT_RANK.get(e["gut_prioridade"], 4),
        0 if e["status_key"] == "vencida" else 1,
    ))

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.8rem;margin:0.5rem 0;'>"
        f"{len(enriched)} tarefa(s) encontrada(s)</p>",
        unsafe_allow_html=True,
    )
    for e in enriched:
        _render_task_card_sv(e["row"])


def _render_task_card_sv(row, show_actions: bool = True) -> None:
    task_id  = str(row.get("Id", "")).strip()
    nome     = str(row.get("Nome_Tarefa", "")).strip() or "Sem nome"
    tipo     = str(row.get("Tipo_Manutencao", "")).strip()
    cat      = str(row.get("Categoria", "")).strip()
    prio     = str(row.get("Prioridade", "")).strip()
    ativo_id = str(row.get("Ativo_Id", "")).strip()
    prox_dt  = str(row.get("Proxima_Execucao_Data", "")).strip()
    prox_h   = str(row.get("Proxima_Execucao_Horimetro", "")).strip()
    pd_dias  = str(row.get("Periodicidade_Dias", "")).strip()
    pd_horas = str(row.get("Periodicidade_Horas", "")).strip()

    h_atual = _get_h(ativo_id) if ativo_id else 0
    status  = calc_task_status(row.to_dict(), h_atual)

    status_accent = status_color(status, "manutencao")

    gut_res  = calculate_gut(row.get("Gut_Gravidade"), row.get("Gut_Urgencia"), row.get("Gut_Tendencia"))
    gut_html = (
        f"<span style='margin-left:5px;'>{status_badge(gut_res['prioridade'], 'gut')}</span>"
        f"<span style='font-size:0.62rem;color:{COLOR_MUTED};margin-left:4px;'>GUT {gut_res['score']}</span>"
    ) if gut_res else ""

    icons = {"Calendário": "📆", "Horímetro": "⏱", "Condição": "🔍"}
    icon  = icons.get(tipo, "📋")

    if tipo == "Horímetro" and prox_h and prox_h not in ("", "nan", "0"):
        detalhe = f"Próximo: {prox_h}h (atual: {h_atual}h)"
    elif tipo == "Calendário" and prox_dt and prox_dt not in ("", "nan"):
        detalhe = f"Próxima: {prox_dt}"
        if pd_dias:
            detalhe += f" (a cada {pd_dias}d)"
    else:
        detalhe = "Aguarda avaliação técnica"

    col_info, col_btns = st.columns([7, 2])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {status_accent};border-radius:10px;"
            f"padding:0.7rem 1rem;margin-bottom:3px;'>"
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:flex-start;flex-wrap:wrap;gap:5px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;'>"
            f"{icon} {nome}</span>"
            f"<div style='display:flex;gap:5px;'>"
            + status_badge(status, "manutencao")
            + status_badge(prio, "prioridade")
            + f"{gut_html}</div></div>"
            f"<p style='color:{COLOR_MUTED};font-size:0.75rem;margin:3px 0 0;'>"
            f"{cat}" + (f"  ·  {detalhe}" if detalhe else "")
            + (f"  ·  ⚙️ {ativo_id}" if ativo_id else "")
            + f"</p></div>",
            unsafe_allow_html=True,
        )
    if show_actions:
        with col_btns:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"_svman_del_{task_id}",
                         use_container_width=True, help="Excluir tarefa"):
                delete_maintenance_task(task_id)
                from sheets import load_sheet as _ls; _ls.clear()
                st.rerun()

    if show_actions:
        with st.expander(f"🎯 GUT — {nome[:40]}", expanded=False):
            st.caption(f"ℹ️ {GUT_DISCLAIMER}")
            gc1, gc2, gc3 = st.columns(3)
            g_atual = int(row.get("Gut_Gravidade") or 3)
            u_atual = int(row.get("Gut_Urgencia") or 3)
            t_atual = int(row.get("Gut_Tendencia") or 3)
            with gc1:
                g_novo = st.number_input("Gravidade", 1, 5, g_atual, key=f"_gut_g_{task_id}")
            with gc2:
                u_novo = st.number_input("Urgência", 1, 5, u_atual, key=f"_gut_u_{task_id}")
            with gc3:
                t_novo = st.number_input("Tendência", 1, 5, t_atual, key=f"_gut_t_{task_id}")
            obs_novo = st.text_area(
                "Observação técnica", value=str(row.get("Gut_Observacao", "")).strip(),
                key=f"_gut_obs_{task_id}", height=68,
            )
            preview = calculate_gut(g_novo, u_novo, t_novo)
            if preview:
                st.markdown(
                    status_badge(preview["prioridade"], "gut")
                    + f" <span style='font-size:0.8rem;color:{COLOR_MUTED};'>Score {preview['score']}</span>",
                    unsafe_allow_html=True,
                )
            if st.button("💾 Salvar GUT", key=f"_gut_save_{task_id}"):
                if update_maintenance_task_gut(task_id, g_novo, u_novo, t_novo, obs_novo):
                    st.success("GUT atualizado.")
                    st.rerun()
                else:
                    st.error("Não foi possível salvar o GUT desta tarefa.")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — EXECUTAR TAREFA
# ═══════════════════════════════════════════════════════════════════════════════

def _render_tab_executar() -> None:
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;margin:0 0 0.75rem;'>"
        f"✅ Registrar Execução de Tarefa</p>",
        unsafe_allow_html=True,
    )

    # Seleção de cliente
    try:
        df_cli = get_all_clientes()
        cli_rows = [
            (str(r.get("Empresa", "")).strip(),
             str(r.get("Client_Id", r.get("Cliente_Id", ""))).strip())
            for _, r in df_cli.iterrows()
            if str(r.get("Empresa", "")).strip()
        ]
    except Exception:
        cli_rows = []

    c1, c2 = st.columns(2)
    with c1:
        if cli_rows:
            opts    = [f"{e} ({c})" for e, c in cli_rows]
            ids     = [c for _, c in cli_rows]
            cli_sel = st.selectbox("Cliente", opts, key="_svman_ex_cli")
            sel_cid = ids[opts.index(cli_sel)] if cli_sel in opts else ""
        else:
            sel_cid = st.text_input("Cliente ID", key="_svman_ex_cid")
    with c2:
        tipo_ex = st.selectbox("Tipo de tarefa", ["Todos"] + _TIPOS_MAN, key="_svman_ex_tipo")

    df_tasks = get_maintenance_tasks(
        client_id = sel_cid,
        tipo      = "" if tipo_ex == "Todos" else tipo_ex,
    )

    if df_tasks.empty:
        empty_state("Nenhuma tarefa encontrada. Cadastre tarefas na aba 'Tarefas'.", icon="🛠️")
        return

    # Calcula status de cada tarefa para ordenação
    tasks_with_status = []
    for _, row in df_tasks.iterrows():
        aid    = str(row.get("Ativo_Id", "")).strip()
        h_at   = _get_h(aid) if aid else 0
        s      = calc_task_status(row.to_dict(), h_at)
        tasks_with_status.append((row, s))

    # Ordena: Vencida → Próxima → Em dia → Condição
    order_map = {"Vencida": 0, "Próxima do vencimento": 1, "Em dia": 2}
    tasks_with_status.sort(key=lambda x: order_map.get(x[1], 3))

    task_labels = [
        f"{str(r.get('Nome_Tarefa','')).strip()} [{s}] (ativo: {str(r.get('Ativo_Id','')).strip() or '—'})"
        for r, s in tasks_with_status
    ]
    task_ids = [str(r.get("Id", "")).strip() for r, _ in tasks_with_status]

    sel_lbl  = st.selectbox("Selecionar tarefa", task_labels, key="_svman_ex_task_sel")
    sel_idx  = task_labels.index(sel_lbl) if sel_lbl in task_labels else 0
    sel_tid  = task_ids[sel_idx]
    sel_row, sel_status = tasks_with_status[sel_idx]

    # Mostra card da tarefa selecionada
    _render_task_card_sv(sel_row, show_actions=False)

    st.markdown("---")
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;margin:0 0 0.5rem;'>"
        f"Registrar execução</p>",
        unsafe_allow_html=True,
    )

    tipo_t = str(sel_row.get("Tipo_Manutencao", "")).strip()
    if tipo_t == "Condição":
        st.warning(
            "Esta é uma tarefa por Condição. Só conclua se relatório técnico "
            "ou avaliação Pred.IO indicar a necessidade. "
            "Não conclua automaticamente por horímetro."
        )

    # Atualização de horímetro (se horímetro)
    aid_sel = str(sel_row.get("Ativo_Id", "")).strip()
    h_atual = _get_h(aid_sel) if aid_sel else 0
    if tipo_t == "Horímetro" and aid_sel:
        h_atual = st.number_input(
            f"Horímetro atual do ativo ({aid_sel})",
            min_value=0, value=h_atual, step=10, key=f"h_sv_{aid_sel}",
            on_change=_do_save_horimetro, args=(aid_sel,),
        )

    # Formulário de execução
    c1, c2 = st.columns(2)
    with c1:
        dt_exec = st.date_input("Data de execução *", value=datetime.date.today(),
                                key="_svman_ex_dt", format="DD/MM/YYYY")
        data_str = dt_exec.strftime("%d/%m/%Y") if dt_exec else ""
    with c2:
        h_exec = st.number_input("Horímetro na execução (se aplicável)", min_value=0,
                                 value=h_atual, step=10, key="_svman_ex_h")

    responsavel = st.text_input("Responsável", value=current_nome(), key="_svman_ex_resp")
    desc_exec   = st.text_area("Descrição da execução", height=90, key="_svman_ex_desc",
                               placeholder="Descreva o que foi feito, observações, condição encontrada...")
    evidencias  = st.text_input("Evidências / referências", key="_svman_ex_evid",
                                placeholder="ex: Foto 001, laudo de óleo nº 44")
    arquivo_url = st.text_input("URL do arquivo/laudo (opcional)", key="_svman_ex_url")

    with st.expander("🔒 Obs. interna"):
        obs_int = st.text_area("Obs. interna (não visível ao cliente)", height=60, key="_svman_ex_obs")

    if st.button("✅ Registrar execução", key="_svman_ex_save", type="primary",
                 use_container_width=True):
        if not data_str:
            st.error("Informe a data de execução.")
        else:
            result = complete_maintenance_task(
                task_id   = sel_tid,
                exec_dados = {
                    "executado_em":       data_str,
                    "horimetro_execucao": h_exec if h_exec else "",
                    "descricao":          desc_exec.strip(),
                    "evidencias":         evidencias.strip(),
                    "arquivo_url":        arquivo_url.strip(),
                    "obs_interna":        obs_int.strip(),
                },
                executed_by = responsavel.strip(),
            )
            if result.get("ok"):
                st.success(
                    f"✅ Execução registrada! ID: {result['exec_id']}  \n"
                    "Próxima execução calculada automaticamente. "
                    "Evento registrado no histórico técnico do ativo."
                )
                from sheets import load_sheet as _ls; _ls.clear()
            else:
                st.error(result.get("erro", "Erro ao registrar execução."))

    # Histórico de execuções da tarefa
    st.markdown("---")
    st.markdown(
        f"<p style='font-weight:600;color:{COLOR_NAVY};font-size:0.85rem;margin:0 0 0.5rem;'>"
        f"📜 Histórico desta tarefa</p>",
        unsafe_allow_html=True,
    )
    df_exec = get_maintenance_executions(
        client_id = str(sel_row.get("Cliente_Id", "")).strip(),
        task_id   = sel_tid,
    )
    if df_exec.empty:
        st.caption("Nenhuma execução registrada ainda para esta tarefa.")
    else:
        for _, ex in df_exec.iterrows():
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-left:3px solid #10B981;border-radius:8px;"
                f"padding:0.6rem 0.9rem;margin-bottom:5px;'>"
                f"<p style='font-size:0.8rem;font-weight:700;color:{COLOR_NAVY};margin:0;'>"
                f"✅ {str(ex.get('Executado_Em',''))}"
                + (f"  ·  ⏱ {str(ex.get('Horimetro_Execucao',''))}h"
                   if str(ex.get('Horimetro_Execucao','')) not in ('','0','nan') else "")
                + f"  ·  👤 {str(ex.get('Responsavel',''))}</p>"
                + (f"<p style='font-size:0.78rem;color:#475569;margin:3px 0 0;'>"
                   f"{str(ex.get('Descricao_Execucao',''))}</p>"
                   if str(ex.get('Descricao_Execucao','')) not in ('','nan') else "")
                + "</div>",
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ALERTAS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_tab_alertas() -> None:
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;margin:0 0 0.75rem;'>"
        f"⚠️ Tarefas Vencidas e Próximas do Vencimento</p>",
        unsafe_allow_html=True,
    )

    # Filtro cliente
    try:
        df_cli = get_all_clientes()
        cli_opts = ["Todos os clientes"] + [
            str(r.get("Empresa", "")).strip()
            for _, r in df_cli.iterrows()
            if str(r.get("Empresa", "")).strip()
        ]
    except Exception:
        cli_opts  = ["Todos os clientes"]
        df_cli    = None

    c1, c2 = st.columns([2, 4])
    with c1:
        cli_f = st.selectbox("Cliente", cli_opts, key="_svman_al_cli")

    cid_f = ""
    if cli_f != "Todos os clientes" and df_cli is not None:
        try:
            cid_f = str(
                df_cli[df_cli["Empresa"].str.strip() == cli_f].iloc[0]
                .get("Client_Id", cli_f)
            ).strip()
        except Exception:
            cid_f = cli_f

    with c2:
        if st.button("🔔 Gerar alertas para tarefas vencidas/próximas", key="_svman_gen_alert",
                     type="primary"):
            with st.spinner("Escaneando tarefas..."):
                count = generate_maintenance_alerts(client_id=cid_f)
            if count > 0:
                st.success(f"✅ {count} alerta(s) gerado(s) na Central de Alertas.")
            else:
                empty_state("Nenhuma tarefa próxima ou vencida encontrada para gerar alertas.", icon="🔔")

    df_tasks = get_maintenance_tasks(client_id=cid_f)
    if df_tasks.empty:
        empty_state("Nenhuma tarefa cadastrada.", icon="🛠️")
        return

    vencidas = []
    proximas = []
    condicao = []

    for _, row in df_tasks.iterrows():
        tipo   = str(row.get("Tipo_Manutencao", "")).strip()
        if tipo in ("Condição", "Condicao"):
            condicao.append(row)
            continue
        aid    = str(row.get("Ativo_Id", "")).strip()
        h_at   = _get_h(aid) if aid else 0
        status = calc_task_status(row.to_dict(), h_at)
        if status == "Vencida":
            vencidas.append((row, status))
        elif status == "Próxima do vencimento":
            proximas.append((row, status))

    # Métricas
    mc = st.columns(3)
    for col, (icon, label, val, cor) in zip(mc, [
        ("🔴", "Vencidas",     len(vencidas), status_color("vencida", "manutencao")),
        ("🟡", "Próximas",     len(proximas), status_color("próxima", "manutencao")),
        ("🔵", "Por condição", len(condicao), status_color("por condição", "manutencao")),
    ]):
        with col:
            sv_metric_card(icon, label, str(val), cor)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    if vencidas:
        st.markdown(
            f"<p style='font-weight:700;color:#991B1B;font-size:0.9rem;margin:0 0 0.5rem;'>"
            f"🔴 Tarefas Vencidas ({len(vencidas)})</p>",
            unsafe_allow_html=True,
        )
        for row, s in vencidas:
            _render_task_card_sv(row, show_actions=False)

    if proximas:
        st.markdown(
            f"<p style='font-weight:700;color:#92400E;font-size:0.9rem;margin:0.75rem 0 0.5rem;'>"
            f"🟡 Próximas do Vencimento ({len(proximas)})</p>",
            unsafe_allow_html=True,
        )
        for row, s in proximas:
            _render_task_card_sv(row, show_actions=False)

    if condicao:
        st.markdown(
            f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
            f"border-radius:8px;padding:0.6rem 1rem;margin-top:0.75rem;'>"
            f"<p style='font-size:0.75rem;font-weight:700;color:#1E40AF;margin:0 0 4px;'>"
            f"🔍 Recomendações por Condição ({len(condicao)})</p>"
            f"<p style='font-size:0.72rem;color:#3B82F6;margin:0;'>"
            f"Estas intervenções não são automáticas por horímetro. "
            f"A decisão depende da interpretação dos laudos técnicos.</p></div>",
            unsafe_allow_html=True,
        )
        for row in condicao:
            _render_task_card_sv(row, show_actions=False)

    if not vencidas and not proximas and not condicao:
        app_alert("Nenhuma tarefa vencida ou próxima do vencimento.", kind="success")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — MODELO MYCOM (referência / mock)
# ═══════════════════════════════════════════════════════════════════════════════

def _render_tab_mock() -> None:
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;margin:0 0 0.5rem;'>"
        f"🔍 Modelo de Referência — Unidade Compressora MYCOM</p>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Plano de referência para compressor MYCOM 200 VLD. "
        "Use como base para criar tarefas na aba 'Tarefas'."
    )

    ativo_id = "AT-2026-001"
    key      = f"h_sv_{ativo_id}"
    if key not in st.session_state:
        h_sheets  = get_horimetro(ativo_id)
        st.session_state[key] = h_sheets if h_sheets is not None else _HORIMETRO_ATUAL_MOCK

    col_h, _ = st.columns([2, 5])
    with col_h:
        st.number_input(
            "⏱ Horímetro atual (h)",
            min_value=0, step=10,
            key=key,
            on_change=_do_save_horimetro,
            args=(ativo_id,),
            help="Altere e pressione Enter para salvar.",
        )

    h = st.session_state[key]
    plano_com_h = [{**t, "horimetro_atual": h} for t in _PLANO_MOCK_COMPRESSOR]
    _render_plano_manutencao(plano_com_h)

    st.markdown(
        f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
        f"border-radius:8px;padding:0.75rem 1rem;margin-top:1rem;'>"
        f"<p style='font-size:0.78rem;color:#1E40AF;margin:0;'>{_NOTE_CONDICAO}</p></div>",
        unsafe_allow_html=True,
    )
