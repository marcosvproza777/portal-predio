"""Botão + modal "O que mudou desde a última reunião?" — componente
reutilizável, usado na Supervisão (cliente e dashboard) e no Portal do
Cliente (versão simplificada).

Não cria sidebar. Não mexe em WhatsApp/e-mail. Não cria comando remoto.
Reaproveita comparativo.py (motor) e os gráficos já existentes em
resumo_executivo_ui.py (mesmo estilo visual do resto do projeto).

SEGURANÇA: mesmo padrão de resumo_executivo_ui.py — client_id do Portal do
Cliente vem sempre da sessão; Supervisão escolhe o cliente antes de chamar
este componente.
"""
from __future__ import annotations

import datetime as _dt
import streamlit as st

from ui import (COLOR_NAVY, COLOR_MUTED, COLOR_BORDER, COLOR_SUCCESS,
                COLOR_WARNING, COLOR_DANGER, COLOR_BLUE)
import comparativo


def _bloco(titulo: str, icone: str, itens: list, cor_fundo: str, cor_borda: str, cor_texto: str) -> None:
    if not itens:
        return
    st.markdown(
        f"<div style='background:{cor_fundo};border:1px solid {cor_borda};border-radius:12px;"
        f"padding:0.9rem 1.1rem;margin-bottom:0.75rem;'>"
        f"<p style='font-weight:800;color:{cor_texto};font-size:0.88rem;margin:0 0 0.5rem;'>"
        f"{icone} {titulo}</p>"
        + "".join(
            f"<div style='display:flex;gap:8px;padding:3px 0;'>"
            f"<span style='color:{cor_texto};'>•</span>"
            f"<span style='font-size:0.83rem;color:{COLOR_NAVY};line-height:1.5;'>{item}</span></div>"
            for item in itens
        )
        + "</div>",
        unsafe_allow_html=True,
    )


def _chart_antes_depois(titulo: str, antes, depois, pior_se_maior: bool = True) -> None:
    if antes is None or depois is None:
        return
    import plotly.graph_objects as go
    st.markdown(
        f"<p style='font-weight:600;color:{COLOR_NAVY};font-size:0.85rem;margin:0 0 0.3rem;'>{titulo}</p>",
        unsafe_allow_html=True,
    )
    piorou = (depois > antes) if pior_se_maior else (depois < antes)
    cor_depois = COLOR_DANGER if piorou else (COLOR_SUCCESS if depois != antes else COLOR_BLUE)
    fig = go.Figure(go.Bar(
        x=["Antes", "Depois"], y=[antes, depois],
        marker_color=[COLOR_MUTED, cor_depois],
        text=[antes, depois], textposition="outside",
    ))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=200, showlegend=False,
                      yaxis=dict(visible=False))
    st.plotly_chart(fig, use_container_width=True, key=f"chart_antes_depois_{titulo}")


def _render_resultado(resultado: dict) -> None:
    p_ini_a, p_fim_a = resultado["periodo_atual"]
    p_ini_p, p_fim_p = resultado["periodo_anterior"]
    st.caption(
        f"Comparando **{p_ini_a.strftime('%d/%m/%Y')} a {p_fim_a.strftime('%d/%m/%Y')}** "
        f"com **{p_ini_p.strftime('%d/%m/%Y')} a {p_fim_p.strftime('%d/%m/%Y')}**."
    )
    if not resultado["tem_snapshot_anterior"]:
        st.info(
            "ℹ️ Ainda não há um snapshot de GUT/score de um comparativo ou reunião "
            "anterior — os gráficos \"antes×depois\" de GUT/saúde só aparecem a "
            "partir da próxima comparação. Por enquanto, \"novidades\" e "
            "\"pendências\" já refletem o período certo."
        )

    c1, c2 = st.columns(2)
    with c1:
        _bloco("Melhorou", "✅", resultado["melhorou"], "#F0FDF4", "#86EFAC", "#065F46")
        _bloco("Novidades", "🆕", resultado["novidades"], "#EFF6FF", "#BFDBFE", "#1E40AF")
    with c2:
        _bloco("Piorou", "⚠️", resultado["piorou"], "#FEF2F2", "#FCA5A5", "#991B1B")
        _bloco("Pendências", "📌", resultado["pendencias"], "#FFFBEB", "#FCD34D", "#92400E")

    if not any([resultado["melhorou"], resultado["piorou"], resultado["novidades"], resultado["pendencias"]]):
        st.caption("Nenhuma mudança relevante identificada no período.")

    pontos = resultado["pontos_gerencia"]
    if pontos:
        st.markdown(
            f"<div style='background:#0D1A38;border-radius:12px;padding:1rem 1.25rem;margin:0.5rem 0;'>"
            f"<p style='font-weight:800;color:#38BDF8;font-size:0.9rem;margin:0 0 0.6rem;'>"
            f"🎯 Principais mudanças desde a última reunião</p>"
            + "".join(
                f"<div style='display:flex;gap:8px;padding:4px 0;'>"
                f"<span style='color:#38BDF8;'>{i+1}.</span>"
                f"<span style='font-size:0.85rem;color:#E2E8F0;line-height:1.5;'>{p}</span></div>"
                for i, p in enumerate(pontos)
            )
            + "</div>",
            unsafe_allow_html=True,
        )

    charts = resultado["charts"]
    if charts:
        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.92rem;margin:0.75rem 0 0.5rem;'>"
            f"📊 Gráficos</p>",
            unsafe_allow_html=True,
        )
        gcols = st.columns(2)
        idx = 0
        if "saude_antes_depois" in charts:
            with gcols[idx % 2]:
                d = charts["saude_antes_depois"]
                _chart_antes_depois("Saúde média — antes × depois", d["antes"], d["depois"], pior_se_maior=False)
            idx += 1
        if "gut_critico_antes_depois" in charts:
            with gcols[idx % 2]:
                d = charts["gut_critico_antes_depois"]
                _chart_antes_depois("GUT Alta/Crítica — antes × depois", d["antes"], d["depois"])
            idx += 1
        if "ativos_por_status" in charts:
            with gcols[idx % 2]:
                from resumo_executivo_ui import _chart_saude_ativos
                _chart_saude_ativos(charts["ativos_por_status"])
            idx += 1
        if "relatorios_por_severidade" in charts:
            with gcols[idx % 2]:
                from resumo_executivo_ui import _chart_relatorios_severidade
                _chart_relatorios_severidade(charts["relatorios_por_severidade"])
            idx += 1


@st.dialog("🔄 O que mudou desde a última reunião?", width="large")
def _dialog_comparativo(client_id: str, cliente_nome: str, ativo_id: str,
                        modo: str, key_prefix: str, staff: bool) -> None:
    # ── Seleção de cliente — SOMENTE Supervisão, e só quando não veio
    # pré-selecionado (ex.: chamado direto de page_sv_clientes.py já com o
    # cliente da tela) — mesmo padrão de resumo_executivo_ui.py::_dialog_resumo. ──
    if staff and not client_id:
        from sheets import get_all_clientes
        df_cli = get_all_clientes()
        if df_cli.empty or "Client_Id" not in df_cli.columns:
            st.warning("Nenhum cliente cadastrado.")
            return
        opcoes_cid = df_cli["Client_Id"].astype(str).str.strip().tolist()
        labels = {row["Client_Id"]: str(row.get("Empresa", row["Client_Id"])).strip()
                  for _, row in df_cli.iterrows()}
        sel_cid = st.selectbox(
            "Cliente *", options=opcoes_cid, format_func=lambda c: labels.get(c, c),
            key=f"{key_prefix}_cliente",
        )
        client_id, cliente_nome = sel_cid, labels.get(sel_cid, sel_cid)
    elif staff:
        st.caption(f"Cliente: **{cliente_nome or client_id}**")

    if staff:
        # Mesma escolha de visão de resumo_executivo_ui.py::_dialog_resumo —
        # visão interna pode citar obs. internas; nunca é o que o cliente vê.
        tipo_visao = st.radio(
            "Visão", ["Resumo para cliente", "Resumo interno Pred.IO"],
            horizontal=True, key=f"{key_prefix}_visao",
            help="Visão interna pode incluir observações internas — nunca é enviada ao cliente.",
        )
        modo = "admin_cliente" if tipo_visao == "Resumo para cliente" else "interno_predio"

    ultima = None
    try:
        import sheets
        ultima = sheets.get_last_meeting(client_id)
    except Exception:
        pass

    usar_reuniao = True
    if ultima:
        st.caption(
            f"Última reunião registrada: **{ultima['titulo']}** em {ultima['data_reuniao']} "
            f"(período analisado: {ultima['periodo_inicio']} a {ultima['periodo_fim']})."
        )
        usar_reuniao = st.checkbox("Comparar com a última reunião registrada", value=True, key=f"{key_prefix}_usar_reuniao")
    else:
        st.caption("Nenhuma reunião registrada para este cliente — escolha os períodos manualmente.")
        usar_reuniao = False

    periodo_atual_ini = periodo_atual_fim = periodo_anterior_ini = periodo_anterior_fim = None
    if not usar_reuniao:
        st.markdown("**Período atual**")
        ca1, ca2 = st.columns(2)
        with ca1:
            periodo_atual_ini = st.date_input("De", value=_dt.date.today() - _dt.timedelta(days=30), key=f"{key_prefix}_pa_ini")
        with ca2:
            periodo_atual_fim = st.date_input("Até", value=_dt.date.today(), key=f"{key_prefix}_pa_fim")
        st.markdown("**Período anterior**")
        cp1, cp2 = st.columns(2)
        with cp1:
            periodo_anterior_ini = st.date_input("De", value=_dt.date.today() - _dt.timedelta(days=60), key=f"{key_prefix}_pp_ini")
        with cp2:
            periodo_anterior_fim = st.date_input("Até", value=_dt.date.today() - _dt.timedelta(days=31), key=f"{key_prefix}_pp_fim")

    if st.button("🔍 Comparar", type="primary", use_container_width=True, key=f"{key_prefix}_comparar"):
        periodos = comparativo.resolver_periodo_comparativo(
            client_id, usar_ultima_reuniao=usar_reuniao,
            periodo_atual_ini=periodo_atual_ini, periodo_atual_fim=periodo_atual_fim,
            periodo_anterior_ini=periodo_anterior_ini, periodo_anterior_fim=periodo_anterior_fim,
        )
        resultado = comparativo.gerar_comparativo(
            client_id, periodos["atual"], periodos["anterior"], ativo_id=ativo_id, modo=modo,
        )
        st.session_state[f"{key_prefix}_resultado"] = resultado

    resultado = st.session_state.get(f"{key_prefix}_resultado")
    if resultado:
        st.markdown(f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0;'/>", unsafe_allow_html=True)
        if not resultado.get("ok"):
            st.error(resultado.get("erro", "Erro ao gerar comparativo."))
        else:
            _render_resultado(resultado)


def render_comparativo_button(
    *, client_id: str = "", cliente_nome: str = "", ativo_id: str = "",
    modo: str = "cliente", key_prefix: str = "cmp", label: str = "🔄 O que mudou desde a última reunião?",
) -> None:
    """Botão que abre o modal do comparativo.

    client_id/cliente_nome: no Portal do Cliente são ignorados e sempre
    substituídos por current_client_id()/current_empresa() — mesma proteção
    de render_resumo_executivo_button contra client_id livre vindo de quem
    chama por engano. Na Supervisão servem como valor pré-selecionado.
    modo="interno_predio" só deve ser passado por telas já atrás de
    require_staff().
    """
    from auth import is_staff, current_client_id, current_empresa
    staff = is_staff()
    if not staff:
        client_id    = current_client_id()
        cliente_nome = current_empresa()
        modo = "cliente"

    if st.button(label, use_container_width=True, key=f"{key_prefix}_btn"):
        if not client_id and not staff:
            st.error("🔒 Sessão inválida.")
            return
        _dialog_comparativo(client_id, cliente_nome, ativo_id, modo, key_prefix, staff)
