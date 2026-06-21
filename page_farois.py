"""Faróis de Condição — saúde dos ativos (página extraída do app.py original)."""
import unicodedata
import pandas as pd
import streamlit as st
from auth import current_client_id, current_empresa
from sheets import get_ativos
from ui import page_header, empty_state, COLOR_NAVY, COLOR_BLUE, COLOR_BG, COLOR_BORDER

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
    if s in ("bom", "verde"):
        return {"key": "Bom",     "label": "Bom",     "dot": "#22c55e",
                "bg": "#f0fdf4", "border": "#86efac"}
    if s in ("atencao", "amarelo"):
        return {"key": "Atenção", "label": "Atenção", "dot": "#f59e0b",
                "bg": "#fffbeb", "border": "#fcd34d"}
    if s in ("critico", "vermelho"):
        return {"key": "Crítico", "label": "Crítico", "dot": "#ef4444",
                "bg": "#fef2f2", "border": "#fca5a5"}
    return {"key": raw, "label": raw, "dot": "#94a3b8",
            "bg": "#f8fafc", "border": "#cbd5e1"}


def render(logo_b64: str) -> None:
    empresa   = current_empresa()
    client_id = current_client_id()

    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        if logo_b64:
            st.markdown(
                f"<div style='padding-top:0.4rem;'>"
                f"<img src='data:image/jpeg;base64,{logo_b64}' style='width:80px;'/></div>",
                unsafe_allow_html=True,
            )
    with col_title:
        page_header("🚦 Faróis de Condição", f"Empresa: <strong>{empresa}</strong>")

    ativos = get_ativos(client_id)
    if ativos.empty:
        empty_state("Nenhum ativo cadastrado para sua empresa.")
        return

    required = {"Tag", "Equipamentos", "Status", "Detalhes"}
    if not required.issubset(ativos.columns):
        st.error(f"Aba 'Ativos' precisa das colunas: {required}")
        return

    ativos["_status_key"] = ativos["Status"].astype(str).apply(
        lambda v: get_status_cfg(v)["key"])
    PRIORITY = {"Crítico": 0, "Atenção": 1, "Bom": 2}
    ativos["_priority"] = ativos["_status_key"].map(lambda k: PRIORITY.get(k, 99))
    has_ns = "Ns" in ativos.columns
    group_cols = ["Tag", "Ns"] if has_ns else ["Tag"]

    worst = (ativos.sort_values("_priority")
             .groupby(group_cols, sort=False)["_status_key"].first())
    counts = worst.value_counts().to_dict()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de Ativos",  len(worst))
    c2.metric("🟢 Bom",           counts.get("Bom",     0))
    c3.metric("🟡 Atenção",       counts.get("Atenção",  0))
    c4.metric("🔴 Crítico",       counts.get("Crítico", 0))

    st.markdown(f"<h3 style='color:{COLOR_NAVY};margin-top:1.5rem;'>Faróis de Condição</h3>",
                unsafe_allow_html=True)

    group_order = (ativos.sort_values("_priority")
                   .groupby(group_cols, sort=False).first().reset_index())
    group_order["_sort"] = pd.Categorical(
        group_order["_status_key"],
        categories=["Crítico", "Atenção", "Bom"], ordered=True)
    group_order = group_order.sort_values("_sort")[group_cols]

    col_cards, col_summary = st.columns([3, 1])

    with col_cards:
        for _, g in group_order.iterrows():
            mask = ativos["Tag"].astype(str).str.strip() == str(g["Tag"]).strip()
            if has_ns:
                mask &= ativos["Ns"].astype(str).str.strip() == str(g["Ns"]).strip()
            grupo = ativos[mask].sort_values("_priority")
            primeiro = grupo.iloc[0]
            tag   = str(primeiro.get("Tag", "")).strip()
            equip = str(primeiro.get("Equipamentos", "")).strip()
            ns    = str(primeiro.get("Ns", "")).strip() if has_ns else ""
            pior  = get_status_cfg(str(primeiro.get("_status_key", "")))
            ns_html = (f"&nbsp;<span style='color:#94a3b8;font-size:0.8rem;'>Nº {ns}</span>"
                       if ns and ns.lower() not in ("", "nan") else "")
            st.markdown(
                f"<div style='margin:22px 0 6px;padding-bottom:8px;"
                f"border-bottom:2px solid {pior[\"dot\"]};'>"
                f"<span style='font-size:1.05rem;font-weight:800;color:{COLOR_NAVY};'>{tag}</span>"
                f"<span style='margin-left:8px;font-size:0.9rem;color:#475569;'>— {equip}</span>"
                f"{ns_html}</div>",
                unsafe_allow_html=True,
            )
            for _, row in grupo.iterrows():
                _render_asset_card(row, has_ns)

    with col_summary:
        _render_summary(ativos, has_ns)


def _render_asset_card(row: pd.Series, has_ns: bool) -> None:
    cfg   = get_status_cfg(str(row.get("Status", "")))
    tag   = str(row.get("Tag", "")).strip()
    equip = str(row.get("Equipamentos", "")).strip()
    ns    = str(row.get("Ns", "")).strip() if has_ns else ""
    det   = str(row.get("Detalhes", "")).strip()
    link  = str(row.get("Link_Documento", "")).strip()
    tipo  = str(row.get("Tipo", "")).strip()
    data  = str(row.get("Data", "")).strip()
    dot, bg, border, label = cfg["dot"], cfg["bg"], cfg["border"], cfg["label"]
    badge_text = "#000" if dot == "#f59e0b" else "#fff"
    equip_display = equip
    if ns and ns.lower() not in ("", "nan"):
        equip_display += f" &nbsp;<span style='color:#94a3b8;font-size:0.8rem;'>Nº {ns}</span>"
    meta_parts = []
    if tipo and tipo.lower() not in ("", "nan"): meta_parts.append(f"📋 {tipo}")
    if data and data.lower() not in ("", "nan"): meta_parts.append(f"📅 {data}")
    meta_html = (f"<div style='margin:6px 0 4px;font-size:0.8rem;color:#64748b;'>"
                 + "  &nbsp;|&nbsp;  ".join(meta_parts) + "</div>") if meta_parts else ""
    st.markdown(
        f"""<div style="background-color:{bg};border:1px solid {border};
                border-left:6px solid {dot};border-radius:10px;
                padding:16px 20px;margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
                <div><span style="font-size:1.05rem;font-weight:700;color:{COLOR_NAVY};">{tag}</span>
                     <span style="margin-left:8px;font-size:0.9rem;color:#475569;">— {equip_display}</span></div>
                <span style="display:inline-block;background-color:{dot};color:{badge_text};
                             -webkit-text-fill-color:{badge_text};
                             font-size:0.78rem;font-weight:700;padding:4px 12px;border-radius:20px;">{label}</span>
            </div>
            {meta_html}
            <p style="margin:6px 0 0;color:#475569;font-size:0.87rem;line-height:1.6;">{det}</p>
        </div>""",
        unsafe_allow_html=True,
    )
    if link and link.lower() not in ("", "nan", "none"):
        st.link_button(f"📄 Ver Laudo — {tag}", link, use_container_width=False)


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
        ns_txt = f" · Nº {ns}" if ns and ns.lower() not in ("", "nan") else ""
        rows_html += (f"<div style='margin-bottom:10px;'>"
                      f"<div style='font-size:0.82rem;font-weight:800;color:{COLOR_NAVY};"
                      f"padding:5px 10px;background:#e8edf4;border-radius:6px;margin-bottom:5px;'>"
                      f"{tag}{ns_txt}</div>")
        tem_dado = False
        for tipo_key, tipo_label in TIPOS_LAUDOS:
            if has_tipo:
                tdf = mdf[mdf["Tipo"].astype(str).apply(
                    lambda v: _sem_acento(v.strip())) == tipo_key].copy()
            else:
                tdf = pd.DataFrame()
            if tdf.empty:
                continue
            tem_dado = True
            if has_data:
                tdf["_dt"] = pd.to_datetime(
                    tdf["Data"].astype(str).str.strip(), dayfirst=True, errors="coerce")
                tdf = tdf.sort_values("_dt", ascending=False)
            cfg = get_status_cfg(str(tdf.iloc[0].get("Status", "")))
            dot, label = cfg["dot"], cfg["label"]
            bt = "#000" if dot == "#f59e0b" else "#fff"
            rows_html += (
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:4px 8px;margin-bottom:3px;background:#fff;"
                f"border-left:3px solid {dot};border-radius:5px;'>"
                f"<span style='font-size:0.7rem;color:#64748b;'>{tipo_label}</span>"
                f"<span style='background:{dot};color:{bt};-webkit-text-fill-color:{bt};"
                f"font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:10px;'>{label}</span>"
                f"</div>")
        if not tem_dado:
            rows_html += "<div style='font-size:0.72rem;color:#94a3b8;padding:3px 8px;'>Sem laudos</div>"
        rows_html += "</div>"

    st.markdown(
        f"<div style='background:{COLOR_BG};border:1px solid {COLOR_BORDER};"
        f"border-radius:10px;padding:14px;max-height:80vh;overflow-y:auto;'>"
        f"<p style='font-size:0.72rem;font-weight:700;color:#94a3b8;letter-spacing:.08em;"
        f"margin:0 0 10px;text-transform:uppercase;'>Status por Máquina</p>"
        f"{rows_html}</div>",
        unsafe_allow_html=True,
    )
