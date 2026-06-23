"""Supervisão — Alertas e Pontos de Atenção manuais."""
import streamlit as st
from auth import require_staff
from sheets import get_all_clientes, get_alertas_sv, add_alerta_sv, delete_alerta_sv
from assistant import send_whatsapp
from ui import sv_page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE

_PRIO_OPTS = ["Crítica", "Alta", "Média", "Baixa"]
_PRIO_COR  = {
    "Crítica": "#EF4444",
    "Alta":    "#F97316",
    "Média":   "#F59E0B",
    "Baixa":   "#64748B",
}


def render() -> None:
    require_staff()
    sv_page_header(
        "🔔 Alertas e Pontos de Atenção",
        "Gerencie alertas visíveis no painel de cada cliente.",
    )

    # ── Formulário novo alerta ────────────────────────────────────────────────
    with st.form("form_novo_alerta", clear_on_submit=True):
        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0 0 0.75rem;'>➕ Publicar novo alerta</p>",
            unsafe_allow_html=True,
        )

        df_cli = get_all_clientes()
        if not df_cli.empty and "Empresa" in df_cli.columns:
            empresas = sorted(df_cli["Empresa"].dropna().unique().tolist())
        else:
            empresas = ["Coca-Cola", "Sibele Alimentos"]

        col_e, col_p = st.columns(2)
        with col_e:
            empresa_sel = st.selectbox("Cliente *", ["Selecione..."] + empresas)
        with col_p:
            prioridade = st.selectbox("Prioridade *", _PRIO_OPTS, index=2)

        titulo    = st.text_input("Título *", placeholder="Ex: Bomba de Óleo em condição crítica")
        descricao = st.text_area(
            "Descrição",
            placeholder="Descreva o ponto de atenção para o cliente...",
            height=80,
        )
        whatsapp = st.text_input(
            "WhatsApp para envio",
            placeholder="Ex: 5511999999999 (com DDI e DDD, sem espaços ou +)",
        )

        submitted = st.form_submit_button(
            "🔔 Publicar alerta", type="primary", use_container_width=True
        )

    if submitted:
        if empresa_sel == "Selecione..." or not titulo.strip():
            st.warning("Selecione o cliente e informe o título do alerta.")
        else:
            if not df_cli.empty and "Client_Id" in df_cli.columns:
                m = df_cli[df_cli["Empresa"].str.strip() == empresa_sel.strip()]
                client_id = str(m.iloc[0]["Client_Id"]).strip().lower() if not m.empty else empresa_sel.strip().lower()
            else:
                client_id = empresa_sel.strip().lower()

            ok = add_alerta_sv(client_id, empresa_sel, titulo.strip(), descricao.strip(), prioridade, whatsapp)
            if ok:
                numero = whatsapp.strip()
                if numero:
                    msg_wa = (
                        f"*🔔 Alerta Pred.IO — {empresa_sel}*\n\n"
                        f"*{titulo.strip()}*\n"
                        + (f"{descricao.strip()}\n" if descricao.strip() else "")
                        + f"\nPrioridade: {prioridade}"
                    )
                    enviado = send_whatsapp(
                        numero, msg_wa,
                        contexto={"empresa": empresa_sel, "client_id": client_id, "tipo": "alerta_sv"},
                    )
                    if enviado:
                        st.success(f"✅ Alerta publicado e WhatsApp enviado para {numero}.")
                    else:
                        st.success(f"✅ Alerta publicado para {empresa_sel}.")
                        st.warning(
                            "WhatsApp não enviado — configure a variável **N8N_WHATSAPP_WEBHOOK_URL** "
                            "no Render com a URL do seu webhook (n8n, Z-API, Evolution API etc.)."
                        )
                else:
                    st.success(f"✅ Alerta publicado para {empresa_sel}.")
                st.rerun()
            else:
                st.error("Erro ao publicar. Verifique as credenciais do Google Sheets.")

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.5rem 0;'/>",
        unsafe_allow_html=True,
    )

    # ── Lista de alertas ──────────────────────────────────────────────────────
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0 0 1rem;'>"
        f"📋 Alertas Publicados</p>",
        unsafe_allow_html=True,
    )

    df = get_alertas_sv()

    if df.empty:
        st.info(
            "Nenhum alerta publicado ainda. "
            "Use o formulário acima para criar pontos de atenção visíveis no portal de cada cliente."
        )
        return

    for _, row in df.iterrows():
        _render_card(row)


def _render_card(row) -> None:
    alerta_id  = str(row.get("Id",         "")).strip()
    empresa    = str(row.get("Empresa",    "")).strip()
    titulo     = str(row.get("Titulo",     "")).strip()
    descricao  = str(row.get("Descricao",  "")).strip()
    prioridade = str(row.get("Prioridade", "Média")).strip()
    criado_em  = str(row.get("Criado_Em",  "")).strip()[:16]
    whatsapp   = str(row.get("Whatsapp",   "")).strip()

    cor = _PRIO_COR.get(prioridade, "#94A3B8")

    col_info, col_del = st.columns([10, 0.7])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {cor};border-radius:10px;"
            f"padding:12px 16px;margin-bottom:4px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"flex-wrap:wrap;gap:6px;margin-bottom:4px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;'>{titulo}</span>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>"
            f"<span style='background:{cor}22;color:{cor};-webkit-text-fill-color:{cor};"
            f"border:1px solid {cor}55;font-size:0.7rem;font-weight:700;"
            f"padding:2px 10px;border-radius:10px;'>{prioridade}</span>"
            f"<span style='background:#EFF6FF;color:#1E40AF;-webkit-text-fill-color:#1E40AF;"
            f"font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:10px;"
            f"border:1px solid #BFDBFE;'>🏢 {empresa}</span>"
            f"</div></div>"
            + (f"<p style='color:#475569;font-size:0.82rem;margin:0 0 4px;'>{descricao}</p>"
               if descricao else "")
            + (f"<p style='color:{COLOR_MUTED};font-size:0.72rem;margin:0;'>📅 {criado_em}</p>"
               if criado_em else "")
            + (f"<p style='color:#25D366;font-size:0.72rem;margin:4px 0 0;'>📱 WhatsApp: {whatsapp}</p>"
               if whatsapp else "")
            + "</div>",
            unsafe_allow_html=True,
        )
    with col_del:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        if st.button("🗑️", key=f"del_alerta_{alerta_id}", use_container_width=True,
                     help="Remover este alerta"):
            ok = delete_alerta_sv(alerta_id)
            if ok:
                st.toast("🗑️ Alerta removido.", icon="🗑️")
                st.rerun()
            else:
                st.toast("⚠️ Não foi possível remover.", icon="⚠️")
