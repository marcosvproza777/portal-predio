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
    ],
    "chamados": [
        "chamado", "abrir chamado", "solicitação", "solicitacao",
        "atendimento", "suporte", "problema", "defeito", "urgente",
        "solicitar", "técnico", "tecnico",
    ],
    "alertas": [
        "alerta", "aviso", "notificação", "notificacao", "ponto de atenção",
        "ponto de atencao",
    ],
}


def detect_intent(pergunta: str) -> str:
    """
    Identifica a intenção da pergunta.
    A ordem importa — intents mais específicos aparecem primeiro.
    """
    q = pergunta.lower()
    for intent in [
        "mycold",           # MYCOLD AB/PAO — antes de qualquer oleo
        "oleo_homologado",  # Tabela de óleos MAYEKAWA/MYCOM
        "revisao_condicao", # 20k horas / overhaul / kit revisão
        "mycom_manual",     # Manual MYCOM / Sistema Chiller
        "oleo",             # Óleo genérico
        "manutencao",       # Plano de manutenção
        "relatorios",
        "documentos",
        "status_ativo",
        "chamados",
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

    # ── Manual MYCOM / Sistema Chiller ────────────────────────────────────────
    if intent == "mycom_manual":
        q = pergunta.lower()

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
        mans = ctx.get("manutencoes", [])
        if not mans:
            return _resp(
                "Não encontrei planos de manutenção cadastrados para sua operação. "
                "Recomendo abrir um chamado técnico para que a equipe Pred.IO verifique.",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )
        itens_str = "; ".join(
            (m.get("vencimento_data") and f"{m['acao']} em {m['vencimento_data']}")
            or (m.get("vencimento_horas") and f"{m['acao']} em {m['vencimento_horas']} horas")
            or m["acao"]
            for m in mans
        )
        # Resposta segura sobre overhaul: não depende só do horímetro
        q_lower = pergunta.lower()
        if any(kw in q_lower for kw in ["overhaul", "revisão geral", "revisao geral"]):
            overhaul_note = _buscar_chunk_overhaul(ctx)
            if overhaul_note:
                return _resp(overhaul_note["answer"],
                             links=[{"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                                    {"label": "📚 Ver Manual", "page": "biblioteca"}],
                             documents=overhaul_note.get("docs", []))
            return _resp(
                "O overhaul não é determinado apenas pelo horímetro. "
                "A decisão deve considerar vibração, análise de óleo, termografia e histórico de falhas. "
                "Consulte o manual técnico ou a equipe Pred.IO para avaliar o momento adequado.",
                links=[{"label": "📅 Ver Plano de Manutenção", "page": "manutencao"},
                       {"label": "📚 Abrir Biblioteca Técnica", "page": "biblioteca"}],
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
        chams = ctx.get("chamados", [])
        answer = "Você pode abrir ou acompanhar solicitações pela área de Chamados Técnicos."
        if chams:
            c = chams[0]
            answer += f" Há um chamado em aberto: \"{c['titulo']}\" (status: {c['status']})."
        return _resp(answer, links=[{"label": "🔧 Abrir Chamados Técnicos", "page": "chamados"}])

    # ── Alertas ───────────────────────────────────────────────────────────────
    if intent == "alertas":
        alertas = ctx.get("alertas", [])
        if not alertas:
            return _resp(
                "Nenhum alerta ativo no momento para sua operação.",
                links=[{"label": "🔔 Ver Alertas", "page": "alertas"}],
            )
        itens = "; ".join(f"{a['titulo']} ({a['prioridade']})" for a in alertas)
        return _resp(
            f"Há {len(alertas)} alerta(s) ativo(s): {itens}.",
            links=[{"label": "🔔 Ver Alertas", "page": "alertas"}],
        )

    # ── Fallback ──────────────────────────────────────────────────────────────
    return _resp(
        "Não encontrei informação suficiente nos dados disponíveis do portal "
        "para responder com segurança. Recomendo abrir um chamado técnico "
        "para avaliação da equipe Pred.IO.",
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
