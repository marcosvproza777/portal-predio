"""Painel de Condição de Ativos — monitoramento técnico com visual premium."""
import unicodedata
import pandas as pd
try:
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except ImportError:
    _HAS_PLOTLY = False

import streamlit as st
from auth import current_client_id, current_empresa
from sheets import get_ativos
from ui import empty_state, COLOR_NAVY, COLOR_BG, COLOR_CARD, COLOR_BORDER, COLOR_MUTED

TIPOS_LAUDOS = [
    ("ordem de servico",    "Ordem de Serviço"),
    ("analise de vibracao", "Análise de Vibração"),
    ("termografia",         "Termografia"),
    ("analise de oleo",     "Análise de Óleo"),
    ("alinhamento a laser", "Alinhamento a Laser"),
]

TIPO_ICONE = {
    "ordem de servico":    "📋",
    "analise de vibracao": "📳",
    "termografia":         "🌡️",
    "analise de oleo":     "🧪",
    "alinhamento a laser": "🎯",
}

HEALTH_PCT = {"Bom": 90, "Atenção": 50, "Crítico": 18}

_CSS_ANIMATIONS = """<style>
@keyframes pulse-red {
    0%   { box-shadow: 0 0 0 0 rgba(239,68,68,0.60); }
    70%  { box-shadow: 0 0 0 9px rgba(239,68,68,0); }
    100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
}
@keyframes pulse-yellow {
    0%   { box-shadow: 0 0 0 0 rgba(245,158,11,0.50); }
    70%  { box-shadow: 0 0 0 8px rgba(245,158,11,0); }
    100% { box-shadow: 0 0 0 0 rgba(245,158,11,0); }
}
.dot-critico {
    display:inline-block; width:11px; height:11px; border-radius:50%;
    background:#EF4444; animation: pulse-red 1.4s infinite;
    vertical-align:middle; margin-right:5px; flex-shrink:0;
}
.dot-atencao {
    display:inline-block; width:11px; height:11px; border-radius:50%;
    background:#F59E0B; animation: pulse-yellow 2s infinite;
    vertical-align:middle; margin-right:5px; flex-shrink:0;
}
.dot-bom {
    display:inline-block; width:11px; height:11px; border-radius:50%;
    background:#10B981; vertical-align:middle; margin-right:5px; flex-shrink:0;
}
.dot-outro {
    display:inline-block; width:11px; height:11px; border-radius:50%;
    background:#94A3B8; vertical-align:middle; margin-right:5px; flex-shrink:0;
}
.health-bar-track {
    background:#E2E8F0; border-radius:6px; height:8px; overflow:hidden;
    margin:6px 0 3px; width:100%;
}
.health-bar-fill {
    height:100%; border-radius:6px;
    transition: width 0.6s ease;
}
.pred-banner-title {
    color:#FFFFFF !important; -webkit-text-fill-color:#FFFFFF !important;
    font-size:1.9rem; font-weight:900; margin:0 0 0.3rem;
    letter-spacing:-0.02em; line-height:1.15;
    text-shadow:0 2px 8px rgba(0,0,0,0.55);
}
.pred-banner-sub {
    color:#38BDF8 !important; font-size:0.72rem; font-weight:700;
    letter-spacing:0.14em; text-transform:uppercase; margin:0 0 0.5rem;
}
</style>"""


def _sem_acento(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


def get_status_cfg(raw: str) -> dict:
    s = _sem_acento(raw.strip())
    if s in ("bom", "verde", "normal", "ok"):
        return {"key": "Bom",     "label": "BOM",     "dot": "#10B981",
                "bg": "#F0FDF4", "border": "#86EFAC", "text": "#065F46",
                "dot_cls": "dot-bom"}
    if s in ("atencao", "amarelo", "alerta", "atençao", "atenção"):
        return {"key": "Atenção", "label": "ATENÇÃO", "dot": "#F59E0B",
                "bg": "#FFFBEB", "border": "#FCD34D", "text": "#92400E",
                "dot_cls": "dot-atencao"}
    if s in ("critico", "vermelho", "critica", "crítico", "crítica"):
        return {"key": "Crítico", "label": "CRÍTICO", "dot": "#EF4444",
                "bg": "#FEF2F2", "border": "#FCA5A5", "text": "#991B1B",
                "dot_cls": "dot-critico"}
    return {"key": raw or "—",  "label": (raw or "—").upper(), "dot": "#94A3B8",
            "bg": "#F8FAFC", "border": "#CBD5E1", "text": "#475569",
            "dot_cls": "dot-outro"}


def render(logo_b64: str) -> None:
    st.markdown(_CSS_ANIMATIONS, unsafe_allow_html=True)

    empresa   = current_empresa()
    client_id = current_client_id()

    try:
        ativos = get_ativos(client_id)
    except Exception as e:
        st.error(f"Erro ao carregar ativos: {e}")
        return

    if ativos.empty:
        _render_empty_banner(empresa)
        empty_state("Nenhum ativo cadastrado. Adicione equipamentos na aba 'Ativos' da planilha.")
        return

    # Colunas mínimas obrigatórias — preenche com vazio se faltar
    for col in ("Tag", "Equipamentos", "Status", "Detalhes"):
        if col not in ativos.columns:
            ativos[col] = ""

    try:
        _render_painel(ativos, empresa, client_id)
    except Exception as e:
        st.error(f"Erro ao renderizar o painel: {e}")
        st.exception(e)


def _render_painel(ativos, empresa: str, client_id: str) -> None:
    """Renderização principal — separada para facilitar captura de erros."""

    ativos["_status_key"] = ativos["Status"].astype(str).apply(
        lambda v: get_status_cfg(v)["key"])
    PRIORITY = {"Crítico": 0, "Atenção": 1, "Bom": 2}
    ativos["_priority"] = ativos["_status_key"].map(lambda k: PRIORITY.get(k, 99))
    has_ns     = "Ns" in ativos.columns
    group_cols = ["Tag", "Ns"] if has_ns else ["Tag"]

    worst  = (ativos.sort_values("_priority")
              .groupby(group_cols, sort=False)["_status_key"].first())
    counts = worst.value_counts().to_dict()
    total  = len(worst)
    bom     = counts.get("Bom",     0)
    atencao = counts.get("Atenção",  0)
    critico = counts.get("Crítico", 0)

    # ── Banner principal ───────────────────────────────────────────────────────
    _render_banner(empresa, total, bom, atencao, critico)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Visão Executiva ───────────────────────────────────────────────────────
    _render_visao_executiva(empresa)

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0 1rem;'/>",
        unsafe_allow_html=True,
    )

    # ── Ordenação por prioridade ──────────────────────────────────────────────
    group_order = (ativos.sort_values("_priority")
                   .groupby(group_cols, sort=False).first().reset_index())
    group_order["_sort"] = pd.Categorical(
        group_order["_status_key"],
        categories=["Crítico", "Atenção", "Bom"], ordered=True)
    group_order = group_order.sort_values("_sort")[group_cols]

    for _, g in group_order.iterrows():
        mask = ativos["Tag"].astype(str).str.strip() == str(g["Tag"]).strip()
        if has_ns:
            mask &= ativos["Ns"].astype(str).str.strip() == str(g["Ns"]).strip()
        grupo = ativos[mask].sort_values("_priority")
        primeiro = grupo.iloc[0]

        tag   = str(primeiro.get("Tag",          "")).strip()
        equip = str(primeiro.get("Equipamentos", "")).strip()
        ns    = str(primeiro.get("Ns",           "")).strip() if has_ns else ""
        pior     = get_status_cfg(str(primeiro.get("_status_key", "")))
        pior_dot = pior["dot"]
        pior_cls = pior["dot_cls"]

        ns_txt = (
            f"&nbsp;<span style='color:#94A3B8;font-size:0.75rem;'>Nº {ns}</span>"
            if ns and ns.lower() not in ("", "nan") else ""
        )

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;"
            f"margin:1.5rem 0 0.5rem;padding-bottom:10px;"
            f"border-bottom:2.5px solid {pior_dot};'>"
            f"<span class='{pior_cls}'></span>"
            f"<span style='font-size:1.1rem;font-weight:800;color:{COLOR_NAVY};'>"
            f"{tag}{ns_txt}</span>"
            f"<span style='color:{COLOR_MUTED};font-size:0.88rem;'>— {equip}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        for _, row in grupo.iterrows():
            _render_card(row, has_ns)


# ── Componentes visuais ───────────────────────────────────────────────────────

def _render_banner(empresa: str, total: int, bom: int, atencao: int, critico: int) -> None:
    critico_pill = (
        f"<span style='background:rgba(239,68,68,0.25);color:#FCA5A5;"
        f"padding:5px 14px;border-radius:20px;font-size:0.8rem;font-weight:700;"
        f"border:1px solid rgba(239,68,68,0.35);'>🔴 {critico} Crítico</span>"
    ) if critico else ""

    st.markdown(
        f"<div style='background:linear-gradient(135deg,#08142B 0%,#1B2A6B 55%,#2563EB 100%);"
        f"border-radius:18px;padding:2rem 2.5rem 1.75rem;margin-bottom:1.25rem;"
        f"box-shadow:0 12px 40px rgba(10,22,40,0.35);'>"
        f"<p class='pred-banner-sub'>⚙️ Pred.IO · {empresa}</p>"
        f"<p class='pred-banner-title'>Painel de Condição de Ativos</p>"
        f"<p style='color:rgba(255,255,255,0.65);font-size:0.88rem;margin:0 0 1.4rem;line-height:1.5;'>"
        f"Monitoramento de Ativos Industriais</p>"
        f"<div style='display:flex;gap:10px;flex-wrap:wrap;align-items:center;'>"
        f"<span style='background:rgba(255,255,255,0.10);color:#E2E8F0;"
        f"padding:5px 16px;border-radius:20px;font-size:0.8rem;font-weight:600;"
        f"border:1px solid rgba(255,255,255,0.18);'>⚙️ {total} Ativos</span>"
        f"<span style='background:rgba(16,185,129,0.20);color:#6EE7B7;"
        f"padding:5px 14px;border-radius:20px;font-size:0.8rem;font-weight:700;"
        f"border:1px solid rgba(16,185,129,0.30);'>🟢 {bom} Bom</span>"
        f"<span style='background:rgba(245,158,11,0.20);color:#FCD34D;"
        f"padding:5px 14px;border-radius:20px;font-size:0.8rem;font-weight:700;"
        f"border:1px solid rgba(245,158,11,0.30);'>🟡 {atencao} Atenção</span>"
        f"{critico_pill}"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_empty_banner(empresa: str) -> None:
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#08142B,#1B2A6B);"
        f"border-radius:18px;padding:2rem 2.5rem;margin-bottom:1.25rem;'>"
        f"<p class='pred-banner-sub'>⚙️ &nbsp;Pred.IO · {empresa}</p>"
        f"<p class='pred-banner-title'>Painel de Condição de Ativos</p>"
        f"<p style='color:rgba(255,255,255,0.60);font-size:0.88rem;margin:0.3rem 0 0;'>"
        f"Monitoramento de Ativos Industriais</p>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_donut(total: int, bom: int, atencao: int, critico: int) -> None:
    if not _HAS_PLOTLY:
        # Fallback CSS quando plotly não está instalado
        pct_bom = round(bom / total * 100) if total else 0
        pct_at  = round(atencao / total * 100) if total else 0
        pct_cr  = round(critico / total * 100) if total else 0
        st.markdown(
            f"<div style='text-align:center;padding:1rem 0;'>"
            f"<p style='font-size:2.5rem;font-weight:900;color:#0F1F3D;margin:0;'>{total}</p>"
            f"<p style='font-size:0.75rem;color:#64748B;margin:0 0 1rem;'>ativos</p>"
            f"<div style='background:#E2E8F0;border-radius:8px;height:10px;overflow:hidden;'>"
            f"<div style='display:flex;height:100%;'>"
            f"<div style='width:{pct_bom}%;background:#10B981;'></div>"
            f"<div style='width:{pct_at}%;background:#F59E0B;'></div>"
            f"<div style='width:{pct_cr}%;background:#EF4444;'></div>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )
        return

    labels = ["Bom", "Atenção", "Crítico"]
    values = [bom, atencao, critico]
    colors = ["#10B981", "#F59E0B", "#EF4444"]

    filtered = [(lb, v, c) for lb, v, c in zip(labels, values, colors) if v > 0]
    if not filtered:
        return
    fl, fv, fc = zip(*filtered)

    fig = go.Figure(data=[go.Pie(
        labels=list(fl),
        values=list(fv),
        hole=0.68,
        marker=dict(colors=list(fc), line=dict(color="#fff", width=2)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value} ativo(s) — %{percent}<extra></extra>",
        sort=False,
    )])
    centro = f"{total}<br>ativos"
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", y=-0.06, x=0.5, xanchor="center",
                    font=dict(size=11, color="#64748B")),
        margin=dict(t=10, b=10, l=0, r=0),
        height=210,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(text=centro, x=0.5, y=0.5, showarrow=False,
                          font=dict(size=14, color=COLOR_NAVY), align="center")],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_metric_card(title: str, value: int, total: int,
                        color: str, bg: str) -> None:
    pct = round(value / total * 100) if total else 0
    st.markdown(
        f"<div style='background:{bg};border:1px solid {color}40;"
        f"border-left:5px solid {color};border-radius:14px;"
        f"padding:1.1rem 1.25rem;height:100%;min-height:120px;"
        f"box-shadow:0 2px 10px {color}18;'>"
        f"<p style='color:{color};font-size:0.7rem;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:0.08em;margin:0 0 0.4rem;'>{title}</p>"
        f"<p style='color:#0F1F3D;font-size:2.4rem;font-weight:900;"
        f"margin:0;line-height:1;'>{value}</p>"
        f"<p style='color:#94A3B8;font-size:0.75rem;margin:0.3rem 0 0;'>"
        f"{pct}% do total</p>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_card(row: pd.Series, has_ns: bool) -> None:
    cfg   = get_status_cfg(str(row.get("Status", "")))
    tag   = str(row.get("Tag",          "")).strip()
    equip = str(row.get("Equipamentos", "")).strip()
    ns    = str(row.get("Ns",           "")).strip() if has_ns else ""
    det   = str(row.get("Detalhes",     "")).strip()
    link  = str(row.get("Link_Documento","")).strip()
    tipo  = str(row.get("Tipo",         "")).strip()
    data  = str(row.get("Data",         "")).strip()

    dot, bg, border, label, text, dot_cls = (
        cfg["dot"], cfg["bg"], cfg["border"],
        cfg["label"], cfg["text"], cfg["dot_cls"])

    health = HEALTH_PCT.get(cfg["key"], 50)
    badge_tc = "#000" if dot == "#F59E0B" else "#fff"

    tipo_key = _sem_acento(tipo)
    icone = TIPO_ICONE.get(tipo_key, "📄")

    ns_html = (
        f"&nbsp;<span style='color:#94A3B8;font-size:0.75rem;font-weight:400;'>"
        f"Nº {ns}</span>"
        if ns and ns.lower() not in ("", "nan") else ""
    )
    meta_parts = []
    if tipo and tipo.lower() not in ("", "nan"):
        meta_parts.append(f"<span>{icone} {tipo}</span>")
    if data and data.lower() not in ("", "nan"):
        meta_parts.append(f"<span>📅 {data}</span>")
    meta_html = (
        f"<div style='display:flex;gap:14px;flex-wrap:wrap;margin:8px 0 4px;"
        f"font-size:0.78rem;color:{COLOR_MUTED};'>"
        + "".join(meta_parts) + "</div>"
    ) if meta_parts else ""

    health_color = dot
    health_bar = (
        f"<div class='health-bar-track'>"
        f"<div class='health-bar-fill' style='width:{health}%;background:{health_color};'>"
        f"</div></div>"
        f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:0 0 6px;'>"
        f"Índice de saúde: <b style='color:{text};'>{health}%</b></p>"
    )

    st.markdown(
        f"""<div style="background:{bg};
            border:1px solid {border};border-left:6px solid {dot};
            border-radius:14px;padding:1rem 1.4rem 0.9rem;margin-bottom:10px;
            box-shadow:0 3px 12px {dot}18;">
          <div style="display:flex;justify-content:space-between;
                      align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:2px;">
            <div>
              <span style="font-size:1rem;font-weight:800;color:{COLOR_NAVY};">
                {tag}{ns_html}</span>
              <span style="color:{COLOR_MUTED};font-size:0.85rem;margin-left:7px;">
                — {equip}</span>
            </div>
            <span style="display:flex;align-items:center;gap:6px;
                         background:{dot};color:{badge_tc};
                         -webkit-text-fill-color:{badge_tc};
                         font-size:0.72rem;font-weight:800;letter-spacing:0.06em;
                         padding:5px 14px;border-radius:20px;
                         box-shadow:0 3px 8px {dot}45;">
              <span class="{dot_cls}" style="margin-right:0;"></span>
              {label}
            </span>
          </div>
          {health_bar}
          {meta_html}
          <p style="margin:4px 0 0;color:#475569;font-size:0.84rem;line-height:1.65;">{det}</p>
        </div>""",
        unsafe_allow_html=True,
    )
    if link and link.lower() not in ("", "nan", "none"):
        st.link_button(f"📄 Ver Laudo — {tag}", link)


def _render_summary(ativos: pd.DataFrame, has_ns: bool) -> None:
    has_tipo = "Tipo" in ativos.columns
    has_data = "Data" in ativos.columns
    group_cols = ["Tag", "Ns"] if has_ns else ["Tag"]

    machines = (ativos.sort_values("_priority")
                .groupby(group_cols, sort=False).first()
                .reset_index()[group_cols])

    rows_html = ""
    for _, mrow in machines.iterrows():
        tag = str(mrow["Tag"]).strip()
        ns  = str(mrow.get("Ns", "")).strip() if has_ns else ""
        mask = ativos["Tag"].astype(str).str.strip() == tag
        if has_ns and ns and ns.lower() not in ("", "nan"):
            mask &= ativos["Ns"].astype(str).str.strip() == ns
        mdf = ativos[mask].copy()

        ns_line = (
            f"<br/><span style='font-size:0.62rem;color:#94A3B8;'>"
            f"Nº {ns}</span>"
        ) if ns and ns.lower() not in ("", "nan") else ""

        # Pior status geral da máquina
        pior_key = mdf.sort_values("_priority").iloc[0]["_status_key"]
        pior_dot = get_status_cfg(pior_key)["dot"]

        rows_html += (
            f"<div style='margin-bottom:10px;border-radius:12px;"
            f"overflow:hidden;border:1.5px solid {pior_dot}30;'>"
            f"<div style='background:linear-gradient(135deg,#08142B,#1B2A6B);"
            f"padding:8px 12px;display:flex;align-items:center;gap:8px;'>"
            f"<div style='width:8px;height:8px;border-radius:50%;"
            f"background:{pior_dot};flex-shrink:0;'></div>"
            f"<span style='font-size:0.8rem;font-weight:700;color:#fff;line-height:1.2;'>"
            f"{tag}{ns_line}</span></div>"
        )

        tem = False
        for tipo_key, tipo_label in TIPOS_LAUDOS:
            if has_tipo:
                tdf = mdf[mdf["Tipo"].astype(str).apply(
                    lambda v: _sem_acento(v.strip())) == tipo_key].copy()
            else:
                tdf = pd.DataFrame()
            if tdf.empty:
                continue
            tem = True
            if has_data:
                tdf["_dt"] = pd.to_datetime(
                    tdf["Data"].astype(str).str.strip(), dayfirst=True, errors="coerce")
                tdf = tdf.sort_values("_dt", ascending=False)
            cfg = get_status_cfg(str(tdf.iloc[0].get("Status", "")))
            dot, label = cfg["dot"], cfg["label"]
            bt = "#000" if dot == "#F59E0B" else "#fff"
            icone = TIPO_ICONE.get(tipo_key, "📄")
            rows_html += (
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;padding:7px 12px;background:#fff;"
                f"border-bottom:1px solid #F1F5F9;"
                f"border-left:3px solid {dot};'>"
                f"<span style='font-size:0.69rem;color:#64748B;'>{icone} {tipo_label}</span>"
                f"<span style='background:{dot};color:{bt};-webkit-text-fill-color:{bt};"
                f"font-size:0.64rem;font-weight:700;padding:2px 8px;"
                f"border-radius:10px;'>{label}</span>"
                f"</div>"
            )

        if not tem:
            rows_html += (
                "<div style='padding:9px 12px;background:#fff;'>"
                "<span style='font-size:0.72rem;color:#94A3B8;'>Sem laudos registrados</span></div>"
            )
        rows_html += "</div>"

    st.markdown(
        f"<div style='background:{COLOR_BG};border:1px solid {COLOR_BORDER};"
        f"border-radius:14px;padding:14px;position:sticky;top:1rem;'>"
        f"<p style='font-size:0.68rem;font-weight:700;color:#94A3B8;"
        f"letter-spacing:.10em;margin:0 0 12px;text-transform:uppercase;'>"
        f"📊 Status por Máquina</p>"
        f"{rows_html}</div>",
        unsafe_allow_html=True,
    )


def _render_alertas_importantes() -> None:
    """Card de alertas não lidos — máx 3 itens, link para Central de Alertas."""
    from page_alertas import _ALERTAS_MOCK, _TIPO_CFG, _PRIO_CFG
    from ui import COLOR_CARD, COLOR_BORDER as CB, COLOR_NAVY as CN, COLOR_MUTED as CM

    nao_lidos = [a for a in _ALERTAS_MOCK if a.get("status") == "nao_lido"]
    _PRIO_ORD = {"Alta": 0, "Média": 1, "Baixa": 2}
    top3 = sorted(nao_lidos, key=lambda a: _PRIO_ORD.get(a.get("prioridade", "Baixa"), 3))[:3]

    total_nao_lidos = len(nao_lidos)
    if total_nao_lidos == 0:
        return

    itens_html = ""
    for a in top3:
        tcfg    = _TIPO_CFG.get(a.get("tipo", ""), {"icone": "🔔", "label": ""})
        pcfg    = _PRIO_CFG.get(a.get("prioridade", "Baixa"), _PRIO_CFG["Baixa"])
        dot_cor = pcfg["dot"]
        itens_html += (
            f"<div style='display:flex;align-items:center;gap:8px;padding:7px 0;"
            f"border-bottom:1px solid {CB};'>"
            f"<span style='font-size:1rem;flex-shrink:0;'>{tcfg['icone']}</span>"
            f"<span style='flex:1;font-size:0.8rem;font-weight:600;color:{CN};"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
            f"{a.get('titulo','')}</span>"
            f"<span style='width:8px;height:8px;border-radius:50%;flex-shrink:0;"
            f"background:{dot_cor};'></span>"
            f"</div>"
        )

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {CB};"
        f"border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:center;margin-bottom:0.6rem;'>"
        f"<p style='font-weight:700;color:{CN};font-size:0.9rem;margin:0;'>"
        f"🔔 Alertas Importantes</p>"
        f"<span style='background:#EF4444;color:#fff;-webkit-text-fill-color:#fff;"
        f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:10px;'>"
        f"{total_nao_lidos} não lido{'s' if total_nao_lidos != 1 else ''}</span>"
        f"</div>"
        f"{itens_html}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.button("🔔 Ver todos os alertas →", key="farois_ver_alertas"):
        st.session_state["portal_page"] = "alertas"
        st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)


def _render_proximas_manutencoes() -> None:
    """Card discreto de próximas manutenções — máx 3 itens."""
    from page_ativos import _PLANO_MOCK_COMPRESSOR, _pm_calc_status, _pm_scfg, _norm

    # Monta top 3 tarefas (horímetro ordenado por urgência + calendário)
    horimetro = sorted(
        [t for t in _PLANO_MOCK_COMPRESSOR if t.get("tipo") == "horimetro"],
        key=lambda x: x.get("vencimento_horas", 9999) - x.get("horimetro_atual", 0)
    )
    calendario = [t for t in _PLANO_MOCK_COMPRESSOR if t.get("tipo") == "calendario"]
    top3 = (horimetro[:2] + calendario[:1])[:3]

    if not top3:
        return

    itens_html = ""
    for t in top3:
        status = _pm_calc_status(t)
        scfg   = _pm_scfg(status)
        tipo   = t.get("tipo", "")
        nome   = t.get("nome", "")
        if tipo == "horimetro":
            restam  = max(0, t.get("vencimento_horas", 0) - t.get("horimetro_atual", 0))
            detalhe = f"em {restam:,}h".replace(",", ".")
        else:
            detalhe = t.get("proxima_data", "")
        itens_html += (
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:center;padding:6px 0;"
            f"border-bottom:1px solid {COLOR_BORDER};'>"
            f"<span style='font-size:0.8rem;color:{COLOR_NAVY};font-weight:600;'>{nome}</span>"
            f"<span style='font-size:0.78rem;font-weight:700;color:{scfg['color']};"
            f"-webkit-text-fill-color:{scfg['color']};'>{detalhe}</span>"
            f"</div>"
        )

    from ui import COLOR_CARD, COLOR_BORDER as CB, COLOR_NAVY as CN, COLOR_MUTED as CM
    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {CB};"
        f"border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;'>"
        f"<p style='font-weight:700;color:{CN};font-size:0.9rem;margin:0 0 0.6rem;'>"
        f"🔔 Próximas Manutenções</p>"
        f"{itens_html}"
        f"<p style='font-size:0.72rem;color:{CM};margin:0.5rem 0 0;'>"
        f"→ Acesse a aba <b>📅 Plano de Manutenção</b> para ver o plano completo."
        f"</p></div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# VISÃO EXECUTIVA — mock data + funções de renderização
# ─────────────────────────────────────────────────────────────────────────────

_EXEC_MOCK = {
    "client_id": "coca-cola",
    # Métricas dos 6 cards
    "ativos_total":              1,
    "status_geral":              "Atenção",
    "status_geral_desc":         "Unidade Compressora 200 VLD requer acompanhamento",
    "componentes_criticos":      1,
    "componentes_criticos_desc": "Bomba de Óleo M60P em condição crítica",
    "manutencoes_proximas":      2,
    "manutencoes_desc":          "Análise de óleo e inspeção do filtro em 320 h",
    "chamados_abertos":          1,
    "chamados_desc":             "Chamado técnico em análise",
    "relatorios_recentes_n":     0,
    "relatorios_desc":           "Nenhum relatório publicado ainda",
    # Pontos de atenção e próximas ações são carregados dinamicamente — ver _render_visao_executiva
    "pontos_atencao": [],
    "proximas_acoes": [],
    # Resumo técnico
    "resumo_tecnico": (
        "A Unidade Compressora Parafuso 200 VLD apresenta status de Atenção, com score de saúde em 72/100. "
        "O componente Bomba de Óleo M60P está em condição crítica e há tarefas preventivas próximas do "
        "vencimento por horímetro. Recomenda-se manter acompanhamento integrado entre vibração, análise de "
        "óleo, temperatura, operação e chamados técnicos."
    ),
    # Relatórios recentes (carregados dinamicamente do Sheets — ver _render_visao_executiva)
    "relatorios": [],
    # Chamados em andamento
    "chamados": [
        {
            "titulo":     "Acompanhamento da Bomba de Óleo M60P",
            "status":     "Em análise",
            "prioridade": "Alta",
            "descricao":  "Chamado aberto para acompanhamento da condição crítica do componente vinculado à Unidade Compressora.",
        },
    ],
}

_EXEC_COR = {
    "Atenção":     "#F59E0B",
    "Crítico":     "#EF4444",
    "Bom":         "#10B981",
    "Crítica":     "#EF4444",
    "Alta":        "#F97316",
    "Média":       "#F59E0B",
    "Baixa":       "#64748B",
    "Em análise":  "#3B82F6",
    "Aberto":      "#F97316",
    "Em andamento":"#8B5CF6",
    "Concluído":   "#10B981",
}
_EXEC_COR_DEFAULT = "#94A3B8"


def _build_pontos_atencao(client_id: str) -> list:
    """Carrega pontos de atenção da aba AlertasSV para o cliente."""
    try:
        from sheets import get_alertas_sv
        df = get_alertas_sv(client_id)
        if df.empty:
            return []
        pontos = []
        for _, row in df.iterrows():
            pontos.append({
                "titulo":     str(row.get("Titulo",     "")).strip(),
                "descricao":  str(row.get("Descricao",  "")).strip(),
                "prioridade": str(row.get("Prioridade", "Média")).strip(),
                "link_page":  "ativos",
            })
        return pontos
    except Exception:
        return []


def _build_proximas_acoes() -> list:
    """Calcula próximas ações usando o horímetro real salvo no Sheets."""
    try:
        from page_ativos import _PLANO_MOCK_COMPRESSOR, _HORIMETRO_ATUAL_MOCK, _pm_calc_status, _norm, _MOCK
        from sheets import get_horimetro
        h = get_horimetro("AT-2026-001")
        if h is None:
            h = _HORIMETRO_ATUAL_MOCK
        plano = [{**t, "horimetro_atual": h} for t in _PLANO_MOCK_COMPRESSOR]

        # Identificação do ativo principal
        ativo       = _MOCK[0] if _MOCK else {}
        ativo_tag   = str(ativo.get("Tag", ativo.get("nome", ""))).strip()
        ativo_model = str(ativo.get("modelo", "")).strip()
        ativo_ns    = str(ativo.get("numero_serie", "")).strip()
        ativo_label = f"{ativo_tag} {ativo_model}".strip()
        ativo_id    = ativo_ns if ativo_ns and ativo_ns.lower() not in ("", "nan") else ativo_tag

        horimetro  = sorted(
            [t for t in plano if t.get("tipo") == "horimetro"],
            key=lambda x: x.get("vencimento_horas", 9999) - x.get("horimetro_atual", 0),
        )
        calendario = [t for t in plano if t.get("tipo") == "calendario"]
        acoes = []
        for t in (horimetro[:2] + calendario[:1])[:3]:
            tipo_t = t.get("tipo", "")
            if tipo_t == "horimetro":
                restam   = max(0, t.get("vencimento_horas", 0) - h)
                prazo    = f"em {restam:,}h".replace(",", ".")
                urgencia = "proximo" if _norm(_pm_calc_status(t)) in (
                    "proximo do vencimento", "vencido") else "normal"
            else:
                prazo    = t.get("proxima_data", "")
                urgencia = "normal"
            acoes.append({
                "nome":        t.get("nome", ""),
                "prazo":       prazo,
                "tipo":        "Preventiva por horímetro" if tipo_t == "horimetro"
                               else "Preventiva por calendário",
                "urgencia":    urgencia,
                "ativo_tag":   ativo_tag,
                "ativo_model": ativo_model,
                "ativo_ns":    ativo_ns,
                "ativo_label": ativo_label,
                "ativo_id":    ativo_id,
            })
        return acoes
    except Exception:
        return []


def _build_componentes_alarme(client_id: str) -> list:
    """Componentes em Crítico ou Atenção com identificação completa (nome, modelo, NS, ativo pai)."""
    try:
        from page_ativos import _MOCK
        alarmes = []
        for ativo in _MOCK:
            ativo_tag   = str(ativo.get("Tag", ativo.get("nome", ""))).strip()
            ativo_ns    = str(ativo.get("numero_serie", "")).strip()
            ativo_model = str(ativo.get("modelo", "")).strip()
            ativo_id = f"{ativo_tag} {ativo_model}".strip()
            if ativo_ns and ativo_ns.lower() not in ("", "nan"):
                ativo_id += f" — NS: {ativo_ns}"
            else:
                ativo_id += f" (tag: {ativo_tag})"
            for comp in ativo.get("componentes", []):
                cfg = get_status_cfg(str(comp.get("Status", "")))
                if cfg["key"] not in ("Crítico", "Atenção"):
                    continue
                cns  = str(comp.get("numero_serie", "")).strip()
                cmod = str(comp.get("modelo", "")).strip()
                alarmes.append({
                    "nome":         str(comp.get("nome", "")).strip(),
                    "modelo":       cmod,
                    "ns":           cns if cns and cns.lower() not in ("", "nan") else None,
                    "tag":          ativo_tag,
                    "status":       cfg["key"],
                    "status_dot":   cfg["dot"],
                    "status_label": cfg["label"],
                    "ativo_id":     ativo_id,
                })
        priority = {"Crítico": 0, "Atenção": 1}
        return sorted(alarmes, key=lambda x: priority.get(x["status"], 2))
    except Exception:
        return []


def _build_resumo_tecnico(client_id: str) -> str:
    """Resumo técnico dinâmico com identificação de ativos (NS ou tag) e componentes críticos."""
    try:
        from page_ativos import _MOCK, _HORIMETRO_ATUAL_MOCK
        from sheets import get_horimetro
        parts = []
        for ativo in _MOCK:
            tag     = str(ativo.get("Tag", ativo.get("nome", ""))).strip()
            modelo  = str(ativo.get("modelo", "")).strip()
            ns      = str(ativo.get("numero_serie", "")).strip()
            status  = str(ativo.get("Status", "")).strip()
            score   = ativo.get("Score", "—")
            try:
                h = get_horimetro("AT-2026-001") or _HORIMETRO_ATUAL_MOCK
            except Exception:
                h = _HORIMETRO_ATUAL_MOCK
            id_label = (
                f"NS: {ns}" if ns and ns.lower() not in ("", "nan") else f"tag: {tag}"
            )
            label = f"{tag} {modelo}".strip()
            criticos = [c for c in ativo.get("componentes", [])
                        if get_status_cfg(str(c.get("Status", "")))["key"] == "Crítico"]
            texto = (
                f"{label} ({id_label}) — Status: {status}, "
                f"Score de saúde: {score}/100, Horímetro: {h:,}h.".replace(",", ".")
            )
            if criticos:
                comp_parts = []
                for c in criticos:
                    cns   = str(c.get("numero_serie", "")).strip()
                    cmod  = str(c.get("modelo", "")).strip()
                    cnome = str(c.get("nome", "")).strip()
                    cid   = f"NS: {cns}" if cns and cns.lower() not in ("", "nan") else f"tag: {tag}"
                    comp_parts.append(f"{cnome} ({cmod}, {cid})" if cmod else f"{cnome} ({cid})")
                texto += f" Componente(s) crítico(s): {', '.join(comp_parts)}."
            rec = str(ativo.get("recomendacao", "")).strip()
            if rec:
                texto += f" {rec}"
            parts.append(texto)
        return " ".join(parts) if parts else _EXEC_MOCK.get("resumo_tecnico", "")
    except Exception:
        return _EXEC_MOCK.get("resumo_tecnico", "")


def _build_relatorios_recentes(client_id: str) -> list:
    """Carrega relatórios reais do Sheets."""
    try:
        from sheets import get_relatorios
        df = get_relatorios(client_id)
        if df.empty:
            return []
        result = []
        for _, row in df.head(3).iterrows():
            titulo = str(row.get("Titulo", "")).strip() or "Relatório"
            data   = str(row.get("Data_Relatorio", "")).strip()[:10]
            result.append({"titulo": titulo, "data": data})
        return result
    except Exception:
        return []


def _render_visao_executiva(empresa: str) -> None:
    """Painel executivo completo: métricas, atenção, ações, resumo, relatórios, chamados."""
    client_id = current_client_id()
    d = dict(_EXEC_MOCK)
    d["pontos_atencao"]        = _build_pontos_atencao(client_id)
    d["componentes_alarme"]    = _build_componentes_alarme(client_id)
    proximas                   = _build_proximas_acoes()
    d["proximas_acoes"]        = proximas
    d["manutencoes_proximas"]  = len(proximas)
    d["manutencoes_desc"]      = (
        ", ".join(a["nome"] for a in proximas[:2]) + " e outras"
        if len(proximas) > 2 else
        " e ".join(a["nome"] for a in proximas)
        if proximas else "Nenhuma manutenção próxima"
    )
    relatorios                 = _build_relatorios_recentes(client_id)
    d["relatorios"]            = relatorios
    d["relatorios_recentes_n"] = len(relatorios)
    d["relatorios_desc"]       = (f"{len(relatorios)} relatório(s) disponível(is)"
                                  if relatorios else "Nenhum relatório publicado ainda")
    d["resumo_tecnico"]        = _build_resumo_tecnico(client_id)

    alarmes   = d["componentes_alarme"]
    n_critico = sum(1 for a in alarmes if a["status"] == "Crítico")
    d["componentes_criticos"]      = n_critico
    d["componentes_criticos_desc"] = (
        ", ".join(
            f"{a['nome']}" + (f" (NS: {a['ns']})" if a.get("ns") else f" (tag: {a['tag']})")
            for a in alarmes if a["status"] == "Crítico"
        )[:120] or "Nenhum componente crítico"
    )

    # Status geral com NS ou tag do equipamento
    try:
        from page_ativos import _MOCK
        if _MOCK:
            av  = _MOCK[0]
            _ns  = str(av.get("numero_serie", "")).strip()
            _mod = str(av.get("modelo", "")).strip()
            _tag = str(av.get("Tag", av.get("nome", ""))).strip()
            _st  = str(av.get("Status", d["status_geral"])).strip()
            _id  = f"NS: {_ns}" if _ns and _ns.lower() not in ("", "nan") else f"tag: {_tag}"
            d["status_geral"]      = _st
            d["status_geral_desc"] = f"{_tag} {_mod} — {_id}"
    except Exception:
        pass

    st.markdown(
        f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:1.1rem;"
        f"margin:0.75rem 0 0.25rem;'>📊 Visão Executiva</p>"
        f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin:0 0 1rem;'>"
        f"Resumo da condição dos ativos, manutenções, relatórios e chamados da sua operação.</p>",
        unsafe_allow_html=True,
    )

    _render_exec_cards(d)

    st.markdown("<div style='height:0.9rem'></div>", unsafe_allow_html=True)

    if alarmes:
        _render_componentes_alarme(d)
        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        _render_pontos_atencao(d)
    with col_b:
        _render_proximas_acoes(d)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    _render_resumo_tecnico(d)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    col_r, col_c = st.columns(2)
    with col_r:
        _render_relatorios_recentes(d)
    with col_c:
        _render_chamados_abertos(d)


def _render_exec_cards(d: dict) -> None:
    cards = [
        {
            "titulo":    "Ativos monitorados",
            "valor":     str(d["ativos_total"]),
            "subtitulo": "Unidade Compressora acompanhada",
            "cor":       COLOR_NAVY,
            "icone":     "⚙️",
        },
        {
            "titulo":    "Status geral",
            "valor":     d["status_geral"],
            "subtitulo": d["status_geral_desc"],
            "cor":       _EXEC_COR.get(d["status_geral"], _EXEC_COR_DEFAULT),
            "icone":     "🟡" if d["status_geral"] == "Atenção" else ("🔴" if d["status_geral"] == "Crítico" else "🟢"),
        },
        {
            "titulo":    "Componentes críticos",
            "valor":     str(d["componentes_criticos"]),
            "subtitulo": d["componentes_criticos_desc"],
            "cor":       "#EF4444" if d["componentes_criticos"] > 0 else "#10B981",
            "icone":     "🔴" if d["componentes_criticos"] > 0 else "🟢",
        },
        {
            "titulo":    "Manutenções próximas",
            "valor":     str(d["manutencoes_proximas"]),
            "subtitulo": d["manutencoes_desc"],
            "cor":       "#F59E0B" if d["manutencoes_proximas"] > 0 else "#10B981",
            "icone":     "🔧",
        },
        {
            "titulo":    "Chamados abertos",
            "valor":     str(d["chamados_abertos"]),
            "subtitulo": d["chamados_desc"],
            "cor":       "#F97316" if d["chamados_abertos"] > 0 else "#10B981",
            "icone":     "📋",
        },
        {
            "titulo":    "Relatórios recentes",
            "valor":     str(d["relatorios_recentes_n"]),
            "subtitulo": d["relatorios_desc"],
            "cor":       "#3B82F6",
            "icone":     "📁",
        },
    ]

    row1 = st.columns(3)
    row2 = st.columns(3)
    for col, card in zip(list(row1) + list(row2), cards):
        with col:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-top:3px solid {card['cor']};border-radius:12px;"
                f"padding:0.85rem 1.1rem;margin-bottom:6px;"
                f"box-shadow:0 1px 4px rgba(15,31,61,0.05);'>"
                f"<p style='font-size:0.61rem;color:{COLOR_MUTED};text-transform:uppercase;"
                f"letter-spacing:.07em;margin:0 0 5px;'>{card['icone']} {card['titulo']}</p>"
                f"<p style='font-size:1.6rem;font-weight:900;color:{card['cor']};"
                f"-webkit-text-fill-color:{card['cor']};margin:0 0 3px;line-height:1.1;'>"
                f"{card['valor']}</p>"
                f"<p style='font-size:0.72rem;color:#64748B;margin:0;line-height:1.4;'>"
                f"{card['subtitulo']}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _render_componentes_alarme(d: dict) -> None:
    """Componentes em Crítico/Atenção com nome, modelo, NS e ativo pai."""
    alarmes = d.get("componentes_alarme", [])
    if not alarmes:
        return

    itens_html = ""
    for a in alarmes:
        dot   = a["status_dot"]
        label = a["status_label"]
        bt    = "#000" if dot == "#F59E0B" else "#fff"
        ns_html = (
            f"<span style='background:#F1F5F9;color:#475569;-webkit-text-fill-color:#475569;"
            f"font-size:0.72rem;padding:1px 7px;border-radius:6px;font-weight:600;'>"
            f"NS: {a['ns']}</span>"
        ) if a.get("ns") else (
            f"<span style='background:#F1F5F9;color:#64748B;-webkit-text-fill-color:#64748B;"
            f"font-size:0.72rem;padding:1px 7px;border-radius:6px;'>"
            f"tag: {a['tag']}</span>"
        )
        mod_html = (
            f"<span style='background:#F1F5F9;color:#475569;-webkit-text-fill-color:#475569;"
            f"font-size:0.72rem;padding:1px 7px;border-radius:6px;'>"
            f"Modelo: {a['modelo']}</span>"
        ) if a.get("modelo") else ""

        itens_html += (
            f"<div style='display:flex;align-items:flex-start;gap:10px;"
            f"padding:9px 0;border-bottom:1px solid {dot}22;'>"
            f"<div style='width:10px;height:10px;border-radius:50%;flex-shrink:0;"
            f"background:{dot};margin-top:4px;'></div>"
            f"<div style='flex:1;min-width:0;'>"
            f"<div style='display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-bottom:5px;'>"
            f"<span style='font-weight:800;color:{COLOR_NAVY};font-size:0.9rem;'>{a['nome']}</span>"
            f"<span style='background:{dot};color:{bt};-webkit-text-fill-color:{bt};"
            f"font-size:0.62rem;font-weight:700;padding:2px 9px;border-radius:10px;"
            f"letter-spacing:.04em;'>{label}</span>"
            f"</div>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:5px;'>"
            f"{ns_html}{mod_html}"
            f"</div>"
            f"<span style='font-size:0.73rem;color:{COLOR_MUTED};'>"
            f"⚙️ Ativo: <b style='color:{COLOR_NAVY};'>{a['ativo_id']}</b></span>"
            f"</div></div>"
        )

    st.markdown(
        f"<div style='background:#FEF2F2;border:1px solid #FCA5A5;"
        f"border-left:5px solid #EF4444;border-radius:0 12px 12px 0;"
        f"padding:1rem 1.25rem;'>"
        f"<p style='font-weight:700;color:#991B1B;font-size:0.92rem;margin:0 0 0.75rem;'>"
        f"🔴 Componentes em Alarme</p>"
        f"{itens_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_pontos_atencao(d: dict) -> None:
    PRIO_COR = {
        "Crítica": "#EF4444",
        "Alta":    "#F97316",
        "Média":   "#F59E0B",
        "Baixa":   "#64748B",
    }

    pontos    = d.get("pontos_atencao", [])
    itens_html = ""
    for pa in pontos:
        cor = PRIO_COR.get(pa.get("prioridade", "Média"), "#F59E0B")
        itens_html += (
            f"<div style='border-left:4px solid {cor};padding:0.55rem 0.75rem;"
            f"margin-bottom:8px;background:{cor}12;border-radius:0 8px 8px 0;'>"
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:flex-start;gap:6px;margin-bottom:3px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.84rem;"
            f"line-height:1.35;'>{pa['titulo']}</span>"
            f"<span style='background:{cor}22;color:{cor};-webkit-text-fill-color:{cor};"
            f"border:1px solid {cor}55;font-size:0.61rem;font-weight:700;"
            f"padding:1px 7px;border-radius:8px;white-space:nowrap;flex-shrink:0;'>"
            f"{pa.get('prioridade','')}</span>"
            f"</div>"
            f"<p style='color:#475569;font-size:0.77rem;margin:0;line-height:1.45;'>"
            f"{pa['descricao']}</p>"
            f"</div>"
        )
    if not pontos:
        itens_html = (
            f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin:0;'>"
            f"Nenhum ponto de atenção no momento.</p>"
        )

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:12px;padding:1rem 1.25rem;'>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;margin:0 0 0.75rem;'>"
        f"⚠️ Pontos de Atenção</p>"
        f"{itens_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("⚠️ Ver ativos monitorados →", key="exec_ver_ativos"):
        st.session_state["portal_page"] = "ativos"
        st.session_state.pop("portal_ativo_id", None)
        st.rerun()


def _render_proximas_acoes(d: dict) -> None:
    URGENCIA = {
        "proximo": {"cor": "#F59E0B", "bg": "#FFFBEB"},
        "normal":  {"cor": "#3B82F6", "bg": "#EFF6FF"},
    }

    acoes = d.get("proximas_acoes", [])

    if not acoes:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:12px;padding:1rem 1.25rem;'>"
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;margin:0 0 0.75rem;'>"
            f"🗓️ Próximas Ações</p>"
            f"<p style='color:{COLOR_MUTED};font-size:0.83rem;margin:0;'>"
            f"Nenhuma manutenção preventiva próxima.</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("📅 Ver plano completo →", key="exec_ver_plano"):
            st.session_state["portal_page"] = "manutencao"
            st.rerun()
        return

    # Agrupa ações por máquina (ativo_label) preservando ordem
    grupos: dict = {}
    for ac in acoes:
        key = ac.get("ativo_label", "Equipamento")
        if key not in grupos:
            grupos[key] = []
        grupos[key].append(ac)

    itens_html = ""
    for ativo_label, lista in grupos.items():
        ac0     = lista[0]
        ativo_ns    = ac0.get("ativo_ns", "")
        ativo_tag   = ac0.get("ativo_tag", "")
        ns_valid    = ativo_ns and ativo_ns.lower() not in ("", "nan")
        id_pill = (
            f"<span style='font-size:0.67rem;font-weight:700;color:#1E40AF;"
            f"-webkit-text-fill-color:#1E40AF;background:#EFF6FF;"
            f"padding:1px 7px;border-radius:6px;margin-left:5px;'>NS: {ativo_ns}</span>"
            if ns_valid else
            f"<span style='font-size:0.67rem;color:#64748B;-webkit-text-fill-color:#64748B;"
            f"background:#F1F5F9;padding:1px 7px;border-radius:6px;margin-left:5px;'>"
            f"tag: {ativo_tag}</span>"
        )
        # Cabeçalho da máquina
        itens_html += (
            f"<div style='background:{COLOR_NAVY}10;border-radius:7px;"
            f"padding:5px 10px;margin-bottom:4px;display:flex;align-items:center;gap:3px;flex-wrap:wrap;'>"
            f"<span style='font-size:0.75rem;font-weight:700;color:{COLOR_NAVY};'>⚙️ {ativo_label}</span>"
            f"{id_pill}"
            f"</div>"
        )
        for ac in lista:
            ucfg = URGENCIA.get(ac.get("urgencia", "normal"), URGENCIA["normal"])
            itens_html += (
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:flex-start;padding:6px 0 6px 12px;"
                f"border-bottom:1px solid {COLOR_BORDER};gap:8px;'>"
                f"<div style='flex:1;min-width:0;'>"
                f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.83rem;margin:0 0 2px;"
                f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{ac['nome']}</p>"
                f"<p style='font-size:0.7rem;color:{COLOR_MUTED};margin:0;'>{ac['tipo']}</p>"
                f"</div>"
                f"<span style='background:{ucfg['bg']};color:{ucfg['cor']};"
                f"-webkit-text-fill-color:{ucfg['cor']};border:1px solid {ucfg['cor']}55;"
                f"font-size:0.7rem;font-weight:700;padding:2px 8px;border-radius:8px;"
                f"white-space:nowrap;flex-shrink:0;'>{ac['prazo']}</span>"
                f"</div>"
            )
        itens_html += "<div style='height:6px'></div>"

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:12px;padding:1rem 1.25rem;'>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;margin:0 0 0.75rem;'>"
        f"🗓️ Próximas Ações</p>"
        f"{itens_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("📅 Ver plano completo →", key="exec_ver_plano"):
        st.session_state["portal_page"] = "manutencao"
        st.rerun()


def _render_resumo_tecnico(d: dict) -> None:
    texto = d.get("resumo_tecnico", "")
    if not texto:
        return
    st.markdown(
        f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
        f"border-left:5px solid #2563EB;border-radius:0 12px 12px 0;"
        f"padding:1rem 1.25rem;'>"
        f"<p style='font-size:0.66rem;font-weight:700;color:#1E40AF;"
        f"text-transform:uppercase;letter-spacing:.07em;margin:0 0 6px;'>"
        f"📝 Resumo Técnico da Operação</p>"
        f"<p style='color:#1E3A8A;font-size:0.88rem;margin:0;line-height:1.65;'>{texto}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_relatorios_recentes(d: dict) -> None:
    itens_html = ""
    for r in d.get("relatorios", []):
        itens_html += (
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:center;padding:7px 0;border-bottom:1px solid {COLOR_BORDER};gap:8px;'>"
            f"<p style='font-size:0.82rem;font-weight:600;color:{COLOR_NAVY};margin:0;"
            f"flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>"
            f"{r['titulo']}</p>"
            f"<span style='font-size:0.7rem;color:{COLOR_MUTED};white-space:nowrap;flex-shrink:0;'>"
            f"{r['data']}</span>"
            f"</div>"
        )

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:12px;padding:1rem 1.25rem;'>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;margin:0 0 0.75rem;'>"
        f"📁 Relatórios Recentes</p>"
        f"{itens_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("📁 Ver todos os relatórios →", key="exec_ver_relat"):
        st.session_state["portal_page"] = "relatorios"
        st.rerun()


def _render_chamados_abertos(d: dict) -> None:
    chamados = d.get("chamados", [])

    PRIO_CFG = {
        "Crítica": {"cor": "#EF4444", "bg": "#FEF2F2"},
        "Alta":    {"cor": "#F97316", "bg": "#FFF7ED"},
        "Média":   {"cor": "#F59E0B", "bg": "#FFFBEB"},
        "Baixa":   {"cor": "#64748B", "bg": "#F8FAFC"},
    }
    ST_CFG = {
        "Em análise":   {"cor": "#3B82F6", "bg": "#EFF6FF"},
        "Aberto":       {"cor": "#F97316", "bg": "#FFF7ED"},
        "Em andamento": {"cor": "#8B5CF6", "bg": "#F5F3FF"},
        "Concluído":    {"cor": "#10B981", "bg": "#F0FDF4"},
    }

    if not chamados:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:12px;padding:1rem 1.25rem;'>"
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;margin:0 0 0.5rem;'>"
            f"🔧 Chamados em Andamento</p>"
            f"<p style='color:{COLOR_MUTED};font-size:0.85rem;margin:0;'>Nenhum chamado em aberto.</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("🔧 Ver chamados →", key="exec_ver_cham"):
            st.session_state["portal_page"] = "chamados"
            st.rerun()
        return

    itens_html = ""
    for ch in chamados:
        pcfg = PRIO_CFG.get(ch.get("prioridade", "Média"), PRIO_CFG["Média"])
        scfg = ST_CFG.get(ch.get("status", "Aberto"), ST_CFG["Aberto"])
        itens_html += (
            f"<div style='border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {pcfg['cor']};border-radius:0 10px 10px 0;"
            f"padding:0.75rem 1rem;margin-bottom:8px;background:{pcfg['bg']};'>"
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:flex-start;gap:6px;flex-wrap:wrap;margin-bottom:5px;'>"
            f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.87rem;"
            f"line-height:1.35;'>{ch['titulo']}</span>"
            f"<div style='display:flex;gap:5px;flex-shrink:0;'>"
            f"<span style='background:{scfg['bg']};color:{scfg['cor']};"
            f"-webkit-text-fill-color:{scfg['cor']};border:1px solid {scfg['cor']}55;"
            f"font-size:0.64rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
            f"{ch['status']}</span>"
            f"<span style='background:{pcfg['bg']};color:{pcfg['cor']};"
            f"-webkit-text-fill-color:{pcfg['cor']};border:1px solid {pcfg['cor']}55;"
            f"font-size:0.64rem;font-weight:700;padding:2px 8px;border-radius:8px;'>"
            f"{ch['prioridade']}</span>"
            f"</div></div>"
            f"<p style='color:#475569;font-size:0.8rem;margin:0;line-height:1.5;'>"
            f"{ch['descricao']}</p>"
            f"</div>"
        )

    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:12px;padding:1rem 1.25rem;'>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;margin:0 0 0.75rem;'>"
        f"🔧 Chamados em Andamento</p>"
        f"{itens_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("🔧 Ver chamados →", key="exec_ver_cham"):
        st.session_state["portal_page"] = "chamados"
        st.rerun()
