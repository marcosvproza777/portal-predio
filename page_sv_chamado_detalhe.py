"""Supervisão Pred.IO — Detalhe do Chamado + Timeline + Ações."""
import streamlit as st
from auth import require_staff, current_nome, current_email
from sheets import (get_chamado_by_id, get_mensagens_chamado,
                    update_chamado, add_mensagem)
from ui import (sv_page_header, COLOR_NAVY, COLOR_BORDER, COLOR_CARD,
                STATUS_CFG, PRIORIDADE_CFG)

_STATUS_OPTS = [
    "Aberto", "Em análise", "Em andamento",
    "Aguardando cliente", "Concluído", "Cancelado", "Reaberto",
]
_PRIO_OPTS = ["Crítica", "Alta", "Média", "Baixa"]


def render() -> None:
    require_staff()

    chamado_id = st.session_state.get("sv_chamado_id", "")
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
        f"Chamado {chamado_id}",
        subtitle=str(chamado.get("Titulo", "")),
        back_label="Lista de Chamados",
        back_view="chamados",
    )

    # ── Cabeçalho do chamado ──────────────────────────────────────────────────
    _render_header_card(chamado)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Corpo: timeline (esq) + painel de ações (dir) ────────────────────────
    col_timeline, col_acoes = st.columns([3, 1], gap="large")

    with col_timeline:
        _render_timeline(chamado_id)
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        _render_reply_box(chamado_id, chamado)

    with col_acoes:
        _render_action_panel(chamado_id, chamado)


# ── Cabeçalho ─────────────────────────────────────────────────────────────────

def _render_header_card(chamado: dict) -> None:
    empresa     = str(chamado.get("Empresa",     "")).strip()
    planta      = str(chamado.get("Planta",      "")).strip()
    equipamento = str(chamado.get("Equipamento", "")).strip()
    email       = str(chamado.get("Email",       "")).strip()
    prioridade  = str(chamado.get("Prioridade",  "Baixa")).strip()
    status      = str(chamado.get("Status",      "Aberto")).strip()
    data_ab     = str(chamado.get("Data_Abertura","")).strip()[:16]
    data_up     = str(chamado.get("Data_Atualizacao","")).strip()[:16]
    responsavel = str(chamado.get("Responsavel", "")).strip()
    descricao   = str(chamado.get("Descricao",   "")).strip()

    pr_bg, pr_tc = PRIORIDADE_CFG.get(prioridade.lower(), ("#94A3B8", "#fff"))
    st_bg, st_tc = STATUS_CFG.get(status.lower(), ("#94A3B8", "#fff"))

    def pill(label, bg, tc):
        return (f"<span style='background:{bg};color:{tc};-webkit-text-fill-color:{tc};"
                f"font-size:0.75rem;font-weight:700;padding:3px 12px;border-radius:20px;'>"
                f"{label}</span>")

    meta_items = [
        ("🏢", empresa),
        ("🏭", planta),
        ("⚙️", equipamento),
        ("✉️", email),
        ("📅", f"Aberto {data_ab}"),
        ("🔄", f"Atualizado {data_up}" if data_up else ""),
        ("👤", f"Responsável: {responsavel}" if responsavel else "Sem responsável"),
    ]
    meta_html = "".join(
        f"<span style='color:#64748B;font-size:0.8rem;margin-right:14px;'>{icon} {val}</span>"
        for icon, val in meta_items if val
    )

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-left:6px solid {pr_bg};border-radius:12px;padding:1.25rem 1.5rem;'>"
        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:0.75rem;flex-wrap:wrap;'>"
        f"{pill(prioridade, pr_bg, pr_tc)} {pill(status, st_bg, st_tc)}"
        f"</div>"
        f"<div style='margin-bottom:0.75rem;flex-wrap:wrap;'>{meta_html}</div>"
        + (f"<div style='background:#F8FAFC;border-radius:8px;padding:12px 14px;"
           f"margin-top:8px;border:1px solid #E2E8F0;'>"
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
            "<p style='color:#94A3B8;font-size:0.88rem;'>"
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

        # Eventos de sistema — centro
        if tipo in ("alteracao_status", "alteracao_prioridade",
                    "atribuicao_responsavel", "encerramento", "reabertura"):
            st.markdown(
                f"<div style='text-align:center;margin:10px 0;'>"
                f"<span style='background:#F1F5F9;border:1px solid #E2E8F0;"
                f"border-radius:20px;padding:4px 16px;font-size:0.75rem;color:#64748B;'>"
                f"🔄 {mensagem} · {data}</span></div>",
                unsafe_allow_html=True,
            )

        # Observação interna — amarelo
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

        # Resposta da equipe Pred.IO — azul escuro (direita)
        elif autor_tipo == "funcionario" or tipo == "resposta_predio":
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

        # Mensagem do cliente — azul claro (esquerda)
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
            novo_status = st.selectbox(
                "Novo status", _STATUS_OPTS,
                index=_STATUS_OPTS.index(str(chamado.get("Status", "Aberto")).strip())
                if str(chamado.get("Status", "Aberto")).strip() in _STATUS_OPTS else 0,
            )
        enviar = st.form_submit_button("📨 Enviar resposta ao cliente",
                                       use_container_width=True, type="primary")

    if enviar and resposta.strip():
        nome = current_nome()
        ok = add_mensagem(
            chamado_id=chamado_id,
            autor=nome,
            autor_tipo="funcionario",
            mensagem=resposta.strip(),
            visivel_cliente=True,
            tipo_mensagem="resposta_predio",
        )
        if ok and atualizar_status and novo_status:
            status_ant = str(chamado.get("Status", "")).strip()
            update_chamado(chamado_id, {"Status": novo_status})
            add_mensagem(
                chamado_id=chamado_id,
                autor="sistema",
                autor_tipo="sistema",
                mensagem=f"Status alterado: {status_ant} → {novo_status}",
                visivel_cliente=True,
                tipo_mensagem="alteracao_status",
            )
        if ok:
            st.success("✅ Resposta enviada com sucesso!")
            st.rerun()
        else:
            st.error("Erro ao enviar. Tente novamente.")


# ── Painel de ações ───────────────────────────────────────────────────────────

def _render_action_panel(chamado_id: str, chamado: dict) -> None:
    status_atual     = str(chamado.get("Status",      "Aberto")).strip()
    prioridade_atual = str(chamado.get("Prioridade",  "Média")).strip()
    responsavel_atual= str(chamado.get("Responsavel", "")).strip()

    # ── Atualizar status / prioridade / responsável ───────────────────────────
    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;'>"
        f"<p style='color:{COLOR_NAVY};font-weight:700;font-size:0.9rem;margin:0 0 0.75rem;'>"
        f"⚙️ Atualizar Chamado</p></div>",
        unsafe_allow_html=True,
    )

    with st.form(f"update_chamado_{chamado_id}"):
        novo_status = st.selectbox(
            "Status",
            _STATUS_OPTS,
            index=_STATUS_OPTS.index(status_atual) if status_atual in _STATUS_OPTS else 0,
        )
        nova_prio = st.selectbox(
            "Prioridade",
            _PRIO_OPTS,
            index=_PRIO_OPTS.index(prioridade_atual) if prioridade_atual in _PRIO_OPTS else 0,
        )
        novo_resp = st.text_input("Responsável", value=responsavel_atual,
                                  placeholder="Nome do técnico responsável")
        salvar = st.form_submit_button("💾 Salvar", use_container_width=True)

    if salvar:
        campos = {}
        msgs_sistema = []

        if novo_status != status_atual:
            campos["Status"] = novo_status
            msgs_sistema.append(f"Status alterado: {status_atual} → {novo_status}")
            if novo_status == "Concluído":
                from datetime import datetime
                campos["Data_Encerramento"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        if nova_prio != prioridade_atual:
            campos["Prioridade"] = nova_prio
            msgs_sistema.append(f"Prioridade alterada: {prioridade_atual} → {nova_prio}")

        if novo_resp.strip() != responsavel_atual:
            campos["Responsavel"] = novo_resp.strip()
            msgs_sistema.append(f"Responsável: {responsavel_atual or 'Nenhum'} → {novo_resp.strip() or 'Nenhum'}")

        if campos:
            ok = update_chamado(chamado_id, campos)
            for msg in msgs_sistema:
                add_mensagem(
                    chamado_id=chamado_id,
                    autor="sistema",
                    autor_tipo="sistema",
                    mensagem=msg,
                    visivel_cliente=True,
                    tipo_mensagem="alteracao_status",
                )
            if ok:
                st.success("Atualizado!")
                st.rerun()
            else:
                st.info("Modo demonstração — alterações não persistidas na planilha.")
                st.rerun()

    # ── Observação interna ────────────────────────────────────────────────────
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='background:#FFFBEB;border:1px solid #FDE68A;"
        f"border-radius:12px;padding:1rem 1.25rem;'>"
        f"<p style='color:#92400E;font-weight:700;font-size:0.9rem;margin:0 0 0.5rem;'>"
        f"🔒 Nota Interna</p>"
        f"<p style='color:#A16207;font-size:0.78rem;margin:0;'>"
        f"Invisível ao cliente</p></div>",
        unsafe_allow_html=True,
    )

    with st.form(f"nota_interna_{chamado_id}", clear_on_submit=True):
        nota = st.text_area(
            "Observação interna",
            placeholder="Anotações técnicas, pendências internas, contexto…",
            height=90, label_visibility="collapsed",
        )
        adicionar = st.form_submit_button("🔒 Adicionar nota interna",
                                          use_container_width=True)

    if adicionar and nota.strip():
        nome = current_nome()
        ok = add_mensagem(
            chamado_id=chamado_id,
            autor=nome,
            autor_tipo="funcionario",
            mensagem=nota.strip(),
            visivel_cliente=False,
            tipo_mensagem="observacao_interna",
        )
        if ok:
            st.success("Nota salva!")
            st.rerun()
        else:
            st.error("Erro ao salvar.")

    # ── Ações rápidas ─────────────────────────────────────────────────────────
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:{COLOR_NAVY};font-weight:700;font-size:0.88rem;"
        f"margin:0 0 0.5rem;'>⚡ Ações Rápidas</p>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if status_atual.lower() != "concluído":
            if st.button("✅ Encerrar", use_container_width=True, key=f"enc_{chamado_id}"):
                from datetime import datetime
                ok = update_chamado(chamado_id, {
                    "Status": "Concluído",
                    "Data_Encerramento": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                })
                add_mensagem(chamado_id, "sistema", "sistema",
                             "Chamado encerrado.", True, "encerramento")
                st.rerun()
    with col_b:
        if status_atual.lower() == "concluído":
            if st.button("🔄 Reabrir", use_container_width=True, key=f"reab_{chamado_id}"):
                update_chamado(chamado_id, {"Status": "Reaberto", "Data_Encerramento": ""})
                add_mensagem(chamado_id, "sistema", "sistema",
                             "Chamado reaberto.", True, "reabertura")
                st.rerun()
