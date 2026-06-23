"""
Dados mockados estruturados para o Assistente Técnico Pred.IO.

SEGURANÇA:
  - Dados são indexados por client_id (vem da sessão, nunca do front-end).
  - Documentos internos da Pred.IO NÃO existem aqui — estes dados são
    os dados AUTORIZADOS que o cliente pode ver.
  - Observações internas NÃO aparecem nesta camada.

SUBSTITUIÇÃO:
  Quando os dados reais estiverem disponíveis via Google Sheets, substituir
  o retorno de get_client_context() em assistant_engine.py pelos dados reais.
  O formato do dict deve permanecer o mesmo para o JS continuar funcionando.
"""

# ---------------------------------------------------------------------------
# Estrutura padrão (fallback para clientes sem dados específicos cadastrados)
# ---------------------------------------------------------------------------
_DEFAULT_CONTEXT: dict = {
    "empresa": "Cliente Pred.IO",
    "ativos": [
        {
            "id": "ativo-001",
            "nome": "Unidade Compressora Parafuso 200 VLD",
            "status": "Atenção",
            "score": 72,
            "componentes": [
                {"id": "comp-001", "nome": "Bomba de Óleo M60P",  "status": "Crítico"},
                {"id": "comp-002", "nome": "Motor WEG 350 CV",    "status": "Normal"},
                {"id": "comp-003", "nome": "Filtro de Ar",         "status": "Normal"},
            ],
        },
        {
            "id": "ativo-002",
            "nome": "Motor WEG 350 CV",
            "status": "Normal",
            "score": 91,
            "componentes": [],
        },
    ],
    "manutencoes": [
        {
            "id": "man-001",
            "ativo": "Unidade Compressora Parafuso 200 VLD",
            "acao": "Análise de óleo",
            "tipo": "Preditiva",
            "vencimento_horas": 320,
            "vencimento_data": None,
        },
        {
            "id": "man-002",
            "ativo": "Unidade Compressora Parafuso 200 VLD",
            "acao": "Inspeção e limpeza do filtro de óleo",
            "tipo": "Preventiva",
            "vencimento_horas": 320,
            "vencimento_data": None,
        },
        {
            "id": "man-003",
            "ativo": "Unidade Compressora Parafuso 200 VLD",
            "acao": "Análise de vibração",
            "tipo": "Preditiva",
            "vencimento_horas": None,
            "vencimento_data": "17/08/2026",
        },
        {
            "id": "man-004",
            "ativo": "Unidade Compressora Parafuso 200 VLD",
            "acao": "Termografia",
            "tipo": "Preditiva",
            "vencimento_horas": None,
            "vencimento_data": "17/10/2026",
        },
    ],
    "relatorios": [
        {
            "id": "rel-001",
            "titulo": "Análise Preditiva — Unidade Compressora Parafuso 200 VLD",
            "tipo": "Preditiva",
            "data": "10/05/2026",
        },
        {
            "id": "rel-002",
            "titulo": "Análise de Óleo — Compressor Parafuso",
            "tipo": "Óleo",
            "data": "02/04/2026",
        },
        {
            "id": "rel-003",
            "titulo": "Análise de Vibração — Motor WEG 350 CV",
            "tipo": "Vibração",
            "data": "15/03/2026",
        },
    ],
    "documentos": [
        {
            "id": "doc-001",
            "titulo": "Manual do Compressor de Parafuso 200 VLD",
            "tipo": "Manual",
            "ativo": "Unidade Compressora Parafuso 200 VLD",
        },
        {
            "id": "doc-002",
            "titulo": "Procedimento de Análise de Óleo",
            "tipo": "Procedimento",
            "ativo": "Unidade Compressora Parafuso 200 VLD",
        },
        {
            "id": "doc-003",
            "titulo": "Guia de Inspeção Preventiva",
            "tipo": "Guia",
            "ativo": "Unidade Compressora Parafuso 200 VLD",
        },
    ],
    "chamados": [
        {
            "id": "cha-001",
            "titulo": "Ruído anormal no compressor",
            "status": "Em andamento",
            "prioridade": "Alta",
            "data": "05/06/2026",
        }
    ],
    "alertas": [
        {
            "id": "ale-001",
            "titulo": "Bomba de Óleo M60P sinalizada como crítica",
            "prioridade": "Crítica",
            "data": "10/06/2026",
        }
    ],
    # None = sem especificação cadastrada → consultar manual / abrir chamado
    "especificacoes": {
        "oleo": None,
    },
}


def get_mock_context(client_id: str) -> dict:
    """
    Retorna o contexto mockado para um client_id.

    SEGURANÇA: client_id SEMPRE vem da sessão do servidor.
    Se não houver dados específicos para o cliente, retorna o contexto padrão.
    Nunca expõe dados de outro cliente.

    Quando os dados reais estiverem no Sheets, substituir por:
      return _build_context_from_sheets(client_id)
    """
    import copy
    # Aqui futuramente: if client_id in _CLIENTES_ESPECIFICOS: return _CLIENTES_ESPECIFICOS[client_id]
    ctx = copy.deepcopy(_DEFAULT_CONTEXT)
    return ctx
