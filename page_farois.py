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
from ui import empty_state, COLOR_NAVY, COLOR_BG, COLOR_BORDER, COLOR_MUTED

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

    st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)

    # ── Gráfico de rosca + métricas numéricas ─────────────────────────────────
    col_donut, col_m1, col_m2, col_m3 = st.columns([1.6, 1, 1, 1])

    with col_donut:
        _render_donut(total, bom, atencao, critico)

    with col_m1:
        _render_metric_card("🟢 Condição Boa", bom, total, "#10B981", "#F0FDF4")
    with col_m2:
        _render_metric_card("🟡 Em Atenção", atencao, total, "#F59E0B", "#FFFBEB")
    with col_m3:
        _render_metric_card("🔴 Estado Crítico", critico, total, "#EF4444", "#FEF2F2")

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:0 0 1rem;'/>",
        unsafe_allow_html=True,
    )

    # ── Ordenação por prioridade ──────────────────────────────────────────────
    group_order = (ativos.sort_values("_priority")
                   .groupby(group_cols, sort=False).first().reset_index())
    group_order["_sort"] = pd.Categorical(
        group_order["_status_key"],
        categories=["Crítico", "Atenção", "Bom"], ordered=True)
    group_order = group_order.sort_values("_sort")[group_cols]

    col_cards, col_summary = st.columns([3, 1], gap="large")

    with col_cards:
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

    with col_summary:
        _render_summary(ativos, has_ns)


# ── Componentes visuais ───────────────────────────────────────────────────────

def _render_banner(empresa: str, total: int, bom: int, atencao: int, critico: int) -> None:
    critico_pill = (
        f"<span style='background:rgba(239,68,68,0.25);color:#FCA5A5;"
        f"padding:5px 14px;border-radius:20px;font-size:0.8rem;font-weight:700;"
        f"border:1px solid rgba(239,68,68,0.35);'>🔴 {critico} Crítico</span>"
    ) if critico else ""

    st.markdown(
        f"<style>.pred-banner-title{{color:#FFFFFF!important;"
        f"-webkit-text-fill-color:#FFFFFF!important;font-size:1.9rem;"
        f"font-weight:900;margin:0 0 0.3rem;letter-spacing:-0.02em;line-height:1.15;"
        f"text-shadow:0 2px 8px rgba(0,0,0,0.55);}}"
        f".pred-banner-sub{{color:#38BDF8!important;font-size:0.72rem;font-weight:700;"
        f"letter-spacing:0.14em;text-transform:uppercase;margin:0 0 0.5rem;}}</style>"
        f"<div style='background:linear-gradient(135deg,#08142B 0%,#1B2A6B 55%,#2563EB 100%);"
        f"border-radius:18px;padding:2rem 2.5rem 1.75rem;margin-bottom:1.25rem;"
        f"box-shadow:0 12px 40px rgba(10,22,40,0.35);'>"
        f"<p class='pred-banner-sub'>⚙️ Pred.IO · Portal do Cliente · {empresa}</p>"
        f"<p class='pred-banner-title'>Painel de Condição de Ativos</p>"
        f"<p style='color:rgba(255,255,255,0.65);font-size:0.88rem;margin:0 0 1.4rem;line-height:1.5;'>"
        f"Monitoramento Técnico e Status dos Ativos Acompanhados pela Pred.IO</p>"
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
        f"<style>.pred-banner-title{{color:#FFFFFF!important;"
        f"-webkit-text-fill-color:#FFFFFF!important;font-size:1.9rem;"
        f"font-weight:900;margin:0;letter-spacing:-0.02em;line-height:1.15;"
        f"text-shadow:0 2px 8px rgba(0,0,0,0.55);}}"
        f".pred-banner-sub{{color:#38BDF8!important;font-size:0.72rem;font-weight:700;"
        f"letter-spacing:0.14em;text-transform:uppercase;margin:0 0 0.5rem;}}</style>"
        f"<div style='background:linear-gradient(135deg,#08142B,#1B2A6B);"
        f"border-radius:18px;padding:2rem 2.5rem;margin-bottom:1.25rem;'>"
        f"<p class='pred-banner-sub'>⚙️ &nbsp;Pred.IO · {empresa}</p>"
        f"<p class='pred-banner-title'>Painel de Condição de Ativos</p>"
        f"<p style='color:rgba(255,255,255,0.60);font-size:0.88rem;margin:0.3rem 0 0;'>"
        f"Monitoramento Técnico e Status dos Ativos Acompanhados pela Pred.IO</p>"
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
