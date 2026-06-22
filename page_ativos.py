"""Meus Equipamentos — catálogo e detalhe hierárquico dos ativos monitorados."""
import unicodedata
import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except ImportError:
    _HAS_PLOTLY = False

from auth import current_client_id
from sheets import get_ativos
from ui import page_header, COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BG

_DETALHE_KEY = "ativo_detalhe_id"

# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATA — estrutura hierárquica: ativo principal → componentes
# ═══════════════════════════════════════════════════════════════════════════════
_MOCK = [
    {
        "id":                    "unidade-compressora-parafuso-200-vld",
        "nome":                  "Unidade Compressora Parafuso",
        "Tag":                   "Unidade Compressora Parafuso",
        "Tipo":                  "Compressor de parafuso",
        "modelo":                "200 VLD",
        "numero_serie":          "CP-2026-001",
        "mb":                    "MB-01",
        "Planta":                "Sala de Compressores",
        "Status":                "Atenção",
        "Score":                 72,
        "Ultima_Atualizacao":    "17/06/2026",
        "criticidade":           "Média",
        "inversor_frequencia":   "Sim",
        "analise_oleo_aplicavel": True,
        "recomendacao": (
            "A unidade compressora apresenta redução gradual do score de saúde, "
            "com indicadores de óleo em atenção e componente Bomba de Óleo M60P em condição crítica. "
            "Recomenda-se acompanhamento integrado da unidade, correlacionando análise de óleo, "
            "vibração, temperatura, regime operacional, motor com inversor de frequência "
            "e condição da bomba de óleo."
        ),
        "historico_score": [
            {"mes": "Mar/2026", "score": 86},
            {"mes": "Abr/2026", "score": 80},
            {"mes": "Mai/2026", "score": 75},
            {"mes": "Jun/2026", "score": 72},
        ],
        "leitura_tendencia": (
            "O ativo apresenta redução gradual do score de saúde nos últimos ciclos, "
            "permanecendo em status de Atenção. Recomenda-se manter acompanhamento preditivo "
            "e avaliar os dados de vibração, temperatura e histórico operacional."
        ),
        "timeline": [
            {"data": "15/06/2026", "texto": "Monitoramento do Motor WEG 350 CV classificado como Bom"},
            {"data": "16/06/2026", "texto": "Análise de óleo indicou pontos de atenção em partículas e oxidação"},
            {"data": "17/06/2026", "texto": "Relatório de análise preditiva da Unidade Compressora publicado"},
            {"data": "18/06/2026", "texto": "Bomba de Óleo M60P classificada como Crítica"},
            {"data": "18/06/2026", "texto": "Status da Unidade Compressora alterado para Atenção"},
            {"data": "19/06/2026", "texto": "Recomendação de acompanhamento integrado registrada"},
        ],
        # ── Componentes vinculados ────────────────────────────────────────────
        "componentes": [
            {
                "nome":                "Motor WEG 350 CV",
                "tipo":               "Motor elétrico",
                "modelo":             "WEG 350 CV",
                "numero_serie":       "MT-2026-014",
                "mb":                 "MB-02",
                "inversor_frequencia":"Sim",
                "Status":             "Bom",
                "Score":              91,
                "Ultima_Atualizacao": "15/06/2026",
                "recomendacao": (
                    "O motor apresenta condição estável. Como opera com inversor de frequência, "
                    "recomenda-se considerar regime de rotação, variação de carga e possíveis "
                    "influências elétricas/mecânicas nas análises."
                ),
                "historico_score": [
                    {"mes": "Mar/2026", "score": 89},
                    {"mes": "Abr/2026", "score": 90},
                    {"mes": "Mai/2026", "score": 91},
                    {"mes": "Jun/2026", "score": 91},
                ],
            },
            {
                "nome":                "Bomba de Óleo M60P",
                "tipo":               "Bomba de óleo",
                "modelo":             "M60P",
                "numero_serie":       "BO-2026-008",
                "mb":                 "MB-03",
                "inversor_frequencia":"Não",
                "Status":             "Crítico",
                "Score":              48,
                "Ultima_Atualizacao": "18/06/2026",
                "recomendacao": (
                    "A bomba de óleo apresenta score crítico e requer acompanhamento técnico. "
                    "Recomenda-se verificar vibração, ruído operacional, pressão, vazão e condição "
                    "de funcionamento dentro do sistema de lubrificação da unidade compressora."
                ),
                "historico_score": [
                    {"mes": "Mar/2026", "score": 70},
                    {"mes": "Abr/2026", "score": 61},
                    {"mes": "Mai/2026", "score": 54},
                    {"mes": "Jun/2026", "score": 48},
                ],
            },
        ],
        # ── Análise de óleo (somente Unidade Compressora) ────────────────────
        "analise_oleo": {
            "titulo":    "Análise de Óleo da Unidade Compressora",
            "subtitulo": (
                "Indicadores de condição do óleo correlacionados com vibração, "
                "temperatura e operação da unidade."
            ),
            "indicadores": [
                {"nome": "Viscosidade",          "valor": "Atenção",  "tipo": "status"},
                {"nome": "Água",                 "valor": "Normal",   "tipo": "status"},
                {"nome": "Partículas",           "valor": "Atenção",  "tipo": "status"},
                {"nome": "Metais de desgaste",   "valor": "Atenção",  "tipo": "status"},
                {"nome": "Oxidação",             "valor": "Atenção",  "tipo": "status"},
                {"nome": "Aditivos",             "valor": "Atenção",  "tipo": "status"},
                {"nome": "Código ISO 4406",      "valor": "19/17/14", "tipo": "codigo"},
                {"nome": "Status geral do óleo", "valor": "Atenção",  "tipo": "status"},
            ],
            "historico_score": [
                {"mes": "Mar/2026", "score": 82},
                {"mes": "Abr/2026", "score": 78},
                {"mes": "Mai/2026", "score": 74},
                {"mes": "Jun/2026", "score": 70},
            ],
            "leitura": (
                "A unidade compressora apresenta redução gradual do score de saúde e indicadores "
                "de óleo em atenção. Recomenda-se correlacionar a evolução da vibração, temperatura, "
                "condição do óleo e histórico operacional nos próximos ciclos para definição "
                "de prioridade de intervenção."
            ),
        },
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
_STATUS = {
    "bom":               {"color": "#10B981", "bg": "#F0FDF4", "border": "#86EFAC", "text": "#065F46", "icon": "🟢"},
    "atencao":           {"color": "#F59E0B", "bg": "#FFFBEB", "border": "#FCD34D", "text": "#92400E", "icon": "🟡"},
    "critico":           {"color": "#EF4444", "bg": "#FEF2F2", "border": "#FCA5A5", "text": "#991B1B", "icon": "🔴"},
    "em acompanhamento": {"color": "#38BDF8", "bg": "#F0F9FF", "border": "#BAE6FD", "text": "#0C4A6E", "icon": "🔵"},
    "normal":            {"color": "#10B981", "bg": "#F0FDF4", "border": "#86EFAC", "text": "#065F46", "icon": "🟢"},
}
_STATUS_DEFAULT = {"color": "#94A3B8", "bg": "#F8FAFC", "border": "#CBD5E1", "text": "#475569", "icon": "⚪"}

_CRITICIDADE = {
    "alta":  {"color": "#EF4444", "bg": "#FEF2F2", "border": "#FCA5A5", "text": "#991B1B"},
    "media": {"color": "#F59E0B", "bg": "#FFFBEB", "border": "#FCD34D", "text": "#92400E"},
    "baixa": {"color": "#10B981", "bg": "#F0FDF4", "border": "#86EFAC", "text": "#065F46"},
}
_CRIT_DEFAULT = {"color": "#94A3B8", "bg": "#F8FAFC", "border": "#CBD5E1", "text": "#475569"}

_SCORE_MAP = {"bom": 90, "atencao": 65, "critico": 40, "em acompanhamento": 66}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _norm(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower().strip())
        if unicodedata.category(c) != "Mn"
    )


def _scfg(status: str) -> dict:
    return _STATUS.get(_norm(status), _STATUS_DEFAULT)


def _ccfg(crit: str) -> dict:
    return _CRITICIDADE.get(_norm(crit), _CRIT_DEFAULT)


def _score_color(score: int) -> str:
    return "#10B981" if score >= 85 else "#F59E0B" if score >= 60 else "#EF4444"


def _score_label(score: int) -> str:
    if score >= 85:
        return "Condição boa — operação dentro dos parâmetros."
    if score >= 60:
        return "Requer atenção técnica — monitoramento recomendado."
    return "Condição crítica — intervenção técnica urgente."


def _lbl(title: str, value: str) -> str:
    return (
        f"<p style='font-size:0.68rem;color:{COLOR_MUTED};margin:0 0 2px;"
        f"text-transform:uppercase;letter-spacing:.06em;'>{title}</p>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;margin:0 0 14px;'>{value}</p>"
    )


def _section(title: str) -> str:
    return (
        f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0 1rem;'/>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0 0 0.75rem;'>"
        f"{title}</p>"
    )


def _load(client_id: str):
    try:
        df = get_ativos(client_id)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return _MOCK, True

    # Old-format Ativos (Tag/Equipamentos/NS/Status) belongs to page_farois.
    # New-format ativos (from cadastrar_ativo_sv) have an Id column.
    # If Id column is absent, fall back to mock to avoid DuplicateWidgetID errors.
    if "Id" not in df.columns:
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

        tag = str(row.get("Tag", "")).strip()
        rows.append({
            "id":                    _norm(tag).replace(" ", "-"),
            "nome":                  tag,
            "Tag":                   tag,
            "Tipo":                  (str(row.get("Tipo", "")) or str(row.get("Equipamentos", ""))).strip(),
            "modelo":                str(row.get("Modelo", "—")).strip() or "—",
            "numero_serie":          str(row.get("Ns", "") or row.get("Numero_Serie", "")).strip() or "—",
            "mb":                    str(row.get("Mb", "")).strip() or "—",
            "Planta":                str(row.get("Planta", "—")).strip() or "—",
            "Status":                status,
            "Score":                 score,
            "Ultima_Atualizacao":    str(row.get("Data", "—")).strip(),
            "criticidade":           str(row.get("Criticidade", "—")).strip() or "—",
            "inversor_frequencia":   str(row.get("Inversor", "—")).strip() or "—",
            "analise_oleo_aplicavel": False,
            "recomendacao":          str(row.get("Detalhes", "")).strip(),
            "historico_score":       [],
            "leitura_tendencia":     "",
            "timeline":              [],
            "componentes":           [],
            "analise_oleo":          None,
        })

    return (rows if rows else _MOCK), (not rows)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def render() -> None:
    client_id = current_client_id()
    ativos, mock = _load(client_id)

    detalhe_id = st.session_state.get(_DETALHE_KEY)
    if detalhe_id:
        ativo = next((a for a in ativos if a["id"] == detalhe_id), None)
        if ativo:
            _render_detalhe(ativo, mock)
            return
        st.session_state.pop(_DETALHE_KEY, None)

    _render_lista(ativos, mock)


# ═══════════════════════════════════════════════════════════════════════════════
# TELA LISTA
# ═══════════════════════════════════════════════════════════════════════════════
def _render_lista(ativos: list, mock: bool) -> None:
    page_header(
        "⚙️ Meus Equipamentos",
        "Acompanhe o status dos equipamentos monitorados pela Pred.IO.",
    )

    if mock:
        st.caption(
            "Exibindo dados de demonstração. "
            "Os dados reais dos seus ativos aparecerão aqui automaticamente."
        )

    col_s, col_p, _ = st.columns([1.3, 1.3, 2.4])
    status_opts = ["Todos os status", "Bom", "Atenção", "Crítico", "Em acompanhamento"]
    plantas     = ["Todas as plantas"] + sorted(
        {a["Planta"] for a in ativos if a["Planta"] not in ("", "—")}
    )
    with col_s:
        sf = st.selectbox("Filtrar por status", status_opts, label_visibility="collapsed")
    with col_p:
        pf = st.selectbox("Filtrar por planta", plantas, label_visibility="collapsed")

    out = [
        a for a in ativos
        if (_norm(sf) in ("todos os status", _norm(a["Status"])))
        and (pf == "Todas as plantas" or a["Planta"] == pf)
    ]
    out = sorted(out, key=lambda x: x["Score"])

    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.85rem;margin:0.5rem 0 1rem;'>"
        f"{len(out)} ativo(s) principal(is) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    if not out:
        st.info("Nenhum ativo encontrado com os filtros selecionados.")
        return

    for a in out:
        _render_card(a)


def _render_card(a: dict) -> None:
    cfg   = _scfg(a["Status"])
    sc    = _score_color(a["Score"])
    score = a["Score"]

    modelo = a.get("modelo", "—")
    ns     = a.get("numero_serie", "—")
    mb     = a.get("mb", "—")

    meta_parts = []
    if modelo and modelo != "—": meta_parts.append(f"Modelo: {modelo}")
    if ns     and ns     != "—": meta_parts.append(f"NS: {ns}")
    if mb     and mb     != "—": meta_parts.append(mb)
    meta2 = "  ·  ".join(meta_parts)

    # Seção compacta de componentes
    componentes = a.get("componentes", [])
    comp_html = ""
    if componentes:
        comp_items = "  ·  ".join(
            f"{_scfg(c['Status'])['icon']} {c['nome']}"
            for c in componentes
        )
        comp_html = (
            f"<div style='border-top:1px solid #F1F5F9;margin-top:10px;padding-top:8px;'>"
            f"<p style='font-size:0.67rem;color:#94A3B8;font-weight:600;"
            f"text-transform:uppercase;letter-spacing:.07em;margin:0 0 3px;'>"
            f"⚙️ Componentes monitorados</p>"
            f"<p style='font-size:0.8rem;color:#475569;margin:0;'>{comp_items}</p>"
            f"</div>"
        )

    st.markdown(
        f"""<div style="background:{COLOR_CARD};border:1px solid {COLOR_BORDER};
            border-left:5px solid {cfg['color']};border-radius:14px;
            padding:1rem 1.4rem 1rem;margin-bottom:4px;
            box-shadow:0 2px 8px rgba(15,31,61,0.05);">
          <div style="display:flex;justify-content:space-between;
                      align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:4px;">
            <span style="font-size:1rem;font-weight:800;color:{COLOR_NAVY};">{a['nome']}</span>
            <span style="background:{cfg['bg']};color:{cfg['text']};
                         -webkit-text-fill-color:{cfg['text']};
                         border:1px solid {cfg['border']};
                         font-size:0.72rem;font-weight:700;letter-spacing:0.04em;
                         padding:3px 14px;border-radius:20px;white-space:nowrap;">
              {cfg['icon']} {a['Status']}
            </span>
          </div>
          <p style="color:{COLOR_MUTED};font-size:0.8rem;margin:0 0 3px;">{a['Tipo']}</p>
          <p style="color:{COLOR_MUTED};font-size:0.76rem;margin:0 0 8px;">{meta2}</p>
          <div style="display:flex;gap:16px;font-size:0.76rem;color:{COLOR_MUTED};
                      flex-wrap:wrap;margin-bottom:10px;">
            <span>🏭 {a['Planta']}</span>
            <span>📅 {a['Ultima_Atualizacao']}</span>
          </div>
          <div style="display:flex;justify-content:space-between;
                      align-items:center;margin-bottom:3px;">
            <span style="font-size:0.67rem;font-weight:700;color:{COLOR_MUTED};
                         text-transform:uppercase;letter-spacing:0.07em;">Score de Saúde</span>
            <span style="font-size:0.85rem;font-weight:800;color:{sc};">{score}/100</span>
          </div>
          <div style="background:#E2E8F0;border-radius:6px;height:7px;overflow:hidden;">
            <div style="height:100%;border-radius:6px;background:{sc};width:{score}%;"></div>
          </div>
          {comp_html}
        </div>""",
        unsafe_allow_html=True,
    )

    col_btn, _ = st.columns([1.2, 4])
    with col_btn:
        if st.button("Ver detalhes →", key=f"det_{a['id']}", use_container_width=True):
            st.session_state[_DETALHE_KEY] = a["id"]
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TELA DETALHE
# ═══════════════════════════════════════════════════════════════════════════════
def _render_detalhe(a: dict, mock: bool) -> None:
    if st.button("← Meus Equipamentos"):
        st.session_state.pop(_DETALHE_KEY, None)
        st.rerun()

    cfg   = _scfg(a["Status"])
    ccfg  = _ccfg(a.get("criticidade", "—"))
    sc    = _score_color(a["Score"])
    score = a["Score"]

    modelo  = a.get("modelo", "—")
    ns      = a.get("numero_serie", "—")
    mb      = a.get("mb", "—")
    inversor= a.get("inversor_frequencia", "—")
    crit    = a.get("criticidade", "—")

    meta_parts = filter(None, [
        a["Tipo"],
        f"Modelo: {modelo}" if modelo != "—" else "",
        f"NS: {ns}"         if ns     != "—" else "",
        mb                  if mb     != "—" else "",
    ])
    meta_line = "  ·  ".join(meta_parts)

    # ── Banner ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#08142B 0%,#1B2A6B 60%,#1E3A8A 100%);"
        f"border-radius:18px;padding:1.75rem 2rem 1.5rem;"
        f"box-shadow:0 12px 40px rgba(10,22,40,0.30);margin-bottom:1rem;'>"
        f"<p style='color:#38BDF8;font-size:0.68rem;font-weight:700;"
        f"letter-spacing:.14em;text-transform:uppercase;margin:0 0 0.4rem;'>"
        f"⚙️ EQUIPAMENTO MONITORADO</p>"
        f"<p style='color:#fff;font-size:1.55rem;font-weight:900;margin:0 0 0.3rem;"
        f"letter-spacing:-0.02em;line-height:1.2;'>{a['nome']}</p>"
        f"<p style='color:rgba(255,255,255,0.65);font-size:0.83rem;margin:0 0 0.6rem;'>{meta_line}</p>"
        f"<div style='display:flex;gap:16px;flex-wrap:wrap;font-size:0.78rem;"
        f"color:rgba(255,255,255,0.55);'>"
        f"<span>🏭 {a['Planta']}</span>"
        f"<span>📅 Atualizado em {a['Ultima_Atualizacao']}</span>"
        f"{'<span>⚡ Inversor: ' + inversor + '</span>' if inversor not in ('', '—') else ''}"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # ── Métricas rápidas ──────────────────────────────────────────────────────
    col_st, col_sc, col_cr = st.columns(3)
    with col_st:
        st.markdown(
            f"<div style='background:{cfg['bg']};border:1px solid {cfg['border']};"
            f"border-radius:12px;padding:1rem 1.2rem;'>"
            f"<p style='font-size:0.67rem;color:{COLOR_MUTED};margin:0 0 4px;"
            f"text-transform:uppercase;letter-spacing:.06em;'>Status</p>"
            f"<p style='font-size:1.05rem;font-weight:800;color:{cfg['text']};"
            f"-webkit-text-fill-color:{cfg['text']};margin:0;'>{cfg['icon']} {a['Status']}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_sc:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:12px;padding:1rem 1.2rem;'>"
            f"<p style='font-size:0.67rem;color:{COLOR_MUTED};margin:0 0 4px;"
            f"text-transform:uppercase;letter-spacing:.06em;'>Score de Saúde</p>"
            f"<p style='font-size:1.45rem;font-weight:900;color:{sc};margin:0;line-height:1;'>"
            f"{score}<span style='font-size:0.82rem;font-weight:500;color:{COLOR_MUTED};'>/100</span></p>"
            f"<div style='background:#E2E8F0;border-radius:4px;height:5px;margin-top:6px;overflow:hidden;'>"
            f"<div style='height:100%;border-radius:4px;background:{sc};width:{score}%;'></div></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_cr:
        st.markdown(
            f"<div style='background:{ccfg['bg']};border:1px solid {ccfg['border']};"
            f"border-radius:12px;padding:1rem 1.2rem;'>"
            f"<p style='font-size:0.67rem;color:{COLOR_MUTED};margin:0 0 4px;"
            f"text-transform:uppercase;letter-spacing:.06em;'>Criticidade</p>"
            f"<p style='font-size:1.05rem;font-weight:800;color:{ccfg['text']};"
            f"-webkit-text-fill-color:{ccfg['text']};margin:0;'>{crit}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Dados técnicos ────────────────────────────────────────────────────────
    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0 1rem;'/>",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(_lbl("Tipo", a["Tipo"]) + _lbl("Modelo", modelo), unsafe_allow_html=True)
    with c2:
        st.markdown(_lbl("Número de Série", ns) + _lbl("MB", mb), unsafe_allow_html=True)
    with c3:
        st.markdown(_lbl("Planta", a["Planta"]) + _lbl("Última Atualização", a["Ultima_Atualizacao"]), unsafe_allow_html=True)
    with c4:
        st.markdown(_lbl("Criticidade", crit) + _lbl("Inversor de Frequência", inversor), unsafe_allow_html=True)

    # ── Evolução do score principal ───────────────────────────────────────────
    historico = a.get("historico_score", [])
    if historico:
        st.markdown(_section("📈 Evolução do Score de Saúde"), unsafe_allow_html=True)
        _render_grafico(historico, sc)

        tendencia = a.get("leitura_tendencia", "")
        if tendencia:
            st.markdown(
                f"<div style='background:{COLOR_BG};border-left:4px solid {sc};"
                f"border-radius:0 8px 8px 0;padding:0.75rem 1rem;margin-top:0.5rem;'>"
                f"<p style='font-size:0.67rem;font-weight:700;color:{COLOR_MUTED};"
                f"text-transform:uppercase;letter-spacing:.06em;margin:0 0 4px;'>Leitura da tendência</p>"
                f"<p style='color:#475569;font-size:0.85rem;margin:0;line-height:1.6;'>{tendencia}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Componentes ───────────────────────────────────────────────────────────
    componentes = a.get("componentes", [])
    if componentes:
        st.markdown(_section("⚙️ Componentes da Unidade"), unsafe_allow_html=True)
        _render_componentes(componentes)

    # ── Análise de óleo ───────────────────────────────────────────────────────
    analise = a.get("analise_oleo") if a.get("analise_oleo_aplicavel") else None
    if analise:
        _render_analise_oleo(analise)

    # ── Linha do tempo ────────────────────────────────────────────────────────
    timeline = a.get("timeline", [])
    if timeline:
        st.markdown(_section("🕐 Linha do Tempo Técnica"), unsafe_allow_html=True)
        _render_timeline(timeline, cfg["color"])

    # ── Recomendação ──────────────────────────────────────────────────────────
    rec = a.get("recomendacao", "")
    if rec and rec.lower() not in ("", "nan", "—"):
        st.markdown(_section("💡 Recomendação Técnica"), unsafe_allow_html=True)
        st.markdown(
            f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
            f"border-left:5px solid #2563EB;border-radius:0 12px 12px 0;"
            f"padding:1rem 1.25rem;'>"
            f"<p style='color:#1E3A8A;font-size:0.88rem;margin:0;line-height:1.65;'>{rec}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO COMPONENTES
# ═══════════════════════════════════════════════════════════════════════════════
def _render_componentes(componentes: list) -> None:
    cols = st.columns(len(componentes))
    for col, comp in zip(cols, componentes):
        with col:
            cfg   = _scfg(comp["Status"])
            sc    = _score_color(comp["Score"])
            score = comp["Score"]
            inv   = comp.get("inversor_frequencia", "—")

            meta = "  ·  ".join(filter(None, [
                f"NS: {comp.get('numero_serie','')}" if comp.get("numero_serie","—") != "—" else "",
                comp.get("mb", ""),
            ]))

            st.markdown(
                f"<div style='background:{COLOR_BG};border:1px solid {cfg['border']};"
                f"border-left:4px solid {cfg['color']};border-radius:12px;"
                f"padding:0.9rem 1.1rem;margin-bottom:8px;'>"
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:4px;'>"
                f"<span style='font-weight:800;color:{COLOR_NAVY};font-size:0.92rem;'>{comp['nome']}</span>"
                f"<span style='background:{cfg['bg']};color:{cfg['text']};"
                f"-webkit-text-fill-color:{cfg['text']};border:1px solid {cfg['border']};"
                f"font-size:0.68rem;font-weight:700;padding:2px 10px;border-radius:20px;'>"
                f"{cfg['icon']} {comp['Status']}</span>"
                f"</div>"
                f"<p style='color:{COLOR_MUTED};font-size:0.77rem;margin:0 0 2px;'>{comp['tipo']}</p>"
                f"<p style='color:{COLOR_MUTED};font-size:0.74rem;margin:0 0 6px;'>"
                f"Modelo: {comp['modelo']}  ·  {meta}</p>"
                f"<p style='color:{COLOR_MUTED};font-size:0.74rem;margin:0 0 8px;'>"
                f"⚡ Inversor: {inv}  ·  📅 {comp['Ultima_Atualizacao']}</p>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:3px;'>"
                f"<span style='font-size:0.65rem;font-weight:700;color:{COLOR_MUTED};"
                f"text-transform:uppercase;letter-spacing:.06em;'>Score de Saúde</span>"
                f"<span style='font-size:0.82rem;font-weight:800;color:{sc};'>{score}/100</span>"
                f"</div>"
                f"<div style='background:#E2E8F0;border-radius:5px;height:6px;overflow:hidden;'>"
                f"<div style='height:100%;border-radius:5px;background:{sc};width:{score}%;'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

            if comp.get("historico_score"):
                _render_grafico(comp["historico_score"], sc, height=170)

            rec = comp.get("recomendacao", "")
            if rec:
                st.markdown(
                    f"<div style='background:{COLOR_BG};border-left:3px solid {cfg['color']};"
                    f"border-radius:0 8px 8px 0;padding:0.65rem 0.9rem;margin-top:6px;'>"
                    f"<p style='font-size:0.67rem;font-weight:700;color:{COLOR_MUTED};"
                    f"text-transform:uppercase;letter-spacing:.05em;margin:0 0 3px;'>Recomendação</p>"
                    f"<p style='color:#475569;font-size:0.82rem;margin:0;line-height:1.55;'>{rec}</p>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO ANÁLISE DE ÓLEO
# ═══════════════════════════════════════════════════════════════════════════════
def _render_analise_oleo(analise: dict) -> None:
    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0 1rem;'/>"
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0 0 4px;'>"
        f"🧪 {analise['titulo']}</p>"
        f"<p style='color:{COLOR_MUTED};font-size:0.82rem;margin:0 0 1rem;line-height:1.5;'>"
        f"{analise['subtitulo']}</p>",
        unsafe_allow_html=True,
    )

    # Grid de indicadores (2 colunas, 4 linhas)
    indicadores = analise.get("indicadores", [])
    col_i1, col_i2 = st.columns(2)
    for i, ind in enumerate(indicadores):
        col = col_i1 if i % 2 == 0 else col_i2
        with col:
            if ind["tipo"] == "codigo":
                st.markdown(
                    f"<div style='background:#F8FAFC;border:1px solid {COLOR_BORDER};"
                    f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:8px;'>"
                    f"<p style='font-size:0.66rem;color:{COLOR_MUTED};margin:0 0 3px;"
                    f"text-transform:uppercase;letter-spacing:.05em;'>{ind['nome']}</p>"
                    f"<span style='font-size:0.92rem;font-weight:700;color:{COLOR_NAVY};"
                    f"letter-spacing:0.05em;'>{ind['valor']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                cfg = _scfg(ind["valor"])
                st.markdown(
                    f"<div style='background:{cfg['bg']};border:1px solid {cfg['border']};"
                    f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:8px;'>"
                    f"<p style='font-size:0.66rem;color:{COLOR_MUTED};margin:0 0 3px;"
                    f"text-transform:uppercase;letter-spacing:.05em;'>{ind['nome']}</p>"
                    f"<span style='background:{cfg['bg']};color:{cfg['text']};"
                    f"-webkit-text-fill-color:{cfg['text']};border:1px solid {cfg['border']};"
                    f"font-size:0.72rem;font-weight:700;padding:2px 10px;border-radius:20px;'>"
                    f"{cfg['icon']} {ind['valor']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # Gráfico de tendência do óleo
    hist_oleo = analise.get("historico_score", [])
    if hist_oleo:
        st.markdown(
            f"<p style='font-size:0.82rem;font-weight:600;color:{COLOR_NAVY};"
            f"margin:0.75rem 0 0.5rem;'>Tendência da Condição do Óleo</p>",
            unsafe_allow_html=True,
        )
        _render_grafico(hist_oleo, "#F59E0B", height=190)

    # Leitura integrada
    leitura = analise.get("leitura", "")
    if leitura:
        st.markdown(
            f"<div style='background:#FFFBEB;border-left:4px solid #F59E0B;"
            f"border-radius:0 8px 8px 0;padding:0.75rem 1rem;margin-top:0.5rem;'>"
            f"<p style='font-size:0.67rem;font-weight:700;color:#92400E;"
            f"text-transform:uppercase;letter-spacing:.06em;margin:0 0 4px;'>"
            f"Leitura integrada</p>"
            f"<p style='color:#475569;font-size:0.85rem;margin:0;line-height:1.6;'>{leitura}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICO DE LINHA
# ═══════════════════════════════════════════════════════════════════════════════
def _render_grafico(historico: list, line_color: str, height: int = 220) -> None:
    meses  = [h["mes"]   for h in historico]
    scores = [h["score"] for h in historico]

    if _HAS_PLOTLY:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=meses, y=scores,
            mode="lines+markers+text",
            text=[str(s) for s in scores],
            textposition="top center",
            textfont=dict(size=11, color=line_color),
            line=dict(color=line_color, width=3),
            marker=dict(size=8, color=line_color,
                        line=dict(color="#fff", width=2)),
            fill="tozeroy",
            fillcolor=f"{line_color}18",
        ))
        fig.add_hline(y=85, line=dict(color="#10B981", width=1, dash="dot"),
                      annotation_text="85", annotation_position="right",
                      annotation_font=dict(size=9, color="#10B981"))
        fig.add_hline(y=60, line=dict(color="#F59E0B", width=1, dash="dot"),
                      annotation_text="60", annotation_position="right",
                      annotation_font=dict(size=9, color="#F59E0B"))
        fig.update_layout(
            height=height,
            margin=dict(t=20, b=10, l=0, r=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, tickfont=dict(size=10, color=COLOR_MUTED)),
            yaxis=dict(range=[0, 110], showgrid=True,
                       gridcolor="#F1F5F9", tickfont=dict(size=10, color=COLOR_MUTED)),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})
    else:
        max_s = max(scores) if scores else 100
        bars  = "".join(
            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:7px;'>"
            f"<span style='font-size:0.76rem;color:{COLOR_MUTED};width:72px;flex-shrink:0;'>{m}</span>"
            f"<div style='flex:1;background:#E2E8F0;border-radius:4px;height:9px;'>"
            f"<div style='width:{int(s/max_s*100)}%;height:100%;border-radius:4px;"
            f"background:{line_color};'></div></div>"
            f"<span style='font-size:0.76rem;font-weight:700;color:{line_color};width:32px;'>{s}</span>"
            f"</div>"
            for m, s in zip(meses, scores)
        )
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:12px;padding:1rem 1.25rem;'>{bars}</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LINHA DO TEMPO
# ═══════════════════════════════════════════════════════════════════════════════
def _render_timeline(timeline: list, dot_color: str) -> None:
    items_html = ""
    for i, ev in enumerate(timeline):
        is_last = (i == len(timeline) - 1)
        items_html += (
            f"<div style='display:flex;gap:12px;'>"
            f"<div style='display:flex;flex-direction:column;align-items:center;'>"
            f"<div style='width:10px;height:10px;border-radius:50%;flex-shrink:0;"
            f"background:{dot_color};margin-top:3px;'></div>"
            f"{'<div style=\"width:2px;flex:1;background:#E2E8F0;margin-top:4px;\"></div>' if not is_last else ''}"
            f"</div>"
            f"<div style='padding-bottom:{0 if is_last else 14}px;'>"
            f"<p style='font-size:0.72rem;color:{COLOR_MUTED};margin:0 0 1px;font-weight:600;'>{ev['data']}</p>"
            f"<p style='font-size:0.85rem;color:#334155;margin:0;'>{ev['texto']}</p>"
            f"</div></div>"
        )
    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:12px;padding:1rem 1.25rem;'>{items_html}</div>",
        unsafe_allow_html=True,
    )
