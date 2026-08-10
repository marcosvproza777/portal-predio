"""Botão + modal "Gerar Resumo Executivo" — componente reutilizável.

Usado no Portal do Cliente (dashboard, ativos, relatórios) e na
Supervisão Pred.IO (dashboard, clientes, ativos, relatórios).

Não cria sidebar — é um botão + st.dialog (modal nativo do Streamlit).
Não mexe em WhatsApp/e-mail. Não cria comando remoto.

SEGURANÇA:
- Portal do Cliente: client_id/cliente_nome vêm SEMPRE de
  current_client_id()/current_empresa() — o parâmetro recebido é ignorado
  para cliente comum, então não há como injetar client_id livre.
- Supervisão: o cliente é escolhido pelo staff dentro do modal (a página
  que chama este componente já está atrás de require_staff()/is_staff()).
- Modo "interno_predio" (observações internas incluídas) só é oferecido
  quando is_staff() é verdadeiro.
- Todo acesso é auditado via security.log_acesso.
"""
from __future__ import annotations

import datetime as _dt
import streamlit as st

from auth import current_client_id, current_empresa, current_email, is_staff
from ui import (COLOR_NAVY, COLOR_MUTED, COLOR_BORDER, COLOR_CARD, COLOR_BLUE,
                COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_URGENT,
                sv_metric_card)
import executive_summary as es

_COR_SAUDE = {"Bom": COLOR_SUCCESS, "Atenção": COLOR_WARNING, "Crítico": COLOR_DANGER, "Urgente": COLOR_URGENT}
_COR_GUT   = {"Baixa": COLOR_SUCCESS, "Moderada": COLOR_WARNING, "Alta": "#F97316", "Crítica": COLOR_DANGER}
_COR_MANUT = {"Em dia": COLOR_SUCCESS, "Próximas": COLOR_WARNING, "Vencidas": COLOR_DANGER,
             "Concluídas": COLOR_BLUE, "Por condição": "#8B5CF6"}
_COR_SEV   = {"Normal": COLOR_SUCCESS, "Atenção": COLOR_WARNING, "Crítico": COLOR_DANGER, "Urgente": COLOR_URGENT}

_PRESET_OPTIONS = [
    ("7d",           "Últimos 7 dias"),
    ("30d",          "Últimos 30 dias"),
    ("90d",          "Últimos 90 dias"),
    ("este_mes",     "Este mês"),
    ("mes_anterior", "Mês anterior"),
    ("custom",       "Personalizado"),
]


def _audit(acao: str, resultado: str, client_id: str, recurso_id: str = "",
          ativo_id: str = "", detalhe: str = "") -> None:
    try:
        from security import log_acesso
        det = detalhe
        if ativo_id:
            det = f"ativo_id={ativo_id}" + (f"; {detalhe}" if detalhe else "")
        log_acesso(
            acao=acao, recurso_tipo="resumo_executivo", recurso_id=recurso_id,
            resultado=resultado, client_id=client_id,
            rota=st.session_state.get("portal_page", st.session_state.get("sv_view", "")),
            detalhe=det,
        )
    except Exception:
        pass


def render_resumo_executivo_button(
    *,
    client_id: str = "",
    cliente_nome: str = "",
    ativo_id: str = "",
    ativo_nome: str = "",
    key_prefix: str = "resexec",
    mostrar_comparativo: bool = False,
) -> None:
    """Renderiza o botão "Gerar Resumo Executivo" (ou "Preparar Reunião" se
    mostrar_comparativo=True). Ao clicar, abre o modal.

    client_id/cliente_nome: no Portal do Cliente são ignorados e sempre
    substituídos por current_client_id()/current_empresa() — proteção
    contra client_id livre vindo de quem chama por engano. Na Supervisão
    servem apenas como valor pré-selecionado no seletor de cliente do modal.

    mostrar_comparativo: injeta o bloco "O que mudou" (reaproveita
    comparativo.py/comparativo_ui.py — não duplica o motor) ANTES do preview
    do resumo executivo já existente. Usado pelo botão "🗓️ Preparar Reunião".
    """
    staff = is_staff()
    if not staff:
        client_id    = current_client_id()
        cliente_nome = current_empresa()

    label = "🗓️ Preparar Reunião" if mostrar_comparativo else "📊 Gerar Resumo Executivo"
    if st.button(label, key=f"{key_prefix}_btn", use_container_width=False):
        if not client_id and not staff:
            st.error("🔒 Sessão inválida.")
            _audit("tentativa_acesso_negado_resumo", "negado", "", detalhe="client_id vazio na sessão")
            return
        _dialog_resumo(client_id, cliente_nome, ativo_id, ativo_nome, staff, key_prefix, mostrar_comparativo)


@st.dialog("📊 Gerar Resumo Executivo", width="large")
def _dialog_resumo(client_id: str, cliente_nome: str, ativo_id: str,
                   ativo_nome: str, staff: bool, key_prefix: str,
                   mostrar_comparativo: bool = False) -> None:
    if mostrar_comparativo:
        st.markdown(
            f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:1rem;margin:-0.5rem 0 0.5rem;'>"
            f"🗓️ Preparar Reunião</p>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<p style='color:{COLOR_MUTED};font-size:0.82rem;margin-top:-0.5rem;'>"
        "Consolida relatórios, manutenções, alertas, chamados e GUT do período "
        "selecionado — pronto para reunião com a gerência.</p>",
        unsafe_allow_html=True,
    )

    modo = "cliente"

    # ── Seleção de cliente — SOMENTE Supervisão ─────────────────────────────
    if staff:
        from sheets import get_all_clientes
        df_cli = get_all_clientes()
        if df_cli.empty or "Client_Id" not in df_cli.columns:
            st.warning("Nenhum cliente cadastrado.")
            return
        opcoes_cid = df_cli["Client_Id"].astype(str).str.strip().tolist()
        labels     = {
            row["Client_Id"]: str(row.get("Empresa", row["Client_Id"])).strip()
            for _, row in df_cli.iterrows()
        }
        idx_default = opcoes_cid.index(client_id) if client_id in opcoes_cid else 0
        sel_cid = st.selectbox(
            "Cliente *", options=opcoes_cid,
            format_func=lambda c: labels.get(c, c),
            index=idx_default, key=f"{key_prefix}_cliente",
        )
        client_id    = sel_cid
        cliente_nome = labels.get(sel_cid, sel_cid)

        tipo_visao = st.radio(
            "Visão do resumo", ["Resumo para cliente", "Resumo interno Pred.IO"],
            horizontal=True, key=f"{key_prefix}_visao",
            help="Resumo interno pode incluir observações internas — nunca é enviado ao cliente.",
        )
        modo = "admin_cliente" if tipo_visao == "Resumo para cliente" else "interno_predio"
    else:
        st.caption(f"Cliente: **{cliente_nome}**")

    # ── Ativo opcional ───────────────────────────────────────────────────────
    from sheets import get_all_ativos_sv
    try:
        df_at = get_all_ativos_sv()
        if not df_at.empty and "Client_Id" in df_at.columns:
            df_at = df_at[df_at["Client_Id"].astype(str).str.strip().str.lower() == client_id.strip().lower()]
        else:
            df_at = df_at.iloc[0:0]
    except Exception:
        df_at = None

    sel_ativo_id, sel_ativo_nome = ativo_id, ativo_nome
    if df_at is not None and not df_at.empty:
        id_col   = "Id" if "Id" in df_at.columns else df_at.columns[0]
        nome_col = "Tag" if "Tag" in df_at.columns else df_at.columns[0]
        opts     = ["(Todos os ativos)"] + df_at[id_col].astype(str).tolist()
        nomes    = dict(zip(df_at[id_col].astype(str), df_at[nome_col].astype(str)))
        idx_at   = opts.index(ativo_id) if ativo_id in opts else 0
        sel = st.selectbox(
            "Ativo (opcional)", options=opts,
            format_func=lambda o: "(Todos os ativos)" if o == "(Todos os ativos)" else nomes.get(o, o),
            index=idx_at, key=f"{key_prefix}_ativo",
        )
        if sel != "(Todos os ativos)":
            sel_ativo_id, sel_ativo_nome = sel, nomes.get(sel, sel)
        else:
            sel_ativo_id, sel_ativo_nome = "", ""
    elif ativo_id:
        st.caption(f"Ativo: **{ativo_nome or ativo_id}**")

    # ── Período ──────────────────────────────────────────────────────────────
    col_p1, col_p2 = st.columns([2, 1])
    with col_p1:
        preset_key = st.selectbox(
            "Período *", options=[p[0] for p in _PRESET_OPTIONS],
            format_func=lambda k: dict(_PRESET_OPTIONS)[k],
            index=1,  # "30d" — período padrão
            key=f"{key_prefix}_preset",
        )
    custom_ini = custom_fim = None
    if preset_key == "custom":
        col_ci, col_cf = st.columns(2)
        with col_ci:
            custom_ini = st.date_input("Data inicial", value=_dt.date.today() - _dt.timedelta(days=30),
                                       key=f"{key_prefix}_ini")
        with col_cf:
            custom_fim = st.date_input("Data final", value=_dt.date.today(), key=f"{key_prefix}_fim")

    # ── Tipo de resumo ───────────────────────────────────────────────────────
    tipo_resumo = st.selectbox("Tipo de resumo", options=es.TIPOS_RESUMO, key=f"{key_prefix}_tipo")

    # ── Tipo de relatório (categoria) — filtra quais relatórios entram ──────
    sel_categoria = st.selectbox(
        "Tipo de relatório", options=["Todos"] + es.CATEGORIAS_RELATORIO,
        key=f"{key_prefix}_categoria",
        help="Restringe o resumo a uma categoria de relatório (ex.: só Vibração).",
    )
    f_tipo_servico = "" if sel_categoria == "Todos" else sel_categoria

    # ── O que incluir ────────────────────────────────────────────────────────
    st.markdown("**Incluir no resumo**")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: inc_rel = st.checkbox("Relatórios", value=True, key=f"{key_prefix}_inc_rel")
    with c2: inc_man = st.checkbox("Manutenções", value=True, key=f"{key_prefix}_inc_man")
    with c3: inc_al  = st.checkbox("Alertas", value=True, key=f"{key_prefix}_inc_al")
    with c4: inc_ch  = st.checkbox("Chamados", value=True, key=f"{key_prefix}_inc_ch")
    with c5: inc_gut = st.checkbox("GUT", value=True, key=f"{key_prefix}_inc_gut")

    gerar = st.button("🔍 Gerar preview", type="primary", use_container_width=True, key=f"{key_prefix}_gerar")

    if gerar:
        ini, fim = es.resolver_periodo(preset_key, custom_ini, custom_fim)
        if fim < ini:
            st.error("A data final deve ser posterior à inicial.")
            return
        resultado = es.generate_executive_summary(
            usuario_id     = current_email(),
            cliente_id     = client_id,
            cliente_nome   = cliente_nome,
            ativo_id       = sel_ativo_id,
            ativo_nome     = sel_ativo_nome,
            periodo_inicio = ini,
            periodo_fim    = fim,
            tipo_resumo    = tipo_resumo,
            modo           = modo,
            incluir        = {"relatorios": inc_rel, "manutencoes": inc_man,
                              "alertas": inc_al, "chamados": inc_ch, "gut": inc_gut},
            salvar         = False,
            tipo_servico   = f_tipo_servico,
        )
        if not resultado.get("ok"):
            st.error(resultado.get("erro", "Erro ao gerar resumo."))
            _audit("tentativa_acesso_negado_resumo", "negado", client_id, ativo_id=sel_ativo_id,
                   detalhe=resultado.get("erro", ""))
            return
        st.session_state[f"{key_prefix}_resultado"] = resultado
        st.session_state.pop(f"{key_prefix}_summary_id", None)  # nova geração invalida o salvamento anterior
        _audit("resumo_executivo_gerado", "permitido", client_id, ativo_id=sel_ativo_id,
              detalhe=f"modo={modo}")

        if mostrar_comparativo:
            # Reaproveita o motor de comparativo (comparativo.py) — mesmo
            # período do resumo como "atual"; "anterior" vem da última
            # reunião registrada, se houver (senão comparativo.py já cai no
            # fallback manual de 30 dias antes). Não duplica lógica de coleta.
            import comparativo as _cmp
            periodos = _cmp.resolver_periodo_comparativo(
                client_id, usar_ultima_reuniao=True,
                periodo_atual_ini=ini, periodo_atual_fim=fim,
            )
            comp_resultado = _cmp.gerar_comparativo(
                client_id, periodos["atual"], periodos["anterior"],
                ativo_id=sel_ativo_id, modo=modo,
            )
            st.session_state[f"{key_prefix}_comparativo"] = comp_resultado

    resultado = st.session_state.get(f"{key_prefix}_resultado")
    if resultado:
        st.markdown(
            f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0;'/>",
            unsafe_allow_html=True,
        )

        if mostrar_comparativo:
            comp_resultado = st.session_state.get(f"{key_prefix}_comparativo")
            if comp_resultado and comp_resultado.get("ok"):
                st.markdown(
                    f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:0.95rem;margin:0 0 0.5rem;'>"
                    f"🔄 O que mudou</p>",
                    unsafe_allow_html=True,
                )
                from comparativo_ui import _render_resultado as _render_comparativo_resultado
                _render_comparativo_resultado(comp_resultado)
                st.markdown(
                    f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0;'/>",
                    unsafe_allow_html=True,
                )
            st.markdown(
                f"<p style='font-weight:800;color:{COLOR_NAVY};font-size:0.95rem;margin:0 0 0.5rem;'>"
                f"📋 Situação atual</p>",
                unsafe_allow_html=True,
            )

        _audit("resumo_executivo_visualizado", "permitido", client_id,
              recurso_id=resultado.get("summary_id", ""), ativo_id=resultado.get("ativo_id", ""))

        _render_preview_visual(resultado)
        _render_relatorios_usados(resultado)

        with st.expander("📄 Ver texto completo (para copiar)"):
            st.code(resultado["texto"], language=None)
            st.caption("Use o ícone de cópia no canto do bloco acima para copiar o texto do resumo.")

        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            try:
                docx_bytes = es.gerar_resumo_executivo_word(resultado)
                if st.download_button(
                    "⬇️ Exportar Word", data=docx_bytes,
                    file_name=_slug(resultado["titulo"]) + ".docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True, key=f"{key_prefix}_dl",
                ):
                    _audit("resumo_executivo_exportado", "permitido", client_id,
                          recurso_id=resultado.get("summary_id", ""), detalhe="formato=docx")
            except Exception as exc:
                st.error(f"Erro ao gerar Word: {exc}")
        with col_a2:
            ja_salvo = bool(st.session_state.get(f"{key_prefix}_summary_id"))
            if st.button("💾 Salvar resumo", use_container_width=True,
                        key=f"{key_prefix}_salvar", disabled=ja_salvo):
                from sheets import add_executive_summary
                summary_id = add_executive_summary(
                    cliente_id=client_id, titulo=resultado["titulo"], resumo_texto=resultado["texto"],
                    gerado_por_usuario_id=current_email(), ativo_id=resultado.get("ativo_id", ""),
                    tipo_resumo=resultado["tipo_resumo"], modo=resultado["modo"],
                    periodo_inicio=resultado["periodo_inicio"].strftime("%d/%m/%Y"),
                    periodo_fim=resultado["periodo_fim"].strftime("%d/%m/%Y"),
                )
                if summary_id:
                    st.session_state[f"{key_prefix}_summary_id"] = summary_id
                    st.success(f"Resumo salvo — ID: {summary_id}")
                else:
                    st.error("Erro ao salvar o resumo.")
        with col_a3:
            summary_id = st.session_state.get(f"{key_prefix}_summary_id")
            if summary_id and st.button("🗄️ Arquivar", use_container_width=True, key=f"{key_prefix}_arquivar"):
                from sheets import update_executive_summary
                if update_executive_summary(summary_id, client_id, Status="Arquivado"):
                    _audit("resumo_executivo_arquivado", "permitido", client_id, recurso_id=summary_id)
                    st.success("Resumo arquivado.")
                else:
                    st.error("Erro ao arquivar.")


def _render_relatorios_usados(resultado: dict) -> None:
    """"Relatórios utilizados: X" — auditoria de fonte do resumo. Mostra só
    os metadados dos relatórios (Título/Ativo/Tipo/Data/Severidade), nunca
    os chunks brutos indexados para a IA."""
    df_rel = resultado.get("dados", {}).get("relatorios")
    n = len(df_rel) if df_rel is not None else 0
    with st.expander(f"📎 Relatórios utilizados: {n}"):
        if not n:
            st.caption("Nenhum relatório publicado entrou neste resumo no período selecionado.")
            return
        for _, r in df_rel.iterrows():
            titulo = str(r.get("Titulo", "Relatório")).strip()
            tipo   = str(r.get("Tipo_Servico", "")).strip()
            data   = str(r.get("Data_Relatorio", "")).strip()
            sev    = str(r.get("Severidade", "")).strip()
            ativo  = str(r.get("Ativo_Id", "")).strip()
            st.markdown(
                f"<div style='padding:6px 0;border-bottom:1px solid {COLOR_BORDER};font-size:0.85rem;'>"
                f"<strong>{titulo}</strong><br/>"
                f"<span style='color:{COLOR_MUTED};'>{tipo} · {data} · {sev}"
                + (f" · Ativo: {ativo}" if ativo else "") + "</span></div>",
                unsafe_allow_html=True,
            )


def _render_preview_visual(resultado: dict) -> None:
    """Preview visual do resumo — cabeçalho, cards, gráficos, pontos para
    gerência, ações prioritárias e histórico resumido. Estilo dashboard
    executivo (Design System Pred.IO)."""
    ind          = resultado["indicadores"]
    charts       = resultado["charts"]
    cliente_nome = resultado.get("cliente_nome", "")
    ativo_nome   = resultado.get("ativo_nome", "")
    p_ini        = resultado["periodo_inicio"].strftime("%d/%m/%Y")
    p_fim        = resultado["periodo_fim"].strftime("%d/%m/%Y")
    gerado_em    = resultado.get("gerado_em")
    gerado_str   = gerado_em.strftime("%d/%m/%Y %H:%M") if gerado_em else ""

    # ── Cabeçalho ────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#08142B 0%,#1B2A6B 60%,#1E3A8A 100%);"
        f"border-radius:16px;padding:1.5rem 1.75rem;margin-bottom:1rem;color:#fff;'>"
        f"<p style='margin:0;font-size:0.7rem;font-weight:700;letter-spacing:0.18em;"
        f"text-transform:uppercase;color:#93C5FD;'>Pred.IO</p>"
        f"<p style='margin:2px 0 0.75rem;font-size:1.35rem;font-weight:800;'>"
        f"Resumo Executivo de Confiabilidade</p>"
        f"<div style='display:flex;flex-wrap:wrap;gap:1.75rem;font-size:0.82rem;'>"
        f"<div><span style='color:#93C5FD;'>Cliente</span><br/><strong>{cliente_nome}</strong></div>"
        f"<div><span style='color:#93C5FD;'>Período</span><br/><strong>{p_ini} a {p_fim}</strong></div>"
        + (f"<div><span style='color:#93C5FD;'>Ativo</span><br/><strong>{ativo_nome}</strong></div>"
           if ativo_nome else "")
        + f"<div><span style='color:#93C5FD;'>Gerado em</span><br/><strong>{gerado_str}</strong></div>"
        f"</div>"
        f"<p style='margin:0.9rem 0 0;font-size:0.8rem;color:#CBD5E1;line-height:1.5;max-width:640px;'>"
        f"Visão consolidada da condição dos ativos, prioridades de manutenção, relatórios técnicos, "
        f"alertas e ações recomendadas no período.</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Cards gerenciais ─────────────────────────────────────────────────────
    saude_cor = COLOR_SUCCESS if (ind["saude_media"] or 0) >= 70 else COLOR_WARNING
    cards = [
        ("⚙️", "Ativos Monitorados", ind["ativos_monitorados"], COLOR_NAVY),
        ("💚", "Saúde Média", f"{ind['saude_media']}/100" if ind["saude_media"] is not None else "—", saude_cor),
        ("🟡", "Ativos em Atenção", ind["ativos_atencao"], COLOR_WARNING),
        ("🔴", "Ativos Críticos", ind["ativos_criticos"],
         COLOR_DANGER if ind["ativos_criticos"] else COLOR_SUCCESS),
        ("📅", "Manutenções Vencidas", ind["manutencoes_vencidas"],
         COLOR_DANGER if ind["manutencoes_vencidas"] else COLOR_SUCCESS),
        ("🎯", "Itens GUT Críticos", ind["itens_gut_criticos"],
         COLOR_DANGER if ind["itens_gut_criticos"] else COLOR_SUCCESS),
        ("🔔", "Alertas Críticos", ind["alertas_criticos"],
         COLOR_DANGER if ind["alertas_criticos"] else COLOR_SUCCESS),
        ("🔧", "Chamados Abertos", ind["chamados_abertos"],
         COLOR_WARNING if ind["chamados_abertos"] else COLOR_SUCCESS),
        ("📁", "Relatórios no Período", ind["relatorios_publicados"], COLOR_BLUE),
    ]
    cols = st.columns(3)
    for i, (icon, title, value, color) in enumerate(cards):
        with cols[i % 3]:
            sv_metric_card(icon, title, value, color)
            st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # ── Gráficos gerenciais ──────────────────────────────────────────────────
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0.75rem 0 0.5rem;'>"
        f"📊 Indicadores gráficos</p>",
        unsafe_allow_html=True,
    )
    g1, g2 = st.columns(2)
    with g1:
        _chart_saude_ativos(charts.get("saude_ativos", {}))
    with g2:
        _chart_gut_prioridade(charts.get("gut_prioridade", {}))

    g3, g4 = st.columns(2)
    with g3:
        _chart_manutencoes_status(charts.get("manutencoes_status", {}))
    with g4:
        _chart_relatorios_severidade(charts.get("relatorios_severidade", {}))

    _chart_score_evolucao(charts.get("score_evolucao", []))
    _chart_top5_criticos(charts.get("top5_criticos", []))

    # ── Principais pontos para gerência ──────────────────────────────────────
    pontos = resultado.get("pontos_gerencia", [])
    st.markdown(
        f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:12px;"
        f"padding:1rem 1.25rem;margin-top:0.5rem;'>"
        f"<p style='font-weight:800;color:#1E40AF;font-size:0.92rem;margin:0 0 0.6rem;'>"
        f"🎯 Principais pontos para gerência</p>"
        + "".join(
            f"<div style='display:flex;gap:8px;padding:5px 0;'>"
            f"<span style='color:#2563EB;'>•</span>"
            f"<span style='font-size:0.85rem;color:#1E3A8A;line-height:1.5;'>{p}</span></div>"
            for p in pontos
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    # ── Ações prioritárias ────────────────────────────────────────────────────
    acoes = resultado.get("acoes_prioritarias", [])
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:1rem 0 0.5rem;'>"
        f"⚡ Ações prioritárias</p>",
        unsafe_allow_html=True,
    )
    if not acoes:
        st.info("Nenhuma ação prioritária identificada no período.")
    else:
        _render_acoes_table(acoes)

    # ── Histórico resumido do período ───────────────────────────────────────
    timeline = resultado.get("timeline", [])
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:1rem 0 0.5rem;'>"
        f"🕒 Histórico resumido do período</p>",
        unsafe_allow_html=True,
    )
    if not timeline:
        st.caption("Nenhum evento relevante registrado no período.")
    else:
        linhas = "".join(
            f"<div style='display:flex;gap:10px;padding:6px 0;border-bottom:1px solid {COLOR_BORDER};'>"
            f"<span style='font-size:0.72rem;color:{COLOR_MUTED};min-width:64px;flex-shrink:0;'>{data}</span>"
            f"<span style='font-size:0.82rem;color:{COLOR_NAVY};'>{tipo} — {titulo}</span>"
            f"</div>"
            for data, tipo, titulo in timeline
        )
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-radius:10px;padding:0.6rem 1rem;'>{linhas}</div>",
            unsafe_allow_html=True,
        )


# ── Gráficos individuais (plotly) ────────────────────────────────────────────

def _chart_title(texto: str) -> None:
    st.markdown(
        f"<p style='font-weight:600;color:{COLOR_NAVY};font-size:0.85rem;margin:0 0 0.3rem;'>{texto}</p>",
        unsafe_allow_html=True,
    )


def _chart_saude_ativos(dados: dict) -> None:
    _chart_title("Saúde dos ativos")
    if not dados:
        st.caption("Dados insuficientes para este gráfico.")
        return
    import plotly.graph_objects as go
    labels = list(dados.keys())
    values = list(dados.values())
    colors = [_COR_SAUDE.get(l, COLOR_MUTED) for l in labels]
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.55,
                           marker=dict(colors=colors), textinfo="label+value"))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=230, showlegend=False)
    st.plotly_chart(fig, use_container_width=True, key="chart_saude_ativos")


def _chart_gut_prioridade(dados: dict) -> None:
    _chart_title("GUT por prioridade")
    if not dados:
        st.caption("Nenhum item com GUT calculado no período.")
        return
    import plotly.graph_objects as go
    ordem  = ["Baixa", "Moderada", "Alta", "Crítica"]
    values = [dados.get(l, 0) for l in ordem]
    colors = [_COR_GUT[l] for l in ordem]
    fig = go.Figure(go.Bar(x=ordem, y=values, marker_color=colors, text=values, textposition="outside"))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=230,
                      yaxis=dict(visible=False), xaxis=dict(tickfont=dict(size=11)))
    st.plotly_chart(fig, use_container_width=True, key="chart_gut_prioridade")


def _chart_manutencoes_status(dados: dict) -> None:
    _chart_title("Manutenções por status")
    if not dados:
        st.caption("Nenhuma manutenção no período.")
        return
    import plotly.graph_objects as go
    ordem  = ["Em dia", "Próximas", "Vencidas", "Concluídas", "Por condição"]
    labels = [l for l in ordem if dados.get(l)]
    values = [dados[l] for l in labels]
    colors = [_COR_MANUT[l] for l in labels]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors, text=values, textposition="outside"))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=230,
                      yaxis=dict(visible=False), xaxis=dict(tickfont=dict(size=10)))
    st.plotly_chart(fig, use_container_width=True, key="chart_manutencoes_status")


def _chart_relatorios_severidade(dados: dict) -> None:
    _chart_title("Relatórios por severidade")
    if not dados:
        st.caption("Nenhum relatório no período.")
        return
    import plotly.graph_objects as go
    ordem  = ["Normal", "Atenção", "Crítico", "Urgente"]
    labels = [l for l in ordem if dados.get(l)]
    values = [dados[l] for l in labels]
    colors = [_COR_SEV[l] for l in labels]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors, text=values, textposition="outside"))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=230,
                      yaxis=dict(visible=False))
    st.plotly_chart(fig, use_container_width=True, key="chart_relatorios_severidade")


def _chart_score_evolucao(pontos: list) -> None:
    _chart_title("Evolução do score de saúde")
    if len(pontos) < 2:
        st.caption("Dados insuficientes para esta série no período (é necessário histórico de mais de uma data).")
        return
    import plotly.graph_objects as go
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode="lines+markers",
                               line=dict(color=COLOR_BLUE, width=3), marker=dict(size=7)))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=220, yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig, use_container_width=True, key="chart_score_evolucao")


def _chart_top5_criticos(itens: list) -> None:
    _chart_title("Top 5 ativos mais críticos")
    if not itens:
        st.caption("Nenhum ativo no período.")
        return
    linhas = ""
    for it in itens:
        score     = it.get("score")
        gut_score = it.get("gut_score")
        prio      = it.get("gut_prioridade", "—")
        cor       = _COR_GUT.get(prio, COLOR_MUTED)
        linhas += (
            f"<div style='display:flex;justify-content:space-between;align-items:center;gap:8px;"
            f"padding:6px 0;border-bottom:1px solid {COLOR_BORDER};flex-wrap:wrap;'>"
            f"<span style='font-size:0.83rem;color:{COLOR_NAVY};flex:1;min-width:120px;'>{it.get('ativo','')}</span>"
            f"<span style='font-size:0.75rem;color:{COLOR_MUTED};'>Score: {score if score is not None else '—'}</span>"
            f"<span style='background:{cor}22;color:{cor};border:1px solid {cor}55;border-radius:6px;"
            f"padding:2px 8px;font-size:0.72rem;font-weight:700;white-space:nowrap;'>"
            f"GUT {gut_score if gut_score is not None else '—'} · {prio}</span>"
            f"</div>"
        )
    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:10px;padding:0.6rem 1rem;'>{linhas}</div>",
        unsafe_allow_html=True,
    )


_RANK_LABEL = {1: "GUT Crítica", 2: "GUT Alta", 3: "Manutenção Vencida",
              4: "Alerta Crítico", 5: "Recomendação por Condição"}


def _render_acoes_table(acoes: list) -> None:
    linhas = ""
    for a in acoes:
        cor = _COR_GUT.get(a.get("prioridade", ""), COLOR_MUTED)
        prazo = str(a.get("prazo", ""))[:16]
        linhas += (
            f"<div style='display:flex;gap:10px;align-items:center;padding:7px 0;"
            f"border-bottom:1px solid {COLOR_BORDER};flex-wrap:wrap;'>"
            f"<span style='background:{cor};color:#fff;font-size:0.62rem;font-weight:700;"
            f"padding:2px 8px;border-radius:6px;white-space:nowrap;'>{_RANK_LABEL.get(a['rank'], '')}</span>"
            f"<span style='font-size:0.83rem;color:{COLOR_NAVY};font-weight:600;flex:1;min-width:140px;'>"
            f"{a.get('acao', '')}</span>"
            f"<span style='font-size:0.72rem;color:{COLOR_MUTED};min-width:80px;'>{a.get('ativo_id','') or '—'}</span>"
            f"<span style='font-size:0.72rem;color:{COLOR_MUTED};min-width:90px;'>{prazo}</span>"
            f"<span style='font-size:0.72rem;color:{COLOR_MUTED};min-width:70px;'>{a.get('status','') or '—'}</span>"
            f"</div>"
        )
    st.markdown(
        f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
        f"border-radius:10px;padding:0.6rem 1rem;'>{linhas}</div>",
        unsafe_allow_html=True,
    )


def _slug(titulo: str) -> str:
    import unicodedata, re
    s = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip()
    s = re.sub(r"[\s-]+", "_", s)
    return s[:60] or "resumo_executivo"
