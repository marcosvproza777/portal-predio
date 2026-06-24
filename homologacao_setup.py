"""
Homologação Pred.IO — módulo de setup de dados de teste.

Chamado a partir de page_sv_homologacao.render() dentro do contexto Streamlit.
Retorna lista de (status, mensagem) para exibição.
"""

from datetime import datetime


# ─── CONFIGURAÇÃO ────────────────────────────────────────────────────────────

EMPRESA_A   = "Pred.IO Teste"
CLIENT_ID_A = "pred.io teste"         # empresa.strip().lower()
EMAIL_A     = "cliente.teste@predio.io"
TELEFONE_A  = "11900000001"

EMPRESA_B   = "Pred.IO Teste B"
CLIENT_ID_B = "pred.io teste b"
EMAIL_B     = "cliente.teste.b@predio.io"
TELEFONE_B  = "11900000002"

EMAIL_STAFF = "supervisor.teste@predio.io"

# ─── DADOS DE ATIVOS ─────────────────────────────────────────────────────────

ATIVOS_A = [
    {
        "_tag_id": "MYCOM-Q63-01",          # chave de idempotência
        "empresa": EMPRESA_A, "client_id": CLIENT_ID_A,
        "nome": "MYCOM Compressor Q63",
        "tipo": "Compressor de Parafuso", "modelo": "MYCOM Q63",
        "numero_serie": "MC-2019-001",
        "mb": "MYCOLD PAO 68",
        "analise_oleo_aplicavel": "Sim",
        "status": "Atenção", "score_saude": 72, "criticidade": "Alta",
        "recomendacao": "Monitorar temperatura de descarga e vibração. Planejar inspeção interna.",
        "observacoes_internas": "Suspeita de desgaste no estágio de compressão. Verificar pistão.",
        "horimetro_atual": 12500,
        "ultima_atualizacao": "20/06/2026",
    },
    {
        "_tag_id": "MTR-75KW-01",
        "empresa": EMPRESA_A, "client_id": CLIENT_ID_A,
        "nome": "Motor Principal 75kW",
        "tipo": "Motor Elétrico", "modelo": "WEG W22 75kW",
        "numero_serie": "WEG-2020-022",
        "mb": "",
        "analise_oleo_aplicavel": "Não",
        "status": "Atenção", "score_saude": 68, "criticidade": "Média",
        "recomendacao": "Verificar alinhamento e lubrificação dos mancais.",
        "observacoes_internas": "Vibração medida em 4,2 mm/s. Limite tolerado: 4,5 mm/s.",
        "horimetro_atual": 8750,
        "ultima_atualizacao": "20/06/2026",
    },
    {
        "_tag_id": "BBA-OL-01",
        "empresa": EMPRESA_A, "client_id": CLIENT_ID_A,
        "nome": "Bomba de Óleo Industrial",
        "tipo": "Bomba Centrífuga", "modelo": "Worthington 4x3",
        "numero_serie": "WOR-2021-055",
        "mb": "MYCOLD PAO 68",
        "analise_oleo_aplicavel": "Sim",
        "status": "Bom", "score_saude": 88, "criticidade": "Baixa",
        "recomendacao": "Continuar monitoramento periódico conforme plano.",
        "observacoes_internas": "Sem anomalias detectadas no último levantamento.",
        "horimetro_atual": 3200,
        "ultima_atualizacao": "20/06/2026",
    },
]

ATIVO_B = {
    "_tag_id": "COMP-B-01",
    "empresa": EMPRESA_B, "client_id": CLIENT_ID_B,
    "nome": "Compressor Teste Isolamento",
    "tipo": "Compressor", "modelo": "Teste-B",
    "numero_serie": "B-001",
    "mb": "", "analise_oleo_aplicavel": "Não",
    "status": "Bom", "score_saude": 75, "criticidade": "Baixa",
    "recomendacao": "Ativo de teste — isolamento cliente.",
    "observacoes_internas": "Criado para teste de isolamento de cliente_id.",
    "horimetro_atual": 1000,
    "ultima_atualizacao": "20/06/2026",
}

# ─── HELPERS INTERNOS ────────────────────────────────────────────────────────

def _find_ativo_id(df, client_id: str, nome: str) -> str | None:
    """Busca ativo existente por client_id + nome (Tag na planilha)."""
    if df.empty or "Client_Id" not in df.columns:
        return None
    mask = (
        df["Client_Id"].astype(str).str.strip().str.lower() == client_id.lower()
    )
    if "Tag" in df.columns:
        mask &= df["Tag"].astype(str).str.strip() == nome
    elif "Nome" in df.columns:
        mask &= df["Nome"].astype(str).str.strip() == nome
    row = df[mask]
    if row.empty:
        return None
    return str(row.iloc[0]["Id"]).strip()


def _email_exists(email: str) -> bool:
    from sheets import verificar_email
    existe, _, _ = verificar_email(email)
    return existe


def _df_exists(df, col: str, value: str, extra_col: str = "", extra_val: str = "") -> str | None:
    """Procura linha por col=value (e extra_col=extra_val) e retorna Id ou None."""
    if df.empty or col not in df.columns or "Id" not in df.columns:
        return None
    mask = df[col].astype(str).str.strip() == value
    if extra_col and extra_col in df.columns:
        mask &= df[extra_col].astype(str).str.strip().str.lower() == extra_val.lower()
    row = df[mask]
    return str(row.iloc[0]["Id"]).strip() if not row.empty else None


# ─── STEPS DE SETUP ──────────────────────────────────────────────────────────

def _step_usuarios(log: list) -> None:
    from sheets import cadastrar_usuario

    usuarios = [
        (EMPRESA_A, EMAIL_A,     TELEFONE_A,   "cliente",     "João Teste"),
        (EMPRESA_B, EMAIL_B,     TELEFONE_B,   "cliente",     "Maria Teste B"),
        ("Pred.IO",  EMAIL_STAFF, "11900000003","funcionario", "Supervisor Teste"),
    ]
    for empresa, email, tel, perfil, nome in usuarios:
        if _email_exists(email):
            log.append(("✓", f"Usuário já existe: {email}"))
        else:
            ok = cadastrar_usuario(empresa, email, tel, perfil, nome, "")
            if ok:
                log.append(("✚", f"Usuário criado: {email} ({perfil})"))
            else:
                log.append(("✗", f"Erro ao criar usuário: {email}"))


def _step_ativos(log: list) -> dict:
    """Retorna dict {_tag_id: ativo_id}."""
    import sheets
    ids = {}
    df = sheets.load_sheet("Ativos")

    todos = ATIVOS_A + [ATIVO_B]
    for ativo in todos:
        tag_id = ativo["_tag_id"]
        nome   = ativo["nome"]
        cid    = ativo["client_id"]
        aid    = _find_ativo_id(df, cid, nome)
        if aid:
            ids[tag_id] = aid
            log.append(("✓", f"Ativo já existe: {nome} (id={aid})"))
        else:
            dados = {k: v for k, v in ativo.items() if not k.startswith("_")}
            aid = sheets.cadastrar_ativo_sv(dados)
            if aid:
                ids[tag_id] = aid
                log.append(("✚", f"Ativo criado: {nome} (id={aid})"))
                df = sheets.load_sheet("Ativos")  # recarrega para próximas buscas
            else:
                log.append(("✗", f"Erro ao criar ativo: {nome}"))
    return ids


def _step_documento(log: list, ativo_ids: dict) -> None:
    import sheets
    df = sheets.load_sheet("BibliotecaTecnica")
    titulo = "Manual de Operação MYCOM Q63"
    aid    = ativo_ids.get("MYCOM-Q63-01", "")
    eid = _df_exists(df, "Titulo", titulo, "Cliente_Id", CLIENT_ID_A)
    if eid:
        log.append(("✓", f"Documento já existe: {titulo}"))
    else:
        doc_id = sheets.add_documento_tecnico({
            "titulo":             titulo,
            "tipo_documento":     "Manual do Fabricante",
            "cliente_id":         CLIENT_ID_A,
            "ativo_id":           aid,
            "fabricante":         "MYCOM",
            "modelo":             "Q63",
            "arquivo_nome":       "manual_mycom_q63.pdf",
            "arquivo_url":        "",
            "resumo":             "Manual completo de operação e manutenção do compressor MYCOM Q63. Inclui procedimentos de partida, parada, lubrificação e troubleshooting.",
            "palavras_chave":     "mycom q63 compressor operação manutenção lubrificação",
            "visibilidade":       "Vinculado a cliente específico",
            "status":             "Ativo",
            "observacoes_internas": "Documento de homologação. URL simulada (PDF real pendente).",
        })
        if doc_id:
            log.append(("✚", f"Documento criado: {titulo} (id={doc_id})"))
        else:
            log.append(("✗", f"Erro ao criar documento: {titulo}"))


def _step_relatorios(log: list, ativo_ids: dict) -> dict:
    """Cria 3 relatórios publicados + 1 rascunho. Retorna {titulo_curto: rep_id}."""
    import sheets
    df  = sheets.load_sheet("TechnicalReports")
    ids = {}

    relatorios = [
        {
            "_key": "vibr",
            "cliente_id":    CLIENT_ID_A,
            "ativo_id":      ativo_ids.get("MYCOM-Q63-01", ""),
            "titulo":        "Análise de Vibração — MYCOM Compressor Q63",
            "tipo_servico":  "Análise de Vibração",
            "severidade":    "Crítica",
            "data_relatorio": "15/06/2026",
            "planta":        "Planta Principal",
            "equipamento":   "MYCOM Compressor Q63",
            "resumo":        "Levantamento de vibração identificou elevação nos níveis de vibração no sentido radial do rolamento dianteiro. Espectro apresenta componente de frequência característica de defeito externo de rolamento.",
            "recomendacoes": "1. Substituir rolamento SKF 6312 no prazo de 30 dias.\n2. Verificar alinhamento eixo-motor.\n3. Realizar nova análise após intervenção.",
            "obs_interna":   "Cliente já foi comunicado informalmente. Aguardar aprovação de orçamento.",
            "publicar":      True,
        },
        {
            "_key": "oleo",
            "cliente_id":    CLIENT_ID_A,
            "ativo_id":      ativo_ids.get("MTR-75KW-01", ""),
            "titulo":        "Análise de Óleo — Motor Principal 75kW",
            "tipo_servico":  "Análise de Óleo",
            "severidade":    "Alta",
            "data_relatorio": "10/06/2026",
            "planta":        "Planta Principal",
            "equipamento":   "Motor Principal WEG W22 75kW",
            "resumo":        "Análise de óleo lubrificante indicou contaminação por partículas metálicas de ferro acima do limite aceitável (85 ppm). Viscosidade dentro da faixa nominal.",
            "recomendacoes": "1. Realizar troca de óleo imediatamente.\n2. Inspecionar mancais quanto a desgaste.\n3. Coletar nova amostra em 30 dias.",
            "obs_interna":   "Enviar laudo do laboratório assim que disponível.",
            "publicar":      True,
        },
        {
            "_key": "prev",
            "cliente_id":    CLIENT_ID_A,
            "ativo_id":      ativo_ids.get("BBA-OL-01", ""),
            "titulo":        "Relatório de Manutenção Preventiva — Bomba de Óleo",
            "tipo_servico":  "Manutenção Preventiva",
            "severidade":    "Normal",
            "data_relatorio": "05/06/2026",
            "planta":        "Planta Principal",
            "equipamento":   "Bomba de Óleo Worthington 4x3",
            "resumo":        "Manutenção preventiva realizada conforme cronograma. Verificação de vedações, alinhamento, aperto de parafusos e limpeza de filtros. Equipamento em boas condições de operação.",
            "recomendacoes": "Continuar monitoramento periódico. Próxima preventiva em 3 meses.",
            "obs_interna":   "Relatório de rotina. Sem intercorrências.",
            "publicar":      True,
        },
        {
            "_key": "rascunho",
            "cliente_id":    CLIENT_ID_A,
            "ativo_id":      ativo_ids.get("MTR-75KW-01", ""),
            "titulo":        "Análise Elétrica Completa — Motor Principal [RASCUNHO]",
            "tipo_servico":  "Análise Elétrica",
            "severidade":    "Alta",
            "data_relatorio": "22/06/2026",
            "planta":        "Planta Principal",
            "equipamento":   "Motor Principal WEG W22 75kW",
            "resumo":        "Rascunho em elaboração. Análise elétrica completa com medição de correntes, tensões e fator de potência.",
            "recomendacoes": "Em elaboração.",
            "obs_interna":   "RASCUNHO — NÃO PUBLICAR ATÉ REVISÃO DO ENGENHEIRO.",
            "publicar":      False,  # deve ser INVISÍVEL ao cliente
        },
    ]

    for r in relatorios:
        key   = r.pop("_key")
        pub   = r.pop("publicar")
        titulo = r["titulo"]

        # Busca por título + cliente
        existing = None
        if not df.empty and "Titulo" in df.columns and "Cliente_Id" in df.columns:
            mask = (
                df["Titulo"].astype(str).str.strip() == titulo
            ) & (
                df["Cliente_Id"].astype(str).str.strip().str.lower() == CLIENT_ID_A
            )
            row = df[mask]
            if not row.empty:
                existing = str(row.iloc[0]["Id"]).strip()

        if existing:
            ids[key] = existing
            log.append(("✓", f"Relatório já existe: «{titulo[:50]}»"))
        else:
            rep_id = sheets.add_technical_report(r, created_by=EMAIL_STAFF)
            if rep_id:
                if pub:
                    sheets.update_technical_report(rep_id, {"Status": "Publicado"})
                ids[key] = rep_id
                status_label = "Publicado" if pub else "Rascunho"
                log.append(("✚", f"Relatório criado ({status_label}): «{titulo[:50]}»"))
                df = sheets.load_sheet("TechnicalReports")
            else:
                log.append(("✗", f"Erro ao criar relatório: {titulo[:50]}"))

    return ids


def _step_manutencao(log: list, ativo_ids: dict) -> None:
    import sheets
    df_plans = sheets.load_sheet("MaintenancePlans")
    plan_nome = "Plano de Manutenção — Pred.IO Teste"

    # Busca plano existente
    plan_id = None
    if not df_plans.empty and "Nome" in df_plans.columns and "Cliente_Id" in df_plans.columns:
        mask = (
            df_plans["Nome"].astype(str).str.strip() == plan_nome
        ) & (
            df_plans["Cliente_Id"].astype(str).str.strip().str.lower() == CLIENT_ID_A
        )
        row = df_plans[mask]
        if not row.empty:
            plan_id = str(row.iloc[0]["Id"]).strip()

    if plan_id:
        log.append(("✓", f"Plano já existe: {plan_nome} (id={plan_id})"))
    else:
        plan_id = sheets.add_maintenance_plan({
            "cliente_id": CLIENT_ID_A,
            "ativo_id":   ativo_ids.get("MYCOM-Q63-01", ""),
            "nome":       plan_nome,
            "descricao":  "Plano de manutenção gerado para homologação do Portal Pred.IO.",
            "status":     "Ativo",
        }, created_by=EMAIL_STAFF)
        if plan_id:
            log.append(("✚", f"Plano criado: {plan_nome} (id={plan_id})"))
        else:
            log.append(("✗", "Erro ao criar plano de manutenção"))
            return

    # Tarefas
    tarefas = [
        {
            "nome_tarefa":          "Troca de Filtro de Óleo",
            "ativo_id":             ativo_ids.get("MYCOM-Q63-01", ""),
            "tipo_manutencao":      "Calendário",
            "categoria":            "Lubrificação",
            "periodicidade_dias":   90,
            "ultima_execucao_data": "01/04/2026",
            "proxima_execucao_data":"30/06/2026",
            "status":               "Próximo",
            "prioridade":           "Alta",
            "descricao":            "Substituição de filtro de óleo lubrificante MYCOM PAO.",
            "obs_interna":          "Usar filtro OEM — código MYC-F-001.",
        },
        {
            "nome_tarefa":          "Revisão de Correias e Acoplamentos",
            "ativo_id":             ativo_ids.get("MYCOM-Q63-01", ""),
            "tipo_manutencao":      "Calendário",
            "categoria":            "Revisão Geral",
            "periodicidade_dias":   180,
            "ultima_execucao_data": "15/01/2026",
            "proxima_execucao_data":"15/09/2026",
            "status":               "Em dia",
            "prioridade":           "Média",
            "descricao":            "Verificação e tensionamento de correias, inspeção de acoplamentos.",
            "obs_interna":          "",
        },
        {
            "nome_tarefa":          "Inspeção de Rolamentos",
            "ativo_id":             ativo_ids.get("MTR-75KW-01", ""),
            "tipo_manutencao":      "Horímetro",
            "categoria":            "Inspeção",
            "periodicidade_horas":  5000,
            "ultima_execucao_horimetro": 6000,
            "proxima_execucao_horimetro": 11000,
            "status":               "Próximo",
            "prioridade":           "Alta",
            "descricao":            "Análise de vibração e temperatura em mancais. Verificar folgas.",
            "obs_interna":          "Horímetro atual: 8750h. Faltam ~2250h.",
        },
        {
            "nome_tarefa":          "Troca de Óleo Lubrificante",
            "ativo_id":             ativo_ids.get("BBA-OL-01", ""),
            "tipo_manutencao":      "Horímetro",
            "categoria":            "Lubrificação",
            "periodicidade_horas":  2000,
            "ultima_execucao_horimetro": 1000,
            "proxima_execucao_horimetro": 3000,
            "status":               "Próximo",
            "prioridade":           "Média",
            "descricao":            "Troca de óleo lubrificante MYCOLD PAO 68.",
            "obs_interna":          "Horímetro atual: 3200h — já venceu. Agendar com urgência.",
        },
        {
            "nome_tarefa":          "Análise por Condição — Temperatura",
            "ativo_id":             ativo_ids.get("MYCOM-Q63-01", ""),
            "tipo_manutencao":      "Condição",
            "categoria":            "Preditiva",
            "descricao":            "Monitoramento contínuo de temperatura de descarga. Intervenção quando T > 85°C.",
            "obs_interna":          "Sensor instalado — leitura manual semanalmente.",
        },
        {
            "nome_tarefa":          "Análise por Condição — Vibração",
            "ativo_id":             ativo_ids.get("MTR-75KW-01", ""),
            "tipo_manutencao":      "Condição",
            "categoria":            "Preditiva",
            "descricao":            "Levantamento de espectro de vibração. Intervenção quando v > 4,5 mm/s RMS.",
            "obs_interna":          "Última leitura: 4,2 mm/s. Monitorar a cada 2 semanas.",
        },
    ]

    df_tasks = sheets.load_sheet("MaintenanceTasks")
    for tarefa in tarefas:
        nome_t = tarefa["nome_tarefa"]
        # Idempotência: buscar por nome + cliente + plano
        existing = None
        if not df_tasks.empty and "Nome_Tarefa" in df_tasks.columns:
            mask = (
                df_tasks["Nome_Tarefa"].astype(str).str.strip() == nome_t
            ) & (
                df_tasks["Cliente_Id"].astype(str).str.strip().str.lower() == CLIENT_ID_A
            )
            row = df_tasks[mask]
            if not row.empty:
                existing = str(row.iloc[0]["Id"]).strip()

        if existing:
            log.append(("✓", f"Tarefa já existe: {nome_t}"))
        else:
            dados = {
                "cliente_id": CLIENT_ID_A,
                "plano_id":   plan_id,
                "origem":     "Homologação Pred.IO",
                **{k: v for k, v in tarefa.items()},
            }
            task_id = sheets.add_maintenance_task(dados, created_by=EMAIL_STAFF)
            if task_id:
                log.append(("✚", f"Tarefa criada: {nome_t} (id={task_id})"))
            else:
                log.append(("✗", f"Erro ao criar tarefa: {nome_t}"))


def _step_alertas(log: list, ativo_ids: dict) -> dict:
    """Cria 3 alertas. Retorna {chave: alerta_id}."""
    import sheets
    df  = sheets.load_sheet("AlertasSV")
    ids = {}

    alertas = [
        {
            "_key":      "temp",
            "client_id": CLIENT_ID_A,
            "empresa":   EMPRESA_A,
            "titulo":    "Alta Temperatura de Descarga — MYCOM Q63",
            "descricao": "Temperatura de descarga registrada em 92°C (limite: 85°C). Necessária intervenção imediata para evitar dano ao compressor.",
            "prioridade":"Crítica",
        },
        {
            "_key":      "vibr",
            "client_id": CLIENT_ID_A,
            "empresa":   EMPRESA_A,
            "titulo":    "Vibração Elevada — Motor Principal 75kW",
            "descricao": "Nível de vibração global atingiu 4,2 mm/s RMS. Monitorar proximamente. Intervenção quando ultrapassar 4,5 mm/s.",
            "prioridade":"Alta",
        },
        {
            "_key":      "oleo",
            "client_id": CLIENT_ID_A,
            "empresa":   EMPRESA_A,
            "titulo":    "Nível de Óleo Baixo — Bomba de Óleo Industrial",
            "descricao": "Nível de óleo lubrificante abaixo do mínimo recomendado. Completar imediatamente com MYCOLD PAO 68.",
            "prioridade":"Média",
        },
    ]

    for alerta in alertas:
        key    = alerta.pop("_key")
        titulo = alerta["titulo"]
        existing = None
        if not df.empty and "Titulo" in df.columns and "Client_Id" in df.columns:
            mask = (
                df["Titulo"].astype(str).str.strip() == titulo
            ) & (
                df["Client_Id"].astype(str).str.strip().str.lower() == CLIENT_ID_A
            )
            row = df[mask]
            if not row.empty:
                existing = str(row.iloc[0]["Id"]).strip()

        if existing:
            ids[key] = existing
            log.append(("✓", f"Alerta já existe: {titulo[:60]}"))
        else:
            ok = sheets.add_alerta_sv(**alerta)
            if ok:
                log.append(("✚", f"Alerta criado: {titulo[:60]}"))
                df = sheets.load_sheet("AlertasSV")
                # Reler para pegar o id recém-criado
                row2 = df[
                    df["Titulo"].astype(str).str.strip() == titulo
                ] if not df.empty and "Titulo" in df.columns else None
                if row2 is not None and not row2.empty:
                    ids[key] = str(row2.iloc[0]["Id"]).strip()
            else:
                log.append(("✗", f"Erro ao criar alerta: {titulo[:60]}"))

    return ids


def _step_chamado(log: list, ativo_ids: dict) -> str | None:
    """Cria chamado de teste com resposta visível + observação interna."""
    import sheets
    df = sheets.load_sheet("Chamados")
    titulo = "Ruído Incomum no Compressor MYCOM Q63"

    existing = None
    if not df.empty and "Titulo" in df.columns and "Client_Id" in df.columns:
        mask = (
            df["Titulo"].astype(str).str.strip() == titulo
        ) & (
            df["Client_Id"].astype(str).str.strip().str.lower() == CLIENT_ID_A
        )
        row = df[mask]
        if not row.empty:
            existing = str(row.iloc[0]["Id"]).strip()

    if existing:
        log.append(("✓", f"Chamado já existe: {titulo} (id={existing})"))
        return existing

    ch_id = sheets.abrir_chamado_v2({
        "client_id":   CLIENT_ID_A,
        "empresa":     EMPRESA_A,
        "email":       EMAIL_A,
        "ativo_id":    ativo_ids.get("MYCOM-Q63-01", ""),
        "titulo":      titulo,
        "descricao":   "Olá equipe Pred.IO! Estamos percebendo um ruído metálico incomum no compressor MYCOM Q63, principalmente durante a partida e nos primeiros minutos de operação. O equipamento está funcionando mas o ruído preocupa a equipe. Poderiam verificar?",
        "categoria":   "Falha em equipamento",
        "prioridade":  "Alta",
        "origem":      "Portal do Cliente",
        "planta":      "Planta Principal",
        "equipamento": "MYCOM Compressor Q63",
    })

    if not ch_id:
        log.append(("✗", f"Erro ao criar chamado: {titulo}"))
        return None

    log.append(("✚", f"Chamado criado: {titulo} (id={ch_id})"))

    # Mensagem visível ao cliente (resposta da equipe)
    sheets.add_mensagem(
        ch_id,
        autor="Supervisor Pred.IO",
        autor_tipo="staff",
        mensagem="Olá João! Recebemos seu chamado e já iniciamos a análise. O ruído metálico descrito pode indicar desgaste de rolamento ou folga em pistão. Nossa equipe realizará uma inspeção técnica em campo. Envie-nos os dados de horímetro atual e a temperatura de descarga registrada. Ficamos à disposição!",
        visivel_cliente=True,
        tipo_mensagem="resposta",
    )
    log.append(("✚", "  → Resposta visível ao cliente adicionada"))

    # Observação interna (NÃO aparece ao cliente)
    sheets.add_mensagem(
        ch_id,
        autor="Supervisor Pred.IO",
        autor_tipo="staff",
        mensagem="OBSERVAÇÃO INTERNA: Suspeita de desgaste no pistão ou falha de rolamento SKF 6312. Preparar kit de reposição antes da visita. Verificar histórico de lubrificação — possível contaminação por partículas metálicas. NÃO compartilhar com cliente até confirmação.",
        visivel_cliente=False,
        tipo_mensagem="observacao_interna",
    )
    log.append(("✚", "  → Observação interna adicionada (invisível ao cliente)"))

    # Atualizar status do chamado para "Em atendimento"
    sheets.update_chamado(ch_id, {"Status": "Em atendimento"})

    return ch_id


def _step_notificacoes(log: list, ativo_ids: dict, report_ids: dict, chamado_id: str | None) -> None:
    import sheets
    df = sheets.load_sheet("NotificacoesPortal")

    notificacoes = [
        {
            "titulo":      "Novo relatório disponível: Análise de Vibração",
            "mensagem":    "O relatório «Análise de Vibração — MYCOM Compressor Q63» foi publicado pela equipe Pred.IO. Clique para visualizar.",
            "tipo_evento": "relatorio_publicado",
            "prioridade":  "Alta",
            "link_page":   "relatorios",
            "link_id":     report_ids.get("vibr", ""),
            "report_id":   report_ids.get("vibr", ""),
        },
        {
            "titulo":      "Seu chamado foi respondido",
            "mensagem":    "A equipe Pred.IO respondeu ao chamado «Ruído Incomum no Compressor MYCOM Q63». Acesse para ver a resposta.",
            "tipo_evento": "chamado_respondido",
            "prioridade":  "Média",
            "link_page":   "chamados",
            "link_id":     chamado_id or "",
            "ticket_id":   chamado_id or "",
        },
        {
            "titulo":      "Manutenção próxima: Troca de Filtro de Óleo",
            "mensagem":    "A tarefa «Troca de Filtro de Óleo» vence em 30/06/2026. Programe a intervenção com antecedência.",
            "tipo_evento": "manutencao_proxima",
            "prioridade":  "Alta",
            "link_page":   "manutencao",
            "link_id":     "",
            "ativo_id":    ativo_ids.get("MYCOM-Q63-01", ""),
        },
        {
            "titulo":      "Alerta Crítico: Alta Temperatura — MYCOM Q63",
            "mensagem":    "Temperatura de descarga do MYCOM Compressor Q63 registrou 92°C (limite: 85°C). Atenção imediata recomendada.",
            "tipo_evento": "alerta_critico",
            "prioridade":  "Crítica",
            "link_page":   "alertas",
            "link_id":     "",
            "ativo_id":    ativo_ids.get("MYCOM-Q63-01", ""),
        },
        {
            "titulo":      "Nova recomendação técnica disponível",
            "mensagem":    "Pred.IO identificou uma recomendação técnica para o ativo MYCOM Compressor Q63 baseada nas últimas leituras preditivas.",
            "tipo_evento": "recomendacao_por_condicao",
            "prioridade":  "Média",
            "link_page":   "ativos",
            "link_id":     ativo_ids.get("MYCOM-Q63-01", ""),
            "ativo_id":    ativo_ids.get("MYCOM-Q63-01", ""),
        },
    ]

    for n in notificacoes:
        titulo = n["titulo"]
        existing = False
        if not df.empty and "Titulo" in df.columns and "Cliente_Id" in df.columns:
            mask = (
                df["Titulo"].astype(str).str.strip() == titulo
            ) & (
                df["Cliente_Id"].astype(str).str.strip().str.lower() == CLIENT_ID_A
            )
            existing = not df[mask].empty

        if existing:
            log.append(("✓", f"Notificação já existe: {titulo[:60]}"))
        else:
            nid = sheets.add_portal_notification({
                "cliente_id": CLIENT_ID_A,
                **n,
            })
            if nid:
                log.append(("✚", f"Notificação criada: {titulo[:60]} (id={nid})"))
            else:
                log.append(("✗", f"Erro ao criar notificação: {titulo[:60]}"))


def _step_ativo_b(log: list) -> None:
    """Garante que cliente B tem pelo menos um ativo (para teste de isolamento)."""
    import sheets
    df = sheets.load_sheet("Ativos")
    aid = _find_ativo_id(df, CLIENT_ID_B, ATIVO_B["nome"])
    if aid:
        log.append(("✓", f"Ativo B já existe: {ATIVO_B['nome']} (id={aid})"))
    else:
        dados = {k: v for k, v in ATIVO_B.items() if not k.startswith("_")}
        aid = sheets.cadastrar_ativo_sv(dados)
        if aid:
            log.append(("✚", f"Ativo B criado: {ATIVO_B['nome']} (id={aid})"))
        else:
            log.append(("✗", f"Erro ao criar ativo B: {ATIVO_B['nome']}"))


# ─── FUNÇÃO PRINCIPAL ────────────────────────────────────────────────────────

def run_setup() -> list[tuple[str, str]]:
    """
    Executa setup completo de dados de homologação.
    Retorna lista de (status_emoji, mensagem).
    Idempotente — verifica antes de criar.
    """
    log: list[tuple[str, str]] = []
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    log.append(("ℹ", f"Iniciando setup — {now}"))

    try:
        log.append(("ℹ", "1. Usuários de teste"))
        _step_usuarios(log)

        log.append(("ℹ", "2. Ativos — Cliente A"))
        ativo_ids = _step_ativos(log)

        log.append(("ℹ", "3. Ativo — Cliente B (isolamento)"))
        _step_ativo_b(log)

        log.append(("ℹ", "4. Documento Técnico"))
        _step_documento(log, ativo_ids)

        log.append(("ℹ", "5. Relatórios (3 publicados + 1 rascunho)"))
        report_ids = _step_relatorios(log, ativo_ids)

        log.append(("ℹ", "6. Plano de Manutenção + 6 Tarefas"))
        _step_manutencao(log, ativo_ids)

        log.append(("ℹ", "7. Alertas"))
        alerta_ids = _step_alertas(log, ativo_ids)

        log.append(("ℹ", "8. Chamado + Mensagens"))
        chamado_id = _step_chamado(log, ativo_ids)

        log.append(("ℹ", "9. Notificações do Portal"))
        _step_notificacoes(log, ativo_ids, report_ids, chamado_id)

        log.append(("ℹ", "─" * 40))
        log.append(("✓", f"Setup concluído em {datetime.now().strftime('%H:%M:%S')}"))
        log.append(("ℹ", f"Cliente A: {EMPRESA_A} (login: {EMAIL_A})"))
        log.append(("ℹ", f"Cliente B: {EMPRESA_B} (login: {EMAIL_B})"))
        log.append(("ℹ", "Senha: deixada em branco → Primeiro Acesso ao logar"))

    except Exception as exc:
        log.append(("✗", f"Erro inesperado: {exc}"))

    return log


# ─── CHECKLIST ───────────────────────────────────────────────────────────────

CHECKLIST_ITEMS = [
    (1,  "Login cliente",              "Consegue entrar com e-mail e senha. Redirecionado para dashboard."),
    (2,  "Dashboard cliente",          "Dashboard exibe KPIs, 3 ativos e sem dados de outro cliente."),
    (3,  "Ativos",                     "Lista os 3 ativos de Cliente A. Não exibe ativo de Cliente B."),
    (4,  "Detalhe do ativo",           "Abre detalhe mostrando score, criticidade, histórico e componentes."),
    (5,  "Relatórios publicados",      "Exibe os 3 relatórios publicados com conteúdo correto."),
    (6,  "Relatório rascunho oculto",  "O relatório em rascunho NÃO aparece na lista do cliente."),
    (7,  "Plano de manutenção",        "Exibe as 6 tarefas com tipos Calendário, Horímetro e Condição."),
    (8,  "Tarefas por condição",       "Tarefas Condição exibem status «Depende de análise preditiva»."),
    (9,  "Alertas",                    "Exibe os 3 alertas com prioridades e descrições corretas."),
    (10, "Chamados",                   "Exibe chamado de teste com status «Em atendimento»."),
    (11, "Observações internas ocultas","A observação interna do chamado NÃO aparece ao cliente."),
    (12, "Biblioteca Técnica",         "Exibe o documento «Manual de Operação MYCOM Q63»."),
    (13, "Documento indexado",         "Documento abre e exibe resumo e palavras-chave."),
    (14, "Assistente Técnico",         "Responde às 10 perguntas de homologação com coerência."),
    (15, "Fonte Pred.IO",              "Assistente cita apenas «Pred.IO» como fonte — nunca IA ou Claude."),
    (16, "Segurança client_id",        "Cliente B não acessa dados do Cliente A (testado via URL/sessão)."),
    (17, "Notificações internas",      "5 notificações aparecem no sino. Badge exibe contador correto."),
    (18, "PWA / Mobile",               "App instalável no celular. Bottom nav funciona. Sem sidebar."),
    (19, "Supervisão Pred.IO",         "Supervisor vê dados de ambos os clientes sem interferência."),
    (20, "Auditoria do Assistente",    "Supervisor consegue auditar perguntas e respostas do assistente."),
]
