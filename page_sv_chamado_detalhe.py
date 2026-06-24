"""Supervisão Pred.IO — Detalhe do Chamado + Timeline + Ações."""
import streamlit as st
from auth import require_staff, current_nome, current_email
from sheets import (
    get_chamado_by_id, get_mensagens_chamado,
    update_chamado, add_mensagem, concluir_chamado,
    abrir_chamado_v2, get_all_clientes, get_ativos,
)
from ui import (sv_page_header, COLOR_NAVY, COLOR_BORDER, COLOR_CARD,
                COLOR_MUTED, STATUS_CFG, PRIORIDADE_CFG)

_STATUS_OPTS = [
    "Aberto", "Em análise", "Em andamento",
    "Aguardando cliente", "Concluído", "Cancelado", "Reaberto",
]
_PRIO_OPTS = ["Crítica", "Alta", "Média", "Baixa"]
_CATEGORIAS = [
    "Dúvida técnica", "Alarme", "Falha operacional",
    "Manutenção vencida", "Manutenção próxima", "Relatório técnico",
    "Recomendação por condição", "Óleo e lubrificação",
    "Vibração", "Termografia", "Painel Mypro Touch", "Painel Mypro Touch AD",
    "Motor elétrico", "Rolamento", "Overhaul por condição", "Outro",
]
_ORIGEM_ICON = {
    "Portal do Cliente":    "🖥️",
    "Assistente Técnico":   "🤖",
    "Alerta":               "🔔",
    "Relatório Técnico":    "📁",
    "Plano de Manutenção":  "📅",
    "Supervisão Pred.IO":   "⚙️",
}


def render() -> None:
    require_staff()

    chamado_id = st.session_state.get("sv_chamado_id", "")

    # Modo de abertura de novo chamado pela supervisão
    if chamado_id == "__novo__":
        _render_form_novo_sv()
        return

    if not chamado_id:
        st.warning("Nenhum chamado selecionado.")
        if st.button("← Voltar"):
            st.session_state["sv_view"] = "chamados"
            st.rerun()
        return

    chamado = get_chamado_by_id(chamado_id)
    if not chamado:
        st.error(f"Chamado {chamado_id} não encontrado.")
        if st.button("← Voltar"):
            st.session_state["sv_view"] = "chamados"
            st.rerun()
        return

    sv_page_header(
        f"Chamado #{chamado_id}",
        subtitle=str(chamado.get("Titulo", "")),
        back_label="Lista de Chamados",
        back_view="chamados",
    )

    _render_header_card(chamado)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    col_timeline, col_acoes = st.columns([3, 1], gap="large")
    with col_timeline:
        _render_timeline(chamado_id)
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        _render_reply_box(chamado_id, chamado)

    with col_acoes:
        _render_action_panel(chamado_id, chamado)


# ── Formulário novo chamado (supervisão) ──────────────────────────────────────

def _render_form_novo_sv() -> None:
    sv_page_header(
        "Abrir Chamado",
        subtitle="Novo chamado criado pela supervisão Pred.IO",
        back_label="Lista de Chamados",
        back_view="chamados",
    )

    try:
        df_cli = get_all_clientes()
        cli_rows = [
            (str(r.get("Empresa", "")).strip(),
             str(r.get("Client_Id", r.get("Empresa", ""))).strip(),
             str(r.get("Email", "")).strip())
            for _, r in df_cli.iterrows()
            if str(r.get("Empresa", "")).strip()
        ]
    except Exception:
        cli_rows = []

    with st.form("form_sv_novo_chamado", clear_on_submit=False):
        if cli_rows:
            opts    = [f"{e} ({c})" for e, c, _ in cli_rows]
            ids     = [c for _, c, _ in cli_rows]
            emails  = [em for _, _, em in cli_rows]
            cli_sel = st.selectbox("Cliente *", opts, key="_svch_nov_cli")
            idx_c   = opts.index(cli_sel) if cli_sel in opts else 0
            sel_cid = ids[idx_c]
            sel_email = emails[idx_c]
        else:
            sel_cid   = st.text_input("Cliente ID *", key="_svch_nov_cid")
            sel_email = st.text_input("E-mail do cliente", key="_svch_nov_email")

        col1, col2 = st.columns(2)
        with col1:
            ativo_id = st.text_input("Ativo ID (opcional)", key="_svch_nov_at")
            comp     = st.text_input("Componente (opcional)", key="_svch_nov_comp")
        with col2:
            cat = st.selectbox("Categoria", _CATEGORIAS, key="_svch_nov_cat")
            prio= st.selectbox("Prioridade", _PRIO_OPTS, index=1, key="_svch_nov_prio")

        titulo    = st.text_input("Título *", key="_svch_nov_titulo")
        descricao = st.text_area("Descrição *", height=110, key="_svch_nov_desc")

        col_r, col_t, col_a = st.columns(3)
        with col_r:
            report_id = st.text_input("Vincular Relatório ID", key="_svch_nov_rep")
        with col_t:
            task_id   = st.text_input("Vincular Tarefa ID", key="_svch_nov_task")
        with col_a:
            alert_id  = st.text_input("Vincular Alerta ID", key="_svch_nov_alt")

        salvar = st.form_submit_button("📨 Criar Chamado", type="primary",
                                       use_container_width=True)

    if salvar:
        if not sel_cid or not titulo.strip() or not descricao.strip():
            st.error("Preencha cliente, título e descrição.")
        else:
            cid = abrir_chamado_v2({
                "client_id":           sel_cid,
                "usuario_id":          current_email(),
                "empresa":             sel_cid,
                "email":               sel_email,
                "ativo_id":            ativo_id.strip(),
                "componente_id":       comp.strip(),
                "report_id":           report_id.strip(),
                "maintenance_task_id": task_id.strip(),
                "alert_id":            alert_id.strip(),
                "titulo":              titulo.strip(),
                "descricao":           descricao.strip(),
                "categoria":           cat,
                "prioridade":          prio,
                "origem":              "Supervisão Pred.IO",
            })
            if cid:
                st.success(f"✅ Chamado #{cid} criado.")
                from sheets import load_sheet as _ls; _ls.clear()
                st.session_state["sv_chamado_id"] = cid
                st.rerun()
            else:
                st.error("Erro ao criar chamado.")


# ── Cabeçalho ─────────────────────────────────────────────────────────────────

def _render_header_card(chamado: dict) -> None:
    empresa    = str(chamado.get("Empresa",     "")).strip()
    email      = str(chamado.get("Email",       "")).strip()
    prioridade = str(chamado.get("Prioridade",  "Baixa")).strip()
    status     = str(chamado.get("Status",      "Aberto")).strip()
    data_ab    = str(chamado.get("Aberto_Em",
                    chamado.get("Data_Abertura",""))).strip()[:16]
    data_up    = str(chamado.get("Atualizado_Em",
                    chamado.get("Data_Atualizacao",""))).strip()[:16]
    responsavel= str(chamado.get("Responsavel", "")).strip()
    descricao  = str(chamado.get("Descricao",   "")).strip()
    categoria  = str(chamado.get("Categoria",   "")).strip()
    origem     = str(chamado.get("Origem",      "")).strip()
    ativo_id   = str(chamado.get("Ativo_Id",    "")).strip()
    comp_id    = str(chamado.get("Componente_Id","")).strip()
    report_id  = str(chamado.get("Report_Id",   "")).strip()
    task_id    = str(chamado.get("Maintenance_Task_Id","")).strip()
    alert_id   = str(chamado.get("Alert_Id",    "")).strip()

    pr_bg, pr_tc = PRIORIDADE_CFG.get(prioridade.lower(), ("#94A3B8", "#fff"))
    st_bg, st_tc = STATUS_CFG.get(status.lower(), ("#94A3B8", "#fff"))

    def pill(label, bg, tc):
        return (f"<span style='background:{bg};color:{tc};-webkit-text-fill-color:{tc};"
                f"font-size:0.75rem;font-weight:700;padding:3px 12px;border-radius:20px;'>"
                f"{label}</span>")

    meta_items = [
        ("🏢", empresa), ("✉️", email),
        ("📅", f"Aberto {data_ab}" if data_ab else ""),
        ("🔄", f"Atualizado {data_up}" if data_up else ""),
        ("👤", f"Responsável: {responsavel}" if responsavel else "Sem responsável"),
        ("🏷️", categoria), (f"{_ORIGEM_ICON.get(origem,'🔗')}", origem),
    ]
    if ativo_id:  meta_items.append(("⚙️", f"Ativo: {ativo_id}"))
    if comp_id:   meta_items.append(("🔩", f"Comp.: {comp_id}"))

    meta_html = "".join(
        f"<span style='color:#64748B;font-size:0.78rem;margin-right:14px;'>{icon} {val}</span>"
        for icon, val in meta_items if val
    )

    vinculos = []
    if report_id: vinculos.append(f"📁 Relatório: {report_id}")
    if task_id:   vinculos.append(f"📅 Tarefa: {task_id}")
    if alert_id:  vinculos.append(f"🔔 Alerta: {alert_id}")

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-left:6px solid {pr_bg};border-radius:12px;padding:1.25rem 1.5rem;'>"
        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:0.75rem;flex-wrap:wrap;'>"
        f"{pill(prioridade, pr_bg, pr_tc)} {pill(status, st_bg, st_tc)}"
        + (f" {pill(categoria,'#F1F5F9','#475569')}" if categoria else "")
        + f"</div>"
        f"<div style='margin-bottom:0.75rem;flex-wrap:wrap;'>{meta_html}</div>"
        + (f"<p style='font-size:0.78rem;color:{COLOR_MUTED};margin:0 0 0.6rem;'>"
           f"🔗 {' · '.join(vinculos)}</p>" if vinculos else "")
        + (f"<div style='background:#F8FAFC;border-radius:8px;padding:12px 14px;"
           f"border:1px solid #E2E8F0;'>"
           f"<p style='color:#1e293b;font-size:0.88rem;margin:0;line-height:1.6;'>"
           f"<strong>Descrição:</strong> {descricao}</p></div>"
           if descricao else "")
        + "</div>",
        unsafe_allow_html=True,
    )


# ── Timeline ──────────────────────────────────────────────────────────────────

def _render_timeline(chamado_id: str) -> None:
    st.markdown(
        f"<p style='color:{COLOR_NAVY};font-weight:700;font-size:0.95rem;"
        f"margin:0 0 0.75rem;'>📋 Histórico do Chamado</p>",
        unsafe_allow_html=True,
    )
    msgs = get_mensagens_chamado(chamado_id)
    if msgs.empty:
        st.markdown(
            f"<p style='color:{COLOR_MUTED};font-size:0.88rem;'>"
            "Nenhuma mensagem registrada ainda.</p>",
            unsafe_allow_html=True,
        )
        return

    for _, m in msgs.iterrows():
        autor_tipo = str(m.get("Autor_Tipo",   "")).strip()
        autor      = str(m.get("Autor",        "")).strip()
        mensagem   = str(m.get("Mensagem",     "")).strip()
        tipo       = str(m.get("Tipo_Mensagem","")).strip()
        data       = str(m.get("Data",         "")).strip()[:16]
        visivel    = str(m.get("Visivel_Cliente","1")).strip()

        if tipo in ("alteracao_status", "alteracao_prioridade",
                    "atribuicao_responsavel", "encerramento", "reabertura"):
            st.markdown(
                f"<div style='text-align:center;margin:10px 0;'>"
                f"<span style='background:#F1F5F9;border:1px solid #E2E8F0;"
                f"border-radius:20px;padding:4px 16px;font-size:0.75rem;color:#64748B;'>"
                f"🔄 {mensagem} · {data}</span></div>",
                unsafe_allow_html=True,
            )
        elif visivel == "0" or tipo == "observacao_interna":
            st.markdown(
                f"<div style='display:flex;justify-content:flex-end;margin:8px 0;'>"
                f"<div style='max-width:82%;background:#FFFBEB;"
                f"border:1px dashed #F59E0B;border-radius:10px;padding:10px 14px;'>"
                f"<div style='font-size:0.72rem;color:#D97706;font-weight:700;"
                f"margin-bottom:4px;'>🔒 INTERNO — {autor}</div>"
                f"<p style='color:#78350F;font-size:0.87rem;margin:0;line-height:1.5;'>"
                f"{mensagem}</p>"
                f"<div style='font-size:0.7rem;color:#A16207;margin-top:5px;'>{data}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        elif autor_tipo in ("funcionario", "predio") or tipo == "resposta_predio":
            st.markdown(
                f"<div style='display:flex;justify-content:flex-end;margin:8px 0;'>"
                f"<div style='max-width:82%;background:#0F1F3D;"
                f"border-radius:12px 12px 2px 12px;padding:11px 15px;'>"
                f"<div style='font-size:0.72rem;color:#93C5FD;font-weight:700;"
                f"margin-bottom:4px;'>⚙️ {autor} (Pred.IO)</div>"
                f"<p style='color:#E2E8F0;font-size:0.87rem;margin:0;line-height:1.5;'>"
                f"{mensagem}</p>"
                f"<div style='font-size:0.7rem;color:#64748B;margin-top:5px;'>{data}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='display:flex;justify-content:flex-start;margin:8px 0;'>"
                f"<div style='max-width:82%;background:#EFF6FF;"
                f"border:1px solid #BFDBFE;"
                f"border-radius:12px 12px 12px 2px;padding:11px 15px;'>"
                f"<div style='font-size:0.72rem;color:#2563EB;font-weight:700;"
                f"margin-bottom:4px;'>👤 {autor}</div>"
                f"<p style='color:#1e293b;font-size:0.87rem;margin:0;line-height:1.5;'>"
                f"{mensagem}</p>"
                f"<div style='font-size:0.7rem;color:#94A3B8;margin-top:5px;'>{data}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )


# ── Resposta ao cliente ───────────────────────────────────────────────────────

def _render_reply_box(chamado_id: str, chamado: dict) -> None:
    st.markdown(
        f"<p style='color:{COLOR_NAVY};font-weight:700;font-size:0.95rem;"
        f"margin:0 0 0.5rem;'>💬 Responder Cliente</p>",
        unsafe_allow_html=True,
    )

    with st.form(f"reply_client_{chamado_id}", clear_on_submit=True):
        resposta = st.text_area(
            "Mensagem visível ao cliente",
            placeholder="Digite a resposta que o cliente verá no portal dele…",
            height=110, label_visibility="visible",
        )
        atualizar_status = st.checkbox("Atualizar status ao enviar resposta")
        novo_status = None
        if atualizar_status:
            cur_status = str(chamado.get("Status", "Aberto")).strip()
            novo_status = st.selectbox(
                "Novo status", _STATUS_OPTS,
                index=_STATUS_OPTS.index(cur_status) if cur_status in _STATUS_OPTS else 0,
            )
        enviar = st.form_submit_button("📨 Enviar resposta ao cliente",
                                       use_container_width=True, type="primary")

    if enviar and resposta.strip():
        nome = current_nome()
        ok = add_mensagem(
            chamado_id    = chamado_id,
            autor         = nome,
            autor_tipo    = "funcionario",
            mensagem      = resposta.strip(),
            visivel_cliente = True,
            tipo_mensagem = "resposta_predio",
        )
        if ok and atualizar_status and novo_status:
            status_ant = str(chamado.get("Status", "")).strip()
            update_chamado(chamado_id, {"Status": novo_status})
            add_mensagem(
                chamado_id    = chamado_id,
                autor         = "sistema",
                autor_tipo    = "sistema",
                mensagem      = f"Status alterado: {status_ant} → {novo_status}",
                visivel_cliente = True,
                tipo_mensagem = "alteracao_status",
            )
        if ok:
            st.success("✅ Resposta enviada com sucesso!")
            st.rerun()
        else:
            st.error("Erro ao enviar. Tente novamente.")


# ── Painel de ações ───────────────────────────────────────────────────────────

def _render_action_panel(chamado_id: str, chamado: dict) -> None:
    status_atual      = str(chamado.get("Status",      "Aberto")).strip()
    prioridade_atual  = str(chamado.get("Prioridade",  "Média")).strip()
    responsavel_atual = str(chamado.get("Responsavel", "")).strip()
    categoria_atual   = str(chamado.get("Categoria",   "Dúvida técnica")).strip()
    report_atual      = str(chamado.get("Report_Id",   "")).strip()
    task_atual        = str(chamado.get("Maintenance_Task_Id", "")).strip()

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;'>"
        f"<p style='color:{COLOR_NAVY};font-weight:700;font-size:0.9rem;margin:0;'>"
        f"⚙️ Atualizar Chamado</p></div>",
        unsafe_allow_html=True,
    )

    with st.form(f"update_chamado_{chamado_id}"):
        novo_status = st.selectbox(
            "Status", _STATUS_OPTS,
            index=_STATUS_OPTS.index(status_atual) if status_atual in _STATUS_OPTS else 0,
        )
        nova_prio = st.selectbox(
            "Prioridade", _PRIO_OPTS,
            index=_PRIO_OPTS.index(prioridade_atual) if prioridade_atual in _PRIO_OPTS else 0,
        )
        nova_cat = st.selectbox(
            "Categoria", _CATEGORIAS,
            index=_CATEGORIAS.index(categoria_atual) if categoria_atual in _CATEGORIAS else 0,
        )
        novo_resp = st.text_input("Responsável", value=responsavel_atual,
                                  placeholder="Nome do técnico")
        novo_rep  = st.text_input("Vincular Relatório ID", value=report_atual,
                                  placeholder="Ex: REP-2026-001")
        novo_task = st.text_input("Vincular Tarefa ID", value=task_atual,
                                  placeholder="Ex: TASK-2026-001")
        salvar = st.form_submit_button("💾 Salvar", use_container_width=True)

    if salvar:
        campos      = {}
        msgs_sistema= []

        if novo_status != status_atual:
            campos["Status"] = novo_status
            msgs_sistema.append(f"Status alterado: {status_atual} → {novo_status}")
        if nova_prio != prioridade_atual:
            campos["Prioridade"] = nova_prio
            msgs_sistema.append(f"Prioridade: {prioridade_atual} → {nova_prio}")
        if nova_cat != categoria_atual:
            campos["Categoria"] = nova_cat
        if novo_resp.strip() != responsavel_atual:
            campos["Responsavel"] = novo_resp.strip()
            msgs_sistema.append(f"Responsável: {responsavel_atual or '—'} → {novo_resp.strip() or '—'}")
        if novo_rep.strip() != report_atual:
            campos["Report_Id"] = novo_rep.strip()
        if novo_task.strip() != task_atual:
            campos["Maintenance_Task_Id"] = novo_task.strip()

        if campos:
            ok = update_chamado(chamado_id, campos)
            for msg in msgs_sistema:
                add_mensagem(chamado_id, "sistema", "sistema", msg,
                             True, "alteracao_status")
            if ok:
                st.success("Atualizado!")
                st.rerun()
            else:
                st.info("Modo demonstração — alterações não persistidas.")
                st.rerun()

    # ── Observação interna ─────────────────────────────────────────────────────
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='background:#FFFBEB;border:1px solid #FDE68A;"
        f"border-radius:12px;padding:1rem 1.25rem;'>"
        f"<p style='color:#92400E;font-weight:700;font-size:0.9rem;margin:0 0 0.25rem;'>"
        f"🔒 Nota Interna</p>"
        f"<p style='color:#A16207;font-size:0.75rem;margin:0;'>Invisível ao cliente</p></div>",
        unsafe_allow_html=True,
    )

    with st.form(f"nota_interna_{chamado_id}", clear_on_submit=True):
        nota = st.text_area(
            "Observação interna",
            placeholder="Anotações técnicas, pendências internas, contexto…",
            height=80, label_visibility="collapsed",
        )
        adicionar = st.form_submit_button("🔒 Adicionar nota interna",
                                          use_container_width=True)

    if adicionar and nota.strip():
        ok = add_mensagem(
            chamado_id    = chamado_id,
            autor         = current_nome(),
            autor_tipo    = "funcionario",
            mensagem      = nota.strip(),
            visivel_cliente = False,
            tipo_mensagem = "observacao_interna",
        )
        if ok:
            st.success("Nota salva!")
            st.rerun()
        else:
            st.error("Erro ao salvar.")

    # ── Ações rápidas ──────────────────────────────────────────────────────────
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:{COLOR_NAVY};font-weight:700;font-size:0.88rem;"
        f"margin:0 0 0.5rem;'>⚡ Ações Rápidas</p>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if status_atual.lower() not in ("concluído", "concluido", "cancelado"):
            if st.button("✅ Encerrar", use_container_width=True, key=f"enc_{chamado_id}"):
                ok = concluir_chamado(chamado_id, concluded_by=current_nome())
                add_mensagem(chamado_id, "sistema", "sistema",
                             f"Chamado encerrado por {current_nome()}.",
                             True, "encerramento")
                if ok:
                    st.success("Chamado encerrado! Evento criado no histórico do ativo.")
                st.rerun()
    with col_b:
        if status_atual.lower() in ("concluído", "concluido"):
            if st.button("🔄 Reabrir", use_container_width=True, key=f"reab_{chamado_id}"):
                update_chamado(chamado_id, {"Status": "Reaberto", "Concluido_Em": "",
                                            "Data_Encerramento": ""})
                add_mensagem(chamado_id, "sistema", "sistema",
                             "Chamado reaberto.", True, "reabertura")
                st.rerun()
