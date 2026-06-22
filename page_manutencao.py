"""Plano de Manutenção — portal do cliente."""
import streamlit as st
from auth import current_client_id
from page_ativos import (
    _load, _pm_calc_status, _pm_scfg, _pm_pcolor,
    _render_tarefa_card, _render_plano_manutencao,
    _norm, _HORIMETRO_ATUAL_MOCK,
)
from ui import (
    page_header,
    COLOR_NAVY, COLOR_CARD, COLOR_BORDER, COLOR_MUTED,
)


def render() -> None:
    page_header(
        "📅 Plano de Manutenção",
        "Acompanhe as próximas ações preventivas e preditivas dos ativos monitorados.",
    )

    client_id = current_client_id()
    ativos, using_mock = _load(client_id)

    if using_mock:
        st.caption(
            "Exibindo plano de demonstração. "
            "O plano real dos seus ativos aparecerá aqui conforme os dados forem registrados."
        )

    # Coleta todas as tarefas com vínculo ao ativo
    tarefas_enriched = _enrich_tarefas(ativos)

    # ── Alertas de vencimento / próximas ────────────────────────────────────
    _render_alertas(tarefas_enriched)

    # ── Cards de próximas manutenções ────────────────────────────────────────
    _render_proximas_cards(tarefas_enriched)

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0 1rem;'/>",
        unsafe_allow_html=True,
    )

    # ── Plano completo ────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
def _enrich_tarefas(ativos: list) -> list:
    """Retorna lista de (ativo_nome, planta, horimetro_atual, tarefa, status) ordenada por urgência."""
    resultado = []
    for a in ativos:
        nome   = a.get("nome", a.get("Tag", "Equipamento"))
        planta = a.get("Planta", "")
        h      = a.get("horimetro_atual", _HORIMETRO_ATUAL_MOCK)
        for t in a.get("plano_manutencao", []):
            s = _pm_calc_status(t)
            resultado.append({
                "ativo_nome": nome,
                "planta":     planta,
                "horimetro_atual": h,
                "tarefa":     t,
                "status":     s,
                "status_key": _norm(s),
            })
    return resultado


def _render_alertas(tarefas_enriched: list) -> None:
    """Banner de alertas para tarefas vencidas ou próximas do vencimento."""
    urgentes = [
        e for e in tarefas_enriched
        if e["status_key"] in ("vencido", "proximo do vencimento")
        and e["tarefa"].get("tipo") != "condicao"
    ]
    if not urgentes:
        return

    msgs = []
    for e in urgentes[:4]:
        t  = e["tarefa"]
        st_key = e["status_key"]
        tipo   = t.get("tipo", "")
        nome   = t.get("nome", "")
        if tipo == "horimetro":
            h_atual = t.get("horimetro_atual", 0)
            v_horas = t.get("vencimento_horas", 0)
            restam  = max(0, v_horas - h_atual)
            if st_key == "vencido":
                msgs.append(f"🔴 <b>{nome}</b> — vencida há {abs(v_horas - h_atual):,}h.".replace(",", "."))
            else:
                msgs.append(f"🟡 <b>{nome}</b> — próxima do vencimento em <b>{restam:,}h</b>.".replace(",", "."))
        elif tipo == "calendario":
            prox = t.get("proxima_data", "")
            if st_key == "vencido":
                msgs.append(f"🔴 <b>{nome}</b> — data de execução ultrapassada ({prox}).")
            else:
                msgs.append(f"🟡 <b>{nome}</b> — prevista para <b>{prox}</b>.")

    if msgs:
        cor_bg = "#FFFBEB" if not any("🔴" in m for m in msgs) else "#FEF2F2"
        cor_b  = "#FCD34D" if not any("🔴" in m for m in msgs) else "#FCA5A5"
        cor_t  = "#92400E" if not any("🔴" in m for m in msgs) else "#991B1B"
        items  = "".join(f"<li style='margin-bottom:4px;'>{m}</li>" for m in msgs)
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


def _render_proximas_cards(tarefas_enriched: list) -> None:
    """Cartões de próximas manutenções (top 3, excluindo condição)."""
    preventivas = [
        e for e in tarefas_enriched
        if e["tarefa"].get("tipo") != "condicao"
    ]

    def _urgency_key(e):
        t = e["tarefa"]
        tipo = t.get("tipo", "")
        sk = e["status_key"]
        # Vencidas primeiro, depois próximas, depois em dia
        order = {"vencido": 0, "proximo do vencimento": 1, "em dia": 2}.get(sk, 3)
        if tipo == "horimetro":
            restam = t.get("vencimento_horas", 9999) - t.get("horimetro_atual", 0)
            return (order, restam)
        if tipo == "calendario":
            from datetime import datetime
            prox = t.get("proxima_data", "")
            try:
                diff = (datetime.strptime(prox, "%d/%m/%Y") - datetime.now()).days
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
            h_atual = t.get("horimetro_atual", 0)
            v_horas = t.get("vencimento_horas", 0)
            restam  = max(0, v_horas - h_atual)
            detalhe = f"em {restam:,}h (vence {v_horas:,}h)".replace(",", ".")
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
