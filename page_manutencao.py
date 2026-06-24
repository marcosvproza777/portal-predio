"""Plano de Manutenção — portal do cliente (Pred.IO)."""
import datetime
import streamlit as st
from auth import current_client_id
from page_ativos import (
    _load, _pm_calc_status, _pm_scfg, _norm,
    _render_plano_manutencao, _HORIMETRO_ATUAL_MOCK,
)
from sheets import get_maintenance_tasks, calc_task_status, get_horimetro
from ui import (
    page_header,
    COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE,
)

_STATUS_BADGE = {
    "em dia":                       ("#10B981", "#F0FDF4", "#86EFAC", "#065F46"),
    "próxima do vencimento":        ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E"),
    "proxima do vencimento":        ("#F59E0B", "#FFFBEB", "#FCD34D", "#92400E"),
    "vencida":                      ("#EF4444", "#FEF2F2", "#FCA5A5", "#991B1B"),
    "depende de análise preditiva": ("#38BDF8", "#F0F9FF", "#BAE6FD", "#0C4A6E"),
    "depende de analise preditiva": ("#38BDF8", "#F0F9FF", "#BAE6FD", "#0C4A6E"),
    "concluída":                    ("#64748B", "#F8FAFC", "#CBD5E1", "#475569"),
    "concluida":                    ("#64748B", "#F8FAFC", "#CBD5E1", "#475569"),
}
_STATUS_DEFAULT = ("#94A3B8", "#F8FAFC", "#CBD5E1", "#475569")

_TIPO_ICON = {"Calendário": "📆", "Horímetro": "⏱", "Condição": "🔍",
              "calendario": "📆", "horimetro": "⏱", "condicao": "🔍"}

_NOTE_CONDICAO = (
    "As recomendações por condição (overhaul, troca de rolamento, kit revisão) "
    "não são automáticas por horímetro. A necessidade é determinada pelos laudos "
    "técnicos de vibração, análise de óleo, termografia e avaliação da equipe Pred.IO. "
    "Em caso de dúvidas, abra um chamado técnico."
)


def render() -> None:
    page_header(
        "📅 Plano de Manutenção",
        "Acompanhe as próximas ações preventivas e preditivas dos ativos monitorados.",
    )

    client_id = current_client_id()  # SEMPRE da sessão

    # ── Tenta carregar tarefas reais do Sheets ────────────────────────────────
    using_sheets = False
    df_tasks = None
    try:
        df_tasks = get_maintenance_tasks(client_id=client_id, staff=False)
        if not df_tasks.empty:
            using_sheets = True
    except Exception:
        pass

    if using_sheets and df_tasks is not None:
        _render_sheets_mode(client_id, df_tasks)
    else:
        _render_mock_mode(client_id)


# ═══════════════════════════════════════════════════════════════════════════════
# MODO SHEETS — dados reais
# ═══════════════════════════════════════════════════════════════════════════════

def _render_sheets_mode(client_id: str, df_tasks) -> None:
    # Calcula status de cada tarefa
    tasks_enriched = []
    for _, row in df_tasks.iterrows():
        task  = row.to_dict()
        aid   = str(task.get("Ativo_Id", "")).strip()
        h_at  = 0
        if aid:
            try:
                h = get_horimetro(aid)
                h_at = h if h is not None else 0
            except Exception:
                pass
        status = calc_task_status(task, h_at)
        tasks_enriched.append({
            "task":        task,
            "status":      status,
            "status_key":  _norm(status),
            "ativo_id":    aid,
            "h_atual":     h_at,
            "tipo":        str(task.get("Tipo_Manutencao", "")).strip(),
        })

    # ── Métricas ──────────────────────────────────────────────────────────────
    n_em_dia  = sum(1 for e in tasks_enriched if e["status_key"] == "em dia")
    n_proximas= sum(1 for e in tasks_enriched
                   if e["status_key"] in ("próxima do vencimento", "proxima do vencimento"))
    n_venc    = sum(1 for e in tasks_enriched if e["status_key"] == "vencida")
    n_cond    = sum(1 for e in tasks_enriched
                   if e["status_key"] in ("depende de análise preditiva", "depende de analise preditiva"))

    mc = st.columns(4)
    for col, (label, val, cor) in zip(mc, [
        ("Em dia",        n_em_dia,   "#10B981"),
        ("Próximas",      n_proximas, "#F59E0B"),
        ("Vencidas",      n_venc,     "#EF4444"),
        ("Por condição",  n_cond,     "#38BDF8"),
    ]):
        with col:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-left:4px solid {cor};border-radius:10px;"
                f"padding:0.8rem 1rem;text-align:center;margin-bottom:4px;'>"
                f"<p style='font-size:0.65rem;color:{COLOR_MUTED};margin:0 0 3px;"
                f"text-transform:uppercase;letter-spacing:0.06em;'>{label}</p>"
                f"<p style='font-size:1.8rem;font-weight:900;color:{cor};margin:0;'>{val}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Alertas de urgência ───────────────────────────────────────────────────
    urgentes = [e for e in tasks_enriched if e["status_key"] == "vencida"]
    proximas_list = [e for e in tasks_enriched
                    if e["status_key"] in ("próxima do vencimento", "proxima do vencimento")]

    if urgentes or proximas_list:
        has_venc = bool(urgentes)
        cor_bg   = "#FEF2F2" if has_venc else "#FFFBEB"
        cor_b    = "#FCA5A5" if has_venc else "#FCD34D"
        cor_t    = "#991B1B" if has_venc else "#92400E"
        msgs = []
        for e in (urgentes + proximas_list)[:4]:
            t    = e["task"]
            nome = str(t.get("Nome_Tarefa", "")).strip()
            tipo = e["tipo"]
            if tipo in ("Horímetro", "horimetro"):
                ph  = str(t.get("Proxima_Execucao_Horimetro", "")).strip()
                mat = f"próxima aos {ph}h (atual: {e['h_atual']}h)" if ph else ""
            elif tipo in ("Calendário", "calendario"):
                mat = str(t.get("Proxima_Execucao_Data", "")).strip()
            else:
                mat = ""
            emoji = "🔴" if e["status_key"] == "vencida" else "🟡"
            msgs.append(f"{emoji} <b>{nome}</b>" + (f" — {mat}" if mat else ""))

        items = "".join(f"<li style='margin-bottom:4px;'>{m}</li>" for m in msgs)
        st.markdown(
            f"<div style='background:{cor_bg};border:1px solid {cor_b};"
            f"border-left:4px solid {cor_b};border-radius:10px;"
            f"padding:0.8rem 1rem;margin-top:0.5rem;margin-bottom:1rem;'>"
            f"<p style='font-weight:700;color:{cor_t};font-size:0.85rem;margin:0 0 6px;'>"
            f"⚠️ Atenção — Manutenções pendentes</p>"
            f"<ul style='margin:0;padding-left:1.2rem;color:{cor_t};font-size:0.82rem;'>"
            f"{items}</ul></div>",
            unsafe_allow_html=True,
        )

    # ── Filtros ────────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            tipo_opts = ["Todos", "Calendário", "Horímetro", "Condição"]
            tipo_f    = st.selectbox("Tipo", tipo_opts, key="_pm_tipo_f")
        with c2:
            status_opts = ["Todos", "Vencida", "Próxima do vencimento", "Em dia",
                           "Depende de análise preditiva", "Concluída"]
            status_f    = st.selectbox("Status", status_opts, key="_pm_st_f")
        with c3:
            prio_opts = ["Todas", "Crítica", "Alta", "Média", "Baixa"]
            prio_f    = st.selectbox("Prioridade", prio_opts, key="_pm_prio_f")

    # Aplica filtros
    filtered = tasks_enriched
    if tipo_f != "Todos":
        filtered = [e for e in filtered if e["tipo"] == tipo_f]
    if status_f != "Todos":
        sf = _norm(status_f)
        filtered = [e for e in filtered if e["status_key"] == sf]
    if prio_f != "Todas":
        pf = prio_f.lower()
        filtered = [e for e in filtered
                   if _norm(str(e["task"].get("Prioridade", "")).strip()) == pf]

    # Ordena: Vencida → Próxima → Em dia → Condição
    _order = {"vencida": 0, "próxima do vencimento": 1, "proxima do vencimento": 1,
               "em dia": 2, "depende de análise preditiva": 3,
               "depende de analise preditiva": 3}
    filtered.sort(key=lambda e: _order.get(e["status_key"], 4))

    # ── Lista de tarefas ──────────────────────────────────────────────────────
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;"
        f"margin:0.5rem 0 0.5rem;'>"
        f"📋 Tarefas ({len(filtered)})</p>",
        unsafe_allow_html=True,
    )

    if not filtered:
        st.info("Nenhuma tarefa encontrada com os filtros selecionados.")
    else:
        preventivas = [e for e in filtered if _norm(e["tipo"]) != "condição" and
                       _norm(e["tipo"]) != "condicao" and _norm(e["tipo"]) != "condição"]
        condicao    = [e for e in filtered if _norm(e["tipo"]) in ("condição", "condicao")]

        for e in preventivas:
            _render_task_card_client(e)

        if condicao:
            _render_condicao_section(condicao)

    # ── Nota sobre análise por condição ───────────────────────────────────────
    st.markdown(
        f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
        f"border-radius:8px;padding:0.7rem 1rem;margin-top:1rem;'>"
        f"<p style='font-size:0.78rem;color:#1E40AF;margin:0;'>ℹ️ {_NOTE_CONDICAO}</p></div>",
        unsafe_allow_html=True,
    )


def _render_task_card_client(e: dict) -> None:
    task    = e["task"]
    nome    = str(task.get("Nome_Tarefa", "")).strip() or "Sem nome"
    tipo    = e["tipo"]
    cat     = str(task.get("Categoria", "")).strip()
    prio    = str(task.get("Prioridade", "")).strip()
    descr   = str(task.get("Descricao", "")).strip()
    recom   = str(task.get("Recomendacao", "")).strip()
    prox_dt = str(task.get("Proxima_Execucao_Data", "")).strip()
    prox_h  = str(task.get("Proxima_Execucao_Horimetro", "")).strip()
    pd_dias = str(task.get("Periodicidade_Dias", "")).strip()
    pd_hs   = str(task.get("Periodicidade_Horas", "")).strip()
    status  = e["status"]
    h_atual = e["h_atual"]

    sc, sb, sbo, st_ = _STATUS_BADGE.get(_norm(status), _STATUS_DEFAULT)
    icon = _TIPO_ICON.get(tipo, "📋")

    if tipo in ("Horímetro", "horimetro"):
        if prox_h and prox_h not in ("", "nan", "0"):
            restam = max(0, int(float(prox_h)) - h_atual)
            detalhe = f"Vence em {int(float(prox_h)):,}h  ·  restam {restam:,}h".replace(",", ".")
            if pd_hs:
                detalhe += f"  ·  periodicidade: {pd_hs}h"
        else:
            detalhe = f"Horímetro atual: {h_atual}h"
    elif tipo in ("Calendário", "calendario"):
        detalhe = f"Próxima: {prox_dt}" if prox_dt and prox_dt not in ("", "nan") else ""
        if pd_dias:
            detalhe += f"  ·  a cada {pd_dias} dias"
    else:
        detalhe = "Aguarda avaliação técnica"

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-left:4px solid {sc};border-radius:10px;"
        f"padding:0.85rem 1rem;margin-bottom:6px;'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:flex-start;flex-wrap:wrap;gap:5px;'>"
        f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.9rem;'>"
        f"{icon} {nome}</span>"
        f"<div style='display:flex;gap:5px;flex-wrap:wrap;'>"
        f"<span style='background:{sb};color:{st_};-webkit-text-fill-color:{st_};"
        f"border:1px solid {sbo};font-size:0.65rem;font-weight:700;"
        f"padding:2px 8px;border-radius:10px;'>{status}</span>"
        + (f"<span style='background:#F3F4F6;color:#374151;-webkit-text-fill-color:#374151;"
           f"font-size:0.65rem;font-weight:600;padding:2px 8px;border-radius:10px;'>{prio}</span>"
           if prio else "")
        + f"</div></div>"
        f"<p style='color:{COLOR_MUTED};font-size:0.77rem;margin:3px 0 0;'>"
        f"{cat}" + (f"  ·  {detalhe}" if detalhe else "") + "</p>"
        + (f"<p style='color:#475569;font-size:0.8rem;margin:5px 0 0;'>{descr[:180]}</p>"
           if descr and descr.lower() not in ("", "nan") else "")
        + (f"<p style='color:#1E40AF;font-size:0.78rem;background:#EFF6FF;"
           f"border-radius:6px;padding:4px 8px;margin:4px 0 0;'>"
           f"💡 {recom[:160]}{'…' if len(recom)>160 else ''}</p>"
           if recom and recom.lower() not in ("", "nan") else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    # Botão "Abrir chamado" para tarefas vencidas ou próximas do vencimento
    sk = e["status_key"]
    if sk in ("vencida", "próxima do vencimento", "proxima do vencimento"):
        task_id = str(task.get("Id", "")).strip()
        at_id   = e.get("ativo_id", "")
        prio_map = {"vencida": "Alta", "próxima do vencimento": "Média",
                    "proxima do vencimento": "Média"}
        cat_map  = {"vencida": "Manutenção vencida", "próxima do vencimento": "Manutenção próxima",
                    "proxima do vencimento": "Manutenção próxima"}
        desc_txt = f"Tarefa: {nome}\nStatus: {status}\nCategoria: {cat}"
        if detalhe:
            desc_txt += f"\n{detalhe}"
        if st.button(f"🔧 Abrir chamado — {nome[:30]}",
                     key=f"man_ch_{task_id or nome[:20]}",
                     use_container_width=False):
            st.session_state["abrir_chamado_titulo"]    = f"Manutenção: {nome}"
            st.session_state["abrir_chamado_descricao"] = desc_txt
            st.session_state["abrir_chamado_categoria"] = cat_map.get(sk, "Manutenção vencida")
            st.session_state["abrir_chamado_prioridade"]= prio_map.get(sk, "Média")
            st.session_state["abrir_chamado_origem"]    = "Plano de Manutenção"
            st.session_state["abrir_chamado_task_id"]   = task_id
            st.session_state["abrir_chamado_ativo_id"]  = at_id
            st.session_state["portal_page"] = "chamados"
            st.rerun()


def _render_condicao_section(condicao: list) -> None:
    st.markdown(
        f"<div style='background:#F0F9FF;border:1px solid #BAE6FD;"
        f"border-radius:10px;padding:0.85rem 1rem;margin-top:0.5rem;'>"
        f"<p style='font-weight:700;color:#0C4A6E;font-size:0.9rem;margin:0 0 6px;'>"
        f"🔍 Recomendações por Condição ({len(condicao)})</p>"
        f"<p style='font-size:0.78rem;color:#0369A1;margin:0 0 8px;'>"
        f"Estas intervenções não têm data automática — dependem de análise "
        f"técnica (vibração, óleo, termografia). Não constituem gatilho "
        f"automático por horímetro.</p>",
        unsafe_allow_html=True,
    )
    for e in condicao:
        task = e["task"]
        nome = str(task.get("Nome_Tarefa", "")).strip() or "Sem nome"
        cat  = str(task.get("Categoria", "")).strip()
        recom= str(task.get("Recomendacao", "")).strip()
        descr= str(task.get("Descricao", "")).strip()
        task_id = str(task.get("Id", "")).strip()
        at_id   = e.get("ativo_id", "")
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid #BAE6FD;"
            f"border-left:3px solid #38BDF8;border-radius:8px;"
            f"padding:0.65rem 0.9rem;margin-bottom:5px;'>"
            f"<p style='font-weight:700;color:#0C4A6E;font-size:0.85rem;margin:0;'>🔍 {nome}</p>"
            + (f"<p style='color:#0369A1;font-size:0.75rem;margin:2px 0 0;'>{cat}</p>" if cat else "")
            + (f"<p style='color:#475569;font-size:0.78rem;margin:3px 0 0;'>{descr[:140]}</p>"
               if descr and descr.lower() not in ("", "nan") else "")
            + (f"<p style='color:#1E40AF;font-size:0.76rem;margin:3px 0 0;'>"
               f"💡 {recom[:140]}{'…' if len(recom)>140 else ''}</p>"
               if recom and recom.lower() not in ("", "nan") else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        if st.button(f"🔧 Abrir chamado — {nome[:35]}",
                     key=f"cond_ch_{task_id or nome[:20]}",
                     use_container_width=False):
            desc_txt = f"Tarefa por condição: {nome}\nCategoria: {cat}"
            if recom:
                desc_txt += f"\nRecomendação: {recom[:300]}"
            st.session_state["abrir_chamado_titulo"]    = f"Avaliação por condição: {nome}"
            st.session_state["abrir_chamado_descricao"] = desc_txt
            st.session_state["abrir_chamado_categoria"] = "Recomendação por condição"
            st.session_state["abrir_chamado_prioridade"]= "Média"
            st.session_state["abrir_chamado_origem"]    = "Plano de Manutenção"
            st.session_state["abrir_chamado_task_id"]   = task_id
            st.session_state["abrir_chamado_ativo_id"]  = at_id
            st.session_state["portal_page"] = "chamados"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MODO MOCK — fallback quando Sheets está vazio
# ═══════════════════════════════════════════════════════════════════════════════

def _render_mock_mode(client_id: str) -> None:
    ativos, _ = _load(client_id)
    st.caption(
        "Exibindo plano de demonstração. "
        "O plano real dos seus ativos aparecerá aqui conforme os dados forem registrados."
    )

    tarefas_enriched = _enrich_tarefas_mock(ativos)

    _render_alertas_mock(tarefas_enriched)
    _render_proximas_cards_mock(tarefas_enriched)

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0 1rem;'/>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:1rem;margin:0 0 1rem;'>"
        f"📋 Plano Completo por Ativo</p>",
        unsafe_allow_html=True,
    )
    for a in ativos:
        plano = a.get("plano_manutencao", [])
        if not plano:
            continue
        nome   = a.get("nome", a.get("Tag", "Equipamento"))
        planta = a.get("Planta", "")
        h_atual = a.get("horimetro_atual", _HORIMETRO_ATUAL_MOCK)
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:12px;padding:1rem 1.25rem 0.75rem;margin-bottom:0.75rem;'>"
            f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:1rem;margin:0 0 4px;'>"
            f"⚙️ {nome}</p>"
            + (f"<p style='color:{COLOR_MUTED};font-size:0.78rem;margin:0 0 2px;'>🏭 {planta}</p>"
               if planta else "")
            + f"<p style='color:{COLOR_MUTED};font-size:0.78rem;margin:0;'>"
            f"⏱ Horímetro atual: <b style='color:{COLOR_NAVY};'>{h_atual:,}h</b></p>".replace(",", ".")
            + "</div>",
            unsafe_allow_html=True,
        )
        _render_plano_manutencao(plano)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)


def _enrich_tarefas_mock(ativos: list) -> list:
    resultado = []
    for a in ativos:
        nome   = a.get("nome", a.get("Tag", "Equipamento"))
        planta = a.get("Planta", "")
        h      = a.get("horimetro_atual", _HORIMETRO_ATUAL_MOCK)
        for t in a.get("plano_manutencao", []):
            s = _pm_calc_status(t)
            resultado.append({
                "ativo_nome":    nome,
                "planta":        planta,
                "horimetro_atual": h,
                "tarefa":        t,
                "status":        s,
                "status_key":    _norm(s),
            })
    return resultado


def _render_alertas_mock(tarefas_enriched: list) -> None:
    urgentes = [
        e for e in tarefas_enriched
        if e["status_key"] in ("vencido", "proximo do vencimento")
        and e["tarefa"].get("tipo") != "condicao"
    ]
    if not urgentes:
        return

    msgs = []
    for e in urgentes[:4]:
        t      = e["tarefa"]
        sk     = e["status_key"]
        tipo   = t.get("tipo", "")
        nome   = t.get("nome", "")
        if tipo == "horimetro":
            h_at = t.get("horimetro_atual", 0)
            v_h  = t.get("vencimento_horas", 0)
            restam = max(0, v_h - h_at)
            if sk == "vencido":
                msgs.append(f"🔴 <b>{nome}</b> — vencida há {abs(v_h - h_at):,}h.".replace(",", "."))
            else:
                msgs.append(f"🟡 <b>{nome}</b> — próxima do vencimento em <b>{restam:,}h</b>.".replace(",", "."))
        elif tipo == "calendario":
            prox = t.get("proxima_data", "")
            if sk == "vencido":
                msgs.append(f"🔴 <b>{nome}</b> — data de execução ultrapassada ({prox}).")
            else:
                msgs.append(f"🟡 <b>{nome}</b> — prevista para <b>{prox}</b>.")

    if msgs:
        has_venc = any("🔴" in m for m in msgs)
        cor_bg   = "#FEF2F2" if has_venc else "#FFFBEB"
        cor_b    = "#FCA5A5" if has_venc else "#FCD34D"
        cor_t    = "#991B1B" if has_venc else "#92400E"
        items    = "".join(f"<li style='margin-bottom:4px;'>{m}</li>" for m in msgs)
        st.markdown(
            f"<div style='background:{cor_bg};border:1px solid {cor_b};"
            f"border-left:4px solid {cor_b};border-radius:10px;"
            f"padding:0.8rem 1rem;margin-bottom:1rem;'>"
            f"<p style='font-weight:700;color:{cor_t};font-size:0.85rem;margin:0 0 6px;'>"
            f"⚠️ Atenção — Manutenções pendentes</p>"
            f"<ul style='margin:0;padding-left:1.2rem;color:{cor_t};font-size:0.82rem;'>"
            f"{items}</ul></div>",
            unsafe_allow_html=True,
        )


def _render_proximas_cards_mock(tarefas_enriched: list) -> None:
    preventivas = [e for e in tarefas_enriched if e["tarefa"].get("tipo") != "condicao"]

    def _urgency_key(e):
        t    = e["tarefa"]
        tipo = t.get("tipo", "")
        sk   = e["status_key"]
        order = {"vencido": 0, "proximo do vencimento": 1, "em dia": 2}.get(sk, 3)
        if tipo == "horimetro":
            restam = t.get("vencimento_horas", 9999) - t.get("horimetro_atual", 0)
            return (order, restam)
        if tipo == "calendario":
            prox = t.get("proxima_data", "")
            try:
                diff = (datetime.datetime.strptime(prox, "%d/%m/%Y") - datetime.datetime.now()).days
            except Exception:
                diff = 9999
            return (order, diff)
        return (order, 9999)

    top3 = sorted(preventivas, key=_urgency_key)[:3]
    if not top3:
        return

    st.markdown(
        f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:1rem;margin:0 0 0.75rem;'>"
        f"🔔 Próximas Manutenções</p>",
        unsafe_allow_html=True,
    )
    cols = st.columns(len(top3))
    for col, e in zip(cols, top3):
        t      = e["tarefa"]
        status = e["status"]
        scfg   = _pm_scfg(status)
        tipo   = t.get("tipo", "")
        icons  = {"calendario": "📆", "horimetro": "⏱", "condicao": "🔍"}
        icon   = icons.get(tipo, "📋")

        if tipo == "horimetro":
            h_at   = t.get("horimetro_atual", 0)
            v_h    = t.get("vencimento_horas", 0)
            restam = max(0, v_h - h_at)
            detalhe= f"em {restam:,}h (vence {v_h:,}h)".replace(",", ".")
        elif tipo == "calendario":
            detalhe = t.get("proxima_data", "")
        else:
            detalhe = "Aguarda análise"

        with col:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-top:3px solid {scfg['color']};border-radius:10px;"
                f"padding:0.85rem 1rem;'>"
                f"<p style='font-size:0.7rem;color:{COLOR_MUTED};margin:0 0 3px;'>"
                f"{icon} {t.get('categoria','')}</p>"
                f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
                f"margin:0 0 6px;line-height:1.3;'>{t.get('nome','')}</p>"
                f"<p style='font-size:0.78rem;font-weight:600;color:{scfg['color']};"
                f"-webkit-text-fill-color:{scfg['color']};margin:0 0 3px;'>{detalhe}</p>"
                f"<span style='background:{scfg['bg']};color:{scfg['text']};"
                f"-webkit-text-fill-color:{scfg['text']};border:1px solid {scfg['border']};"
                f"font-size:0.62rem;font-weight:700;padding:2px 6px;border-radius:8px;'>"
                f"{status}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
