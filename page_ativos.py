"""Ativos Monitorados — visão consolidada dos equipamentos do cliente."""
import unicodedata
import pandas as pd
import streamlit as st
from auth import current_client_id
from sheets import get_ativos
from ui import page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED

# ── Dados mockados (fallback enquanto não há dados reais na planilha) ─────────
_MOCK = [
    {
        "Tag": "Bomba B-204",
        "Planta": "Jacarepaguá",
        "Tipo": "Bomba centrífuga",
        "Status": "Atenção",
        "Score": 72,
        "Ultima_Atualizacao": "17/06/2026",
        "Detalhes": "Vibração elevada detectada na última análise. Monitoramento semanal em curso.",
    },
    {
        "Tag": "Motor M-10",
        "Planta": "Rio de Janeiro",
        "Tipo": "Motor elétrico",
        "Status": "Bom",
        "Score": 91,
        "Ultima_Atualizacao": "15/06/2026",
        "Detalhes": "Operação normal. Temperaturas e vibração dentro dos parâmetros.",
    },
    {
        "Tag": "Compressor C-03",
        "Planta": "Jacarepaguá",
        "Tipo": "Compressor",
        "Status": "Crítico",
        "Score": 48,
        "Ultima_Atualizacao": "18/06/2026",
        "Detalhes": "Anomalia crítica identificada. Intervenção técnica recomendada com urgência.",
    },
    {
        "Tag": "Redutor R-08",
        "Planta": "Linha 02",
        "Tipo": "Redutor",
        "Status": "Em acompanhamento",
        "Score": 66,
        "Ultima_Atualizacao": "12/06/2026",
        "Detalhes": "Acompanhamento preventivo em curso. Próxima análise agendada.",
    },
]

# ── Config de status ──────────────────────────────────────────────────────────
_STATUS = {
    "bom":               {"color": "#10B981", "bg": "#F0FDF4", "border": "#86EFAC", "text": "#065F46", "icon": "🟢"},
    "atencao":           {"color": "#F59E0B", "bg": "#FFFBEB", "border": "#FCD34D", "text": "#92400E", "icon": "🟡"},
    "critico":           {"color": "#EF4444", "bg": "#FEF2F2", "border": "#FCA5A5", "text": "#991B1B", "icon": "🔴"},
    "em acompanhamento": {"color": "#38BDF8", "bg": "#F0F9FF", "border": "#BAE6FD", "text": "#0C4A6E", "icon": "🔵"},
}
_STATUS_DEFAULT = {"color": "#94A3B8", "bg": "#F8FAFC", "border": "#CBD5E1", "text": "#475569", "icon": "⚪"}

_SCORE_MAP = {"bom": 90, "atencao": 65, "critico": 40, "em acompanhamento": 66}


def _norm(s: str) -> str:
    """Remove acentos e coloca em minúsculas para comparações."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower().strip())
        if unicodedata.category(c) != "Mn"
    )


def _scfg(status: str) -> dict:
    return _STATUS.get(_norm(status), _STATUS_DEFAULT)


def _score_color(score: int) -> str:
    return "#10B981" if score >= 85 else "#F59E0B" if score >= 60 else "#EF4444"


def _score_label(score: int) -> str:
    if score >= 85:
        return "Condição boa — operação dentro dos parâmetros."
    if score >= 60:
        return "Requer atenção técnica — monitoramento intensificado recomendado."
    return "Condição crítica — intervenção técnica urgente necessária."


def _load(client_id: str):
    """Retorna (lista_ativos, usando_mock)."""
    try:
        df = get_ativos(client_id)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return _MOCK, True

    rows = []
    for _, row in df.iterrows():
        status = str(row.get("Status", "")).strip()
        sc_raw = row.get("Score", None)
        try:
            score = int(float(str(sc_raw))) if sc_raw and str(sc_raw).strip() not in ("", "nan") else None
        except (ValueError, TypeError):
            score = None
        if score is None:
            score = _SCORE_MAP.get(_norm(status), 50)

        rows.append({
            "Tag":                str(row.get("Tag", "")).strip(),
            "Planta":             str(row.get("Planta", "—")).strip() or "—",
            "Tipo":               (str(row.get("Tipo", "")) or str(row.get("Equipamentos", ""))).strip(),
            "Status":             status,
            "Score":              score,
            "Ultima_Atualizacao": str(row.get("Data", "—")).strip(),
            "Detalhes":           str(row.get("Detalhes", "")).strip(),
        })

    return (rows if rows else _MOCK), (not rows)


def render() -> None:
    page_header(
        "⚙️ Meus Equipamentos",
        "Acompanhe o status dos equipamentos monitorados pela Pred.IO.",
    )

    client_id = current_client_id()
    ativos, mock = _load(client_id)

    if mock:
        st.caption(
            "Exibindo dados de demonstração. "
            "Os dados reais dos seus ativos aparecerão aqui automaticamente."
        )

    # ── Filtros ───────────────────────────────────────────────────────────────
    col_s, col_p, _ = st.columns([1.3, 1.3, 2.4])
    status_opts = ["Todos os status", "Bom", "Atenção", "Crítico", "Em acompanhamento"]
    plantas     = ["Todas as plantas"] + sorted(
        {a["Planta"] for a in ativos if a["Planta"] not in ("", "—")}
    )

    with col_s:
        sf = st.selectbox("Filtrar por status", status_opts, label_visibility="collapsed")
    with col_p:
        pf = st.selectbox("Filtrar por planta", plantas, label_visibility="collapsed")

    # ── Aplicar filtros + ordenar: crítico primeiro ───────────────────────────
    out = [
        a for a in ativos
        if (_norm(sf) in ("todos os status", _norm(a["Status"])))
        and (pf == "Todas as plantas" or a["Planta"] == pf)
    ]
    out = sorted(out, key=lambda x: x["Score"])

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.85rem;margin:0.5rem 0 1rem;'>"
        f"{len(out)} ativo(s) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    if not out:
        st.info("Nenhum ativo encontrado com os filtros selecionados.")
        return

    for ativo in out:
        _render_card(ativo)


def _render_card(a: dict) -> None:
    cfg   = _scfg(a["Status"])
    sc    = _score_color(a["Score"])
    score = a["Score"]

    st.markdown(
        f"""<div style="background:{COLOR_CARD};border:1px solid {COLOR_BORDER};
            border-left:5px solid {cfg['color']};border-radius:14px;
            padding:1rem 1.4rem 1rem;margin-bottom:4px;
            box-shadow:0 2px 8px rgba(15,31,61,0.05);">
          <div style="display:flex;justify-content:space-between;
                      align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;">
            <div>
              <span style="font-size:1rem;font-weight:800;color:{COLOR_NAVY};">{a['Tag']}</span>
              <span style="color:{COLOR_MUTED};font-size:0.82rem;margin-left:8px;">— {a['Tipo']}</span>
            </div>
            <span style="background:{cfg['bg']};color:{cfg['text']};
                         -webkit-text-fill-color:{cfg['text']};
                         border:1px solid {cfg['border']};
                         font-size:0.72rem;font-weight:700;letter-spacing:0.04em;
                         padding:3px 14px;border-radius:20px;white-space:nowrap;">
              {cfg['icon']} {a['Status']}
            </span>
          </div>
          <div style="display:flex;gap:16px;font-size:0.78rem;color:{COLOR_MUTED};
                      flex-wrap:wrap;margin-bottom:10px;">
            <span>🏭 {a['Planta']}</span>
            <span>📅 {a['Ultima_Atualizacao']}</span>
          </div>
          <div style="display:flex;justify-content:space-between;
                      align-items:center;margin-bottom:3px;">
            <span style="font-size:0.68rem;font-weight:700;color:{COLOR_MUTED};
                         text-transform:uppercase;letter-spacing:0.07em;">Score de Saúde</span>
            <span style="font-size:0.85rem;font-weight:800;color:{sc};">{score}/100</span>
          </div>
          <div style="background:#E2E8F0;border-radius:6px;height:7px;overflow:hidden;">
            <div style="height:100%;border-radius:6px;background:{sc};width:{score}%;"></div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    with st.expander("Ver detalhes"):
        c1, c2 = st.columns(2)
        lbl = (
            "<p style='font-size:0.7rem;color:{m};margin:0 0 2px;"
            "text-transform:uppercase;letter-spacing:.06em;'>{t}</p>"
            "<p style='font-weight:700;color:{n};margin:0 0 12px;'>{v}</p>"
        )
        with c1:
            st.markdown(
                lbl.format(m=COLOR_MUTED, n=COLOR_NAVY, t="Tipo de Equipamento", v=a["Tipo"])
                + lbl.format(m=COLOR_MUTED, n=COLOR_NAVY, t="Planta", v=a["Planta"])
                + lbl.format(m=COLOR_MUTED, n=COLOR_NAVY, t="Última Atualização",
                             v=a["Ultima_Atualizacao"]).replace("margin:0 0 12px", "margin:0"),
                unsafe_allow_html=True,
            )
        with c2:
            det = a.get("Detalhes", "")
            obs_html = (
                f"<p style='font-size:0.7rem;color:{COLOR_MUTED};margin:12px 0 2px;"
                f"text-transform:uppercase;letter-spacing:.06em;'>Observação Técnica</p>"
                f"<p style='color:#475569;font-size:0.84rem;margin:0;'>{det}</p>"
            ) if det and det.lower() not in ("", "nan") else ""

            st.markdown(
                f"<p style='font-size:0.7rem;color:{COLOR_MUTED};margin:0 0 2px;"
                f"text-transform:uppercase;letter-spacing:.06em;'>Score de Saúde</p>"
                f"<p style='font-size:1.55rem;font-weight:900;color:{sc};margin:0 0 2px;'>"
                f"{score}"
                f"<span style='font-size:0.88rem;font-weight:500;color:{COLOR_MUTED};'>/100</span></p>"
                f"<p style='color:#475569;font-size:0.83rem;margin:0;'>{_score_label(score)}</p>"
                f"{obs_html}",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
