"""Supervisão — Alertas e Pontos de Atenção manuais."""
import streamlit as st
from auth import require_staff
from sheets import (get_all_clientes, get_alertas_sv, add_alerta_sv,
                    delete_alerta_sv, update_alerta_gut)
from assistant import send_whatsapp
from ui import (sv_page_header, status_badge, status_color, empty_state,
                COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE)
from gut import calculate_gut, GUT_DISCLAIMER

_PRIO_OPTS = ["Crítica", "Alta", "Média", "Baixa"]


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
        ativo_id = st.text_input("Ativo relacionado (Id, opcional)", placeholder="Ex: AT-2026-001")
        whatsapp = st.text_input(
            "WhatsApp para envio",
            placeholder="Ex: 5511999999999 (com DDI e DDD, sem espaços ou +)",
        )

        st.markdown("**🎯 Prioridade GUT (opcional)**")
        st.caption(f"ℹ️ {GUT_DISCLAIMER} Deixe em branco para definir depois.")
        gc1, gc2, gc3 = st.columns(3)
        with gc1:
            g_ini = st.selectbox("Gravidade", ["—", 1, 2, 3, 4, 5], key="_novoal_g")
        with gc2:
            u_ini = st.selectbox("Urgência", ["—", 1, 2, 3, 4, 5], key="_novoal_u")
        with gc3:
            t_ini = st.selectbox("Tendência", ["—", 1, 2, 3, 4, 5], key="_novoal_t")

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

            novo_id = add_alerta_sv(client_id, empresa_sel, titulo.strip(), descricao.strip(),
                                    prioridade, whatsapp, ativo_id.strip())
            ok = bool(novo_id)
            if ok and g_ini != "—" and u_ini != "—" and t_ini != "—":
                update_alerta_gut(novo_id, g_ini, u_ini, t_ini)
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
        empty_state(
            "Nenhum alerta publicado ainda. "
            "Use o formulário acima para criar pontos de atenção visíveis no portal de cada cliente.",
            icon="🔔",
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

    cor = status_color(prioridade, "prioridade")

    gut_res  = calculate_gut(row.get("Gut_Gravidade"), row.get("Gut_Urgencia"), row.get("Gut_Tendencia"))
    gut_html = (
        f"<span style='margin-left:4px;'>{status_badge(gut_res['prioridade'], 'gut')}</span>"
        f"<span style='font-size:0.62rem;color:{COLOR_MUTED};margin-left:4px;'>GUT {gut_res['score']}</span>"
    ) if gut_res else ""

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
            + status_badge(prioridade, "prioridade")
            + f"<span style='background:#EFF6FF;color:#1E40AF;-webkit-text-fill-color:#1E40AF;"
            f"font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:10px;"
            f"border:1px solid #BFDBFE;'>🏢 {empresa}</span>"
            f"{gut_html}"
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

    with st.expander(f"🎯 GUT — {titulo[:40]}", expanded=False):
        st.caption(f"ℹ️ {GUT_DISCLAIMER}")
        gc1, gc2, gc3 = st.columns(3)
        g_atual = int(row.get("Gut_Gravidade") or 3)
        u_atual = int(row.get("Gut_Urgencia") or 3)
        t_atual = int(row.get("Gut_Tendencia") or 3)
        with gc1:
            g_novo = st.number_input("Gravidade", 1, 5, g_atual, key=f"_gut_g_al_{alerta_id}")
        with gc2:
            u_novo = st.number_input("Urgência", 1, 5, u_atual, key=f"_gut_u_al_{alerta_id}")
        with gc3:
            t_novo = st.number_input("Tendência", 1, 5, t_atual, key=f"_gut_t_al_{alerta_id}")
        obs_novo = st.text_area(
            "Observação técnica", value=str(row.get("Gut_Observacao", "")).strip(),
            key=f"_gut_obs_al_{alerta_id}", height=68,
        )
        preview = calculate_gut(g_novo, u_novo, t_novo)
        if preview:
            st.markdown(
                status_badge(preview["prioridade"], "gut")
                + f" <span style='font-size:0.8rem;color:{COLOR_MUTED};'>Score {preview['score']}</span>",
                unsafe_allow_html=True,
            )
        if st.button("💾 Salvar GUT", key=f"_gut_save_al_{alerta_id}"):
            if update_alerta_gut(alerta_id, g_novo, u_novo, t_novo, obs_novo):
                st.success("GUT atualizado.")
                st.rerun()
            else:
                st.error("Não foi possível salvar o GUT deste alerta.")
