"""Portal do Cliente — Preferências de Notificação por Evento."""
import streamlit as st
from auth import current_client_id
from ui import page_header, COLOR_NAVY, COLOR_BLUE, COLOR_BORDER, COLOR_MUTED, COLOR_CARD

# Aviso obrigatório (Etapa 4)
_AVISO_ETAPA = (
    "E-mail e WhatsApp estão preparados para uma próxima etapa. "
    "Nesta fase, as notificações serão exibidas dentro do Portal Pred.IO."
)

_FREQUENCIA_OPTS = ["Imediata", "Diária", "Semanal"]
_PRIORIDADE_OPTS = ["Baixa", "Média", "Alta", "Crítica"]


def render() -> None:
    if not st.session_state.get("logged_in"):
        st.error("🔒 Faça login para acessar esta página.")
        st.stop()

    page_header(
        "🔔 Preferências de Notificação",
        "Configure quais eventos geram avisos e como você deseja recebê-los.",
    )

    client_id  = current_client_id()   # SEMPRE da sessão
    usuario_id = st.session_state.get("email_logado", "")
    nome       = st.session_state.get("nome", "")
    telefone   = st.session_state.get("telefone", "")

    # ── Aviso obrigatório ─────────────────────────────────────────────────────
    st.markdown(
        "<div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;"
        "padding:12px 16px;margin-bottom:1.5rem;'>"
        f"<p style='margin:0;font-size:0.83rem;color:#1E40AF;'>ℹ️ {_AVISO_ETAPA}</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    from notifications import EVENTOS, _DEFAULT_EVENT_PREFS, ensure_default_preferences
    from sheets import get_event_preferences, upsert_event_preference, get_preferencias_notificacao, upsert_preferencias_notificacao

    # Garante preferências padrão inicializadas
    ensure_default_preferences(client_id)

    tabs = st.tabs(["⚙️ Eventos", "📬 Contato", "📋 Modelos"])

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 1: Por evento
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[0]:
        _render_tab_eventos(client_id)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 2: Dados de contato
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[1]:
        _render_tab_contato(client_id, usuario_id, nome, telefone)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 3: Modelos de mensagem
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[2]:
        _render_tab_modelos()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Configuração por evento
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_eventos(client_id: str) -> None:
    from notifications import EVENTOS, _DEFAULT_EVENT_PREFS
    from sheets import get_event_preferences, upsert_event_preference

    df_prefs = get_event_preferences(client_id)

    # Monta dict evento → preferência atual (com fallback nos defaults)
    pref_atual: dict = {}
    for evento, default in _DEFAULT_EVENT_PREFS.items():
        pref_atual[evento] = dict(default)

    if not df_prefs.empty:
        for _, row in df_prefs.iterrows():
            ev = str(row.get("Evento", "")).strip()
            if ev in pref_atual:
                def _b(col: str, d_key: str) -> bool:
                    val = str(row.get(col, row.get(d_key, "true"))).strip().lower()
                    return val in ("true", "1", "sim", "yes")

                pref_atual[ev] = {
                    "canal_portal":    _b("Canal_Portal",    "canal_portal"),
                    "canal_email":     _b("Canal_Email",     "canal_email"),
                    "canal_whatsapp":  _b("Canal_Whatsapp",  "canal_whatsapp"),
                    "prioridade_minima": str(row.get("Prioridade_Minima",
                                               row.get("prioridade_minima", "Baixa"))).strip(),
                    "frequencia":      str(row.get("Frequencia",
                                           row.get("frequencia", "Imediata"))).strip(),
                    "ativo":           _b("Ativo", "ativo"),
                }

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.82rem;margin-bottom:1rem;'>"
        "Configure cada evento abaixo. Clique em <strong>Salvar</strong> na linha correspondente.</p>",
        unsafe_allow_html=True,
    )

    # Cabeçalho da grade
    h0, h1, h2, h3, h4, h5, h6 = st.columns([3, 1.2, 1.2, 1.2, 1.8, 2, 1.2])
    for col, lbl in zip(
        [h0, h1, h2, h3, h4, h5, h6],
        ["EVENTO", "PORTAL", "E-MAIL", "WHATSAPP", "PRIORIDADE MÍN.", "FREQUÊNCIA", "ATIVO"],
    ):
        col.markdown(
            f"<p style='font-size:0.7rem;font-weight:700;color:{COLOR_MUTED};"
            f"margin:0 0 4px;text-transform:uppercase;letter-spacing:.06em;'>{lbl}</p>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:0 0 8px;'/>",
        unsafe_allow_html=True,
    )

    for evento, cfg in EVENTOS.items():
        pref = pref_atual.get(evento, _DEFAULT_EVENT_PREFS.get(evento, {}))
        _render_evento_row(client_id, evento, cfg, pref)


def _render_evento_row(client_id: str, evento: str, cfg: dict, pref: dict) -> None:
    from sheets import upsert_event_preference

    label = cfg["label"]
    key   = f"_pn_{evento}"

    c0, c1, c2, c3, c4, c5, c6 = st.columns([3, 1.2, 1.2, 1.2, 1.8, 2, 1.2])

    with c0:
        st.markdown(
            f"<p style='font-size:0.83rem;font-weight:600;color:{COLOR_NAVY};"
            f"margin:8px 0 0;'>{label}</p>",
            unsafe_allow_html=True,
        )

    with c1:
        portal_on = st.toggle(
            "Portal",
            value=bool(pref.get("canal_portal", True)),
            key=f"{key}_portal",
            label_visibility="collapsed",
            help="Exibir notificação no portal Pred.IO",
        )

    with c2:
        email_on = st.toggle(
            "E-mail",
            value=bool(pref.get("canal_email", False)),
            key=f"{key}_email",
            label_visibility="collapsed",
            disabled=True,
            help="E-mail — preparado para etapa futura. Não será enviado agora.",
        )

    with c3:
        wa_on = st.toggle(
            "WhatsApp",
            value=bool(pref.get("canal_whatsapp", False)),
            key=f"{key}_wa",
            label_visibility="collapsed",
            disabled=True,
            help="WhatsApp — preparado para etapa futura. Não será enviado agora.",
        )

    with c4:
        prio_val = pref.get("prioridade_minima", "Baixa")
        if prio_val not in _PRIORIDADE_OPTS:
            prio_val = "Baixa"
        prio = st.selectbox(
            "Prioridade",
            _PRIORIDADE_OPTS,
            index=_PRIORIDADE_OPTS.index(prio_val),
            key=f"{key}_prio",
            label_visibility="collapsed",
        )

    with c5:
        freq_val = pref.get("frequencia", "Imediata")
        if freq_val not in _FREQUENCIA_OPTS:
            freq_val = "Imediata"
        freq = st.selectbox(
            "Frequência",
            _FREQUENCIA_OPTS,
            index=_FREQUENCIA_OPTS.index(freq_val),
            key=f"{key}_freq",
            label_visibility="collapsed",
        )

    with c6:
        ativo = st.toggle(
            "Ativo",
            value=bool(pref.get("ativo", True)),
            key=f"{key}_ativo",
            label_visibility="collapsed",
        )
        if st.button(
            "💾",
            key=f"{key}_save",
            use_container_width=True,
            help=f"Salvar preferências para: {label}",
        ):
            ok = upsert_event_preference(client_id, evento, {
                "canal_portal":    portal_on,
                "canal_email":     False,     # nunca salva True nesta etapa
                "canal_whatsapp":  False,     # nunca salva True nesta etapa
                "prioridade_minima": prio,
                "frequencia":      freq,
                "ativo":           ativo,
            })
            if ok:
                st.toast(f"✅ Salvo: {label}", icon="🔔")
                st.rerun()
            else:
                st.error("Erro ao salvar. Tente novamente.")

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:4px 0;opacity:.5;'/>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Dados de contato
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_contato(client_id: str, usuario_id: str,
                         nome: str, telefone: str) -> None:
    from sheets import get_preferencias_notificacao, upsert_preferencias_notificacao

    st.markdown(
        "<div style='background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;"
        "padding:12px 16px;margin-bottom:1.2rem;'>"
        "<p style='margin:0;font-size:0.83rem;color:#166534;'>"
        "✅ <strong>E-mail e WhatsApp</strong> estarão disponíveis em uma próxima etapa. "
        "Cadastre seus dados agora para que a ativação seja imediata quando disponível.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    df_pref = get_preferencias_notificacao(usuario_id=usuario_id)
    if not df_pref.empty:
        r = df_pref.iloc[0]
        pref_email    = str(r.get("Email",    "")).strip() or usuario_id
        pref_whatsapp = str(r.get("Whatsapp", "")).strip() or telefone
        pref_id       = str(r.get("Id",       "")).strip()
        pref_created  = str(r.get("Created_At","")).strip()
    else:
        pref_email    = usuario_id
        pref_whatsapp = telefone
        pref_id       = ""
        pref_created  = ""

    with st.form("form_pref_contato", clear_on_submit=False):
        col_em, col_wh = st.columns(2)
        with col_em:
            email_val = st.text_input(
                "📧 E-mail para notificações futuras",
                value=pref_email,
                placeholder="seu@email.com",
            )
        with col_wh:
            whatsapp_val = st.text_input(
                "📲 WhatsApp (com DDD)",
                value=pref_whatsapp,
                placeholder="+55 11 99999-9999",
            )

        submitted = st.form_submit_button(
            "💾 Salvar dados de contato", type="primary", use_container_width=True
        )

    if submitted:
        ok = upsert_preferencias_notificacao({
            "id":                       pref_id,
            "usuario_id":               usuario_id,
            "cliente_id":               client_id,
            "nome":                     nome,
            "email":                    email_val.strip(),
            "whatsapp":                 whatsapp_val.strip(),
            "receber_email":            False,
            "receber_whatsapp":         False,
            "receber_relatorios":       True,
            "receber_alertas_criticos": True,
            "receber_manutencao":       True,
            "receber_chamados":         True,
            "created_at":               pref_created,
        })
        if ok:
            st.success("✅ Dados de contato salvos!")
            st.rerun()
        else:
            st.error("Erro ao salvar. Verifique as credenciais e tente novamente.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Modelos de mensagem (informativo)
# ─────────────────────────────────────────────────────────────────────────────

def _render_tab_modelos() -> None:
    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin-bottom:1rem;'>"
        "Exemplos de como as notificações serão formatadas quando cada canal estiver ativo.</p>",
        unsafe_allow_html=True,
    )

    with st.expander("📄 Relatório publicado"):
        st.markdown(
            "**Portal Pred.IO:**\n"
            "> 📄 Novo relatório técnico publicado  \n"
            "> Um novo relatório técnico foi publicado para o ativo [Nome do Ativo].\n\n"
            "**E-mail (etapa futura):**\n"
            "```\n"
            "Assunto: Pred.IO | Novo relatório técnico disponível\n\n"
            "Olá, [Nome].\n"
            "Um novo relatório técnico foi publicado.\n"
            "Relatório: [Nome do relatório]\n"
            "Ativo: [Nome do ativo]\n"
            "Fonte: Pred.IO\n"
            "```\n\n"
            "**WhatsApp (etapa futura):**\n"
            "```\n"
            "Pred.IO | Novo relatório disponível.\n"
            "Acesse o portal com seu login para visualizar. Fonte: Pred.IO\n"
            "```"
        )

    with st.expander("🚨 Alerta crítico"):
        st.markdown(
            "**Portal Pred.IO:**\n"
            "> 🚨 Alerta técnico crítico  \n"
            "> Um alerta crítico foi gerado para o ativo [Nome]. Acesse o portal para detalhes.\n\n"
            "**WhatsApp (etapa futura):**\n"
            "```\n"
            "Pred.IO | Alerta crítico.\n"
            "Acesse o portal para detalhes. Fonte: Pred.IO\n"
            "```"
        )

    with st.expander("🔴 Manutenção vencida"):
        st.markdown(
            "**Portal Pred.IO:**\n"
            "> 🔴 Manutenção vencida  \n"
            "> A tarefa [Nome da Tarefa] está vencida no ativo [Nome do Ativo].\n\n"
            "**WhatsApp (etapa futura):**\n"
            "```\n"
            "Pred.IO | Manutenção vencida.\n"
            "Providencie agendamento acessando o portal. Fonte: Pred.IO\n"
            "```"
        )

    with st.expander("💬 Chamado respondido"):
        st.markdown(
            "**Portal Pred.IO:**\n"
            "> 💬 Chamado respondido pela equipe Pred.IO  \n"
            "> O chamado \"[Título]\" recebeu uma nova resposta da equipe Pred.IO.\n\n"
            "**WhatsApp (etapa futura):**\n"
            "```\n"
            "Pred.IO | Chamado respondido.\n"
            "Acesse o portal para visualizar a resposta. Fonte: Pred.IO\n"
            "```"
        )

    st.markdown(
        "<div style='background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;"
        "padding:10px 14px;margin-top:1rem;'>"
        "<p style='margin:0;font-size:0.8rem;color:#92400E;'>"
        "🔒 <strong>Segurança:</strong> Notificações externas exibem apenas avisos resumidos. "
        "O conteúdo técnico completo deve ser acessado com login no portal Pred.IO.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
