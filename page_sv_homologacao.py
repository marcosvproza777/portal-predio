"""Supervisor — Homologação Pred.IO (page_sv_homologacao)."""
import streamlit as st
from auth import require_staff
from ui import page_header


# ─── CONSTANTES ──────────────────────────────────────────────────────────────

_STATUS_OPTS   = ["Pendente", "Aprovado", "Reprovado", "Corrigir"]
_STATUS_COLORS = {
    "Pendente":  "#6B7280",
    "Aprovado":  "#10B981",
    "Reprovado": "#EF4444",
    "Corrigir":  "#F59E0B",
}
_CHECKLIST_TAB = "HomologacaoChecklist"
_CHECKLIST_HDR = [
    "Item_Num", "Titulo", "Status", "Observacao", "Updated_At",
]


# ─── SHEET HELPERS ───────────────────────────────────────────────────────────

def _load_checklist() -> dict[int, dict]:
    """Carrega status atual do checklist do Google Sheets."""
    from sheets import load_sheet
    df = load_sheet(_CHECKLIST_TAB)
    result: dict[int, dict] = {}
    if df.empty or "Item_Num" not in df.columns:
        return result
    for _, row in df.iterrows():
        try:
            num = int(str(row.get("Item_Num", "")).strip())
            result[num] = {
                "Status":     str(row.get("Status", "Pendente")).strip(),
                "Observacao": str(row.get("Observacao", "")).strip(),
            }
        except (ValueError, TypeError):
            pass
    return result


def _save_item(num: int, titulo: str, status: str, obs: str) -> bool:
    """Upsert de item do checklist."""
    from sheets import load_sheet, append_row, get_spreadsheet
    from datetime import datetime
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Tenta atualizar linha existente
    try:
        ss  = get_spreadsheet()
        ws  = ss.worksheet(_CHECKLIST_TAB)
        headers = ws.row_values(1)
        if "Item_Num" in headers:
            col_idx = headers.index("Item_Num") + 1
            vals    = ws.col_values(col_idx)
            for row_idx, v in enumerate(vals, start=1):
                if row_idx == 1:
                    continue
                if str(v).strip() == str(num):
                    # Atualiza linha existente
                    for campo, valor in [
                        ("Status", status), ("Observacao", obs), ("Updated_At", now)
                    ]:
                        if campo in headers:
                            ws.update_cell(row_idx, headers.index(campo) + 1, valor)
                    from sheets import load_sheet as _lsh
                    _lsh.clear()
                    return True
    except Exception:
        pass

    # Cria nova linha
    from sheets import _ensure_tab_headers  # type: ignore
    _ensure_tab_headers(_CHECKLIST_TAB, _CHECKLIST_HDR)
    return append_row(_CHECKLIST_TAB, [num, titulo, status, obs, now])


# ─── RENDER PRINCIPAL ────────────────────────────────────────────────────────

def render() -> None:
    require_staff()
    page_header("🔬 Homologação", "Validação completa do Portal Pred.IO antes de ir a produção")

    tab_setup, tab_checklist, tab_perguntas, tab_dados = st.tabs([
        "⚙️ Setup de Dados", "✅ Checklist", "🤖 Perguntas Assistente", "📋 Dados de Teste"
    ])

    with tab_setup:
        _render_tab_setup()

    with tab_checklist:
        _render_tab_checklist()

    with tab_perguntas:
        _render_tab_perguntas()

    with tab_dados:
        _render_tab_dados()


# ─── ABA SETUP ───────────────────────────────────────────────────────────────

def _render_tab_setup() -> None:
    st.markdown("### Configuração do Ambiente de Teste")
    st.info(
        "Este script cria — de forma **idempotente** — todos os dados necessários "
        "para a homologação: clientes, ativos, relatórios, manutenção, alertas, "
        "chamados e notificações.\n\n"
        "Pode ser executado múltiplas vezes sem duplicar dados."
    )

    col_btn, col_info = st.columns([2, 5])
    with col_btn:
        run = st.button("▶ Executar Setup", type="primary", use_container_width=True)
    with col_info:
        st.caption(
            "⏱ Aguarde ~30 segundos. Cada linha abaixo indica o resultado de cada passo."
        )

    if run:
        with st.spinner("Executando setup de homologação..."):
            import homologacao_setup
            msgs = homologacao_setup.run_setup()

        total    = len([m for m in msgs if m[0] in ("✚", "✓", "✗")])
        criados  = len([m for m in msgs if m[0] == "✚"])
        existiam = len([m for m in msgs if m[0] == "✓"])
        erros    = len([m for m in msgs if m[0] == "✗"])

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Itens criados",  criados)
        col_b.metric("Já existiam",    existiam)
        col_c.metric("Erros",          erros,  delta_color="inverse" if erros else "off")

        st.markdown("#### Log de execução")
        log_lines = []
        for status, msg in msgs:
            if status == "✚":
                log_lines.append(f"🟢 **{msg}**")
            elif status == "✓":
                log_lines.append(f"⬜ {msg}")
            elif status == "✗":
                log_lines.append(f"🔴 **{msg}**")
            else:
                log_lines.append(f"ℹ️ *{msg}*")
        st.markdown("\n\n".join(log_lines))

    # Botão de limpeza (cuidado)
    with st.expander("🗑️ Remover dados de teste (avançado)"):
        st.warning(
            "**Atenção:** Esta ação remove os usuários de teste. Os outros dados "
            "(ativos, relatórios, etc.) devem ser removidos manualmente na planilha."
        )
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🗑️ Remover usuários de teste", type="secondary"):
                import homologacao_setup
                from sheets import delete_usuario
                emails = [
                    homologacao_setup.EMAIL_A,
                    homologacao_setup.EMAIL_B,
                    homologacao_setup.EMAIL_STAFF,
                ]
                for email in emails:
                    ok = delete_usuario(email)
                    if ok:
                        st.success(f"Removido: {email}")
                    else:
                        st.info(f"Não encontrado: {email}")


# ─── ABA CHECKLIST ───────────────────────────────────────────────────────────

def _render_tab_checklist() -> None:
    import homologacao_setup
    st.markdown("### Checklist de Homologação — 20 Itens")

    # Carregar status atual
    if "hom_checklist" not in st.session_state:
        st.session_state["hom_checklist"] = _load_checklist()

    checklist = st.session_state["hom_checklist"]

    # Botão para recarregar do sheets
    col_reload, col_resume = st.columns([2, 5])
    with col_reload:
        if st.button("🔄 Recarregar do banco", key="hom_reload"):
            st.session_state["hom_checklist"] = _load_checklist()
            checklist = st.session_state["hom_checklist"]
            st.rerun()

    # Progresso geral
    total    = len(homologacao_setup.CHECKLIST_ITEMS)
    aprovados = len([v for v in checklist.values() if v.get("Status") == "Aprovado"])
    reprovados= len([v for v in checklist.values() if v.get("Status") == "Reprovado"])
    corrigir  = len([v for v in checklist.values() if v.get("Status") == "Corrigir"])
    pendentes = total - aprovados - reprovados - corrigir

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Aprovados",  aprovados)
    c2.metric("❌ Reprovados", reprovados)
    c3.metric("⚠️ Corrigir",   corrigir)
    c4.metric("⏳ Pendentes",  pendentes)

    if aprovados == total:
        st.success("🎉 Todos os itens aprovados! Portal pronto para produção.")
    elif reprovados or corrigir:
        st.warning(f"⚠️ {reprovados + corrigir} item(s) requerem atenção antes de ir a produção.")

    st.divider()

    # Renderizar cada item
    for num, titulo, descricao in homologacao_setup.CHECKLIST_ITEMS:
        item_data = checklist.get(num, {"Status": "Pendente", "Observacao": ""})
        cur_status = item_data.get("Status", "Pendente")
        cur_obs    = item_data.get("Observacao", "")
        color      = _STATUS_COLORS.get(cur_status, "#6B7280")

        with st.container():
            c_num, c_titulo, c_status, c_btn = st.columns([0.4, 4, 2, 1.2])
            with c_num:
                st.markdown(
                    f"<div style='font-size:1.1rem;font-weight:700;color:{color};"
                    f"text-align:center;padding-top:4px'>{num}</div>",
                    unsafe_allow_html=True,
                )
            with c_titulo:
                st.markdown(
                    f"<div style='font-weight:600;margin-top:4px'>{titulo}</div>"
                    f"<div style='color:#9CA3AF;font-size:0.8rem'>{descricao}</div>",
                    unsafe_allow_html=True,
                )
            with c_status:
                new_status = st.selectbox(
                    "Status",
                    _STATUS_OPTS,
                    index=_STATUS_OPTS.index(cur_status) if cur_status in _STATUS_OPTS else 0,
                    key=f"hom_status_{num}",
                    label_visibility="collapsed",
                )
            with c_btn:
                if st.button("💾", key=f"hom_save_{num}", help="Salvar este item"):
                    obs_key = f"hom_obs_{num}"
                    obs_val = st.session_state.get(obs_key, cur_obs)
                    ok = _save_item(num, titulo, new_status, obs_val)
                    if ok:
                        st.session_state["hom_checklist"][num] = {
                            "Status": new_status, "Observacao": obs_val
                        }
                        st.rerun()

            # Área de observação expandível quando status não é Aprovado
            if cur_status in ("Reprovado", "Corrigir") or cur_obs:
                obs_new = st.text_input(
                    "Observação",
                    value=cur_obs,
                    key=f"hom_obs_{num}",
                    label_visibility="collapsed",
                    placeholder="Detalhe o problema ou ação corretiva...",
                )
            st.markdown("<hr style='margin:4px 0;border-color:#1E3A5F'>", unsafe_allow_html=True)

    # Botão exportar sumário
    st.divider()
    if st.button("📋 Gerar Relatório de Homologação", type="secondary"):
        _gerar_relatorio(homologacao_setup.CHECKLIST_ITEMS, checklist)


def _gerar_relatorio(items: list, checklist: dict) -> None:
    """Exibe o relatório de homologação formatado."""
    from datetime import datetime
    import homologacao_setup

    linhas = [
        "# Relatório de Homologação — Portal Pred.IO",
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"**Cliente teste:** {homologacao_setup.EMPRESA_A} ({homologacao_setup.EMAIL_A})",
        "",
        "## Resultados do Checklist",
        "",
        "| # | Item | Status | Observação |",
        "|---|------|--------|------------|",
    ]
    for num, titulo, _ in items:
        data   = checklist.get(num, {"Status": "Pendente", "Observacao": ""})
        status = data.get("Status", "Pendente")
        obs    = data.get("Observacao", "")
        emoji  = {"Aprovado": "✅", "Reprovado": "❌", "Corrigir": "⚠️", "Pendente": "⏳"}.get(status, "")
        linhas.append(f"| {num} | {titulo} | {emoji} {status} | {obs} |")

    total     = len(items)
    aprovados = len([v for v in checklist.values() if v.get("Status") == "Aprovado"])
    linhas += [
        "",
        "## Resumo",
        f"- Total de itens: **{total}**",
        f"- Aprovados: **{aprovados}**",
        f"- Reprovados: **{len([v for v in checklist.values() if v.get('Status') == 'Reprovado'])}**",
        f"- A Corrigir: **{len([v for v in checklist.values() if v.get('Status') == 'Corrigir'])}**",
        f"- Pendentes: **{total - len(checklist)}**",
        "",
        f"**Resultado Geral:** {'✅ APROVADO' if aprovados == total else '⚠️ EM ANDAMENTO'}",
        "",
        "*Gerado por Pred.IO*",
    ]

    texto = "\n".join(linhas)
    st.download_button(
        "⬇️ Baixar relatório (.md)",
        data=texto,
        file_name=f"homologacao_predio_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown",
    )
    st.markdown(texto)


# ─── ABA PERGUNTAS DO ASSISTENTE ─────────────────────────────────────────────

def _render_tab_perguntas() -> None:
    st.markdown("### 10 Perguntas de Homologação — Assistente Técnico")
    st.info(
        "Faça estas perguntas ao Assistente Técnico logado como **Cliente A** "
        "(Pred.IO Teste) e registre as respostas esperadas."
    )

    perguntas = [
        (1, "Quais são os meus ativos em situação de atenção?",
            "Deve listar MYCOM Compressor Q63 e Motor Principal 75kW com score abaixo de 75."),
        (2, "O que diz o último relatório disponível?",
            "Deve resumir a Análise de Vibração publicada (score, recomendação)."),
        (3, "Quais manutenções estão próximas do vencimento?",
            "Deve mencionar 'Troca de Filtro de Óleo' vencendo em 30/06/2026."),
        (4, "Tenho algum alerta crítico agora?",
            "Deve mencionar o alerta de alta temperatura no MYCOM Q63."),
        (5, "Qual o status do meu chamado sobre o ruído no compressor?",
            "Deve dizer que o chamado está 'Em atendimento' com resposta disponível."),
        (6, "Me explique o que significa score 68 no Motor Principal.",
            "Deve explicar Atenção (60-74) sem transformar score em decisão automática de parada."),
        (7, "Existe algum documento técnico do MYCOM Q63?",
            "Deve mencionar o 'Manual de Operação MYCOM Q63' disponível na Biblioteca."),
        (8, "Qual óleo devo usar no Compressor MYCOM Q63?",
            "Deve responder MYCOLD PAO (referência atual — não usar MYCOLD AB 68 descontinuado)."),
        (9, "Como ativo as notificações por e-mail?",
            "Deve informar que e-mail está preparado para etapa futura e guiar para Preferências."),
        (10, "Quem é você? Qual o seu nome?",
             "Deve responder que é o Assistente Técnico Pred.IO — nunca mencionar Claude ou IA genérica."),
    ]

    for num, pergunta, esperado in perguntas:
        with st.expander(f"{num}. {pergunta}"):
            st.markdown(f"**Resposta esperada:** {esperado}")
            status_key = f"hom_qa_{num}"
            cur = st.session_state.get(status_key, "Pendente")
            col_s, col_obs = st.columns([2, 5])
            with col_s:
                novo = st.selectbox(
                    "Resultado",
                    _STATUS_OPTS,
                    index=_STATUS_OPTS.index(cur) if cur in _STATUS_OPTS else 0,
                    key=f"hom_qa_sel_{num}",
                )
                if novo != cur:
                    st.session_state[status_key] = novo
            with col_obs:
                st.text_area(
                    "Observação / resposta real obtida",
                    key=f"hom_qa_obs_{num}",
                    height=70,
                    placeholder="Cole aqui a resposta que o assistente deu...",
                )


# ─── ABA DADOS DE TESTE ──────────────────────────────────────────────────────

def _render_tab_dados() -> None:
    import homologacao_setup
    st.markdown("### Referência — Dados de Teste Criados")

    st.markdown(f"""
**Cliente A (Teste Principal)**
- Empresa: `{homologacao_setup.EMPRESA_A}`
- Client ID: `{homologacao_setup.CLIENT_ID_A}`
- E-mail login: `{homologacao_setup.EMAIL_A}`
- Telefone: `{homologacao_setup.TELEFONE_A}`
- Senha: *em branco → Primeiro Acesso ao logar*

**Cliente B (Isolamento)**
- Empresa: `{homologacao_setup.EMPRESA_B}`
- Client ID: `{homologacao_setup.CLIENT_ID_B}`
- E-mail login: `{homologacao_setup.EMAIL_B}`
- Senha: *em branco → Primeiro Acesso ao logar*

**Staff de Teste**
- E-mail: `{homologacao_setup.EMAIL_STAFF}`
- Perfil: funcionário
""")

    st.markdown("---")
    st.markdown("#### Ativos — Cliente A")
    for a in homologacao_setup.ATIVOS_A:
        st.markdown(
            f"- **{a['nome']}** | Score: {a['score_saude']} | "
            f"Status: {a['status']} | Criticidade: {a['criticidade']}"
        )

    st.markdown("#### Relatórios")
    st.markdown("""
- Análise de Vibração — MYCOM Q63 → **Publicado** (Crítica)
- Análise de Óleo — Motor Principal → **Publicado** (Alta)
- Manutenção Preventiva — Bomba de Óleo → **Publicado** (Normal)
- Análise Elétrica — Motor Principal → **Rascunho** (invisível ao cliente)
""")

    st.markdown("#### Plano de Manutenção — 6 Tarefas")
    st.markdown("""
| Tarefa | Tipo | Status |
|--------|------|--------|
| Troca de Filtro de Óleo | Calendário | Próximo (vence 30/06/2026) |
| Revisão de Correias | Calendário | Em dia (vence 15/09/2026) |
| Inspeção de Rolamentos | Horímetro | Próximo (~2250h restantes) |
| Troca de Óleo Lubrificante | Horímetro | Próximo (~200h restantes) |
| Análise por Condição — Temperatura | Condição | Depende de análise preditiva |
| Análise por Condição — Vibração | Condição | Depende de análise preditiva |
""")

    st.markdown("#### Alertas")
    st.markdown("""
- Alta Temperatura — MYCOM Q63 → Crítica
- Vibração Elevada — Motor 75kW → Alta
- Nível de Óleo Baixo — Bomba → Média
""")

    st.markdown("#### Chamado de Teste")
    st.markdown("""
- Título: «Ruído Incomum no Compressor MYCOM Q63»
- Status: Em atendimento
- 1 resposta visível ao cliente
- 1 observação interna (invisível ao cliente)
""")

    st.markdown("#### Notificações do Portal")
    st.markdown("""
- Novo relatório: Análise de Vibração (Alta)
- Chamado respondido (Média)
- Manutenção próxima: Filtro de Óleo (Alta)
- Alerta Crítico: Temperatura MYCOM (Crítica)
- Nova recomendação técnica (Média)
""")

    st.markdown("#### Ativo Cliente B (Isolamento)")
    st.markdown(f"""
- **{homologacao_setup.ATIVO_B['nome']}**
- Deve aparecer APENAS para o Cliente B
- Cliente A não deve ver este ativo
""")
