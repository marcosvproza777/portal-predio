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
    "manutencao": [
        "manutenção", "manutencao", "próxima", "proxima", "plano", "vencimento",
        "horímetro", "horimetro", "análise de óleo", "analise de oleo",
        "vibração", "vibracao", "termografia", "preventiva", "preditiva",
        "inspeção", "inspecao", "overhaul", "lubrificação", "lubrificacao",
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
        "qual óleo", "qual oleo", "óleo usar", "oleo usar",
        "especificação de óleo", "especificacao de oleo",
        "óleo recomendado", "oleo recomendado",
        "tipo de óleo", "tipo de oleo",
        "viscosidade", "lubrificante recomendado",
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
    Retorna a chave do intent ou 'nao_encontrado'.
    A ordem importa: 'oleo' antes de 'manutencao' para capturar perguntas específicas.
    """
    q = pergunta.lower()
    for intent in ["oleo", "manutencao", "relatorios", "documentos",
                   "status_ativo", "chamados", "alertas"]:
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

    # FUTURE: Descomente e adapte quando os sheets estiverem prontos:
    # try:
    #     from sheets import get_ativos_cliente, get_manutencoes_cliente, ...
    #     return _build_from_sheets(client_id)
    # except Exception:
    #     pass

    from assistant_mock_data import get_mock_context
    ctx = get_mock_context(client_id)
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


def _build_response(intent: str, ctx: dict, pergunta: str, ativo_id: str = "") -> dict:
    """Constrói a resposta controlada para a intenção detectada."""

    empresa = ctx.get("empresa", "sua operação")

    # ── Manutenção ────────────────────────────────────────────────────────────
    if intent == "manutencao":
        mans = ctx.get("manutencoes", [])
        if not mans:
            return _resp(
                "Não encontrei planos de manutenção cadastrados para sua operação. "
                "Recomendo abrir um chamado técnico para que a equipe Pred.IO verifique.",
                links=[{"label": "🔧 Abrir Chamado", "page": "chamados"}],
            )
        itens = []
        for m in mans:
            prazo = (
                m.get("vencimento_data")
                or (f"{m['vencimento_horas']}h" if m.get("vencimento_horas") else "a definir")
            )
            itens.append(f"• {m['acao']} — {prazo}")
        answer = (
            "As próximas ações programadas são: "
            + "; ".join(
                (m.get("vencimento_data") and f"{m['acao']} em {m['vencimento_data']}")
                or (m.get("vencimento_horas") and f"{m['acao']} em {m['vencimento_horas']} horas")
                or m["acao"]
                for m in mans
            ) + "."
        )
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

    # ── Especificação de óleo (intent mais específico) ────────────────────────
    if intent == "oleo":
        spec = ctx.get("especificacoes", {}).get("oleo")
        if spec:
            return _resp(
                f"O óleo recomendado para esta unidade é: {spec}.",
                links=[{"label": "📚 Ver Manual", "page": "biblioteca"}],
            )
        return _resp(
            "Não encontrei especificação de óleo cadastrada para este ativo. "
            "Consulte o manual técnico disponível na Biblioteca Técnica ou abra "
            "um chamado para validação da equipe Pred.IO.",
            links=[{"label": "📚 Abrir Biblioteca Técnica", "page": "biblioteca"},
                   {"label": "🔧 Abrir Chamado", "page": "chamados"}],
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
