"""Supervisão Pred.IO — Clientes e Histórico."""
import streamlit as st
from auth import require_staff, enter_admin_preview, current_nome
from sheets import (get_all_clientes, get_historico_cliente, get_all_chamados,
                    cadastrar_usuario, delete_usuario, update_usuario,
                    get_client_logo, save_client_logo, delete_ativos_por_cliente,
                    get_contagem_usuarios_global, get_usuarios_staff,
                    add_client_meeting, get_last_meeting, get_client_meetings,
                    snapshot_cliente, get_all_ativos_sv, get_gut_summary,
                    get_maintenance_tasks, calc_task_status, get_report_timeline_events,
                    verificar_email)
from ui import (sv_page_header, sv_metric_card, status_badge, status_color, empty_state, app_alert,
                COLOR_NAVY, COLOR_BLUE, COLOR_BORDER, COLOR_CARD, COLOR_MUTED,
                COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER)


def _compress_logo(file_obj) -> str:
    """Redimensiona para 160×160 e converte para base64 JPEG (mantém tamanho < 50 KB)."""
    try:
        import io, base64
        from PIL import Image
        img = Image.open(file_obj).convert("RGB")
        img.thumbnail((160, 160), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def render() -> None:
    require_staff()
    sv_view = st.session_state.get("sv_view", "clientes")

    if sv_view == "cliente_historico":
        render_historico()
    elif sv_view == "cliente_novo":
        _render_form_novo_cliente()
    else:
        _render_lista()


def _render_lista() -> None:
    sv_page_header("👥 Clientes", "Cadastre e acompanhe os clientes da Pred.IO.")

    # ── Formulário sempre visível no topo ─────────────────────────────────────
    _form_novo_cliente_content(inline=True)

    # ── Adicionar mais uma pessoa a um cliente que já existe ──────────────────
    # "Novo Cliente" acima sempre cria uma EMPRESA nova — não tinha nenhuma
    # tela pra dar acesso a uma segunda pessoa da mesma empresa. Reaproveita
    # cadastrar_usuario() (mesma aba Usuarios), só que com o nome de empresa
    # já existente, pra cair no mesmo client_id (client_id = empresa em
    # minúsculas — auth.get_client_id() — sem coluna própria).
    _form_adicionar_pessoa_content()

    st.markdown(
        f"<hr style='border-color:{COLOR_BORDER};margin:1.5rem 0;'/>",
        unsafe_allow_html=True,
    )

    clientes = get_all_clientes()
    df_todos = get_all_chamados()
    contagem_global = get_contagem_usuarios_global()
    staff = get_usuarios_staff()

    if clientes.empty and df_todos.empty:
        empty_state("Nenhum cliente encontrado.", icon="👥")
        return

    # Derivar lista de clientes dos chamados se a sheet Clientes estiver vazia
    if clientes.empty and not df_todos.empty and "Empresa" in df_todos.columns:
        empresas = (
            df_todos[["Empresa", "Client_Id", "Email"]]
            .drop_duplicates(subset=["Empresa"])
            .reset_index(drop=True)
        )
    else:
        empresas = clientes

    if empresas.empty:
        empty_state("Nenhum cliente encontrado.", icon="👥")
        return

    # Resumo de usuários cadastrados no sistema
    n_cli  = contagem_global.get("cliente",     0)
    n_func = contagem_global.get("funcionario", 0)
    n_adm  = contagem_global.get("admin",       0)
    partes = [f"<strong>{n_cli}</strong> cliente(s)"]
    if n_func: partes.append(f"👷 <strong>{n_func}</strong> funcionário(s)")
    if n_adm:  partes.append(f"🔑 <strong>{n_adm}</strong> admin(s)")
    st.markdown(
        f"<p style='color:#64748B;font-size:0.85rem;margin:0 0 0.5rem;'>"
        f"{'  ·  '.join(partes)} cadastrado(s)</p>",
        unsafe_allow_html=True,
    )

    if staff:
        with st.expander("👤 Ver funcionários e admins cadastrados", expanded=False):
            _PERFIL_BADGE = {
                "admin":       ("#EFF6FF", "#1D4ED8"),
                "funcionario": ("#F0FDF4", "#15803D"),
            }
            linhas = ""
            for u in staff:
                bg, tc = _PERFIL_BADGE.get(u["perfil"], ("#F1F5F9", "#475569"))
                label = "Admin" if u["perfil"] == "admin" else "Funcionário"
                nome  = u["nome"]  or "—"
                email = u["email"] or "—"
                emp   = u["empresa"] or "—"
                linhas += (
                    f"<div style='display:flex;align-items:center;gap:10px;"
                    f"padding:7px 0;border-bottom:1px solid {COLOR_BORDER};'>"
                    f"<span style='background:{bg};color:{tc};-webkit-text-fill-color:{tc};"
                    f"font-size:0.68rem;font-weight:700;padding:2px 8px;"
                    f"border-radius:8px;white-space:nowrap;'>{label}</span>"
                    f"<div>"
                    f"<p style='margin:0;font-size:0.82rem;font-weight:600;color:{COLOR_NAVY};'>{nome}</p>"
                    f"<p style='margin:0;font-size:0.75rem;color:#64748B;'>{email}  ·  {emp}</p>"
                    f"</div></div>"
                )
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-radius:10px;padding:0.5rem 1rem;'>{linhas}</div>",
                unsafe_allow_html=True,
            )

    # Quantos contatos cada client_id tem nesta lista — agora que um cliente
    # pode ter mais de uma pessoa (ver _form_adicionar_pessoa_content), duas
    # linhas podem cair no mesmo client_id. Usado abaixo pra (1) gerar chaves
    # de widget únicas por linha, não só por client_id, e (2) decidir se o
    # botão de excluir pode apagar os ativos do cliente junto (só quando é o
    # único contato — com mais de um, apagaria ativos que outros contatos
    # ainda usam).
    _cid_counts: dict[str, int] = {}
    for _, _r in empresas.iterrows():
        _cid = str(_r.get("Client_Id", str(_r.get("Empresa", "")).strip().lower())).strip()
        _cid_counts[_cid] = _cid_counts.get(_cid, 0) + 1

    for _idx, row in empresas.iterrows():
        empresa    = str(row.get("Empresa",   "")).strip()
        client_id  = str(row.get("Client_Id", empresa.lower())).strip()
        email      = str(row.get("Email",     "")).strip()
        # Sufixo único por linha (e-mail já é o identificador de login,
        # portanto naturalmente único por contato; índice como reforço se
        # faltar e-mail) — client_id sozinho não basta mais como chave.
        _row_key = (email or str(_idx)).replace("@", "_at_").replace(".", "_")

        # Métricas do cliente
        if not df_todos.empty and "Empresa" in df_todos.columns:
            df_cli  = df_todos[df_todos["Empresa"].str.strip().str.lower() == empresa.lower()]
            total   = len(df_cli)
            abertos = len(df_cli[df_cli.get("Status", "").str.lower().str.strip() == "aberto"]) \
                      if "Status" in df_cli.columns else 0
            criticos= len(df_cli[df_cli.get("Prioridade", "").str.lower().str.strip() == "crítica"]) \
                      if "Prioridade" in df_cli.columns else 0
        else:
            total = abertos = criticos = 0

        resumo = []
        if total:    resumo.append(f"<strong>{total}</strong> chamado(s)")
        if abertos:  resumo.append(f"<strong style='color:#3B82F6;'>{abertos}</strong> aberto(s)")
        if criticos: resumo.append(f"<strong style='color:#EF4444;'>{criticos}</strong> crítico(s)")
        if email:    resumo.append(f"✉️ {email}")
        resumo_html = "  ·  ".join(
            f"<span style='font-size:0.8rem;color:#475569;'>{r}</span>" for r in resumo
        )

        col_info, col_preview, col_hist, col_del = st.columns([6, 1.4, 1.2, 0.7])
        with col_info:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-left:4px solid {COLOR_BLUE};border-radius:10px;"
                f"padding:14px 18px;margin-bottom:8px;'>"
                f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:1rem;'>"
                f"🏢 {empresa}</span>"
                f"<div style='margin-top:5px;'>{resumo_html}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_preview:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            if st.button("👁️ Ver como cliente", key=f"sv_cli_preview_{client_id}_{_row_key}",
                         use_container_width=True,
                         help="Visualizar o Portal do Cliente com os dados deste cliente"):
                if enter_admin_preview(client_id, empresa):
                    from sheets import log_audit
                    from auth import current_email, current_perfil
                    log_audit(current_email(), current_perfil(), client_id,
                               "admin_visualizou_portal_cliente", recurso_tipo="cliente",
                               recurso_id=client_id)
                    st.rerun()
        with col_hist:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            if st.button("Histórico →", key=f"sv_cli_{client_id}_{_row_key}",
                         use_container_width=True):
                st.session_state["sv_view"]          = "cliente_historico"
                st.session_state["sv_cliente_id"]    = client_id
                st.session_state["sv_cliente_nome"]  = empresa
                st.session_state["sv_cliente_email"] = email
                st.rerun()
        with col_del:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            _unico_contato = _cid_counts.get(client_id, 1) <= 1
            _del_help = (
                "Excluir este cliente e todos os seus ativos" if _unico_contato
                else "Excluir só o acesso desta pessoa — outros contatos deste "
                     "cliente continuam com acesso, ativos não são tocados"
            )
            if st.button("🗑️", key=f"sv_cli_del_{client_id}_{_row_key}",
                         use_container_width=True, help=_del_help):
                ok = delete_usuario(email)
                if ok:
                    if _unico_contato:
                        n_ativos = delete_ativos_por_cliente(client_id)
                        msg = f"🗑️ Cliente '{empresa}' removido."
                        if n_ativos:
                            msg += f" {n_ativos} ativo(s) relacionado(s) também removido(s)."
                    else:
                        # Mais de um contato neste cliente — apaga só o acesso
                        # desta pessoa. Apagar os ativos aqui derrubaria dados
                        # que os outros contatos do mesmo cliente ainda usam.
                        msg = f"🗑️ Acesso de '{email or empresa}' removido. Ativos de '{empresa}' preservados."
                    st.toast(msg, icon="🗑️")
                    st.rerun()
                else:
                    st.toast("⚠️ Não encontrado na planilha ou é dado de demonstração.", icon="⚠️")


@st.dialog("📅 Registrar reunião")
def _dialog_registrar_reuniao(client_id: str) -> None:
    """Registra quando uma reunião com o cliente aconteceu e qual período
    foi analisado nela — permite que o comparativo "O que mudou desde a
    última reunião?" saiba automaticamente o período de referência.
    Observação é sempre interna (nunca aparece pro cliente, mesmo padrão de
    Obs_Interna usado no resto do projeto)."""
    import datetime as _dt

    titulo = st.text_input("Título", value="Reunião de acompanhamento")
    data_reuniao = st.date_input("Data da reunião", value=_dt.date.today())
    c1, c2 = st.columns(2)
    with c1:
        periodo_ini = st.date_input("Período analisado — de", value=_dt.date.today() - _dt.timedelta(days=30))
    with c2:
        periodo_fim = st.date_input("Período analisado — até", value=_dt.date.today())
    observacao = st.text_area("Observação (interna, opcional)", value="")

    if st.button("✅ Registrar", type="primary", use_container_width=True):
        if periodo_fim < periodo_ini:
            st.error("O período final deve ser posterior ao inicial.")
            return
        meeting_id = add_client_meeting(
            cliente_id=client_id, titulo=titulo,
            data_reuniao=data_reuniao.strftime("%d/%m/%Y"),
            periodo_inicio=periodo_ini.strftime("%d/%m/%Y"),
            periodo_fim=periodo_fim.strftime("%d/%m/%Y"),
            observacao=observacao, criado_por=current_nome(),
        )
        if meeting_id:
            try:
                snapshot_cliente(client_id)
            except Exception:
                pass
            st.success("Reunião registrada.")
            st.rerun()
        else:
            st.error("Não foi possível registrar a reunião.")


def _render_visao_executiva(client_id: str) -> None:
    """"Visão Executiva do Cliente" — cartões-resumo no topo da tela.
    Reaproveita a mesma lógica de status/GUT já usada em executive_summary.py
    (_status_ativo_norm), mas calcula manutenções vencidas via
    calc_task_status() dinâmico — não via Status bruto salvo na tarefa, que
    não é recalculado com o tempo (ficaria sempre "Em dia" indefinidamente
    pra tarefa realmente vencida há semanas)."""
    import pandas as pd
    import datetime as _dt_mod
    from executive_summary import _status_ativo_norm
    from sheets import get_alertas_sv, get_chamados_v2, get_technical_reports

    df_ativos = get_all_ativos_sv()
    if not df_ativos.empty and "Client_Id" in df_ativos.columns:
        df_ativos = df_ativos[df_ativos["Client_Id"].astype(str).str.strip().str.lower() == client_id.strip().lower()]

    n_ativos = len(df_ativos)
    scores = pd.to_numeric(df_ativos.get("Score", pd.Series(dtype=float)), errors="coerce").dropna()
    saude_media = round(float(scores.mean()), 1) if len(scores) else None
    if not df_ativos.empty and "Status" in df_ativos.columns:
        st_norm = df_ativos["Status"].astype(str).apply(_status_ativo_norm)
    else:
        st_norm = pd.Series(dtype=str)
    n_criticos = int(st_norm.isin(["Crítico", "Urgente"]).sum())
    n_atencao  = int((st_norm == "Atenção").sum())

    try:
        gut_itens = get_gut_summary(client_id)
    except Exception:
        gut_itens = []
    maior_gut = gut_itens[0]["score"] if gut_itens else None

    n_venc = 0
    try:
        df_tasks = get_maintenance_tasks(client_id=client_id, staff=True)
        if not df_tasks.empty and "Status" in df_tasks.columns:
            df_tasks = df_tasks[~df_tasks["Status"].astype(str).str.lower().str.contains("conclu|arquiv", na=False)]
        for _, t in df_tasks.iterrows():
            if calc_task_status(t.to_dict()) == "Vencida":
                n_venc += 1
    except Exception:
        pass

    n_alertas_criticos = 0
    try:
        df_al = get_alertas_sv(client_id)
        if not df_al.empty and "Prioridade" in df_al.columns:
            n_alertas_criticos = int(df_al["Prioridade"].astype(str).str.lower().isin(
                ["crítica", "critica", "urgente"]).sum())
    except Exception:
        pass

    n_chamados_abertos = 0
    try:
        df_cham = get_chamados_v2(client_id=client_id)
        if not df_cham.empty and "Status" in df_cham.columns:
            n_chamados_abertos = int((df_cham["Status"].astype(str).str.strip() != "Concluído").sum())
    except Exception:
        pass

    n_rel_30d = 0
    try:
        df_rel = get_technical_reports(client_id=client_id, staff=True)
        if not df_rel.empty and "Data_Relatorio" in df_rel.columns:
            dts = pd.to_datetime(df_rel["Data_Relatorio"], dayfirst=True, errors="coerce")
            n_rel_30d = int((dts >= pd.Timestamp(_dt_mod.date.today() - _dt_mod.timedelta(days=30))).sum())
    except Exception:
        pass

    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:0.75rem 0 0.5rem;'>"
        f"📊 Visão Executiva do Cliente</p>",
        unsafe_allow_html=True,
    )
    cards = [
        ("⚙️", "Ativos", n_ativos, COLOR_NAVY),
        ("💚", "Saúde Média", f"{saude_media}/100" if saude_media is not None else "—",
         COLOR_SUCCESS if (saude_media or 0) >= 70 else COLOR_WARNING),
        ("🔴", "Ativos Críticos", n_criticos, COLOR_DANGER if n_criticos else COLOR_SUCCESS),
        ("🟡", "Ativos em Atenção", n_atencao, COLOR_WARNING if n_atencao else COLOR_SUCCESS),
        ("🎯", "Maior GUT", maior_gut if maior_gut is not None else "—",
         COLOR_DANGER if (maior_gut or 0) >= 60 else COLOR_BLUE),
        ("📅", "Manutenções Vencidas", n_venc, COLOR_DANGER if n_venc else COLOR_SUCCESS),
        ("🔔", "Alertas Críticos", n_alertas_criticos, COLOR_DANGER if n_alertas_criticos else COLOR_SUCCESS),
        ("🔧", "Chamados Abertos", n_chamados_abertos, COLOR_WARNING if n_chamados_abertos else COLOR_SUCCESS),
        ("📁", "Relatórios (30d)", n_rel_30d, COLOR_BLUE),
    ]
    cols = st.columns(3)
    for i, (icon, title, value, color) in enumerate(cards):
        with cols[i % 3]:
            sv_metric_card(icon, title, value, color)
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)


def _render_top_prioridades(client_id: str) -> None:
    """"Prioridades atuais" — Top 5 por GUT, com botão para o ativo."""
    try:
        gut_itens = get_gut_summary(client_id)[:5]
    except Exception:
        gut_itens = []
    if not gut_itens:
        return

    df_ativos = get_all_ativos_sv()
    nome_por_id = {}
    if not df_ativos.empty and "Id" in df_ativos.columns:
        nome_col = "Tag" if "Tag" in df_ativos.columns else "Id"
        for _, r in df_ativos.iterrows():
            nome_por_id[str(r.get("Id", "")).strip()] = str(r.get(nome_col, "")).strip()

    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:1rem 0 0.5rem;'>"
        f"🎯 Prioridades atuais</p>",
        unsafe_allow_html=True,
    )
    for item in gut_itens:
        ativo_id_item = item.get("ativo_id", "")
        ativo_nome = nome_por_id.get(ativo_id_item, "") or ativo_id_item or "—"
        cor = {"Crítica": COLOR_DANGER, "Alta": "#F97316"}.get(item.get("prioridade", ""), COLOR_WARNING)
        col_info, col_btn = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-left:4px solid {cor};border-radius:10px;padding:10px 14px;margin-bottom:4px;'>"
                f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.85rem;'>{ativo_nome}</span> — "
                f"<span style='font-size:0.82rem;color:#475569;'>{item.get('titulo', '')}</span><br/>"
                f"<span style='font-size:0.72rem;color:{COLOR_MUTED};'>Origem: {item.get('origem', '')} · "
                f"Prioridade: {item.get('prioridade', '')} · Ação: {item.get('acao_recomendada', '')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            if ativo_id_item and st.button("Ver →", key=f"topprio_{item.get('id', '')}", use_container_width=True):
                st.session_state["sv_ativo_id"] = ativo_id_item
                st.session_state["sv_ativo_cliente_id"] = client_id
                st.session_state["sv_view"] = "ativo_detalhe"
                st.rerun()


def _render_ativos_atencao(client_id: str) -> None:
    """"Ativos que merecem atenção" — no máximo 5, ordenados por
    Urgente → Crítico → maior GUT → pior score."""
    import pandas as pd
    from executive_summary import _status_ativo_norm

    df_ativos = get_all_ativos_sv()
    if df_ativos.empty or "Client_Id" not in df_ativos.columns:
        return
    df_ativos = df_ativos[df_ativos["Client_Id"].astype(str).str.strip().str.lower() == client_id.strip().lower()]
    if df_ativos.empty:
        return

    try:
        gut_itens = get_gut_summary(client_id)
    except Exception:
        gut_itens = []
    gut_por_ativo: dict = {}
    for i in gut_itens:
        aid = i.get("ativo_id", "")
        if aid and (aid not in gut_por_ativo or i["score"] > gut_por_ativo[aid]):
            gut_por_ativo[aid] = i["score"]

    id_col   = "Id" if "Id" in df_ativos.columns else df_ativos.columns[0]
    nome_col = "Tag" if "Tag" in df_ativos.columns else id_col
    rank_status = {"Urgente": 0, "Crítico": 1, "Atenção": 2, "Bom": 3}
    linhas = []
    for _, row in df_ativos.iterrows():
        aid = str(row.get(id_col, "")).strip()
        status_norm = _status_ativo_norm(row.get("Status", ""))
        try:
            score = int(float(row.get("Score", "0") or "0"))
        except Exception:
            score = 999
        linhas.append({
            "ativo_id": aid, "nome": str(row.get(nome_col, aid)).strip() or aid,
            "status": status_norm, "score": score, "gut": gut_por_ativo.get(aid, 0),
        })
    linhas.sort(key=lambda l: (rank_status.get(l["status"], 3), -l["gut"], l["score"]))
    linhas = [l for l in linhas if l["status"] != "Bom" or l["gut"] > 0][:5]
    if not linhas:
        return

    from sheets import get_technical_reports
    st.markdown(
        f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.95rem;margin:1rem 0 0.5rem;'>"
        f"⚠️ Ativos que merecem atenção</p>",
        unsafe_allow_html=True,
    )
    for l in linhas:
        ultimo_rel = "—"
        try:
            df_r = get_technical_reports(client_id=client_id, ativo_id=l["ativo_id"], staff=True)
            if not df_r.empty and "Data_Relatorio" in df_r.columns:
                ultimo_rel = str(df_r.iloc[0].get("Data_Relatorio", "—"))
        except Exception:
            pass
        cor = {"Urgente": COLOR_DANGER, "Crítico": COLOR_DANGER, "Atenção": COLOR_WARNING}.get(l["status"], COLOR_SUCCESS)
        col_info, col_btn = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
                f"border-left:4px solid {cor};border-radius:10px;padding:10px 14px;margin-bottom:4px;'>"
                f"<span style='font-weight:700;color:{COLOR_NAVY};font-size:0.85rem;'>{l['nome']}</span> "
                + status_badge(l["status"], "saude_ativo")
                + f"<br/><span style='font-size:0.72rem;color:{COLOR_MUTED};'>"
                f"Score: {l['score']} · Maior GUT: {l['gut'] or '—'} · Último relatório: {ultimo_rel}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            if st.button("Ver →", key=f"atativo_{l['ativo_id']}", use_container_width=True):
                st.session_state["sv_ativo_id"] = l["ativo_id"]
                st.session_state["sv_ativo_cliente_id"] = client_id
                st.session_state["sv_view"] = "ativo_detalhe"
                st.rerun()


def _render_atividade_recente(client_id: str) -> None:
    """"Atividade recente" — timeline agregada do CLIENTE (todos os ativos),
    limitada a 15 eventos — nunca carrega o histórico completo de uma vez
    (mesmo adaptador de dados de page_sv_ativos.py, reaproveitando
    _render_historico_tecnico de page_ativos.py)."""
    try:
        df_tl = get_report_timeline_events(ativo_id="", cliente_id=client_id, staff=True, limit=15)
    except Exception:
        df_tl = None
    if df_tl is None or df_tl.empty:
        return

    from page_ativos import _render_historico_tecnico
    ht_data = [
        {
            "id":              str(r.get("Id", "")),
            "tipo":            str(r.get("Tipo", "relatorio_publicado")),
            "titulo":          str(r.get("Titulo", "")),
            "descricao":       str(r.get("Descricao", "")),
            "data":            str(r.get("Data", "")),
            "origem":          str(r.get("Origem", "")),
            "link_page":       "relatorios",
            "visivel_cliente": str(r.get("Visivel_Cliente", "true")).strip().lower() != "false",
            "obs_interna":     str(r.get("Obs_Interna", "")).strip() or None,
        }
        for _, r in df_tl.iterrows()
    ]
    st.markdown(f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0;'/>", unsafe_allow_html=True)
    _render_historico_tecnico(ht_data, ativo_id=f"cliente_{client_id}", is_staff=True, prefix="svcli_atv_")


def render_historico() -> None:
    client_id = st.session_state.get("sv_cliente_id", "")
    empresa   = st.session_state.get("sv_cliente_nome", client_id)

    sv_page_header(
        f"📋 {empresa}",
        subtitle="Histórico completo do cliente",
        back_label="Clientes",
        back_view="clientes",
    )

    if not client_id:
        st.warning("Cliente não identificado.")
        return

    _render_visao_executiva(client_id)
    st.markdown(f"<hr style='border-color:{COLOR_BORDER};margin:1rem 0;'/>", unsafe_allow_html=True)

    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    with col_btn1:
        from resumo_executivo_ui import render_resumo_executivo_button
        render_resumo_executivo_button(client_id=client_id, cliente_nome=empresa, key_prefix="svcli_resexec")
    with col_btn2:
        # Mesmo componente/motor do botão acima, com o comparativo "o que
        # mudou" injetado antes do preview — não duplica lógica.
        render_resumo_executivo_button(client_id=client_id, cliente_nome=empresa,
                                       key_prefix="svcli_prepreuniao", mostrar_comparativo=True)
    with col_btn3:
        from comparativo_ui import render_comparativo_button
        render_comparativo_button(client_id=client_id, cliente_nome=empresa, key_prefix="svcli_comparativo")
    with col_btn4:
        if st.button("📅 Registrar reunião", use_container_width=True):
            _dialog_registrar_reuniao(client_id)

    ultima_reuniao = get_last_meeting(client_id)
    if ultima_reuniao:
        st.caption(
            f"🗓️ Última reunião registrada: **{ultima_reuniao['titulo']}** em "
            f"{ultima_reuniao['data_reuniao']} (período analisado: "
            f"{ultima_reuniao['periodo_inicio']} a {ultima_reuniao['periodo_fim']})."
        )
    else:
        st.caption("🗓️ Nenhuma reunião registrada ainda para este cliente.")

    _render_top_prioridades(client_id)
    _render_ativos_atencao(client_id)
    _render_atividade_recente(client_id)
    st.markdown(f"<hr style='border-color:{COLOR_BORDER};margin:1.25rem 0;'/>", unsafe_allow_html=True)

    historico = get_historico_cliente(client_id)
    chamados   = historico.get("chamados",   None)
    relatorios = historico.get("relatorios", None)

    import pandas as pd
    if chamados is None:
        chamados = pd.DataFrame()
    if relatorios is None:
        relatorios = pd.DataFrame()

    # ── Métricas ──────────────────────────────────────────────────────────────
    total_cham  = len(chamados)
    abertos     = 0
    criticos    = 0
    concluidos  = 0
    ultimo_cham = "—"

    if not chamados.empty:
        if "Status" in chamados.columns:
            status_lower = chamados["Status"].str.strip().str.lower()
            abertos    = len(chamados[status_lower == "aberto"])
            concluidos = len(chamados[status_lower == "concluído"])
        if "Prioridade" in chamados.columns:
            criticos = len(chamados[chamados["Prioridade"].str.strip().str.lower() == "crítica"])
        if "Data_Abertura" in chamados.columns:
            ultimo_cham = chamados.iloc[0].get("Data_Abertura", "—")
            ultimo_cham = str(ultimo_cham)[:10] if ultimo_cham else "—"

    total_rel   = len(relatorios)
    ultimo_rel  = "—"
    if not relatorios.empty and "Data_Relatorio" in relatorios.columns:
        ultimo_rel = str(relatorios.iloc[0].get("Data_Relatorio", "—"))[:10]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sv_metric_card("🔧", "Total de Chamados", total_cham, "#3B82F6")
    with c2:
        sv_metric_card("🔴", "Chamados Críticos", criticos, "#EF4444")
    with c3:
        sv_metric_card("✅", "Concluídos", concluidos, "#10B981")
    with c4:
        sv_metric_card("📁", "Relatórios", total_rel, "#6366F1")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Logo do cliente ───────────────────────────────────────────────────────
    with st.expander("🖼️ Logo do cliente no portal", expanded=False):
        logo_atual = get_client_logo(client_id)
        if logo_atual:
            col_img, col_msg = st.columns([1, 5])
            with col_img:
                st.image(f"data:image/jpeg;base64,{logo_atual}", width=72)
            with col_msg:
                st.caption("Logo atual exibida no portal do cliente.")
        else:
            st.caption("Nenhuma logo cadastrada para este cliente.")

        logo_nova = st.file_uploader(
            "Enviar nova logo",
            type=["jpg", "jpeg", "png"],
            key=f"logo_historico_{client_id}",
            help="PNG ou JPEG — será redimensionada para 160×160 px.",
        )
        if logo_nova:
            nova_b64 = _compress_logo(logo_nova)
            if nova_b64:
                col_prev2, _ = st.columns([1, 6])
                with col_prev2:
                    st.image(f"data:image/jpeg;base64,{nova_b64}", width=64)
                if st.button("💾 Salvar logo", key=f"btn_logo_{client_id}"):
                    if save_client_logo(client_id, nova_b64):
                        st.success("Logo salva com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao salvar a logo.")

    # ── Tabs: Editar / Chamados / Relatórios ─────────────────────────────────
    tab_edit, tab_cham, tab_rel = st.tabs(["✏️ Editar dados", "🔧 Chamados", "📁 Relatórios"])

    with tab_edit:
        _render_edit_cliente(client_id, empresa)

    with tab_cham:
        if chamados.empty:
            empty_state("Nenhum chamado registrado para este cliente.", icon="🔧")
        else:
            for _, row in chamados.iterrows():
                _render_chamado_mini(row)

    with tab_rel:
        if relatorios.empty:
            empty_state("Nenhum relatório registrado para este cliente.", icon="📁")
        else:
            for _, row in relatorios.iterrows():
                _render_relatorio_mini(row)


def _render_edit_cliente(client_id: str, empresa: str) -> None:
    """Formulário de edição dos dados cadastrais do cliente."""
    # Carregar dados atuais
    df_cli = get_all_clientes()
    dados_atuais = {}
    if not df_cli.empty:
        match = df_cli[df_cli.get("Client_Id", df_cli.get("Empresa", df_cli.iloc[:, 0]))
                       .str.strip().str.lower() == client_id.lower()]
        if not match.empty:
            dados_atuais = match.iloc[0].to_dict()

    email_atual   = str(dados_atuais.get("Email",    st.session_state.get("sv_cliente_email", ""))).strip()
    nome_atual    = str(dados_atuais.get("Nome",     "")).strip()
    telefone_atual= str(dados_atuais.get("Telefone", "")).strip()
    perfil_atual  = str(dados_atuais.get("Perfil",   "cliente")).strip().lower()

    perfis = ["cliente", "funcionario", "admin"]
    perfil_idx = perfis.index(perfil_atual) if perfil_atual in perfis else 0

    with st.form("form_edit_cliente"):
        st.markdown(
            f"<p style='font-size:0.8rem;color:#64748B;margin:0 0 0.75rem;'>"
            f"🏢 Empresa: <strong>{empresa}</strong> &nbsp;·&nbsp; "
            f"Client ID: <code>{client_id}</code></p>",
            unsafe_allow_html=True,
        )
        col_n, col_e = st.columns(2)
        with col_n:
            novo_nome = st.text_input("Nome do contato", value=nome_atual)
        with col_e:
            novo_email = st.text_input("E-mail", value=email_atual)

        col_t, col_p = st.columns(2)
        with col_t:
            novo_tel = st.text_input("Telefone", value=telefone_atual)
        with col_p:
            novo_perfil = st.selectbox(
                "Perfil",
                perfis,
                index=perfil_idx,
                format_func=lambda x: {"cliente": "Cliente", "funcionario": "Funcionário", "admin": "Admin"}[x],
            )

        salvar = st.form_submit_button("💾 Salvar alterações", type="primary",
                                       use_container_width=True)

    if salvar:
        if not email_atual:
            st.warning("E-mail atual não encontrado — não foi possível identificar o registro.")
            return
        campos = {
            "Nome":     novo_nome.strip(),
            "Email":    novo_email.strip().lower(),
            "Telefone": novo_tel.strip(),
            "Perfil":   novo_perfil,
        }
        ok = update_usuario(email_atual, campos)
        if ok:
            st.success("✅ Dados do cliente atualizados com sucesso!")
            if novo_email.strip().lower() != email_atual:
                st.session_state["sv_cliente_email"] = novo_email.strip().lower()
        else:
            st.error("❌ Erro ao salvar. Verifique se a aba Usuarios existe e tem permissão de escrita.")


def _render_chamado_mini(row) -> None:
    chamado_id  = str(row.get("Id",          "")).strip()
    titulo      = str(row.get("Titulo",      "Sem título")).strip()
    planta      = str(row.get("Planta",      "")).strip()
    equipamento = str(row.get("Equipamento", "")).strip()
    prioridade  = str(row.get("Prioridade",  "Baixa")).strip()
    status      = str(row.get("Status",      "Aberto")).strip()
    data_ab     = str(row.get("Data_Abertura","")).strip()[:10]

    pr_bg = status_color(prioridade, "prioridade")

    col_info, col_btn = st.columns([7, 1])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {pr_bg};border-radius:8px;"
            f"padding:10px 14px;margin-bottom:6px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"flex-wrap:wrap;gap:6px;'>"
            f"<span style='font-weight:600;color:{COLOR_NAVY};font-size:0.9rem;'>{titulo}</span>"
            f"<div style='display:flex;gap:5px;'>"
            + status_badge(prioridade, "prioridade")
            + status_badge(status, "chamado")
            + f"</div></div>"
            f"<div style='margin-top:4px;font-size:0.78rem;color:#64748B;'>"
            + (f"🏭 {planta}  " if planta else "")
            + (f"⚙️ {equipamento}  " if equipamento else "")
            + (f"📅 {data_ab}" if data_ab else "")
            + "</div></div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if chamado_id and st.button("Ver →", key=f"cli_cham_{chamado_id}_{id(row)}",
                                    use_container_width=True):
            st.session_state["sv_view"]       = "chamado_detalhe"
            st.session_state["sv_chamado_id"] = chamado_id
            st.rerun()


def _render_relatorio_mini(row) -> None:
    titulo  = str(row.get("Titulo",         "")).strip() or "Relatório"
    tipo    = str(row.get("Tipo_Servico",   "")).strip()
    data    = str(row.get("Data_Relatorio", "")).strip()[:10]
    planta  = str(row.get("Planta",         "")).strip()
    equip   = str(row.get("Equipamento",    "")).strip()
    url     = str(row.get("Arquivo_Url",    "")).strip()
    status  = str(row.get("Status",         "Disponível")).strip()

    col_info, col_btn = st.columns([7, 1])
    with col_info:
        st.markdown(
            f"<div style='background:{COLOR_CARD};border:1px solid {COLOR_BORDER};"
            f"border-left:4px solid {COLOR_BLUE};border-radius:8px;"
            f"padding:10px 14px;margin-bottom:6px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='font-weight:600;color:{COLOR_NAVY};font-size:0.9rem;'>{titulo}</span>"
            + status_badge(status, "relatorio")
            + f"</div>"
            f"<div style='font-size:0.78rem;color:#64748B;margin-top:4px;'>"
            + (f"📋 {tipo}  " if tipo else "")
            + (f"📅 {data}  " if data else "")
            + (f"🏭 {planta}  " if planta else "")
            + (f"⚙️ {equip}" if equip else "")
            + "</div></div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if url and url.lower() not in ("", "nan", "none"):
            st.link_button("📄", url, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULÁRIO — NOVO CLIENTE (conteúdo reutilizável)
# ═══════════════════════════════════════════════════════════════════════════════
def _form_novo_cliente_content(inline: bool = False) -> None:
    import hashlib

    form_key = "form_novo_cliente_inline" if inline else "form_novo_cliente"

    with st.form(form_key, clear_on_submit=False):
        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0 0 0.75rem;'>1. Empresa</p>",
            unsafe_allow_html=True,
        )
        col_emp, col_nome = st.columns(2)
        with col_emp:
            empresa = st.text_input("Nome da empresa *", placeholder="Ex: Coca-Cola")
        with col_nome:
            nome = st.text_input("Nome do contato *", placeholder="Ex: João Silva")

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0.75rem 0 0.75rem;'>2. Acesso</p>",
            unsafe_allow_html=True,
        )
        col_email, col_tel = st.columns(2)
        with col_email:
            email = st.text_input("E-mail", placeholder="Ex: joao@empresa.com")
        with col_tel:
            telefone = st.text_input("Telefone", placeholder="Ex: 21999990000")

        col_perfil, col_senha = st.columns(2)
        with col_perfil:
            perfil = st.selectbox(
                "Perfil de acesso",
                ["cliente", "funcionario", "admin"],
                format_func=lambda x: {"cliente": "Cliente", "funcionario": "Funcionário", "admin": "Admin"}[x],
            )
        with col_senha:
            senha = st.text_input(
                "Senha inicial (opcional)",
                type="password",
                placeholder="Deixe vazio para primeiro acesso",
                help="Se não informada, o usuário definirá a senha no primeiro login.",
            )

        app_alert(
            "Se a senha ficar em branco, o usuário vai cadastrar a própria senha "
            "no primeiro acesso ao portal.", kind="info",
        )

        st.markdown(
            f"<p style='font-weight:700;color:{COLOR_NAVY};font-size:0.88rem;"
            f"margin:0.75rem 0 0.5rem;'>3. Logo do cliente (opcional)</p>",
            unsafe_allow_html=True,
        )
        logo_file = st.file_uploader(
            "Selecione a logo",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
            key=f"logo_upload_{form_key}",
            help="Aparece no portal do cliente. PNG ou JPEG, qualquer tamanho — será redimensionada.",
        )
        logo_b64 = ""
        if logo_file:
            logo_b64 = _compress_logo(logo_file)
            if logo_b64:
                col_prev, _ = st.columns([1, 6])
                with col_prev:
                    st.image(f"data:image/jpeg;base64,{logo_b64}", width=64)

        submitted = st.form_submit_button("💾 Cadastrar cliente", type="primary",
                                          use_container_width=True)

    if submitted:
        erros = []
        if not empresa.strip():
            erros.append("Informe o nome da empresa.")
        if not nome.strip():
            erros.append("Informe o nome do contato.")
        if not email.strip() and not telefone.strip():
            erros.append("Informe ao menos e-mail ou telefone para o login.")
        if erros:
            for e in erros:
                st.warning(e)
            return

        senha_hash = hashlib.sha256(senha.encode("utf-8")).hexdigest() if senha.strip() else ""

        ok = cadastrar_usuario(
            empresa=empresa.strip(),
            email=email.strip().lower(),
            telefone=telefone.strip(),
            perfil=perfil,
            nome=nome.strip(),
            senha_hash=senha_hash,
        )

        if ok:
            if logo_b64:
                save_client_logo(empresa.strip().lower(), logo_b64)
            st.success(
                f"✅ Cliente **{empresa.strip()}** cadastrado com sucesso! "
                + ("O usuário deverá definir a senha no primeiro acesso."
                   if not senha.strip() else "Acesso liberado com a senha informada.")
            )
            st.balloons()
            if inline:
                st.session_state.pop("sv_show_form_cliente", None)
            else:
                st.session_state["sv_view"] = "clientes"
            st.rerun()
        else:
            st.error(
                "Erro ao cadastrar o cliente. Verifique se a aba 'Usuarios' existe "
                "na planilha e se as credenciais têm permissão de escrita."
            )


def _form_adicionar_pessoa_content() -> None:
    """Adiciona uma nova pessoa (contato) a um cliente/empresa JÁ cadastrado
    — mesma aba Usuarios do "Novo Cliente" acima, mas sem criar empresa nova.
    Usa exatamente o nome de empresa já salvo, pra cair no mesmo client_id do
    cliente existente."""
    import hashlib

    clientes = get_all_clientes()
    if clientes.empty or "Empresa" not in clientes.columns:
        return
    empresas_unicas = sorted(
        e for e in clientes["Empresa"].dropna().astype(str).str.strip().unique() if e
    )
    if not empresas_unicas:
        return

    with st.expander("➕ Adicionar pessoa a um cliente já cadastrado", expanded=False):
        with st.form("form_add_pessoa_cliente", clear_on_submit=False):
            empresa_sel = st.selectbox("Empresa *", empresas_unicas)

            col_nome, col_email = st.columns(2)
            with col_nome:
                nome = st.text_input("Nome do contato *", placeholder="Ex: Maria Souza")
            with col_email:
                email = st.text_input("E-mail", placeholder="Ex: maria@empresa.com")

            col_tel, col_perfil = st.columns(2)
            with col_tel:
                telefone = st.text_input("Telefone", placeholder="Ex: 21999990000")
            with col_perfil:
                perfil = st.selectbox(
                    "Perfil de acesso",
                    ["cliente", "funcionario", "admin"],
                    format_func=lambda x: {"cliente": "Cliente", "funcionario": "Funcionário", "admin": "Admin"}[x],
                )

            senha = st.text_input(
                "Senha inicial (opcional)",
                type="password",
                placeholder="Deixe vazio para primeiro acesso",
                help="Se não informada, a pessoa define a própria senha no primeiro login.",
            )

            submitted = st.form_submit_button("💾 Adicionar pessoa", type="primary",
                                              use_container_width=True)

        if submitted:
            erros = []
            if not nome.strip():
                erros.append("Informe o nome do contato.")
            if not email.strip() and not telefone.strip():
                erros.append("Informe ao menos e-mail ou telefone para o login.")
            if erros:
                for e in erros:
                    st.warning(e)
                return

            # Impede duas pessoas compartilhando o mesmo login: o login busca
            # por e-mail e depois por telefone, parando no primeiro que casar
            # (auth._find_user) — sem checar aqui, a pessoa nova cairia
            # sempre na conta da primeira que usar o mesmo contato.
            login_candidato = email.strip() or telefone.strip()
            existe, _, dados_existentes = verificar_email(login_candidato)
            if existe:
                dono = str((dados_existentes or {}).get("Nome", "")).strip() or "outra pessoa"
                st.error(
                    f"Esse e-mail/telefone já está cadastrado para **{dono}**. "
                    "Use um e-mail ou telefone diferente para esta pessoa."
                )
                return

            senha_hash = hashlib.sha256(senha.encode("utf-8")).hexdigest() if senha.strip() else ""
            ok = cadastrar_usuario(
                empresa=empresa_sel,
                email=email.strip().lower(),
                telefone=telefone.strip(),
                perfil=perfil,
                nome=nome.strip(),
                senha_hash=senha_hash,
            )
            if ok:
                st.success(
                    f"✅ **{nome.strip()}** adicionado(a) como acesso de **{empresa_sel}**! "
                    + ("A pessoa deverá definir a senha no primeiro acesso."
                       if not senha.strip() else "Acesso liberado com a senha informada.")
                )
                st.rerun()
            else:
                st.error(
                    "Erro ao adicionar. Verifique se a aba 'Usuarios' existe na planilha "
                    "e se as credenciais têm permissão de escrita."
                )


def _render_form_novo_cliente() -> None:
    sv_page_header(
        "➕ Novo Cliente",
        subtitle="Cadastre um cliente para acessar o Portal de Confiabilidade.",
        back_label="Clientes",
        back_view="clientes",
    )
    _form_novo_cliente_content(inline=False)
