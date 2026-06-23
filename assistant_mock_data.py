"""
Dados mockados estruturados para o Assistente Técnico Pred.IO.

SEGURANÇA:
  - Dados indexados por client_id (sempre da sessão, nunca do front-end).
  - Documentos internos ("Apenas equipe Pred.IO") NÃO estão nesta camada
    — são filtrados por get_documentos_tecnicos() antes de chegar aqui.
  - Observações internas NÃO existem nesta camada.

SUBSTITUIÇÃO:
  Quando sheets.get_documentos_tecnicos() estiver com dados reais,
  o campo "documentos" de get_mock_context() é ignorado — veja
  assistant_engine.get_client_context().
"""

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
    # Documentos mock — Documento 3 (interno) NÃO aparece aqui.
    # Em produção, get_documentos_tecnicos(client_id) filtra "Apenas equipe Pred.IO".
    "documentos": [
        {
            "id": "doc-001",
            "titulo": "Manual Técnico - Unidade Compressora Parafuso 200 VLD",
            "tipo_documento": "Manual técnico",
            "fabricante": "",
            "modelo": "200 VLD",
            "ativo": "Unidade Compressora Parafuso 200 VLD",
            "resumo": "Manual técnico de referência para operação, manutenção e especificações da unidade compressora.",
            "palavras_chave": "compressor, 200 VLD, unidade compressora, manual, manutenção",
            "arquivo_url": "/mock/manual-unidade-compressora-200-vld.pdf",
            "arquivo_nome": "manual-unidade-compressora-200-vld.pdf",
            "status_indexacao": "Indexado",
            "chunks": [
                {
                    "chunk_index": 1,
                    "titulo_secao": "Sistema de Lubrificação",
                    "conteudo": (
                        "O sistema de lubrificação utiliza óleo sintético VDL 46 (ISO VG 46). "
                        "Capacidade: 35 litros. Temperatura operacional: 70°C a 85°C. "
                        "Alarme acima de 95°C; desligamento acima de 105°C. Pressão mínima: 2,0 bar."
                    ),
                    "palavras_chave": "lubrificação, óleo, temperatura, pressão, VDL 46, reservatório",
                    "pagina_inicio": "1",
                },
                {
                    "chunk_index": 2,
                    "titulo_secao": "Especificações de Óleo e Intervalos de Troca",
                    "conteudo": (
                        "Óleo recomendado: VDL 46 sintético. Equivalentes: Shell Corena S4 R 46, "
                        "Castrol Aircol PD 46, Mobil Rarus SHC 1024. "
                        "Troca a cada 2.000 horas ou 1 ano. Análise de óleo a cada 500 horas. "
                        "Filtro separador: troca a cada 4.000 horas."
                    ),
                    "palavras_chave": "óleo recomendado, VDL 46, troca de óleo, 2000 horas, análise de óleo, filtro separador",
                    "pagina_inicio": "2",
                },
                {
                    "chunk_index": 3,
                    "titulo_secao": "Manutenção dos Filtros",
                    "conteudo": (
                        "Filtro de ar: inspeção 250h, limpeza 500h, troca 2.000h. "
                        "Filtro de óleo: troca 1.000h. Filtro separador: troca 4.000h. "
                        "Filtro do resfriador: limpeza 500h com ar comprimido."
                    ),
                    "palavras_chave": "filtro, ar, óleo, troca, inspeção, resfriador, separador",
                    "pagina_inicio": "3",
                },
                {
                    "chunk_index": 4,
                    "titulo_secao": "Critérios para Overhaul",
                    "conteudo": (
                        "O overhaul não é determinado apenas pelo horímetro. "
                        "A decisão considera: vibração (≥7,5 mm/s RMS), análise de óleo (ferro >50 ppm), "
                        "termografia (pontos quentes >15°C acima da referência) e histórico de falhas. "
                        "Intervalo máximo: 12.000 horas, podendo ser antecipado pelos indicadores preditivos."
                    ),
                    "palavras_chave": "overhaul, revisão geral, horímetro, vibração, análise de óleo, termografia, preditivo",
                    "pagina_inicio": "4",
                },
                {
                    "chunk_index": 5,
                    "titulo_secao": "Segurança e Operação",
                    "conteudo": (
                        "Pressão máxima: 8,0 bar. Temperatura máxima de descarga: 110°C. "
                        "Nunca bloquear válvula de segurança. Purga do separador: diária. "
                        "Em caso de alarme: aguardar resfriamento 15 min antes de abrir tampas. "
                        "Espaço livre: 1 metro ao redor."
                    ),
                    "palavras_chave": "segurança, pressão máxima, temperatura, válvula, purga, alarme, operação",
                    "pagina_inicio": "5",
                },
            ],
        },
        {
            "id": "doc-002",
            "titulo": "Datasheet - Motor WEG 350 CV",
            "tipo_documento": "Datasheet",
            "fabricante": "WEG",
            "modelo": "350 CV",
            "ativo": "Motor WEG 350 CV",
            "resumo": "Documento técnico com informações do motor WEG 350 CV.",
            "palavras_chave": "motor, WEG, 350 CV, datasheet, inversor",
            "arquivo_url": "/mock/datasheet-motor-weg-350cv.pdf",
            "arquivo_nome": "datasheet-motor-weg-350cv.pdf",
            "status_indexacao": "Não indexado",
            "chunks": [],
        },
        # DOC-003 é interno ("Apenas equipe Pred.IO") — NÃO aparece aqui.
        # Validação: buscar por "procedimento interno analise vibracao" não deve
        # retornar doc algum para o cliente, pois o doc está excluído desde a origem.
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
    "especificacoes": {
        "oleo": None,
    },
}


def get_mock_context(client_id: str) -> dict:
    """
    Retorna o contexto mockado para um client_id.

    SEGURANÇA: client_id SEMPRE da sessão. Nunca do front-end.
    Documentos internos já excluídos neste mock.
    Observações internas nunca presentes.
    """
    import copy
    return copy.deepcopy(_DEFAULT_CONTEXT)


# Dados de documentos internos (para referência/teste — NUNCA expor ao cliente)
_DOCS_INTERNOS_PRED_IO = [
    {
        "id": "doc-int-001",
        "titulo": "Procedimento Interno Pred.IO - Análise de Vibração",
        "tipo_documento": "Procedimento de manutenção",
        "visibilidade": "Apenas equipe Pred.IO",
        "nota": "Este documento NUNCA deve aparecer para clientes. "
                "Filtrado por get_documentos_tecnicos() na camada sheets.",
    },
]
