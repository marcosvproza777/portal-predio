"""
Busca na internet controlada para o Assistente Técnico Pred.IO.

SEGURANÇA OBRIGATÓRIA:
  - Chave de API nunca vai ao front-end (lida apenas em os.environ).
  - Query sanitizada antes de qualquer chamada externa.
  - Dados sensíveis de clientes nunca saem do servidor.
  - Ativada apenas quando WEB_SEARCH_ENABLED=true.
  - Internet nunca autoriza decisão crítica sozinha.

ORDEM DE BUSCA DO ASSISTENTE:
  1. Biblioteca Técnica Pred.IO (chunks indexados)
  2. Relatórios técnicos publicados
  3. Plano de manutenção / histórico do ativo
  4. Chamados / alertas
  5. Base FAQ Pred.IO
  10. Internet (apenas se tudo acima for insuficiente)
"""
from __future__ import annotations

import os
import re
import hashlib
import time

# ── Configuração via variáveis de ambiente ────────────────────────────────────
WEB_SEARCH_ENABLED     = os.environ.get("WEB_SEARCH_ENABLED",     "false").lower() == "true"
WEB_SEARCH_PROVIDER    = os.environ.get("WEB_SEARCH_PROVIDER",    "tavily").lower()
WEB_SEARCH_API_KEY     = os.environ.get("WEB_SEARCH_API_KEY",     "")
WEB_SEARCH_MAX_RESULTS = int(os.environ.get("WEB_SEARCH_MAX_RESULTS", "5"))

# ── Cache em memória (reinicia com o servidor — adequado para Render.com) ─────
_CACHE: dict[str, tuple[list, float]] = {}
_CACHE_TTL_SECONDS = 7 * 24 * 3600   # 7 dias

# ── Allowlist de domínios confiáveis ─────────────────────────────────────────
ALLOWED_DOMAINS: dict[str, str] = {
    # Compressores / Refrigeração
    "mayekawa.com":           "Fabricante",
    "mycom.co.jp":            "Fabricante",
    "danfoss.com":            "Fabricante",
    "copeland.com":           "Fabricante",
    "bitzer.de":              "Fabricante",
    "carlylecs.com":          "Fabricante",
    "grasso.com":             "Fabricante",
    # Rolamentos
    "skf.com":                "Rolamentos",
    "skfbrasil.com.br":       "Rolamentos",
    "schaeffler.com":         "Rolamentos",
    "timken.com":             "Rolamentos",
    "nsk.com":                "Rolamentos",
    "ntn.com.br":             "Rolamentos",
    # Motores elétricos
    "weg.net":                "Motores elétricos",
    "siemens.com":            "Motores elétricos",
    "abb.com":                "Motores elétricos",
    "easa.com":               "Motores elétricos",
    "nidec.com":              "Motores elétricos",
    # Lubrificação / Óleo
    "mobil.com":              "Óleo e lubrificação",
    "shell.com":              "Óleo e lubrificação",
    "totalbrasil.com.br":     "Óleo e lubrificação",
    "castrol.com":            "Óleo e lubrificação",
    # Normas técnicas
    "abnt.org.br":            "Norma técnica",
    "iso.org":                "Norma técnica",
    "ansi.org":               "Norma técnica",
    "nfpa.org":               "Norma técnica",
    # Manutenção preditiva / Vibração / Termografia
    "reliabilityweb.com":     "Manutenção preditiva",
    "maintenanceworld.com":   "Manutenção preditiva",
    "vibration-institute.org":"Vibração",
    "bindt.org":              "Termografia / END",
    "ndt.net":                "Termografia / END",
    # Documentação técnica geral confiável
    "engineers.org":          "Engenharia",
    "asme.org":               "Norma técnica",
}

# ── Padrões de dados sensíveis — removidos antes da query ────────────────────
_SENSITIVE_PATTERNS: list[tuple[str, str]] = [
    (r"\b[A-Z]{2,5}-\d{3,}\b",                      "[ID]"),      # CLI-001, ATI-002
    (r"\b\d{6,}\b",                                  "[NUM]"),     # série, matrícula
    (r"\b(senha|password|token|chave|key|secret)\b", "[CRED]"),    # credenciais
    (r"cliente\s*[:\-]?\s*[\w\s]+",                  "[CLIENTE]"), # "cliente: XYZ"
    (r"\b(cpf|cnpj)\s*[\d.\-/]+",                   "[DOC]"),     # CPF/CNPJ
    (r"\b(relatório|relatorio)\s+interno\b",         "[REL]"),     # relatório interno
    (r"obs(ervação|ervacao)?\s+interna",             "[OBS]"),     # obs interna
]

# ── Palavras-chave de decisão crítica — internet não autoriza ─────────────────
_CRITICAL_KEYWORDS: list[str] = [
    "parar a máquina", "parar maquina", "desligar o compressor",
    "ligar o compressor", "partir o compressor",
    "reset", "resetar alarme", "limpar alarme",
    "trocar rolamento", "fazer overhaul", "fazer revisão",
    "kit revisão", "desmontagem", "desmontar",
    "substituir componente", "trocar óleo agora",
    "alterar set point", "alterar setpoint",
    "mudar capacidade", "alterar capacidade",
    "autorizar parada", "autorizar partida",
]


# ── Funções públicas ──────────────────────────────────────────────────────────

def is_enabled() -> bool:
    """True se busca web está ativa e configurada."""
    if not WEB_SEARCH_ENABLED:
        return False
    if WEB_SEARCH_PROVIDER == "duckduckgo":
        return True   # não precisa de API key
    return bool(WEB_SEARCH_API_KEY)


def sanitize_query(pergunta: str, client_id: str = "") -> str:
    """
    Remove dados sensíveis da pergunta antes de enviar para a internet.
    Nunca inclui client_id, IDs internos ou informações de cliente.
    """
    q = pergunta.strip()

    # Remove client_id se aparecer literalmente
    if client_id:
        q = q.replace(client_id, "[ID]")

    # Aplica padrões de remoção
    for pattern, replacement in _SENSITIVE_PATTERNS:
        q = re.sub(pattern, replacement, q, flags=re.IGNORECASE)

    # Limita tamanho
    if len(q) > 200:
        q = q[:197] + "..."

    return q.strip()


def is_critical_decision(pergunta: str) -> bool:
    """
    True se a pergunta envolve decisão operacional crítica.
    Nesses casos, a internet NÃO pode autorizar a ação.
    """
    q = pergunta.lower()
    return any(kw in q for kw in _CRITICAL_KEYWORDS)


def extract_domain(url: str) -> str:
    """Extrai o domínio limpo de uma URL."""
    m = re.search(r"https?://(?:www\.)?([^/?\s]+)", url)
    return m.group(1).lower() if m else url.lower()[:50]


def search(
    pergunta: str,
    client_id: str = "",
    force: bool = False,
) -> dict:
    """
    Executa busca web controlada.

    Retorna:
    {
        "ok":              bool,
        "usou_internet":   bool,
        "query_limpa":     str,
        "resultados":      [{"titulo", "resumo", "url", "dominio", "categoria", "confianca"}],
        "motivo_skip":     str,   # motivo se não buscou
        "provider":        str,
    }

    SEGURANÇA: client_id nunca vai para a query; dados sensíveis removidos.
    """
    base = {
        "ok": False, "usou_internet": False,
        "query_limpa": "", "resultados": [],
        "motivo_skip": "", "provider": WEB_SEARCH_PROVIDER,
    }

    if not is_enabled() and not force:
        base["motivo_skip"] = (
            "A busca na internet não está ativada no Portal Pred.IO. "
            "Configure WEB_SEARCH_ENABLED=true e WEB_SEARCH_API_KEY no servidor."
        )
        return base

    query_limpa = sanitize_query(pergunta, client_id)
    base["query_limpa"] = query_limpa

    if len(query_limpa.strip()) < 5:
        base["motivo_skip"] = "Pergunta muito curta após sanitização."
        return base

    # Cache
    cached = _get_cache(query_limpa)
    if cached:
        _log(pergunta, query_limpa, cached, client_id, cache_hit=True)
        base.update({"ok": True, "usou_internet": True, "resultados": cached})
        return base

    # Executa busca
    try:
        if WEB_SEARCH_PROVIDER == "tavily":
            resultados = _search_tavily(query_limpa, WEB_SEARCH_MAX_RESULTS)
        elif WEB_SEARCH_PROVIDER == "brave":
            resultados = _search_brave(query_limpa, WEB_SEARCH_MAX_RESULTS)
        else:
            resultados = _search_duckduckgo(query_limpa, WEB_SEARCH_MAX_RESULTS)
    except Exception as exc:
        _log(pergunta, query_limpa, [], client_id, erro=str(exc))
        base["motivo_skip"] = f"Erro ao consultar provedor ({type(exc).__name__})."
        return base

    # Filtra por allowlist
    resultados = _filter_by_allowlist(resultados)
    if not resultados:
        base["motivo_skip"] = "Nenhum resultado de domínio confiável encontrado."
        _log(pergunta, query_limpa, [], client_id)
        return base

    _save_cache(query_limpa, resultados)
    _log(pergunta, query_limpa, resultados, client_id)
    base.update({"ok": True, "usou_internet": True, "resultados": resultados})
    return base


# ── Providers ─────────────────────────────────────────────────────────────────

def _search_tavily(query: str, max_n: int) -> list[dict]:
    try:
        from tavily import TavilyClient
    except ImportError as exc:
        raise RuntimeError(
            "tavily-python não instalado. Adicione 'tavily-python>=0.3.0' ao requirements.txt."
        ) from exc
    client = TavilyClient(api_key=WEB_SEARCH_API_KEY)
    resp = client.search(
        query=query,
        search_depth="basic",
        max_results=max_n,
        include_domains=list(ALLOWED_DOMAINS.keys()),
    )
    return [
        {"titulo": r.get("title", ""), "resumo": r.get("content", "")[:500], "url": r.get("url", "")}
        for r in resp.get("results", [])
    ]


def _search_brave(query: str, max_n: int) -> list[dict]:
    import requests
    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": max_n},
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": WEB_SEARCH_API_KEY,
        },
        timeout=8,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"titulo": r.get("title", ""), "resumo": r.get("description", "")[:500], "url": r.get("url", "")}
        for r in data.get("web", {}).get("results", [])
    ]


def _search_duckduckgo(query: str, max_n: int) -> list[dict]:
    """DuckDuckGo Instant Answers — gratuito, sem API key, resultado limitado."""
    import requests
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=6,
        )
        data = resp.json()
    except Exception:
        return []

    results: list[dict] = []
    if data.get("Abstract"):
        results.append({
            "titulo": data.get("Heading", query[:60]),
            "resumo": data["Abstract"][:500],
            "url":    data.get("AbstractURL", ""),
        })
    for topic in data.get("RelatedTopics", [])[:max_n]:
        if isinstance(topic, dict) and topic.get("Text"):
            results.append({
                "titulo": topic["Text"][:60],
                "resumo": topic["Text"][:400],
                "url":    topic.get("FirstURL", ""),
            })
        if len(results) >= max_n:
            break
    return results


# ── Allowlist ──────────────────────────────────────────────────────────────────

def _filter_by_allowlist(results: list[dict]) -> list[dict]:
    """Mantém resultados de domínios confiáveis; marca confiança baixa nos demais."""
    alta: list[dict] = []
    baixa: list[dict] = []
    for r in results:
        dom = extract_domain(r.get("url", ""))
        cat = next((v for k, v in ALLOWED_DOMAINS.items() if k in dom), None)
        r["dominio"] = dom
        if cat:
            r["categoria"] = cat
            r["confianca"] = "alta"
            alta.append(r)
        else:
            r["categoria"] = "Fonte externa"
            r["confianca"] = "baixa"
            baixa.append(r)
    return alta if alta else baixa


# ── Cache em memória ──────────────────────────────────────────────────────────

def _cache_key(query: str) -> str:
    return hashlib.md5(query.lower().strip().encode()).hexdigest()


def _get_cache(query: str) -> list[dict] | None:
    key = _cache_key(query)
    entry = _CACHE.get(key)
    if entry is None:
        return None
    results, ts = entry
    if time.time() - ts > _CACHE_TTL_SECONDS:
        del _CACHE[key]
        return None
    return results


def _save_cache(query: str, results: list[dict]) -> None:
    _CACHE[_cache_key(query)] = (results, time.time())


# ── Log de auditoria ──────────────────────────────────────────────────────────

def _log(
    pergunta_original: str,
    query_limpa: str,
    resultados: list[dict],
    cliente_id: str = "",
    cache_hit: bool = False,
    erro: str = "",
) -> None:
    try:
        from sheets import add_web_search_log
        dominios = "; ".join({r.get("dominio", "") for r in resultados if r.get("dominio")})
        add_web_search_log({
            "cliente_id":         (cliente_id or "")[:50],
            "pergunta_original":  pergunta_original[:200],
            "query_limpa":        query_limpa[:200],
            "provider":           WEB_SEARCH_PROVIDER,
            "dominios":           dominios[:300],
            "n_resultados":       str(len(resultados)),
            "cache_hit":          "Sim" if cache_hit else "Não",
            "erro":               erro[:200] if erro else "",
        })
    except Exception:
        pass
