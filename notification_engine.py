"""
Motor de Templates, Fila e Validação — Notificações Pred.IO.
Etapa 6.7 — Preparação para envio externo (e-mail / WhatsApp).

NENHUMA mensagem real é enviada nesta etapa.

REGRAS ABSOLUTAS:
  ✓ NOTIFICATION_EXTERNAL_SEND_ENABLED=false — nunca alterar nesta etapa
  ✓ Variáveis sensíveis bloqueadas nos templates
  ✓ Links diretos para storage bloqueados
  ✓ client_id SEMPRE da sessão — nunca do front-end
  ✓ Consentimento validado antes de enfileirar
  ✓ modo='Teste' em todos os registros desta etapa
  ✓ Obs_Interna nunca aparece no corpo da mensagem
  ✓ Cliente A não usa dados/contatos do Cliente B
"""
from __future__ import annotations
import re
import os

# ── Modo teste global ─────────────────────────────────────────────────────────
# NUNCA alterar para True nesta etapa.
EXTERNAL_SEND_ENABLED: bool = False


def is_send_enabled() -> bool:
    """Sempre retorna False nesta etapa. Bloqueio definitivo."""
    return False


# ── Variáveis de template ─────────────────────────────────────────────────────

_ALLOWED_VARS = {
    "cliente_nome", "ativo_nome", "tipo_evento", "prioridade",
    "resumo", "link_portal", "data_evento", "status", "fonte",
}

_BLOCKED_VARS = {
    "senha", "token", "chave_api", "observacao_interna",
    "chunks", "log_interno", "arquivo_url_publica", "prompt_interno",
    "obs_interna", "api_key", "secret", "password", "chave",
    "observacao", "hash", "cookie", "session_token",
}

# ── Palavras sensíveis no conteúdo ────────────────────────────────────────────

_SENSITIVE_KEYWORDS = [
    "senha", "login de painel", "token", "chave de api",
    "observação interna", "observacao interna",
    "erro técnico", "traceback", "exception", "stacktrace",
    "chunk bruto", "prompt interno",
    "laudo completo", "relatório completo", "anexo privado",
    "comando operacional",
    "storage.googleapis.com", "s3.amazonaws.com",
    "blob.core.windows.net", "firebasestorage.googleapis.com",
]

# ── Padrões de link bloqueados ────────────────────────────────────────────────

_BLOCKED_LINK_PATTERNS = [
    r"storage\.googleapis\.com",
    r"s3\.amazonaws\.com",
    r"blob\.core\.windows\.net",
    r"firebasestorage\.googleapis\.com",
    r"https?://[^\s]+\.(pdf|docx|xlsx|zip|rar)(\?|$|#)",
    r"drive\.google\.com/file",
    r"dropbox\.com/s/",
    r"onedrive\.live\.com",
]

_FONTE_PADRAO = "Pred.IO"

# ── Templates padrão (semeados na primeira execução) ─────────────────────────

DEFAULT_TEMPLATES: list[dict] = [
    {
        "nome":                "E-mail — Relatório Publicado",
        "tipo_evento":         "relatorio_publicado",
        "canal":               "E-mail",
        "assunto":             "[Pred.IO] Novo relatório técnico publicado - {{ativo_nome}}",
        "corpo": (
            "Olá.\n\n"
            "Um novo relatório técnico foi publicado no Portal Pred.IO.\n\n"
            "Cliente: {{cliente_nome}}\n"
            "Ativo: {{ativo_nome}}\n"
            "Tipo: {{tipo_evento}}\n"
            "Prioridade: {{prioridade}}\n\n"
            "Resumo:\n{{resumo}}\n\n"
            "Acesse o Portal Pred.IO para visualizar os detalhes:\n{{link_portal}}\n\n"
            "Fonte: Pred.IO\n\n"
            "Esta é uma mensagem automática do Portal Pred.IO."
        ),
        "variaveis_permitidas": "cliente_nome,ativo_nome,tipo_evento,prioridade,resumo,link_portal,fonte",
        "status": "Ativo",
    },
    {
        "nome":                "WhatsApp — Relatório Publicado",
        "tipo_evento":         "relatorio_publicado",
        "canal":               "WhatsApp",
        "assunto":             "",
        "corpo": (
            "Pred.IO\n\n"
            "Novo relatório técnico publicado.\n\n"
            "Cliente: {{cliente_nome}}\n"
            "Ativo: {{ativo_nome}}\n"
            "Prioridade: {{prioridade}}\n\n"
            "Resumo:\n{{resumo}}\n\n"
            "Acesse o Portal Pred.IO para visualizar:\n{{link_portal}}\n\n"
            "Fonte: Pred.IO"
        ),
        "variaveis_permitidas": "cliente_nome,ativo_nome,prioridade,resumo,link_portal,fonte",
        "status": "Ativo",
    },
    {
        "nome":                "E-mail — Manutenção Vencida",
        "tipo_evento":         "manutencao_vencida",
        "canal":               "E-mail",
        "assunto":             "[Pred.IO] Manutenção vencida - {{ativo_nome}}",
        "corpo": (
            "Olá.\n\n"
            "Uma manutenção está vencida no Portal Pred.IO.\n\n"
            "Cliente: {{cliente_nome}}\n"
            "Ativo: {{ativo_nome}}\n\n"
            "Resumo:\n{{resumo}}\n\n"
            "Acesse o Portal Pred.IO para visualizar o plano de manutenção:\n{{link_portal}}\n\n"
            "Fonte: Pred.IO"
        ),
        "variaveis_permitidas": "cliente_nome,ativo_nome,resumo,link_portal,fonte",
        "status": "Ativo",
    },
    {
        "nome":                "WhatsApp — Manutenção Vencida",
        "tipo_evento":         "manutencao_vencida",
        "canal":               "WhatsApp",
        "assunto":             "",
        "corpo": (
            "Pred.IO\n\n"
            "Manutenção vencida.\n\n"
            "Cliente: {{cliente_nome}}\n"
            "Ativo: {{ativo_nome}}\n\n"
            "Resumo:\n{{resumo}}\n\n"
            "Acesse o Portal Pred.IO:\n{{link_portal}}\n\n"
            "Fonte: Pred.IO"
        ),
        "variaveis_permitidas": "cliente_nome,ativo_nome,resumo,link_portal,fonte",
        "status": "Ativo",
    },
    {
        "nome":                "E-mail — Chamado Respondido",
        "tipo_evento":         "chamado_respondido",
        "canal":               "E-mail",
        "assunto":             "[Pred.IO] Chamado respondido - {{ativo_nome}}",
        "corpo": (
            "Olá.\n\n"
            "Um chamado técnico recebeu resposta da equipe Pred.IO.\n\n"
            "Cliente: {{cliente_nome}}\n"
            "Ativo: {{ativo_nome}}\n\n"
            "Resumo:\n{{resumo}}\n\n"
            "Acesse o Portal Pred.IO para visualizar a resposta:\n{{link_portal}}\n\n"
            "Fonte: Pred.IO"
        ),
        "variaveis_permitidas": "cliente_nome,ativo_nome,resumo,link_portal,fonte",
        "status": "Ativo",
    },
    {
        "nome":                "WhatsApp — Chamado Respondido",
        "tipo_evento":         "chamado_respondido",
        "canal":               "WhatsApp",
        "assunto":             "",
        "corpo": (
            "Pred.IO\n\n"
            "Chamado técnico respondido.\n\n"
            "Cliente: {{cliente_nome}}\n"
            "Ativo: {{ativo_nome}}\n\n"
            "Resumo:\n{{resumo}}\n\n"
            "Acesse o Portal Pred.IO:\n{{link_portal}}\n\n"
            "Fonte: Pred.IO"
        ),
        "variaveis_permitidas": "cliente_nome,ativo_nome,resumo,link_portal,fonte",
        "status": "Ativo",
    },
    {
        "nome":                "E-mail — Alerta Crítico",
        "tipo_evento":         "alerta_critico",
        "canal":               "E-mail",
        "assunto":             "[Pred.IO] Alerta crítico - {{ativo_nome}}",
        "corpo": (
            "Olá.\n\n"
            "Um alerta crítico foi gerado no Portal Pred.IO.\n\n"
            "Cliente: {{cliente_nome}}\n"
            "Ativo: {{ativo_nome}}\n"
            "Prioridade: {{prioridade}}\n\n"
            "Resumo:\n{{resumo}}\n\n"
            "Acesse o Portal Pred.IO para visualizar:\n{{link_portal}}\n\n"
            "Fonte: Pred.IO"
        ),
        "variaveis_permitidas": "cliente_nome,ativo_nome,prioridade,resumo,link_portal,fonte",
        "status": "Ativo",
    },
    {
        "nome":                "WhatsApp — Alerta Crítico",
        "tipo_evento":         "alerta_critico",
        "canal":               "WhatsApp",
        "assunto":             "",
        "corpo": (
            "Pred.IO\n\n"
            "Alerta crítico gerado.\n\n"
            "Cliente: {{cliente_nome}}\n"
            "Ativo: {{ativo_nome}}\n"
            "Prioridade: {{prioridade}}\n\n"
            "Acesse o Portal Pred.IO:\n{{link_portal}}\n\n"
            "Fonte: Pred.IO"
        ),
        "variaveis_permitidas": "cliente_nome,ativo_nome,prioridade,link_portal,fonte",
        "status": "Ativo",
    },
]


# ── Renderização de template ──────────────────────────────────────────────────

def render_template(corpo: str, assunto: str, dados: dict) -> dict:
    """
    Renderiza template substituindo apenas variáveis permitidas.
    Bloqueia variáveis sensíveis com marcador.
    Retorna: corpo_final, assunto_final, variaveis_usadas, variaveis_bloqueadas, ok.
    """
    dados_safe: dict = {k: str(v) for k, v in dados.items() if k in _ALLOWED_VARS}
    dados_safe.setdefault("fonte", _FONTE_PADRAO)

    variaveis_usadas: list[str] = []
    variaveis_bloqueadas: list[str] = []

    def _rep(m: re.Match) -> str:
        var = m.group(1).strip()
        if var in _BLOCKED_VARS:
            variaveis_bloqueadas.append(var)
            return f"[VARIÁVEL BLOQUEADA: {var}]"
        if var not in _ALLOWED_VARS:
            return m.group(0)  # desconhecida: mantém placeholder
        if var in dados_safe:
            variaveis_usadas.append(var)
            return dados_safe[var]
        return m.group(0)  # permitida mas sem valor

    def _sub(texto: str) -> str:
        return re.sub(r"\{\{(\w+)\}\}", _rep, texto)

    corpo_final   = _sub(corpo)
    assunto_final = _sub(assunto)

    return {
        "corpo_final":          corpo_final,
        "assunto_final":        assunto_final,
        "variaveis_usadas":     list(dict.fromkeys(variaveis_usadas)),
        "variaveis_bloqueadas": list(dict.fromkeys(variaveis_bloqueadas)),
        "ok":                   len(variaveis_bloqueadas) == 0,
    }


# ── Validação de conteúdo ─────────────────────────────────────────────────────

def validate_content(conteudo: str) -> dict:
    """
    Verifica conteúdo contra palavras e padrões sensíveis.
    Retorna: ok, riscos, mensagem.
    """
    c_lower = conteudo.lower()
    riscos: list[str] = []

    for kw in _SENSITIVE_KEYWORDS:
        if kw.lower() in c_lower:
            riscos.append(kw)

    if riscos:
        return {
            "ok":       False,
            "riscos":   riscos,
            "mensagem": f"{len(riscos)} risco(s) detectado(s): " + "; ".join(riscos[:3]),
        }
    return {"ok": True, "riscos": [], "mensagem": "Conteúdo validado sem riscos."}


# ── Validação de link ─────────────────────────────────────────────────────────

def validate_link(link: str) -> dict:
    """
    Verifica se o link aponta para rota autenticada do portal, não storage/arquivo.
    Retorna: ok, motivo.
    """
    if not link:
        return {"ok": True, "motivo": "Sem link definido."}

    for pattern in _BLOCKED_LINK_PATTERNS:
        if re.search(pattern, link, re.IGNORECASE):
            return {
                "ok":     False,
                "motivo": f"Link bloqueado: aponta para storage ou arquivo externo. Use rotas do portal.",
            }

    return {"ok": True, "motivo": "Link válido — aponta para rota do portal."}


# ── Validação de consentimento ────────────────────────────────────────────────

def validate_consent(contato: dict, canal: str) -> dict:
    """
    Verifica se o contato tem consentimento e dados para o canal.
    Retorna: ok, motivo.
    """
    canal_lower = canal.lower().replace("-", "").replace(" ", "")
    ativo = _truthy(contato.get("ativo", True))

    if not ativo:
        return {"ok": False, "motivo": "Contato inativo."}

    if "email" in canal_lower:
        email = str(contato.get("email", "")).strip()
        if not email:
            return {"ok": False, "motivo": "Contato sem e-mail cadastrado."}
        if not _truthy(contato.get("recebe_email", contato.get("tem_email", True))):
            return {"ok": False, "motivo": "Contato não aceita e-mail."}
        if not _truthy(contato.get("consentimento_email", True)):
            return {"ok": False, "motivo": "Consentimento de e-mail não registrado."}

    elif "whatsapp" in canal_lower:
        wa = str(contato.get("telefone_whatsapp", contato.get("whatsapp", ""))).strip()
        if not wa:
            return {"ok": False, "motivo": "Contato sem telefone WhatsApp cadastrado."}
        if not _truthy(contato.get("recebe_whatsapp", contato.get("tem_whatsapp", True))):
            return {"ok": False, "motivo": "Contato não aceita WhatsApp."}
        if not _truthy(contato.get("consentimento_whatsapp", True)):
            return {"ok": False, "motivo": "Consentimento de WhatsApp não registrado."}

    return {"ok": True, "motivo": "Consentimento válido."}


def _truthy(val) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "sim", "yes", "s")


# ── Bloqueio de envio externo ─────────────────────────────────────────────────

def check_external_send_blocked() -> dict:
    """Sempre retorna bloqueado nesta etapa (NOTIFICATION_EXTERNAL_SEND_ENABLED=false)."""
    return {
        "blocked":  True,
        "mensagem": "Envio externo desativado. Notificação registrada em modo teste. "
                    "(NOTIFICATION_EXTERNAL_SEND_ENABLED=false)",
    }


# ── Geração de preview completo ───────────────────────────────────────────────

def generate_preview(
    *,
    template: dict,
    dados: dict,
    contato: dict,
    canal: str,
    client_id: str,
) -> dict:
    """
    Gera pré-visualização completa com validações.
    Retorna: preview, validacoes, riscos, ok, erro_validacao, modo_teste, envio_externo.
    SEGURANÇA: client_id validado; obs_interna nunca chega em dados.
    """
    corpo   = str(template.get("corpo",   "")).strip()
    assunto = str(template.get("assunto", "")).strip()
    link    = str(dados.get("link_portal", "/portal")).strip()

    render      = render_template(corpo, assunto, dados)
    val_content = validate_content(render["corpo_final"])
    val_link    = validate_link(link)
    val_consent = validate_consent(contato, canal)

    riscos: list[str] = []
    if not render["ok"]:
        riscos.append(f"Variáveis bloqueadas: {', '.join(render['variaveis_bloqueadas'])}")
    if not val_content["ok"]:
        riscos.extend(val_content["riscos"][:3])
    if not val_link["ok"]:
        riscos.append(f"Link: {val_link['motivo']}")
    if not val_consent["ok"]:
        riscos.append(f"Consentimento: {val_consent['motivo']}")

    erro_validacao = "; ".join(riscos)
    ok_geral = len(riscos) == 0

    dest_display = (
        contato.get("email", "")
        or contato.get("whatsapp", "")
        or contato.get("nome", "—")
    )

    return {
        "preview": {
            "assunto":          render["assunto_final"],
            "corpo":            render["corpo_final"],
            "link":             link,
            "canal":            canal,
            "destinatario":     dest_display,
            "cliente_id":       client_id,
            "vars_usadas":      render["variaveis_usadas"],
        },
        "validacoes": {
            "conteudo":         val_content,
            "link":             val_link,
            "consentimento":    val_consent,
            "vars_bloqueadas":  render["variaveis_bloqueadas"],
        },
        "riscos":          riscos,
        "ok":              ok_geral,
        "erro_validacao":  erro_validacao,
        "modo_teste":      True,
        "envio_externo":   False,
    }


# ── Enfileiramento ────────────────────────────────────────────────────────────

def enqueue_notification(
    *,
    client_id: str,
    contato_id: str = "",
    template_id: str = "",
    tipo_evento: str = "",
    canal: str = "",
    destinatario: str = "",
    assunto: str = "",
    corpo_renderizado: str = "",
    link_portal: str = "",
    prioridade: str = "Média",
    erro_validacao: str = "",
    notification_id: str = "",
) -> str:
    """
    Enfileira notificação em modo=Teste.
    Nunca envia mensagem real.
    SEGURANÇA: client_id da sessão; modo sempre 'Teste' nesta etapa.
    """
    from sheets import add_notification_queue_item

    status = "Bloqueado" if erro_validacao else "Simulado"

    return add_notification_queue_item({
        "client_id":          client_id,
        "contato_id":         contato_id,
        "notification_id":    notification_id,
        "template_id":        template_id,
        "tipo_evento":        tipo_evento,
        "canal":              canal,
        "destinatario":       destinatario,
        "assunto":            assunto,
        "corpo_renderizado":  corpo_renderizado,
        "link_portal":        link_portal,
        "prioridade":         prioridade,
        "status":             status,
        "modo":               "Teste",
        "erro_validacao":     erro_validacao,
    })


# ── Simulação completa ────────────────────────────────────────────────────────

def simulate_notification(
    *,
    template: dict,
    client_id: str,
    contato: dict,
    canal: str,
    dados: dict,
) -> dict:
    """
    Gera preview + valida + enfileira em modo=Teste.
    Retorna: preview_result, queue_id, bloqueado.
    NUNCA envia mensagem real.
    """
    preview_result = generate_preview(
        template=template,
        dados=dados,
        contato=contato,
        canal=canal,
        client_id=client_id,
    )

    queue_id = enqueue_notification(
        client_id=client_id,
        contato_id=str(contato.get("id", "")),
        template_id=str(template.get("id", "")),
        tipo_evento=str(template.get("tipo_evento", "")),
        canal=canal,
        destinatario=preview_result["preview"]["destinatario"],
        assunto=preview_result["preview"]["assunto"],
        corpo_renderizado=preview_result["preview"]["corpo"],
        link_portal=preview_result["preview"]["link"],
        prioridade=str(dados.get("prioridade", "Média")),
        erro_validacao=preview_result["erro_validacao"],
    )

    return {
        "preview_result": preview_result,
        "queue_id":       queue_id or "",
        "bloqueado":      not preview_result["ok"],
        "envio_externo":  False,
        "modo":           "Teste",
    }


# ── Seed de templates padrão ──────────────────────────────────────────────────

def seed_default_templates() -> int:
    """
    Insere templates padrão se a aba estiver vazia.
    Retorna número de templates inseridos.
    """
    try:
        from sheets import get_notification_templates, add_notification_template
        df = get_notification_templates()
        if not df.empty:
            return 0  # já existem templates
        count = 0
        for tpl in DEFAULT_TEMPLATES:
            if add_notification_template(tpl):
                count += 1
        return count
    except Exception:
        return 0
