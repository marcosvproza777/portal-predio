"""Dashboard principal — cards de resumo."""
import pandas as pd
import streamlit as st
from auth import current_client_id, current_empresa
from sheets import get_relatorios, get_chamados, get_ativos
from ui import page_header, COLOR_NAVY, COLOR_BLUE, COLOR_CYAN, COLOR_CARD, COLOR_BORDER


def render(logo_b64: str) -> None:
    empresa    = current_empresa()
    client_id  = current_client_id()

    # Logo + cabeçalho
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        if logo_b64:
            st.markdown(
                f"<div style='padding-top:0.4rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' style='width:80px;'/></div>",
                unsafe_allow_html=True,
            )
    with col_title:
        page_header("Dashboard", f"Bem-vindo, <strong>{empresa}</strong>")

    # ── Cards de resumo ───────────────────────────────────────────────────────
    df_rel  = get_relatorios(client_id)
    df_cham = get_chamados(client_id)
    df_ativ = get_ativos(client_id)

    total_rel    = len(df_rel)
    chamados_ab  = len(df_cham[df_cham.get("Status", pd.Series(dtype=str))
                               .str.lower().str.strip() == "aberto"]) \
                   if not df_cham.empty and "Status" in df_cham.columns else 0
    equip_monit  = df_ativ["Tag"].nunique() if not df_ativ.empty and "Tag" in df_ativ.columns else 0
    ultimo_rel   = (df_rel.iloc[0]["Data_Relatorio"]
                   if total_rel and "Data_Relatorio" in df_rel.columns else "—")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📁 Total de Relatórios",     total_rel)
    c2.metric("🔧 Chamados Abertos",         chamados_ab)
    c3.metric("⚙️ Equipamentos Monitorados", equip_monit)
    c4.metric("📅 Último Relatório",         str(ultimo_rel))

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Atalhos ───────────────────────────────────────────────────────────────
    cards = [
        ("farois",     "🚦", "Faróis de Condição",
         "Saúde dos equipamentos em tempo real"),
        ("relatorios", "📁", "Meus Relatórios",
         "Acesse e baixe seus laudos técnicos"),
        ("assistente", "🤖", "Assistente Técnico",
         "Tire dúvidas sobre seus equipamentos e relatórios"),
        ("chamados",   "🔧", "Chamados Técnicos",
         "Abra um chamado em caso de dúvida ou emergência"),
    ]

    cols = st.columns(2)
    for i, (page_key, icon, title, desc) in enumerate(cards):
        with cols[i % 2]:
            st.markdown(
                f"""<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};
                    border-radius:12px;padding:1.4rem 1.6rem;margin-bottom:1rem;
                    box-shadow:0 2px 12px rgba(27,42,107,0.07);cursor:pointer;'>
                  <div style='font-size:2rem;margin-bottom:0.4rem;'>{icon}</div>
                  <h3 style='color:{COLOR_NAVY};margin:0 0 0.3rem;font-size:1.1rem;'>{title}</h3>
                  <p style='color:#64748b;font-size:0.85rem;margin:0;'>{desc}</p>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button(f"Acessar →", key=f"dash_{page_key}", use_container_width=True):
                st.session_state["page"] = page_key
                st.rerun()

    # ── Últimos relatórios ────────────────────────────────────────────────────
    if total_rel:
        st.markdown("---")
        st.markdown(
            f"<h3 style='color:{COLOR_NAVY};'>Últimos Relatórios</h3>",
            unsafe_allow_html=True,
        )
        preview = df_rel.head(5)
        for _, row in preview.iterrows():
            _render_report_row(row)


def _render_report_row(row) -> None:
    from ui import COLOR_NAVY, COLOR_BORDER, COLOR_CARD
    titulo = str(row.get("Titulo", row.get("Tag", "Relatório"))).strip()
    tipo   = str(row.get("Tipo_Servico", row.get("Tipo", ""))).strip()
    data   = str(row.get("Data_Relatorio", row.get("Data", ""))).strip()
    planta = str(row.get("Planta", "")).strip()
    url    = str(row.get("Arquivo_Url", row.get("Link_Documento", ""))).strip()

    col_info, col_btn = st.columns([5, 1])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:8px;padding:10px 16px;margin-bottom:6px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};'>{titulo}</span>"
            f"<span style='color:#94a3b8;font-size:0.8rem;margin-left:10px;'>{tipo}</span>"
            f"<span style='color:#94a3b8;font-size:0.8rem;margin-left:10px;'>📅 {data}</span>"
            f"{'<span style=\"color:#94a3b8;font-size:0.8rem;margin-left:10px;\">🏭 ' + planta + '</span>' if planta else ''}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        if url and url.lower() not in ("", "nan", "none"):
            st.link_button("📄 Abrir", url, use_container_width=True)
