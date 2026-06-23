"""Supervisão — Notificações Externas (e-mail / WhatsApp)."""
import pandas as pd
import streamlit as st
from datetime import datetime
from auth import require_staff, current_nome
from sheets import (
    get_notificacoes, add_notificacao, update_notificacao_status,
    get_all_clientes, get_contatos_notificacao,
)
from ui import sv_page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE

# ── Eventos ───────────────────────────────────────────────────────────────────

_EVENTO_OPCOES = [
    ("report_published",             "📄 Novo relatório publicado"),
    ("critical_alarm",               "🚨 Alarme crítico"),
    ("asset_critical",               "⚠️ Ativo em condição crítica"),
    ("maintenance_due",              "📅 Manutenção próxima do vencimento"),
    ("maintenance_overdue",          "🔴 Manutenção vencida"),
    ("ticket_replied",               "🔧 Chamado respondido pela Pred.IO"),
    ("technical_document_available", "📚 Documento técnico disponível"),
    ("custom",                       "✏️ Mensagem personalizada"),
]

_EVENTO_KEY_BY_LABEL  = {v: k for k, v in _EVENTO_OPCOES}
_EVENTO_LABEL_BY_KEY  = {k: v for k, v in _EVENTO_OPCOES}
_EVENTO_LABEL_BY_KEY["ticket_waiting_customer"] = "⏳ Aguardando cliente"

_TEMPLATES: dict = {
    "report_published": {
        "titulo":    "Pred.IO | Novo relatório técnico disponível",
        "msg_email": "Um novo relatório técnico foi publicado no Portal de Confiabilidade Pred.IO. Acesse com seu login para visualizar o conteúdo completo.",
        "msg_wa":    "Pred.IO | Novo relatório disponível. Acesse o portal: {link}",
        "link":      "/portal/relatorios",
    },
    "critical_alarm": {
        "titulo":    "Pred.IO | Alerta crítico no ativo monitorado",
        "msg_email": "Um ativo monitorado foi sinalizado como condição crítica. Acesse o portal para visualizar detalhes e recomendações técnicas.",
        "msg_wa":    "Pred.IO | Alerta crítico. Verifique no portal: {link}",
        "link":      "/portal/ativos",
    },
    "asset_critical": {
        "titulo":    "Pred.IO | Ativo em condição crítica",
        "msg_email": "Um equipamento monitorado pela Pred.IO foi classificado em condição crítica. Acesse o portal para detalhes.",
        "msg_wa":    "Pred.IO | Ativo crítico. Verifique no portal: {link}",
        "link":      "/portal/ativos",
    },
    "maintenance_due": {
        "titulo":    "Pred.IO | Manutenção próxima do vencimento",
        "msg_email": "Uma tarefa de manutenção preventiva está próxima do vencimento. Acesse o plano de manutenção no portal para detalhes.",
        "msg_wa":    "Pred.IO | Manutenção próxima do vencimento. Acesse: {link}",
        "link":      "/portal/manutencao",
    },
    "maintenance_overdue": {
        "titulo":    "Pred.IO | Manutenção vencida",
        "msg_email": "Uma tarefa de manutenção preventiva está vencida. Providencie o agendamento acessando o plano de manutenção no portal.",
        "msg_wa":    "Pred.IO | Manutenção vencida. Providencie agendamento: {link}",
        "link":      "/portal/manutencao",
    },
    "ticket_replied": {
        "titulo":    "Pred.IO | Chamado respondido",
        "msg_email": "A equipe Pred.IO respondeu um chamado técnico. Acesse o portal para visualizar a resposta e dar continuidade ao atendimento.",
        "msg_wa":    "Pred.IO | Chamado respondido. Acesse o portal: {link}",
        "link":      "/portal/chamados",
    },
    "technical_document_available": {
        "titulo":    "Pred.IO | Documento técnico disponibilizado",
        "msg_email": "Um novo documento técnico foi disponibilizado no Portal de Confiabilidade Pred.IO. Acesse para visualizar.",
        "msg_wa":    "Pred.IO | Novo documento técnico disponível. Acesse: {link}",
        "link":      "/portal/relatorios",
    },
    "custom": {
        "titulo":    "",
        "msg_email": "",
        "msg_wa":    "",
        "link":      "/portal",
    },
}

_STATUS_COR: dict = {
    "Enviado":                 ("#16A34A", "#fff"),
    "Simulado":                ("#6366F1", "#fff"),
    "Pendente":                ("#F59E0B", "#000"),
    "Falhou":                  ("#EF4444", "#fff"),
    "Cancelado":               ("#94A3B8", "#fff"),
    "Ignorado":                ("#94A3B8", "#fff"),
    "Aguardando configuração": ("#0EA5E9", "#fff"),
}

_CANAL_COR: dict = {
    "E-mail":   ("#2563EB", "#fff"),
    "WhatsApp": ("#16A34A", "#fff"),
    "Portal":   ("#0F1F3D", "#fff"),
}


# ═══════════════════════════════════════════════════════════════════════════════
def render() -> None:
    require_staff()
    sv_page_header(
        "📨 Notificações Externas",
        "Envie avisos por e-mail e WhatsApp para contatos dos clientes cadastrados.",
    )

    tab_enviar, tab_log = st.tabs(["📤 Enviar notificação", "📋 Log de envios"])
    with tab_enviar:
        _render_tab_enviar()
    with tab_log:
        _render_tab_log()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: ENVIAR — fluxo em 3 etapas
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_enviar() -> None:
    step = st.session_state.get("_sv_notif_step", 1)
    _render_step_bar(step)
    if step == 1:
        _render_step_compose()
    elif step == 2:
        _render_step_preview()
    else:
        _render_step_result()


def _render_step_bar(step: int) -> None:
    labels = ["1. Configurar", "2. Revisar", "3. Concluído"]
    cols   = st.columns(len(labels))
    for i, (col, lbl) in enumerate(zip(cols, labels), start=1):
        done   = i < step
        active = i == step
        bg = COLOR_BLUE if active else ("#16A34A" if done else "#E2E8F0")
        tc = "#fff" if (active or done) else "#64748B"
        col.markdown(
            f"<div style='background:{bg};color:{tc};-webkit-text-fill-color:{tc};"
            f"text-align:center;padding:6px 4px;border-radius:8px;"
            f"font-size:0.78rem;font-weight:700;'>"
            f"{'✓ ' if done else ''}{lbl}</div>",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)


# ─── Etapa 1: Configurar ──────────────────────────────────────────────────────

def _render_step_compose() -> None:
    # ── 1. Clientes ──────────────────────────────────────────────────────────
    _label("1. Clientes destinatários")
    df_cli = get_all_clientes()

    if df_cli.empty or "Empresa" not in df_cli.columns:
        st.warning("Nenhum cliente cadastrado. Cadastre clientes antes de enviar notificações.")
        return

    # Monta mapa nome → {id, nome}
    mapa_cli: dict = {}
    for _, r in df_cli.iterrows():
        nome = str(r.get("Empresa", "")).strip()
        cid  = str(r.get("Client_Id", "")).strip() or nome.lower()
        if nome:
            mapa_cli[nome] = {"id": cid, "nome": nome}

    sel_nomes: list = st.multiselect(
        "Clientes",
        options=list(mapa_cli.keys()),
        default=st.session_state.get("_sv_notif_cli_sel", []),
        placeholder="Pesquise e selecione clientes...",
        label_visibility="collapsed",
    )
    st.session_state["_sv_notif_cli_sel"] = sel_nomes

    if not sel_nomes:
        st.info("Selecione ao menos um cliente para continuar.")
        return

    sel_clientes = [mapa_cli[n] for n in sel_nomes if n in mapa_cli]

    # ── 2. Tipo de evento (fora do form para permitir auto-fill) ─────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _label("2. Tipo de notificação")

    prev_evt = st.session_state.get("_sv_notif_evt_prev", "")
    evt_label = st.selectbox(
        "Tipo",
        [v for _, v in _EVENTO_OPCOES],
        key="_sv_notif_evt_label",
        label_visibility="collapsed",
    )
    evt_key = _EVENTO_KEY_BY_LABEL.get(evt_label, "custom")
    tpl = _TEMPLATES[evt_key]

    # Auto-fill quando tipo muda ou primeira renderização
    if prev_evt != evt_key:
        st.session_state["_sv_notif_evt_prev"] = evt_key
        st.session_state["_sv_n_titulo"]    = tpl["titulo"]
        st.session_state["_sv_n_msg_email"] = tpl["msg_email"]
        st.session_state["_sv_n_msg_wa"]    = tpl["msg_wa"]
        st.session_state["_sv_n_link"]      = tpl["link"]

    # Inicializa chaves se primeira visita
    for k, v in [("_sv_n_titulo",    tpl["titulo"]),
                 ("_sv_n_msg_email", tpl["msg_email"]),
                 ("_sv_n_msg_wa",    tpl["msg_wa"]),
                 ("_sv_n_link",      tpl["link"])]:
        if k not in st.session_state:
            st.session_state[k] = v

    # ── 3. Contatos por cliente ───────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _label("3. Contatos destinatários")

    contatos_por_cli: dict = {}
    for cli in sel_clientes:
        contatos = get_contatos_notificacao(cli["id"])
        contatos_por_cli[cli["id"]] = {"cli": cli, "contatos": contatos}
        # Inicializar chaves de checkbox (sem sobrescrever seleções existentes)
        for c in contatos:
            ek = f"_nc_e_{cli['id']}_{c['id']}"
            wk = f"_nc_w_{cli['id']}_{c['id']}"
            if ek not in st.session_state:
                st.session_state[ek] = c["tem_email"]
            if wk not in st.session_state:
                st.session_state[wk] = c["tem_whatsapp"]

    has_any_contact = any(d["contatos"] for d in contatos_por_cli.values())

    # Botão "Selecionar todos"
    if has_any_contact:
        col_sa, _ = st.columns([2, 6])
        with col_sa:
            if st.button("☑️ Selecionar todos", key="_sv_notif_sel_all"):
                for cid, data in contatos_por_cli.items():
                    for c in data["contatos"]:
                        if c["tem_email"]:
                            st.session_state[f"_nc_e_{cid}_{c['id']}"] = True
                        if c["tem_whatsapp"]:
                            st.session_state[f"_nc_w_{cid}_{c['id']}"] = True
                st.rerun()

    if not has_any_contact:
        st.warning(
            "Nenhum contato com preferências cadastradas foi encontrado para os clientes selecionados. "
            "Solicite ao cliente que configure suas preferências em Configurações do portal."
        )
        return

    # ── Formulário principal ─────────────────────────────────────────────────
    with st.form("_sv_notif_form_compose"):

        for cid, data in contatos_por_cli.items():
            cli      = data["cli"]
            contatos = data["contatos"]

            st.markdown(
                f"<div style='background:#F8FAFC;border:1px solid {COLOR_BORDER};"
                f"border-left:3px solid {COLOR_BLUE};border-radius:8px;"
                f"padding:10px 14px;margin-bottom:6px;'>"
                f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.85rem;margin:0;'>"
                f"🏢 {cli['nome']}</p></div>",
                unsafe_allow_html=True,
            )

            if not contatos:
                st.caption("Nenhum contato com preferências cadastradas para este cliente.")
                continue

            # Cabeçalho das colunas
            h1, h2, h3, h4 = st.columns([2.5, 3.5, 1.5, 1.5])
            h1.markdown(f"<p style='font-size:0.72rem;color:{COLOR_MUTED};font-weight:600;margin:0;'>NOME</p>", unsafe_allow_html=True)
            h2.markdown(f"<p style='font-size:0.72rem;color:{COLOR_MUTED};font-weight:600;margin:0;'>CONTATO</p>", unsafe_allow_html=True)
            h3.markdown(f"<p style='font-size:0.72rem;color:{COLOR_MUTED};font-weight:600;margin:0;'>E-MAIL</p>", unsafe_allow_html=True)
            h4.markdown(f"<p style='font-size:0.72rem;color:{COLOR_MUTED};font-weight:600;margin:0;'>WHATSAPP</p>", unsafe_allow_html=True)

            for c in contatos:
                ek   = f"_nc_e_{cid}_{c['id']}"
                wk   = f"_nc_w_{cid}_{c['id']}"
                nome = c["nome"] or c["usuario_id"] or "—"
                em   = c["email"]    or "—"
                wa   = c["whatsapp"] or "—"

                col1, col2, col3, col4 = st.columns([2.5, 3.5, 1.5, 1.5])
                with col1:
                    st.markdown(
                        f"<p style='font-size:0.83rem;font-weight:600;color:#334155;"
                        f"margin:6px 0 0;'>{nome}</p>",
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.markdown(
                        f"<p style='font-size:0.72rem;color:{COLOR_MUTED};margin:7px 0 0;'>"
                        f"📧 {em}<br>📲 {wa}</p>",
                        unsafe_allow_html=True,
                    )
                with col3:
                    st.checkbox(
                        "E-mail",
                        key=ek,
                        disabled=not c["tem_email"],
                        label_visibility="collapsed",
                    )
                    if not c["tem_email"]:
                        st.caption("Sem e-mail")
                with col4:
                    st.checkbox(
                        "WhatsApp",
                        key=wk,
                        disabled=not c["tem_whatsapp"],
                        label_visibility="collapsed",
                    )
                    if not c["tem_whatsapp"]:
                        st.caption("Sem número")

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        st.markdown(
            f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0;'/>",
            unsafe_allow_html=True,
        )

        # Mensagem
        _label_md("4. Mensagem")
        titulo    = st.text_input("Título *", key="_sv_n_titulo",
                                  placeholder="Ex: Pred.IO | Novo relatório disponível")
        msg_email = st.text_area("Mensagem completa (E-mail)", key="_sv_n_msg_email",
                                 height=80,
                                 help="Conteúdo completo enviado por e-mail.")
        msg_wa    = st.text_area("Mensagem resumida (WhatsApp)", key="_sv_n_msg_wa",
                                 height=60,
                                 help="Resumo + link. Nunca conteúdo técnico completo.")
        link      = st.text_input("Link do portal", key="_sv_n_link",
                                  placeholder="Ex: /portal/relatorios",
                                  help="O cliente precisará fazer login para acessar.")

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button(
            "Próximo: Revisar →", type="primary", use_container_width=True
        )

    if submitted:
        _processar_compose(contatos_por_cli, evt_key, evt_label)


def _processar_compose(contatos_por_cli: dict, evt_key: str, evt_label: str) -> None:
    """Valida e empacota dados do formulário para a etapa de preview."""
    titulo    = st.session_state.get("_sv_n_titulo",    "").strip()
    msg_email = st.session_state.get("_sv_n_msg_email", "").strip()
    msg_wa    = st.session_state.get("_sv_n_msg_wa",    "").strip()
    link      = st.session_state.get("_sv_n_link",      "").strip()

    erros: list = []
    if not titulo:
        erros.append("Informe o título da notificação.")
    if not msg_email and not msg_wa:
        erros.append("Preencha ao menos uma mensagem (E-mail ou WhatsApp).")

    # Coletar destinatários selecionados por cliente
    # SECURITY: cada cliente recebe apenas seus próprios contatos
    destins_por_cli: dict = {}
    for cid, data in contatos_por_cli.items():
        cli      = data["cli"]
        contatos = data["contatos"]
        sel: list = []
        for c in contatos:
            quer_email = bool(st.session_state.get(f"_nc_e_{cid}_{c['id']}", False) and c["tem_email"])
            quer_wa    = bool(st.session_state.get(f"_nc_w_{cid}_{c['id']}", False) and c["tem_whatsapp"])
            if quer_email or quer_wa:
                sel.append({**c, "quer_email": quer_email, "quer_wa": quer_wa})
        if sel:
            destins_por_cli[cid] = {"cli": cli, "contatos": sel}

    if not destins_por_cli:
        erros.append("Selecione ao menos um contato e um canal de envio.")

    if erros:
        for e in erros:
            st.warning(e)
        return

    st.session_state["_sv_notif_payload"] = {
        "evt_key":         evt_key,
        "evt_label":       evt_label,
        "titulo":          titulo,
        "msg_email":       msg_email,
        "msg_wa":          msg_wa,
        "link":            link,
        "destins_por_cli": destins_por_cli,
    }
    st.session_state["_sv_notif_step"] = 2
    st.rerun()


# ─── Etapa 2: Revisar ────────────────────────────────────────────────────────

def _render_step_preview() -> None:
    payload = st.session_state.get("_sv_notif_payload")
    if not payload:
        st.session_state["_sv_notif_step"] = 1
        st.rerun()
        return

    destins = payload["destins_por_cli"]
    n_cli   = len(destins)
    n_dest  = sum(len(d["contatos"]) for d in destins.values())

    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0 0 0.5rem;'>"
        f"📋 Pré-visualização — {n_cli} cliente(s) · {n_dest} destinatário(s)</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;"
        "padding:10px 14px;margin-bottom:1rem;'>"
        "<p style='margin:0;font-size:0.82rem;color:#92400E;'>"
        "🔒 Confirme se os destinatários estão corretos. Cada cliente receberá "
        "apenas seus próprios contatos — nunca informações de outro cliente.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    link_final = payload["link"]
    msg_wa_fin = payload["msg_wa"].replace("{link}", link_final)

    for cid, data in destins.items():
        cli      = data["cli"]
        contatos = data["contatos"]

        with st.expander(f"🏢 {cli['nome']}  —  {len(contatos)} destinatário(s)", expanded=True):
            dest_lines = ""
            for c in contatos:
                canais = []
                if c["quer_email"]:
                    canais.append("📧 E-mail")
                if c["quer_wa"]:
                    canais.append("📲 WhatsApp")
                dest_lines += (
                    f"<p style='font-size:0.82rem;color:#334155;margin:0 0 3px;'>"
                    f"• <strong>{c['nome']}</strong> — {' + '.join(canais)}</p>"
                )

            msg_email_preview = payload["msg_email"] or "—"
            msg_wa_preview    = msg_wa_fin or "—"

            st.markdown(
                f"<p style='font-size:0.8rem;font-weight:600;color:{COLOR_NAVY};margin:0 0 4px;'>Destinatários:</p>"
                f"{dest_lines}"
                f"<div style='margin-top:8px;background:#F8FAFC;border:1px solid {COLOR_BORDER};"
                f"border-radius:6px;padding:8px 12px;'>"
                f"<p style='font-size:0.72rem;font-weight:700;color:#0F1F3D;margin:0 0 4px;'>"
                f"{payload['titulo']}</p>"
                f"<p style='font-size:0.76rem;color:#475569;margin:0;'>📧 {msg_email_preview}</p>"
                f"</div>"
                f"<div style='margin-top:6px;background:#F0FDF4;border:1px solid #BBF7D0;"
                f"border-radius:6px;padding:8px 12px;'>"
                f"<p style='font-size:0.76rem;color:#166534;margin:0;'>📲 {msg_wa_preview}</p>"
                f"</div>"
                f"<p style='font-size:0.72rem;color:{COLOR_MUTED};margin:4px 0 0;'>🔗 {link_final}</p>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    col_ok, col_back = st.columns(2)
    with col_ok:
        if st.button("✅ Confirmar simulação de envio", type="primary", use_container_width=True):
            result = _executar_simulacao(payload)
            st.session_state["_sv_notif_resultado"] = result
            st.session_state["_sv_notif_step"] = 3
            st.rerun()
    with col_back:
        if st.button("← Voltar e editar", use_container_width=True):
            st.session_state["_sv_notif_step"] = 1
            st.rerun()


# ─── Etapa 3: Resultado ──────────────────────────────────────────────────────

def _render_step_result() -> None:
    result = st.session_state.get("_sv_notif_resultado", {})

    n_cli  = result.get("n_clientes",  0)
    n_dest = result.get("n_destins",   0)
    n_reg  = result.get("n_registros", 0)
    ids    = result.get("ids_criados", [])

    st.success(
        f"Notificações simuladas com sucesso para **{n_cli} cliente(s)** "
        f"e **{n_dest} destinatário(s)** — **{n_reg} registro(s)** criados no log."
    )
    st.caption(
        "Os registros aparecem na aba **📋 Log de envios** com status **Simulado**. "
        "Quando a integração real estiver ativa (n8n / API), o status será alterado para Enviado."
    )
    if ids:
        st.caption("IDs criados: " + ", ".join(ids[:12]) + (" ..." if len(ids) > 12 else ""))

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("📨 Enviar nova notificação", use_container_width=True):
        for k in ["_sv_notif_step", "_sv_notif_payload", "_sv_notif_resultado",
                  "_sv_notif_cli_sel", "_sv_notif_evt_prev", "_sv_notif_evt_label"]:
            st.session_state.pop(k, None)
        st.rerun()


# ─── Lógica de simulação ─────────────────────────────────────────────────────

def _executar_simulacao(payload: dict) -> dict:
    """Cria registros no Google Sheets com status='Simulado'.

    SECURITY:
    - Cada registro usa o client_id correto do respectivo cliente.
    - WhatsApp recebe apenas mensagem resumida (nunca conteúdo técnico completo).
    - Observações internas não são incluídas.
    - Nunca mistura contatos de clientes diferentes.
    """
    enviado_por = current_nome() or "Staff Pred.IO"
    now         = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    destins     = payload["destins_por_cli"]
    link        = payload["link"]
    msg_wa_fin  = payload["msg_wa"].replace("{link}", link)

    ids_criados: list = []
    n_clientes  = 0
    n_destins   = 0

    for cid, data in destins.items():
        cli      = data["cli"]
        contatos = data["contatos"]
        n_clientes += 1

        for c in contatos:
            n_destins += 1

            if c["quer_email"]:
                nid = add_notificacao({
                    "cliente_id":            cid,
                    "cliente_nome":          cli["nome"],
                    "usuario_id":            c["usuario_id"],
                    "usuario_nome":          c["nome"],
                    "email_destinatario":    c["email"],
                    "whatsapp_destinatario": "",
                    "evento_tipo":           payload["evt_key"],
                    "canal":                 "E-mail",
                    "titulo":                payload["titulo"],
                    "mensagem":              payload["msg_email"],
                    "link_portal":           link,
                    "status":                "Simulado",
                    "enviado_por":           enviado_por,
                    "enviado_em":            now,
                })
                if nid:
                    ids_criados.append(nid)

            if c["quer_wa"]:
                nid = add_notificacao({
                    "cliente_id":            cid,
                    "cliente_nome":          cli["nome"],
                    "usuario_id":            c["usuario_id"],
                    "usuario_nome":          c["nome"],
                    "email_destinatario":    "",
                    "whatsapp_destinatario": c["whatsapp"],
                    "evento_tipo":           payload["evt_key"],
                    "canal":                 "WhatsApp",
                    "titulo":                payload["titulo"],
                    # SECURITY: WhatsApp sempre recebe mensagem resumida + link
                    "mensagem":              msg_wa_fin,
                    "link_portal":           link,
                    "status":                "Simulado",
                    "enviado_por":           enviado_por,
                    "enviado_em":            now,
                })
                if nid:
                    ids_criados.append(nid)

    return {
        "n_clientes":  n_clientes,
        "n_destins":   n_destins,
        "n_registros": len(ids_criados),
        "ids_criados": ids_criados,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TAB: LOG
# ─────────────────────────────────────────────────────────────────────────────

_MOCK_LOG = [
    {
        "Id": "NOTIF-DEMO-001", "Cliente_Id": "demo-client",
        "Cliente_Nome": "Empresa Demo", "Usuario_Id": "contato@empresa.com",
        "Usuario_Nome": "João Silva", "Email_Destinatario": "contato@empresa.com",
        "Whatsapp_Destinatario": "", "Evento_Tipo": "report_published",
        "Canal": "E-mail", "Titulo": "Novo relatório técnico disponível",
        "Mensagem": "Análise Preditiva — Junho/2026 publicada no portal.",
        "Link_Portal": "/portal/relatorios", "Status": "Simulado",
        "Tentativas": "1", "Erro": "", "Enviado_Por": "Staff Pred.IO",
        "Enviado_Em": "23/06/2026 09:30", "Created_At": "23/06/2026 09:28",
    },
    {
        "Id": "NOTIF-DEMO-002", "Cliente_Id": "demo-client",
        "Cliente_Nome": "Empresa Demo", "Usuario_Id": "contato@empresa.com",
        "Usuario_Nome": "Maria Souza", "Email_Destinatario": "",
        "Whatsapp_Destinatario": "+55 21 99999-9999", "Evento_Tipo": "critical_alarm",
        "Canal": "WhatsApp", "Titulo": "Alerta crítico no ativo monitorado",
        "Mensagem": "Pred.IO | Alerta crítico. Verifique no portal: /portal/ativos",
        "Link_Portal": "/portal/ativos", "Status": "Pendente",
        "Tentativas": "0", "Erro": "", "Enviado_Por": "Staff Pred.IO",
        "Enviado_Em": "", "Created_At": "23/06/2026 10:15",
    },
    {
        "Id": "NOTIF-DEMO-003", "Cliente_Id": "demo-client-2",
        "Cliente_Nome": "Empresa Beta", "Usuario_Id": "ops@beta.com",
        "Usuario_Nome": "Carlos Andrade", "Email_Destinatario": "ops@beta.com",
        "Whatsapp_Destinatario": "", "Evento_Tipo": "maintenance_overdue",
        "Canal": "E-mail", "Titulo": "Pred.IO | Manutenção vencida",
        "Mensagem": "Uma tarefa de manutenção preventiva está vencida. Acesse o portal.",
        "Link_Portal": "/portal/manutencao", "Status": "Pendente",
        "Tentativas": "0", "Erro": "", "Enviado_Por": "Staff Pred.IO",
        "Enviado_Em": "", "Created_At": "23/06/2026 11:00",
    },
]


def _render_tab_log() -> None:
    df_real   = get_notificacoes()
    using_mock = df_real.empty

    if using_mock:
        st.caption("💡 Exibindo dados de demonstração. Notificações reais aparecem após a primeira simulação.")
        df = _get_mock_df()
    else:
        df = df_real

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        f_status = st.selectbox(
            "Status",
            ["Todos", "Simulado", "Pendente", "Enviado", "Falhou", "Cancelado"],
            key="_sv_log_status",
        )
    with col_f2:
        f_canal = st.selectbox(
            "Canal",
            ["Todos", "E-mail", "WhatsApp"],
            key="_sv_log_canal",
        )
    with col_f3:
        evt_opts = ["Todos"] + [v for _, v in _EVENTO_OPCOES]
        f_evt = st.selectbox("Tipo de evento", evt_opts, key="_sv_log_evt")

    st.markdown(f"<hr style='border-color:{COLOR_BORDER};margin:0.5rem 0 1rem;'/>", unsafe_allow_html=True)

    df_f = df.copy()
    if f_status != "Todos":
        df_f = df_f[df_f["Status"].astype(str).str.strip() == f_status]
    if f_canal != "Todos":
        df_f = df_f[df_f["Canal"].astype(str).str.strip() == f_canal]
    if f_evt != "Todos":
        ek = _EVENTO_KEY_BY_LABEL.get(f_evt)
        if ek:
            df_f = df_f[df_f["Evento_Tipo"].astype(str).str.strip() == ek]

    total   = len(df_f)
    sim     = len(df_f[df_f["Status"].astype(str).str.strip() == "Simulado"])
    pend    = len(df_f[df_f["Status"].astype(str).str.strip() == "Pendente"])
    env     = len(df_f[df_f["Status"].astype(str).str.strip() == "Enviado"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total",     total)
    m2.metric("Simulados", sim)
    m3.metric("Pendentes", pend)
    m4.metric("Enviados",  env)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if df_f.empty:
        st.info("Nenhum registro encontrado com os filtros selecionados.")
        return

    for _, row in df_f.iterrows():
        _render_log_card(row, using_mock)


def _get_mock_df() -> pd.DataFrame:
    overrides = st.session_state.get("_sv_notif_mock_status", {})
    rows = []
    for r in _MOCK_LOG:
        r2 = dict(r)
        if r2["Id"] in overrides:
            r2["Status"] = overrides[r2["Id"]]
            if overrides[r2["Id"]] == "Enviado":
                r2["Enviado_Em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        rows.append(r2)
    return pd.DataFrame(rows)


def _render_log_card(row, using_mock: bool) -> None:
    notif_id    = str(row.get("Id",                    "")).strip()
    cli_nome    = str(row.get("Cliente_Nome",           row.get("Cliente_Id", ""))).strip()
    dest_nome   = str(row.get("Usuario_Nome",           row.get("Usuario_Id", ""))).strip()
    canal       = str(row.get("Canal",                 "")).strip()
    titulo      = str(row.get("Titulo",                "")).strip()
    mensagem    = str(row.get("Mensagem",              "")).strip()
    link        = str(row.get("Link_Portal",           "")).strip()
    status      = str(row.get("Status",                "Pendente")).strip()
    tentativas  = str(row.get("Tentativas",            "0")).strip()
    erro        = str(row.get("Erro",                  "")).strip()
    enviado_em  = str(row.get("Enviado_Em",            "")).strip()
    criado_em   = str(row.get("Created_At",            "")).strip()[:16]
    enviado_por = str(row.get("Enviado_Por",           "")).strip()
    evento      = str(row.get("Evento_Tipo",           "")).strip()

    evt_lbl     = _EVENTO_LABEL_BY_KEY.get(evento, evento)
    border_col  = (
        "#F59E0B" if status == "Pendente"
        else "#16A34A" if status == "Enviado"
        else "#6366F1" if status == "Simulado"
        else "#EF4444"
    )
    is_pending  = status in ("Pendente",)

    col_main, col_act = st.columns([11, 1.4])

    with col_main:
        with st.expander(
            f"🏢 {cli_nome}  ·  {dest_nome}  ·  {canal}  ·  {titulo[:45]}  ·  {status}",
            expanded=False,
        ):
            extras = ""
            if enviado_em:
                extras += f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>✅ Enviado: {enviado_em}</p>"
            if tentativas not in ("0", ""):
                extras += f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>🔁 Tentativas: {tentativas}</p>"
            if erro:
                extras += f"<p style='color:#EF4444;font-size:0.72rem;margin:0;'>❌ Erro: {erro}</p>"
            if enviado_por:
                extras += f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>👤 Enviado por: {enviado_por}</p>"

            st.markdown(
                f"<div style='background:{COLOR_CARD};border-left:4px solid {border_col};"
                f"border-radius:0 8px 8px 0;padding:12px 16px;'>"
                f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;'>"
                f"{_badge(canal, _CANAL_COR, '#2563EB')}"
                f"{_badge(status, _STATUS_COR)}"
                f"<span style='background:#EFF6FF;color:#1E40AF;-webkit-text-fill-color:#1E40AF;"
                f"font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:20px;"
                f"border:1px solid #BFDBFE;'>{evt_lbl}</span>"
                f"</div>"
                f"<p style='color:#334155;font-size:0.83rem;margin:0 0 8px;'>{mensagem}</p>"
                f"<div style='display:flex;flex-wrap:wrap;gap:16px;'>"
                f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>📅 Criado: {criado_em}</p>"
                f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>🔗 {link}</p>"
                f"{extras}"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    with col_act:
        if is_pending:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            if st.button(
                "📤 Simular",
                key=f"_sv_sim_{notif_id}",
                use_container_width=True,
                help="Simula o envio — status muda para Enviado",
            ):
                if using_mock:
                    ov = st.session_state.setdefault("_sv_notif_mock_status", {})
                    ov[notif_id] = "Enviado"
                    st.toast("✅ Envio simulado!", icon="📤")
                else:
                    ok = update_notificacao_status(
                        notif_id, "Enviado",
                        enviado_em=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    )
                    st.toast("✅ Status atualizado." if ok else "⚠️ Não foi possível atualizar.",
                             icon="📤" if ok else "⚠️")
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers visuais
# ─────────────────────────────────────────────────────────────────────────────

def _badge(text: str, color_map: dict, default_bg: str = "#64748B") -> str:
    bg, tc = color_map.get(text, (default_bg, "#fff"))
    return (
        f"<span style='background:{bg};color:{tc};-webkit-text-fill-color:{tc};"
        f"font-size:0.7rem;font-weight:700;padding:2px 10px;border-radius:20px;"
        f"white-space:nowrap;'>{text}</span>"
    )


def _label(text: str) -> None:
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;margin:0 0 4px;'>{text}</p>",
        unsafe_allow_html=True,
    )


def _label_md(text: str) -> None:
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;margin:0.5rem 0 4px;'>{text}</p>",
        unsafe_allow_html=True,
    )
