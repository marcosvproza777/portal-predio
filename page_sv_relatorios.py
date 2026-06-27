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
    delete_technical_report,
)
from ui import (
    sv_page_header,
    COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE,
)

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
    "rascunho":  ("#94A3B8", "#F8FAFC", "#CBD5E1"),
    "publicado": ("#10B981", "#F0FDF4", "#86EFAC"),
    "arquivado": ("#64748B", "#F1F5F9", "#CBD5E1"),
}
_STATUS_DEFAULT = ("#94A3B8", "#F8FAFC", "#CBD5E1")

_KEY_REP_ID = "_svrel_rep_id"


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

    col_btn, _ = st.columns([1.4, 4])
    with col_btn:
        if st.button("➕ Novo Relatório", use_container_width=True, type="primary"):
            st.session_state["sv_view"] = "relatorio_novo"
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            status_opts = ["Todos", "Rascunho", "Publicado", "Arquivado"]
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
        if status == "Rascunho":
            if st.button("📢 Publicar", key=f"_svrel_pub_{rep_id}", use_container_width=True,
                         type="primary"):
                st.session_state[f"_svrel_confirm_pub_{rep_id}"] = True
                st.rerun()
        if status == "Publicado":
            if st.button("🗂️ Arquivar", key=f"_svrel_arch_{rep_id}", use_container_width=True):
                st.session_state[f"_svrel_confirm_arch_{rep_id}"] = True
                st.rerun()

    # Confirmação publicar
    if st.session_state.pop(f"_svrel_confirm_pub_{rep_id}", False):
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
                if result.get("ok"):
                    msg = "Relatório publicado com sucesso."
                    if result.get("score_atualizado"):
                        msg += f" Score do ativo ajustado em {result['score_delta']:+d} pts."
                    if result.get("alerta"):
                        msg += " Alerta interno gerado."
                    try:
                        from sheets import get_technical_report_by_id, index_relatorio_tecnico
                        _rep = get_technical_report_by_id(rep_id)
                        if _rep:
                            index_relatorio_tecnico(
                                rep_id,
                                _rep.get("Cliente_Id", ""),
                                _rep.get("Ativo_Id",   ""),
                                _rep,
                            )
                    except Exception:
                        pass
                    st.success(msg)
                    from sheets import load_sheet as _ls
                    _ls.clear()
                    st.rerun()
                else:
                    st.error(result.get("erro", "Erro ao publicar."))
        with col_no:
            if st.button("❌ Cancelar", key=f"_svrel_pubNO_{rep_id}", use_container_width=True):
                st.rerun()

    # Confirmação arquivar
    if st.session_state.pop(f"_svrel_confirm_arch_{rep_id}", False):
        col_ok2, col_no2, _ = st.columns([1, 1, 3])
        st.warning(f"Arquivar '{titulo}'? O cliente não poderá mais acessá-lo.")
        with col_ok2:
            if st.button("✅ Arquivar", key=f"_svrel_archOK_{rep_id}", type="primary",
                         use_container_width=True):
                archive_technical_report(rep_id)
                from sheets import load_sheet as _ls
                _ls.clear()
                st.rerun()
        with col_no2:
            if st.button("❌ Cancelar", key=f"_svrel_archNO_{rep_id}", use_container_width=True):
                st.rerun()

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULÁRIO CRIAR / EDITAR
# ═══════════════════════════════════════════════════════════════════════════════

def _render_form(report: dict | None) -> None:
    editing = report is not None
    label   = "✏️ Editar Relatório" if editing else "➕ Novo Relatório Técnico"
    sv_page_header(label, back_label="Voltar à lista", back_view="relatorios_sv")

    # Defaults
    def _d(k: str, default="") -> str:
        return (report.get(k, "") or "") if editing else default

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

    resumo = st.text_area(
        "Resumo (visível ao cliente) *",
        value=_d("Resumo"), height=120, key="_svrel_f_resumo",
    )
    recomendacoes = st.text_area(
        "Recomendações (visível ao cliente)",
        value=_d("Recomendacoes"), height=120, key="_svrel_f_rec",
    )
    arquivo_url = st.text_input(
        "Link do PDF (Google Drive / URL pública)",
        value=_d("Arquivo_Url"), key="_svrel_f_url",
    )

    with st.expander("🔒 Observações internas (não visível ao cliente)"):
        obs_interna = st.text_area(
            "Obs. Interna", value=_d("Obs_Interna"), height=90,
            key="_svrel_f_obs",
        )

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
        return {
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
            "arquivo_url":   arquivo_url.strip(),
            "obs_interna":   obs_interna.strip(),
        }

    with col_save:
        if st.button("💾 Salvar Rascunho", use_container_width=True):
            if not sel_cid:
                st.error("Selecione um cliente.")
            elif not titulo.strip():
                st.error("Informe o título do relatório.")
            elif not resumo.strip():
                st.error("O resumo é obrigatório.")
            else:
                dados = _dados()
                if editing:
                    ok = update_technical_report(
                        st.session_state.get(_KEY_REP_ID, ""), dados
                    )
                    if ok:
                        st.success("Rascunho atualizado com sucesso!")
                        from sheets import load_sheet as _ls
                        _ls.clear()
                    else:
                        st.error("Erro ao salvar. Tente novamente.")
                else:
                    new_id = add_technical_report(dados, current_nome())
                    if new_id:
                        st.success(f"Relatório criado! ID: {new_id}")
                        st.session_state[_KEY_REP_ID] = new_id
                        st.session_state["sv_view"]   = "relatorio_editar"
                        from sheets import load_sheet as _ls
                        _ls.clear()
                        st.rerun()
                    else:
                        st.error("Erro ao criar relatório.")

    with col_pub:
        can_pub = editing and (report or {}).get("Status", "Rascunho") in ("Rascunho", "")
        if can_pub:
            if st.button("📢 Publicar", use_container_width=True, type="primary"):
                if not sel_cid:
                    st.error("Selecione um cliente.")
                elif not titulo.strip():
                    st.error("Informe o título.")
                elif not resumo.strip():
                    st.error("O resumo é obrigatório.")
                else:
                    # Salva campos antes de publicar
                    update_technical_report(
                        st.session_state.get(_KEY_REP_ID, ""), _dados()
                    )
                    _pub_rep_id = st.session_state.get(_KEY_REP_ID, "")
                    with st.spinner("Publicando..."):
                        result = publish_technical_report(_pub_rep_id, current_nome())
                    if result.get("ok"):
                        msg = "✅ Relatório publicado!"
                        if result.get("score_atualizado"):
                            msg += f" Score do ativo: {result['score_delta']:+d} pts."
                        if result.get("alerta"):
                            msg += " Alerta interno gerado."
                        try:
                            from sheets import get_technical_report_by_id, index_relatorio_tecnico
                            _rep = get_technical_report_by_id(_pub_rep_id)
                            if _rep:
                                index_relatorio_tecnico(
                                    _pub_rep_id,
                                    _rep.get("Cliente_Id", ""),
                                    _rep.get("Ativo_Id",   ""),
                                    _rep,
                                )
                        except Exception:
                            pass
                        st.success(msg)
                        from sheets import load_sheet as _ls
                        _ls.clear()
                        st.session_state["sv_view"] = "relatorios_sv"
                        st.rerun()
                    else:
                        st.error(result.get("erro", "Erro ao publicar."))

    with col_del:
        if editing:
            rep_status = (report or {}).get("Status", "Rascunho")
            if rep_status == "Rascunho":
                if st.button("🗑️ Excluir", use_container_width=True):
                    st.session_state["_svrel_confirm_del"] = True
                    st.rerun()

    if st.session_state.pop("_svrel_confirm_del", False):
        st.warning("Excluir este rascunho permanentemente?")
        col_ok, col_no, _ = st.columns([1, 1, 4])
        with col_ok:
            if st.button("✅ Confirmar exclusão", key="_svrel_delOK", type="primary",
                         use_container_width=True):
                delete_technical_report(st.session_state.get(_KEY_REP_ID, ""))
                st.session_state["sv_view"] = "relatorios_sv"
                st.session_state.pop(_KEY_REP_ID, None)
                from sheets import load_sheet as _ls
                _ls.clear()
                st.rerun()
        with col_no:
            if st.button("❌ Cancelar", key="_svrel_delNO", use_container_width=True):
                st.rerun()
