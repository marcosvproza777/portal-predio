"""
Assistente Técnico Pred.IO com IA controlada.

ARQUITETURA DE INTEGRAÇÃO (Opção A — backend direto):
  Streamlit (Python, servidor Render.com)
      → monta contexto autorizado
      → chama Anthropic API (server-side, nunca browser)
      → retorna resposta estruturada

  Opção B (n8n) disponível como fallback em assistant.py se
  ANTHROPIC_API_KEY não estiver configurada e N8N_ASSISTANT_WEBHOOK_URL sim.

SEGURANÇA OBRIGATÓRIA:
  ✓ ANTHROPIC_API_KEY em variável de ambiente do servidor — nunca no front-end
  ✓ client_id SEMPRE da sessão/autenticação — nunca do front-end
  ✓ Contexto filtrado por client_id antes de enviar para IA
  ✓ Documentos internos e de outros clientes excluídos ANTES do prompt
  ✓ Observações internas NUNCA incluídas no contexto enviado à IA
  ✓ IA responde apenas com base no contexto fornecido (imposto pelo system prompt)
"""

from __future__ import annotations
import json
import os
import re as _re
import unicodedata as _ud

from assistant_engine import get_client_context, detect_intent, _build_response

_STOP_TOKENS_RESUMO = {
    "que", "para", "com", "uma", "das", "dos", "por", "sem", "mais",
    "esta", "esse", "essa", "isso", "foi", "sao", "tem", "nos", "nas",
    "dentro", "esta", "sobre",
}


def _tokenizar_resumo(texto: str) -> set[str]:
    n = _ud.normalize("NFD", (texto or "").lower())
    n = "".join(c for c in n if _ud.category(c) != "Mn")
    palavras = _re.findall(r"[a-z0-9]+", n)
    return {p for p in palavras if len(p) > 3 and p not in _STOP_TOKENS_RESUMO}


def _detectar_uso_resumo_tecnico(ctx: dict, answer: str) -> dict:
    """Auditoria (item 13/16): detecta se resumo_tecnico foi mesmo a base
    da resposta final — sem isso não dá pra saber, pela planilha de logs,
    se o Assistente realmente usou o campo ou só tinha acesso a ele.

    Não há como instrumentar a chamada à Anthropic API por dentro (é uma
    chamada de terceiro, a resposta já vem pronta) — a heurística compara
    a resposta final com o resumo_tecnico de cada relatório publicado no
    contexto do cliente: se uma fração relevante das palavras do resumo
    aparece na resposta, considera que aquele resumo foi usado. Funciona
    tanto para a resposta da IA quanto para o motor de fallback (mesma
    função, mesmo critério, sem duplicar lógica nos dois caminhos)."""
    answer_tokens = _tokenizar_resumo(answer)
    disponiveis: list[str] = []
    usado_em = ""
    if answer_tokens:
        for rep in ctx.get("relatorios_tecnicos_indexados", []):
            resumo = (rep.get("resumo") or "").strip()
            if not resumo:
                continue
            rep_id = rep.get("id", "")
            if rep_id:
                disponiveis.append(rep_id)
            resumo_tokens = _tokenizar_resumo(resumo)
            if not resumo_tokens:
                continue
            overlap = len(resumo_tokens & answer_tokens) / len(resumo_tokens)
            if overlap >= 0.35 and not usado_em:
                usado_em = rep_id
    return {
        "usou_resumo_tecnico": bool(usado_em),
        "report_id_resumo_usado": usado_em,
        "reports_com_resumo_disponivel": disponiveis,
    }

_SYSTEM_PROMPT = """\
Você é o Nico, o Assistente Técnico Pred.IO.

Você auxilia clientes a entender informações técnicas dos ativos monitorados,
relatórios, planos de manutenção, chamados, alertas e documentos disponíveis no portal.

REGRA ESPECIAL — SEU NOME:
- Seu nome é Nico. Isso é um fato sobre você, não um dado técnico do cliente —
  NUNCA se aplica a ele a regra de "responda só com base no contexto" abaixo.
- Se perguntarem seu nome, quem você é, ou algo do tipo, responda diretamente
  "Sou o Nico" (ou variação natural) — nunca diga que não tem essa informação
  no contexto, nunca hesite, nunca se identifique só como "Assistente Técnico
  Pred.IO" sem o nome.

REGRAS OBRIGATÓRIAS (aplicam-se a dados TÉCNICOS do cliente — ativos, relatórios,
manutenção, especificações — não à sua própria identidade, já estabelecida acima):
- Responda SOMENTE com base no contexto técnico fornecido nesta mensagem.
- Não invente informação técnica, especificação de óleo, torque, temperatura, pressão, prazo ou procedimento.
- Não afirme que algo está em um manual se a informação não estiver no contexto fornecido.
- Se a informação não estiver disponível no contexto, diga claramente que não encontrou base suficiente.
- Cite a fonte sempre que possível (nome do documento, plano de manutenção, relatório, seção).
- Para decisões críticas (overhaul, troca de rolamento, parada de equipamento, intervenção pesada),
  recomende abertura de chamado ou avaliação da equipe Pred.IO — nunca tome a decisão sozinho.
- Não revele observações internas, documentos internos ou dados de outros clientes.
- Mantenha resposta objetiva, técnica e segura.
- Se a pergunta envolver risco operacional, falha crítica, parada de máquina ou segurança,
  oriente imediatamente a abertura de chamado técnico.

REGRA ESPECIAL — 20.000 HORAS:
- A revisão de 20.000 horas do manual MYCOM é REFERÊNCIA TÉCNICA, não gatilho automático de overhaul.
- NUNCA recomende overhaul, desmontagem do compressor, kit revisão ou intervenção pesada apenas por horímetro.
- A decisão deve considerar: análise de vibração, análise de óleo, termografia, histórico operacional,
  tendência de score de saúde, falhas recorrentes e avaliação técnica da equipe Pred.IO.
- Frase obrigatória quando o assunto surgir: "20.000 horas é referência técnica, não gatilho automático
  de overhaul. A decisão depende da saúde real da máquina."

REGRA ESPECIAL — ÓLEO MYCOLD:
- MYCOLD AB 68 foi DESCONTINUADO. Nunca recomende MYCOLD AB 68 como óleo atual.
- Quando o cliente perguntar sobre MYCOLD AB 68, responda que foi descontinuado e substituído por MYCOLD PAO.
- O óleo MYCOM homologado atual no Portal Pred.IO é MYCOLD PAO.
- Nunca use MYCOLD AB 68 em plano de manutenção ou recomendação de óleo.

REGRA ESPECIAL — ÓLEOS HOMOLOGADOS:
- ISO VG 68 é apenas um dos critérios. A seleção depende do fluido refrigerante, classe do lubrificante
  (PAO, POE, mineral), aplicação, condição operacional e tabela homologada MAYEKAWA/MYCOM.
- Nunca recomende substituição de óleo sem validação técnica.
- Sempre citar a Tabela de Óleos Homologados MAYEKAWA/MYCOM como fonte.

REGRA ESPECIAL — PAINEL MYPRO TOUCH / MYPRO TOUCH AD:
- A nomenclatura correta é SEMPRE "Mypro Touch" ou "Mypro Touch AD".
- NUNCA usar "Mypro Touch+", "MYPRO Touch+", "MyproTouch+", "Touch Plus" ou qualquer variação com "+".
- Para partida, parada, reset de alarme, alteração de set point ou capacidade:
  adicionar sempre "Use apenas se você for operador autorizado."
- O Assistente Técnico Pred.IO NÃO executa comando na máquina. Apenas orienta.

REGRA ESPECIAL — TEMPERATURA DE DESCARGA:
- Para compressor alternativo: referência 80 °C a 140 °C.
- Para compressor parafuso: referência até 90 °C.
- Sempre perguntar ou considerar o tipo de compressor antes de avaliar temperatura.

REGRA ESPECIAL — PRIORIZAÇÃO GUT (Gravidade x Urgência x Tendência):
- GUT é uma ferramenta de priorização técnica (nota 1-5 em cada eixo, score = G x U x T, 1-125).
- Faixas: 1-20 Baixa, 21-50 Moderada, 51-80 Alta, 81-125 Crítica.
- Use os dados de "=== PRIORIZAÇÃO GUT ===" no contexto para responder perguntas como
  "qual item é mais crítico", "qual ativo tem maior prioridade", "o que devo fazer primeiro".
- GUT alto (Crítica/Alta) indica PRIORIDADE DE ANÁLISE — nunca autoriza sozinho overhaul,
  troca de rolamento, parada de máquina ou qualquer intervenção automática.
- Para item com prioridade GUT Crítica, sempre recomende abrir chamado técnico.
- Frase obrigatória ao explicar GUT: "GUT é uma ferramenta de priorização e não substitui
  a avaliação técnica da equipe Pred.IO."

REGRA ESPECIAL — PRIORIDADE DE LEITURA DO RELATÓRIO TÉCNICO:
- Cada relatório técnico pode ter um Resumo Técnico preenchido manualmente
  pela equipe Pred.IO na Supervisão — é a fonte PRIORITÁRIA sobre aquele
  relatório quando presente (marcado no contexto como "Resumo Técnico
  (fonte prioritária)").
- Ordem de prioridade ao responder sobre um relatório: (1) Resumo Técnico,
  (2) Diagnóstico, (3) Conclusão, (4) Recomendações, (5) Severidade e GUT,
  (6) medições estruturadas, (7) trechos indexados do relatório (chunks),
  (8) texto extraído do PDF.
- Se o Resumo Técnico existir, use-o como base principal da resposta sobre
  aquele relatório — os demais campos complementam, nunca substituem.
- Se o PDF de um relatório não estiver indexado, mas houver Resumo Técnico,
  Diagnóstico, Conclusão ou Recomendações preenchidos, responda normalmente
  com base neles — nunca bloqueie a resposta só por falta de PDF indexado.

REGRA ESPECIAL — FONTE:
- A fonte exibida ao cliente deve ser sempre "Pred.IO".
- Não inventar informação técnica. Se não houver base suficiente, responder:
  "Não encontrei informação suficiente na base Pred.IO. Recomendo abrir chamado técnico."

REGRA ESPECIAL — DOCUMENTOS INTERNOS:
- Documentos com visibilidade "Apenas equipe Pred.IO" nunca devem ser mencionados ou revelados ao cliente.
- Observações internas de chamados e relatórios nunca devem aparecer na resposta.

FORMATO DE RESPOSTA — responda SOMENTE com JSON válido, sem texto fora do JSON:
{
  "answer": "texto da resposta técnica em português",
  "confidence": "alta",
  "sources": [
    {"titulo": "nome da fonte", "tipo": "Manual|Relatório|Plano de Manutenção|Alerta|Chamado|Tabela técnica", "secao": "seção se disponível"}
  ],
  "related_documents": [{"titulo": "...", "id": "..."}],
  "related_reports": [{"titulo": "...", "data": "..."}],
  "suggested_actions": [{"label": "...", "page": "biblioteca|chamados|manutencao|relatorios|ativos|alertas"}]
}

Regras de confiança:
- "alta": resposta baseada em fonte direta (manual com texto, plano com data, relatório com resultado específico)
- "media": resposta baseada em correlação entre fontes disponíveis
- "baixa": não há fonte suficiente ou há dúvida técnica relevante — SEMPRE adicionar chamado em suggested_actions
"""


def _build_context_str(ctx: dict) -> str:
    """
    Constrói o contexto técnico estruturado para envio à IA.

    SEGURANÇA: recebe ctx já filtrado por client_id — sem dados internos
    ou de outros clientes. Observações internas nunca chegam aqui.
    """
    parts: list[str] = []

    # Ativos e componentes
    ativos = ctx.get("ativos", [])
    if ativos:
        parts.append("=== ATIVOS MONITORADOS ===")
        for a in ativos:
            linha = f"• {a['nome']} — Status: {a['status']}, Score: {a['score']}/100"
            comps = a.get("componentes", [])
            if comps:
                linha += "\n  Componentes: " + ", ".join(
                    f"{c['nome']} [{c['status']}]" for c in comps
                )
            parts.append(linha)

    # Plano de manutenção
    mans = ctx.get("manutencoes", [])
    if mans:
        parts.append("\n=== PLANO DE MANUTENÇÃO ===")
        for m in mans:
            prazo = (
                m.get("vencimento_data")
                or (f"{m['vencimento_horas']}h" if m.get("vencimento_horas") else "indefinido")
            )
            parts.append(f"• {m['acao']} [{m.get('tipo','')}] — Ativo: {m.get('ativo','')} — Prazo: {prazo}")

    # Relatórios técnicos
    rels = ctx.get("relatorios", [])
    if rels:
        parts.append("\n=== RELATÓRIOS TÉCNICOS ===")
        for r in rels:
            parts.append(f"• {r['titulo']} — {r.get('data','')}")

    # Tarefas de manutenção reais
    tarefas = ctx.get("tarefas_manutencao", [])
    if tarefas:
        parts.append("\n=== PLANO DE MANUTENÇÃO — TAREFAS ===")
        for t in tarefas:
            linha = f"• {t.get('nome','')} [{t.get('tipo','')}] — Status: {t.get('status','')} — Ativo: {t.get('ativo_id','')}"
            if t.get("prox_data"):
                linha += f" — Próx. data: {t['prox_data']}"
            if t.get("gut_prioridade"):
                linha += f" — GUT: {t['gut_score']} ({t['gut_prioridade']})"
            if t.get("recomendacao"):
                linha += f"\n  Recomendação: {t['recomendacao']}"
            parts.append(linha)

    # Relatórios técnicos indexados com chunks
    reps_idx = ctx.get("relatorios_tecnicos_indexados", [])
    if reps_idx:
        parts.append("\n=== RELATÓRIOS TÉCNICOS — CONTEÚDO INDEXADO ===")
        for rep in reps_idx:
            linha_rep = (
                f"• {rep.get('titulo','')} — Sev: {rep.get('severidade','')} — "
                f"Data: {rep.get('data','')} — Ativo: {rep.get('ativo','')}"
            )
            if rep.get("gut_prioridade"):
                linha_rep += f" — GUT: {rep.get('gut_score','')} ({rep['gut_prioridade']})"
            parts.append(linha_rep)
            chunks = rep.get("chunks", [])
            if chunks:
                # Chunks já refletem a ordem de prioridade (Resumo Técnico →
                # Diagnóstico → Conclusão → Recomendações → medições → PDF),
                # ver sheets.index_relatorio_tecnico().
                for ch in chunks:
                    secao    = ch.get("titulo_secao", "")
                    conteudo = ch.get("conteudo", "")
                    if conteudo:
                        parts.append(f"  [{secao}]: {conteudo}")
            else:
                # Sem chunks (PDF ainda não indexado, ou relatório antigo) —
                # ainda assim responde com os campos estruturados disponíveis,
                # na mesma ordem de prioridade: resumo técnico → diagnóstico →
                # conclusão → recomendações. Nunca bloqueia a resposta.
                if rep.get("resumo"):
                    parts.append(f"  [Resumo Técnico (fonte prioritária)]: {rep['resumo']}")
                if rep.get("diagnostico"):
                    parts.append(f"  [Diagnóstico]: {rep['diagnostico']}")
                if rep.get("conclusao"):
                    parts.append(f"  [Conclusão]: {rep['conclusao']}")
                if rep.get("recomendacoes"):
                    parts.append(f"  [Recomendações]: {rep['recomendacoes']}")

    # Relatórios executivos publicados
    exec_reps = ctx.get("relatorios_executivos", [])
    if exec_reps:
        parts.append("\n=== RELATÓRIOS EXECUTIVOS PUBLICADOS ===")
        for er in exec_reps:
            parts.append(
                f"• {er.get('titulo','')} — Período: {er.get('periodo','')} — Ativo: {er.get('ativo_id','')} — Versão: {er.get('versao','')}"
            )
            if er.get("resumo_executivo"):
                parts.append(f"  Resumo executivo: {er['resumo_executivo']}")

    # Chamados reais (prioridade sobre mock)
    chams_reais = ctx.get("chamados_reais", [])
    chams_mock  = ctx.get("chamados", [])
    chams = chams_reais or chams_mock
    if chams:
        parts.append("\n=== CHAMADOS TÉCNICOS ===")
        for c in chams:
            titulo   = c.get("titulo",    c.get("Titulo",    ""))
            status   = c.get("status",    c.get("Status",    ""))
            prior    = c.get("prioridade",c.get("Prioridade",""))
            ativo    = c.get("ativo_id",  c.get("Ativo_Id",  ""))
            linha    = f"• {titulo} — Status: {status}"
            if prior:
                linha += f" ({prior})"
            if ativo:
                linha += f" — Ativo: {ativo}"
            parts.append(linha)

    # Alertas reais (prioridade sobre mock)
    alertas_reais = ctx.get("alertas_reais", [])
    alertas_mock  = ctx.get("alertas", [])
    als = alertas_reais or alertas_mock
    if als:
        parts.append("\n=== ALERTAS ATIVOS ===")
        for a in als:
            titulo    = a.get("titulo",     a.get("Titulo",     ""))
            prioridade= a.get("prioridade", a.get("Prioridade", ""))
            descricao = a.get("descricao",  "")
            linha     = f"• {titulo} — Prioridade: {prioridade}"
            if descricao:
                linha += f"\n  {descricao}"
            parts.append(linha)

    # Priorização GUT (Gravidade x Urgência x Tendência)
    gut_itens = ctx.get("gut_summary", [])
    if gut_itens:
        parts.append("\n=== PRIORIZAÇÃO GUT (maior score primeiro) ===")
        for g in gut_itens[:15]:
            linha = f"• [{g.get('origem','')}] {g.get('titulo','')} — GUT {g.get('score','')} ({g.get('prioridade','')})"
            if g.get("ativo_id"):
                linha += f" — Ativo: {g['ativo_id']}"
            parts.append(linha)

    # Especificações
    spec = ctx.get("especificacoes", {})
    if spec.get("oleo"):
        parts.append(f"\n=== ESPECIFICAÇÕES ===\n• Óleo recomendado: {spec['oleo']}")

    # Documentos e chunks (maior valor para IA)
    docs = ctx.get("documentos", [])
    if docs:
        parts.append("\n=== BIBLIOTECA TÉCNICA — DOCUMENTOS AUTORIZADOS ===")
        for d in docs:
            doc_line = f"• [{d.get('tipo_documento','')}] {d['titulo']}"
            if d.get("modelo"):
                doc_line += f" — Modelo: {d['modelo']}"
            if d.get("resumo"):
                doc_line += f"\n  Resumo: {d['resumo']}"
            parts.append(doc_line)

            # Chunks indexados — conteúdo real do manual
            chunks = d.get("chunks", [])
            if chunks:
                parts.append(f"  Conteúdo indexado do documento '{d['titulo']}':")
                for ch in chunks:
                    secao = ch.get("titulo_secao", "")
                    conteudo = ch.get("conteudo", "")
                    pagina = ch.get("pagina_inicio", "")
                    chunk_line = f"    [{secao}{'  pag. '+pagina if pagina else ''}]: {conteudo}"
                    parts.append(chunk_line)

    return "\n".join(parts) if parts else "Nenhum dado técnico disponível para este cliente."


def _parse_ai_response(raw: str, ctx: dict) -> dict:
    """
    Tenta interpretar a resposta JSON da IA.
    Fallback robusto: se parsing falhar, usa o texto como answer.
    """
    raw = raw.strip()
    # Remove possível markdown code block
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()

    try:
        data = json.loads(raw)
        return {
            "answer":            str(data.get("answer", raw)),
            "confidence":        str(data.get("confidence", "media")),
            "sources":           data.get("sources", []),
            "related_documents": data.get("related_documents", []),
            "related_reports":   data.get("related_reports", []),
            "suggested_actions": data.get("suggested_actions", []),
        }
    except (json.JSONDecodeError, Exception):
        # Extrai texto útil do raw se não for JSON
        return {
            "answer":            raw or "Não foi possível processar a resposta. Tente novamente.",
            "confidence":        "baixa",
            "sources":           [],
            "related_documents": [],
            "related_reports":   [],
            "suggested_actions": [{"label": "🔧 Abrir Chamado", "page": "chamados"}],
        }


def _fallback_engine(
    client_id: str, pergunta: str, ativo_id: str = ""
) -> dict:
    """Usa o motor controlado sem IA como fallback seguro."""
    ctx = get_client_context(client_id)
    intent = detect_intent(pergunta)
    result = _build_response(intent, ctx, pergunta, ativo_id)
    resposta = {
        "answer":            result.get("answer", ""),
        "confidence":        "media",
        "sources":           [],
        "related_documents": result.get("related_documents", []),
        "related_reports":   result.get("related_reports", []),
        "suggested_actions": result.get("related_links", []),
    }
    resposta.update(_detectar_uso_resumo_tecnico(ctx, resposta["answer"]))
    return resposta


def query_ai(
    client_id: str,
    pergunta: str,
    rota_atual: str = "",
    ativo_id: str = "",
    componente_id: str = "",
) -> dict:
    """
    Ponto de entrada principal do assistente com IA controlada.

    SEGURANÇA:
      - client_id SEMPRE da sessão (nunca do front-end)
      - Contexto montado server-side a partir de dados autorizados
      - ANTHROPIC_API_KEY em variável de ambiente — nunca exposta ao cliente
      - IA recebe apenas contexto já filtrado

    Prioridade:
      1. Anthropic API (Option A — backend direto) se ANTHROPIC_API_KEY configurado
      2. Fallback: motor controlado sem IA (assistant_engine)

    Para n8n: use assistant.call_assistant() que já tem esse fluxo.
    """
    if not client_id:
        return {
            "answer": "Sessão não identificada. Por favor, faça login novamente.",
            "confidence": "baixa",
            "sources": [],
            "related_documents": [],
            "related_reports": [],
            "suggested_actions": [],
        }

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    if not api_key:
        # Sem API key: usa motor controlado (sem IA)
        return _fallback_engine(client_id, pergunta, ativo_id)

    # Monta contexto seguro server-side
    ctx = get_client_context(client_id)
    context_str = _build_context_str(ctx)

    user_message = (
        f"CONTEXTO TÉCNICO DO CLIENTE (dados autorizados, filtrados server-side):\n\n"
        f"{context_str}\n\n"
        f"---\n"
        f"PERGUNTA DO CLIENTE: {pergunta}\n\n"
        f"Responda com base EXCLUSIVAMENTE no contexto acima. "
        f"Se a informação não estiver disponível no contexto, diga que não encontrou base suficiente. "
        f"Retorne SOMENTE JSON válido no formato especificado."
    )

    if rota_atual:
        user_message += f"\n(Rota atual do cliente no portal: {rota_atual})"
    if ativo_id:
        user_message += f"\n(Ativo em foco: {ativo_id})"

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = message.content[0].text
        result = _parse_ai_response(raw, ctx)
        result.update(_detectar_uso_resumo_tecnico(ctx, result.get("answer", "")))
        return result

    except ImportError as exc:
        import sys as _sys
        print(f"[query_ai] anthropic nao instalado: {exc}", file=_sys.stderr, flush=True)
        return _fallback_engine(client_id, pergunta, ativo_id)
    except Exception as exc:
        import sys as _sys
        print(f"[query_ai] falha na API: {type(exc).__name__}: {exc}", file=_sys.stderr, flush=True)
        return _fallback_engine(client_id, pergunta, ativo_id)


def answer_about_report(pergunta: str, contexto_relatorio: str) -> str | None:
    """Responde uma pergunta específica sobre UM relatório já localizado
    (por assistant_lookup.rotear_pergunta) — mesmo motor/prompt de domínio
    de query_ai(), mas com contexto pequeno e focado (só os campos desse
    relatório, já organizados por summarize_technical_report na ordem de
    prioridade certa) em vez do contexto completo do cliente. Existe pra
    trocar a resposta por concatenação de campos (rasa) por uma síntese de
    verdade, sem perder a vantagem de já saber qual relatório é o certo.

    Retorna None se a IA não estiver configurada ou a chamada falhar — quem
    chama deve usar o texto determinístico já calculado como reserva."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None

    user_message = (
        f"RELATÓRIO TÉCNICO (dados autorizados, já localizado pelo sistema "
        f"como o relatório relevante para esta pergunta):\n\n"
        f"{contexto_relatorio}\n\n"
        f"---\n"
        f"PERGUNTA DO CLIENTE: {pergunta}\n\n"
        f"Responda com base EXCLUSIVAMENTE nos dados do relatório acima. "
        f"Retorne SOMENTE JSON válido no formato especificado."
    )
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = message.content[0].text
        result = _parse_ai_response(raw, {})
        return result.get("answer") or None
    except Exception as exc:
        import sys as _sys
        print(f"[answer_about_report] falhou: {type(exc).__name__}: {exc}", file=_sys.stderr, flush=True)
        return None


def is_critical_question(pergunta: str) -> bool:
    """
    Detecta perguntas de risco operacional que exigem abertura de chamado.
    Complementa assistant.is_critical() com termos técnicos específicos.
    """
    critical_kws = [
        "parada", "parou", "travou", "quebrou", "explosão", "vazamento",
        "incêndio", "risco", "urgente", "emergência", "crítico", "falha grave",
        "acidente", "perigo", "segurança", "posso continuar", "posso operar",
        "posso ignorar", "parar a máquina", "parar o compressor",
        "troco o rolamento", "troca do rolamento", "intervenção",
    ]
    q = pergunta.lower()
    return any(kw in q for kw in critical_kws)
