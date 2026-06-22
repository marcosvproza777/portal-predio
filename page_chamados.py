"""Chamados Técnicos — abertura e listagem com histórico de respostas."""
import streamlit as st
from auth import current_client_id, current_email, current_empresa
from sheets import (abrir_chamado, get_chamados,
                    get_mensagens_visiveis_cliente, add_mensagem)
from ui import (page_header, empty_state, COLOR_NAVY, COLOR_BLUE,
                COLOR_CARD, COLOR_BORDER, PRIORIDADES, PRIORIDADE_CFG, STATUS_CFG, badge)


def render() -> None:
    page_header("🔧 Chamados Técnicos", "Solicite suporte técnico da equipe Pred.IO")

    client_id = current_client_id()
    email     = current_email()

    tab_lista, tab_novo = st.tabs(["📋 Meus Chamados", "➕ Novo Chamado"])

    with tab_lista:
        _listar_chamados(client_id)

    with tab_novo:
        _form_novo_chamado(client_id, email)


def _form_novo_chamado(client_id: str, email: str) -> None:
    st.caption(
        "⚠️ Em caso de parada de máquina ou emergência, use **Prioridade Crítica** "
        "— resposta em até 1 hora."
    )

    with st.form("form_chamado", clear_on_submit=True):
        titulo = st.text_input("Título do chamado *",
                               placeholder="Ex: Vibração excessiva na bomba B-204")
        descricao = st.text_area("Descrição detalhada *",
                                 placeholder="Descreva o problema, sintomas observados e histórico recente…",
                                 height=130)
        c1, c2 = st.columns(2)
        with c1:
            planta = st.text_input("Planta", placeholder="Ex: Planta RJ")
        with c2:
            equipamento = st.text_input("Equipamento", placeholder="Ex: Bomba B-204")
        prioridade = st.selectbox("Prioridade", PRIORIDADES)

        submitted = st.form_submit_button("📨 Abrir Chamado", use_container_width=True)

    if submitted:
        if not titulo.strip() or not descricao.strip():
            st.warning("Preencha pelo menos o título e a descrição.")
            return
        ok = abrir_chamado(
            client_id=client_id,
            empresa=current_empresa(),
            email=email,
            titulo=titulo.strip(),
            descricao=descricao.strip(),
            planta=planta.strip(),
            equipamento=equipamento.strip(),
            prioridade=prioridade,
        )
        if ok:
            st.success("✅ Chamado aberto com sucesso! Nossa equipe entrará em contato em breve.")
        else:
            st.error("Erro ao abrir o chamado. Tente novamente ou entre em contato por e-mail.")


def _listar_chamados(client_id: str) -> None:
    df = get_chamados(client_id)
    if df.empty:
        empty_state("Nenhum chamado encontrado.")
        return

    st.markdown(
        f"<p style='color:#64748b;font-size:0.85rem;'>{len(df)} chamado(s) encontrado(s)</p>",
        unsafe_allow_html=True,
    )

    for _, row in df.iterrows():
        chamado_id = str(row.get("Id", "")).strip()
        titulo     = str(row.get("Titulo",       "")).strip() or "Sem título"
        descricao  = str(row.get("Descricao",    "")).strip()
        planta     = str(row.get("Planta",       "")).strip()
        equipamento= str(row.get("Equipamento",  "")).strip()
        prioridade = str(row.get("Prioridade",   "Baixa")).strip()
        status     = str(row.get("Status",       "Aberto")).strip()
        data_ab    = str(row.get("Data_Abertura","")).strip()

        st_color, st_text = STATUS_CFG.get(status.lower(), ("#94a3b8", "#fff"))
        pr_color, pr_text = PRIORIDADE_CFG.get(prioridade.lower(), ("#94a3b8", "#fff"))

        meta = []
        if data_ab:     meta.append(f"📅 {data_ab[:10]}")
        if planta:      meta.append(f"🏭 {planta}")
        if equipamento: meta.append(f"⚙️ {equipamento}")
        if chamado_id:  meta.append(f"#{chamado_id}")
        meta_html = "  ·  ".join(
            f"<span style='color:#64748b;font-size:0.78rem;'>{m}</span>" for m in meta
        )

        label = f"{'🔴' if prioridade.lower()=='crítica' else '🟡' if prioridade.lower()=='alta' else '🔵'} {titulo}"
        with st.expander(label, expanded=False):
            st.markdown(
                f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;'>"
                f"{badge(prioridade, pr_color, pr_text)} {badge(status, st_color, st_text)}"
                f"</div>"
                f"<div style='margin-bottom:8px;'>{meta_html}</div>"
                + (f"<p style='color:#475569;font-size:0.88rem;background:#f8fafc;"
                   f"border-radius:8px;padding:10px 14px;margin:0 0 10px;'>{descricao}</p>"
                   if descricao else ""),
                unsafe_allow_html=True,
            )

            # Thread de mensagens visíveis ao cliente
            if chamado_id:
                _render_thread_cliente(chamado_id, client_id, current_email())


def _render_thread_cliente(chamado_id: str, client_id: str, email: str) -> None:
    """Exibe histórico visível ao cliente e campo de resposta."""
    msgs = get_mensagens_visiveis_cliente(chamado_id)

    if not msgs.empty:
        st.markdown(
            "<p style='color:#64748b;font-size:0.78rem;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.06em;margin:8px 0 6px;'>"
            "Histórico do chamado</p>",
            unsafe_allow_html=True,
        )
        for _, m in msgs.iterrows():
            autor_tipo  = str(m.get("Autor_Tipo",  "cliente")).strip()
            autor       = str(m.get("Autor",       "")).strip()
            mensagem    = str(m.get("Mensagem",    "")).strip()
            tipo        = str(m.get("Tipo_Mensagem","")).strip()
            data        = str(m.get("Data",        "")).strip()[:16]

            if tipo in ("alteracao_status", "atribuicao_responsavel",
                        "encerramento", "reabertura"):
                st.markdown(
                    f"<div style='text-align:center;margin:6px 0;'>"
                    f"<span style='background:#F1F5F9;border:1px solid #E2E8F0;"
                    f"border-radius:20px;padding:3px 12px;font-size:0.75rem;color:#64748B;'>"
                    f"🔄 {mensagem} · {data}</span></div>",
                    unsafe_allow_html=True,
                )
            elif autor_tipo == "funcionario" or tipo == "resposta_predio":
                st.markdown(
                    f"<div style='display:flex;justify-content:flex-end;margin:6px 0;'>"
                    f"<div style='max-width:80%;background:#0F1F3D;"
                    f"border-radius:12px 12px 2px 12px;padding:10px 14px;'>"
                    f"<div style='font-size:0.72rem;color:#93C5FD;font-weight:600;"
                    f"margin-bottom:4px;'>⚙️ Equipe Pred.IO</div>"
                    f"<p style='color:#E2E8F0;font-size:0.88rem;margin:0;'>{mensagem}</p>"
                    f"<div style='font-size:0.7rem;color:#64748B;margin-top:4px;'>{data}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='display:flex;justify-content:flex-start;margin:6px 0;'>"
                    f"<div style='max-width:80%;background:#EFF6FF;"
                    f"border:1px solid #BFDBFE;border-radius:12px 12px 12px 2px;"
                    f"padding:10px 14px;'>"
                    f"<div style='font-size:0.72rem;color:#2563EB;font-weight:600;"
                    f"margin-bottom:4px;'>👤 Você</div>"
                    f"<p style='color:#1e293b;font-size:0.88rem;margin:0;'>{mensagem}</p>"
                    f"<div style='font-size:0.7rem;color:#94a3b8;margin-top:4px;'>{data}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

    # Formulário de resposta do cliente
    with st.form(f"reply_{chamado_id}", clear_on_submit=True):
        resposta = st.text_area(
            "Complementar ou responder",
            placeholder="Adicione informações, atualizações ou dúvidas…",
            height=80, label_visibility="collapsed",
        )
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            enviar = st.form_submit_button("📨 Enviar", use_container_width=True)
        with col_info:
            st.markdown(
                "<p style='color:#94a3b8;font-size:0.75rem;padding-top:8px;'>"
                "Sua mensagem ficará visível para a equipe Pred.IO</p>",
                unsafe_allow_html=True,
            )
    if enviar and resposta.strip():
        ok = add_mensagem(
            chamado_id=chamado_id,
            autor=email,
            autor_tipo="cliente",
            mensagem=resposta.strip(),
            visivel_cliente=True,
            tipo_mensagem="mensagem_cliente",
        )
        if ok:
            st.success("Mensagem enviada!")
            st.rerun()
        else:
            st.error("Erro ao enviar. Tente novamente.")
