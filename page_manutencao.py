"""Plano de Manutenção — portal do cliente."""
import streamlit as st
from auth import current_client_id
from page_ativos import (
    _load, _render_tarefa_card, _render_plano_manutencao,
    _pm_scfg,
)
from ui import (
    page_header,
    COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED,
)


def render() -> None:
    page_header(
        "📅 Plano de Manutenção",
        "Manutenções preventivas e preditivas programadas para seus ativos.",
    )

    client_id = current_client_id()
    ativos, using_mock = _load(client_id)

    if using_mock:
        st.caption(
            "Exibindo dados de demonstração. "
            "O plano real dos seus ativos aparecerá aqui automaticamente."
        )

    # ── Próximas Manutenções (top 4) ─────────────────────────────────────────
    _render_proximas(ativos)

    # ── Plano completo por ativo ──────────────────────────────────────────────
    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.5rem 0 1rem;'/>"
        f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:1rem;margin:0 0 1rem;'>"
        f"⚙️ Plano Completo por Ativo</p>",
        unsafe_allow_html=True,
    )

    for a in ativos:
        plano = a.get("plano_manutencao", [])
        if not plano:
            continue

        nome  = a.get("nome", a.get("Tag", "Equipamento"))
        planta = a.get("Planta", "")

        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:12px;padding:0.9rem 1.2rem 0.6rem;margin-bottom:0.75rem;'>"
            f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:1rem;margin:0 0 2px;'>"
            f"⚙️ {nome}</p>"
            + (f"<p style='color:{COLOR_MUTED};font-size:0.78rem;margin:0;'>🏭 {planta}</p>"
               if planta else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        _render_plano_manutencao(plano)
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
def _render_proximas(ativos: list) -> None:
    """Card com as 4 tarefas mais urgentes entre todos os ativos."""
    horimetro_tasks = [
        (a.get("nome", a.get("Tag", "Equipamento")), t)
        for a in ativos
        for t in a.get("plano_manutencao", [])
        if t.get("tipo") == "horimetro"
    ]
    horimetro_tasks.sort(key=lambda x: x[1].get("proxima_horas", 9999))

    calendario_tasks = [
        (a.get("nome", a.get("Tag", "Equipamento")), t)
        for a in ativos
        for t in a.get("plano_manutencao", [])
        if t.get("tipo") == "calendario"
    ]

    top4 = (horimetro_tasks[:2] + calendario_tasks[:2])[:4]
    if not top4:
        return

    st.markdown(
        f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:1rem;margin:0 0 0.75rem;'>"
        f"🔔 Próximas Manutenções</p>",
        unsafe_allow_html=True,
    )

    cols = st.columns(len(top4))
    for col, (ativo_nome, t) in zip(cols, top4):
        with col:
            scfg = _pm_scfg(t.get("status", ""))
            tipo = t.get("tipo", "")
            icons = {"calendario": "📆", "horimetro": "⏱", "condicao": "🔍"}
            icon = icons.get(tipo, "📋")

            if tipo == "calendario":
                detalhe_cor  = scfg["color"]
                detalhe_text = f"📅 {t.get('proxima_data', '')}"
            elif tipo == "horimetro":
                detalhe_cor  = scfg["color"]
                detalhe_text = f"⏱ Vencimento em {t.get('proxima_horas', 0)}h"
            else:
                detalhe_cor  = scfg["color"]
                detalhe_text = "🔍 Aguarda análise"

            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-top:3px solid {scfg['color']};border-radius:10px;"
                f"padding:0.85rem 1rem;height:100%;'>"
                f"<p style='font-size:0.7rem;color:{COLOR_MUTED};margin:0 0 3px;'>"
                f"{icon} {t.get('categoria', '')}</p>"
                f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
                f"margin:0 0 6px;line-height:1.3;'>{t.get('nome', '')}</p>"
                f"<p style='font-size:0.78rem;font-weight:600;color:{detalhe_cor};"
                f"-webkit-text-fill-color:{detalhe_cor};margin:0;'>{detalhe_text}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
