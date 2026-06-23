"""Portal do Cliente — Preferências de Notificação Externa."""
import streamlit as st
from auth import current_client_id
from sheets import get_preferencias_notificacao, upsert_preferencias_notificacao
from ui import page_header, COLOR_NAVY, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE


def render() -> None:
    if not st.session_state.get("logged_in"):
        st.error("🔒 Faça login para acessar esta página.")
        st.stop()
    page_header(
        "📱 Preferências de Notificação",
        "Escolha como deseja receber avisos sobre relatórios, alertas, manutenções e chamados.",
    )

    # SECURITY: client_id e usuario_id sempre vêm da sessão/autenticação
    client_id  = current_client_id()
    usuario_id = st.session_state.get("email_logado", "")
    nome       = st.session_state.get("nome", "")
    telefone   = st.session_state.get("telefone", "")

    # Aviso de segurança
    st.markdown(
        "<div style='background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;"
        "padding:12px 16px;margin-bottom:1.5rem;'>"
        "<p style='margin:0;font-size:0.83rem;color:#92400E;'>"
        "🔒 <strong>Segurança:</strong> As notificações externas exibem apenas avisos resumidos. "
        "O conteúdo técnico completo deve ser acessado com login no portal.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Carregar preferências existentes ──────────────────────────────────────
    df_pref = get_preferencias_notificacao(usuario_id=usuario_id)
    if not df_pref.empty:
        r = df_pref.iloc[0]
        def _bool(col: str, default: bool = True) -> bool:
            return str(r.get(col, str(default))).strip().lower() == "true"
        prefs = {
            "receber_email":            _bool("Receber_Email",            False),
            "receber_whatsapp":         _bool("Receber_Whatsapp",         False),
            "receber_relatorios":       _bool("Receber_Relatorios",       True),
            "receber_alertas_criticos": _bool("Receber_Alertas_Criticos", True),
            "receber_manutencao":       _bool("Receber_Manutencao",       True),
            "receber_chamados":         _bool("Receber_Chamados",         True),
        }
        pref_email    = str(r.get("Email",    "")).strip() or usuario_id
        pref_whatsapp = str(r.get("Whatsapp", "")).strip() or telefone
        pref_id       = str(r.get("Id",       "")).strip()
        pref_created  = str(r.get("Created_At","")).strip()
    else:
        prefs = {
            "receber_email":            False,
            "receber_whatsapp":         False,
            "receber_relatorios":       True,
            "receber_alertas_criticos": True,
            "receber_manutencao":       True,
            "receber_chamados":         True,
        }
        pref_email    = usuario_id
        pref_whatsapp = telefone
        pref_id       = ""
        pref_created  = ""

    # ── Formulário ─────────────────────────────────────────────────────────────
    with st.form("form_pref_notif", clear_on_submit=False):
        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0 0 0.75rem;'>1. Canais de envio</p>",
            unsafe_allow_html=True,
        )

        col_te, col_tw = st.columns(2)
        with col_te:
            receber_email     = st.toggle("📧 Receber por e-mail",   value=prefs["receber_email"])
        with col_tw:
            receber_whatsapp  = st.toggle("📲 Receber por WhatsApp", value=prefs["receber_whatsapp"])

        col_em, col_wh = st.columns(2)
        with col_em:
            email_val = st.text_input(
                "E-mail para notificações",
                value=pref_email,
                placeholder="seu@email.com",
            )
        with col_wh:
            whatsapp_val = st.text_input(
                "WhatsApp (com DDD)",
                value=pref_whatsapp,
                placeholder="+55 11 99999-9999",
            )

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:1rem 0 0.5rem;'>2. Tipos de evento</p>",
            unsafe_allow_html=True,
        )
        st.caption("Selecione quais eventos devem gerar aviso nos canais escolhidos acima:")

        col_ev1, col_ev2 = st.columns(2)
        with col_ev1:
            rec_rel   = st.checkbox(
                "📄 Novos relatórios e documentos",
                value=prefs["receber_relatorios"],
            )
            rec_mnt   = st.checkbox(
                "📅 Manutenções próximas ou vencidas",
                value=prefs["receber_manutencao"],
            )
        with col_ev2:
            rec_alert = st.checkbox(
                "🚨 Alertas críticos",
                value=prefs["receber_alertas_criticos"],
            )
            rec_cham  = st.checkbox(
                "🔧 Respostas de chamados técnicos",
                value=prefs["receber_chamados"],
            )

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button(
            "💾 Salvar preferências", type="primary", use_container_width=True
        )

    if submitted:
        erros = []
        if receber_email and not email_val.strip():
            erros.append("Informe o e-mail para notificações por e-mail.")
        if receber_whatsapp and not whatsapp_val.strip():
            erros.append("Informe o WhatsApp para notificações por WhatsApp.")
        if erros:
            for e in erros:
                st.warning(e)
        else:
            ok = upsert_preferencias_notificacao({
                "id":                       pref_id,
                "usuario_id":               usuario_id,
                "cliente_id":               client_id,
                "nome":                     nome,
                "email":                    email_val.strip(),
                "whatsapp":                 whatsapp_val.strip(),
                "receber_email":            receber_email,
                "receber_whatsapp":         receber_whatsapp,
                "receber_relatorios":       rec_rel,
                "receber_alertas_criticos": rec_alert,
                "receber_manutencao":       rec_mnt,
                "receber_chamados":         rec_cham,
                "created_at":               pref_created,
            })
            if ok:
                st.success("✅ Preferências salvas com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao salvar. Verifique as credenciais e tente novamente.")

    # ── Templates de mensagem (informativo) ────────────────────────────────────
    with st.expander("📋 Modelos de notificação"):
        st.markdown(
            "**E-mail — Novo relatório:**\n"
            "```\n"
            "Assunto: Pred.IO | Novo relatório técnico disponível\n\n"
            "Olá, [Nome].\n"
            "Um novo relatório técnico foi publicado.\n"
            "Relatório: [Nome do relatório]\n"
            "Ativo: [Nome do ativo]\n"
            "Acesse: [Link seguro com login]\n"
            "```\n\n"
            "**WhatsApp — Alerta crítico:**\n"
            "```\n"
            "Pred.IO | Alerta crítico\n"
            "O ativo \"[Nome]\" foi sinalizado como condição crítica.\n"
            "Acesse o portal: [Link seguro]\n"
            "```\n\n"
            "**WhatsApp — Manutenção próxima:**\n"
            "```\n"
            "Pred.IO | Manutenção próxima\n"
            "A tarefa \"[Nome]\" está próxima do vencimento.\n"
            "Ativo: [Nome] | Prazo: [Horas/data]\n"
            "Acesse: [Link seguro]\n"
            "```\n\n"
            "**WhatsApp — Chamado respondido:**\n"
            "```\n"
            "Pred.IO | Chamado respondido\n"
            "A equipe Pred.IO respondeu seu chamado técnico.\n"
            "Acesse o portal para visualizar: [Link seguro]\n"
            "```"
        )
