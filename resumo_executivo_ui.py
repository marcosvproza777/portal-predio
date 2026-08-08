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
from ui import COLOR_NAVY, COLOR_MUTED, COLOR_BORDER
import executive_summary as es

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
) -> None:
    """Renderiza o botão "Gerar Resumo Executivo". Ao clicar, abre o modal.

    client_id/cliente_nome: no Portal do Cliente são ignorados e sempre
    substituídos por current_client_id()/current_empresa() — proteção
    contra client_id livre vindo de quem chama por engano. Na Supervisão
    servem apenas como valor pré-selecionado no seletor de cliente do modal.
    """
    staff = is_staff()
    if not staff:
        client_id    = current_client_id()
        cliente_nome = current_empresa()

    if st.button("📊 Gerar Resumo Executivo", key=f"{key_prefix}_btn", use_container_width=False):
        if not client_id and not staff:
            st.error("🔒 Sessão inválida.")
            _audit("tentativa_acesso_negado_resumo", "negado", "", detalhe="client_id vazio na sessão")
            return
        _dialog_resumo(client_id, cliente_nome, ativo_id, ativo_nome, staff, key_prefix)


@st.dialog("📊 Gerar Resumo Executivo", width="large")
def _dialog_resumo(client_id: str, cliente_nome: str, ativo_id: str,
                   ativo_nome: str, staff: bool, key_prefix: str) -> None:
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

    resultado = st.session_state.get(f"{key_prefix}_resultado")
    if resultado:
        st.markdown(
            f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0;'/>"
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;'>📋 Preview</p>",
            unsafe_allow_html=True,
        )
        _audit("resumo_executivo_visualizado", "permitido", client_id,
              recurso_id=resultado.get("summary_id", ""), ativo_id=resultado.get("ativo_id", ""))
        st.code(resultado["texto"], language=None)

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

        st.caption("Use o ícone de cópia no canto do bloco acima para copiar o texto do resumo.")


def _slug(titulo: str) -> str:
    import unicodedata, re
    s = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip()
    s = re.sub(r"[\s-]+", "_", s)
    return s[:60] or "resumo_executivo"
