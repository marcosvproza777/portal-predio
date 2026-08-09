"""Supervisão — Relatórios Técnicos: CRUD, publicação, impacto no score."""
import datetime
import streamlit as st
from auth import require_staff, current_nome

from sheets import (
    get_all_clientes,
    get_ativos,
    get_technical_reports,
    get_technical_report_by_id,
    add_technical_report,
    update_technical_report,
    publish_technical_report,
    archive_technical_report,
    delete_technical_report_full,
    update_report_gut,
    ORIGEM_UPLOAD_DIRETO,
    ORIGEM_GOOGLE_DRIVE,
    ORIGEM_APP_RELATORIOS,
    ORIGEM_UPLOAD_MANUAL_VIBRACAO,
)
from ui import (
    sv_page_header, status_badge,
    COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE,
)
from gut import calculate_gut, GUT_DISCLAIMER

# ── Constantes ────────────────────────────────────────────────────────────────

_TIPOS_SERVICO = [
    "Análise de Vibração",
    "Análise de Óleo",
    "Termografia",
    "Inspeção Técnica",
    "Análise Preditiva",
    "Relatório de Alarme",
    "Outro",
]

_SEVERIDADES = ["Normal", "Atenção", "Crítico", "Urgente"]

_SEV_COLOR = {
    "normal":   ("#10B981", "#F0FDF4", "#86EFAC", "#065F46"),
    "atenção":  ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E"),
    "atencao":  ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E"),
    "crítico":  ("#EF4444", "#FEF2F2", "#FCA5A5", "#991B1B"),
    "critico":  ("#EF4444", "#FEF2F2", "#FCA5A5", "#991B1B"),
    "urgente":  ("#7C3AED", "#F5F3FF", "#C4B5FD", "#4C1D95"),
}
_SEV_DEFAULT = ("#94A3B8", "#F8FAFC", "#CBD5E1", "#475569")

_STATUS_COLOR = {
    "rascunho":    ("#94A3B8", "#F8FAFC", "#CBD5E1"),
    "em revisão":  ("#7C3AED", "#F5F3FF", "#C4B5FD"),
    "publicado":   ("#10B981", "#F0FDF4", "#86EFAC"),
    "arquivado":   ("#64748B", "#F1F5F9", "#CBD5E1"),
}
# Status que ainda podem ser publicados pela Supervisão — Rascunho (criado
# no Portal) e Em revisão (chegou publicado direto pelo App Relatórios,
# Etapa 3) usam o mesmo botão "Publicar".
_STATUS_PUBLICAVEIS = ("Rascunho", "Em revisão", "")
_STATUS_DEFAULT = ("#94A3B8", "#F8FAFC", "#CBD5E1")

_KEY_REP_ID = "_svrel_rep_id"

# Prefill de sessão consumido uma única vez ao abrir um relatório NOVO — usado
# pelo botão "Adicionar Relatório de Vibração" (lista de relatórios e detalhe
# do ativo) pra já abrir o formulário com tipo/origem/status/cliente/ativo
# certos, sem duplicar o formulário genérico.
_KEY_PREFILL_TIPO       = "_svrel_prefill_tipo"
_KEY_PREFILL_ORIGEM     = "_svrel_prefill_origem"
_KEY_PREFILL_STATUS     = "_svrel_prefill_status_inicial"
_KEY_PREFILL_CLIENTE_ID = "_svrel_prefill_cliente_id"
_KEY_PREFILL_ATIVO_ID   = "_svrel_prefill_ativo_id"

_ORIGEM_OPTS = [
    (ORIGEM_UPLOAD_DIRETO,          "📤 Upload direto (PDF do computador)"),
    (ORIGEM_UPLOAD_MANUAL_VIBRACAO, "📳 Vibração — Upload Manual"),
    (ORIGEM_GOOGLE_DRIVE,           "🔗 Google Drive / URL"),
    (ORIGEM_APP_RELATORIOS,         "🔌 App Relatórios Pred.IO (em breve)"),
]


_WIDGET_KEYS_NOVO_RELATORIO = (
    "_svrel_f_cliente", "_svrel_f_cliente_id", "_svrel_f_ativo",
    "_svrel_f_tipo_serv", "_svrel_f_origem", "_svrel_f_pdf", "_svrel_f_url",
)


def _clear_prefill() -> None:
    for k in (_KEY_PREFILL_TIPO, _KEY_PREFILL_ORIGEM, _KEY_PREFILL_STATUS,
              _KEY_PREFILL_CLIENTE_ID, _KEY_PREFILL_ATIVO_ID):
        st.session_state.pop(k, None)


def abrir_novo_relatorio_vibracao(cliente_id: str = "", ativo_id: str = "") -> None:
    """Prepara e navega para o formulário de Novo Relatório já configurado
    como Relatório de Vibração — usada pelo botão na lista de Relatórios e
    pelo botão no detalhe do ativo (que já manda cliente_id/ativo_id).

    Limpa o estado dos campos do formulário antes de preencher de novo —
    sem isso, um cliente/ativo escolhido numa sessão de "Novo Relatório"
    anterior ficaria "grudado" no formulário (widgets com key fixa só
    respeitam um novo valor default se a key ainda não existir)."""
    for k in _WIDGET_KEYS_NOVO_RELATORIO:
        st.session_state.pop(k, None)
    st.session_state.pop(_KEY_REP_ID, None)
    st.session_state[_KEY_PREFILL_TIPO]       = "Análise de Vibração"
    st.session_state[_KEY_PREFILL_ORIGEM]     = ORIGEM_UPLOAD_MANUAL_VIBRACAO
    st.session_state[_KEY_PREFILL_STATUS]     = "Em revisão"
    st.session_state[_KEY_PREFILL_CLIENTE_ID] = cliente_id
    st.session_state[_KEY_PREFILL_ATIVO_ID]   = ativo_id
    st.session_state["sv_view"] = "relatorio_novo"


def _origem_default(report: dict | None) -> str:
    """Origem padrão ao abrir o formulário — infere pelo conteúdo já salvo
    para relatórios antigos que não têm a coluna Origem preenchida."""
    if not report:
        prefill = st.session_state.get(_KEY_PREFILL_ORIGEM, "")
        return prefill or ORIGEM_UPLOAD_DIRETO
    origem = (report.get("Origem") or "").strip()
    if origem in (ORIGEM_UPLOAD_DIRETO, ORIGEM_GOOGLE_DRIVE, ORIGEM_APP_RELATORIOS,
                  ORIGEM_UPLOAD_MANUAL_VIBRACAO):
        return origem
    if (report.get("Storage_Path") or "").strip():
        return ORIGEM_UPLOAD_DIRETO
    return ORIGEM_GOOGLE_DRIVE


# ── Entry point ───────────────────────────────────────────────────────────────

def render() -> None:
    require_staff()
    sv_view = st.session_state.get("sv_view", "relatorios_sv")
    if sv_view == "relatorio_novo":
        _render_form(report=None)
    elif sv_view == "relatorio_editar":
        rep_id = st.session_state.get(_KEY_REP_ID, "")
        rep    = get_technical_report_by_id(rep_id) if rep_id else None
        _render_form(report=rep)
    else:
        _render_lista()


# ═══════════════════════════════════════════════════════════════════════════════
# LISTA
# ═══════════════════════════════════════════════════════════════════════════════

def _render_lista() -> None:
    sv_page_header(
        "📁 Relatórios Técnicos",
        "Gerencie, publique e acompanhe os relatórios técnicos dos clientes.",
    )

    col_btn, col_vib, col_resumo = st.columns([1.4, 1.8, 1.8])
    with col_btn:
        if st.button("➕ Novo Relatório", use_container_width=True, type="primary"):
            _clear_prefill()
            st.session_state["sv_view"] = "relatorio_novo"
            st.rerun()
    with col_vib:
        if st.button("📳 Adicionar Relatório de Vibração", use_container_width=True):
            abrir_novo_relatorio_vibracao()
            st.rerun()
    with col_resumo:
        from resumo_executivo_ui import render_resumo_executivo_button
        render_resumo_executivo_button(key_prefix="svrel_resexec")

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            status_opts = ["Todos", "Rascunho", "Em revisão", "Publicado", "Arquivado"]
            f_status = st.selectbox("Status", status_opts, key="_svrel_f_status")
        with c2:
            sev_opts = ["Todas"] + _SEVERIDADES
            f_sev = st.selectbox("Severidade", sev_opts, key="_svrel_f_sev")
        with c3:
            tipo_opts = ["Todos"] + _TIPOS_SERVICO
            f_tipo = st.selectbox("Tipo de Serviço", tipo_opts, key="_svrel_f_tipo")
        with c4:
            try:
                df_cli = get_all_clientes()
                cli_map = {
                    str(r.get("Empresa", "")).strip(): str(r.get("Client_Id", r.get("Cliente_Id", ""))).strip()
                    for _, r in df_cli.iterrows()
                    if str(r.get("Empresa", "")).strip()
                }
                cli_list = ["Todos os clientes"] + sorted(cli_map.keys())
            except Exception:
                cli_map  = {}
                cli_list = ["Todos os clientes"]
            f_cli_label = st.selectbox("Cliente", cli_list, key="_svrel_f_cli")

    # Carrega relatórios
    f_client_id = cli_map.get(f_cli_label, "") if f_cli_label != "Todos os clientes" else ""
    df = get_technical_reports(
        client_id = f_client_id,
        status    = "" if f_status == "Todos" else f_status,
        staff     = True,
    )

    # Filtros adicionais em memória
    if not df.empty and f_sev != "Todas":
        df = df[df["Severidade"].str.strip() == f_sev]
    if not df.empty and f_tipo != "Todos":
        df = df[df["Tipo_Servico"].str.strip() == f_tipo]

    # Métricas rápidas
    mc = st.columns(4)
    total    = len(df) if not df.empty else 0
    rascunho = len(df[df["Status"].str.strip() == "Rascunho"])  if not df.empty else 0
    publics  = len(df[df["Status"].str.strip() == "Publicado"]) if not df.empty else 0
    criticos = (
        len(df[df["Severidade"].str.strip().isin(["Crítico", "Urgente"])])
        if not df.empty else 0
    )
    for col, (label, val, color) in zip(mc, [
        ("Total", total, COLOR_BLUE),
        ("Rascunhos", rascunho, "#94A3B8"),
        ("Publicados", publics, "#10B981"),
        ("Críticos/Urgentes", criticos, "#EF4444"),
    ]):
        with col:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-left:4px solid {color};border-radius:10px;"
                f"padding:0.75rem 1rem;text-align:center;'>"
                f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:0 0 4px;"
                f"text-transform:uppercase;letter-spacing:.08em;'>{label}</p>"
                f"<p style='font-size:1.6rem;font-weight:900;color:{color};margin:0;'>{val}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.85rem;margin:1rem 0 0.5rem;'>"
        f"{total} relatório(s)</p>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("Nenhum relatório encontrado com os filtros selecionados.")
        return

    for _, row in df.iterrows():
        _render_card(row)


def _sev_cfg(sev: str) -> tuple:
    return _SEV_COLOR.get(sev.strip().lower(), _SEV_DEFAULT)


def _status_cfg(status: str) -> tuple:
    return _STATUS_COLOR.get(status.strip().lower(), _STATUS_DEFAULT)


def _render_card(row) -> None:
    rep_id     = str(row.get("Id",            "")).strip()
    titulo     = str(row.get("Titulo",         "Sem título")).strip()
    tipo       = str(row.get("Tipo_Servico",   "")).strip()
    sev        = str(row.get("Severidade",     "Normal")).strip()
    data       = str(row.get("Data_Relatorio", "")).strip()
    planta     = str(row.get("Planta",         "")).strip()
    equipamento= str(row.get("Equipamento",    "")).strip()
    status     = str(row.get("Status",         "Rascunho")).strip()
    cliente_id = str(row.get("Cliente_Id",     "")).strip()
    score_imp  = str(row.get("Score_Impacto",  "")).strip()
    resumo     = str(row.get("Resumo",         "")).strip()

    sc, sb, sbo, st_ = _sev_cfg(sev)
    stc, stb, stbo   = _status_cfg(status)

    meta = []
    if tipo:       meta.append(f"📋 {tipo}")
    if data:       meta.append(f"📅 {data}")
    if planta:     meta.append(f"🏭 {planta}")
    if equipamento:meta.append(f"⚙️ {equipamento}")
    if cliente_id: meta.append(f"👤 {cliente_id}")
    meta_html = "  ·  ".join(
        f"<span style='color:{COLOR_MUTED};font-size:0.78rem;'>{m}</span>" for m in meta
    )

    score_html = ""
    if score_imp and score_imp not in ("", "nan", "0"):
        try:
            si = int(score_imp)
            sc_color = "#10B981" if si >= 0 else "#EF4444"
            score_html = (
                f"<span style='font-size:0.72rem;font-weight:700;color:{sc_color};"
                f"margin-left:8px;'>Score: {si:+d}</span>"
            )
        except Exception:
            pass

    col_info, col_btns = st.columns([6, 2])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:5px solid {sc};border-radius:10px;"
            f"padding:0.9rem 1.1rem;margin-bottom:3px;'>"
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:flex-start;flex-wrap:wrap;gap:6px;margin-bottom:5px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.97rem;'>{titulo}</span>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>"
            f"<span style='background:{sb};color:{st_};-webkit-text-fill-color:{st_};"
            f"border:1px solid {sbo};font-size:0.67rem;font-weight:700;"
            f"padding:2px 10px;border-radius:12px;'>{sev}</span>"
            f"<span style='background:{stb};color:{stc};-webkit-text-fill-color:{stc};"
            f"border:1px solid {stbo};font-size:0.67rem;font-weight:700;"
            f"padding:2px 10px;border-radius:12px;'>{status}</span>"
            + score_html
            + f"</div></div>"
            f"<div style='margin-bottom:4px;'>{meta_html}</div>"
            + (f"<p style='color:#475569;font-size:0.8rem;margin:4px 0 0;"
               f"line-height:1.5;'>{resumo[:180]}{'…' if len(resumo)>180 else ''}</p>"
               if resumo and resumo.lower() not in ("", "nan") else "")
            + "</div>",
            unsafe_allow_html=True,
        )
    with col_btns:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        if st.button("✏️ Editar", key=f"_svrel_edit_{rep_id}", use_container_width=True):
            st.session_state[_KEY_REP_ID] = rep_id
            st.session_state["sv_view"]   = "relatorio_editar"
            st.rerun()
        if status in _STATUS_PUBLICAVEIS:
            if st.button("📢 Publicar", key=f"_svrel_pub_{rep_id}", use_container_width=True,
                         type="primary"):
                st.session_state[f"_svrel_confirm_pub_{rep_id}"] = True
                st.rerun()
        if status == "Publicado":
            if st.button("🗂️ Arquivar", key=f"_svrel_arch_{rep_id}", use_container_width=True):
                st.session_state[f"_svrel_confirm_arch_{rep_id}"] = True
                st.rerun()
        if st.button("🗑️ Excluir", key=f"_svrel_del_{rep_id}", use_container_width=True):
            st.session_state[f"_svrel_confirm_del_{rep_id}"] = True
            st.rerun()

    # Confirmação publicar
    # IMPORTANTE: usar .get() aqui, não .pop() — .pop() já remove a chave na
    # hora de checar, então no rerun causado pelo clique em "Confirmar" (um
    # segundo rerun, distinto do que abriu a confirmação) a chave já não
    # existe mais e este bloco inteiro (com o botão "Confirmar" dentro) nem
    # chega a ser executado, perdendo o clique silenciosamente — sintoma:
    # "clico em confirmar e não acontece nada". A chave só deve ser limpa
    # explicitamente ao cancelar ou ao concluir a ação (senão fica "presa"
    # em True e a confirmação reaparece sozinha na próxima vez que o card
    # for renderizado).
    if st.session_state.get(f"_svrel_confirm_pub_{rep_id}", False):
        sev_delta = {
            "urgente": -25, "crítico": -15, "critico": -15,
            "atenção": -7, "atencao": -7, "normal": 2,
        }.get(sev.strip().lower(), 0)
        st.warning(
            f"**Publicar '{titulo}'?**  \n"
            f"Severidade: **{sev}** · Score do ativo: **{sev_delta:+d} pts**  \n"
            f"Clique novamente em Publicar para confirmar."
        )
        col_ok, col_no, _ = st.columns([1, 1, 3])
        with col_ok:
            if st.button("✅ Confirmar", key=f"_svrel_pubOK_{rep_id}", type="primary",
                         use_container_width=True):
                with st.spinner("Publicando..."):
                    result = publish_technical_report(rep_id, current_nome())
                st.session_state.pop(f"_svrel_confirm_pub_{rep_id}", None)
                if result.get("ok"):
                    msg = "Relatório publicado com sucesso."
                    if result.get("score_atualizado"):
                        msg += f" Score do ativo ajustado em {result['score_delta']:+d} pts."
                    if result.get("alerta"):
                        msg += " Alerta interno gerado."
                    # indexação para o Assistente Técnico já roda dentro de
                    # publish_technical_report() (Etapa 5) — nada a fazer aqui.
                    st.success(msg)
                    from sheets import load_sheet as _ls
                    _ls.clear()
                    st.rerun()
                else:
                    st.error(result.get("erro", "Erro ao publicar."))
        with col_no:
            if st.button("❌ Cancelar", key=f"_svrel_pubNO_{rep_id}", use_container_width=True):
                st.session_state.pop(f"_svrel_confirm_pub_{rep_id}", None)
                st.rerun()

    # Confirmação arquivar — mesmo motivo do .get() acima
    if st.session_state.get(f"_svrel_confirm_arch_{rep_id}", False):
        col_ok2, col_no2, _ = st.columns([1, 1, 3])
        st.warning(f"Arquivar '{titulo}'? O cliente não poderá mais acessá-lo.")
        with col_ok2:
            if st.button("✅ Arquivar", key=f"_svrel_archOK_{rep_id}", type="primary",
                         use_container_width=True):
                archive_technical_report(rep_id)
                st.session_state.pop(f"_svrel_confirm_arch_{rep_id}", None)
                from sheets import load_sheet as _ls
                _ls.clear()
                st.rerun()
        with col_no2:
            if st.button("❌ Cancelar", key=f"_svrel_archNO_{rep_id}", use_container_width=True):
                st.session_state.pop(f"_svrel_confirm_arch_{rep_id}", None)
                st.rerun()

    # Confirmação excluir — diferente de Rascunho, apagar um Publicado
    # também reverte o Score do ativo e remove chunks/timeline (ver
    # delete_technical_report_full em sheets.py). Mesmo motivo do .get()
    # acima (não usar .pop() aqui).
    if st.session_state.get(f"_svrel_confirm_del_{rep_id}", False):
        if status == "Publicado":
            st.error(
                f"**Apagar '{titulo}' (PUBLICADO)?** O cliente pode já ter visto este "
                f"relatório. Isso remove o relatório, os chunks indexados no Assistente "
                f"Técnico e o evento no histórico do ativo, e reverte o impacto no Score. "
                f"**Esta ação não pode ser desfeita.**"
            )
        else:
            st.warning(f"Apagar '{titulo}' permanentemente? Esta ação não pode ser desfeita.")
        col_ok3, col_no3, _ = st.columns([1, 1, 3])
        with col_ok3:
            if st.button("🗑️ Confirmar exclusão", key=f"_svrel_delOK_{rep_id}",
                         type="primary", use_container_width=True):
                result = delete_technical_report_full(rep_id)
                st.session_state.pop(f"_svrel_confirm_del_{rep_id}", None)
                from sheets import load_sheet as _ls
                _ls.clear()
                if result.get("ok"):
                    st.success("Relatório excluído.")
                    st.rerun()
                else:
                    st.error(result.get("erro", "Erro ao excluir."))
        with col_no3:
            if st.button("❌ Cancelar", key=f"_svrel_delNO_{rep_id}", use_container_width=True):
                st.session_state.pop(f"_svrel_confirm_del_{rep_id}", None)
                st.rerun()

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULÁRIO CRIAR / EDITAR
# ═══════════════════════════════════════════════════════════════════════════════

def _render_form(report: dict | None) -> None:
    editing = report is not None
    label   = "✏️ Editar Relatório" if editing else "➕ Novo Relatório Técnico"
    sv_page_header(label, back_label="Voltar à lista", back_view="relatorios_sv")

    # Defaults — para relatório novo, Cliente/Ativo/Tipo consultam o prefill
    # de sessão (abrir_novo_relatorio_vibracao) antes de cair no default.
    _PREFILL_MAP = {
        "Cliente_Id":   _KEY_PREFILL_CLIENTE_ID,
        "Ativo_Id":     _KEY_PREFILL_ATIVO_ID,
        "Tipo_Servico": _KEY_PREFILL_TIPO,
    }

    def _d(k: str, default="") -> str:
        if editing:
            return report.get(k, "") or ""
        prefill_key = _PREFILL_MAP.get(k)
        if prefill_key:
            v = st.session_state.get(prefill_key, "")
            if v:
                return v
        return default

    # ── Selects de contexto ───────────────────────────────────────────────────
    try:
        df_cli = get_all_clientes()
        cli_rows = [
            (str(r.get("Empresa", "")).strip(),
             str(r.get("Client_Id", r.get("Cliente_Id", ""))).strip())
            for _, r in df_cli.iterrows()
            if str(r.get("Empresa", "")).strip()
        ]
        cli_labels = [f"{emp} ({cid})" for emp, cid in cli_rows]
        cli_ids    = [cid for _, cid in cli_rows]
    except Exception:
        cli_labels, cli_ids, cli_rows = [], [], []

    st.markdown(
        f"<p style='font-size:0.75rem;color:{COLOR_MUTED};margin:0 0 0.25rem;"
        f"font-weight:700;text-transform:uppercase;letter-spacing:.08em;'>Cliente *</p>",
        unsafe_allow_html=True,
    )
    if cli_labels:
        cur_cid = _d("Cliente_Id")
        try:
            cur_idx = cli_ids.index(cur_cid) if cur_cid in cli_ids else 0
        except ValueError:
            cur_idx = 0
        cli_sel_idx = st.selectbox(
            "Cliente *", cli_labels, index=cur_idx,
            key="_svrel_f_cliente", label_visibility="collapsed",
        )
        sel_cid = cli_ids[cli_labels.index(cli_sel_idx)] if cli_sel_idx in cli_labels else ""
    else:
        st.warning("Nenhum cliente cadastrado.")
        sel_cid = st.text_input("Cliente ID *", value=_d("Cliente_Id"),
                                key="_svrel_f_cliente_id")

    # ── Ativo (opcional) ──────────────────────────────────────────────────────
    ativo_options = ["— Nenhum —"]
    ativo_ids     = [""]
    if sel_cid:
        try:
            df_at = get_ativos(sel_cid)
            if not df_at.empty and "Id" in df_at.columns:
                for _, ar in df_at.iterrows():
                    tag = str(ar.get("Tag", "") or ar.get("Nome", "")).strip()
                    aid = str(ar.get("Id", "")).strip()
                    if tag and aid:
                        ativo_options.append(f"{tag} ({aid})")
                        ativo_ids.append(aid)
        except Exception:
            pass

    cur_aid = _d("Ativo_Id")
    try:
        aid_idx = ativo_ids.index(cur_aid) if cur_aid in ativo_ids else 0
    except ValueError:
        aid_idx = 0
    ativo_sel = st.selectbox(
        "Ativo vinculado (opcional)", ativo_options, index=aid_idx, key="_svrel_f_ativo",
    )
    sel_aid = ativo_ids[ativo_options.index(ativo_sel)] if ativo_sel in ativo_options else ""

    st.markdown("---")

    # ── Campos do relatório ───────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        titulo = st.text_input("Título do Relatório *", value=_d("Titulo"),
                               key="_svrel_f_titulo")
    with c2:
        tipo_idx = _TIPOS_SERVICO.index(_d("Tipo_Servico")) if _d("Tipo_Servico") in _TIPOS_SERVICO else 0
        tipo_sel = st.selectbox("Tipo de Serviço *", _TIPOS_SERVICO, index=tipo_idx,
                                key="_svrel_f_tipo_serv")

    # ── Origem do relatório ───────────────────────────────────────────────────
    st.markdown(
        f"<p style='font-size:0.75rem;color:{COLOR_MUTED};margin:0.75rem 0 0.25rem;"
        f"font-weight:700;text-transform:uppercase;letter-spacing:.08em;'>Origem *</p>",
        unsafe_allow_html=True,
    )
    origem_labels = {v: l for v, l in _ORIGEM_OPTS}
    origem_keys   = [v for v, _ in _ORIGEM_OPTS]
    origem_sel = st.radio(
        "Origem *", origem_keys, index=origem_keys.index(_origem_default(report)),
        format_func=lambda v: origem_labels[v], key="_svrel_f_origem",
        horizontal=True, label_visibility="collapsed",
    )

    if origem_sel == ORIGEM_APP_RELATORIOS:
        st.info(
            "🔌 A integração automática com o App Relatórios Pred.IO está "
            "planejada (Etapa 1 do projeto de integração), mas ainda não foi "
            "implementada. Escolha **Upload direto** ou **Google Drive / URL** "
            "por enquanto."
        )
        return

    arquivo_bytes: bytes | None = None
    arquivo_nome_upload = ""
    arquivo_url = ""
    if origem_sel in (ORIGEM_UPLOAD_DIRETO, ORIGEM_UPLOAD_MANUAL_VIBRACAO):
        cur_storage_path = _d("Storage_Path")
        cur_arquivo_nome = _d("Arquivo_Nome")
        if cur_storage_path:
            col_atual, col_ver = st.columns([3, 1.4])
            with col_atual:
                st.caption(f"📎 Arquivo atual: {cur_arquivo_nome or 'relatorio.pdf'}")
            with col_ver:
                try:
                    from drive_storage import get_report_pdf_url
                    _view_url = get_report_pdf_url(cur_storage_path)
                    st.link_button("👁️ Visualizar PDF atual", _view_url, use_container_width=True)
                except Exception:
                    st.caption("Link indisponível no momento.")
        up = st.file_uploader(
            "Substituir PDF" if cur_storage_path else "Selecionar PDF *",
            type=["pdf"], key="_svrel_f_pdf",
            help="Arquivo enviado do computador. Fica em storage privado — "
                 "só é acessível por quem tem permissão para este cliente.",
        )
        if up is not None:
            arquivo_bytes = up.read()
            arquivo_nome_upload = up.name
    else:
        arquivo_url = st.text_input(
            "Link do PDF (Google Drive / URL) *",
            value=_d("Arquivo_Url"), key="_svrel_f_url",
        )

    c3, c4 = st.columns(2)
    with c3:
        sev_idx = _SEVERIDADES.index(_d("Severidade")) if _d("Severidade") in _SEVERIDADES else 0
        sev_sel = st.selectbox("Severidade *", _SEVERIDADES, index=sev_idx, key="_svrel_f_sev")
    with c4:
        cur_data = _d("Data_Relatorio") or datetime.datetime.now().strftime("%d/%m/%Y")
        try:
            dt_default = datetime.datetime.strptime(cur_data, "%d/%m/%Y").date()
        except Exception:
            dt_default = datetime.date.today()
        data_sel = st.date_input("Data do Relatório *", value=dt_default, key="_svrel_f_data",
                                 format="DD/MM/YYYY")
        data_str = data_sel.strftime("%d/%m/%Y") if data_sel else cur_data

    c5, c6 = st.columns(2)
    with c5:
        planta = st.text_input("Planta", value=_d("Planta"), key="_svrel_f_planta")
    with c6:
        equipamento = st.text_input("Equipamento", value=_d("Equipamento"), key="_svrel_f_equip")

    tecnico = st.text_input(
        "Técnico responsável", value=_d("Tecnico") or current_nome(),
        key="_svrel_f_tecnico",
    )

    resumo = st.text_area(
        "Resumo / Diagnóstico (visível ao cliente) *",
        value=_d("Resumo"), height=120, key="_svrel_f_resumo",
    )
    conclusao = st.text_area(
        "Conclusão (visível ao cliente)",
        value=_d("Conclusao"), height=90, key="_svrel_f_conclusao",
    )
    recomendacoes = st.text_area(
        "Recomendações (visível ao cliente)",
        value=_d("Recomendacoes"), height=120, key="_svrel_f_rec",
    )

    # ── Dados de Vibração (opcional) ──────────────────────────────────────────
    # Pontos de medição — reaproveita a mesma coluna Medicoes_Json já usada
    # pelo App Relatórios (Etapa 4), só que preenchida manualmente aqui. Só
    # aparece pra Tipo de Serviço "Análise de Vibração" e nunca é obrigatório.
    vib_pontos: list[dict] = []
    if tipo_sel == "Análise de Vibração":
        _rep_key_load = report.get("Id", "") if editing else "novo"
        if st.session_state.get("_svrel_vib_loaded_for") != _rep_key_load:
            pontos_iniciais = []
            if editing:
                import json as _json
                raw = (report or {}).get("Medicoes_Json", "")
                if raw:
                    try:
                        parsed = _json.loads(raw)
                        if isinstance(parsed, list):
                            pontos_iniciais = parsed
                    except Exception:
                        pontos_iniciais = []
            for p in pontos_iniciais:
                p.setdefault("_uid", st.session_state.get("_svrel_vib_next_id", 0))
                st.session_state["_svrel_vib_next_id"] = st.session_state.get("_svrel_vib_next_id", 0) + 1
            st.session_state["_svrel_vib_pontos"]     = pontos_iniciais
            st.session_state["_svrel_vib_loaded_for"] = _rep_key_load

        vib_pontos = st.session_state.get("_svrel_vib_pontos", [])
        _sev_pontos_opts = ["", "Normal", "Atenção", "Crítico", "Urgente"]

        with st.expander("📈 Dados de Vibração (opcional)", expanded=bool(vib_pontos)):
            st.caption(
                "Pontos de medição do relatório — todos os campos são opcionais. "
                "Adicione quantos pontos precisar."
            )
            _remover_idx = None
            for i, p in enumerate(vib_pontos):
                uid = p["_uid"]
                st.markdown(f"**Ponto {i + 1}**")
                pc1, pc2, pc3 = st.columns(3)
                with pc1:
                    p["ponto"]   = st.text_input("Ponto de medição", value=p.get("ponto", ""), key=f"_vib_ponto_{uid}")
                    p["direcao"] = st.text_input("Direção", value=p.get("direcao", ""), key=f"_vib_direcao_{uid}")
                with pc2:
                    p["posicao"]      = st.text_input("Posição", value=p.get("posicao", ""), key=f"_vib_posicao_{uid}")
                    p["valor_global"] = st.text_input("Valor global", value=p.get("valor_global", ""), key=f"_vib_valor_{uid}")
                with pc3:
                    p["unidade"] = st.text_input("Unidade", value=p.get("unidade", "mm/s"), key=f"_vib_unidade_{uid}")
                    p["frequencia_dominante"] = st.text_input(
                        "Frequência dominante", value=p.get("frequencia_dominante", ""), key=f"_vib_freq_{uid}",
                    )
                pc4, pc5 = st.columns([2, 1])
                with pc4:
                    _sev_idx = _sev_pontos_opts.index(p.get("severidade", "")) if p.get("severidade", "") in _sev_pontos_opts else 0
                    p["severidade"] = st.selectbox(
                        "Severidade do ponto", _sev_pontos_opts, index=_sev_idx, key=f"_vib_sev_{uid}",
                    )
                with pc5:
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ Remover", key=f"_vib_del_{uid}", use_container_width=True):
                        _remover_idx = i
                p["diagnostico"] = st.text_area(
                    "Diagnóstico do ponto", value=p.get("diagnostico", ""), key=f"_vib_diag_{uid}", height=60,
                )
                p["recomendacao"] = st.text_area(
                    "Recomendação do ponto", value=p.get("recomendacao", ""), key=f"_vib_rec_{uid}", height=60,
                )
                st.markdown("<hr style='margin:4px 0'/>", unsafe_allow_html=True)

            if _remover_idx is not None:
                vib_pontos.pop(_remover_idx)
                st.rerun()

            if st.button("➕ Adicionar ponto de medição", key="_vib_add_ponto"):
                novo_uid = st.session_state.get("_svrel_vib_next_id", 0)
                st.session_state["_svrel_vib_next_id"] = novo_uid + 1
                vib_pontos.append({"_uid": novo_uid})
                st.rerun()

    with st.expander("🔒 Observações internas (não visível ao cliente)"):
        obs_interna = st.text_area(
            "Obs. Interna", value=_d("Obs_Interna"), height=90,
            key="_svrel_f_obs",
        )

    if editing:
        with st.expander("🎯 Prioridade GUT da recomendação", expanded=False):
            st.caption(f"ℹ️ {GUT_DISCLAIMER}")
            g_atual = int((report or {}).get("Gut_Gravidade") or 3)
            u_atual = int((report or {}).get("Gut_Urgencia") or 3)
            t_atual = int((report or {}).get("Gut_Tendencia") or 3)
            gc1, gc2, gc3 = st.columns(3)
            with gc1:
                g_novo = st.number_input("Gravidade", 1, 5, g_atual, key="_gut_g_rel")
            with gc2:
                u_novo = st.number_input("Urgência", 1, 5, u_atual, key="_gut_u_rel")
            with gc3:
                t_novo = st.number_input("Tendência", 1, 5, t_atual, key="_gut_t_rel")
            obs_gut = st.text_area(
                "Observação técnica GUT",
                value=str((report or {}).get("Gut_Observacao", "")).strip(),
                key="_gut_obs_rel", height=68,
            )
            preview = calculate_gut(g_novo, u_novo, t_novo)
            if preview:
                st.markdown(
                    status_badge(preview["prioridade"], "gut")
                    + f" <span style='font-size:0.8rem;color:{COLOR_MUTED};'>Score {preview['score']}</span>",
                    unsafe_allow_html=True,
                )
            if st.button("💾 Salvar GUT da recomendação", key="_gut_save_rel"):
                rep_id = st.session_state.get(_KEY_REP_ID, "")
                if update_report_gut(rep_id, g_novo, u_novo, t_novo, obs_gut):
                    st.success("GUT da recomendação atualizado.")
                    st.rerun()
                else:
                    st.error("Não foi possível salvar o GUT deste relatório.")

    # ── Preview de impacto no score ───────────────────────────────────────────
    delta_map = {
        "Urgente": -25, "Crítico": -15, "Atenção": -7, "Normal": 2,
    }
    delta_prev = delta_map.get(sev_sel, 0)
    color_prev = "#10B981" if delta_prev >= 0 else "#EF4444"
    st.markdown(
        f"<div style='background:#F8FAFC;border:1px solid {COLOR_BORDER};"
        f"border-radius:8px;padding:0.65rem 1rem;margin-top:0.5rem;'>"
        f"<p style='font-size:0.75rem;color:{COLOR_MUTED};margin:0;'>"
        f"Impacto estimado no score do ativo: "
        f"<b style='color:{color_prev};'>{delta_prev:+d} pontos</b>"
        f"&nbsp; (calculado no momento da publicação)</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    # ── Ações ─────────────────────────────────────────────────────────────────
    col_save, col_pub, col_del, _ = st.columns([1.2, 1.2, 1, 2])

    def _dados() -> dict:
        dados = {
            "cliente_id":    sel_cid,
            "ativo_id":      sel_aid,
            "titulo":        titulo.strip(),
            "tipo_servico":  tipo_sel,
            "severidade":    sev_sel,
            "data_relatorio": data_str,
            "planta":        planta.strip(),
            "equipamento":   equipamento.strip(),
            "resumo":        resumo.strip(),
            "recomendacoes": recomendacoes.strip(),
            "conclusao":     conclusao.strip(),
            "arquivo_url":   arquivo_url.strip(),
            "obs_interna":   obs_interna.strip(),
            "origem":        origem_sel,
            "tecnico":       tecnico.strip(),
        }
        # Medições de vibração só são tocadas quando o tipo é "Análise de
        # Vibração" — pra não sobrescrever Medicoes_Json de outro tipo (ex.
        # relatório vindo do App Relatórios) ao editar campos não relacionados.
        if tipo_sel == "Análise de Vibração":
            # "unidade" tem valor default (mm/s) mesmo num ponto em branco —
            # só conta como preenchido se algum campo além dela tiver conteúdo,
            # senão um ponto adicionado e deixado vazio vira lixo no JSON.
            _campos_relevantes = (
                "ponto", "posicao", "direcao", "valor_global",
                "frequencia_dominante", "severidade", "diagnostico", "recomendacao",
            )
            pontos_limpos = []
            for p in vib_pontos:
                if not any(str(p.get(c, "")).strip() for c in _campos_relevantes):
                    continue
                pontos_limpos.append({k: v for k, v in p.items() if k != "_uid" and str(v).strip()})
            import json as _json
            dados["medicoes_json"] = _json.dumps(pontos_limpos, ensure_ascii=False) if pontos_limpos else ""
        return dados

    # add_technical_report() espera chaves em snake_case (dados["cliente_id"]...),
    # mas update_technical_report() só grava campos cujo nome bate exatamente
    # com o cabeçalho da planilha (Title_Case — "Cliente_Id", "Titulo"...).
    # BUG CORRIGIDO: os dois botões abaixo passavam _dados() (snake_case)
    # direto para update_technical_report(), então nenhuma edição de título/
    # resumo/severidade/etc. em relatório já existente era realmente salva —
    # só "Updated_At" batia por coincidência. Este mapeamento traduz para o
    # nome real da coluna antes de chamar update_technical_report().
    _DADOS_TO_SHEET_COL = {
        "cliente_id": "Cliente_Id", "ativo_id": "Ativo_Id", "titulo": "Titulo",
        "tipo_servico": "Tipo_Servico", "severidade": "Severidade",
        "data_relatorio": "Data_Relatorio", "planta": "Planta",
        "equipamento": "Equipamento", "resumo": "Resumo",
        "recomendacoes": "Recomendacoes", "conclusao": "Conclusao",
        "arquivo_url": "Arquivo_Url", "obs_interna": "Obs_Interna",
        "origem": "Origem", "tecnico": "Tecnico",
        "medicoes_json": "Medicoes_Json",
    }

    def _dados_sheet() -> dict:
        return {_DADOS_TO_SHEET_COL[k]: v for k, v in _dados().items()}

    _ORIGENS_COM_UPLOAD = (ORIGEM_UPLOAD_DIRETO, ORIGEM_UPLOAD_MANUAL_VIBRACAO)

    def _validar_upload_direto() -> str | None:
        """Regra dos fluxos de upload de PDF (upload direto e vibração
        manual): ativo é obrigatório e precisa haver um PDF (o já salvo, ou
        um novo selecionado agora)."""
        if origem_sel not in _ORIGENS_COM_UPLOAD:
            return None
        if not sel_aid:
            return "Selecione o ativo vinculado — obrigatório para enviar o PDF."
        if not _d("Storage_Path") and arquivo_bytes is None:
            return "Selecione o arquivo PDF do relatório."
        return None

    def _persistir_upload(rep_id: str) -> str | None:
        """Se um novo PDF foi selecionado nesta submissão, envia ao storage
        privado (clientes/{cliente}/relatorios/[vibracao/]{ativo}/{report}/
        relatorio.pdf) e grava Storage_Path/Arquivo_Nome no relatório.
        Retorna mensagem de erro em caso de falha, ou None em sucesso/
        sem-arquivo-novo."""
        if origem_sel not in _ORIGENS_COM_UPLOAD or arquivo_bytes is None:
            return None
        try:
            from drive_storage import upload_report_pdf
            subpasta = "vibracao" if origem_sel == ORIGEM_UPLOAD_MANUAL_VIBRACAO else ""
            storage_path = upload_report_pdf(
                arquivo_bytes, sel_cid, sel_aid, rep_id, arquivo_nome_upload,
                subpasta=subpasta,
            )
        except Exception as exc:
            return f"Falha ao enviar o PDF: {exc}"
        update_technical_report(rep_id, {
            "Storage_Path": storage_path,
            "Arquivo_Nome": arquivo_nome_upload,
            "Arquivo_Url":  "",
            "Origem":       origem_sel,
        })
        return None

    _btn_salvar_label = (
        "📤 Enviar relatório"
        if (not editing and origem_sel in _ORIGENS_COM_UPLOAD)
        else "💾 Salvar Rascunho"
    )

    with col_save:
        if st.button(_btn_salvar_label, use_container_width=True):
            _erro_upload = _validar_upload_direto()
            if not sel_cid:
                st.error("Selecione um cliente.")
            elif not titulo.strip():
                st.error("Informe o título do relatório.")
            elif not resumo.strip():
                st.error("O resumo é obrigatório.")
            elif _erro_upload:
                st.error(_erro_upload)
            else:
                dados = _dados()
                if editing:
                    rep_id = st.session_state.get(_KEY_REP_ID, "")
                    ok = update_technical_report(rep_id, _dados_sheet())
                    if not ok:
                        st.error(
                            "Erro ao salvar. Verifique se o ativo selecionado "
                            "pertence ao cliente."
                        )
                    else:
                        _erro_pdf = _persistir_upload(rep_id)
                        # Relatório já publicado sendo editado — conteúdo mudou,
                        # reindexa pro Assistente Técnico não ficar com chunk
                        # desatualizado (Etapa 5). Rascunho/Em revisão não
                        # passam no guard de reindex_technical_report().
                        if (report or {}).get("Status", "").strip() == "Publicado":
                            from sheets import reindex_technical_report
                            reindex_technical_report(rep_id)
                        from sheets import load_sheet as _ls
                        _ls.clear()
                        if _erro_pdf:
                            st.warning(f"Rascunho salvo, mas {_erro_pdf.lower()}")
                        else:
                            st.success("Rascunho atualizado com sucesso!")
                        st.rerun()
                else:
                    _status_inicial = st.session_state.get(_KEY_PREFILL_STATUS, "")
                    if _status_inicial:
                        dados["status"] = _status_inicial
                    new_id = add_technical_report(dados, current_nome())
                    if not new_id:
                        st.error(
                            "Erro ao criar relatório. Verifique se o ativo "
                            "selecionado pertence ao cliente."
                        )
                    else:
                        _erro_pdf = _persistir_upload(new_id)
                        st.session_state[_KEY_REP_ID] = new_id
                        st.session_state["sv_view"]   = "relatorio_editar"
                        from sheets import load_sheet as _ls
                        _ls.clear()
                        if _erro_pdf:
                            st.warning(f"Relatório criado (ID: {new_id}), mas {_erro_pdf.lower()}")
                        else:
                            st.success(f"Relatório criado! ID: {new_id}")
                        st.rerun()

    with col_pub:
        can_pub = editing and (report or {}).get("Status", "Rascunho") in _STATUS_PUBLICAVEIS
        if can_pub:
            if st.button("📢 Publicar", use_container_width=True, type="primary"):
                _erro_upload = _validar_upload_direto()
                if not sel_cid:
                    st.error("Selecione um cliente.")
                elif not titulo.strip():
                    st.error("Informe o título.")
                elif not resumo.strip():
                    st.error("O resumo é obrigatório.")
                elif _erro_upload:
                    st.error(_erro_upload)
                else:
                    _pub_rep_id = st.session_state.get(_KEY_REP_ID, "")
                    # Salva campos e eventual novo PDF antes de publicar
                    update_technical_report(_pub_rep_id, _dados_sheet())
                    _erro_pdf = _persistir_upload(_pub_rep_id)
                    if _erro_pdf:
                        st.error(f"Não foi possível publicar: {_erro_pdf}")
                        result = None
                    else:
                        with st.spinner("Publicando..."):
                            result = publish_technical_report(_pub_rep_id, current_nome())
                    if result and result.get("ok"):
                        msg = "✅ Relatório publicado!"
                        if result.get("score_atualizado"):
                            msg += f" Score do ativo: {result['score_delta']:+d} pts."
                        if result.get("alerta"):
                            msg += " Alerta interno gerado."
                        # indexação para o Assistente Técnico já roda dentro de
                        # publish_technical_report() (Etapa 5) — nada a fazer aqui.
                        st.success(msg)
                        from sheets import load_sheet as _ls
                        _ls.clear()
                        st.session_state["sv_view"] = "relatorios_sv"
                        st.rerun()
                    elif result:
                        st.error(result.get("erro", "Erro ao publicar."))

    with col_del:
        if editing:
            if st.button("🗑️ Excluir", use_container_width=True):
                st.session_state["_svrel_confirm_del"] = True
                st.rerun()

    # .get(), não .pop() — ver comentário extenso em _render_card() sobre por
    # que .pop() aqui faz o clique em "Confirmar exclusão" ser ignorado (a
    # chave já teria sido removida no rerun anterior, antes deste botão
    # sequer ser instanciado de novo).
    if st.session_state.get("_svrel_confirm_del", False):
        rep_status = (report or {}).get("Status", "Rascunho")
        if rep_status == "Publicado":
            st.error(
                "**Apagar este relatório PUBLICADO?** O cliente pode já ter visto. "
                "Isso remove o relatório, os chunks indexados no Assistente Técnico "
                "e o evento no histórico do ativo, e reverte o impacto no Score. "
                "**Esta ação não pode ser desfeita.**"
            )
        else:
            st.warning("Excluir este relatório permanentemente? Esta ação não pode ser desfeita.")
        col_ok, col_no, _ = st.columns([1, 1, 4])
        with col_ok:
            if st.button("✅ Confirmar exclusão", key="_svrel_delOK", type="primary",
                         use_container_width=True):
                result = delete_technical_report_full(st.session_state.get(_KEY_REP_ID, ""))
                st.session_state.pop("_svrel_confirm_del", None)
                from sheets import load_sheet as _ls
                _ls.clear()
                if result.get("ok"):
                    st.session_state["sv_view"] = "relatorios_sv"
                    st.session_state.pop(_KEY_REP_ID, None)
                    st.rerun()
                else:
                    st.error(result.get("erro", "Erro ao excluir."))
        with col_no:
            if st.button("❌ Cancelar", key="_svrel_delNO", use_container_width=True):
                st.session_state.pop("_svrel_confirm_del", None)
                st.rerun()
