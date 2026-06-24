"""
Módulo central de segurança — Portal Pred.IO.

Centraliza:
  - Validação de client_id (sempre da sessão)
  - Guard de ownership para chamados, relatórios e documentos
  - Bloqueio de acesso de cliente a rotas de supervisão
  - Registro de auditoria de acesso (AcessoAuditoria no Sheets)
  - Sanitização de parâmetros de navegação

REGRAS ABSOLUTAS:
  ✓ client_id SEMPRE da sessão — nunca do front-end
  ✓ Cliente nunca vê dados de outro cliente
  ✓ Cliente nunca acessa /supervisao/*
  ✓ Rascunhos nunca aparecem para cliente
  ✓ Observações internas nunca aparecem para cliente
  ✓ Mensagens com Visivel_Cliente=0 nunca aparecem para cliente
"""
from __future__ import annotations

import streamlit as st

# ── Páginas válidas do Portal do Cliente ─────────────────────────────────────
# Qualquer valor fora deste conjunto é rejeitado quando vindo da URL
VALID_CLIENT_PAGES: frozenset = frozenset({
    "dashboard", "farois", "ativos", "manutencao", "relatorios",
    "chamados", "alertas", "biblioteca", "assistente", "preferencias",
    "notificacoes",
})


# ── Guard: client_id da sessão ────────────────────────────────────────────────

def guard_client_id(client_id: str, acao: str = "acesso") -> str:
    """
    Valida que client_id é não-vazio e vem da sessão.
    Para a execução se inválido — cliente autenticado sempre tem client_id.

    Uso: client_id = guard_client_id(current_client_id())
    """
    cid = (client_id or "").strip()
    if not cid:
        log_acesso(
            acao=acao,
            recurso_tipo="sessao",
            recurso_id="",
            resultado="negado",
            client_id="",
            detalhe="client_id vazio — sessão inválida",
        )
        st.error("🔒 Sessão inválida. Faça login novamente.")
        st.stop()
    return cid


# ── Guard: ownership de chamado ───────────────────────────────────────────────

def require_client_owns_chamado(chamado_id: str, client_id: str) -> bool:
    """
    Valida que o chamado pertence ao client_id da sessão.
    Retorna True se autorizado; para a execução se negado.
    """
    from sheets import get_chamado_v2_by_id
    row = get_chamado_v2_by_id(chamado_id, client_id=client_id)
    if row is None:
        log_acesso(
            acao="visualizar_chamado",
            recurso_tipo="chamado",
            recurso_id=chamado_id,
            resultado="negado",
            client_id=client_id,
            detalhe="chamado não encontrado ou de outro cliente",
        )
        st.error("🔒 Chamado não encontrado ou acesso não autorizado.")
        st.stop()
    return True


# ── Guard: ownership de relatório ─────────────────────────────────────────────

def require_client_owns_relatorio(report_id: str, client_id: str) -> bool:
    """
    Valida que o relatório pertence ao client_id e está publicado.
    Retorna True se autorizado; para a execução se negado.
    """
    from sheets import get_technical_report_by_id
    row = get_technical_report_by_id(report_id)
    if row is None:
        log_acesso(
            acao="visualizar_relatorio",
            recurso_tipo="relatorio",
            recurso_id=report_id,
            resultado="negado",
            client_id=client_id,
            detalhe="relatório não encontrado",
        )
        st.error("🔒 Relatório não encontrado.")
        st.stop()

    # Valida ownership
    row_client = str(row.get("Cliente_Id", "")).strip().lower()
    if row_client != client_id.strip().lower():
        log_acesso(
            acao="visualizar_relatorio",
            recurso_tipo="relatorio",
            recurso_id=report_id,
            resultado="negado",
            client_id=client_id,
            detalhe=f"relatório pertence a cliente diferente: {row_client}",
        )
        st.error("🔒 Acesso não autorizado.")
        st.stop()

    # Valida status — somente publicado
    status = str(row.get("Status", "")).strip().lower()
    if status != "publicado":
        log_acesso(
            acao="visualizar_relatorio",
            recurso_tipo="relatorio",
            recurso_id=report_id,
            resultado="negado",
            client_id=client_id,
            detalhe=f"status não publicado: {status}",
        )
        st.error("🔒 Relatório não disponível.")
        st.stop()

    return True


# ── Guard: ownership de documento ─────────────────────────────────────────────

def require_client_owns_documento(doc_id: str, client_id: str) -> bool:
    """
    Valida que o documento está autorizado para o client_id.
    Retorna True se autorizado; para a execução se negado.
    """
    from sheets import get_documentos_tecnicos
    df = get_documentos_tecnicos(client_id=client_id, staff=False)
    if df.empty or "Id" not in df.columns:
        log_acesso(
            acao="baixar_documento",
            recurso_tipo="documento",
            recurso_id=doc_id,
            resultado="negado",
            client_id=client_id,
            detalhe="nenhum documento autorizado",
        )
        st.error("🔒 Documento não autorizado.")
        st.stop()

    encontrado = (df["Id"].astype(str).str.strip() == doc_id.strip()).any()
    if not encontrado:
        log_acesso(
            acao="baixar_documento",
            recurso_tipo="documento",
            recurso_id=doc_id,
            resultado="negado",
            client_id=client_id,
            detalhe="documento não pertence ao cliente",
        )
        st.error("🔒 Documento não autorizado ou não encontrado.")
        st.stop()

    return True


# ── Guard: cliente não pode acessar supervisão ────────────────────────────────

def block_client_supervisao() -> None:
    """
    Impede que cliente acesse qualquer rota de supervisão.
    Deve ser chamado no início de qualquer função de supervisão.
    (Redundante com require_staff() — mas como defesa em profundidade.)
    """
    from auth import is_staff
    if not is_staff():
        client_id = st.session_state.get("client_id", "")
        log_acesso(
            acao="acessar_rota_supervisao",
            recurso_tipo="rota",
            recurso_id="supervisao",
            resultado="negado",
            client_id=client_id,
            detalhe="tentativa de acesso não autorizado à Supervisão Pred.IO",
        )
        st.error("🔒 Acesso restrito à equipe Pred.IO.")
        st.stop()


# ── Sanitização de navegação da URL ──────────────────────────────────────────

def sanitize_portal_page(nav_param: str) -> str | None:
    """
    Aceita navegação via URL apenas para páginas do cliente autorizadas.
    Retorna a página sanitizada ou None se inválida.
    Impede que cliente injete rotas de supervisão ou páginas inexistentes.
    """
    if not nav_param:
        return None
    page = nav_param.strip().lower()
    if page in VALID_CLIENT_PAGES:
        return page
    # Registra tentativa suspeita mas não bloqueia — apenas ignora
    client_id = st.session_state.get("client_id", "")
    if page.startswith(("supervisao", "sv_", "admin", "staff")):
        log_acesso(
            acao="acessar_rota_supervisao",
            recurso_tipo="url_param",
            recurso_id=page,
            resultado="negado",
            client_id=client_id,
            detalhe=f"tentativa de injeção via portal_page URL: {page}",
        )
    return None  # ignora pages inválidas


# ── Log de auditoria de acesso ────────────────────────────────────────────────

_AUDIT_TAB = "AcessoAuditoria"

_AUDIT_HEADERS = [
    "Id", "Usuario_Id", "Cliente_Id", "Acao", "Recurso_Tipo",
    "Recurso_Id", "Rota", "Resultado", "Detalhe", "Created_At",
]


def log_acesso(
    acao: str,
    recurso_tipo: str,
    recurso_id: str,
    resultado: str,
    client_id: str = "",
    rota: str = "",
    detalhe: str = "",
) -> None:
    """
    Registra evento de acesso no Google Sheets (aba AcessoAuditoria).

    Parâmetros:
        acao          — ex: "visualizar_relatorio", "tentativa_acesso_negado"
        recurso_tipo  — ex: "chamado", "relatorio", "documento", "rota"
        recurso_id    — ID do recurso (string)
        resultado     — "permitido" | "negado" | "erro"
        client_id     — da sessão (nunca do front-end)
        rota          — ex: "portal/relatorios"
        detalhe       — informação adicional (opcional)
    """
    try:
        from datetime import datetime
        import uuid
        from sheets import append_row, _ensure_tab_headers

        usuario_id = st.session_state.get("email_logado", "")
        if not client_id:
            client_id = st.session_state.get("client_id", "")
        if not rota:
            rota = st.session_state.get("portal_page",
                   st.session_state.get("sv_view", ""))

        log_id = f"LOG-{str(uuid.uuid4())[:8].upper()}"
        now    = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        _ensure_tab_headers(_AUDIT_TAB, _AUDIT_HEADERS)
        append_row(_AUDIT_TAB, [
            log_id,
            usuario_id,
            client_id,
            acao,
            recurso_tipo,
            recurso_id,
            rota,
            resultado,
            detalhe[:300],
            now,
        ])
    except Exception:
        # Audit log nunca deve quebrar o fluxo principal
        pass


def log_acesso_permitido(acao: str, recurso_tipo: str, recurso_id: str,
                         client_id: str = "") -> None:
    """Atalho para registrar acesso permitido."""
    log_acesso(acao=acao, recurso_tipo=recurso_tipo, recurso_id=recurso_id,
               resultado="permitido", client_id=client_id)


def log_acesso_negado(acao: str, recurso_tipo: str, recurso_id: str,
                      client_id: str = "", detalhe: str = "") -> None:
    """Atalho para registrar acesso negado."""
    log_acesso(acao=acao, recurso_tipo=recurso_tipo, recurso_id=recurso_id,
               resultado="negado", client_id=client_id, detalhe=detalhe)


# ── Campos que NUNCA devem ser expostos ao cliente ────────────────────────────

CAMPOS_INTERNOS = frozenset({
    "observacoes_internas",
    "observacao_interna",
    "obs_interna",
    "internal_notes",
    "erro_indexacao",
    "texto_extraido",
    "embedding_id",
    "status_indexacao",
    "notas_internas",
    "nota_interna",
})


def strip_internal_fields(data: dict) -> dict:
    """
    Remove campos internos de um dicionário antes de exibir ao cliente.
    Deve ser usado como última linha de defesa antes de renderizar dados.
    """
    return {
        k: v for k, v in data.items()
        if k.lower() not in CAMPOS_INTERNOS
    }
