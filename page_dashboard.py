"""Dashboard Executivo Final — Portal do Cliente Pred.IO."""
import unicodedata
import pandas as pd
import streamlit as st
from auth import current_client_id, current_empresa
from ui import (page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER,
                COLOR_MUTED, COLOR_BLUE)

# ── Disclaimer obrigatório ────────────────────────────────────────────────────
_DISCLAIMER = (
    "O score de saúde é uma visão consolidada para priorização técnica e "
    "não substitui a avaliação da equipe Pred.IO."
)

# Score fictício por status (quando não há campo Score numérico)
_STATUS_SCORE = {"Bom": 90, "Atenção": 65, "Crítico": 40, "Urgente": 15}

# Recomendações padrão exibidas quando não há dados de relatórios
_RECOM_PADRAO = [
    "Acompanhar tendência de vibração do motor conforme histórico técnico.",
    "Antecipar análise de óleo conforme plano preditivo.",
    "Realizar termografia para investigar aquecimento.",
    "Verificar lubrificação dos rolamentos conforme plano.",
    "Avaliar troca de rolamento somente após análise de vibração — não automático.",
    "Overhaul depende de análise preditiva e avaliação técnica Pred.IO — não automático.",
]


# ── Normalizadores ────────────────────────────────────────────────────────────

def _sem_acento(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower().strip())
        if unicodedata.category(c) != "Mn"
    )


def _ativo_status(raw: str) -> str:
    s = _sem_acento(raw)
    if s in ("bom", "verde", "normal", "ok"):
        return "Bom"
    if s in ("atencao", "amarelo", "alerta"):
        return "Atenção"
    if s in ("critico", "critica", "vermelho"):
        return "Crítico"
    if s == "urgente":
        return "Urgente"
    return "—"


def _score_cor(score: int) -> tuple:
    """(cor_texto, cor_bg, cor_borda)"""
    if score >= 85:
        return "#059669", "#F0FDF4", "#86EFAC"
    if score >= 60:
        return "#D97706", "#FFFBEB", "#FCD34D"
    if score >= 30:
        return "#DC2626", "#FEF2F2", "#FCA5A5"
    return "#7C3AED", "#F5F3FF", "#C4B5FD"


def _score_label(score: int) -> str:
    if score >= 85:
        return "Bom"
    if score >= 60:
        return "Atenção"
    if score >= 30:
        return "Crítico"
    return "Urgente"


# ── Carregamento de dados ─────────────────────────────────────────────────────

def _load_data(client_id: str) -> dict:
    """Carrega todos os dados do dashboard — client_id sempre da sessão."""
    from sheets import (
        get_ativos, get_maintenance_tasks, calc_task_status,
        get_technical_reports, get_alertas_sv,
        get_chamados_resumo_assistente,
    )
    import datetime

    d = {
        # Ativos
        "ativos_total":  0,
        "score_medio":   0,
        "score_label":   "—",
        "n_bom":         0,
        "n_atencao":     0,
        "n_critico":     0,
        "n_urgente":     0,
        # Manutenção
        "manut_vencidas":  0,
        "manut_proximas":  0,
        "manut_condicao":  0,
        "manut_em_dia":    0,
        "manut_list":      [],
        # Chamados
        "cham_abertos":       0,
        "cham_analise":       0,
        "cham_aguardando":    0,
        "cham_concluidos_mes": 0,
        "cham_list":          [],
        # Alertas
        "alertas":        [],
        # Relatórios
        "relatorios":     [],
        # Recomendações e ações
        "recomendacoes":        [],
        "acoes_prioritarias":   [],
    }

    hoje_mes = datetime.datetime.now().strftime("%Y-%m")

    # ── Ativos ───────────────────────────────────────────────────────────────
    try:
        df_at = get_ativos(client_id)
        if not df_at.empty:
            d["ativos_total"] = len(df_at)
            df_at["_st"] = df_at["Status"].astype(str).apply(_ativo_status)
            d["n_bom"]     = int((df_at["_st"] == "Bom").sum())
            d["n_atencao"] = int((df_at["_st"] == "Atenção").sum())
            d["n_critico"] = int((df_at["_st"] == "Crítico").sum())
            d["n_urgente"] = int((df_at["_st"] == "Urgente").sum())

            # Score médio (campo numérico ou derivado do status)
            if "Score" in df_at.columns:
                scores = pd.to_numeric(df_at["Score"], errors="coerce").dropna()
                if len(scores) > 0:
                    d["score_medio"] = int(scores.mean())
            if d["score_medio"] == 0:
                vals = [
                    _STATUS_SCORE.get(s, 0)
                    for s in df_at["_st"]
                    if s != "—"
                ]
                d["score_medio"] = int(sum(vals) / len(vals)) if vals else 0

            d["score_label"] = _score_label(d["score_medio"])
    except Exception:
        pass

    # ── Manutenção ───────────────────────────────────────────────────────────
    try:
        df_mt = get_maintenance_tasks(client_id=client_id, staff=False)
        if not df_mt.empty:
            manut_list = []
            for _, row in df_mt.iterrows():
                task   = row.to_dict()
                status = calc_task_status(task, 0)
                tipo   = str(task.get("Tipo_Manutencao", "")).strip()
                nome   = str(task.get("Nome", "")).strip() or str(task.get("Descricao", "")).strip()
                ativo  = str(task.get("Ativo_Id", "")).strip()
                prox   = str(task.get("Proxima_Execucao_Data", "")).strip()

                tipo_n = _sem_acento(tipo)
                if tipo_n in ("condicao",):
                    d["manut_condicao"] += 1
                    continue  # Condição não aparece como vencida automaticamente

                s_n = _sem_acento(status)
                if "vencida" in s_n or "atraso" in s_n:
                    d["manut_vencidas"] += 1
                    urgencia = "vencida"
                elif "proxima" in s_n or "proximo" in s_n:
                    d["manut_proximas"] += 1
                    urgencia = "proxima"
                else:
                    d["manut_em_dia"] += 1
                    urgencia = "em_dia"

                if urgencia in ("vencida", "proxima"):
                    manut_list.append({
                        "nome":     nome or f"Tarefa ({tipo})",
                        "ativo":    ativo,
                        "status":   status,
                        "tipo":     tipo,
                        "prox":     prox,
                        "urgencia": urgencia,
                    })

            # Vencidas primeiro
            manut_list.sort(key=lambda x: 0 if x["urgencia"] == "vencida" else 1)
            d["manut_list"] = manut_list[:5]
    except Exception:
        pass

    # ── Chamados ─────────────────────────────────────────────────────────────
    try:
        chams = get_chamados_resumo_assistente(client_id)
        for ch in chams:
            st_raw = _sem_acento(str(ch.get("status", "")))
            if st_raw in ("concluido", "fechado", "cancelado"):
                data_ab = str(ch.get("aberto_em", ""))[:7]
                if data_ab == hoje_mes:
                    d["cham_concluidos_mes"] += 1
            elif "aguardando" in st_raw:
                d["cham_aguardando"] += 1
                d["cham_abertos"] += 1
            elif "analise" in st_raw or "análise" in st_raw:
                d["cham_analise"] += 1
                d["cham_abertos"] += 1
            else:
                d["cham_abertos"] += 1

        d["cham_list"] = [
            ch for ch in chams
            if _sem_acento(ch.get("status", "")) not in
            ("concluido", "fechado", "cancelado")
        ][:5]
    except Exception:
        pass

    # ── Alertas ──────────────────────────────────────────────────────────────
    try:
        df_al = get_alertas_sv(client_id)
        if not df_al.empty:
            _prio_ord = {"Urgente": 0, "Crítica": 0, "Alta": 1, "Média": 2, "Baixa": 3}
            alertas_raw = []
            for _, row in df_al.iterrows():
                alertas_raw.append({
                    "titulo":     str(row.get("Titulo", "")).strip(),
                    "prioridade": str(row.get("Prioridade", "Média")).strip(),
                    "ativo":      str(row.get("Ativo_Id", "")).strip(),
                    "descricao":  str(row.get("Descricao", "")).strip(),
                    "data":       str(row.get("Data", row.get("Criado_Em", ""))).strip(),
                })
            alertas_raw.sort(key=lambda a: _prio_ord.get(a["prioridade"], 3))
            d["alertas"] = alertas_raw[:5]
    except Exception:
        pass

    # ── Relatórios ───────────────────────────────────────────────────────────
    try:
        df_rel = get_technical_reports(client_id=client_id, staff=False)
        if not df_rel.empty:
            relatorios = []
            for _, row in df_rel.head(5).iterrows():
                sev      = str(row.get("Severidade", "Normal")).strip().lower()
                recomend = str(row.get("Recomendacoes", "")).strip()
                relatorios.append({
                    "titulo":     str(row.get("Titulo", "")).strip() or "Relatório",
                    "tipo":       str(row.get("Tipo_Servico", "")).strip(),
                    "ativo":      str(row.get("Ativo_Id", "")).strip(),
                    "data":       str(row.get("Data_Relatorio", "")).strip(),
                    "severidade": str(row.get("Severidade", "Normal")).strip(),
                    "url":        str(row.get("Arquivo_Url", "")).strip(),
                    "urgente":    sev in ("urgente", "crítico", "critico"),
                    "recomend":   recomend,
                })
                # Extrai recomendações para a seção de condição
                if recomend and recomend.lower() not in ("", "nan"):
                    texto = recomend[:200]
                    if texto not in d["recomendacoes"]:
                        d["recomendacoes"].append(texto)
            d["relatorios"] = relatorios
    except Exception:
        pass

    # Fallback de recomendações
    if not d["recomendacoes"]:
        d["recomendacoes"] = _RECOM_PADRAO[:4]

    # ── Ações Prioritárias ───────────────────────────────────────────────────
    acoes = []
    if d["manut_vencidas"]:
        acoes.append(("🚨", f"{d['manut_vencidas']} manutenção(ões) vencida(s) — atenção imediata", "manutencao"))
    if d["cham_aguardando"]:
        acoes.append(("⏳", f"{d['cham_aguardando']} chamado(s) aguardando sua resposta", "chamados"))
    if d["n_critico"] + d["n_urgente"] > 0:
        n = d["n_critico"] + d["n_urgente"]
        acoes.append(("🔴", f"{n} ativo(s) em estado crítico ou urgente", "ativos"))
    if d["relatorios"] and d["relatorios"][0].get("urgente"):
        titulo = d["relatorios"][0]["titulo"][:50]
        acoes.append(("📁", f"Relatório crítico disponível: {titulo}", "relatorios"))
    if d["manut_proximas"]:
        acoes.append(("🔧", f"{d['manut_proximas']} manutenção(ões) próxima(s) do vencimento", "manutencao"))
    if d["alertas"] and len(acoes) < 5:
        acoes.append(("🔔", f"{len(d['alertas'])} alerta(s) técnico(s) ativo(s)", "alertas"))
    d["acoes_prioritarias"] = acoes[:5]

    return d


# ── Cards superiores ──────────────────────────────────────────────────────────

def _card(icon: str, label: str, value, sublabel: str,
          cor: str, bg: str = COLOR_CARD, borda_top: str = "") -> str:
    bt = f"border-top:3px solid {borda_top or cor};"
    return (
        f"<div style='background:{bg};border:1px solid {COLOR_BORDER};"
        f"{bt}border-radius:12px;padding:0.85rem 1.1rem;"
        f"box-shadow:0 1px 4px rgba(15,31,61,0.05);'>"
        f"<p style='font-size:0.62rem;color:{COLOR_MUTED};text-transform:uppercase;"
        f"letter-spacing:.07em;margin:0 0 5px;'>{icon} {label}</p>"
        f"<p style='font-size:1.65rem;font-weight:900;color:{cor};"
        f"-webkit-text-fill-color:{cor};margin:0 0 3px;line-height:1.1;'>{value}</p>"
        f"<p style='font-size:0.7rem;color:{COLOR_MUTED};margin:0;'>{sublabel}</p>"
        f"</div>"
    )


def _render_top_cards(d: dict) -> None:
    sc, sb, _ = _score_cor(d["score_medio"])

    cards = [
        ("⚙️", "Ativos Monitorados",    d["ativos_total"],
         f"Bom: {d['n_bom']}  ·  Atenção: {d['n_atencao']}  ·  Crítico: {d['n_critico']}",
         COLOR_NAVY, "ativos"),

        ("💚", "Saúde Média",           f"{d['score_medio']}/100",
         f"Status geral: {d['score_label']}",
         sc, "ativos"),

        ("🟡", "Ativos em Atenção",     d["n_atencao"],
         "Monitoramento recomendado",
         "#D97706", "ativos"),

        ("🔴", "Ativos Críticos",       d["n_critico"] + d["n_urgente"],
         f"Crítico: {d['n_critico']}  ·  Urgente: {d['n_urgente']}",
         "#DC2626" if (d["n_critico"] + d["n_urgente"]) > 0 else "#10B981",
         "ativos"),

        ("📅", "Manutenções Vencidas",  d["manut_vencidas"],
         f"Próximas: {d['manut_proximas']}  ·  Em dia: {d['manut_em_dia']}",
         "#EF4444" if d["manut_vencidas"] > 0 else "#10B981",
         "manutencao"),

        ("🔧", "Chamados Abertos",       d["cham_abertos"],
         f"Em análise: {d['cham_analise']}  ·  Aguardando: {d['cham_aguardando']}",
         "#F97316" if d["cham_abertos"] > 0 else "#10B981",
         "chamados"),
    ]

    # 3 + 3 layout
    row1 = st.columns(3)
    row2 = st.columns(3)
    for (icon, label, val, sub, cor, page_key), col in zip(cards, list(row1) + list(row2)):
        with col:
            st.markdown(_card(icon, label, val, sub, cor), unsafe_allow_html=True)
            if st.button(f"Ver →", key=f"dash_card_{page_key}_{label[:6]}",
                         use_container_width=True):
                st.session_state["portal_page"] = page_key
                st.rerun()

    st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)


# ── Alertas Importantes ───────────────────────────────────────────────────────

_PRIO_COR = {
    "Urgente": "#7C3AED", "Crítica": "#DC2626",
    "Alta": "#F97316", "Média": "#F59E0B", "Baixa": "#64748B",
}


def _render_alertas(d: dict) -> None:
    alertas = d["alertas"]
    total   = len(alertas)

    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;'>"
        f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;'>🔔 Alertas Importantes</span>"
        + (f"<span style='background:#EF4444;color:#fff;-webkit-text-fill-color:#fff;"
           f"font-size:0.65rem;font-weight:700;padding:1px 7px;border-radius:8px;'>{total}</span>"
           if total > 0 else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    if not alertas:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:10px;padding:0.85rem 1rem;'>"
            f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin:0;'>Nenhum alerta ativo.</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        itens = ""
        for a in alertas:
            cor = _PRIO_COR.get(a["prioridade"], "#64748B")
            itens += (
                f"<div style='border-left:3px solid {cor};padding:6px 10px;"
                f"margin-bottom:6px;background:{cor}08;border-radius:0 8px 8px 0;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:4px;'>"
                f"<span style='font-size:0.8rem;font-weight:600;color:{COLOR_NAVY};"
                f"line-height:1.35;flex:1;'>{a['titulo']}</span>"
                f"<span style='background:{cor};color:#fff;-webkit-text-fill-color:#fff;"
                f"font-size:0.6rem;font-weight:700;padding:1px 6px;border-radius:6px;"
                f"white-space:nowrap;flex-shrink:0;'>{a['prioridade']}</span>"
                f"</div>"
                + (f"<p style='font-size:0.72rem;color:{COLOR_MUTED};margin:2px 0 0;'>"
                   f"⚙️ {a['ativo']}</p>" if a.get("ativo") else "")
                + "</div>"
            )
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:10px;padding:0.85rem 1rem;'>"
            f"{itens}"
            f"</div>",
            unsafe_allow_html=True,
        )

    if st.button("🔔 Ver todos os alertas →", key="dash_ver_alertas",
                 use_container_width=True):
        st.session_state["portal_page"] = "alertas"
        st.rerun()


# ── Manutenções ───────────────────────────────────────────────────────────────

def _render_manutencoes(d: dict) -> None:
    vencidas = d["manut_vencidas"]
    proximas = d["manut_proximas"]
    condicao = d["manut_condicao"]

    header_cor = "#EF4444" if vencidas > 0 else (
        "#F59E0B" if proximas > 0 else "#10B981"
    )

    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;'>"
        f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;'>📅 Manutenções</span>"
        + (f"<span style='background:{header_cor};color:#fff;-webkit-text-fill-color:#fff;"
           f"font-size:0.65rem;font-weight:700;padding:1px 7px;border-radius:8px;'>"
           f"{vencidas} vencida(s)</span>" if vencidas > 0 else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    # Resumo métrico
    resumo = (
        f"<div style='display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;'>"
        f"<span style='background:#FEF2F2;color:#991B1B;-webkit-text-fill-color:#991B1B;"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
        f"Vencidas: {vencidas}</span>"
        f"<span style='background:#FFFBEB;color:#92400E;-webkit-text-fill-color:#92400E;"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
        f"Próximas: {proximas}</span>"
        f"<span style='background:#EFF6FF;color:#1E40AF;-webkit-text-fill-color:#1E40AF;"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
        f"Por condição: {condicao}</span>"
        f"<span style='background:#F0FDF4;color:#065F46;-webkit-text-fill-color:#065F46;"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
        f"Em dia: {d['manut_em_dia']}</span>"
        f"</div>"
    )

    itens = ""
    if d["manut_list"]:
        for m in d["manut_list"]:
            cor = "#EF4444" if m["urgencia"] == "vencida" else "#F59E0B"
            label = "Vencida" if m["urgencia"] == "vencida" else "Próxima"
            itens += (
                f"<div style='display:flex;align-items:flex-start;gap:8px;"
                f"padding:6px 0;border-bottom:1px solid {COLOR_BORDER};'>"
                f"<div style='flex:1;min-width:0;'>"
                f"<p style='font-weight:600;color:{COLOR_NAVY};font-size:0.8rem;margin:0;"
                f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{m['nome']}</p>"
                f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:1px 0 0;'>"
                f"{m['tipo']} · {m['ativo'] or '—'}</p>"
                f"</div>"
                f"<span style='background:{cor};color:#fff;-webkit-text-fill-color:#fff;"
                f"font-size:0.62rem;font-weight:700;padding:2px 7px;border-radius:6px;"
                f"white-space:nowrap;flex-shrink:0;'>{label}</span>"
                f"</div>"
            )
    elif vencidas == 0 and proximas == 0:
        itens = (
            f"<p style='color:{COLOR_MUTED};font-size:0.8rem;margin:0;'>"
            f"Nenhuma manutenção urgente no momento.</p>"
        )

    # Nota sobre condição
    nota_cond = ""
    if condicao > 0:
        nota_cond = (
            f"<p style='font-size:0.7rem;color:#1E40AF;margin:6px 0 0;"
            f"background:#EFF6FF;border-radius:6px;padding:4px 8px;'>"
            f"💡 {condicao} tarefa(s) por condição — depende de análise preditiva.</p>"
        )

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:10px;padding:0.85rem 1rem;'>"
        f"{resumo}{itens}{nota_cond}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.button("📅 Ver plano de manutenção →", key="dash_ver_manut",
                 use_container_width=True):
        st.session_state["portal_page"] = "manutencao"
        st.rerun()


# ── Chamados ──────────────────────────────────────────────────────────────────

_CHAM_ST_COR = {
    "aberto":     ("#F97316", "#FFF7ED"),
    "em análise": ("#3B82F6", "#EFF6FF"),
    "em andamento": ("#8B5CF6", "#F5F3FF"),
    "aguardando cliente": ("#D97706", "#FFFBEB"),
    "concluído":  ("#10B981", "#F0FDF4"),
}


def _render_chamados(d: dict) -> None:
    abertos = d["cham_abertos"]

    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;'>"
        f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;'>🔧 Chamados</span>"
        + (f"<span style='background:#F97316;color:#fff;-webkit-text-fill-color:#fff;"
           f"font-size:0.65rem;font-weight:700;padding:1px 7px;border-radius:8px;'>"
           f"{abertos} aberto(s)</span>" if abertos > 0 else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    resumo = (
        f"<div style='display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;'>"
        f"<span style='background:#FFF7ED;color:#C2410C;-webkit-text-fill-color:#C2410C;"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
        f"Abertos: {abertos}</span>"
        f"<span style='background:#EFF6FF;color:#1D4ED8;-webkit-text-fill-color:#1D4ED8;"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
        f"Em análise: {d['cham_analise']}</span>"
        f"<span style='background:#FFFBEB;color:#92400E;-webkit-text-fill-color:#92400E;"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
        f"Aguardando: {d['cham_aguardando']}</span>"
        f"<span style='background:#F0FDF4;color:#065F46;-webkit-text-fill-color:#065F46;"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
        f"Concluídos no mês: {d['cham_concluidos_mes']}</span>"
        f"</div>"
    )

    itens = ""
    if d["cham_list"]:
        for ch in d["cham_list"]:
            st_raw = ch.get("status", "Aberto")
            st_key = st_raw.strip().lower()
            st_cor, st_bg = _CHAM_ST_COR.get(st_key, ("#94A3B8", "#F8FAFC"))
            prio   = ch.get("prioridade", "")
            cat    = ch.get("categoria", "")
            titulo = ch.get("titulo", "Chamado")
            itens += (
                f"<div style='display:flex;align-items:flex-start;gap:8px;"
                f"padding:6px 0;border-bottom:1px solid {COLOR_BORDER};'>"
                f"<div style='flex:1;min-width:0;'>"
                f"<p style='font-weight:600;color:{COLOR_NAVY};font-size:0.8rem;margin:0;"
                f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{titulo}</p>"
                f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:1px 0 0;'>"
                f"{cat or '—'}"
                + (f" · {prio}" if prio else "")
                + f"</p>"
                f"</div>"
                f"<span style='background:{st_bg};color:{st_cor};-webkit-text-fill-color:{st_cor};"
                f"border:1px solid {st_cor}44;font-size:0.6rem;font-weight:700;"
                f"padding:2px 7px;border-radius:6px;white-space:nowrap;flex-shrink:0;'>{st_raw}</span>"
                f"</div>"
            )
    else:
        itens = (
            f"<p style='color:{COLOR_MUTED};font-size:0.8rem;margin:0;'>"
            f"Nenhum chamado em aberto.</p>"
        )

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:10px;padding:0.85rem 1rem;'>"
        f"{resumo}{itens}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.button("🔧 Ver meus chamados →", key="dash_ver_cham",
                 use_container_width=True):
        st.session_state["portal_page"] = "chamados"
        st.rerun()


# ── Últimos Relatórios ────────────────────────────────────────────────────────

_SEV_COR = {
    "normal":   ("#10B981", "#F0FDF4", "#86EFAC"),
    "atenção":  ("#F59E0B", "#FFFBEB", "#FCD34D"),
    "atencao":  ("#F59E0B", "#FFFBEB", "#FCD34D"),
    "crítico":  ("#EF4444", "#FEF2F2", "#FCA5A5"),
    "critico":  ("#EF4444", "#FEF2F2", "#FCA5A5"),
    "urgente":  ("#7C3AED", "#F5F3FF", "#C4B5FD"),
}


def _render_relatorios(d: dict) -> None:
    relatorios = d["relatorios"]

    st.markdown(
        f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:1rem;margin:0 0 0.6rem;'>"
        f"📁 Últimos Relatórios Publicados</p>",
        unsafe_allow_html=True,
    )

    if not relatorios:
        st.info("Nenhum relatório publicado disponível. Entre em contato com a equipe Pred.IO.")
    else:
        for r in relatorios:
            sev_key = _sem_acento(r["severidade"])
            sc, sb, sbo = _SEV_COR.get(sev_key, ("#94A3B8", "#F8FAFC", "#CBD5E1"))

            meta_parts = []
            if r["tipo"]: meta_parts.append(f"📋 {r['tipo']}")
            if r["data"]: meta_parts.append(f"📅 {r['data']}")
            if r["ativo"]: meta_parts.append(f"⚙️ {r['ativo']}")
            meta_html = "  ·  ".join(
                f"<span style='color:{COLOR_MUTED};font-size:0.78rem;'>{m}</span>"
                for m in meta_parts
            )

            col_info, col_btn = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                    f"border-left:4px solid {sc};border-radius:10px;"
                    f"padding:10px 14px;margin-bottom:6px;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;"
                    f"gap:8px;margin-bottom:4px;'>"
                    f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;'>{r['titulo']}</span>"
                    f"<span style='background:{sb};color:{sc};-webkit-text-fill-color:{sc};"
                    f"border:1px solid {sbo};font-size:0.65rem;font-weight:700;"
                    f"padding:2px 9px;border-radius:10px;'>{r['severidade']}</span>"
                    f"</div>"
                    f"<div>{meta_html}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_btn:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                url = r.get("url", "")
                if url and url.lower() not in ("", "nan", "none"):
                    st.link_button("📄 Abrir", url, use_container_width=True)
                else:
                    if st.button("Ver →", key=f"dash_rel_{r['titulo'][:12]}",
                                 use_container_width=True):
                        st.session_state["portal_page"] = "relatorios"
                        st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if st.button("📁 Ver todos os relatórios →", key="dash_ver_relat"):
        st.session_state["portal_page"] = "relatorios"
        st.rerun()


# ── Recomendações por Condição ────────────────────────────────────────────────

def _render_recomendacoes(d: dict) -> None:
    recomendacoes = d["recomendacoes"]

    itens_html = ""
    for i, rec in enumerate(recomendacoes[:6]):
        # Regra: overhaul e rolamento nunca automáticos
        rec_safe = rec
        itens_html += (
            f"<div style='display:flex;align-items:flex-start;gap:8px;padding:7px 0;"
            f"border-bottom:1px solid {COLOR_BORDER};'>"
            f"<span style='font-size:0.85rem;flex-shrink:0;margin-top:1px;'>💡</span>"
            f"<p style='font-size:0.8rem;color:#1E3A8A;margin:0;line-height:1.5;'>{rec_safe}</p>"
            f"</div>"
        )

    if not itens_html:
        itens_html = (
            f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin:0;'>"
            f"Nenhuma recomendação disponível no momento.</p>"
        )

    st.markdown(
        f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
        f"border-radius:12px;padding:1rem 1.25rem;'>"
        f"<p style='font-weight:700;color:#1E40AF;font-size:0.92rem;margin:0 0 0.5rem;'>"
        f"💡 Recomendações por Condição</p>"
        f"<p style='font-size:0.68rem;color:#3B82F6;margin:0 0 0.75rem;'>"
        f"Baseado em relatórios técnicos, manutenção e avaliação Pred.IO</p>"
        f"{itens_html}"
        f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:8px 0 0;font-style:italic;'>"
        f"Overhaul e troca de rolamento dependem de análise preditiva — "
        f"nunca automáticos por horímetro. Fonte: Pred.IO</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("🔧 Abrir chamado técnico →", key="dash_cham_recom"):
        st.session_state["portal_page"] = "chamados"
        st.rerun()


# ── Ações Prioritárias ────────────────────────────────────────────────────────

def _render_acoes_prioritarias(d: dict) -> None:
    acoes = d["acoes_prioritarias"]

    if not acoes:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:12px;padding:1rem 1.25rem;'>"
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;margin:0 0 0.5rem;'>"
            f"✅ Ações Prioritárias</p>"
            f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin:0;'>"
            f"Nenhuma ação urgente no momento. Continue acompanhando.</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
        return

    ICONE_COR = {
        "🚨": "#EF4444",
        "⏳": "#D97706",
        "🔴": "#DC2626",
        "📁": "#2563EB",
        "🔧": "#F59E0B",
        "🔔": "#6366F1",
    }

    itens_html = ""
    for i, (icon, texto, page) in enumerate(acoes):
        cor = ICONE_COR.get(icon, "#64748B")
        itens_html += (
            f"<div style='display:flex;align-items:flex-start;gap:10px;"
            f"padding:8px 0;border-bottom:1px solid {cor}22;'>"
            f"<span style='font-size:1.1rem;flex-shrink:0;'>{icon}</span>"
            f"<div style='flex:1;'>"
            f"<p style='font-size:0.82rem;font-weight:600;color:{COLOR_NAVY};"
            f"margin:0;line-height:1.4;'>{texto}</p>"
            f"</div>"
            f"<span style='color:{cor};font-size:0.62rem;font-weight:700;"
            f"-webkit-text-fill-color:{cor};background:{cor}12;"
            f"padding:2px 7px;border-radius:6px;white-space:nowrap;flex-shrink:0;"
            f"align-self:flex-start;'>"
            f"#{i + 1}</span>"
            f"</div>"
        )

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-top:3px solid #EF4444;border-radius:12px;padding:1rem 1.25rem;'>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;margin:0 0 0.5rem;'>"
        f"🎯 Ações Prioritárias</p>"
        f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:0 0 0.75rem;'>"
        f"Itens que requerem atenção no momento</p>"
        f"{itens_html}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Botões de navegação rápida para as páginas das ações
    pages_set = list(dict.fromkeys(page for _, _, page in acoes))  # preserva ordem
    for pg in pages_set[:3]:
        label_map = {
            "manutencao": "📅 Ver manutenção",
            "chamados":   "🔧 Ver chamados",
            "ativos":     "⚙️ Ver ativos",
            "relatorios": "📁 Ver relatórios",
            "alertas":    "🔔 Ver alertas",
        }
        if st.button(label_map.get(pg, f"Ver {pg} →"), key=f"dash_acao_{pg}",
                     use_container_width=True):
            st.session_state["portal_page"] = pg
            st.rerun()


# ── Render Principal ──────────────────────────────────────────────────────────

def render() -> None:
    empresa   = current_empresa()
    client_id = current_client_id()  # SEMPRE da sessão, nunca do front-end

    page_header("📊 Dashboard", f"Visão executiva — {empresa}")

    # ── Banner de notificações não lidas ────────────────────────────────────
    try:
        from notifications import get_unread_count as _gnc
        _n_unread = _gnc(client_id)
        if _n_unread > 0:
            col_notif, _ = st.columns([6, 2])
            with col_notif:
                st.markdown(
                    f"<div style='background:#FEF2F2;border:1px solid #FECACA;"
                    f"border-radius:8px;padding:8px 14px;margin-bottom:0.5rem;"
                    f"display:flex;align-items:center;justify-content:space-between;'>"
                    f"<p style='margin:0;font-size:0.83rem;color:#991B1B;'>"
                    f"🔔 Você tem <strong>{_n_unread} notificação(ões) não lida(s)</strong>.</p>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"🔔 Ver notificações ({_n_unread})",
                    key="_dash_notif_btn",
                    use_container_width=False,
                ):
                    st.session_state["portal_page"] = "notificacoes"
                    st.rerun()
    except Exception:
        pass

    # Carrega todos os dados (client_id validado pelo auth)
    with st.spinner("Carregando..."):
        d = _load_data(client_id)

    # ── 6 Cards superiores ───────────────────────────────────────────────────
    _render_top_cards(d)

    # ── Disclaimer obrigatório ───────────────────────────────────────────────
    st.markdown(
        f"<p style='font-size:0.72rem;color:{COLOR_MUTED};text-align:center;"
        f"margin:0.1rem 0 1rem;font-style:italic;'>ℹ️ {_DISCLAIMER}</p>",
        unsafe_allow_html=True,
    )

    # ── Seção: Alertas | Manutenções | Chamados ──────────────────────────────
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        _render_alertas(d)
    with col_b:
        _render_manutencoes(d)
    with col_c:
        _render_chamados(d)

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0;'/>",
        unsafe_allow_html=True,
    )

    # ── Últimos Relatórios ───────────────────────────────────────────────────
    _render_relatorios(d)

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0;'/>",
        unsafe_allow_html=True,
    )

    # ── Recomendações | Ações Prioritárias ───────────────────────────────────
    col_r, col_ac = st.columns(2)
    with col_r:
        _render_recomendacoes(d)
    with col_ac:
        _render_acoes_prioritarias(d)

    # ── Rodapé informativo ───────────────────────────────────────────────────
    st.markdown(
        f"<div style='margin-top:2rem;padding:0.75rem 1rem;"
        f"background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:8px;'>"
        f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:0;text-align:center;'>"
        f"Dashboard Pred.IO · Fonte: Pred.IO · "
        f"Dados consolidados para priorização técnica. Não substitui avaliação presencial da equipe Pred.IO. "
        f"Overhaul e troca de rolamento nunca são automáticos por horímetro.</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
