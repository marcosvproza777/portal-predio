"""Faróis de Condição — saúde dos ativos."""
import unicodedata
import pandas as pd
import streamlit as st
from auth import current_client_id, current_empresa
from sheets import get_ativos
from ui import page_header, empty_state, COLOR_NAVY, COLOR_BG, COLOR_BORDER, COLOR_MUTED

TIPOS_LAUDOS = [
    ("ordem de servico",    "Ordem de Serviço"),
    ("analise de vibracao", "Análise de Vibração"),
    ("termografia",         "Termografia"),
    ("analise de oleo",     "Análise de Óleo"),
    ("alinhamento a laser", "Alinhamento a Laser"),
]


def _sem_acento(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


def get_status_cfg(raw: str) -> dict:
    s = _sem_acento(raw.strip())
    if s in ("bom", "verde", "normal", "ok"):
        return {"key": "Bom",     "label": "Bom",     "dot": "#10B981",
                "bg": "#F0FDF4", "border": "#6EE7B7", "text": "#065F46"}
    if s in ("atencao", "amarelo", "alerta", "atençao", "atenção"):
        return {"key": "Atenção", "label": "Atenção", "dot": "#F59E0B",
                "bg": "#FFFBEB", "border": "#FCD34D", "text": "#92400E"}
    if s in ("critico", "vermelho", "critica", "crítico", "crítica"):
        return {"key": "Crítico", "label": "Crítico", "dot": "#EF4444",
                "bg": "#FEF2F2", "border": "#FCA5A5", "text": "#991B1B"}
    return {"key": raw or "—", "label": raw or "—", "dot": "#94A3B8",
            "bg": "#F8FAFC", "border": "#CBD5E1", "text": "#475569"}


def render(logo_b64: str) -> None:
    empresa   = current_empresa()
    client_id = current_client_id()

    page_header("🚦 Faróis de Condição", f"Monitoramento de ativos · {empresa}")

    ativos = get_ativos(client_id)
    if ativos.empty:
        empty_state("Nenhum ativo cadastrado. Adicione equipamentos na aba 'Ativos' da planilha.")
        return

    required = {"Tag", "Equipamentos", "Status", "Detalhes"}
    if not required.issubset(ativos.columns):
        st.error(f"A aba 'Ativos' precisa das colunas: {required}")
        return

    ativos["_status_key"] = ativos["Status"].astype(str).apply(
        lambda v: get_status_cfg(v)["key"])
    PRIORITY = {"Crítico": 0, "Atenção": 1, "Bom": 2}
    ativos["_priority"] = ativos["_status_key"].map(lambda k: PRIORITY.get(k, 99))
    has_ns  = "Ns" in ativos.columns
    group_cols = ["Tag", "Ns"] if has_ns else ["Tag"]

    worst  = (ativos.sort_values("_priority")
              .groupby(group_cols, sort=False)["_status_key"].first())
    counts = worst.value_counts().to_dict()

    # ── Métricas ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⚙️ Ativos",    len(worst))
    c2.metric("🟢 Bom",       counts.get("Bom",     0))
    c3.metric("🟡 Atenção",   counts.get("Atenção",  0))
    c4.metric("🔴 Crítico",   counts.get("Crítico", 0))

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

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
            pior  = get_status_cfg(str(primeiro.get("_status_key", "")))

            # Cabeçalho do grupo
            ns_txt = f" · Nº {ns}" if ns and ns.lower() not in ("", "nan") else ""
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:10px;"
                f"margin:1.4rem 0 0.5rem;padding-bottom:10px;"
                f"border-bottom:2px solid {pior['dot']};'>"
                f"<span style='font-size:1.05rem;font-weight:800;color:{COLOR_NAVY};'>{tag}</span>"
                f"<span style='color:{COLOR_MUTED};font-size:0.88rem;'>— {equip}</span>"
                f"<span style='color:#94A3B8;font-size:0.78rem;'>{ns_txt}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            for _, row in grupo.iterrows():
                _render_card(row, has_ns)

    with col_summary:
        _render_summary(ativos, has_ns)


def _render_card(row: pd.Series, has_ns: bool) -> None:
    cfg   = get_status_cfg(str(row.get("Status", "")))
    tag   = str(row.get("Tag",          "")).strip()
    equip = str(row.get("Equipamentos", "")).strip()
    ns    = str(row.get("Ns",           "")).strip() if has_ns else ""
    det   = str(row.get("Detalhes",     "")).strip()
    link  = str(row.get("Link_Documento","")).strip()
    tipo  = str(row.get("Tipo",         "")).strip()
    data  = str(row.get("Data",         "")).strip()

    dot, bg, border, label, txt = (
        cfg["dot"], cfg["bg"], cfg["border"], cfg["label"], cfg["text"])

    ns_html = (
        f"&nbsp;<span style='color:#94A3B8;font-size:0.78rem;'>Nº {ns}</span>"
        if ns and ns.lower() not in ("", "nan") else ""
    )
    meta = []
    if tipo and tipo.lower() not in ("", "nan"): meta.append(f"📋 {tipo}")
    if data and data.lower() not in ("", "nan"): meta.append(f"📅 {data}")
    meta_html = (
        f"<div style='margin:7px 0 5px;font-size:0.78rem;color:{COLOR_MUTED};'>"
        + "  ·  ".join(meta) + "</div>"
    ) if meta else ""

    badge_tc = "#000" if dot == "#F59E0B" else "#fff"

    st.markdown(
        f"""<div style="background:{bg};
            border:1px solid {border};border-left:5px solid {dot};
            border-radius:12px;padding:1rem 1.25rem;margin-bottom:10px;
            box-shadow:0 2px 8px rgba(15,31,61,0.06);
            transition:box-shadow 0.2s;">
          <div style="display:flex;justify-content:space-between;
                      align-items:center;flex-wrap:wrap;gap:8px;">
            <div style="font-size:1.02rem;font-weight:700;color:{COLOR_NAVY};">
              {tag}{ns_html}
              <span style="font-weight:400;color:{COLOR_MUTED};font-size:0.87rem;
                           margin-left:6px;">— {equip}</span>
            </div>
            <span style="background:{dot};color:{badge_tc};
                         -webkit-text-fill-color:{badge_tc};
                         font-size:0.75rem;font-weight:700;
                         padding:4px 14px;border-radius:20px;
                         box-shadow:0 2px 6px rgba(0,0,0,0.12);">{label}</span>
          </div>
          {meta_html}
          <p style="margin:4px 0 0;color:#475569;font-size:0.85rem;line-height:1.6;">{det}</p>
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

        ns_txt = f"<br/><span style='font-size:0.65rem;color:#94A3B8;'>Nº {ns}</span>" \
                 if ns and ns.lower() not in ("", "nan") else ""

        rows_html += (
            f"<div style='margin-bottom:12px;border-radius:10px;"
            f"overflow:hidden;border:1px solid #E2E8F0;'>"
            f"<div style='background:linear-gradient(135deg,#0F1F3D,#1B2A6B);"
            f"padding:7px 10px;'>"
            f"<span style='font-size:0.8rem;font-weight:700;color:#fff;'>{tag}{ns_txt}</span>"
            f"</div>"
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
            rows_html += (
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;padding:6px 10px;background:#fff;"
                f"border-bottom:1px solid #F1F5F9;'>"
                f"<span style='font-size:0.7rem;color:#64748B;'>{tipo_label}</span>"
                f"<span style='background:{dot};color:{bt};-webkit-text-fill-color:{bt};"
                f"font-size:0.65rem;font-weight:700;padding:2px 8px;"
                f"border-radius:10px;'>{label}</span>"
                f"</div>"
            )
        if not tem:
            rows_html += (
                "<div style='padding:8px 10px;background:#fff;'>"
                "<span style='font-size:0.72rem;color:#94A3B8;'>Sem laudos</span></div>"
            )
        rows_html += "</div>"

    st.markdown(
        f"<div style='background:{COLOR_BG};border:1px solid {COLOR_BORDER};"
        f"border-radius:12px;padding:14px;position:sticky;top:1rem;'>"
        f"<p style='font-size:0.7rem;font-weight:700;color:#94A3B8;letter-spacing:.08em;"
        f"margin:0 0 12px;text-transform:uppercase;'>Status por Máquina</p>"
        f"{rows_html}</div>",
        unsafe_allow_html=True,
    )
