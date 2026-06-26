"""Supervisão Pred.IO — Dashboard Executivo."""
import datetime
import pandas as pd
import streamlit as st
from auth import require_staff
from sheets import get_all_chamados
from ui import (sv_metric_card, sv_page_header,
                COLOR_NAVY, COLOR_BORDER, COLOR_CARD, COLOR_MUTED,
                STATUS_CFG, PRIORIDADE_CFG)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count(df: pd.DataFrame, col: str, valor: str) -> int:
    if df.empty or col not in df.columns:
        return 0
    return len(df[df[col].str.strip().str.lower() == valor.strip().lower()])


def _col(df: pd.DataFrame, *names: str):
    """Retorna o primeiro nome de coluna que existe no DataFrame."""
    for n in names:
        if n in df.columns:
            return n
    return None


# ── Carregamento de dados de supervisão ──────────────────────────────────────

def _load_sv_data() -> dict:
    hoje_mes = datetime.datetime.now().strftime("%Y-%m")

    d = {
        # Clientes e ativos
        "clientes_ativos":       0,
        "total_clientes":        0,
        "ativos_total":          0,
        "ativos_criticos":       0,  # count por cliente vem separado
        "ativos_criticos_lista": [],

        # Chamados
        "cham_abertos":       0,
        "cham_criticos":      0,
        "cham_em_andamento":  0,
        "cham_aguardando":    0,
        "cham_concluidos_mes": 0,
        "cham_list":          [],

        # Relatórios
        "rel_publicados_mes": 0,
        "rel_rascunhos":      0,

        # Manutenção
        "manut_vencidas_total": 0,

        # Alertas
        "alertas_criticos": 0,

        # Documentos
        "docs_nao_indexados": 0,

        # Assistente
        "assistente_recentes":   [],
        "assistente_marcados":   [],
    }

    # ── Clientes ──────────────────────────────────────────────────────────────
    try:
        from sheets import get_all_clientes
        df_cl = get_all_clientes()
        if not df_cl.empty:
            d["total_clientes"] = len(df_cl)
    except Exception:
        pass

    # ── Ativos (global) ───────────────────────────────────────────────────────
    try:
        from sheets import get_all_ativos_sv
        df_at = get_all_ativos_sv()
        if not df_at.empty:
            d["ativos_total"] = len(df_at)

            # Status crítico/urgente
            st_col = _col(df_at, "Status")
            if st_col:
                critico_mask = df_at[st_col].str.strip().str.lower().isin(
                    ["critico", "crítico", "urgente"]
                )
                d["ativos_criticos"] = int(critico_mask.sum())

                # Ativos críticos por cliente
                id_col = _col(df_at, "Cliente_Id", "client_id", "Empresa")
                if id_col:
                    df_crit = df_at[critico_mask][[id_col, st_col]].copy()
                    if not df_crit.empty:
                        grupo = (
                            df_crit.groupby(id_col).size()
                            .reset_index(name="n")
                            .sort_values("n", ascending=False)
                            .head(8)
                        )
                        d["ativos_criticos_lista"] = grupo.to_dict("records")
    except Exception:
        pass

    # ── Chamados ──────────────────────────────────────────────────────────────
    try:
        df_ch = get_all_chamados()
        if not df_ch.empty:
            st_col = _col(df_ch, "Status")
            pr_col = _col(df_ch, "Prioridade")

            def _st(s):
                return s.strip().lower() if isinstance(s, str) else ""

            def _pr(s):
                return s.strip().lower() if isinstance(s, str) else ""

            for _, row in df_ch.iterrows():
                s = _st(row.get(st_col, "")) if st_col else ""
                p = _pr(row.get(pr_col, "")) if pr_col else ""

                if s in ("aberto", "em analise", "em análise", "em andamento"):
                    d["cham_abertos"] += 1
                elif "aguardando" in s:
                    d["cham_aguardando"] += 1
                    d["cham_abertos"] += 1

                if p in ("critica", "crítica", "crítico", "critico", "urgente"):
                    d["cham_criticos"] += 1

                if s == "em andamento":
                    d["cham_em_andamento"] += 1

                dt_col = _col(df_ch, "Data_Abertura")
                if dt_col:
                    dt = str(row.get(dt_col, ""))[:7]
                    if dt == hoje_mes and s in ("concluido", "concluído"):
                        d["cham_concluidos_mes"] += 1

            # Lista recentes (não concluídos) — top 8
            mask_open = df_ch[st_col].str.strip().str.lower().isin(
                ["aberto", "em andamento", "em analise", "em análise", "aguardando cliente"]
            ) if st_col else pd.Series([True] * len(df_ch))

            # Clientes com chamados abertos ativos
            em_col = _col(df_ch, "Empresa", "Cliente_Id")
            if em_col:
                d["clientes_ativos"] = int(
                    df_ch[mask_open][em_col].nunique()
                )

            d["cham_list"] = df_ch[mask_open].head(8).to_dict("records")

    except Exception:
        pass

    # ── Relatórios ────────────────────────────────────────────────────────────
    try:
        from sheets import get_technical_reports
        df_rel = get_technical_reports(client_id="", staff=True)
        if not df_rel.empty:
            s_col = _col(df_rel, "Status")
            d_col = _col(df_rel, "Data_Relatorio", "Criado_Em")

            if s_col:
                pub_mask = df_rel[s_col].str.strip().str.lower() == "publicado"
                ras_mask = df_rel[s_col].str.strip().str.lower().isin(
                    ["rascunho", "draft", "pendente"]
                )
                d["rel_rascunhos"] = int(ras_mask.sum())

                if d_col:
                    pub_df = df_rel[pub_mask & (
                        df_rel[d_col].astype(str).str[:7] == hoje_mes
                    )]
                    d["rel_publicados_mes"] = len(pub_df)
                else:
                    d["rel_publicados_mes"] = int(pub_mask.sum())
    except Exception:
        pass

    # ── Manutenção vencida (global) ───────────────────────────────────────────
    try:
        from sheets import get_maintenance_tasks, calc_task_status
        df_mt = get_maintenance_tasks(client_id="", staff=True)
        if not df_mt.empty:
            count_v = 0
            for _, row in df_mt.iterrows():
                task  = row.to_dict()
                tipo  = str(task.get("Tipo_Manutencao", "")).strip().lower()
                if tipo in ("condicao", "condição"):
                    continue
                s = calc_task_status(task, 0)
                if "vencida" in s.lower() or "atraso" in s.lower():
                    count_v += 1
            d["manut_vencidas_total"] = count_v
    except Exception:
        pass

    # ── Alertas críticos ──────────────────────────────────────────────────────
    try:
        from sheets import get_alertas_sv
        df_al = get_alertas_sv("")  # all clients (staff)
        if df_al is not None and not df_al.empty:
            p_col = _col(df_al, "Prioridade")
            if p_col:
                d["alertas_criticos"] = int(
                    df_al[p_col].str.strip().str.lower().isin(
                        ["urgente", "crítica", "critica", "alta"]
                    ).sum()
                )
    except Exception:
        pass

    # ── Documentos não indexados ──────────────────────────────────────────────
    try:
        from sheets import get_documentos_tecnicos
        df_doc = get_documentos_tecnicos(client_id=None, staff=True)
        if df_doc is not None and not df_doc.empty:
            idx_col = _col(df_doc, "Indexado", "Status")
            if idx_col:
                d["docs_nao_indexados"] = int(
                    df_doc[idx_col].str.strip().str.lower().isin(
                        ["nao", "não", "pendente", "0", "false", ""]
                    ).sum()
                )
    except Exception:
        pass

    # ── Assistente técnico ────────────────────────────────────────────────────
    try:
        from sheets import get_assistant_logs
        df_log = get_assistant_logs(limit=50)
        if df_log is not None and not df_log.empty:
            # Perguntas recentes (top 6)
            q_col = _col(df_log, "Pergunta", "Question", "User_Message")
            cl_col = _col(df_log, "Cliente_Id", "client_id", "Empresa")
            dt_col_a = _col(df_log, "Timestamp", "Criado_Em", "Data")

            if q_col:
                recentes = []
                for _, row in df_log.head(6).iterrows():
                    recentes.append({
                        "pergunta": str(row.get(q_col, "")).strip()[:150],
                        "cliente":  str(row.get(cl_col, "")).strip() if cl_col else "",
                        "data":     str(row.get(dt_col_a, "")).strip()[:16] if dt_col_a else "",
                    })
                d["assistente_recentes"] = recentes

            # Respostas marcadas como incorretas ou "precisa melhorar"
            fb_col = _col(df_log, "Feedback", "Avaliacao", "Rating")
            if fb_col:
                marcados = df_log[
                    df_log[fb_col].astype(str).str.strip().str.lower().isin(
                        ["incorreto", "errado", "precisa melhorar",
                         "negativo", "ruim", "nao", "não", "thumbs_down",
                         "bad", "false", "0"]
                    )
                ]
                d["assistente_marcados"] = []
                for _, row in marcados.head(5).iterrows():
                    d["assistente_marcados"].append({
                        "pergunta":  str(row.get(q_col, "")).strip()[:150] if q_col else "",
                        "feedback":  str(row.get(fb_col, "")).strip(),
                        "cliente":   str(row.get(cl_col, "")).strip() if cl_col else "",
                        "data":      str(row.get(dt_col_a, "")).strip()[:16] if dt_col_a else "",
                    })
    except Exception:
        pass

    return d


# ── Sub-componentes visuais ───────────────────────────────────────────────────

def _render_metrics_grid(d: dict) -> None:
    """12 cards métricas em 3 linhas × 4 colunas."""

    # Linha 1: Escopo global
    st.markdown(
        f"<p style='font-size:0.75rem;text-transform:uppercase;letter-spacing:.07em;"
        f"color:{COLOR_MUTED};font-weight:700;margin:0 0 6px;'>Clientes &amp; Ativos</p>",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sv_metric_card("👥", "Clientes Cadastrados", d["total_clientes"], "#6366F1",
                       f"Com chamados abertos: {d['clientes_ativos']}")
    with c2:
        sv_metric_card("⚙️", "Ativos Monitorados", d["ativos_total"], "#0F1F3D",
                       "Total geral")
    with c3:
        cor = "#EF4444" if d["ativos_criticos"] > 0 else "#10B981"
        sv_metric_card("🔴", "Ativos Críticos", d["ativos_criticos"], cor,
                       "Status crítico ou urgente")
    with c4:
        cor = "#F59E0B" if d["manut_vencidas_total"] > 0 else "#10B981"
        sv_metric_card("📅", "Manutenções Vencidas", d["manut_vencidas_total"], cor,
                       "Calendário vencido")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Linha 2: Chamados e Relatórios
    st.markdown(
        f"<p style='font-size:0.75rem;text-transform:uppercase;letter-spacing:.07em;"
        f"color:{COLOR_MUTED};font-weight:700;margin:0 0 6px;'>Chamados &amp; Relatórios</p>",
        unsafe_allow_html=True,
    )
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        cor = "#3B82F6" if d["cham_abertos"] > 0 else "#10B981"
        sv_metric_card("🔧", "Chamados Abertos", d["cham_abertos"], cor,
                       f"Em andamento: {d['cham_em_andamento']}")
    with c6:
        cor = "#DC2626" if d["cham_criticos"] > 0 else "#10B981"
        sv_metric_card("🚨", "Chamados Críticos", d["cham_criticos"], cor,
                       "Prioridade crítica/urgente")
    with c7:
        sv_metric_card("📄", "Relatórios no Mês", d["rel_publicados_mes"], "#059669",
                       "Publicados este mês")
    with c8:
        cor = "#D97706" if d["rel_rascunhos"] > 0 else "#94A3B8"
        sv_metric_card("📝", "Em Rascunho", d["rel_rascunhos"], cor,
                       "Aguardando publicação")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Linha 3: Alertas, Documentos e Assistente
    st.markdown(
        f"<p style='font-size:0.75rem;text-transform:uppercase;letter-spacing:.07em;"
        f"color:{COLOR_MUTED};font-weight:700;margin:0 0 6px;'>Alertas &amp; Conteúdo</p>",
        unsafe_allow_html=True,
    )
    c9, c10, c11, c12 = st.columns(4)
    with c9:
        cor = "#F97316" if d["alertas_criticos"] > 0 else "#10B981"
        sv_metric_card("🔔", "Alertas Críticos", d["alertas_criticos"], cor,
                       "Prioridade alta/urgente")
    with c10:
        cor = "#64748B" if d["cham_aguardando"] == 0 else "#D97706"
        sv_metric_card("⏳", "Aguardando Cliente", d["cham_aguardando"], cor,
                       "Chamados pendentes resp.")
    with c11:
        cor = "#8B5CF6" if d["docs_nao_indexados"] > 0 else "#10B981"
        sv_metric_card("📚", "Docs não Indexados", d["docs_nao_indexados"], cor,
                       "Biblioteca pendente")
    with c12:
        n_marcados = len(d["assistente_marcados"])
        cor = "#EF4444" if n_marcados > 0 else "#10B981"
        sv_metric_card("🤖", "Respostas Marcadas", n_marcados, cor,
                       "Incorreto/precisa melhorar")


def _render_ativos_criticos_lista(d: dict) -> None:
    lista = d["ativos_criticos_lista"]
    if not lista:
        return

    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;margin:1rem 0 0.5rem;'>"
        f"🔴 Ativos Críticos por Cliente</p>",
        unsafe_allow_html=True,
    )

    itens = ""
    for r in lista:
        cli = r.get("Cliente_Id") or r.get("client_id") or r.get("Empresa") or "—"
        n   = r.get("n", 0)
        cor = "#EF4444" if n >= 3 else "#F97316"
        itens += (
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:5px 0;border-bottom:1px solid {COLOR_BORDER};'>"
            f"<span style='font-size:0.82rem;color:{COLOR_NAVY};font-weight:600;'>{cli}</span>"
            f"<span style='background:{cor};color:#fff;-webkit-text-fill-color:#fff;"
            f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
            f"{n} crítico(s)</span>"
            f"</div>"
        )

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:10px;padding:0.85rem 1rem;'>{itens}</div>",
        unsafe_allow_html=True,
    )


def _render_chamados_recentes(d: dict) -> None:
    lista = d["cham_list"]

    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;margin:1.25rem 0 0.75rem;'>"
        f"🔧 Chamados Abertos</p>",
        unsafe_allow_html=True,
    )

    if not lista:
        st.info("Nenhum chamado em aberto no momento.")
        return

    for idx, row in enumerate(lista):
        chamado_id  = str(row.get("Id",           "")).strip()
        titulo      = str(row.get("Titulo",       "Sem título")).strip()
        empresa     = str(row.get("Empresa",      "")).strip()
        planta      = str(row.get("Planta",       "")).strip()
        equipamento = str(row.get("Equipamento",  "")).strip()
        descricao   = str(row.get("Descricao",    "")).strip()
        prioridade  = str(row.get("Prioridade",   "Baixa")).strip()
        status      = str(row.get("Status",       "Aberto")).strip()
        data_ab     = str(row.get("Data_Abertura","")).strip()[:16]
        responsavel = str(row.get("Responsavel",  "")).strip()

        pr_bg, pr_tc = PRIORIDADE_CFG.get(prioridade.lower(), ("#94A3B8", "#fff"))
        st_bg, st_tc = STATUS_CFG.get(status.lower(), ("#94A3B8", "#fff"))

        meta = []
        if empresa:     meta.append(f"🏢 {empresa}")
        if planta:      meta.append(f"🏭 {planta}")
        if equipamento: meta.append(f"⚙️ {equipamento}")
        if data_ab:     meta.append(f"📅 {data_ab}")
        if responsavel: meta.append(f"👤 {responsavel}")
        meta_str = "   ·   ".join(meta)

        with st.container():
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-left:5px solid {pr_bg};border-radius:12px;"
                f"padding:12px 16px 8px;margin-bottom:4px;'>"
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:flex-start;flex-wrap:wrap;gap:6px;margin-bottom:5px;'>"
                f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;'>{titulo}</span>"
                f"<div style='display:flex;gap:5px;flex-wrap:wrap;'>"
                f"<span style='background:{pr_bg};color:{pr_tc};-webkit-text-fill-color:{pr_tc};"
                f"font-size:0.7rem;font-weight:700;padding:2px 10px;border-radius:12px;'>{prioridade}</span>"
                f"<span style='background:{st_bg};color:{st_tc};-webkit-text-fill-color:{st_tc};"
                f"font-size:0.7rem;font-weight:700;padding:2px 10px;border-radius:12px;'>{status}</span>"
                f"</div></div>"
                f"<p style='color:{COLOR_MUTED};font-size:0.78rem;margin:0 0 5px;'>{meta_str}</p>"
                + (f"<p style='color:#475569;font-size:0.82rem;margin:0;"
                   f"background:#F8FAFC;border-radius:6px;padding:6px 8px;'>"
                   f"{descricao[:200]}{'…' if len(descricao) > 200 else ''}</p>"
                   if descricao else "")
                + "</div>",
                unsafe_allow_html=True,
            )
            _, col_btn = st.columns([4, 1])
            with col_btn:
                if st.button("👁️ Ver", key=f"svdash_ch_{idx}",
                             use_container_width=True, type="primary"):
                    st.session_state["sv_view"]       = "chamado_detalhe"
                    st.session_state["sv_chamado_id"] = chamado_id
                    st.rerun()
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


def _render_assistente_recentes(d: dict) -> None:
    recentes = d["assistente_recentes"]
    marcados = d["assistente_marcados"]

    if not recentes and not marcados:
        return

    col_r, col_m = st.columns(2)

    with col_r:
        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;margin:0 0 0.5rem;'>"
            f"🤖 Perguntas Recentes ao Assistente</p>",
            unsafe_allow_html=True,
        )
        if not recentes:
            st.markdown(
                f"<p style='color:{COLOR_MUTED};font-size:0.82rem;'>Sem registros recentes.</p>",
                unsafe_allow_html=True,
            )
        else:
            itens = ""
            for r in recentes:
                itens += (
                    f"<div style='padding:6px 0;border-bottom:1px solid {COLOR_BORDER};'>"
                    f"<p style='font-size:0.8rem;color:{COLOR_NAVY};margin:0;line-height:1.45;'>"
                    f"{r['pergunta']}</p>"
                    f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:2px 0 0;'>"
                    + (f"🏢 {r['cliente']}  " if r.get("cliente") else "")
                    + (f"📅 {r['data']}" if r.get("data") else "")
                    + f"</p></div>"
                )
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-radius:10px;padding:0.85rem 1rem;'>{itens}</div>",
                unsafe_allow_html=True,
            )

    with col_m:
        st.markdown(
            f"<p style='font-weight:700;color:#DC2626;font-size:0.9rem;margin:0 0 0.5rem;'>"
            f"⚠️ Respostas com Feedback Negativo</p>",
            unsafe_allow_html=True,
        )
        if not marcados:
            st.markdown(
                f"<p style='color:{COLOR_MUTED};font-size:0.82rem;'>"
                f"Nenhuma resposta marcada negativamente.</p>",
                unsafe_allow_html=True,
            )
        else:
            itens = ""
            for m in marcados:
                itens += (
                    f"<div style='padding:6px 0;border-bottom:1px solid #FCA5A5;'>"
                    f"<p style='font-size:0.8rem;color:{COLOR_NAVY};margin:0;line-height:1.45;'>"
                    f"{m['pergunta']}</p>"
                    f"<div style='display:flex;gap:6px;align-items:center;margin-top:3px;'>"
                    f"<span style='background:#FEF2F2;color:#991B1B;-webkit-text-fill-color:#991B1B;"
                    f"font-size:0.62rem;font-weight:700;padding:1px 6px;border-radius:6px;'>"
                    f"{m['feedback']}</span>"
                    + (f"<span style='font-size:0.68rem;color:{COLOR_MUTED};'>"
                       f"🏢 {m['cliente']}</span>" if m.get("cliente") else "")
                    + f"</div></div>"
                )
            st.markdown(
                f"<div style='background:#FEF2F2;border:1px solid #FCA5A5;"
                f"border-radius:10px;padding:0.85rem 1rem;'>{itens}</div>",
                unsafe_allow_html=True,
            )


# ── Render Principal ──────────────────────────────────────────────────────────

def render() -> None:
    require_staff()
    sv_page_header("Dashboard", "Visão executiva Pred.IO — todos os clientes")

    tab_dash, tab_ativo, tab_cliente = st.tabs([
        "📊 Visão Geral",
        "➕ Cadastrar Ativo",
        "🏢 Cadastrar Cliente",
    ])

    with tab_ativo:
        from page_sv_ativos import _form_novo_ativo_content
        _form_novo_ativo_content(inline=True)

    with tab_cliente:
        from page_sv_clientes import _form_novo_cliente_content
        _form_novo_cliente_content(inline=True)

    with tab_dash:
        with st.spinner("Carregando dados..."):
            d = _load_sv_data()

        # ── 12 cartões métricos ───────────────────────────────────────────────
        _render_metrics_grid(d)

        st.markdown(
            f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0;'/>",
            unsafe_allow_html=True,
        )

        # ── Ativos críticos por cliente + Chamados recentes ───────────────────
        col_crit, col_cham = st.columns([2, 3])
        with col_crit:
            _render_ativos_criticos_lista(d)

            # Navegação rápida
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            bnav_cols = st.columns(2)
            with bnav_cols[0]:
                if st.button("⚙️ Ver Ativos", key="svdash_nav_ativos",
                             use_container_width=True):
                    st.session_state["sv_view"] = "ativos"
                    st.rerun()
            with bnav_cols[1]:
                if st.button("📄 Relatórios", key="svdash_nav_rel",
                             use_container_width=True):
                    st.session_state["sv_view"] = "relatorios"
                    st.rerun()

        with col_cham:
            _render_chamados_recentes(d)
            if st.button("🔧 Ver todos os chamados →", key="svdash_nav_cham",
                         use_container_width=True):
                st.session_state["sv_view"] = "chamados"
                st.rerun()

        st.markdown(
            f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0;'/>",
            unsafe_allow_html=True,
        )

        # ── Assistente técnico: recentes + marcados ───────────────────────────
        _render_assistente_recentes(d)

        # Rodapé
        st.markdown(
            f"<div style='margin-top:2rem;padding:0.6rem 1rem;"
            f"background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:8px;'>"
            f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:0;text-align:center;'>"
            f"Dashboard Pred.IO Supervisão · Dados atualizados conforme Google Sheets (TTL 30s). "
            f"Manutenções vencidas excluem tarefas por condição.</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
