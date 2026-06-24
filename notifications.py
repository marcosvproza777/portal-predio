"""
Motor de Notificações — Portal Pred.IO.

Responsável por:
  - Catálogo de eventos notificáveis
  - Geração de notificações internas (Portal)
  - Preparação de notificações futuras (E-mail / WhatsApp — não enviadas nesta etapa)
  - Consulta de notificações por cliente
  - Marcação como lida
  - Inicialização de preferências padrão

REGRAS ABSOLUTAS:
  ✓ client_id SEMPRE da sessão — nunca do front-end
  ✓ Cliente só vê suas próprias notificações
  ✓ E-mail e WhatsApp NÃO são enviados nesta etapa
  ✓ Apenas canal Portal está ativo
  ✓ Fonte exibida ao cliente: Pred.IO
"""
from __future__ import annotations


# ── Catálogo de eventos ───────────────────────────────────────────────────────

EVENTOS: dict[str, dict] = {
    "relatorio_publicado": {
        "label":    "📄 Relatório publicado",
        "titulo":   "Novo relatório técnico publicado",
        "mensagem": "Um novo relatório técnico foi publicado para o ativo {ativo_nome}.",
        "link_page": "relatorios",
        "prioridade_default": "Média",
    },
    "relatorio_critico": {
        "label":    "🚨 Relatório crítico publicado",
        "titulo":   "Relatório crítico publicado",
        "mensagem": "Um relatório crítico foi publicado para o ativo {ativo_nome}. Recomenda-se avaliação técnica.",
        "link_page": "relatorios",
        "prioridade_default": "Alta",
    },
    "ativo_atencao": {
        "label":    "🟡 Ativo em atenção",
        "titulo":   "Ativo em condição de atenção",
        "mensagem": "O ativo {ativo_nome} está com status Atenção. Acompanhe recomendações técnicas.",
        "link_page": "ativos",
        "prioridade_default": "Média",
    },
    "ativo_critico": {
        "label":    "🔴 Ativo crítico",
        "titulo":   "Ativo em condição crítica",
        "mensagem": "O ativo {ativo_nome} está com status {status}. Verifique recomendações e chamados.",
        "link_page": "ativos",
        "prioridade_default": "Alta",
    },
    "manutencao_proxima": {
        "label":    "📅 Manutenção próxima do vencimento",
        "titulo":   "Manutenção próxima do vencimento",
        "mensagem": "A tarefa {tarefa_nome} está próxima do vencimento no ativo {ativo_nome}.",
        "link_page": "manutencao",
        "prioridade_default": "Média",
    },
    "manutencao_vencida": {
        "label":    "🔴 Manutenção vencida",
        "titulo":   "Manutenção vencida",
        "mensagem": "A tarefa {tarefa_nome} está vencida no ativo {ativo_nome}.",
        "link_page": "manutencao",
        "prioridade_default": "Alta",
    },
    "chamado_aberto": {
        "label":    "🔧 Chamado aberto",
        "titulo":   "Chamado técnico aberto",
        "mensagem": "O chamado \"{chamado_titulo}\" foi aberto com sucesso e está em análise.",
        "link_page": "chamados",
        "prioridade_default": "Baixa",
    },
    "chamado_respondido": {
        "label":    "💬 Chamado respondido",
        "titulo":   "Chamado respondido pela equipe Pred.IO",
        "mensagem": "O chamado \"{chamado_titulo}\" recebeu uma nova resposta da equipe Pred.IO.",
        "link_page": "chamados",
        "prioridade_default": "Média",
    },
    "chamado_aguardando_cliente": {
        "label":    "⏳ Chamado aguardando cliente",
        "titulo":   "Chamado aguardando sua resposta",
        "mensagem": "O chamado \"{chamado_titulo}\" está aguardando uma resposta do cliente.",
        "link_page": "chamados",
        "prioridade_default": "Alta",
    },
    "alerta_critico": {
        "label":    "🚨 Alerta crítico",
        "titulo":   "Alerta técnico crítico",
        "mensagem": "Um alerta crítico foi gerado para o ativo {ativo_nome}. Acesse o portal para detalhes.",
        "link_page": "alertas",
        "prioridade_default": "Alta",
    },
    "recomendacao_por_condicao": {
        "label":    "💡 Recomendação por condição",
        "titulo":   "Nova recomendação por condição",
        "mensagem": "Foi gerada uma recomendação por condição para o ativo {ativo_nome}. Fonte: Pred.IO",
        "link_page": "relatorios",
        "prioridade_default": "Média",
    },
    "documento_publicado": {
        "label":    "📚 Documento técnico publicado",
        "titulo":   "Novo documento técnico disponível",
        "mensagem": "Um novo documento técnico foi disponibilizado na Biblioteca Técnica Pred.IO.",
        "link_page": "biblioteca",
        "prioridade_default": "Baixa",
    },
}

# ── Preferências padrão por evento ────────────────────────────────────────────

_DEFAULT_EVENT_PREFS: dict[str, dict] = {
    "relatorio_publicado": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": True,
    },
    "relatorio_critico": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": True,
    },
    "ativo_atencao": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": False,
    },
    "ativo_critico": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": True,
    },
    "manutencao_proxima": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": True,
    },
    "manutencao_vencida": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": True,
    },
    "chamado_aberto": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": True,
    },
    "chamado_respondido": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": True,
    },
    "chamado_aguardando_cliente": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": True,
    },
    "alerta_critico": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": True,
    },
    "recomendacao_por_condicao": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": True,
    },
    "documento_publicado": {
        "canal_portal": True, "canal_email": False, "canal_whatsapp": False,
        "prioridade_minima": "Baixa", "frequencia": "Imediata", "ativo": False,
    },
}

# Prioridade numérica para filtro de prioridade_minima
_PRIO_NIVEL = {"Baixa": 0, "Média": 1, "Media": 1, "Alta": 2, "Crítica": 3, "Critica": 3}


# ── Função principal de criação ───────────────────────────────────────────────

def create_notification(
    evento: str,
    client_id: str,
    dados: dict,
) -> list[str]:
    """
    Gera notificação(ões) para o cliente conforme preferências de evento.

    SEGURANÇA:
    - client_id SEMPRE da sessão — nunca do front-end.
    - E-mail e WhatsApp NÃO são enviados nesta etapa.
    - Canal Portal é o único ativo.

    Parâmetros de `dados`:
      ativo_nome        — nome do ativo relacionado
      ativo_id          — ID do ativo
      tarefa_nome       — nome da tarefa (manutenção)
      chamado_titulo    — título do chamado
      status            — status do ativo/chamado
      report_id         — ID do relatório
      ticket_id         — ID do chamado
      maintenance_task_id — ID da tarefa
      alert_id          — ID do alerta
      document_id       — ID do documento
      prioridade        — prioridade da notificação (override)

    Retorna: lista de IDs de notificações criadas.
    """
    if not client_id or not evento:
        return []

    if evento not in EVENTOS:
        return []

    from sheets import (
        get_event_preferences, add_portal_notification, add_notificacao,
    )

    # Verifica preferências do cliente para este evento
    df_prefs = get_event_preferences(client_id)
    pref_evento = None

    if not df_prefs.empty:
        match = df_prefs[df_prefs["Evento"].str.strip() == evento]
        if not match.empty:
            pref_evento = match.iloc[0].to_dict()

    # Usa padrão se não encontrou preferência
    if pref_evento is None:
        pref_evento = _DEFAULT_EVENT_PREFS.get(evento, {})

    # Verifica se evento está ativo
    ativo = str(pref_evento.get("Ativo", pref_evento.get("ativo", "true"))).lower()
    if ativo not in ("true", "1", "sim", "yes"):
        return []

    # Verifica prioridade mínima
    evento_cfg    = EVENTOS[evento]
    prio_notif    = dados.get("prioridade", evento_cfg["prioridade_default"])
    prio_min      = str(pref_evento.get("Prioridade_Minima",
                         pref_evento.get("prioridade_minima", "Baixa"))).strip()
    nivel_notif   = _PRIO_NIVEL.get(prio_notif, 0)
    nivel_minimo  = _PRIO_NIVEL.get(prio_min, 0)

    if nivel_notif < nivel_minimo:
        return []

    # Monta título e mensagem
    titulo   = evento_cfg["titulo"]
    template = evento_cfg["mensagem"]
    mensagem = template.format(
        ativo_nome     = dados.get("ativo_nome", "—"),
        tarefa_nome    = dados.get("tarefa_nome", "—"),
        chamado_titulo = dados.get("chamado_titulo", "—"),
        status         = dados.get("status", "—"),
    )
    link_page = evento_cfg["link_page"]
    created_ids: list[str] = []

    # ── Canal Portal (ÚNICO ATIVO NESTA ETAPA) ───────────────────────────────
    canal_portal = str(pref_evento.get("Canal_Portal",
                        pref_evento.get("canal_portal", "true"))).lower()
    if canal_portal in ("true", "1", "sim", "yes"):
        nid = add_portal_notification({
            "cliente_id":          client_id,
            "usuario_id":          dados.get("usuario_id", ""),
            "ativo_id":            dados.get("ativo_id", ""),
            "report_id":           dados.get("report_id", ""),
            "ticket_id":           dados.get("ticket_id", ""),
            "maintenance_task_id": dados.get("maintenance_task_id", ""),
            "alert_id":            dados.get("alert_id", ""),
            "document_id":         dados.get("document_id", ""),
            "tipo_evento":         evento,
            "titulo":              titulo,
            "mensagem":            mensagem,
            "prioridade":          prio_notif,
            "canal":               "Portal",
            "link_page":           link_page,
            "link_id":             dados.get("link_id", ""),
        })
        if nid:
            created_ids.append(nid)

    # ── Canal E-mail (preparado, sem envio real) ──────────────────────────────
    canal_email = str(pref_evento.get("Canal_Email",
                       pref_evento.get("canal_email", "false"))).lower()
    if canal_email in ("true", "1", "sim", "yes"):
        nid = add_notificacao({
            "cliente_id":  client_id,
            "usuario_id":  dados.get("usuario_id", ""),
            "evento_tipo": evento,
            "canal":       "E-mail",
            "titulo":      titulo,
            "mensagem":    mensagem,
            "link_portal": link_page,
            "status":      "Preparado para etapa futura",
            "enviado_por": "sistema_predio",
        })
        if nid:
            created_ids.append(nid)

    # ── Canal WhatsApp (preparado, sem envio real) ────────────────────────────
    canal_wa = str(pref_evento.get("Canal_Whatsapp",
                    pref_evento.get("canal_whatsapp", "false"))).lower()
    if canal_wa in ("true", "1", "sim", "yes"):
        resumo = f"{titulo}. Acesse o portal para detalhes. Fonte: Pred.IO"
        nid = add_notificacao({
            "cliente_id":  client_id,
            "usuario_id":  dados.get("usuario_id", ""),
            "evento_tipo": evento,
            "canal":       "WhatsApp",
            "titulo":      titulo,
            "mensagem":    resumo,
            "link_portal": link_page,
            "status":      "Preparado para etapa futura",
            "enviado_por": "sistema_predio",
        })
        if nid:
            created_ids.append(nid)

    return created_ids


# ── Consultas ─────────────────────────────────────────────────────────────────

def get_portal_notifications(client_id: str, apenas_nao_lidas: bool = False,
                              limit: int = 30) -> list[dict]:
    """
    Retorna notificações do portal para o cliente.
    SEGURANÇA: client_id sempre da sessão.
    """
    from sheets import get_portal_notifications as _get
    df = _get(client_id, apenas_nao_lidas=apenas_nao_lidas, limit=limit)
    if df.empty:
        return []
    result = []
    for _, row in df.iterrows():
        result.append({
            "id":            str(row.get("Id",          "")).strip(),
            "tipo_evento":   str(row.get("Tipo_Evento", "")).strip(),
            "titulo":        str(row.get("Titulo",      "")).strip(),
            "mensagem":      str(row.get("Mensagem",    "")).strip(),
            "prioridade":    str(row.get("Prioridade",  "Média")).strip(),
            "status":        str(row.get("Status",      "Não lida")).strip(),
            "link_page":     str(row.get("Link_Page",   "")).strip(),
            "link_id":       str(row.get("Link_Id",     "")).strip(),
            "ativo_id":      str(row.get("Ativo_Id",    "")).strip(),
            "report_id":     str(row.get("Report_Id",   "")).strip(),
            "ticket_id":     str(row.get("Ticket_Id",   "")).strip(),
            "created_at":    str(row.get("Created_At",  "")).strip(),
            "lida_em":       str(row.get("Lida_Em",     "")).strip(),
        })
    return result


def get_unread_count(client_id: str) -> int:
    """Conta notificações não lidas do portal para o cliente."""
    from sheets import count_portal_notifications_unread
    return count_portal_notifications_unread(client_id)


def mark_as_read(notif_id: str, client_id: str) -> bool:
    """Marca notificação como lida — valida ownership."""
    from sheets import mark_portal_notification_read
    return mark_portal_notification_read(notif_id, client_id)


def mark_all_read(client_id: str) -> int:
    """Marca todas as notificações como lidas."""
    from sheets import mark_all_portal_notifications_read
    return mark_all_portal_notifications_read(client_id)


def ensure_default_preferences(client_id: str) -> bool:
    """Garante que preferências padrão existem para o cliente."""
    from sheets import init_default_event_preferences
    return init_default_event_preferences(client_id)


# ── Gatilhos de eventos ───────────────────────────────────────────────────────

def on_relatorio_publicado(client_id: str, report_id: str,
                            ativo_nome: str = "", ativo_id: str = "",
                            severidade: str = "Normal") -> list[str]:
    """Chamado quando relatório é publicado. Gera notificação interna."""
    is_critico = severidade.lower() in ("crítico", "critico", "urgente")
    evento = "relatorio_critico" if is_critico else "relatorio_publicado"
    prio   = "Alta" if is_critico else "Média"
    return create_notification(evento, client_id, {
        "ativo_nome": ativo_nome,
        "ativo_id":   ativo_id,
        "report_id":  report_id,
        "link_id":    report_id,
        "prioridade": prio,
    })


def on_chamado_respondido(client_id: str, ticket_id: str,
                           chamado_titulo: str = "") -> list[str]:
    """Chamado quando equipe Pred.IO responde chamado."""
    return create_notification("chamado_respondido", client_id, {
        "chamado_titulo": chamado_titulo,
        "ticket_id":      ticket_id,
        "link_id":        ticket_id,
        "prioridade":     "Média",
    })


def on_chamado_aguardando_cliente(client_id: str, ticket_id: str,
                                   chamado_titulo: str = "") -> list[str]:
    """Chamado quando chamado muda para 'Aguardando cliente'."""
    return create_notification("chamado_aguardando_cliente", client_id, {
        "chamado_titulo": chamado_titulo,
        "ticket_id":      ticket_id,
        "link_id":        ticket_id,
        "prioridade":     "Alta",
    })


def on_chamado_aberto(client_id: str, ticket_id: str,
                       chamado_titulo: str = "") -> list[str]:
    """Chamado quando cliente abre chamado."""
    return create_notification("chamado_aberto", client_id, {
        "chamado_titulo": chamado_titulo,
        "ticket_id":      ticket_id,
        "link_id":        ticket_id,
        "prioridade":     "Baixa",
    })


def on_manutencao_status(client_id: str, task_id: str,
                          tarefa_nome: str = "", ativo_nome: str = "",
                          ativo_id: str = "", vencida: bool = False) -> list[str]:
    """Chamado quando tarefa muda para Próxima ou Vencida."""
    evento = "manutencao_vencida" if vencida else "manutencao_proxima"
    prio   = "Alta" if vencida else "Média"
    return create_notification(evento, client_id, {
        "tarefa_nome":    tarefa_nome,
        "ativo_nome":     ativo_nome,
        "ativo_id":       ativo_id,
        "maintenance_task_id": task_id,
        "link_id":        task_id,
        "prioridade":     prio,
    })


def on_ativo_status(client_id: str, ativo_id: str,
                     ativo_nome: str = "", status: str = "") -> list[str]:
    """Chamado quando status do ativo muda para Crítico ou Urgente."""
    s_low = status.lower()
    if s_low in ("crítico", "critico"):
        evento, prio = "ativo_critico", "Alta"
    elif s_low == "urgente":
        evento, prio = "ativo_critico", "Crítica"
    elif s_low in ("atenção", "atencao"):
        evento, prio = "ativo_atencao", "Média"
    else:
        return []
    return create_notification(evento, client_id, {
        "ativo_nome": ativo_nome,
        "ativo_id":   ativo_id,
        "status":     status,
        "link_id":    ativo_id,
        "prioridade": prio,
    })


def on_alerta_critico(client_id: str, alert_id: str,
                       ativo_nome: str = "", ativo_id: str = "") -> list[str]:
    """Chamado quando alerta crítico é criado."""
    return create_notification("alerta_critico", client_id, {
        "ativo_nome": ativo_nome,
        "ativo_id":   ativo_id,
        "alert_id":   alert_id,
        "link_id":    alert_id,
        "prioridade": "Alta",
    })


def on_documento_publicado(client_id: str, doc_id: str) -> list[str]:
    """Chamado quando documento técnico é publicado."""
    return create_notification("documento_publicado", client_id, {
        "document_id": doc_id,
        "link_id":     doc_id,
        "prioridade":  "Baixa",
    })


def on_recomendacao_por_condicao(client_id: str, ativo_id: str = "",
                                  ativo_nome: str = "",
                                  report_id: str = "") -> list[str]:
    """Chamado quando recomendação por condição é gerada. Nunca automática por horímetro."""
    return create_notification("recomendacao_por_condicao", client_id, {
        "ativo_nome": ativo_nome,
        "ativo_id":   ativo_id,
        "report_id":  report_id,
        "link_id":    report_id or ativo_id,
        "prioridade": "Média",
    })
