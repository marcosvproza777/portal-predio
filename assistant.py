"""Integração com n8n — Assistente Técnico Pred.IO."""
import os
from datetime import datetime

import requests


def call_assistant(client_id: str, email: str, empresa: str, pergunta: str) -> tuple[str, str]:
    """
    Chama o webhook n8n com client_id da SESSÃO (nunca do front-end).
    Retorna (resposta, fontes).
    """
    webhook_url = os.environ.get("N8N_ASSISTANT_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return (
            "O Assistente Técnico ainda não está configurado. "
            "Entre em contato com a equipe Pred.IO.",
            "",
        )

    payload = {
        "client_id":    client_id,   # sempre da sessão do servidor
        "usuario_email": email,
        "nome_cliente": empresa,
        "pergunta":     pergunta,
        "timestamp":    datetime.now().isoformat(),
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        resposta = data.get("resposta") or data.get("response") or data.get("output", "")
        fontes   = data.get("fontes")  or data.get("sources",  "")
        if not resposta:
            resposta = "O assistente não retornou uma resposta. Tente novamente."
        return str(resposta), str(fontes)
    except requests.exceptions.Timeout:
        return "O assistente demorou para responder. Tente novamente.", ""
    except requests.exceptions.ConnectionError:
        return "Não foi possível conectar ao assistente. Verifique a configuração.", ""
    except Exception as e:
        return f"Erro inesperado ao contatar o assistente: {e}", ""


def send_whatsapp(numero: str, mensagem: str, contexto: dict | None = None) -> bool:
    """Envia mensagem WhatsApp via webhook configurado em N8N_WHATSAPP_WEBHOOK_URL.

    Payload enviado ao webhook:
      { "numero": "5511999999999", "mensagem": "...", "contexto": {...} }

    O webhook n8n (ou qualquer outra API) recebe e despacha pelo WhatsApp.
    Retorna True se o webhook respondeu 2xx, False caso contrário.
    """
    webhook_url = os.environ.get("N8N_WHATSAPP_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return False  # não configurado — falha silenciosa, aviso tratado pelo chamador

    payload = {
        "numero":   numero.strip(),
        "mensagem": mensagem.strip(),
        "contexto": contexto or {},
        "timestamp": datetime.now().isoformat(),
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        return resp.status_code < 300
    except Exception:
        return False


CRITICAL_KEYWORDS = [
    "parada", "parou", "travou", "quebrou", "explosão", "vazamento",
    "incêndio", "risco", "urgente", "emergência", "crítico", "falha grave",
    "acidente", "perigo", "segurança",
]


def is_critical(pergunta: str) -> bool:
    """Detecta se a pergunta indica situação crítica/emergencial."""
    p = pergunta.lower()
    return any(kw in p for kw in CRITICAL_KEYWORDS)
