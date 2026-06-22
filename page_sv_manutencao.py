"""Supervisão — Plano de Manutenção (gestão interna)."""
import streamlit as st
from auth import require_staff
from page_ativos import (
    _PLANO_MOCK_COMPRESSOR,
    _render_tarefa_card,
    _render_plano_manutencao,
    _pm_scfg,
    _pm_pcolor,
    _norm,
)
from ui import (
    sv_page_header,
    COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED, COLOR_BLUE,
)

# ── Mock de ativos com plano (para fase de demonstração) ──────────────────────
_MOCK_ATIVOS_PLANO = [
    {
        "id":     "AT-2026-001",
        "nome":   "Unidade Compressora Parafuso 200 VLD",
        "empresa": "Coca-Cola",
        "planta": "Sala de Compressores",
        "tag":    "CCP-001",
        "plano":  _PLANO_MOCK_COMPRESSOR,
    },
]


def render() -> None:
    require_staff()
    sv_page_header(
        "📅 Plano de Manutenção",
        "Gestão e acompanhamento das manutenções programadas dos ativos monitorados.",
    )

    # ── Resumo executivo ──────────────────────────────────────────────────────
    _render_resumo(_MOCK_ATIVOS_PLANO)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Plano por ativo ───────────────────────────────────────────────────────
    for ativo in _MOCK_ATIVOS_PLANO:
        _render_ativo_section(ativo)


# ─────────────────────────────────────────────────────────────────────────────
def _render_resumo(ativos: list) -> None:
    all_tarefas = [t for a in ativos for t in a.get("plano", [])]
    total     = len(all_tarefas)
    em_dia    = sum(1 for t in all_tarefas if _norm(t.get("status", "")) == "em dia")
    proximo   = sum(1 for t in all_tarefas if _norm(t.get("status", "")) == "proximo")
    vencido   = sum(1 for t in all_tarefas if _norm(t.get("status", "")) == "vencido")
    aguarda   = sum(1 for t in all_tarefas if _norm(t.get("status", "")) == "aguarda analise")

    c1, c2, c3, c4 = st.columns(4)
    for col, label, valor, cor in [
        (c1, "Total de Tarefas",   total,   COLOR_NAVY),
        (c2, "Em Dia",             em_dia,  "#10B981"),
        (c3, "Próximo Vencimento", proximo, "#F59E0B"),
        (c4, "Aguarda Análise",    aguarda, "#38BDF8"),
    ]:
        with col:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-top:3px solid {cor};border-radius:10px;padding:0.9rem 1rem;'>"
                f"<p style='font-size:0.68rem;color:{COLOR_MUTED};text-transform:uppercase;"
                f"letter-spacing:.06em;margin:0 0 4px;'>{label}</p>"
                f"<p style='font-size:1.6rem;font-weight:900;color:{cor};"
                f"-webkit-text-fill-color:{cor};margin:0;'>{valor}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _render_ativo_section(ativo: dict) -> None:
    nome    = ativo.get("nome", "Equipamento")
    empresa = ativo.get("empresa", "")
    planta  = ativo.get("planta", "")
    tag     = ativo.get("tag", "")
    plano   = ativo.get("plano", [])

    with st.expander(f"⚙️  {nome}  —  {empresa} / {planta}", expanded=True):
        meta = []
        if tag:     meta.append(f"🏷 {tag}")
        if empresa: meta.append(f"🏢 {empresa}")
        if planta:  meta.append(f"🏭 {planta}")
        if meta:
            st.markdown(
                f"<p style='font-size:0.78rem;color:{COLOR_MUTED};margin:0 0 0.75rem;'>"
                f"{'   ·   '.join(meta)}</p>",
                unsafe_allow_html=True,
            )

        # ── Tabs por tipo ─────────────────────────────────────────────────────
        calendario = [t for t in plano if t.get("tipo") == "calendario"]
        horimetro  = [t for t in plano if t.get("tipo") == "horimetro"]
        condicao   = [t for t in plano if t.get("tipo") == "condicao"]

        tab_labels = []
        if calendario: tab_labels.append(f"📆 Calendário ({len(calendario)})")
        if horimetro:  tab_labels.append(f"⏱ Horímetro ({len(horimetro)})")
        if condicao:   tab_labels.append(f"🔍 Condição ({len(condicao)})")
        tab_labels.append("📋 Todas")

        tabs = st.tabs(tab_labels)
        tab_idx = 0

        if calendario:
            with tabs[tab_idx]:
                _render_tabela_tarefas(calendario)
            tab_idx += 1

        if horimetro:
            with tabs[tab_idx]:
                _render_tabela_tarefas(horimetro)
            tab_idx += 1

        if condicao:
            with tabs[tab_idx]:
                _render_tabela_tarefas(condicao)
            tab_idx += 1

        with tabs[tab_idx]:
            _render_plano_manutencao(plano)


def _render_tabela_tarefas(tarefas: list) -> None:
    for t in tarefas:
        _render_sv_tarefa_card(t)


def _render_sv_tarefa_card(t: dict) -> None:
    """Card de tarefa com botões de ação (Concluir / Adiar) para supervisão."""
    scfg = _pm_scfg(t.get("status", ""))
    pcor = _pm_pcolor(t.get("prioridade", ""))
    tipo = t.get("tipo", "")
    nome = t.get("nome", "")
    tid  = t.get("id", nome)

    if tipo == "calendario":
        prox = t.get("proxima_data", "")
        per  = t.get("periodicidade_texto", "")
        trigger = f"📅 Próxima execução: **{prox}** · {per}"
    elif tipo == "horimetro":
        prox_h = t.get("proxima_horas", 0)
        per_h  = t.get("periodicidade_horas", 0)
        trigger = f"⏱ Vencimento em **{prox_h}h** · A cada {per_h:,}h".replace(",", ".")
    else:
        trigger = "🔍 Decisão condicionada à interpretação dos relatórios técnicos"

    col_info, col_acoes = st.columns([7, 2])
    with col_info:
        _render_tarefa_card(t)

    with col_acoes:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("✅ Concluir", key=f"sv_pm_concluir_{tid}",
                     use_container_width=True, type="primary"):
            st.toast(f"✅ '{nome}' marcada como concluída.", icon="✅")

        if tipo in ("calendario", "horimetro"):
            if st.button("⏩ Adiar", key=f"sv_pm_adiar_{tid}",
                         use_container_width=True):
                st.toast(f"⏩ '{nome}' adiada. Atualize a data/horas no painel.", icon="⏩")

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
