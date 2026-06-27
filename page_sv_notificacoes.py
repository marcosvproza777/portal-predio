"""Supervisão — Notificações: Templates, Fila, Sandbox e Log."""
import pandas as pd
import streamlit as st
from datetime import datetime
from auth import require_staff, current_nome
from sheets import (
    get_notificacoes, add_notificacao, update_notificacao_status,
    get_all_clientes, get_contatos_notificacao,
)
from ui import sv_page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE

COLOR_GREEN = "#10B981"
COLOR_WARN  = "#F59E0B"
COLOR_RED   = "#EF4444"

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
        "📨 Notificações",
        "Gerencie notificações do portal e envios por e-mail / WhatsApp.",
    )

    tab_enviar, tab_log, tab_portal, tab_prefs, tab_tpl, tab_fila, tab_sandbox = st.tabs([
        "📤 Enviar notificação",
        "📋 Log de envios",
        "📊 Notificações Portal",
        "⚙️ Preferências por Cliente",
        "📝 Templates",
        "📋 Fila",
        "🧪 Sandbox",
    ])
    with tab_enviar:
        _render_tab_enviar()
    with tab_log:
        _render_tab_log()
    with tab_portal:
        _render_tab_portal()
    with tab_prefs:
        _render_tab_prefs_cliente()
    with tab_tpl:
        _render_tab_templates()
    with tab_fila:
        _render_tab_fila()
    with tab_sandbox:
        _render_tab_sandbox()


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


# ─────────────────────────────────────────────────────────────────────────────
# TAB: NOTIFICAÇÕES PORTAL — visão supervisor de todas as notificações internas
# ─────────────────────────────────────────────────────────────────────────────

_PRIO_COR_SV: dict = {
    "Baixa":   ("#6366F1", "#EEF2FF"),
    "Média":   ("#F59E0B", "#FFFBEB"),
    "Media":   ("#F59E0B", "#FFFBEB"),
    "Alta":    ("#EF4444", "#FEF2F2"),
    "Crítica": ("#7C3AED", "#F5F3FF"),
    "Critica": ("#7C3AED", "#F5F3FF"),
}

_STATUS_PORTAL_COR: dict = {
    "Não lida": ("#EF4444", "#fff"),
    "nao_lida": ("#EF4444", "#fff"),
    "Lida":     ("#16A34A", "#fff"),
    "lida":     ("#16A34A", "#fff"),
}


def _render_tab_portal() -> None:
    from sheets import load_sheet

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin-bottom:0.75rem;'>"
        "Visão consolidada de todas as notificações internas geradas para clientes.</p>",
        unsafe_allow_html=True,
    )

    # Carrega NotificacoesPortal
    try:
        df = load_sheet("NotificacoesPortal", ttl=30)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.info("Nenhuma notificação de portal registrada ainda.")
        return

    # Normaliza colunas
    df.columns = [str(c).strip() for c in df.columns]

    # Filtros
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        cli_opts = ["Todos"] + sorted(df.get("Cliente_Id", pd.Series(dtype=str)).dropna().unique().tolist())
        f_cli = st.selectbox("Cliente", cli_opts, key="_sv_np_cli")
    with col_f2:
        prio_opts = ["Todas", "Crítica", "Alta", "Média", "Baixa"]
        f_prio = st.selectbox("Prioridade", prio_opts, key="_sv_np_prio")
    with col_f3:
        st_opts = ["Todos", "Não lida", "Lida"]
        f_st = st.selectbox("Status", st_opts, key="_sv_np_status")
    with col_f4:
        ev_col = df.get("Tipo_Evento", pd.Series(dtype=str))
        ev_opts = ["Todos"] + sorted(ev_col.dropna().unique().tolist())
        f_ev = st.selectbox("Tipo de evento", ev_opts, key="_sv_np_ev")

    df_f = df.copy()
    if "Cliente_Id" in df_f.columns and f_cli != "Todos":
        df_f = df_f[df_f["Cliente_Id"].astype(str).str.strip() == f_cli]
    if "Prioridade" in df_f.columns and f_prio != "Todas":
        df_f = df_f[df_f["Prioridade"].astype(str).str.strip() == f_prio]
    if "Status" in df_f.columns and f_st != "Todos":
        df_f = df_f[df_f["Status"].astype(str).str.strip().str.lower() == f_st.lower()]
    if "Tipo_Evento" in df_f.columns and f_ev != "Todos":
        df_f = df_f[df_f["Tipo_Evento"].astype(str).str.strip() == f_ev]

    total   = len(df_f)
    nao_lid = (df_f.get("Status", pd.Series(dtype=str)).astype(str).str.lower().isin(["não lida", "nao_lida"]).sum()
               if "Status" in df_f.columns else 0)

    m1, m2 = st.columns(2)
    m1.metric("Total filtrado", total)
    m2.metric("Não lidas",      nao_lid)
    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:0.5rem 0 1rem;'/>",
        unsafe_allow_html=True,
    )

    if df_f.empty:
        st.info("Nenhuma notificação com os filtros selecionados.")
        return

    for _, row in df_f.head(80).iterrows():
        _render_portal_notif_sv(row)


def _render_portal_notif_sv(row) -> None:
    cli_id   = str(row.get("Cliente_Id",   "")).strip()
    titulo   = str(row.get("Titulo",       "")).strip() or "—"
    mensagem = str(row.get("Mensagem",     "")).strip()
    prio     = str(row.get("Prioridade",   "Baixa")).strip()
    status   = str(row.get("Status",       "")).strip()
    evento   = str(row.get("Tipo_Evento",  "")).strip()
    criado   = str(row.get("Created_At",   "")).strip()[:16]
    lida_em  = str(row.get("Lida_Em",      "")).strip()[:16]

    tc, bg = _PRIO_COR_SV.get(prio, ("#64748B", "#F8FAFC"))
    s_bg, s_tc = _STATUS_PORTAL_COR.get(status, ("#94A3B8", "#fff"))

    st.markdown(
        f"<div style='background:{bg};border:1px solid {COLOR_BORDER};"
        f"border-left:4px solid {tc};border-radius:8px;"
        f"padding:10px 14px;margin-bottom:6px;'>"
        f"<div style='display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px;"
        f"margin-bottom:4px;'>"
        f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.85rem;'>{titulo}</span>"
        f"<div style='display:flex;gap:6px;'>"
        f"<span style='background:{tc};color:#fff;-webkit-text-fill-color:#fff;"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:12px;'>{prio}</span>"
        f"<span style='background:{s_bg};color:{s_tc};-webkit-text-fill-color:{s_tc};"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:12px;'>{status}</span>"
        f"</div></div>"
        f"<p style='color:#475569;font-size:0.8rem;margin:0 0 4px;'>{mensagem}</p>"
        f"<div style='display:flex;gap:16px;flex-wrap:wrap;'>"
        f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>🏢 {cli_id}</p>"
        f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>📅 {criado}</p>"
        + (f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>✓ Lida: {lida_em}</p>" if lida_em else "")
        + f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>🏷 {evento}</p>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB: PREFERÊNCIAS POR CLIENTE — supervisor edita preferências de evento
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_prefs_cliente() -> None:
    from notifications import EVENTOS, _DEFAULT_EVENT_PREFS
    from sheets import get_all_clientes, get_event_preferences, upsert_event_preference

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin-bottom:0.75rem;'>"
        "Visualize e edite as preferências de notificação por evento de cada cliente.</p>",
        unsafe_allow_html=True,
    )

    df_cli = get_all_clientes()
    if df_cli.empty or "Empresa" not in df_cli.columns:
        st.warning("Nenhum cliente cadastrado.")
        return

    cli_map: dict = {}
    for _, r in df_cli.iterrows():
        nome = str(r.get("Empresa", "")).strip()
        cid  = str(r.get("Client_Id", "")).strip()
        if nome and cid:
            cli_map[nome] = cid

    if not cli_map:
        st.warning("Nenhum cliente com ID cadastrado.")
        return

    cli_sel = st.selectbox(
        "Cliente",
        list(cli_map.keys()),
        key="_sv_prefs_cli_sel",
    )
    client_id = cli_map[cli_sel]
    if not client_id:
        return

    df_prefs = get_event_preferences(client_id)

    # Monta estado atual com fallback nos defaults
    pref_atual: dict = {}
    for ev, default in _DEFAULT_EVENT_PREFS.items():
        pref_atual[ev] = dict(default)
    if not df_prefs.empty:
        for _, row in df_prefs.iterrows():
            ev = str(row.get("Evento", "")).strip()
            if ev in pref_atual:
                def _b(col: str, d: str) -> bool:
                    return str(row.get(col, row.get(d, "true"))).strip().lower() in ("true", "1", "sim")
                pref_atual[ev] = {
                    "canal_portal":      _b("Canal_Portal",   "canal_portal"),
                    "canal_email":       _b("Canal_Email",    "canal_email"),
                    "canal_whatsapp":    _b("Canal_Whatsapp", "canal_whatsapp"),
                    "prioridade_minima": str(row.get("Prioridade_Minima",
                                              row.get("prioridade_minima", "Baixa"))).strip(),
                    "frequencia":        str(row.get("Frequencia",
                                              row.get("frequencia", "Imediata"))).strip(),
                    "ativo":             _b("Ativo", "ativo"),
                }

    _freq_opts  = ["Imediata", "Diária", "Semanal"]
    _prio_opts  = ["Baixa", "Média", "Alta", "Crítica"]

    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
        f"margin:0 0 8px;'>Preferências de evento — {cli_sel}</p>",
        unsafe_allow_html=True,
    )

    # Cabeçalho
    h0, h1, h2, h3, h4, h5, h6 = st.columns([3, 1.1, 1.1, 1.1, 1.8, 2, 1.2])
    for col, lbl in zip(
        [h0, h1, h2, h3, h4, h5, h6],
        ["EVENTO", "PORTAL", "E-MAIL", "WHATSAPP", "PRIO. MÍN.", "FREQUÊNCIA", "ATIVO"],
    ):
        col.markdown(
            f"<p style='font-size:0.68rem;font-weight:700;color:{COLOR_MUTED};"
            f"margin:0;text-transform:uppercase;'>{lbl}</p>",
            unsafe_allow_html=True,
        )
    st.markdown(f"<hr style='border-color:{COLOR_BORDER};margin:4px 0 8px;'/>", unsafe_allow_html=True)

    for evento, cfg in EVENTOS.items():
        pref = pref_atual.get(evento, _DEFAULT_EVENT_PREFS.get(evento, {}))
        label = cfg["label"]
        key   = f"_svpref_{client_id}_{evento}"

        c0, c1, c2, c3, c4, c5, c6 = st.columns([3, 1.1, 1.1, 1.1, 1.8, 2, 1.2])
        with c0:
            st.markdown(
                f"<p style='font-size:0.82rem;font-weight:600;color:{COLOR_NAVY};"
                f"margin:8px 0 0;'>{label}</p>",
                unsafe_allow_html=True,
            )
        with c1:
            portal_on = st.toggle("P", value=bool(pref.get("canal_portal", True)),
                                  key=f"{key}_p", label_visibility="collapsed")
        with c2:
            email_on = st.toggle("E", value=bool(pref.get("canal_email", False)),
                                 key=f"{key}_e", label_visibility="collapsed",
                                 disabled=True, help="E-mail — etapa futura")
        with c3:
            wa_on = st.toggle("W", value=bool(pref.get("canal_whatsapp", False)),
                              key=f"{key}_w", label_visibility="collapsed",
                              disabled=True, help="WhatsApp — etapa futura")
        with c4:
            pv = pref.get("prioridade_minima", "Baixa")
            if pv not in _prio_opts:
                pv = "Baixa"
            prio = st.selectbox("pr", _prio_opts, index=_prio_opts.index(pv),
                                key=f"{key}_pr", label_visibility="collapsed")
        with c5:
            fv = pref.get("frequencia", "Imediata")
            if fv not in _freq_opts:
                fv = "Imediata"
            freq = st.selectbox("fr", _freq_opts, index=_freq_opts.index(fv),
                                key=f"{key}_fr", label_visibility="collapsed")
        with c6:
            ativo = st.toggle("A", value=bool(pref.get("ativo", True)),
                              key=f"{key}_a", label_visibility="collapsed")
            if st.button("💾", key=f"{key}_save", use_container_width=True,
                         help=f"Salvar: {label}"):
                ok = upsert_event_preference(client_id, evento, {
                    "canal_portal":    portal_on,
                    "canal_email":     False,
                    "canal_whatsapp":  False,
                    "prioridade_minima": prio,
                    "frequencia":      freq,
                    "ativo":           ativo,
                })
                st.toast(f"✅ Salvo: {label}" if ok else "⚠️ Erro ao salvar.", icon="⚙️")
                if ok:
                    st.rerun()

        st.markdown(
            f"<hr style='border-color:{COLOR_BORDER};margin:4px 0;opacity:.5;'/>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: TEMPLATES — gerenciar templates de notificação
# ═══════════════════════════════════════════════════════════════════════════════

_TIPO_EVENTO_OPCOES = [
    "relatorio_publicado", "relatorio_critico", "ativo_critico",
    "manutencao_vencida", "manutencao_proxima", "chamado_respondido",
    "chamado_aguardando_cliente", "alerta_critico",
    "recomendacao_por_condicao", "documento_publicado",
]
_CANAL_OPCOES = ["E-mail", "WhatsApp", "Portal"]
_STATUS_TPL   = ["Rascunho", "Ativo", "Arquivado"]
_VARS_HINT    = "cliente_nome, ativo_nome, tipo_evento, prioridade, resumo, link_portal, data_evento, status, fonte"


def _render_tab_templates() -> None:
    from sheets import (
        get_notification_templates, add_notification_template,
        update_notification_template,
    )
    from notification_engine import DEFAULT_TEMPLATES, seed_default_templates

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin-bottom:0.5rem;'>"
        "Gerencie templates de notificação. Variáveis sensíveis são bloqueadas automaticamente."
        f"<br>Modo atual: <strong style='color:{COLOR_RED};'>NOTIFICATION_EXTERNAL_SEND_ENABLED=false</strong> "
        "— nenhum envio real ocorre.</p>",
        unsafe_allow_html=True,
    )

    df = get_notification_templates()

    # Seed se vazio
    if df.empty:
        col_seed, _ = st.columns([2, 6])
        with col_seed:
            if st.button("🌱 Criar templates padrão", type="primary", use_container_width=True):
                n = seed_default_templates()
                if n > 0:
                    st.success(f"{n} templates padrão criados.")
                    st.rerun()
                else:
                    st.info("Templates já existem ou não foi possível criar.")
        st.info("Nenhum template cadastrado. Clique em 'Criar templates padrão' para começar.")

    # Formulário de criação
    with st.expander("➕ Novo template", expanded=df.empty):
        _render_form_template(None)

    if df.empty:
        return

    # Filtros
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        f_evt = st.selectbox("Tipo de evento", ["Todos"] + _TIPO_EVENTO_OPCOES, key="_tpl_f_evt")
    with cf2:
        f_can = st.selectbox("Canal", ["Todos"] + _CANAL_OPCOES, key="_tpl_f_can")
    with cf3:
        f_st  = st.selectbox("Status", ["Todos"] + _STATUS_TPL, key="_tpl_f_st")

    df_f = df.copy()
    if f_evt != "Todos":
        df_f = df_f[df_f["Tipo_Evento"].str.strip() == f_evt]
    if f_can != "Todos":
        df_f = df_f[df_f["Canal"].str.strip() == f_can]
    if f_st  != "Todos":
        df_f = df_f[df_f["Status"].str.strip() == f_st]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total", len(df))
    m2.metric("Ativos", len(df[df["Status"].str.strip() == "Ativo"]))
    m3.metric("Rascunhos", len(df[df["Status"].str.strip() == "Rascunho"]))
    st.markdown(f"<hr style='border-color:{COLOR_BORDER};margin:0.5rem 0 1rem;'/>", unsafe_allow_html=True)

    if df_f.empty:
        st.info("Nenhum template com os filtros selecionados.")
        return

    for _, row in df_f.iterrows():
        _render_template_card(row)


def _render_template_card(row) -> None:
    from sheets import update_notification_template
    tpl_id   = str(row.get("Id",          "")).strip()
    nome     = str(row.get("Nome",         "Sem nome")).strip()
    tipo_ev  = str(row.get("Tipo_Evento",  "")).strip()
    canal    = str(row.get("Canal",        "")).strip()
    status   = str(row.get("Status",       "Rascunho")).strip()
    assunto  = str(row.get("Assunto",      "")).strip()
    corpo    = str(row.get("Corpo",        "")).strip()
    vars_perm= str(row.get("Variaveis_Permitidas", "")).strip()

    status_colors = {
        "Ativo":     (COLOR_GREEN, "#F0FDF4", "#86EFAC"),
        "Rascunho":  ("#94A3B8",   "#F8FAFC", "#CBD5E1"),
        "Arquivado": ("#64748B",   "#F1F5F9", "#CBD5E1"),
    }
    canal_colors = {
        "E-mail":   (COLOR_BLUE,  "#EFF6FF"),
        "WhatsApp": (COLOR_GREEN, "#F0FDF4"),
        "Portal":   (COLOR_NAVY,  "#EFF6FF"),
    }
    sc, sb, sbo = status_colors.get(status, ("#94A3B8", "#F8FAFC", "#CBD5E1"))
    cc, cb = canal_colors.get(canal, ("#64748B", "#F8FAFC"))

    with st.expander(f"📝 {nome}  ·  {canal}  ·  {tipo_ev}  ·  {status}", expanded=False):
        st.markdown(
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;'>"
            f"<span style='background:{sb};color:{sc};-webkit-text-fill-color:{sc};"
            f"border:1px solid {sbo};font-size:0.7rem;font-weight:700;"
            f"padding:2px 10px;border-radius:12px;'>{status}</span>"
            f"<span style='background:{cb};color:{cc};-webkit-text-fill-color:{cc};"
            f"font-size:0.7rem;font-weight:700;padding:2px 10px;border-radius:12px;"
            f"border:1px solid {cb};'>{canal}</span>"
            f"<span style='background:#EFF6FF;color:{COLOR_NAVY};-webkit-text-fill-color:{COLOR_NAVY};"
            f"font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:12px;"
            f"border:1px solid #BFDBFE;'>{tipo_ev}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if assunto:
            st.markdown(f"**Assunto:** `{assunto}`")
        if corpo:
            st.text_area("Corpo", corpo, height=120, disabled=True, key=f"_tplbody_{tpl_id}")
        if vars_perm:
            st.caption(f"Variáveis permitidas: {vars_perm}")

        col_ed, col_at, col_ar, _ = st.columns([1, 1, 1, 3])
        with col_ed:
            if st.button("✏️ Editar", key=f"_tpl_edit_{tpl_id}", use_container_width=True):
                st.session_state[f"_tpl_editing_{tpl_id}"] = True
                st.rerun()
        with col_at:
            if status != "Ativo":
                if st.button("✅ Ativar", key=f"_tpl_ativ_{tpl_id}", use_container_width=True):
                    ok = update_notification_template(tpl_id, {"Status": "Ativo"})
                    st.toast("Template ativado." if ok else "Erro ao ativar.", icon="✅")
                    if ok:
                        st.rerun()
        with col_ar:
            if status != "Arquivado":
                if st.button("📦 Arquivar", key=f"_tpl_arch_{tpl_id}", use_container_width=True):
                    ok = update_notification_template(tpl_id, {"Status": "Arquivado"})
                    st.toast("Template arquivado." if ok else "Erro.", icon="📦")
                    if ok:
                        st.rerun()

        if st.session_state.get(f"_tpl_editing_{tpl_id}"):
            st.markdown("---")
            _render_form_template(row.to_dict())
            if st.button("❌ Cancelar edição", key=f"_tpl_canceledit_{tpl_id}"):
                st.session_state.pop(f"_tpl_editing_{tpl_id}", None)
                st.rerun()


def _render_form_template(tpl: dict | None) -> None:
    from sheets import add_notification_template, update_notification_template
    editing = tpl is not None
    tpl_id  = str((tpl or {}).get("Id", "")).strip()

    def _d(k: str, default="") -> str:
        return str((tpl or {}).get(k, "")).strip() or default

    with st.form(f"_form_tpl_{tpl_id or 'new'}"):
        c1, c2, c3 = st.columns(3)
        with c1:
            nome = st.text_input("Nome *", value=_d("Nome"), placeholder="Ex: E-mail — Relatório Publicado")
        with c2:
            te_idx = _TIPO_EVENTO_OPCOES.index(_d("Tipo_Evento")) if _d("Tipo_Evento") in _TIPO_EVENTO_OPCOES else 0
            tipo_ev = st.selectbox("Tipo de evento *", _TIPO_EVENTO_OPCOES, index=te_idx)
        with c3:
            can_idx = _CANAL_OPCOES.index(_d("Canal")) if _d("Canal") in _CANAL_OPCOES else 0
            canal   = st.selectbox("Canal *", _CANAL_OPCOES, index=can_idx)

        assunto = st.text_input(
            "Assunto (somente E-mail)",
            value=_d("Assunto"),
            placeholder="[Pred.IO] Novo relatório - {{ativo_nome}}",
        )
        corpo = st.text_area(
            "Corpo da mensagem *",
            value=_d("Corpo"),
            height=200,
            placeholder="Olá.\n\nUm novo relatório foi publicado.\n\nCliente: {{cliente_nome}}\n...\n\nFonte: Pred.IO",
        )
        st.caption(f"Variáveis permitidas: {_VARS_HINT}")
        st.caption("Variáveis sensíveis (ex: {{senha}}, {{token}}) são bloqueadas automaticamente.")

        vars_perm = st.text_input(
            "Variáveis esperadas neste template",
            value=_d("Variaveis_Permitidas", "cliente_nome,ativo_nome,resumo,link_portal,fonte"),
        )
        st_idx = _STATUS_TPL.index(_d("Status", "Rascunho")) if _d("Status", "Rascunho") in _STATUS_TPL else 0
        status = st.selectbox("Status", _STATUS_TPL, index=st_idx)

        submitted = st.form_submit_button("💾 Salvar template", type="primary")

    if submitted:
        if not nome.strip():
            st.error("Informe o nome do template.")
            return
        if not corpo.strip():
            st.error("O corpo da mensagem é obrigatório.")
            return

        from notification_engine import render_template, validate_content
        test_render = render_template(corpo, assunto, {})
        if test_render["variaveis_bloqueadas"]:
            st.error(
                f"Template contém variáveis bloqueadas: "
                f"{', '.join(test_render['variaveis_bloqueadas'])}. "
                "Remova-as antes de salvar."
            )
            return

        campos = {
            "Nome": nome.strip(), "Tipo_Evento": tipo_ev, "Canal": canal,
            "Assunto": assunto.strip(), "Corpo": corpo.strip(),
            "Variaveis_Permitidas": vars_perm.strip(), "Status": status,
        }
        if editing and tpl_id:
            ok = update_notification_template(tpl_id, campos)
            st.success("Template atualizado." if ok else "Erro ao atualizar.")
        else:
            ok = add_notification_template(campos)
            st.success("Template criado com sucesso." if ok else "Erro ao criar template.")
        if ok:
            st.session_state.pop(f"_tpl_editing_{tpl_id}", None)
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: FILA — visualizar fila de notificações
# ═══════════════════════════════════════════════════════════════════════════════

_STATUS_FILA_COR = {
    "Simulado":               ("#6366F1", "#fff"),
    "Bloqueado":              ("#EF4444", "#fff"),
    "Pendente":               ("#F59E0B", "#000"),
    "Aguardando aprovacao":   ("#0EA5E9", "#fff"),
    "Aprovado para envio futuro": ("#10B981", "#fff"),
    "Cancelado":              ("#94A3B8", "#fff"),
}


def _render_tab_fila() -> None:
    from sheets import get_notification_queue, update_notification_queue_status

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin-bottom:0.5rem;'>"
        "Notificações enfileiradas em modo Teste. Nenhuma mensagem real foi enviada.</p>",
        unsafe_allow_html=True,
    )

    df_cli = get_all_clientes()
    cli_opts = ["Todos"]
    cli_map: dict = {}
    if not df_cli.empty and "Empresa" in df_cli.columns:
        for _, r in df_cli.iterrows():
            nome = str(r.get("Empresa", "")).strip()
            cid  = str(r.get("Client_Id", "")).strip()
            if nome and cid:
                cli_map[nome] = cid
                cli_opts.append(nome)

    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        f_cli = st.selectbox("Cliente", cli_opts, key="_fila_f_cli")
    with cf2:
        f_st  = st.selectbox("Status", ["Todos", "Simulado", "Bloqueado", "Cancelado"], key="_fila_f_st")
    with cf3:
        f_can = st.selectbox("Canal", ["Todos", "E-mail", "WhatsApp", "Portal"], key="_fila_f_can")

    cid_sel = cli_map.get(f_cli, "") if f_cli != "Todos" else ""
    df = get_notification_queue(client_id=cid_sel, limit=200)

    if df.empty:
        st.info("Fila vazia. Use o Sandbox para simular notificações.")
        return

    if f_st != "Todos":
        df = df[df["Status"].str.strip() == f_st]
    if f_can != "Todos":
        df = df[df["Canal"].str.strip() == f_can]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total", len(df))
    m2.metric("Simulados", len(df[df["Status"].str.strip() == "Simulado"]))
    m3.metric("Bloqueados", len(df[df["Status"].str.strip() == "Bloqueado"]))
    st.markdown(f"<hr style='border-color:{COLOR_BORDER};margin:0.5rem 0 1rem;'/>", unsafe_allow_html=True)

    if df.empty:
        st.info("Nenhum item com os filtros selecionados.")
        return

    for _, row in df.tail(80).iterrows():
        _render_fila_card(row)


def _render_fila_card(row) -> None:
    item_id  = str(row.get("Id",               "")).strip()
    cli_id   = str(row.get("Client_Id",         "")).strip()
    canal    = str(row.get("Canal",             "")).strip()
    dest     = str(row.get("Destinatario",      "")).strip()
    assunto  = str(row.get("Assunto",           "")).strip()
    corpo    = str(row.get("Corpo_Renderizado", "")).strip()
    link     = str(row.get("Link_Portal",       "")).strip()
    tipo_ev  = str(row.get("Tipo_Evento",       "")).strip()
    prioridade= str(row.get("Prioridade",       "")).strip()
    status   = str(row.get("Status",            "Simulado")).strip()
    modo     = str(row.get("Modo",              "Teste")).strip()
    erro     = str(row.get("Erro_Validacao",    "")).strip()
    criado   = str(row.get("Created_At",        "")).strip()[:16]

    bg, tc = _STATUS_FILA_COR.get(status, ("#94A3B8", "#fff"))
    border  = "#EF4444" if status == "Bloqueado" else "#6366F1" if status == "Simulado" else "#F59E0B"

    with st.expander(
        f"🏢 {cli_id}  ·  {canal}  ·  {tipo_ev}  ·  {status}  ·  {criado}",
        expanded=False,
    ):
        st.markdown(
            f"<div style='background:{COLOR_CARD};border-left:4px solid {border};"
            f"border-radius:0 8px 8px 0;padding:12px 16px;'>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;'>"
            f"<span style='background:{bg};color:{tc};-webkit-text-fill-color:{tc};"
            f"font-size:0.7rem;font-weight:700;padding:2px 10px;border-radius:12px;'>{status}</span>"
            f"<span style='background:#EFF6FF;color:{COLOR_NAVY};-webkit-text-fill-color:{COLOR_NAVY};"
            f"font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:12px;"
            f"border:1px solid #BFDBFE;'>Modo: {modo}</span>"
            + (f"<span style='background:#FEF2F2;color:#EF4444;-webkit-text-fill-color:#EF4444;"
               f"font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:12px;"
               f"border:1px solid #FECACA;'>⚠️ Bloqueado: {erro[:60]}</span>"
               if erro else "")
            + f"</div>"
            f"<p style='font-size:0.83rem;color:#334155;margin:0 0 4px;'>"
            f"<strong>Destinatário:</strong> {dest or '—'}</p>"
            + (f"<p style='font-size:0.83rem;color:#334155;margin:0 0 4px;'>"
               f"<strong>Assunto:</strong> {assunto}</p>" if assunto else "")
            + f"<p style='font-size:0.8rem;color:#475569;margin:0 0 6px;white-space:pre-wrap;'>{corpo[:300]}{'…' if len(corpo)>300 else ''}</p>"
            f"<p style='font-size:0.72rem;color:{COLOR_MUTED};margin:0;'>🔗 {link or '—'}  ·  Prioridade: {prioridade}  ·  {criado}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: SANDBOX — simular notificação sem enviar mensagem real
# ═══════════════════════════════════════════════════════════════════════════════

def _render_tab_sandbox() -> None:
    from sheets import get_notification_templates, get_all_clientes, get_contatos_notificacao
    from notification_engine import simulate_notification, check_external_send_blocked

    st.markdown(
        f"<div style='background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;"
        f"padding:10px 14px;margin-bottom:1rem;'>"
        f"<p style='margin:0;font-size:0.82rem;color:#92400E;font-weight:600;'>"
        f"🔒 Modo Teste Ativo — <code>NOTIFICATION_EXTERNAL_SEND_ENABLED=false</code></p>"
        f"<p style='margin:4px 0 0;font-size:0.78rem;color:#92400E;'>"
        f"Nenhuma mensagem real será enviada. Resultados aparecem na aba Fila como 'Simulado'.</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    block_info = check_external_send_blocked()
    st.info(f"🔒 {block_info['mensagem']}")

    df_tpl = get_notification_templates(status="Ativo")
    if df_tpl.empty:
        st.warning("Nenhum template ativo. Crie e ative um template na aba Templates primeiro.")
        return

    tpl_opts = {
        f"{row['Nome']} ({row['Canal']})": row.to_dict()
        for _, row in df_tpl.iterrows()
        if str(row.get("Nome", "")).strip()
    }
    df_cli = get_all_clientes()
    cli_map: dict = {}
    if not df_cli.empty and "Empresa" in df_cli.columns:
        for _, r in df_cli.iterrows():
            nome = str(r.get("Empresa", "")).strip()
            cid  = str(r.get("Client_Id", "")).strip()
            if nome and cid:
                cli_map[nome] = cid

    if not cli_map:
        st.warning("Nenhum cliente cadastrado.")
        return

    with st.form("_sb_form"):
        _label("1. Template")
        tpl_sel_label = st.selectbox("Template *", list(tpl_opts.keys()), label_visibility="collapsed")

        _label("2. Cliente")
        cli_nome = st.selectbox("Cliente *", list(cli_map.keys()), label_visibility="collapsed")

        _label("3. Dados para substituição de variáveis")
        c1, c2 = st.columns(2)
        with c1:
            v_ativo    = st.text_input("Ativo ({{ativo_nome}})", value="Compressor A1")
            v_prioridade = st.selectbox("Prioridade ({{prioridade}})", ["Média", "Alta", "Baixa", "Crítica"])
            v_link     = st.text_input("Link portal ({{link_portal}})", value="/portal/relatorios")
        with c2:
            v_resumo   = st.text_area("Resumo ({{resumo}})", value="Vibração acima do limite aceitável detectada.", height=80)
            v_data     = st.text_input("Data do evento ({{data_evento}})", value=datetime.now().strftime("%d/%m/%Y"))
            v_status   = st.text_input("Status ({{status}})", value="Em análise")

        submitted = st.form_submit_button("🧪 Simular notificação", type="primary")

    if submitted:
        client_id = cli_map[cli_nome]
        template  = tpl_opts[tpl_sel_label]
        canal     = str(template.get("Canal", "")).strip()

        contatos = get_contatos_notificacao(client_id)
        if not contatos:
            st.warning(
                f"Nenhum contato cadastrado para {cli_nome}. "
                "Configure preferências de notificação para este cliente."
            )
            return

        dados = {
            "cliente_nome": cli_nome,
            "ativo_nome":   v_ativo.strip() or "—",
            "prioridade":   v_prioridade,
            "resumo":       v_resumo.strip() or "—",
            "link_portal":  v_link.strip() or "/portal",
            "data_evento":  v_data.strip(),
            "status":       v_status.strip(),
            "tipo_evento":  str(template.get("Tipo_Evento", "")),
            "fonte":        "Pred.IO",
        }

        resultados: list = []
        for contato in contatos:
            result = simulate_notification(
                template=template,
                client_id=client_id,
                contato=contato,
                canal=canal,
                dados=dados,
            )
            resultados.append({"contato": contato, "result": result})

        # Exibe resultados
        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:1rem 0 0.5rem;'>"
            f"Resultado da simulação — {len(resultados)} contato(s)</p>",
            unsafe_allow_html=True,
        )

        for item in resultados:
            contato = item["contato"]
            result  = item["result"]
            pr      = result["preview_result"]
            ok      = pr["ok"]
            qid     = result.get("queue_id", "")

            border_col = COLOR_GREEN if ok else COLOR_RED
            status_txt = "✅ Simulado" if ok else "🚫 Bloqueado"

            with st.expander(
                f"{status_txt}  ·  {contato.get('nome', '—')}  ·  {canal}",
                expanded=True,
            ):
                if not ok:
                    st.error("Validação falhou — item enfileirado como Bloqueado.")
                    for risco in pr.get("riscos", []):
                        st.warning(f"⚠️ {risco}")
                else:
                    st.success(f"Simulação registrada na fila. ID: {qid}")

                st.markdown("**Pré-visualização:**")
                preview = pr["preview"]
                if preview.get("assunto"):
                    st.markdown(f"**Assunto:** `{preview['assunto']}`")
                st.text_area(
                    "Corpo renderizado",
                    preview.get("corpo", ""),
                    height=180,
                    disabled=True,
                    key=f"_sb_preview_{qid}_{contato.get('id','')}",
                )
                st.caption(
                    f"🔗 Link: {preview.get('link','—')}  ·  "
                    f"Destinatário: {preview.get('destinatario','—')}  ·  "
                    f"Variáveis usadas: {', '.join(preview.get('vars_usadas',[]))}"
                )

                # Validações
                val = pr.get("validacoes", {})
                col_v1, col_v2, col_v3 = st.columns(3)
                with col_v1:
                    v_cont = val.get("conteudo", {})
                    icon = "✅" if v_cont.get("ok") else "🚫"
                    st.caption(f"{icon} Conteúdo: {v_cont.get('mensagem','')}")
                with col_v2:
                    v_lnk = val.get("link", {})
                    icon = "✅" if v_lnk.get("ok") else "🚫"
                    st.caption(f"{icon} Link: {v_lnk.get('motivo','')}")
                with col_v3:
                    v_con = val.get("consentimento", {})
                    icon = "✅" if v_con.get("ok") else "🚫"
                    st.caption(f"{icon} Consentimento: {v_con.get('motivo','')}")

                st.caption(
                    f"🔒 Modo: Teste  ·  Envio externo: Não  ·  "
                    f"NOTIFICATION_EXTERNAL_SEND_ENABLED=false"
                )
