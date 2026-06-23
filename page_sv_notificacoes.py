"""Supervisão — Notificações Externas (e-mail / WhatsApp)."""
import pandas as pd
import streamlit as st
from datetime import datetime
from auth import require_staff
from sheets import get_notificacoes, update_notificacao_status
from ui import sv_page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE

# ── Mock data — exibido quando a aba NotificacoesExternas ainda está vazia ────
_MOCK = [
    {
        "Id": "NOTIF-DEMO-001",
        "Cliente_Id": "demo-client",
        "Usuario_Id": "contato@empresa.com",
        "Evento_Tipo": "report_published",
        "Canal": "E-mail",
        "Titulo": "Novo relatório técnico disponível",
        "Mensagem": (
            'O relatório "Análise Preditiva - Unidade Compressora 200 VLD - Junho/2026" '
            "foi publicado no Portal de Confiabilidade Pred.IO."
        ),
        "Link_Portal": "/portal/relatorios",
        "Status": "Enviado",
        "Tentativas": "1",
        "Erro": "",
        "Enviado_Em": "17/06/2026 09:30",
        "Created_At": "17/06/2026 09:28",
        "Updated_At": "17/06/2026 09:30",
    },
    {
        "Id": "NOTIF-DEMO-002",
        "Cliente_Id": "demo-client",
        "Usuario_Id": "contato@empresa.com",
        "Evento_Tipo": "critical_alarm",
        "Canal": "WhatsApp",
        "Titulo": "Alerta crítico no ativo monitorado",
        "Mensagem": (
            "A Bomba de Óleo M60P foi sinalizada como condição crítica. "
            "Acesse o portal para visualizar detalhes e recomendações."
        ),
        "Link_Portal": "/portal/ativos",
        "Status": "Pendente",
        "Tentativas": "0",
        "Erro": "",
        "Enviado_Em": "",
        "Created_At": "17/06/2026 10:15",
        "Updated_At": "17/06/2026 10:15",
    },
    {
        "Id": "NOTIF-DEMO-003",
        "Cliente_Id": "demo-client",
        "Usuario_Id": "contato@empresa.com",
        "Evento_Tipo": "maintenance_due",
        "Canal": "E-mail",
        "Titulo": "Manutenção próxima do vencimento",
        "Mensagem": (
            "A análise de óleo da Unidade Compressora 200 VLD está "
            "próxima do vencimento em 320 horas."
        ),
        "Link_Portal": "/portal/manutencao",
        "Status": "Pendente",
        "Tentativas": "0",
        "Erro": "",
        "Enviado_Em": "",
        "Created_At": "17/06/2026 10:45",
        "Updated_At": "17/06/2026 10:45",
    },
    {
        "Id": "NOTIF-DEMO-004",
        "Cliente_Id": "demo-client",
        "Usuario_Id": "contato@empresa.com",
        "Evento_Tipo": "ticket_replied",
        "Canal": "WhatsApp",
        "Titulo": "Chamado respondido pela Pred.IO",
        "Mensagem": (
            "A equipe Pred.IO respondeu um chamado técnico. "
            "Acesse o portal para visualizar a resposta."
        ),
        "Link_Portal": "/portal/chamados",
        "Status": "Enviado",
        "Tentativas": "1",
        "Erro": "",
        "Enviado_Em": "17/06/2026 11:00",
        "Created_At": "17/06/2026 10:50",
        "Updated_At": "17/06/2026 11:00",
    },
]

_EVENTO_LABEL: dict = {
    "report_published":             "📄 Relatório publicado",
    "critical_alarm":               "🚨 Alerta crítico",
    "asset_critical":               "⚠️ Ativo crítico",
    "maintenance_due":              "📅 Manutenção próxima",
    "maintenance_overdue":          "🔴 Manutenção vencida",
    "ticket_replied":               "🔧 Chamado respondido",
    "ticket_waiting_customer":      "⏳ Aguardando cliente",
    "technical_document_available": "📚 Documento disponível",
}

_STATUS_COR: dict = {
    "Enviado":                  ("#16A34A", "#fff"),
    "Pendente":                 ("#F59E0B", "#000"),
    "Falhou":                   ("#EF4444", "#fff"),
    "Cancelado":                ("#94A3B8", "#fff"),
    "Ignorado":                 ("#94A3B8", "#fff"),
    "Aguardando configuração":  ("#6366F1", "#fff"),
}

_CANAL_COR: dict = {
    "E-mail":   ("#2563EB", "#fff"),
    "WhatsApp": ("#16A34A", "#fff"),
    "Portal":   ("#0F1F3D", "#fff"),
}


# ═════════════════════════════════════════════════════════════════════════════
def render() -> None:
    require_staff()
    sv_page_header(
        "📨 Notificações Externas",
        "Gerencie avisos enviados por e-mail e WhatsApp aos clientes.",
    )

    st.info(
        "**Integração futura:** os envios serão realizados via n8n, serviço de e-mail "
        "ou API oficial de WhatsApp. Nesta versão, registros são criados como *Pendente* "
        "e o botão **📤 Simular** atualiza o status para *Enviado*.",
        icon="ℹ️",
    )

    # ── Carregar dados ────────────────────────────────────────────────────────
    df_real = get_notificacoes()
    using_mock = df_real.empty

    if using_mock:
        st.caption(
            "💡 Exibindo dados de demonstração. "
            "Notificações reais aparecem após o primeiro evento ser gerado."
        )
        overrides = st.session_state.get("_sv_notif_mock_status", {})
        rows = []
        for r in _MOCK:
            r2 = dict(r)
            if r2["Id"] in overrides:
                r2["Status"] = overrides[r2["Id"]]
                if overrides[r2["Id"]] == "Enviado":
                    r2["Enviado_Em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            rows.append(r2)
        df = pd.DataFrame(rows)
    else:
        df = df_real

    # ── Filtros ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        f_status = st.selectbox(
            "Status",
            ["Todos", "Pendente", "Enviado", "Falhou", "Cancelado", "Ignorado"],
        )
    with col_f2:
        f_canal = st.selectbox("Canal", ["Todos", "E-mail", "WhatsApp", "Portal"])
    with col_f3:
        evento_opts = ["Todos"] + list(_EVENTO_LABEL.values())
        f_evento_label = st.selectbox("Tipo de evento", evento_opts)

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:0.5rem 0 1rem;'/>",
        unsafe_allow_html=True,
    )

    df_f = df.copy()
    if f_status != "Todos":
        df_f = df_f[df_f["Status"].astype(str).str.strip() == f_status]
    if f_canal != "Todos":
        df_f = df_f[df_f["Canal"].astype(str).str.strip() == f_canal]
    if f_evento_label != "Todos":
        evt_key = next((k for k, v in _EVENTO_LABEL.items() if v == f_evento_label), None)
        if evt_key:
            df_f = df_f[df_f["Evento_Tipo"].astype(str).str.strip() == evt_key]

    total = len(df_f)
    pendentes = len(df_f[df_f["Status"].astype(str).str.strip() == "Pendente"]) if total else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", total)
    c2.metric("Pendentes", pendentes)
    c3.metric("Enviados", total - pendentes)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if df_f.empty:
        st.info("Nenhuma notificação encontrada com os filtros selecionados.")
        return

    for _, row in df_f.iterrows():
        _render_card(row, using_mock)


# ─────────────────────────────────────────────────────────────────────────────
def _badge(text: str, color_map: dict, default_bg: str = "#64748B") -> str:
    bg, tc = color_map.get(text, (default_bg, "#fff"))
    return (
        f"<span style='background:{bg};color:{tc};-webkit-text-fill-color:{tc};"
        f"font-size:0.7rem;font-weight:700;padding:2px 10px;border-radius:20px;"
        f"white-space:nowrap;'>{text}</span>"
    )


def _render_card(row, using_mock: bool) -> None:
    notif_id   = str(row.get("Id",          "")).strip()
    usuario_id = str(row.get("Usuario_Id",  "")).strip()
    evento     = str(row.get("Evento_Tipo", "")).strip()
    canal      = str(row.get("Canal",       "")).strip()
    titulo     = str(row.get("Titulo",      "")).strip()
    mensagem   = str(row.get("Mensagem",    "")).strip()
    link       = str(row.get("Link_Portal", "")).strip()
    status     = str(row.get("Status",      "Pendente")).strip()
    tentativas = str(row.get("Tentativas",  "0")).strip()
    erro       = str(row.get("Erro",        "")).strip()
    enviado_em = str(row.get("Enviado_Em",  "")).strip()
    created_at = str(row.get("Created_At",  "")).strip()[:16]

    evento_label = _EVENTO_LABEL.get(evento, evento)
    is_pending   = status == "Pendente"
    border_col   = (
        "#F59E0B" if is_pending
        else "#16A34A" if status == "Enviado"
        else "#EF4444"
    )

    col_main, col_act = st.columns([11, 1.4])

    with col_main:
        with st.expander(
            f"{_EVENTO_LABEL.get(evento, evento)}  ·  {canal}  ·  {titulo}  ·  {status}",
            expanded=False,
        ):
            extras = ""
            if enviado_em:
                extras += f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>✅ Enviado: {enviado_em}</p>"
            if tentativas not in ("0", ""):
                extras += f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>🔁 Tentativas: {tentativas}</p>"
            if erro:
                extras += f"<p style='color:#EF4444;font-size:0.72rem;margin:0;'>❌ Erro: {erro}</p>"

            st.markdown(
                f"<div style='background:{COLOR_CARD};border-left:4px solid {border_col};"
                f"border-radius:0 8px 8px 0;padding:12px 16px;'>"
                f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;'>"
                f"{_badge(canal, _CANAL_COR, '#2563EB')}"
                f"{_badge(status, _STATUS_COR)}"
                f"<span style='background:#EFF6FF;color:#1E40AF;-webkit-text-fill-color:#1E40AF;"
                f"font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:20px;"
                f"border:1px solid #BFDBFE;'>{evento_label}</span>"
                f"</div>"
                f"<p style='color:#334155;font-size:0.83rem;margin:0 0 8px;'>{mensagem}</p>"
                f"<div style='display:flex;flex-wrap:wrap;gap:16px;'>"
                f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>👤 {usuario_id}</p>"
                f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>📅 Criado: {created_at}</p>"
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
                key=f"sv_notif_sim_{notif_id}",
                use_container_width=True,
                help="Simula o envio alterando status para Enviado",
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
                    if ok:
                        st.toast("✅ Status atualizado para Enviado.", icon="📤")
                    else:
                        st.toast("⚠️ Não foi possível atualizar.", icon="⚠️")
                st.rerun()
