"""
Motor de busca controlada — Assistente Técnico Pred.IO.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENDPOINT FUTURO (preparado, ainda não exposto via HTTP):

  POST /api/assistant/technical-query
  Headers: Authorization: Bearer <token_sessao>
  Payload: {
    "pergunta":       str,
    "rota_atual":     str  (opcional),
    "ativo_id":       str  (opcional),
    "componente_id":  str  (opcional)
  }
  Resposta: {
    "answer":            str,
    "related_links":     [{"label": str, "page": str}],
    "related_documents": [{"titulo": str, "id": str}],
    "related_reports":   [{"titulo": str, "data": str}],
    "suggested_actions": [{"label": str, "page": str}]
  }

FLUXO FUTURO COM IA:
  Cliente pergunta → API recebe → obtém client_id da SESSÃO
  → busca dados autorizados → IA responde usando apenas essas fontes
  → Portal exibe resposta + fontes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEGURANÇA OBRIGATÓRIA:
  ✓ client_id SEMPRE vem da sessão/autenticação do servidor
  ✓ Nunca aceitar client_id livre do front-end
  ✓ Dados retornados filtrados por client_id antes de qualquer resposta
  ✓ Documentos internos da Pred.IO nunca aparecem para clientes
  ✓ Observações internas nunca são retornadas
  ✓ Supervisão Pred.IO não aparece no portal do cliente
  ✓ Nenhuma resposta inventa especificação técnica sem fonte cadastrada
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

# ── Mapa de intenções ────────────────────────────────────────────────────────

_INTENTS: dict[str, list[str]] = {
    # MYCOLD AB 68 / PAO — verificar antes de qualquer outra intent de óleo
    "mycold": [
        "mycold", "mycold ab", "mycold pao", "mycold ab 68",
        "oleo mycom", "óleo mycom",
    ],
    # Óleos homologados MAYEKAWA/MYCOM (tabela)
    "oleo_homologado": [
        "óleo homologado", "oleo homologado", "homologado", "homologados",
        "tabela de oleo", "tabela de óleo", "tabela de oleos", "tabela de óleos",
        "reflo", "rab 68", "r 200", "gargoyle", "esso refrigeration",
        "eal arctic", "icematic", "capella hfc", "capella 68",
        "pao", "poe", "polialfaolefina", "poliolester",
        "oleo para r134a", "óleo para r134a", "oleo para r404a",
        "oleo para amonia", "óleo para amônia", "oleo para nh3",
        "pode usar qualquer oleo", "pode usar qualquer óleo",
        "qual oleo usar", "qual óleo usar",
    ],
    # Manual MYCOM / Sistema Chiller
    "mycom_manual": [
        "mycom", "chiller", "sistema chiller",
        "fluxostato", "soft-starter", "inversor de frequencia", "inversor de frequência",
        "condensador a placa", "trocador a placa",
        "pressao de descarga", "pressão de descarga",
        "pressao de succao", "pressão de sucção",
        "pressao de oleo", "pressão de óleo",
        "temperatura de descarga", "temperatura do selo",
        "painel eletrico", "painel elétrico",
        "filtro coalescente", "filtro de succao", "filtro de sucção",
        "alinhamento motor", "alinhamento eixo",
        "inspeção diária", "inspecao diaria",
        "inspeção semanal", "inspecao semanal",
        "inspeção mensal", "inspecao mensal",
        "inspeção trimestral", "inspecao trimestral",
        "inspeção semestral", "inspecao semestral",
        "inspeção anual", "inspecao anual",
        "5000 horas", "5.000 horas", "10000 horas", "10.000 horas",
        "psv", "pressostato", "termostato",
        "quando trocar filtro", "quando trocar oleo",
        "quando conferir alinhamento",
        "analise de oleo", "análise de óleo",
        "coletar amostra", "amostra de oleo",
        "quando fazer analise", "quando devo fazer analise",
        "oleo o manual", "oleo que o manual", "oleo cita",
        "qual oleo o manual", "oleo do manual",
        "compressor parafuso", "compressor alternativo",
        "diferenca entre compressor", "tipo de compressor",
        "o que e uma unidade", "unidade compressora",
        "dados importantes para avaliar",
        "temperatura para parafuso", "temperatura para alternativo",
        "temperatura normal de descarga", "temperatura de descarga normal",
        "parafuso com descarga", "alternativo com descarga",
        "descarga normal", "o que pode causar descarga",
        "pressão de descarga alta", "pressao de descarga alta",
        "pressão de descarga baixa", "pressao de descarga baixa",
        "pressão de sucção alta", "pressao de succao alta",
        "pressão de sucção baixa", "pressao de succao baixa",
        "descarga alta o que", "descarga baixa o que",
        "pressão de óleo baixa é", "pressao de oleo baixa",
        "o que verificar quando pressao", "verificar pressao de oleo",
    ],
    # 20.000 horas / overhaul / kit revisão — resposta obrigatória por condição
    "revisao_condicao": [
        "20000 horas", "20.000 horas", "20 000 horas", "bienal",
        "desmontagem", "desmontar compressor", "desmontar o compressor",
        "kit revisão", "kit revisao", "revisão geral", "revisao geral",
        "overhaul", "preciso revisar", "preciso fazer overhaul",
        "preciso trocar kit", "hora de revisar", "hora do overhaul",
        "quando fazer overhaul", "quando fazer revisao",
    ],
    "manutencao": [
        "manutenção", "manutencao", "próxima", "proxima", "plano", "vencimento",
        "horímetro", "horimetro", "análise de óleo", "analise de oleo",
        "vibração", "vibracao", "termografia", "preventiva", "preditiva",
        "inspeção", "inspecao", "lubrificação", "lubrificacao",
        "filtro", "próximas ações", "proximas acoes",
        "como vibração ajuda", "como vibracao ajuda",
        "como analise de oleo ajuda", "como análise de óleo ajuda",
        "como termografia ajuda", "termografia ajuda compressor",
        "vibração ajuda", "vibracao ajuda", "analise de oleo ajuda",
        "como reduzir risco", "reduzir risco de falha",
        "o que fazer antes de intervencao", "antes de intervencao",
    ],
    "relatorio_executivo": [
        "relatório executivo", "relatorio executivo", "resumo executivo",
        "relatório de confiabilidade", "relatorio de confiabilidade",
        "histórico do ativo", "historico do ativo",
        "principais pontos", "principais achados",
        "manutenções realizadas", "manutencoes realizadas",
        "manutenções pendentes", "manutencoes pendentes",
        "indicação de overhaul", "indicacao de overhaul",
        "indicação de rolamento", "indicacao de rolamento",
        "recomendação por condição", "recomendacao por condicao",
        "existe relatório executivo", "existe relatorio executivo",
        "qual resumo do ativo", "qual resumo executivo",
    ],
    "relatorios": [
        "relatório", "relatorio", "laudo", "análise preditiva", "analise preditiva",
        "análise de vibração", "analise de vibracao", "resultado", "publicado",
        "relatórios", "relatorios",
    ],
    "documentos": [
        "manual", "datasheet", "documento", "especificação", "especificacao",
        "catálogo", "catalogo", "biblioteca", "pdf", "procedimento",
        "guia", "instrução", "instrucao", "ficha técnica", "ficha tecnica",
    ],
    "oleo": [
        "óleo", "oleo", "especificação de óleo", "especificacao de oleo",
        "óleo recomendado", "oleo recomendado",
        "tipo de óleo", "tipo de oleo",
        "viscosidade", "lubrificante recomendado", "iso 68", "iso vg 68",
    ],
    "status_ativo": [
        "status", "condição", "condicao", "saúde", "saude", "score",
        "crítico", "critico", "atenção", "atencao", "bomba de óleo",
        "bomba de oleo", "compressor", "motor", "ativo", "equipamento",
        "falha", "alarme", "sensor",
        "score de saude", "score de saúde", "score do ativo", "o que e score",
        "ativo em atencao", "ativo em atenção", "o que significa atencao",
        "ativo critico", "ativo crítico", "o que significa critico",
        "saude do ativo", "saúde do ativo",
    ],
    "chamados": [
        "chamado", "abrir chamado", "solicitação", "solicitacao",
        "atendimento", "suporte", "problema", "defeito",
        "solicitar", "técnico", "tecnico",
        "quando abrir chamado", "quando devo abrir chamado",
        "tenho chamados", "chamados abertos", "meus chamados",
        "status do chamado", "meu chamado", "qual status",
        "chamado foi respondido", "foi respondido", "responderam meu chamado",
        "tem chamado para esse ativo", "chamado para o ativo",
        "abrir solicitação", "abrir solicitacao",
        "quero abrir chamado", "preciso de suporte", "preciso de atendimento",
    ],
    "notificacoes_portal": [
        "notificações não lidas", "notificacoes nao lidas",
        "tenho notificações", "tenho notificacoes",
        "quantas notificações", "quantas notificacoes",
        "minhas notificações", "minhas notificacoes",
        "ativar notificação", "ativar notificacao",
        "configurar notificação", "configurar notificacao",
        "preferências de notificação", "preferencias de notificacao",
        "como ativo notificação", "como ativo notificacao",
        "como ativar notificação", "como ativar notificacao",
        "notificação de manutenção", "notificacao de manutencao",
        "notificação por email", "notificacao por email",
        "notificação por whatsapp", "notificacao por whatsapp",
        "recebi algum alerta", "recebi alerta hoje",
        "avisos não lidos", "avisos nao lidos",
    ],
    "alertas": [
        "alerta", "aviso", "notificação", "notificacao", "ponto de atenção",
        "ponto de atencao",
    ],
    # Painel Mypro Touch / Mypro Touch AD
    "mypro_touch": [
        "mypro touch", "mypro touch ad", "painel mypro",
        "login painel", "senha painel", "login mypro", "senha mypro",
        "level 1", "level 2", "nivel 1 painel", "nivel 2 painel",
        "como ligar o compressor", "como ligar compressor",
        "tecla partida", "como partir",
        "como parar o compressor", "como parar compressor",
        "tecla parar",
        "set point cut", "cut in", "cut out",
        "set point #1", "set point #2", "set point 1", "set point 2",
        "alterar set point", "mudar set point",
        "alterar capacidade manualmente", "capacidade manual",
        "limpar alarme", "reset alarme", "resetar alarme", "limpar falha",
        "alarme vermelho", "alarme azul", "falha vermelha",
        "estado do compressor", "condição atual",
        "onde vejo alarme", "onde ver alarme", "onde vejo falha",
        "o que registrar quando", "registrar quando falha",
        "alarme voltou", "alarme recorrente", "alarme varias vezes",
        "posso limpar alarme sem", "limpar sem resolver",
        "o que é mypro", "o que e mypro",
        "o que fazer quando falha painel",
    ],
    # Comunicação industrial e monitoramento remoto
    "comunicacao_monitoramento": [
        "modbus", "comunicacao ethernet", "comunicação ethernet",
        "expor painel", "painel na internet", "painel internet",
        "monitoramento online pode", "monitoramento pode comandar",
        "o monitoramento pode", "o monitoramento online",
        "portal pode buscar dados", "portal pode comandar",
        "quais dados o portal", "dados do portal deve buscar",
        "comando remoto", "partida remota", "parada remota",
        "buscar dados painel", "dados do painel mypro",
    ],
    # Perguntas meta sobre o próprio Assistente Técnico
    "meta_assistente": [
        "assistente pode decidir", "pode decidir parar",
        "assistente substitui", "o assistente substitui",
        "assistente executa", "assistente opera a",
        "assistente pode parar a",
    ],
}


def detect_intent(pergunta: str) -> str:
    """
    Identifica a intenção da pergunta.
    A ordem importa — intents mais específicos aparecem primeiro.
    """
    q = pergunta.lower()
    for intent in [
        "mycold",                    # MYCOLD AB/PAO — antes de qualquer oleo
        "oleo_homologado",           # Tabela de óleos MAYEKAWA/MYCOM
        "revisao_condicao",          # 20k horas / overhaul / kit revisão
        "mypro_touch",               # Painel Mypro Touch / Mypro Touch AD
        "comunicacao_monitoramento", # Modbus / Ethernet / monitoramento remoto
        "mycom_manual",              # Manual MYCOM / Sistema Chiller
        "meta_assistente",           # Perguntas meta sobre o Assistente
        "relatorio_executivo",       # Relatório Executivo de Confiabilidade publicado
        "oleo",                      # Óleo genérico
        "manutencao",                # Plano de manutenção
        "relatorios",
        "documentos",
        "status_ativo",
        "chamados",
        "notificacoes_portal",
        "alertas",
    ]:
        if any(kw in q for kw in _INTENTS[intent]):
            return intent
    return "nao_encontrado"


# ── Busca de contexto do cliente ─────────────────────────────────────────────

def get_client_context(client_id: str) -> dict:
    """
    Retorna dados autorizados do cliente para o assistente.

    SEGURANÇA: client_id SEMPRE vem da sessão do servidor. Nunca do front-end.
    Dados são filtrados por client_id — nenhum dado de outro cliente é retornado.

    Estratégia atual: tenta dados reais do Sheets; cai para mock estruturado.
    Futuramente: integrar com get_ativos(), get_manutencoes(), etc. do sheets.py

    NÃO INCLUI:
      - Documentos internos da Pred.IO
      - Observações internas de chamados
      - Dados de outros clientes
      - Dados da Supervisão Pred.IO
    """
    if not client_id:
        return _empty_context()

    from assistant_mock_data import get_mock_context
    ctx = get_mock_context(client_id)

    # Tenta carregar documentos reais do Sheets.
    # SEGURANÇA: client_id da sessão; get_documentos_tecnicos() filtra
    # documentos internos e de outros clientes antes de retornar.
    # Tenta carregar relatórios técnicos publicados do Sheets.
    # SEGURANÇA: staff=False → somente Status=Publicado do próprio cliente.
    try:
        from sheets import get_technical_reports
        df_rep = get_technical_reports(client_id=client_id, staff=False)
        if not df_rep.empty:
            reps = []
            for _, r in df_rep.iterrows():
                titulo  = str(r.get("Titulo",         "")).strip()
                data    = str(r.get("Data_Relatorio", "")).strip()
                tipo    = str(r.get("Tipo_Servico",   "")).strip()
                sev     = str(r.get("Severidade",     "")).strip()
                resumo  = str(r.get("Resumo",         "")).strip()
                recomen = str(r.get("Recomendacoes",  "")).strip()
                ativo   = str(r.get("Ativo_Id",       "")).strip()
                equip   = str(r.get("Equipamento",    "")).strip()
                if titulo:
                    reps.append({
                        "titulo":        titulo,
                        "data":          data,
                        "tipo":          tipo,
                        "severidade":    sev,
                        "resumo":        resumo,
                        "recomendacoes": recomen,
                        "ativo":         ativo or equip,
                    })
            if reps:
                ctx["relatorios"] = reps
    except Exception:
        pass

    # Carrega tarefas de manutenção reais (staff=False → sem obs_interna).
    # SEGURANÇA: client_id da sessão; filtra pelo cliente antes de retornar.
    try:
        from sheets import get_maintenance_tasks, calc_task_status, get_horimetro
        df_mt = get_maintenance_tasks(client_id=client_id, staff=False)
        if not df_mt.empty:
            tarefas = []
            for _, r in df_mt.iterrows():
                task     = r.to_dict()
                aid      = str(task.get("Ativo_Id", "")).strip()
                h_at     = 0
                if aid:
                    try:
                        h = get_horimetro(aid)
                        h_at = h if h is not None else 0
                    except Exception:
                        pass
                tipo   = str(task.get("Tipo_Manutencao", "")).strip()
                status = calc_task_status(task, h_at)
                tarefas.append({
                    "nome":        str(task.get("Nome_Tarefa", "")).strip(),
                    "tipo":        tipo,
                    "categoria":   str(task.get("Categoria", "")).strip(),
                    "prioridade":  str(task.get("Prioridade", "")).strip(),
                    "ativo_id":    aid,
                    "status":      status,
                    "prox_data":   str(task.get("Proxima_Execucao_Data", "")).strip(),
                    "prox_h":      str(task.get("Proxima_Execucao_Horimetro", "")).strip(),
                    "h_atual":     h_at,
                    "recomendacao": str(task.get("Recomendacao", "")).strip(),
                })
            if tarefas:
                ctx["tarefas_manutencao"] = tarefas
    except Exception:
        pass

    # Carrega chamados reais do cliente para o assistente.
    # SEGURANÇA: client_id da sessão; nunca mostra obs. internas.
    try:
        from sheets import get_chamados_resumo_assistente
        chamados_res = get_chamados_resumo_assistente(client_id=client_id)
        if chamados_res:
            ctx["chamados_reais"] = chamados_res
    except Exception:
        pass

    # Carrega relatórios executivos PUBLICADOS para o assistente.
    # SEGURANÇA: get_relatorios_executivos_publicados() filtra somente status=Publicado,
    # remove obs_interna, e filtra por client_id da sessão.
    try:
        from sheets import get_relatorios_executivos_publicados
        df_exec = get_relatorios_executivos_publicados(client_id)
        if not df_exec.empty:
            exec_reps = []
            for _, r in df_exec.iterrows():
                titulo    = str(r.get("Titulo",          "")).strip()
                periodo_i = str(r.get("Periodo_Inicio",  "")).strip()
                periodo_f = str(r.get("Periodo_Fim",     "")).strip()
                resumo_ex = str(r.get("Resumo_Executivo","")).strip()
                ativo_id  = str(r.get("Ativo_Id",        "")).strip()
                versao    = str(r.get("Versao",           "1")).strip()
                pub_em    = str(r.get("Publicado_Em",     "")).strip()
                if titulo:
                    exec_reps.append({
                        "titulo":           titulo,
                        "periodo":          f"{periodo_i} a {periodo_f}" if periodo_i else "",
                        "resumo_executivo": resumo_ex,
                        "ativo_id":         ativo_id,
                        "versao":           versao,
                        "publicado_em":     pub_em,
                        "fonte":            "Pred.IO",
                    })
            if exec_reps:
                ctx["relatorios_executivos"] = exec_reps
    except Exception:
        pass

    # Carrega alertas reais da supervisão para o assistente.
    # SEGURANÇA: client_id da sessão; filtra pelo cliente antes de retornar.
    try:
        from sheets import get_alertas_sv
        df_al = get_alertas_sv(client_id=client_id)
        if not df_al.empty:
            alertas_reais = []
            for _, r in df_al.iterrows():
                titulo    = str(r.get("Titulo",     "")).strip()
                descricao = str(r.get("Descricao",  "")).strip()
                prioridade= str(r.get("Prioridade", "")).strip()
                criado_em = str(r.get("Criado_Em",  "")).strip()
                if titulo:
                    alertas_reais.append({
                        "titulo":     titulo,
                        "descricao":  descricao,
                        "prioridade": prioridade,
                        "criado_em":  criado_em,
                    })
            if alertas_reais:
                ctx["alertas_reais"] = alertas_reais
    except Exception:
        pass

    # Carrega chunks de relatórios técnicos publicados.
    # Usa get_chunks_relatorio() por relatório já carregado em ctx["relatorios"].
    try:
        from sheets import get_chunks_relatorio, get_technical_reports
        df_rep_ids = get_technical_reports(client_id=client_id, staff=False)
        if not df_rep_ids.empty and "Id" in df_rep_ids.columns:
            reps_com_chunks = []
            for _, r in df_rep_ids.iterrows():
                rep_id  = str(r.get("Id",     "")).strip()
                titulo  = str(r.get("Titulo",  "")).strip()
                resumo  = str(r.get("Resumo",  "")).strip()
                recom   = str(r.get("Recomendacoes","")).strip()
                sev     = str(r.get("Severidade","")).strip()
                data    = str(r.get("Data_Relatorio","")).strip()
                ativo   = str(r.get("Ativo_Id", r.get("Equipamento",""))).strip()
                if not titulo:
                    continue
                entry = {
                    "id":            rep_id,
                    "titulo":        titulo,
                    "resumo":        resumo,
                    "recomendacoes": recom,
                    "severidade":    sev,
                    "data":          data,
                    "ativo":         ativo,
                    "chunks":        [],
                }
                if rep_id:
                    try:
                        df_chk = get_chunks_relatorio(rep_id, client_id=client_id)
                        if not df_chk.empty:
                            entry["chunks"] = [
                                {
                                    "chunk_index":  str(c.get("Chunk_Index", "")),
                                    "titulo_secao": str(c.get("Titulo_Secao", "")).strip(),
                                    "conteudo":     str(c.get("Conteudo",     "")).strip(),
                                }
                                for _, c in df_chk.iterrows()
                            ]
                    except Exception:
                        pass
                reps_com_chunks.append(entry)
            if reps_com_chunks:
                ctx["relatorios_tecnicos_indexados"] = reps_com_chunks
    except Exception:
        pass

    try:
        from sheets import get_documentos_tecnicos, get_chunks_documento
        df_docs = get_documentos_tecnicos(client_id=client_id, staff=False)
        if not df_docs.empty:
            docs = []
            for _, r in df_docs.iterrows():
                doc_id = str(r.get("Id", "")).strip()
                doc = {
                    "id":               doc_id,
                    "titulo":           str(r.get("Titulo",          "")).strip(),
                    "tipo_documento":   str(r.get("Tipo_Documento",  "")).strip(),
                    "fabricante":       str(r.get("Fabricante",      "")).strip(),
                    "modelo":           str(r.get("Modelo",          "")).strip(),
                    "ativo":            str(r.get("Ativo_Id",        "")).strip(),
                    "resumo":           str(r.get("Resumo",          "")).strip(),
                    "palavras_chave":   str(r.get("Palavras_Chave",  "")).strip(),
                    "arquivo_url":      str(r.get("Arquivo_Url",     "")).strip(),
                    "arquivo_nome":     str(r.get("Arquivo_Nome",    "")).strip(),
                    "status_indexacao": str(r.get("Status_Indexacao","Não indexado")).strip(),
                    "chunks":           [],
                }
                # Carrega chunks se o documento estiver indexado
                if doc["status_indexacao"] == "Indexado" and doc_id:
                    try:
                        df_chk = get_chunks_documento(doc_id)
                        if not df_chk.empty:
                            doc["chunks"] = [
                                {
                                    "chunk_index":  int(str(c.get("Chunk_Index",  0) or 0)),
                                    "titulo_secao": str(c.get("Titulo_Secao",  "")).strip(),
                                    "conteudo":     str(c.get("Conteudo",      "")).strip(),
                                    "palavras_chave": str(c.get("Palavras_Chave","")).strip(),
                                    "pagina_inicio": str(c.get("Pagina_Inicio", "")).strip(),
                                }
                                for _, c in df_chk.iterrows()
                            ]
                    except Exception:
                        pass
                docs.append(doc)
            ctx["documentos"] = docs
    except Exception:
        pass  # mantém docs do mock

    ctx["client_id"] = client_id
    return ctx


def _empty_context() -> dict:
    return {
        "empresa": "",
        "ativos": [], "manutencoes": [], "relatorios": [],
        "documentos": [], "chamados": [], "alertas": [],
        "especificacoes": {"oleo": None},
    }


# ── Motor de resposta ─────────────────────────────────────────────────────────

def query_assistant(
    client_id: str,
    pergunta: str,
    rota_atual: str = "",
    ativo_id: str = "",
    componente_id: str = "",
) -> dict:
    """
    Ponto de entrada principal do motor de busca controlada.

    SEGURANÇA: client_id SEMPRE da sessão. Nunca do payload do front-end.

    Retorna:
      {
        answer:            str,
        related_links:     [{label, page}],
        related_documents: [{titulo, id}],
        related_reports:   [{titulo, data}],
        suggested_actions: [{label, page}]
      }

    FUTURO: será exposto como POST /api/assistant/technical-query
    """
    intent  = detect_intent(pergunta)
    context = get_client_context(client_id)
    return _build_response(intent, context, pergunta, ativo_id)


def query_assistant_audit(
    client_id: str,
    pergunta: str,
    ativo_id: str = "",
) -> dict:
    """
    Versão estendida de query_assistant() para a tela de auditoria.
    Adiciona _intent, _confidence e _origem_resposta ao dict de resposta.
    SEGURANÇA: client_id SEMPRE da sessão.
    """
    intent  = detect_intent(pergunta)
    context = get_client_context(client_id)
    result  = _build_response(intent, context, pergunta, ativo_id)

    ans_lower = result["answer"].lower()
    sem_base  = "não encontrei informação suficiente" in ans_lower

    # Origem
    if sem_base:
        origem = "Sem base suficiente"
    elif result["related_documents"]:
        origem = "Biblioteca Técnica"
    elif intent == "manutencao":
        origem = "Plano de Manutenção"
    elif intent == "relatorios":
        origem = "Relatório Técnico"
    else:
        origem = "Base Pred.IO"

    # Confiança
    if sem_base:
        confidence = "Baixa"
    elif result["related_documents"]:
        confidence = "Alta"
    else:
        confidence = "Média"

    # Estatísticas de fontes usadas no contexto
    docs       = context.get("documentos", [])
    reps_idx   = context.get("relatorios_tecnicos_indexados", [])
    exec_reps  = context.get("relatorios_executivos", [])
    chams      = context.get("chamados_reais", []) or context.get("chamados", [])
    alertas    = context.get("alertas_reais", []) or context.get("alertas", [])

    result["_intent"]          = intent
    result["_confidence"]      = confidence
    result["_origem_resposta"] = origem
    result["_document_ids"]    = [d.get("id", "") for d in docs if d.get("id")]
    result["_report_ids"]      = [r.get("id", "") for r in reps_idx if r.get("id")]
    result["_chunks_count"]    = sum(len(d.get("chunks", [])) for d in docs) + sum(len(r.get("chunks", [])) for r in reps_idx)
    result["_exec_reports"]    = len(exec_reps)
    result["_chamados_count"]  = len(chams)
    result["_alertas_count"]   = len(alertas)
    return result


def _build_response(intent: str, ctx: dict, pergunta: str = "", ativo_id: str = "") -> dict:
    """Constrói a resposta controlada para a intenção detectada."""

    empresa = ctx.get("empresa", "sua operação")

    # ── MYCOLD AB 68 / MYCOLD PAO ─────────────────────────────────────────────
    if intent == "mycold":
        q = pergunta.lower()
        hist = ctx.get("mycold_ab_historico", {})
        if any(kw in q for kw in ["ab 68", "mycold ab", "ab68"]):
            return _resp(
                "O MYCOLD AB 68 foi descontinuado. No Portal Pred.IO, a referência atual deve ser "
                "<strong>MYCOLD PAO</strong>. O MYCOLD AB 68 pode aparecer apenas como referência "
                "histórica/inativa para redirecionamento, mas não deve ser recomendado como óleo "
                "homologado atual.",
                links=[
                    {"label": "📚 Ver Tabela de Óleos", "page": "biblioteca"},
                    {"label": "🔧 Abrir Chamado", "page": "chamados"},
                ],
                documents=[{"titulo": "Tabela de Óleos Homologados MAYEKAWA/MYCOM", "id": "doc-mycom-002"}],
            )
        return _resp(
            "Com base na Tabela de Óleos Homologados MAYEKAWA/MYCOM, o óleo MYCOM homologado atual "
            "na base Pred.IO é <strong>MYCOLD PAO</strong> (ISO VG 68, classe PAO sintético, fluido: "
            "NH3/R22, 53 cSt @ 40°C). A referência antiga MYCOLD AB 68 foi descontinuada e não deve "
            "ser usada como recomendação atual.",
            links=[{"label": "📚 Ver Tabela de Óleos Homologados", "page": "biblioteca"}],
            documents=[{"titulo": "Tabela de Óleos Homologados MAYEKAWA/MYCOM", "id": "doc-mycom-002"}],
        )

    # ── Óleos homologados MAYEKAWA/MYCOM ──────────────────────────────────────
    if intent == "oleo_homologado":
        q = pergunta.lower()
        oleos = ctx.get("oleos_homologados", [])

        # Pode usar qualquer ISO 68?
        if "qualquer" in q:
            return _resp(
                "Não. A viscosidade ISO VG 68 é apenas um dos critérios. A seleção do óleo deve "
                "considerar o fluido refrigerante, a classe do lubrificante (PAO, POE, mineral), "
                "a aplicação, a condição operacional, a compatibilidade e a tabela homologada "
                "MAYEKAWA/MYCOM. Recomenda-se validação técnica antes de qualquer substituição.",
                links=[{"label": "📚 Ver Tabela de Óleos Homologados", "page": "biblioteca"}],
                documents=[{"titulo": "Tabela de Óleos Homologados MAYEKAWA/MYCOM", "id": "doc-mycom-002"}],
            )

        # Óleo para R134a / R404a
        if any(kw in q for kw in ["r134a", "r404a", "hfc"]):
            return _resp(
                "Com base na Tabela de Óleos Homologados MAYEKAWA/MYCOM, para R134a/R404a as "
                "opções são óleos sintéticos <strong>POE (Poliolester) ISO VG 68</strong>: "
                "MOBIL EAL ARCTIC 68, ICEMATIC SW 68 e CAPELLA HFC 68. A aplicação deve ser "
                "validada conforme fluido, equipamento, condição operacional e orientação técnica "
                "da equipe Pred.IO.",
                links=[
                    {"label": "📚 Ver Tabela de Óleos Homologados", "page": "biblioteca"},
                    {"label": "🔧 Abrir Chamado", "page": "chamados"},
                ],
                documents=[{"titulo": "Tabela de Óleos Homologados MAYEKAWA/MYCOM", "id": "doc-mycom-002"}],
            )

        # Óleo para Amônia / NH3
        if any(kw in q for kw in ["amônia", "amonia", "nh3"]):
            return _resp(
                "Com base na Tabela de Óleos Homologados MAYEKAWA/MYCOM, para Amônia/NH3 há opções "
                "ISO VG 68 com classe PAO, semi-sintético PAO e mineral: REFLO 68A, RAB 68, R 200, "
                "MOBIL GARGOYLE ARCTIC SHC 226 E, MOBIL GARGOYLE ARCTIC EH, ESSO REFRIGERATION 68, "
                "CAPELLA 68 e MYCOLD PAO. A seleção deve considerar fluido, operação, análise de óleo "
                "e validação técnica da equipe Pred.IO.",
                links=[
                    {"label": "📚 Ver Tabela de Óleos Homologados", "page": "biblioteca"},
                    {"label": "🔧 Abrir Chamado", "page": "chamados"},
                ],
                documents=[{"titulo": "Tabela de Óleos Homologados MAYEKAWA/MYCOM", "id": "doc-mycom-002"}],
            )

        # Listagem geral de óleos homologados
        if oleos:
            ativos = [o for o in oleos if o.get("status") == "Homologado"]
            nomes = ", ".join(o["nome"] for o in ativos)
            return _resp(
                "Com base na Tabela de Óleos Homologados MAYEKAWA/MYCOM, os óleos homologados "
                f"cadastrados (ISO VG 68) são: <strong>{nomes}</strong>. A seleção depende do "
                "fluido refrigerante, da classe do lubrificante, da aplicação, da condição "
                "operacional, da análise de óleo e da validação técnica da equipe Pred.IO.",
                links=[{"label": "📚 Ver Tabela de Óleos Homologados", "page": "biblioteca"}],
                documents=[{"titulo": "Tabela de Óleos Homologados MAYEKAWA/MYCOM", "id": "doc-mycom-002"}],
            )

        # Fallback: busca em chunks
        chunk_result = _buscar_chunk_oleo_mycom(ctx, pergunta)
        if chunk_result:
            return _resp(
                chunk_result["answer"],
                links=[{"label": "📚 Ver Tabela de Óleos Homologados", "page": "biblioteca"}],
                documents=chunk_result.get("docs", []),
            )
        return _resp(
            "Não encontrei informação suficiente na base de óleos homologados. "
            "Consulte a Tabela de Óleos Homologados MAYEKAWA/MYCOM na Biblioteca Técnica "
            "ou abra um chamado para validação da equipe Pred.IO.",
            links=[
                {"label": "📚 Ver Tabela de Óleos Homologados", "page": "biblioteca"},
                {"label": "🔧 Abrir Chamado", "page": "chamados"},
            ],
        )

    # ── Relatório Executivo de Confiabilidade ────────────────────────────────
    if intent == "relatorio_executivo":
        exec_reps = ctx.get("relatorios_executivos", [])
        q = pergunta.lower()

        # Perguntas sobre overhaul/rolamento — resposta padrão obrigatória
        if any(kw in q for kw in ["overhaul", "rolamento", "troca de rolamento",
                                   "indicação de overhaul", "indicacao de overhaul"]):
            return _resp(
                "Não há indicação automática de overhaul por horímetro. O overhaul é uma "
                "recomendação por condição e depende da saúde real do ativo, relatórios "
                "preditivos, histórico operacional e avaliação técnica Pred.IO. "
                "<strong>20.000 horas é referência técnica, não gatilho automático de overhaul.</strong> "
                "Fonte: Pred.IO.",
                links=[{"label": "🔧 Abrir Chamado Técnico", "page": "chamados"}],
                confidence="media",
            )

        if any(kw in q for kw in ["ruído", "ruido", "barulho", "rolamento", "troca de rolamento"]):
            return _resp(
                "Troca de rolamento não deve ser automática apenas por ruído, temperatura ou "
                "horímetro. A decisão deve considerar análise de vibração, termografia, "
                "lubrificação, tendência e avaliação técnica Pred.IO. Fonte: Pred.IO.",
                links=[{"label": "🔧 Abrir Chamado Técnico", "page": "chamados"}],
                confidence="media",
            )

        if not exec_reps:
            return _resp(
                "Não encontrei relatório executivo publicado para o seu ativo no Portal Pred.IO. "
                "Quando a equipe Pred.IO publicar um relatório executivo, ele aparecerá aqui e em "
                "📁 Meus Relatórios. Fonte: Pred.IO.",
                links=[{"label": "📁 Ver Relatórios", "page": "relatorios"}],
                confidence="media",
            )

        # Resumo dos relatórios executivos disponíveis
        rep = exec_reps[0]
        titulo    = rep.get("titulo",           "Relatório Executivo")
        periodo   = rep.get("periodo",          "—")
        resumo_ex = rep.get("resumo_executivo", "")
        pub_em    = rep.get("publicado_em",      "")
        total_ex  = len(exec_reps)

        base_msg = (
            f"Encontrei <strong>{total_ex}</strong> relatório(s) executivo(s) publicado(s) "
            f"para o seu ativo.<br><br>"
            f"<strong>{titulo}</strong><br>"
            f"Período: {periodo}"
            + (f" | Publicado em: {pub_em}" if pub_em else "")
        )
        if resumo_ex:
            base_msg += f"<br><br><em>Resumo:</em> {resumo_ex[:500]}"
        base_msg += "<br><br>Fonte: Pred.IO."

        return _resp(
            base_msg,
            links=[{"label": "📁 Ver Relatório Executivo", "page": "relatorios"}],
            documents=[{"titulo": titulo, "id": "relatorio-executivo"}],
            confidence="alta",
        )

    # ── 20.000 horas / Overhaul / Kit revisão / Desmontagem ──────────────────
    if intent == "revisao_condicao":
        q = pergunta.lower()
        if any(kw in q for kw in ["overhaul", "preciso fazer overhaul", "quando fazer overhaul"]):
            return _resp(
                "O overhaul não deve ser decidido automaticamente por horímetro. A recomendação "
                "deve considerar a saúde real da máquina, com base em: análise de vibração, "
                "análise de óleo, termografia, histórico operacional, tendência de score de saúde, "
                "falhas recorrentes e avaliação técnica da equipe Pred.IO. "
                "<strong>20.000 horas é referência técnica, não gatilho automático de overhaul. "
                "A decisão depende da saúde real da máquina.</strong> "
                "Recomendo abrir um chamado técnico ou aguardar a recomendação dos relatórios preditivos.",
                links=[
                    {"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                    {"label": "📚 Ver Manual", "page": "biblioteca"},
                    {"label": "🔧 Abrir Chamado Técnico", "page": "chamados"},
                ],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )
        if any(kw in q for kw in ["kit revisão", "kit revisao", "kit de revisao", "kit de revisão"]):
            return _resp(
                "A substituição do kit revisão do compressor não é automática por horímetro. "
                "A indicação deve depender de avaliação técnica e da condição real da máquina, "
                "considerando análise de vibração, análise de óleo, termografia, histórico "
                "operacional e avaliação da equipe Pred.IO. "
                "<strong>20.000 horas é referência técnica, não gatilho automático de overhaul. "
                "A decisão depende da saúde real da máquina.</strong>",
                links=[
                    {"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                    {"label": "🔧 Abrir Chamado Técnico", "page": "chamados"},
                ],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )
        # Resposta padrão para 20k horas / revisão / desmontagem
        return _resp(
            "O manual cita a revisão/desmontagem como referência técnica para inspeção bienal ou "
            "20.000 horas, porém <strong>no Portal Pred.IO essa decisão não é automática por "
            "horímetro</strong>. A indicação deve considerar a saúde real da máquina, com base em "
            "análise de vibração, análise de óleo, termografia, histórico operacional, tendência de "
            "score, falhas recorrentes e avaliação técnica da equipe Pred.IO. "
            "<strong>20.000 horas é referência técnica, não gatilho automático de overhaul. "
            "A decisão depende da saúde real da máquina.</strong> "
            "Recomenda-se abrir um chamado técnico ou aguardar a recomendação dos relatórios preditivos.",
            links=[
                {"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                {"label": "📚 Ver Manual", "page": "biblioteca"},
                {"label": "🔧 Abrir Chamado Técnico", "page": "chamados"},
            ],
            documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
        )

    # ── Mypro Touch / Mypro Touch AD ─────────────────────────────────────────
    if intent == "mypro_touch":
        q = pergunta.lower()

        # O que é Mypro Touch AD
        if "touch ad" in q:
            return _resp(
                "O <strong>Mypro Touch AD</strong> é uma nomenclatura utilizada na base Pred.IO "
                "para painel/interface de operação MYCOM com aplicação conforme o projeto da "
                "unidade. Deve ser tratado como variação do painel Mypro Touch, respeitando a "
                "configuração específica do equipamento e do cliente.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # O que é Mypro Touch (genérico)
        if any(kw in q for kw in ["o que é mypro", "o que e mypro", "o que e o mypro"]):
            return _resp(
                "O <strong>Mypro Touch</strong> é um painel/interface de operação utilizado em "
                "unidades MYCOM, que permite visualizar o estado do compressor, alarmes, falhas, "
                "set points e comandos operacionais, conforme a configuração do sistema.\n\n"
                "Fonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Login / senha — supervisor
        if any(kw in q for kw in ["supervisor", "level 2", "nivel 2", "xyz", "2222"]):
            return _resp(
                "Na base Pred.IO, o acesso <strong>Level 2 — Supervisor/Administrador</strong> "
                "do painel Mypro Touch é:\n\n"
                "Login: <code>XYZ</code> / Senha: <code>2222</code>\n\n"
                "⚠️ Use apenas se você for operador autorizado. Alterações indevidas podem "
                "causar danos ao compressor.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Login / senha — operador
        if any(kw in q for kw in ["operador", "level 1", "nivel 1", "abc", "1111"]):
            return _resp(
                "Na base Pred.IO, o acesso <strong>Level 1 — Operador</strong> do "
                "painel Mypro Touch é:\n\n"
                "Login: <code>ABC</code> / Senha: <code>1111</code>\n\n"
                "⚠️ Use apenas se você for operador autorizado.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Login / senha (geral)
        if any(kw in q for kw in ["login", "senha", "level", "nivel", "acesso"]):
            return _resp(
                "Na base Pred.IO, os acessos do painel <strong>Mypro Touch</strong> são:\n\n"
                "• <strong>Level 1 — Operador:</strong> Login: <code>ABC</code> / Senha: <code>1111</code>\n"
                "• <strong>Level 2 — Supervisor/Administrador:</strong> Login: <code>XYZ</code> / Senha: <code>2222</code>\n\n"
                "⚠️ Use apenas se você for operador autorizado. Alterações indevidas de "
                "parâmetros podem causar danos ao compressor.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Como ligar / dar partida
        if any(kw in q for kw in ["ligar", "partir", "partida", "como ligar", "como partir"]):
            return _resp(
                "No painel <strong>Mypro Touch</strong>, para ligar o compressor:\n\n"
                "Pressione a tecla <strong>PARTIDA</strong> por alguns segundos até que ela "
                "fique verde. Em seguida, acompanhe a janela <em>Condição Atual</em> no campo "
                "<em>Estado do Compressor</em>. O painel deve indicar "
                "<em>Preparar para Partir</em> e depois <em>Compressor Ligado</em>.\n\n"
                "⚠️ Use apenas se você for operador autorizado.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Como parar
        if any(kw in q for kw in ["parar", "parada", "desligar", "como parar", "como desligar"]):
            return _resp(
                "No painel <strong>Mypro Touch</strong>, para parar o compressor:\n\n"
                "Pressione a tecla <strong>PARAR</strong> por alguns instantes até que o "
                "<em>Estado do Compressor</em> apresente <em>Recolhimento do Sistema</em>.\n\n"
                "⚠️ Use apenas se você for operador autorizado.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Alarme recorrente
        if any(kw in q for kw in ["voltou", "varias vezes", "várias vezes", "recorrente", "voltando"]):
            return _resp(
                "Alarme recorrente não deve ser tratado apenas com reset. Registre as condições "
                "operacionais, verifique a tendência, correlacione com pressões, temperaturas, "
                "óleo, vibração e histórico, e <strong>abra um chamado técnico</strong> para "
                "análise da equipe Pred.IO.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado Técnico", "page": "chamados"}],
            )

        # Limpar alarme / sem resolver causa
        if any(kw in q for kw in ["limpar alarme", "limpar sem", "resetar", "reset alarme", "limpar falha", "sem resolver"]):
            return _resp(
                "No painel <strong>Mypro Touch</strong>, primeiro resolva a causa da falha. "
                "Depois, acione o botão de limpeza ou reconhecimento de alarme.\n\n"
                "Não é recomendado limpar alarme sem tratar a causa — isso pode mascarar uma "
                "condição insegura e dificultar a análise da falha. Se o alarme for recorrente, "
                "abra chamado técnico.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Onde ver alarmes
        if any(kw in q for kw in ["onde vejo alarme", "onde ver alarme", "onde vejo falha", "ver alarme", "alarmes e falhas"]):
            return _resp(
                "No painel <strong>Mypro Touch</strong>, os alarmes e falhas aparecem na janela "
                "<em>Alarmes/Falhas</em>. Falhas ativas aparecem em <strong>vermelho</strong>. "
                "Após solucionar a causa e reconhecer/limpar o alarme, a indicação pode ficar "
                "<strong>azul</strong>.\n\nFonte: Pred.IO",
            )

        # Alarme azul
        if "alarme azul" in q or ("azul" in q and "alarme" in q):
            return _resp(
                "Na base Pred.IO, alarme ou falha em <strong>azul</strong> indica condição "
                "reconhecida após a tratativa ou reconhecimento. Ainda assim, deve-se garantir "
                "que a causa foi resolvida.\n\nFonte: Pred.IO",
            )

        # Alarme vermelho
        if any(kw in q for kw in ["alarme vermelho", "falha vermelha", "vermelho"]):
            return _resp(
                "Falha em <strong>vermelho</strong> no painel Mypro Touch indica uma falha "
                "ativa ou recente que exige atenção. A causa deve ser solucionada antes de "
                "reconhecer ou limpar o alarme.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Cut In
        if "cut in" in q:
            return _resp(
                "Na base Pred.IO, <strong>SET POINT CUT IN</strong> define a pressão em que o "
                "compressor liga automaticamente.\n\nFonte: Pred.IO",
            )

        # Cut Out
        if "cut out" in q:
            return _resp(
                "Na base Pred.IO, <strong>SET POINT CUT OUT</strong> define a pressão em que o "
                "compressor desliga automaticamente por baixa pressão.\n\nFonte: Pred.IO",
            )

        # Set Point de Controle sobre Pressão (genérico)
        if any(kw in q for kw in ["set point de controle", "controle sobre pressao", "controle sobre pressão"]):
            return _resp(
                "O <strong>Set Point de Controle sobre Pressão</strong> é a pressão que o "
                "compressor terá como referência de controle durante a operação.\n\nFonte: Pred.IO",
            )

        # Set Point #1 e #2
        if any(kw in q for kw in ["set point #1", "set point 1", "set point #2", "set point 2", "#1", "#2"]):
            return _resp(
                "Na base Pred.IO:\n\n"
                "• <strong>Set Point #1</strong> — referência para -10 °C\n"
                "• <strong>Set Point #2</strong> — referência para -40 °C\n\n"
                "A seleção deve ser feita na área indicada do painel, apenas por operador "
                "autorizado.\n\nFonte: Pred.IO",
            )

        # Alterar set point
        if any(kw in q for kw in ["alterar set point", "mudar set point", "como alterar set"]):
            return _resp(
                "Para alterar set point no painel <strong>Mypro Touch</strong>:\n\n"
                "1. Clique no ícone de usuário\n"
                "2. Digite o login → pressione ENTER\n"
                "3. Digite a senha → pressione ENTER\n"
                "4. Clique em <em>LOG ON</em> → aguarde a luz ficar verde\n"
                "5. Acesse os campos de set point desejados\n\n"
                "⚠️ Alterações devem ser feitas apenas por operador autorizado. Parâmetros "
                "incorretos podem causar instabilidade, alarmes e danos ao compressor.\n\n"
                "Fonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Alterar capacidade
        if any(kw in q for kw in ["alterar capacidade", "capacidade manual", "capacidade manualmente"]):
            return _resp(
                "Para alterar a capacidade manualmente no painel <strong>Mypro Touch</strong>:\n\n"
                "Acesse <em>MENU > CONTROLE</em>, abra a tela de controle de capacidade e "
                "altere o valor para o limite desejado.\n\n"
                "⚠️ Deve ser feito apenas por operador autorizado. A alteração interfere no "
                "limite operacional e pode afetar processo, pressão, carga, consumo e segurança. "
                "Não é recomendado alterar para qualquer valor sem validação técnica.\n\n"
                "Fonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # O que registrar quando falha
        if any(kw in q for kw in ["o que registrar", "registrar quando", "dados para registrar"]):
            return _resp(
                "Quando ocorrer uma falha no painel <strong>Mypro Touch</strong>, registrar:\n\n"
                "• Data e hora, ativo e modelo\n"
                "• Horímetro e estado do compressor\n"
                "• Alarme/falha exibida\n"
                "• Pressão de sucção, descarga e óleo\n"
                "• Temperatura de descarga e do óleo\n"
                "• Corrente, capacidade e frequência\n"
                "• Vibração e condições do processo\n"
                "• Ação realizada e responsável\n\n"
                "Fonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Estado do compressor / onde ver se está ligado
        if any(kw in q for kw in ["estado do compressor", "condição atual", "está ligado"]):
            return _resp(
                "No painel <strong>Mypro Touch</strong>, verifique a janela "
                "<em>Condição Atual</em>, campo <em>Estado do Compressor</em>. Após a partida, "
                "o painel indica <em>Preparar para Partir</em> e depois "
                "<em>Compressor Ligado</em>.\n\nFonte: Pred.IO",
            )

        # Fallback Mypro Touch
        return _resp(
            "O Assistente Técnico Pred.IO tem base técnica sobre o painel "
            "<strong>Mypro Touch</strong> e <strong>Mypro Touch AD</strong>. "
            "Para partida, parada, reset de alarme, set point ou capacidade, use apenas se "
            "você for operador autorizado. Para situações críticas, abra um chamado técnico.\n\n"
            "Fonte: Pred.IO",
            links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
        )

    # ── Comunicação industrial / Monitoramento remoto ─────────────────────────
    if intent == "comunicacao_monitoramento":
        q = pergunta.lower()

        if "modbus" in q:
            return _resp(
                "Modbus é um protocolo de comunicação industrial que pode permitir leitura de "
                "dados do painel ou controlador. Para o Portal Pred.IO, recomenda-se iniciar "
                "com leitura e monitoramento de variáveis, evitando comandos de escrita sem "
                "projeto de segurança validado.\n\nFonte: Pred.IO",
            )

        if "ethernet" in q:
            return _resp(
                "Comunicação Ethernet é uma forma de conexão em rede que pode permitir "
                "integração entre painel, CLP, supervisório ou portal, dependendo do projeto "
                "e dos protocolos disponíveis. Essa integração deve ser feita com rede segura, "
                "permissões e validação técnica.\n\nFonte: Pred.IO",
            )

        if any(kw in q for kw in ["expor painel", "painel na internet", "painel internet"]):
            return _resp(
                "Não é recomendado expor o painel industrial diretamente na internet. O acesso "
                "deve ser protegido por rede segura, VPN, firewall, credenciais, permissões e "
                "política de acesso. Expor painel industrial diretamente na internet aumenta o "
                "risco de acesso indevido e falha operacional.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        if any(kw in q for kw in ["pode comandar", "partida remota", "parada remota", "comando remoto"]):
            return _resp(
                "Não nesta fase. O Portal Pred.IO deve priorizar monitoramento, alertas e "
                "histórico técnico. Comandos remotos como partida, parada, reset de alarme, "
                "alteração de set point ou capacidade só devem ser considerados em fase futura, "
                "com autenticação forte, permissões, intertravamentos, auditoria, confirmação "
                "dupla e validação de segurança operacional.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        if any(kw in q for kw in ["monitoramento pode", "o monitoramento pode", "monitoramento pode comandar"]):
            return _resp(
                "Nesta fase, o monitoramento online Pred.IO deve priorizar leitura, alertas, "
                "tendência e histórico. Comando remoto só deve ser considerado em projeto "
                "específico, com autorização, intertravamentos, autenticação forte, auditoria "
                "e validação de segurança.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        if any(kw in q for kw in ["quais dados", "dados o portal", "dados do portal", "buscar dados"]):
            return _resp(
                "O Portal Pred.IO deve priorizar dados de leitura da unidade compressora: "
                "estado do compressor, alarmes, falhas, pressão de sucção, pressão de descarga, "
                "pressão de óleo, temperatura de descarga, temperatura do óleo, corrente do "
                "motor, capacidade, frequência do inversor, horímetro, níveis, vibração e "
                "histórico de eventos.\n\nFonte: Pred.IO",
            )

        if any(kw in q for kw in ["portal pode buscar", "pode buscar dados", "buscar dados painel"]):
            return _resp(
                "Sim, desde que exista comunicação configurada e segura. O Portal Pred.IO deve "
                "priorizar leitura de dados como estado do compressor, alarmes, pressões, "
                "temperaturas, horímetro, capacidade, corrente e variáveis operacionais "
                "disponíveis no painel Mypro Touch ou Mypro Touch AD.\n\nFonte: Pred.IO",
            )

        return _resp(
            "O Portal Pred.IO suporta comunicação segura para monitoramento de dados da "
            "unidade compressora. Nesta fase, a prioridade é leitura de variáveis, alertas "
            "e histórico. Comandos remotos requerem projeto de segurança específico. "
            "Para integração ou acesso remoto, abra um chamado técnico.\n\nFonte: Pred.IO",
            links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
        )

    # ── Manual MYCOM / Sistema Chiller ────────────────────────────────────────
    if intent == "mycom_manual":
        q = pergunta.lower()

        # O que é uma unidade compressora MYCOM
        if any(kw in q for kw in ["o que e uma unidade", "unidade compressora mycom", "o que e compressor mycom"]):
            return _resp(
                "Uma unidade compressora MYCOM é um conjunto industrial usado em sistemas de "
                "refrigeração, chiller, congelamento ou processo, composto normalmente por "
                "compressor, motor, sistema de lubrificação, separador de óleo, painel de "
                "controle, sensores, válvulas, instrumentos e dispositivos de segurança. A "
                "avaliação deve considerar condição mecânica, elétrica, térmica, operacional "
                "e de lubrificação.\n\nFonte: Pred.IO",
                links=[{"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"}],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Diferença entre parafuso e alternativo
        if any(kw in q for kw in ["diferenca entre compressor", "parafuso e alternativo", "compressor parafuso", "compressor alternativo", "tipo de compressor"]):
            return _resp(
                "O compressor <strong>parafuso</strong> realiza compressão por rotores, sendo "
                "muito usado em aplicações industriais contínuas. O compressor "
                "<strong>alternativo</strong> realiza compressão por pistões e cilindros. "
                "A análise técnica deve considerar o tipo do compressor, porque temperatura de "
                "descarga, vibração, manutenção, falhas e limites operacionais podem variar "
                "conforme o modelo.\n\n"
                "Referência de temperatura de descarga:\n"
                "• Compressor alternativo: 80 °C a 140 °C\n"
                "• Compressor parafuso: até 90 °C\n\n"
                "Fonte: Pred.IO",
                links=[{"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"}],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Temperatura de descarga — parafuso
        if any(kw in q for kw in ["temperatura para parafuso", "temperatura compressor parafuso", "parafuso com descarga", "descarga parafuso"]):
            q_has_value = any(str(n) in q for n in range(85, 151))
            if "95" in q:
                return _resp(
                    "Para compressor parafuso, a referência Pred.IO é temperatura de descarga "
                    "até 90 °C. Uma leitura de 95 °C deve ser tratada como condição de atenção "
                    "e avaliada junto com pressão de descarga, pressão de sucção, condição do "
                    "óleo, arrefecimento e carga operacional. Se persistir, recomenda-se abrir "
                    "chamado técnico.\n\nFonte: Pred.IO",
                    links=[
                        {"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"},
                        {"label": "🔧 Abrir Chamado Técnico", "page": "chamados"},
                    ],
                )
            if "120" in q:
                return _resp(
                    "Para compressor parafuso, a referência Pred.IO é temperatura de descarga "
                    "até 90 °C. Uma leitura de 120 °C exige avaliação técnica imediata — "
                    "verificar arrefecimento, pressão de descarga, condição do óleo, filtros, "
                    "carga operacional e alarmes. Recomenda-se abrir chamado técnico.\n\n"
                    "Fonte: Pred.IO",
                    links=[
                        {"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"},
                        {"label": "🔧 Abrir Chamado Técnico", "page": "chamados"},
                    ],
                )
            return _resp(
                "Para compressor <strong>parafuso</strong>, a referência Pred.IO é temperatura "
                "de descarga <strong>até 90 °C</strong>. Leituras acima disso devem ser "
                "avaliadas tecnicamente, considerando pressão de descarga, pressão de sucção, "
                "óleo, arrefecimento, carga operacional e histórico do equipamento.\n\n"
                "Fonte: Pred.IO",
                links=[{"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"}],
            )

        # Temperatura de descarga — alternativo
        if any(kw in q for kw in ["temperatura para alternativo", "temperatura compressor alternativo", "alternativo com descarga", "descarga alternativo"]):
            if "120" in q:
                return _resp(
                    "Para compressor alternativo, a referência Pred.IO é de 80 °C a 140 °C. "
                    "Uma leitura de 120 °C pode estar dentro da faixa de referência, mas deve "
                    "ser interpretada junto com carga, fluido, pressão de descarga, pressão de "
                    "sucção, óleo, corrente elétrica e histórico operacional.\n\nFonte: Pred.IO",
                    links=[{"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"}],
                )
            return _resp(
                "Para compressor <strong>alternativo</strong>, a referência Pred.IO é de "
                "<strong>80 °C a 140 °C</strong>. A interpretação deve considerar fluido "
                "refrigerante, carga, pressão de descarga, pressão de sucção, condição do "
                "óleo e histórico do equipamento.\n\nFonte: Pred.IO",
                links=[{"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"}],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Temperatura de descarga (genérico — sem tipo especificado)
        if any(kw in q for kw in ["temperatura de descarga", "temperatura descarga", "descarga normal", "temperatura normal de descarga"]):
            return _resp(
                "A temperatura de descarga depende do tipo de compressor:\n\n"
                "• <strong>Compressor alternativo:</strong> referência Pred.IO de 80 °C a 140 °C\n"
                "• <strong>Compressor parafuso:</strong> referência Pred.IO até 90 °C\n\n"
                "A avaliação deve considerar fluido, carga, pressão de sucção, pressão de "
                "descarga, condição do óleo e histórico operacional.\n\nFonte: Pred.IO",
                links=[{"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"}],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # O que pode causar temperatura de descarga alta
        if any(kw in q for kw in ["o que pode causar descarga", "causa temperatura descarga alta", "descarga alta o que"]):
            return _resp(
                "Temperatura de descarga alta pode estar relacionada a: pressão de descarga "
                "elevada, taxa de compressão alta, falta de arrefecimento, condensador sujo, "
                "problema na água de arrefecimento, filtro de sucção obstruído, óleo "
                "deteriorado, carga operacional elevada ou operação com superaquecimento.\n\n"
                "Fonte: Pred.IO",
                links=[
                    {"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"},
                    {"label": "🔧 Abrir Chamado", "page": "chamados"},
                ],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Pressão de descarga alta
        if any(kw in q for kw in ["pressão de descarga alta", "pressao de descarga alta", "descarga alta"]):
            return _resp(
                "Com base na base técnica Pred.IO, pressão de descarga alta pode estar "
                "relacionada a: falta de água de arrefecimento, temperatura elevada da água, "
                "condensador sujo, excesso de refrigerante, presença de ar no sistema, óleo "
                "no condensador ou capacidade insuficiente do condensador.\n\n"
                "Recomenda-se verificar condensador, água de arrefecimento, carga de "
                "refrigerante e histórico de alarmes.\n\nFonte: Pred.IO",
                links=[
                    {"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"},
                    {"label": "🔧 Abrir Chamado", "page": "chamados"},
                ],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Pressão de descarga baixa
        if any(kw in q for kw in ["pressão de descarga baixa", "pressao de descarga baixa", "descarga baixa"]):
            return _resp(
                "Com base na base técnica Pred.IO, pressão de descarga baixa pode estar "
                "associada a: excesso de água de arrefecimento, baixa temperatura da água, "
                "restrição ou entupimento na tubulação, abertura excessiva da válvula de "
                "expansão, falta de refrigerante ou vazamento interno. A ação correta depende "
                "da condição operacional do sistema.\n\nFonte: Pred.IO",
                links=[{"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"}],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Pressão de sucção alta
        if any(kw in q for kw in ["pressão de sucção alta", "pressao de succao alta", "sucção alta", "succao alta"]):
            return _resp(
                "Com base na base técnica Pred.IO, pressão de sucção alta pode indicar: "
                "excesso de abertura da válvula de expansão, aumento de carga térmica, queda "
                "de capacidade do compressor ou vazamento interno, dependendo do tipo de "
                "compressor e da condição de operação.\n\nFonte: Pred.IO",
                links=[{"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"}],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Pressão de sucção baixa
        if any(kw in q for kw in ["pressão de sucção baixa", "pressao de succao baixa", "sucção baixa", "succao baixa"]):
            return _resp(
                "Com base na base técnica Pred.IO, pressão de sucção baixa pode estar "
                "relacionada a: válvula de expansão muito fechada ou obstruída, falta de "
                "refrigerante, óleo no evaporador, evaporador congelado, filtro de sucção "
                "obstruído ou restrição na linha de sucção.\n\nFonte: Pred.IO",
                links=[
                    {"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"},
                    {"label": "🔧 Abrir Chamado", "page": "chamados"},
                ],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Dados importantes para avaliar
        if any(kw in q for kw in ["dados importantes para avaliar", "quais dados", "dados para avaliar"]):
            return _resp(
                "Para avaliação inicial de uma unidade compressora, são importantes: tipo de "
                "compressor, fluido refrigerante, modelo, horímetro, pressão de sucção, pressão "
                "de descarga, pressão de óleo, temperatura de descarga, temperatura do óleo, "
                "corrente elétrica, vibração, termografia, análise de óleo, alarmes ativos, "
                "histórico de falhas e plano de manutenção.\n\nFonte: Pred.IO",
                links=[{"label": "📅 Ver Plano de Manutenção", "page": "manutencao"}],
            )

        # Fluxostato
        if "fluxostato" in q:
            return _resp(
                "Com base no <strong>Manual Operacional MYCOM - Sistema Chiller</strong> "
                "(Seção: Fluxostato), encontrei: O fluxostato é uma chave de controle de fluxo "
                "usada para indicar presença ou ausência de fluxo dentro da tubulação. Ele atua "
                "como dispositivo complementar de segurança e proteção para ligar ou desligar "
                "alarmes, motores, compressores, máquinas e bombas d'água.",
                links=[{"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"}],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Pressão de óleo baixa
        if any(kw in q for kw in ["pressao de oleo", "pressão de óleo", "oleo baixo", "óleo baixo", "pressao oleo baixa"]):
            return _resp(
                "Com base no <strong>Manual Operacional MYCOM - Sistema Chiller</strong> "
                "(Seção: Parâmetros operacionais — Pressão de óleo), pressão de óleo abaixo do "
                "valor indicado pode estar relacionada à diminuição da viscosidade do óleo, "
                "obstrução do filtro, óleo deteriorado ou defeito na bomba de óleo. As ações "
                "indicadas incluem ajustar a pressão do óleo, limpar o filtro, trocar o óleo ou "
                "examinar/consertar a bomba. Em caso de condição crítica, recomenda-se abrir chamado técnico.",
                links=[
                    {"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"},
                    {"label": "🔧 Abrir Chamado Técnico", "page": "chamados"},
                ],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Análise de óleo — quando fazer
        if any(kw in q for kw in ["analise de oleo", "análise de óleo", "quando fazer analise", "coletar amostra"]):
            return _resp(
                "Com base no <strong>Manual Operacional MYCOM - Sistema Chiller</strong> "
                "(Seção: Inspeção semestral ou 5.000 horas), a análise de óleo está prevista na "
                "inspeção semestral ou a cada 5.000 horas de funcionamento. O manual orienta coletar "
                "amostra de óleo do compressor e enviar para análise de laboratório. Se o relatório "
                "for desfavorável, o óleo deve ser drenado e substituído por carga correta de óleo "
                "novo ISO 68. A seleção do óleo deve considerar a Tabela de Óleos Homologados "
                "MAYEKAWA/MYCOM, fluido refrigerante, condição operacional e validação técnica.",
                links=[
                    {"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"},
                    {"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                ],
                documents=[
                    {"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"},
                    {"titulo": "Tabela de Óleos Homologados MAYEKAWA/MYCOM", "id": "doc-mycom-002"},
                ],
            )

        # Filtro coalescente — quando trocar
        if any(kw in q for kw in ["coalescente", "filtro coalescente", "quando trocar filtro"]):
            return _resp(
                "Com base no <strong>Manual Operacional MYCOM - Sistema Chiller</strong> "
                "(Seção: Inspeção anual ou 10.000 horas), a substituição do elemento filtro "
                "coalescente aparece na inspeção anual ou 10.000 horas. O manual também cita o "
                "filtro coalescente na referência bienal, mas no Portal Pred.IO a revisão de "
                "20.000 horas não é tratada como gatilho automático de intervenção.",
                links=[
                    {"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"},
                    {"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                ],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Alinhamento — quando conferir
        if any(kw in q for kw in ["alinhamento", "alinhar", "eixos", "motor x compressor", "quando conferir alinhamento"]):
            return _resp(
                "Com base no <strong>Manual Operacional MYCOM - Sistema Chiller</strong> "
                "(Seção: Inspeção semestral ou 5.000 horas), a conferência do alinhamento dos "
                "eixos motor x compressor está prevista na inspeção semestral ou 5.000 horas. "
                "O manual cita tolerância radial/axial de 0,06 mm.",
                links=[
                    {"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"},
                    {"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                ],
                documents=[{"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"}],
            )

        # Busca em chunks do manual MYCOM
        chunk_result = _buscar_chunk_mycom(ctx, pergunta)
        if chunk_result:
            return _resp(
                chunk_result["answer"],
                links=[{"label": "📚 Abrir Manual MYCOM", "page": "biblioteca"}],
                documents=chunk_result.get("docs", []),
            )

        # Tem manual MYCOM?
        docs = ctx.get("documentos", [])
        mycom_docs = [d for d in docs if "mycom" in d.get("titulo", "").lower() or "chiller" in d.get("titulo", "").lower()]
        if mycom_docs:
            answer = (
                "Encontrei o <strong>Manual Operacional MYCOM - Sistema Chiller</strong> "
                "disponível na Biblioteca Técnica. O manual contém informações sobre funcionamento, "
                "defeitos, parâmetros operacionais, painel elétrico, fluxostato, condensador a "
                "placa e rotinas de inspeção."
            )
            return _resp(
                answer,
                links=[{"label": "📚 Abrir Biblioteca Técnica", "page": "biblioteca"}],
                documents=[{"titulo": d["titulo"], "id": d.get("id", "")} for d in mycom_docs],
            )
        return _resp(
            "Não encontrei informação suficiente no Manual MYCOM cadastrado. "
            "Consulte a Biblioteca Técnica ou abra um chamado técnico.",
            links=[
                {"label": "📚 Abrir Biblioteca Técnica", "page": "biblioteca"},
                {"label": "🔧 Abrir Chamado", "page": "chamados"},
            ],
        )

    # ── Manutenção ────────────────────────────────────────────────────────────
    if intent == "manutencao":
        q_lower = pergunta.lower()

        # Como a análise de vibração ajuda
        if any(kw in q_lower for kw in ["como vibração ajuda", "como vibracao ajuda", "vibração ajuda", "vibracao ajuda"]):
            return _resp(
                "A análise de vibração ajuda a identificar tendências de desalinhamento, "
                "desbalanceamento, folgas, falhas em rolamentos, problemas de acoplamento, "
                "base frouxa, ressonância e alterações mecânicas. A decisão de intervenção "
                "deve considerar tendência e correlação com inspeção, óleo e termografia.\n\n"
                "No Portal Pred.IO, a análise de vibração está prevista como rotina preditiva "
                "a cada 2 meses.\n\nFonte: Pred.IO",
                links=[{"label": "📅 Ver Plano de Manutenção", "page": "manutencao"}],
            )

        # Como a análise de óleo ajuda
        if any(kw in q_lower for kw in ["como analise de oleo ajuda", "como análise de óleo ajuda", "analise de oleo ajuda"]):
            return _resp(
                "A análise de óleo ajuda a avaliar a condição do lubrificante e do equipamento, "
                "incluindo viscosidade, contaminação por água, partículas, oxidação, aditivos e "
                "metais de desgaste. Ela apoia decisões sobre troca de óleo, investigação de "
                "desgaste e prioridade de intervenção.\n\nFonte: Pred.IO",
                links=[
                    {"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                    {"label": "📚 Ver Tabela de Óleos Homologados", "page": "biblioteca"},
                ],
            )

        # Como a termografia ajuda
        if any(kw in q_lower for kw in ["como termografia ajuda", "termografia ajuda"]):
            return _resp(
                "A termografia ajuda a identificar aquecimento anormal em motor, painéis, "
                "conexões elétricas, rolamentos, mancais, sistema de lubrificação e componentes "
                "críticos. Deve ser correlacionada com corrente elétrica, carga, vibração e "
                "histórico operacional.\n\n"
                "No Portal Pred.IO, a termografia está prevista como rotina preditiva a cada "
                "4 meses.\n\nFonte: Pred.IO",
                links=[{"label": "📅 Ver Plano de Manutenção", "page": "manutencao"}],
            )

        # Como reduzir risco de falha
        if any(kw in q_lower for kw in ["como reduzir risco", "reduzir risco de falha"]):
            return _resp(
                "Para reduzir risco de falha na unidade compressora: manter inspeções diárias "
                "e semanais, cumprir plano de manutenção, realizar análise de óleo, vibração e "
                "termografia, tratar alarmes recorrentes, registrar dados operacionais, manter "
                "filtros e óleo em condição adequada, verificar alinhamento e correlacionar "
                "histórico técnico.\n\nFonte: Pred.IO",
                links=[
                    {"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                    {"label": "🔧 Abrir Chamado", "page": "chamados"},
                ],
            )

        # O que fazer antes de intervenção
        if any(kw in q_lower for kw in ["antes de intervencao", "o que fazer antes de intervencao", "antes de intervir"]):
            return _resp(
                "Antes de uma intervenção na unidade compressora: registrar a condição "
                "operacional, verificar alarmes ativos, consultar relatórios técnicos, avaliar "
                "histórico do ativo, confirmar o plano de manutenção, garantir segurança "
                "operacional e, se necessário, abrir chamado técnico com a equipe Pred.IO.\n\n"
                "Fonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # Tenta dados reais do Sheets; cai para mock legacy
        tarefas_real = ctx.get("tarefas_manutencao", [])
        mans_mock    = ctx.get("manutencoes", [])

        # ── Próxima análise de óleo ───────────────────────────────────────────
        if any(kw in q_lower for kw in ["análise de óleo", "analise de oleo",
                                         "próxima análise", "proxima analise",
                                         "coletar amostra", "amostra de oleo"]):
            if tarefas_real:
                oleo_tasks = [
                    t for t in tarefas_real
                    if "óleo" in t.get("nome", "").lower()
                    or "oleo" in t.get("nome", "").lower()
                    or "análise de óleo" in t.get("categoria", "").lower()
                    or "oleo" in t.get("categoria", "").lower()
                ]
                if oleo_tasks:
                    tk = oleo_tasks[0]
                    prox = tk.get("prox_data", "") or (f"horímetro {tk['prox_h']}h" if tk.get("prox_h") else "")
                    return _resp(
                        f"A próxima análise de óleo está programada para: <strong>{prox or 'aguarda avaliação'}</strong>. "
                        f"Status atual: <strong>{tk['status']}</strong>.\n\n"
                        "A análise de óleo é fundamental para avaliar viscosidade, contaminação, "
                        "oxidação e metais de desgaste. Recomenda-se validar o resultado com a equipe "
                        "Pred.IO antes de decisões de troca ou intervenção.\n\nFonte: Pred.IO",
                        links=[{"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                               {"label": "📚 Ver Tabela de Óleos", "page": "biblioteca"}],
                    )

        # ── Quais manutenções estão próximas ─────────────────────────────────
        if any(kw in q_lower for kw in ["próximas", "proximas", "quais manutenções",
                                         "quais manutencoes", "próxima do vencimento",
                                         "proxima do vencimento"]):
            if tarefas_real:
                proximas = [t for t in tarefas_real
                           if "próxima" in t.get("status", "").lower()
                           or "proxima" in t.get("status", "").lower()]
                if proximas:
                    itens = "; ".join(
                        f"{t['nome']}"
                        + (f" (prevista para {t['prox_data']})" if t.get("prox_data") else
                           f" (próxima aos {t['prox_h']}h)" if t.get("prox_h") else "")
                        for t in proximas[:4]
                    )
                    return _resp(
                        f"As tarefas próximas do vencimento são: <strong>{itens}</strong>.\n\n"
                        "Verifique o plano completo no Portal para mais detalhes.\n\nFonte: Pred.IO",
                        links=[{"label": "📅 Ver Plano de Manutenção", "page": "manutencao"}],
                    )

        # ── Tenho manutenção vencida ──────────────────────────────────────────
        if any(kw in q_lower for kw in ["vencida", "vencidas", "atrasada", "atrasadas",
                                         "em atraso", "ultrapassada", "ultrapassadas"]):
            if tarefas_real:
                vencidas = [t for t in tarefas_real
                           if t.get("status", "").lower() == "vencida"]
                if vencidas:
                    itens = "; ".join(t["nome"] for t in vencidas[:4])
                    return _resp(
                        f"Foram encontradas <strong>{len(vencidas)} tarefa(s) vencida(s)</strong>: {itens}.\n\n"
                        "Recomendo priorizar estas atividades e, se necessário, abrir um chamado "
                        "técnico com a equipe Pred.IO.\n\nFonte: Pred.IO",
                        links=[
                            {"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                            {"label": "🔧 Abrir Chamado", "page": "chamados"},
                        ],
                    )
                return _resp(
                    "Não há tarefas de manutenção vencidas no momento. "
                    "Continue acompanhando o plano de manutenção para manter o equipamento em dia.\n\n"
                    "Fonte: Pred.IO",
                    links=[{"label": "📅 Ver Plano de Manutenção", "page": "manutencao"}],
                )

        # ── Resposta geral com dados reais ────────────────────────────────────
        if tarefas_real:
            vencidas  = [t for t in tarefas_real if t.get("status","").lower() == "vencida"]
            proximas  = [t for t in tarefas_real
                        if "próxima" in t.get("status","").lower()
                        or "proxima" in t.get("status","").lower()]
            em_dia    = [t for t in tarefas_real if t.get("status","").lower() == "em dia"]

            partes = []
            if vencidas:
                partes.append(
                    f"⚠️ {len(vencidas)} tarefa(s) vencida(s): "
                    + ", ".join(t["nome"] for t in vencidas[:3])
                )
            if proximas:
                partes.append(
                    f"🟡 {len(proximas)} tarefa(s) próxima(s) do vencimento: "
                    + ", ".join(t["nome"] for t in proximas[:3])
                )
            if em_dia:
                partes.append(f"✅ {len(em_dia)} tarefa(s) em dia")

            answer = " | ".join(partes) if partes else "Plano de manutenção atualizado."
            return _resp(
                f"{answer}\n\nFonte: Pred.IO",
                links=[{"label": "📅 Ver Plano de Manutenção", "page": "manutencao"}],
            )

        # ── Fallback mock ──────────────────────────────────────────────────────
        if not mans_mock:
            return _resp(
                "Não encontrei planos de manutenção cadastrados para sua operação. "
                "Recomendo abrir um chamado técnico para que a equipe Pred.IO verifique.",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )
        itens_str = "; ".join(
            (m.get("vencimento_data") and f"{m['acao']} em {m['vencimento_data']}")
            or (m.get("vencimento_horas") and f"{m['acao']} em {m['vencimento_horas']} horas")
            or m["acao"]
            for m in mans_mock
        )
        answer = f"As próximas ações programadas são: {itens_str}."
        return _resp(answer, links=[{"label": "📅 Ver Plano de Manutenção", "page": "manutencao"}])

    # ── Relatórios ────────────────────────────────────────────────────────────
    if intent == "relatorios":
        rels = ctx.get("relatorios", [])
        if not rels:
            return _resp(
                "Nenhum relatório técnico publicado ainda para sua operação.",
                links=[{"label": "📋 Ver Relatórios", "page": "relatorios"}],
            )
        ativos_rel = sorted({r.get("ativo", "") for r in rels if r.get("ativo")})
        nomes = ", ".join(r["titulo"] for r in rels[:3])
        answer = (
            f"Encontrei {len(rels)} relatório(s) técnico(s) recente(s)"
            + (f" vinculados à {ativos_rel[0]}" if ativos_rel else "")
            + f", incluindo: {nomes}."
        )
        return _resp(
            answer,
            links=[{"label": "📋 Ver Relatórios Técnicos", "page": "relatorios"}],
            reports=[{"titulo": r["titulo"], "data": r.get("data", "")} for r in rels],
        )

    # ── Documentos / Manual ───────────────────────────────────────────────────
    if intent == "documentos":
        docs = ctx.get("documentos", [])
        if not docs:
            return _resp(
                "Nenhum documento técnico publicado na Biblioteca ainda. "
                "Entre em contato com a equipe Pred.IO para solicitar.",
                links=[{"label": "📚 Abrir Biblioteca Técnica", "page": "biblioteca"},
                       {"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )
        # Busca em chunks primeiro (prioridade: conteúdo indexado)
        chunk_result = _buscar_chunks_geral(ctx, pergunta)
        if chunk_result:
            return _resp(
                chunk_result["answer"],
                links=[{"label": "📚 Abrir Biblioteca Técnica", "page": "biblioteca"}],
                documents=chunk_result.get("docs", []),
            )
        ativos_doc = sorted({d.get("ativo", "") for d in docs if d.get("ativo")})
        answer = (
            "Encontrei documentos técnicos disponíveis na Biblioteca Técnica"
            + (f" vinculados à {ativos_doc[0]}" if ativos_doc else "")
            + "."
        )
        return _resp(
            answer,
            links=[{"label": "📚 Abrir Biblioteca Técnica", "page": "biblioteca"}],
            documents=[{"titulo": d["titulo"], "id": d.get("id", "")} for d in docs],
        )

    # ── Especificação de óleo (genérico) ─────────────────────────────────────
    if intent == "oleo":
        spec = ctx.get("especificacoes", {}).get("oleo")
        if spec:
            return _resp(
                f"O óleo recomendado para esta unidade é: {spec}.",
                links=[{"label": "📚 Ver Manual", "page": "biblioteca"}],
            )
        # Busca no manual MYCOM (menciona ISO 68 e direciona para tabela)
        chunk_result = _buscar_chunk_oleo(ctx) or _buscar_chunk_oleo_mycom(ctx, pergunta)
        if chunk_result:
            return _resp(
                chunk_result["answer"],
                links=[
                    {"label": "📚 Ver Manual", "page": "biblioteca"},
                    {"label": "📚 Ver Tabela de Óleos Homologados", "page": "biblioteca"},
                ],
                documents=chunk_result.get("docs", []),
            )
        return _resp(
            "Com base no Manual Operacional MYCOM - Sistema Chiller, o manual cita óleo "
            "lubrificante ISO 68. Para seleção do óleo homologado, consulte a Tabela de Óleos "
            "Homologados MAYEKAWA/MYCOM. A referência MYCOLD AB 68 foi descontinuada e deve ser "
            "substituída por MYCOLD PAO. Antes de qualquer substituição, recomenda-se validar "
            "a aplicação com a equipe Pred.IO.",
            links=[
                {"label": "📚 Abrir Biblioteca Técnica", "page": "biblioteca"},
                {"label": "🔧 Abrir Chamado", "page": "chamados"},
            ],
            documents=[
                {"titulo": "Manual Operacional MYCOM - Sistema Chiller", "id": "doc-mycom-001"},
                {"titulo": "Tabela de Óleos Homologados MAYEKAWA/MYCOM", "id": "doc-mycom-002"},
            ],
        )

    # ── Status do ativo ───────────────────────────────────────────────────────
    if intent == "status_ativo":
        q_lower = pergunta.lower()

        # O que é score de saúde
        if any(kw in q_lower for kw in ["score de saude", "score de saúde", "o que e score", "o que é score", "saude do ativo", "saúde do ativo"]):
            return _resp(
                "Score de saúde é uma representação resumida da condição do ativo, calculada "
                "a partir de dados como vibração, óleo, termografia, alarmes, chamados, "
                "manutenção, histórico operacional e criticidade. Ele não substitui laudo "
                "técnico, mas ajuda a priorizar acompanhamento.\n\nFonte: Pred.IO",
                links=[{"label": "⚙️ Ver Ativos", "page": "ativos"}],
            )

        # O que significa ativo em atenção
        if any(kw in q_lower for kw in ["ativo em atencao", "ativo em atenção", "o que significa atencao", "em atenção significa"]):
            return _resp(
                "Ativo em <strong>atenção</strong> indica que há sinais de acompanhamento "
                "necessário, como tendência de piora, manutenção próxima, alerta recorrente, "
                "alteração de score, anomalia em óleo, vibração ou temperatura. Não significa "
                "necessariamente parada imediata, mas exige monitoramento e análise.\n\n"
                "Fonte: Pred.IO",
                links=[{"label": "⚙️ Ver Ativos", "page": "ativos"}],
            )

        # O que significa ativo crítico
        if any(kw in q_lower for kw in ["ativo critico", "ativo crítico", "o que significa critico", "crítico significa"]):
            return _resp(
                "Ativo <strong>crítico</strong> indica condição com maior prioridade técnica, "
                "podendo envolver risco de falha, componente com score baixo, alarme crítico, "
                "tendência acelerada de degradação ou condição operacional fora da referência. "
                "Recomenda-se abertura ou acompanhamento de chamado técnico.\n\nFonte: Pred.IO",
                links=[
                    {"label": "⚙️ Ver Ativos", "page": "ativos"},
                    {"label": "🔧 Abrir Chamado", "page": "chamados"},
                ],
            )

        ativos = ctx.get("ativos", [])
        if not ativos:
            return _resp(
                "Nenhum ativo monitorado cadastrado ainda para sua operação.",
                links=[{"label": "⚙️ Ver Ativos", "page": "ativos"}],
            )
        ativo = ativos[0]
        criticos = [c for c in ativo.get("componentes", []) if c.get("status") == "Crítico"]
        answer = (
            f"A {ativo['nome']} está com status {ativo['status']} "
            f"e score de saúde {ativo['score']}/100."
        )
        if criticos:
            nomes = ", ".join(c["nome"] for c in criticos)
            answer += f" O componente {nomes} está sinalizado como crítico."
        return _resp(answer, links=[{"label": "⚙️ Ver Ativos Monitorados", "page": "ativos"}])

    # ── Chamados ──────────────────────────────────────────────────────────────
    if intent == "chamados":
        q_lower    = pergunta.lower()
        chams_real = ctx.get("chamados_reais", [])
        chams_mock = ctx.get("chamados", [])
        chams      = chams_real or chams_mock  # preferência para dados reais

        # "Tenho chamados abertos?"
        if any(kw in q_lower for kw in ["tenho chamados", "chamados abertos",
                                         "meus chamados", "abertos"]):
            abertos = [c for c in chams if c.get("status", "").lower()
                       in ("aberto", "em análise", "em analise", "em andamento",
                           "aguardando cliente", "reaberto")]
            if abertos:
                itens = "; ".join(
                    f'"{c["titulo"]}" — {c["status"]}'
                    + (f' (ativo: {c["ativo_id"]})' if c.get("ativo_id") else "")
                    for c in abertos[:4]
                )
                return _resp(
                    f"Você tem <strong>{len(abertos)} chamado(s) em aberto</strong>: {itens}.\n\n"
                    "Acesse a área de Chamados para acompanhar e responder.\n\nFonte: Pred.IO",
                    links=[{"label": "🔧 Ver Chamados Técnicos", "page": "chamados"}],
                )
            return _resp(
                "Não há chamados em aberto no momento. "
                "Se precisar de suporte, use a área de Chamados Técnicos.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )

        # "Qual status do meu chamado?" / "O chamado foi respondido?"
        if any(kw in q_lower for kw in ["status do chamado", "meu chamado", "qual status",
                                          "foi respondido", "responderam", "chamado respondido"]):
            if chams:
                c = chams[0]
                respondido = c.get("status", "").lower() in ("em análise", "em andamento",
                                                              "aguardando cliente")
                resp_txt   = (
                    f'O chamado mais recente é "<strong>{c["titulo"]}</strong>" — '
                    f'status: <strong>{c["status"]}</strong>.'
                )
                if respondido:
                    resp_txt += " A equipe Pred.IO já está analisando."
                elif c.get("status", "").lower() == "concluído":
                    resp_txt += " Este chamado foi concluído pela equipe Pred.IO."
                else:
                    resp_txt += " Ainda aguardando análise inicial."
                return _resp(
                    resp_txt + "\n\nFonte: Pred.IO",
                    links=[{"label": "🔧 Ver Chamados", "page": "chamados"}],
                )

        # "Tem chamado para esse ativo?"
        if any(kw in q_lower for kw in ["chamado para esse ativo", "chamado para o ativo",
                                          "chamado do ativo"]):
            if ativo_id and chams_real:
                chams_ativo = [c for c in chams_real if c.get("ativo_id") == ativo_id]
                if chams_ativo:
                    itens = "; ".join(
                        f'"{c["titulo"]}" ({c["status"]})'
                        for c in chams_ativo[:3]
                    )
                    return _resp(
                        f"Há {len(chams_ativo)} chamado(s) vinculado(s) ao ativo {ativo_id}: "
                        f"{itens}.\n\nFonte: Pred.IO",
                        links=[{"label": "🔧 Ver Chamados", "page": "chamados"}],
                    )
                return _resp(
                    f"Não há chamados abertos para o ativo {ativo_id}.\n\nFonte: Pred.IO",
                    links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
                )

        # Resposta geral
        n_abertos = len([c for c in chams if c.get("status", "").lower()
                         in ("aberto", "em análise", "em analise",
                             "em andamento", "aguardando cliente", "reaberto")])
        if n_abertos:
            return _resp(
                f"Você tem <strong>{n_abertos} chamado(s) em aberto</strong>. "
                "Acesse a área de Chamados Técnicos para acompanhar e responder.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Ver Chamados Técnicos", "page": "chamados"}],
            )
        return _resp(
            "Você pode abrir ou acompanhar solicitações pela área de Chamados Técnicos. "
            "O Assistente não abre chamados sozinho — a abertura é sempre pelo cliente ou pela equipe Pred.IO.\n\nFonte: Pred.IO",
            links=[{"label": "🔧 Abrir Chamado Técnico", "page": "chamados"}],
        )

    # ── Notificações Portal ───────────────────────────────────────────────────
    if intent == "notificacoes_portal":
        client_id = ctx.get("client_id", "")
        q = pergunta.lower()

        # Orientação sobre ativar notificação de evento específico
        if any(kw in q for kw in ["como ativo", "como ativar", "ativar notificação", "ativar notificacao",
                                   "configurar notificação", "configurar notificacao",
                                   "preferências", "preferencias"]):
            return _resp(
                "Para ativar ou configurar notificações, acesse **Preferências de Notificação** no menu do portal. "
                "Lá você encontra cada tipo de evento (relatórios, alertas, manutenção vencida, chamados, etc.) "
                "com opção de ativar ou desativar individualmente.\n\n"
                "📌 Nesta fase, as notificações são exibidas dentro do Portal Pred.IO. "
                "E-mail e WhatsApp estão preparados para uma próxima etapa.\n\nFonte: Pred.IO",
                links=[
                    {"label": "⚙️ Preferências de Notificação", "page": "preferencias"},
                    {"label": "🔔 Minhas Notificações",          "page": "notificacoes"},
                ],
            )

        # Consulta de não lidas
        unread = 0
        try:
            from notifications import get_unread_count
            unread = get_unread_count(client_id)
        except Exception:
            pass

        if unread == 0:
            return _resp(
                "Você não tem notificações não lidas no portal no momento.",
                links=[{"label": "🔔 Ver Notificações", "page": "notificacoes"}],
            )
        return _resp(
            f"Você tem **{unread} notificação(ões) não lida(s)** no portal. "
            "Acesse para visualizar todas.",
            links=[{"label": f"🔔 Ver {unread} Notificações", "page": "notificacoes"}],
        )

    # ── Alertas ───────────────────────────────────────────────────────────────
    if intent == "alertas":
        alertas_reais = ctx.get("alertas_reais", [])
        alertas_mock  = ctx.get("alertas", [])
        alertas = alertas_reais or alertas_mock
        if not alertas:
            return _resp(
                "Nenhum alerta ativo no momento para sua operação.",
                links=[{"label": "🔔 Ver Alertas", "page": "alertas"}],
            )
        itens = "; ".join(
            f"{a.get('titulo', a.get('Titulo', ''))} ({a.get('prioridade', a.get('Prioridade', ''))})"
            for a in alertas
        )
        return _resp(
            f"Há {len(alertas)} alerta(s) ativo(s): {itens}.\n\nFonte: Pred.IO",
            links=[{"label": "🔔 Ver Alertas", "page": "alertas"}],
        )

    # ── Meta — sobre o Assistente Técnico Pred.IO ────────────────────────────
    if intent == "meta_assistente":
        q = pergunta.lower()
        if any(kw in q for kw in ["substitui", "substitui o técnico", "substitui o tecnico"]):
            return _resp(
                "Não. O Assistente Técnico Pred.IO ajuda a consultar informações técnicas, "
                "organizar dados, explicar alarmes e orientar próximos passos, mas não "
                "substitui avaliação técnica presencial, laudo especializado ou decisão "
                "operacional de segurança.\n\nFonte: Pred.IO",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )
        return _resp(
            "Não. O Assistente Técnico Pred.IO não executa comando na máquina. Ele pode "
            "orientar, indicar condição de atenção ou sugerir abertura de chamado técnico, "
            "mas a decisão de parada, intervenção ou operação deve ser tomada por operador "
            "autorizado, manutenção ou engenharia responsável.\n\nFonte: Pred.IO",
            links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
        )

    # ── Fallback ──────────────────────────────────────────────────────────────
    return _resp(
        "Não encontrei informação suficiente nos dados disponíveis do portal "
        "para responder com segurança. Recomendo abrir um chamado técnico "
        "para avaliação da equipe Pred.IO.\n\nFonte: Pred.IO",
        links=[{"label": "🔧 Abrir Chamado Técnico", "page": "chamados"}],
    )


def _normalizar(texto: str) -> str:
    import re
    t = texto.lower()
    t = re.sub(r'[ãâàáä]', 'a', t)
    t = re.sub(r'[êèéë]', 'e', t)
    t = re.sub(r'[îìíï]', 'i', t)
    t = re.sub(r'[õôòóö]', 'o', t)
    t = re.sub(r'[ûùúü]', 'u', t)
    t = re.sub(r'ç', 'c', t)
    return t


def _buscar_chunk_oleo(ctx: dict) -> dict | None:
    """Busca especificação de óleo nos chunks de documentos indexados."""
    kws_oleo = ["oleo", "lubrificante", "viscosidade", "vdl", "synthetic", "sintetico"]
    for doc in ctx.get("documentos", []):
        for chunk in doc.get("chunks", []):
            hay = _normalizar(
                chunk.get("conteudo", "") + " " + chunk.get("palavras_chave", "")
            )
            if any(kw in hay for kw in kws_oleo):
                return {
                    "answer": (
                        f"Com base no documento <strong>{doc['titulo']}</strong> "
                        f"(Seção: {chunk['titulo_secao']}), encontrei: {chunk['conteudo']}"
                    ),
                    "docs": [{"titulo": doc["titulo"], "id": doc.get("id", "")}],
                }
    return None


def _buscar_chunk_overhaul(ctx: dict) -> dict | None:
    """Busca informações sobre overhaul nos chunks de documentos indexados."""
    kws = ["overhaul", "revisao geral", "horimetro", "vibracao", "termografia"]
    for doc in ctx.get("documentos", []):
        for chunk in doc.get("chunks", []):
            hay = _normalizar(
                chunk.get("conteudo", "") + " " + chunk.get("titulo_secao", "")
            )
            if any(kw in hay for kw in kws):
                return {
                    "answer": (
                        f"Com base no documento <strong>{doc['titulo']}</strong> "
                        f"(Seção: {chunk['titulo_secao']}), encontrei: {chunk['conteudo']}"
                    ),
                    "docs": [{"titulo": doc["titulo"], "id": doc.get("id", "")}],
                }
    return None


def _buscar_chunk_mycom(ctx: dict, pergunta: str) -> dict | None:
    """Busca por palavras-chave da pergunta nos chunks do Manual MYCOM."""
    q_norm = _normalizar(pergunta)
    words = [w for w in q_norm.split() if len(w) > 2]
    if not words:
        return None
    best_score = 0
    best_result = None
    for doc in ctx.get("documentos", []):
        if "mycom" not in doc.get("titulo", "").lower() and "mayekawa" not in doc.get("titulo", "").lower():
            continue
        for chunk in doc.get("chunks", []):
            hay = _normalizar(
                chunk.get("titulo_secao", "") + " "
                + chunk.get("conteudo", "") + " "
                + chunk.get("palavras_chave", "")
            )
            score = sum(1 for w in words if w in hay)
            if score > best_score:
                best_score = score
                best_result = {
                    "answer": (
                        f"Com base no documento <strong>{doc['titulo']}</strong> "
                        f"(Seção: {chunk['titulo_secao']}), encontrei: {chunk['conteudo']}"
                    ),
                    "docs": [{"titulo": doc["titulo"], "id": doc.get("id", "")}],
                }
    return best_result if best_score > 0 else None


def _buscar_chunk_oleo_mycom(ctx: dict, pergunta: str = "") -> dict | None:
    """Busca por especificação de óleo nos chunks da tabela MAYEKAWA/MYCOM."""
    kws = ["oleo", "lubrificante", "mycold", "pao", "poe", "mineral", "homologado",
           "reflo", "rab", "gargoyle", "esso", "icematic", "capella"]
    for doc in ctx.get("documentos", []):
        if "mayekawa" not in doc.get("titulo", "").lower() and "oleo" not in doc.get("titulo", "").lower():
            continue
        for chunk in doc.get("chunks", []):
            hay = _normalizar(
                chunk.get("conteudo", "") + " " + chunk.get("palavras_chave", "")
            )
            q_norm = _normalizar(pergunta) if pergunta else ""
            q_words = [w for w in q_norm.split() if len(w) > 2]
            score_q = sum(1 for w in q_words if w in hay) if q_words else 0
            score_kw = sum(1 for kw in kws if kw in hay)
            if score_q > 0 or score_kw >= 2:
                return {
                    "answer": (
                        f"Com base no documento <strong>{doc['titulo']}</strong> "
                        f"(Seção: {chunk['titulo_secao']}), encontrei: {chunk['conteudo']}"
                    ),
                    "docs": [{"titulo": doc["titulo"], "id": doc.get("id", "")}],
                }
    return None


def _buscar_chunks_geral(ctx: dict, pergunta: str) -> dict | None:
    """Busca por palavras-chave da pergunta nos chunks de todos os docs autorizados."""
    q_norm = _normalizar(pergunta)
    words = [w for w in q_norm.split() if len(w) > 2]
    if not words:
        return None
    best_score = 0
    best_result = None
    for doc in ctx.get("documentos", []):
        for chunk in doc.get("chunks", []):
            hay = _normalizar(
                chunk.get("titulo_secao", "") + " "
                + chunk.get("conteudo", "") + " "
                + chunk.get("palavras_chave", "")
            )
            score = sum(1 for w in words if w in hay)
            if score > best_score:
                best_score = score
                best_result = {
                    "answer": (
                        f"Com base no documento <strong>{doc['titulo']}</strong> "
                        f"(Seção: {chunk['titulo_secao']}), encontrei: {chunk['conteudo']}"
                    ),
                    "docs": [{"titulo": doc["titulo"], "id": doc.get("id", "")}],
                }
    return best_result if best_score > 0 else None


def _resp(
    answer: str,
    links: list | None = None,
    documents: list | None = None,
    reports: list | None = None,
    actions: list | None = None,
) -> dict:
    return {
        "answer":            answer,
        "related_links":     links     or [],
        "related_documents": documents or [],
        "related_reports":   reports   or [],
        "suggested_actions": actions   or [],
    }
