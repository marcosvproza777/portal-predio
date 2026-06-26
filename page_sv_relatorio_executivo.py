"""Supervisão — Gerador de Relatório Executivo Editável em Word (Etapa 6.5)."""
import datetime
import streamlit as st
from auth import require_staff, current_nome

from sheets import (
    get_all_ativos_sv,
    get_all_clientes,
    get_technical_reports,
    get_maintenance_tasks,
    get_maintenance_executions,
    get_alertas_sv,
    get_chamados_v2,
    get_horimetro,
    get_relatorios_executivos,
    add_relatorio_executivo,
    update_relatorio_executivo,
)
from ui import sv_page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE

_SV_ATIVO_ID  = "sv_ativo_id"
_SV_CLIE_ID   = "sv_ativo_cliente_id"   # definido em page_sv_ativos.py
_SV_CLIE_REL  = "sv_ativo_cliente_id_rel"  # chave usada para navegação aqui


# ── Cores status ──────────────────────────────────────────────────────────────
_STATUS_COLOR = {
    "rascunho gerado": ("#94A3B8", "#F8FAFC", "#CBD5E1"),
    "em revisão":      ("#F59E0B", "#FFFBEB", "#FCD34D"),
    "publicado":       ("#10B981", "#F0FDF4", "#86EFAC"),
    "arquivado":       ("#64748B", "#F1F5F9", "#CBD5E1"),
}
_STATUS_DEFAULT = ("#94A3B8", "#F8FAFC", "#CBD5E1")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def render() -> None:
    require_staff()
    sv_view = st.session_state.get("sv_view", "relatorio_executivo")

    if sv_view == "relatorio_executivo":
        _render_gerador()
    else:
        _render_gerador()


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════
def _render_gerador() -> None:
    sv_page_header("📄 Relatório Executivo Word", subtitulo="Geração, revisão e publicação")

    ativo_id  = st.session_state.get(_SV_ATIVO_ID, "")
    client_id = st.session_state.get(_SV_CLIE_REL, "") or st.session_state.get(_SV_CLIE_ID, "")

    # ── Botão Voltar ─────────────────────────────────────────────────────────
    if st.button("← Voltar ao ativo", key="btn_voltar_rel_exec"):
        st.session_state["sv_view"] = "ativo_detalhe"
        st.rerun()

    if not ativo_id:
        st.warning("Nenhum ativo selecionado. Volte ao ativo e clique em 'Gerar Relatório Executivo'.")
        return

    # ── Carregar ativo ────────────────────────────────────────────────────────
    df_ativos, _ = _carregar_ativo(ativo_id)
    if df_ativos is None:
        st.error("Ativo não encontrado.")
        return

    row  = df_ativos.iloc[0]
    nome = str(row.get("Tag", "")).strip() or str(row.get("Nome", "")).strip() or ativo_id

    # ── Deduzir client_id a partir do ativo se não vier do estado ─────────────
    if not client_id:
        client_id = str(row.get("Client_Id", "")).strip() or str(row.get("Empresa", "")).strip().lower()

    # ── Nome do cliente ───────────────────────────────────────────────────────
    cliente_nome = _nome_cliente(client_id)

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};border-radius:10px;"
        f"padding:1rem 1.2rem;margin-bottom:1rem;'>"
        f"<span style='font-size:0.8rem;color:{COLOR_MUTED};'>Ativo selecionado</span><br/>"
        f"<span style='font-size:1rem;font-weight:700;color:{COLOR_NAVY};'>{nome}</span>"
        f"  <span style='color:{COLOR_MUTED};font-size:0.85rem;'>— {cliente_nome}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Abas: Gerar | Histórico ───────────────────────────────────────────────
    tab_gerar, tab_hist = st.tabs(["📝 Gerar novo relatório", "📋 Histórico de relatórios"])

    with tab_gerar:
        _render_form_gerar(ativo_id, client_id, cliente_nome, row)

    with tab_hist:
        _render_historico(ativo_id, client_id)


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULÁRIO DE GERAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
def _render_form_gerar(ativo_id: str, client_id: str, cliente_nome: str, row) -> None:
    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.85rem;margin-bottom:0.5rem;'>"
        "Preencha as opções e clique em <b>Gerar .docx</b>. O arquivo é gerado em memória — "
        "baixe, edite e publique.</p>",
        unsafe_allow_html=True,
    )

    hoje       = datetime.date.today()
    tres_meses = hoje - datetime.timedelta(days=90)

    with st.form("form_relatorio_exec"):
        col_ti, col_op = st.columns([3, 2])
        with col_ti:
            titulo = st.text_input(
                "Título do relatório *",
                value=f"Relatório Executivo — {str(row.get('Tag','') or row.get('Nome','')).strip()}",
                key="rex_titulo",
            )
        with col_op:
            st.markdown("&nbsp;", unsafe_allow_html=True)

        col_ini, col_fim = st.columns(2)
        with col_ini:
            periodo_ini = st.date_input("Período: início *", value=tres_meses, key="rex_inicio")
        with col_fim:
            periodo_fim = st.date_input("Período: fim *",    value=hoje,       key="rex_fim")

        st.markdown("**Seções a incluir**")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            inc_graficos  = st.checkbox("Gráficos executivos", value=True, key="rex_graficos")
            inc_historico = st.checkbox("Histórico técnico",   value=True, key="rex_historico")
        with col_s2:
            inc_manut     = st.checkbox("Manutenções realizadas",  value=True, key="rex_manut")
            inc_manut_fut = st.checkbox("Manutenções a realizar",  value=True, key="rex_manut_fut")
        with col_s3:
            inc_relat     = st.checkbox("Resumo dos relatórios",   value=True, key="rex_relat")
            inc_alertas   = st.checkbox("Alertas e chamados",       value=True, key="rex_alertas")
            inc_rec_cond  = st.checkbox("Recom. por condição",      value=True, key="rex_rec_cond")

        obs_interna = st.text_area(
            "Observação interna (não aparece no documento)",
            placeholder="Uso exclusivo Pred.IO — não será incluída no Word",
            key="rex_obs",
        )

        submitted = st.form_submit_button("📄 Gerar .docx", type="primary", use_container_width=True)

    if not submitted:
        return

    # ── Validação ─────────────────────────────────────────────────────────────
    if not titulo.strip():
        st.error("Informe o título do relatório.")
        return
    if periodo_fim < periodo_ini:
        st.error("A data de fim deve ser posterior ao início.")
        return

    p_ini_str = periodo_ini.strftime("%d/%m/%Y")
    p_fim_str = periodo_fim.strftime("%d/%m/%Y")

    with st.spinner("Coletando dados e gerando o relatório..."):
        dados = _coletar_dados(
            ativo_id      = ativo_id,
            client_id     = client_id,
            cliente_nome  = cliente_nome,
            row           = row,
            periodo_ini   = p_ini_str,
            periodo_fim   = p_fim_str,
            inc_graficos  = inc_graficos,
            inc_historico = inc_historico,
            inc_manut     = inc_manut,
            inc_manut_fut = inc_manut_fut,
            inc_relat     = inc_relat,
            inc_alertas   = inc_alertas,
            inc_rec_cond  = inc_rec_cond,
        )

        try:
            from report_word_generator import gerar_relatorio_word
            docx_bytes = gerar_relatorio_word(dados)
        except Exception as exc:
            st.error(f"Erro ao gerar o Word: {exc}")
            return

        # Registra na aba RelatoriosExecutivos
        nome_autor = current_nome() or "Supervisor"
        rel_id     = add_relatorio_executivo(
            client_id      = client_id,
            ativo_id       = ativo_id,
            titulo         = titulo.strip(),
            gerado_por     = nome_autor,
            periodo_inicio = p_ini_str,
            periodo_fim    = p_fim_str,
            obs_interna    = obs_interna.strip(),
        )

    st.success("Relatório gerado com sucesso! Baixe, edite e use o painel abaixo para publicar.")

    # ── Download ──────────────────────────────────────────────────────────────
    nome_arquivo = _slug_filename(titulo) + ".docx"
    st.download_button(
        label      = "⬇️ Baixar relatório .docx",
        data       = docx_bytes,
        file_name  = nome_arquivo,
        mime       = "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )

    if rel_id:
        st.caption(f"Relatório registrado — ID: {rel_id}  ·  Status: Rascunho gerado")
        _render_acoes_status(rel_id, client_id, "Rascunho gerado")


# ═══════════════════════════════════════════════════════════════════════════════
# AÇÕES DE STATUS
# ═══════════════════════════════════════════════════════════════════════════════
def _render_acoes_status(rel_id: str, client_id: str, status_atual: str) -> None:
    """Botões para mover o relatório no fluxo: Rascunho → Em revisão → Publicado → Arquivado."""
    st.markdown(
        f"<div style='background:#F8FAFC;border:1px solid {COLOR_BORDER};"
        f"border-radius:8px;padding:0.75rem 1rem;margin-top:0.5rem;'>"
        f"<span style='font-size:0.8rem;color:{COLOR_MUTED};'>Fluxo do relatório</span></div>",
        unsafe_allow_html=True,
    )

    fluxo = ["Rascunho gerado", "Em revisão", "Publicado", "Arquivado"]
    idx   = next((i for i, s in enumerate(fluxo) if s.lower() == status_atual.lower()), 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        if idx < 1:
            if st.button("📋 Enviar para revisão", key=f"btn_revisao_{rel_id}", use_container_width=True):
                if update_relatorio_executivo(rel_id, client_id, Status="Em revisão"):
                    st.success("Status atualizado para 'Em revisão'.")
                    st.rerun()
    with col2:
        if idx < 2:
            if st.button("✅ Publicar para cliente", key=f"btn_pub_{rel_id}", use_container_width=True):
                if update_relatorio_executivo(rel_id, client_id, Status="Publicado"):
                    st.success("Relatório publicado — agora visível para o cliente.")
                    st.rerun()
    with col3:
        if idx < 3:
            if st.button("📦 Arquivar", key=f"btn_arq_{rel_id}", use_container_width=True):
                if update_relatorio_executivo(rel_id, client_id, Status="Arquivado"):
                    st.success("Relatório arquivado.")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# HISTÓRICO DE RELATÓRIOS DO ATIVO
# ═══════════════════════════════════════════════════════════════════════════════
def _render_historico(ativo_id: str, client_id: str) -> None:
    df = get_relatorios_executivos(client_id, ativo_id=ativo_id)

    if df.empty:
        st.info("Nenhum relatório executivo gerado ainda para este ativo.")
        return

    for _, rel in df.iterrows():
        rel_id    = str(rel.get("Id",            "")).strip()
        titulo    = str(rel.get("Titulo",         "Relatório")).strip()
        status    = str(rel.get("Status",         "Rascunho gerado")).strip()
        gerado_em = str(rel.get("Gerado_Em",      "")).strip()
        gerado_p  = str(rel.get("Gerado_Por",     "")).strip()
        p_ini     = str(rel.get("Periodo_Inicio", "")).strip()
        p_fim     = str(rel.get("Periodo_Fim",    "")).strip()
        versao    = str(rel.get("Versao",         "1")).strip()

        sc, bg, bd = _STATUS_COLOR.get(status.lower(), _STATUS_DEFAULT)

        st.markdown(
            f"<div style='background:{bg};border:1px solid {bd};border-radius:10px;"
            f"padding:0.85rem 1.1rem;margin-bottom:0.75rem;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.93rem;'>{titulo}</span>"
            f"<span style='background:{sc}22;color:{sc};border:1px solid {sc}55;"
            f"border-radius:5px;padding:2px 8px;font-size:0.75rem;font-weight:600;'>{status}</span>"
            f"</div>"
            f"<div style='margin-top:0.3rem;color:{COLOR_MUTED};font-size:0.78rem;'>"
            f"Gerado em {gerado_em}  ·  Por: {gerado_p}  ·  Período: {p_ini} – {p_fim}  "
            f"·  Versão: {versao}  ·  ID: {rel_id}"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Ações de status inline
        _render_acoes_status(rel_id, client_id, status)
        st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# COLETA DE DADOS PARA O GERADOR
# ═══════════════════════════════════════════════════════════════════════════════
def _coletar_dados(
    ativo_id: str,
    client_id: str,
    cliente_nome: str,
    row,
    periodo_ini: str,
    periodo_fim: str,
    inc_graficos: bool  = True,
    inc_historico: bool = True,
    inc_manut: bool     = True,
    inc_manut_fut: bool = True,
    inc_relat: bool     = True,
    inc_alertas: bool   = True,
    inc_rec_cond: bool  = True,
) -> dict:
    """Coleta todos os dados necessários do Sheets e monta o dict para o gerador."""
    import pandas as pd

    # Horímetro
    horimetro = get_horimetro(ativo_id)

    # Relatórios técnicos publicados
    df_rel = pd.DataFrame()
    if inc_relat or inc_historico:
        try:
            df_rel = get_technical_reports(
                client_id = client_id,
                ativo_id  = ativo_id,
                staff     = True,
            )
            df_rel = _filtrar_periodo(df_rel, "Data_Relatorio", periodo_ini, periodo_fim)
        except Exception:
            df_rel = pd.DataFrame()

    # Manutenções executadas
    df_mex = pd.DataFrame()
    if inc_manut or inc_historico:
        try:
            df_mex = get_maintenance_executions(
                client_id = client_id,
                ativo_id  = ativo_id,
            )
            df_mex = _filtrar_periodo(df_mex, "Executado_Em", periodo_ini, periodo_fim)
            # Nunca expõe obs interna
            if "Obs_Interna" in df_mex.columns:
                df_mex = df_mex.drop(columns=["Obs_Interna"])
        except Exception:
            df_mex = pd.DataFrame()

    # Manutenções pendentes
    df_mpend = pd.DataFrame()
    if inc_manut_fut:
        try:
            df_mpend = get_maintenance_tasks(
                client_id = client_id,
                ativo_id  = ativo_id,
                staff     = True,
            )
            # filtrar apenas as não concluídas
            if "Status" in df_mpend.columns:
                df_mpend = df_mpend[~df_mpend["Status"].str.lower().str.contains("conclu|arquiv", na=False)]
        except Exception:
            df_mpend = pd.DataFrame()

    # Alertas
    df_al = pd.DataFrame()
    if inc_alertas or inc_historico:
        try:
            df_al = get_alertas_sv(client_id=client_id)
            if not df_al.empty and "Ativo_Id" in df_al.columns:
                df_al = df_al[df_al["Ativo_Id"].str.strip() == ativo_id.strip()]
            df_al = _filtrar_periodo(df_al, "Data", periodo_ini, periodo_fim)
        except Exception:
            df_al = pd.DataFrame()

    # Chamados
    df_cham = pd.DataFrame()
    if inc_alertas or inc_historico:
        try:
            df_cham = get_chamados_v2(client_id=client_id, ativo_id=ativo_id)
            df_cham = _filtrar_periodo(df_cham, "Aberto_Em", periodo_ini, periodo_fim)
        except Exception:
            df_cham = pd.DataFrame()

    # Ativo como dict para o gerador
    ativo_dict = dict(row) if row is not None else {}

    return {
        "ativo":                     ativo_dict,
        "cliente_nome":              cliente_nome,
        "horimetro":                 horimetro,
        "periodo_inicio":            periodo_ini,
        "periodo_fim":               periodo_fim,
        "relatorios":                df_rel   if not df_rel.empty   else pd.DataFrame(),
        "manutencoes_executadas":    df_mex   if not df_mex.empty   else pd.DataFrame(),
        "manutencoes_pendentes":     df_mpend if not df_mpend.empty else pd.DataFrame(),
        "alertas":                   df_al    if not df_al.empty    else pd.DataFrame(),
        "chamados":                  df_cham  if not df_cham.empty  else pd.DataFrame(),
        # flags de seção
        "incluir_graficos":               inc_graficos,
        "incluir_historico":              inc_historico,
        "incluir_manutencoes":            inc_manut,
        "incluir_manutencoes_futuras":    inc_manut_fut,
        "incluir_relatorios":             inc_relat,
        "incluir_alertas":                inc_alertas,
        "incluir_recomendacoes_condicao": inc_rec_cond,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _carregar_ativo(ativo_id: str):
    try:
        df = get_all_ativos_sv()
    except Exception:
        return None, None
    if df is None or df.empty:
        return None, None
    id_col = "Id" if "Id" in df.columns else df.columns[0]
    match  = df[df[id_col].astype(str).str.strip() == ativo_id.strip()]
    if match.empty:
        return None, None
    return match, False


def _nome_cliente(client_id: str) -> str:
    try:
        df_cli = get_all_clientes()
        cid_col = "Client_Id" if "Client_Id" in df_cli.columns else "Cliente_Id"
        if cid_col in df_cli.columns:
            m = df_cli[df_cli[cid_col].astype(str).str.strip().str.lower() == client_id.strip().lower()]
            if not m.empty:
                return str(m.iloc[0].get("Empresa", client_id)).strip()
    except Exception:
        pass
    return client_id


def _filtrar_periodo(df, col_data: str, ini: str, fim: str):
    import pandas as pd
    if df is None or df.empty or col_data not in df.columns:
        return df if df is not None else pd.DataFrame()
    try:
        df = df.copy()
        df["_dt"] = pd.to_datetime(df[col_data], dayfirst=True, errors="coerce")
        dt_ini = pd.to_datetime(ini, dayfirst=True, errors="coerce")
        dt_fim = pd.to_datetime(fim, dayfirst=True, errors="coerce")
        mask = pd.Series([True] * len(df), index=df.index)
        if pd.notna(dt_ini):
            mask &= df["_dt"] >= dt_ini
        if pd.notna(dt_fim):
            mask &= df["_dt"] <= dt_fim
        return df[mask].drop(columns=["_dt"]).reset_index(drop=True)
    except Exception:
        return df


def _slug_filename(titulo: str) -> str:
    import unicodedata, re
    s = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip()
    s = re.sub(r"[\s-]+", "_", s)
    return s[:60] or "relatorio_executivo"
