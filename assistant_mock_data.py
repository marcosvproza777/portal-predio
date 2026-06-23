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
        {
            "id": "doc-mycom-001",
            "titulo": "Manual Operacional MYCOM - Sistema Chiller",
            "tipo_documento": "Manual operacional",
            "fabricante": "MYCOM",
            "modelo": "",
            "ativo": "Sistema Chiller / Compressor MYCOM",
            "resumo": (
                "Manual operacional com informações sobre funcionamento, desenho explodido, "
                "lista de peças, defeitos de funcionamento e correções, painel elétrico, "
                "fluxostato, trocador/condensador a placa e rotinas de manutenção preventiva/preditiva."
            ),
            "palavras_chave": (
                "MYCOM, sistema chiller, compressor, operação, manutenção, defeitos, "
                "pressão de descarga, pressão de sucção, pressão de óleo, temperatura de descarga, "
                "corrente elétrica, voltagem, análise de óleo, óleo ISO 68, filtros de óleo, "
                "filtro de sucção, filtro coalescente, alinhamento, painel elétrico, inversor de frequência, "
                "soft-starter, fluxostato, condensador a placa, inspeção diária, inspeção semanal, "
                "inspeção mensal, inspeção trimestral, inspeção semestral, 5000 horas, 10000 horas, "
                "20000 horas, revisão por condição, overhaul por condição"
            ),
            "arquivo_url": "/mock/manual-operacional-mycom-sistema-chiller.pdf",
            "arquivo_nome": "OPERACIONAL - Cópia.pdf",
            "status_indexacao": "Indexado",
            "chunks": [
                {
                    "chunk_index": 1, "titulo_secao": "Identificação do manual", "pagina_inicio": "1",
                    "conteudo": "Manual Operacional MYCOM - Sistema Chiller. Documento de operação e manutenção para sistema chiller/compressor MYCOM.",
                    "palavras_chave": "MYCOM, sistema chiller, compressor, operação, manual",
                },
                {
                    "chunk_index": 2, "titulo_secao": "Índice do manual", "pagina_inicio": "1",
                    "conteudo": "O manual contém desenho explodido do compressor, lista de peças, defeitos de funcionamento e suas eliminações, painel elétrico, fluxostato, trocador/condensador a placa e inspeções.",
                    "palavras_chave": "índice, desenho explodido, lista de peças, defeitos, painel elétrico, fluxostato, condensador, inspeções",
                },
                {
                    "chunk_index": 3, "titulo_secao": "Defeito — Motor não se movimenta", "pagina_inicio": "2",
                    "conteudo": "Causas e correções para motor que ronca e não dá partida, não reage ao botão da chave magnética, recebe força mas desliga, ou para logo após a partida. Causas: defeito do motor, correia apertada, excesso de carga, voltagem baixa, fusíveis interrompidos, mau contato, chave OP/HP atuada, baixa pressão de óleo, pressão de descarga alta, retorno de líquido.",
                    "palavras_chave": "motor não parte, motor ronca, chave magnética, fusível, voltagem baixa, OP, HP, baixa pressão de óleo, retorno de líquido",
                },
                {
                    "chunk_index": 4, "titulo_secao": "Defeito — Pressão anormalmente alta", "pagina_inicio": "3",
                    "conteudo": "O manual relaciona pressão anormalmente alta a quantidade insuficiente de água, temperatura de água elevada, distribuição irregular da água de arrefecimento, tubos obstruídos, ventilador defeituoso, filtro ou injetor entupido, excesso de refrigerante, presença de ar no condensador, óleo no condensador.",
                    "palavras_chave": "pressão alta, pressão de descarga, condensador, água de arrefecimento, refrigerante, ar no sistema, óleo no condensador",
                },
                {
                    "chunk_index": 5, "titulo_secao": "Defeito — Pressão de descarga muito baixa", "pagina_inicio": "4",
                    "conteudo": "Pressão de descarga muito baixa pode estar relacionada a excesso de água de arrefecimento, baixa temperatura da água, entupimento de tubulação de líquido ou sucção, compressão de líquido por abertura excessiva da válvula de expansão, falta de refrigerante ou vazamento em válvulas, anéis ou assentos.",
                    "palavras_chave": "pressão de descarga baixa, válvula de expansão, falta de refrigerante, tubulação entupida, vazamento",
                },
                {
                    "chunk_index": 6, "titulo_secao": "Defeito — Pressão de sucção alta ou baixa", "pagina_inicio": "5",
                    "conteudo": "Pressão de sucção alta: excesso de abertura da válvula de expansão, aumento de carga, queda de capacidade por vazamentos. Pressão de sucção baixa: falta de refrigerante, válvula de expansão fechada, óleo no evaporador, evaporador congelado, filtros obstruídos.",
                    "palavras_chave": "pressão de sucção, válvula de expansão, falta de refrigerante, evaporador congelado, filtro de sucção",
                },
                {
                    "chunk_index": 7, "titulo_secao": "Defeito — Ruído, vibração e superaquecimento", "pagina_inicio": "6",
                    "conteudo": "Som metálico, ruído alto, vibração excessiva e superaquecimento relacionados a corpos estranhos entre pistão e cabeçote, válvulas danificadas, abrasão, engripamento, ruptura de peças, bomba de óleo defeituosa, martelamento de líquido, martelamento de óleo, alinhamento incorreto, base frouxa, desbalanceamento.",
                    "palavras_chave": "ruído, vibração, superaquecimento, martelamento de líquido, martelamento de óleo, alinhamento incorreto, bomba de óleo",
                },
                {
                    "chunk_index": 8, "titulo_secao": "Defeito — Consumo anormal de óleo", "pagina_inicio": "7",
                    "conteudo": "Consumo anormal de óleo relacionado a retorno de líquido, obstrução de furo equalizador ou filtro, excesso de pressão, camisa quebrada, anel desgastado, pressão de óleo alta, diminuição de viscosidade, óleo deteriorado, bomba de óleo defeituosa e superaquecimento.",
                    "palavras_chave": "consumo de óleo, retorno de líquido, filtro obstruído, óleo deteriorado, viscosidade, bomba de óleo",
                },
                {
                    "chunk_index": 9, "titulo_secao": "Parâmetros operacionais — Pressão na parte de alta", "pagina_inicio": "8",
                    "conteudo": "Para amônia e R-22, condições normais de pressão na parte de alta entre 8 e 13,5 kg/cm². Valores acima: falta de água de arrefecimento, alta temperatura da água, condensador sujo, excesso de refrigerante, presença de ar no sistema.",
                    "palavras_chave": "pressão alta, amônia, R-22, kg/cm2, condensador, água de arrefecimento, parâmetros operacionais",
                },
                {
                    "chunk_index": 10, "titulo_secao": "Parâmetros operacionais — Pressão de óleo", "pagina_inicio": "9",
                    "conteudo": "A pressão de óleo deve ser a pressão no lado de baixa acrescida de 1,2 a 2 kg/cm². Pressão abaixo: diminuição de viscosidade, obstrução de filtro, óleo deteriorado ou bomba de óleo defeituosa. Ações: ajustar pressão, limpar filtro, trocar óleo, examinar a bomba.",
                    "palavras_chave": "pressão de óleo, viscosidade, filtro obstruído, óleo deteriorado, bomba de óleo, parâmetros",
                },
                {
                    "chunk_index": 11, "titulo_secao": "Parâmetros operacionais — Temperatura de descarga", "pagina_inicio": "10",
                    "conteudo": "Temperatura da seção de descarga para amônia e R-22 entre 80 e 140ºC; para R-12 entre 40 e 90ºC. Temperaturas acima: pressão anormalmente alta, falta de água de arrefecimento, vazamento de gás, filtro de sucção obstruído, camisa riscada, operação com superaquecimento.",
                    "palavras_chave": "temperatura de descarga, amônia, R-22, R-12, superaquecimento, filtro de sucção, óleo carbonizado",
                },
                {
                    "chunk_index": 12, "titulo_secao": "Painel elétrico", "pagina_inicio": "11",
                    "conteudo": "O painel elétrico é construído conforme projeto elétrico e mecânico. O inversor de frequência variável aciona motor elétrico variando frequência e tensão para controlar velocidade. Soft-starter controla a tensão de partida de motor trifásico. Botoeiras para retirada de alarmes e lâmpadas amarelas para indicação de nível alto e alarmes do chiller. Alarmes só devem ser retirados se os problemas forem solucionados.",
                    "palavras_chave": "painel elétrico, inversor de frequência, soft-starter, alarmes, chiller, motor elétrico",
                },
                {
                    "chunk_index": 13, "titulo_secao": "Fluxostato", "pagina_inicio": "12",
                    "conteudo": "O manual define fluxostato como chave de controle de fluxo usada para indicar presença ou ausência de fluxo dentro da tubulação. Ele atua como dispositivo complementar de segurança e proteção para ligar ou desligar alarmes, motores, compressores, máquinas e bombas d'água.",
                    "palavras_chave": "fluxostato, chave de fluxo, fluxo, segurança, alarme, compressor, bomba",
                },
                {
                    "chunk_index": 14, "titulo_secao": "Trocador/condensador a placa", "pagina_inicio": "12",
                    "conteudo": "O trocador/condensador a placa é um trocador de calor que utiliza placas de metal para transferência de calor entre dois fluidos. Importância de tratar quimicamente a água da torre para evitar incrustação de sujeira nas placas, o que prejudicaria a condensação.",
                    "palavras_chave": "trocador a placa, condensador a placa, água da torre, incrustação, transferência de calor, condensação",
                },
                {
                    "chunk_index": 15, "titulo_secao": "Manutenção — Inspeção diária", "pagina_inicio": "13",
                    "conteudo": "O manual recomenda registrar pressão de descarga, pressão de sucção, pressão de óleo, corrente e voltagem do motor, temperatura de descarga, temperatura de sucção e temperatura do óleo em diário de leitura. Intervalos de 2 a 3 horas durante operação.",
                    "palavras_chave": "inspeção diária, pressão de descarga, pressão de sucção, pressão de óleo, corrente, voltagem, temperatura, diário de leitura",
                },
                {
                    "chunk_index": 16, "titulo_secao": "Manutenção — Inspeção semanal", "pagina_inicio": "14",
                    "conteudo": "Inspecionar o sistema de entrada de gás e o sistema de óleo. Usar detector de gás ou cordão de enxofre para inspecionar linhas e conexões. Vazamento de óleo pelo selo de vedação acima de 6 gotas por minuto indica selo danificado.",
                    "palavras_chave": "inspeção semanal, sistema de gás, sistema de óleo, detector de gás, cordão de enxofre, vazamento de óleo, selo de vedação",
                },
                {
                    "chunk_index": 17, "titulo_secao": "Manutenção — Inspeção mensal", "pagina_inicio": "14",
                    "conteudo": "Checar o funcionamento dos trips de segurança, verificando se estão operando satisfatoriamente e corretamente ajustados. Testar a operação do sistema de controle de capacidade, incluindo calibração da slide válvula, testes de atuação da válvula direcional de 4 vias e verificação da capacidade do compressor.",
                    "palavras_chave": "inspeção mensal, trips de segurança, controle de capacidade, slide válvula, válvula direcional, compressor",
                },
                {
                    "chunk_index": 18, "titulo_secao": "Manutenção — Inspeção trimestral", "pagina_inicio": "15",
                    "conteudo": "Revisar ajustes dos instrumentos de pressão e temperatura, substituindo se necessário. Realizar lubrificação dos rolamentos do motor elétrico, revisão dos terminais e cabeamento e megagem do embobinamento.",
                    "palavras_chave": "inspeção trimestral, instrumentos de pressão, temperatura, lubrificação, rolamentos, motor elétrico, terminais, cabeamento, megagem",
                },
                {
                    "chunk_index": 19, "titulo_secao": "Manutenção — Inspeção semestral ou 5.000 horas", "pagina_inicio": "15",
                    "conteudo": "Repetir inspeções mensal e trimestral. Coletar amostra de óleo do compressor e enviar para análise de laboratório. Se relatório desfavorável, drenar e substituir o óleo lubrificante ISO 68. Substituir filtros de óleo. Conferir alinhamento dos eixos motor x compressor com tolerância radial/axial de 0,06 mm.",
                    "palavras_chave": "inspeção semestral, 5000 horas, análise de óleo, óleo ISO 68, filtro de óleo, alinhamento, motor x compressor, 0,06 mm",
                },
                {
                    "chunk_index": 20, "titulo_secao": "Manutenção — Inspeção anual ou 10.000 horas", "pagina_inicio": "16",
                    "conteudo": "Repetir inspeções mensal, trimestral e semestral. Substituir óleo lubrificante ISO 68, filtros de óleo e elemento filtro coalescente. Calibrar instrumentos de medição como manômetros e transmissores de pressão/temperatura, instrumentos de segurança como pressostatos, termostatos e fluxostatos, válvulas de segurança PSV. Testes de vazamento e estanqueidade na unidade compressora.",
                    "palavras_chave": "inspeção anual, 10000 horas, óleo ISO 68, filtro de óleo, filtro coalescente, calibração, manômetros, transmissores, pressostatos, termostatos, fluxostatos, PSV, estanqueidade",
                },
                {
                    "chunk_index": 21, "titulo_secao": "Referência técnica — 20.000 horas e revisão por condição", "pagina_inicio": "17",
                    "conteudo": "O manual cita inspeção bienal ou 20.000 horas incluindo desmontagem do compressor para análise visual e possível substituição do kit revisão. NO PORTAL PRED.IO, essa informação é referência técnica e NÃO é gatilho automático de manutenção. Revisão geral, desmontagem, kit revisão, overhaul ou intervenção pesada só devem ser indicados quando a saúde real da máquina indicar necessidade, considerando análise de vibração, análise de óleo, termografia, histórico operacional, falhas recorrentes, tendência de score e avaliação técnica da equipe Pred.IO. FRASE-CHAVE: 20.000 horas é referência técnica, não gatilho automático de overhaul. A decisão depende da saúde real da máquina.",
                    "palavras_chave": "20000 horas, revisão por condição, overhaul, kit revisão, desmontagem, análise preditiva, saúde da máquina, vibração, análise de óleo, termografia",
                },
            ],
        },
        {
            "id": "doc-mycom-002",
            "titulo": "Tabela de Óleos Homologados MAYEKAWA/MYCOM",
            "tipo_documento": "Tabela técnica",
            "fabricante": "MAYEKAWA / MYCOM",
            "modelo": "Todos os modelos/tipos aplicáveis conforme tabela",
            "ativo": "Compressores de refrigeração alternativos e de parafuso",
            "resumo": (
                "Tabela de seleção de óleos lubrificantes para compressores de refrigeração "
                "MYCOM/MAYEKAWA, incluindo fluidos aplicáveis, viscosidade ISO VG 68, classe de "
                "lubrificante, nome comercial e características típicas. A referência MYCOLD AB 68 "
                "deve ser substituída por MYCOLD PAO por descontinuação."
            ),
            "palavras_chave": (
                "óleo homologado, óleo lubrificante, MYCOM, MAYEKAWA, compressor, refrigeração, "
                "ISO VG 68, PAO, POE, mineral, Mycold PAO, Mycold AB, REFLO 68A, RAB 68, R 200, "
                "Mobil Gargoyle Arctic SHC 226 E, Mobil Gargoyle Arctic EH, Esso Refrigeration 68, "
                "Mobil EAL Arctic 68, Icematic SW 68, Capella HFC 68, Capella 68"
            ),
            "arquivo_url": "/mock/tabela-oleos-homologados-mayekawa-mycom.pdf",
            "arquivo_nome": "TABELAS DE ÓLEO HOMOLOGADOS (MAYEKAWA) (1).PDF",
            "status_indexacao": "Indexado",
            "chunks": [
                {
                    "chunk_index": 1, "titulo_secao": "Tabela de óleos homologados — PAO para Amônia/Freon", "pagina_inicio": "1",
                    "conteudo": "A tabela MAYEKAWA/MYCOM apresenta óleos ISO VG 68 para compressores de refrigeração. Para Amônia - NH3, Freon R12, R22 e R502, aparecem opções como REFLO 68A (TECNO DATA, semi-sintético PAO, -42°C), RAB 68 (TEC SUMMIT, sintético PAO), R 200 (KLUBBER SUMMIT, sintético PAO, apenas NH3) e MOBIL GARGOYLE ARCTIC SHC 226 E (MOBIL, sintético PAO, -45°C, IV 138).",
                    "palavras_chave": "PAO, amônia, NH3, Freon R12, R22, R502, REFLO 68A, RAB 68, R 200, Mobil Gargoyle Arctic SHC 226 E, óleo sintético",
                },
                {
                    "chunk_index": 2, "titulo_secao": "Tabela de óleos homologados — minerais", "pagina_inicio": "1",
                    "conteudo": "A tabela MAYEKAWA/MYCOM apresenta óleos minerais ISO VG 68 para NH3, R12, R22 e R502: MOBIL GARGOYLE ARCTIC EH (MOBIL, mineral, -26°C), ESSO REFRIGERATION 68 (MOBIL/ESSO, mineral, -33°C) e CAPELLA 68 (TEXACO, mineral, -36°C).",
                    "palavras_chave": "óleo mineral, ISO VG 68, Mobil Gargoyle Arctic EH, Esso Refrigeration 68, Capella 68, amônia, R22, R12, R502",
                },
                {
                    "chunk_index": 3, "titulo_secao": "Tabela de óleos homologados — POE para R134a/R404a", "pagina_inicio": "2",
                    "conteudo": "A tabela MAYEKAWA/MYCOM apresenta óleos sintéticos POE ISO VG 68 para R134a e R404a: MOBIL EAL ARCTIC 68 (MOBIL, POE, -43°C, IV 101), ICEMATIC SW 68 (CASTROL, POE, -39°C) e CAPELLA HFC 68 (TEXACO, POE, -57°C, densid. 0,971).",
                    "palavras_chave": "POE, Poliolester, R134a, R404a, Mobil EAL Arctic 68, Icematic SW 68, Capella HFC 68",
                },
                {
                    "chunk_index": 4, "titulo_secao": "Tabela de óleos homologados — Mycold PAO (MYCOM atual)", "pagina_inicio": "2",
                    "conteudo": "No Portal Pred.IO, o óleo MYCOM homologado atual é MYCOLD PAO (MYCOM, PAO sintético, NH3/R22, ISO VG 68, 53 cSt @ 40°C). A referência antiga MYCOLD AB 68 foi DESCONTINUADA e deve ser usada apenas como alias histórico para redirecionamento ao MYCOLD PAO. O Assistente Técnico não deve recomendar MYCOLD AB 68 como óleo atual. REGRA: MYCOLD AB 68 foi descontinuado. No Portal Pred.IO, a referência atual deve ser MYCOLD PAO.",
                    "palavras_chave": "Mycold PAO, Mycold AB 68, óleo descontinuado, óleo homologado MYCOM, MYCOM, ISO VG 68, PAO",
                },
            ],
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
    "especificacoes": {
        "oleo": None,
    },
    # Óleos homologados MAYEKAWA/MYCOM (ativos)
    "oleos_homologados": [
        {"nome": "REFLO 68A",                    "fabricante": "TECNO DATA",   "fluido": "NH3/R12/R22/R502", "classe": "PAO semi-sintético",  "viscosidade_cst": "58,0", "status": "Homologado"},
        {"nome": "RAB 68",                        "fabricante": "TEC SUMMIT",   "fluido": "NH3/R12/R22/R502", "classe": "PAO sintético",       "viscosidade_cst": "56,0", "status": "Homologado"},
        {"nome": "R 200",                         "fabricante": "KLUBBER SUMMIT","fluido": "NH3",             "classe": "PAO sintético",       "viscosidade_cst": "n/d",  "status": "Homologado"},
        {"nome": "MOBIL GARGOYLE ARCTIC SHC 226 E","fabricante": "MOBIL",       "fluido": "NH3/R12/R22/R502", "classe": "PAO sintético",       "viscosidade_cst": "68,0", "status": "Homologado"},
        {"nome": "MOBIL GARGOYLE ARCTIC EH",      "fabricante": "MOBIL",        "fluido": "NH3/R12/R22/R502", "classe": "Mineral",             "viscosidade_cst": "68,0", "status": "Homologado"},
        {"nome": "ESSO REFRIGERATION 68",         "fabricante": "MOBIL/ESSO",   "fluido": "NH3/R12/R22/R502", "classe": "Mineral",             "viscosidade_cst": "68,0", "status": "Homologado"},
        {"nome": "MOBIL EAL ARCTIC 68",           "fabricante": "MOBIL",        "fluido": "R134a/R404a",      "classe": "POE sintético",       "viscosidade_cst": "68,0", "status": "Homologado"},
        {"nome": "ICEMATIC SW 68",                "fabricante": "CASTROL",      "fluido": "R134a/R404a",      "classe": "POE sintético",       "viscosidade_cst": "68,0", "status": "Homologado"},
        {"nome": "CAPELLA HFC 68",                "fabricante": "TEXACO",       "fluido": "R134a/R404a",      "classe": "POE sintético",       "viscosidade_cst": "68,0", "status": "Homologado"},
        {"nome": "CAPELLA 68",                    "fabricante": "TEXACO",       "fluido": "NH3/R12/R22",      "classe": "Mineral",             "viscosidade_cst": "68,0", "status": "Homologado"},
        {"nome": "MYCOLD PAO",                    "fabricante": "MYCOM",        "fluido": "NH3/R22",          "classe": "PAO sintético",       "viscosidade_cst": "53,0", "status": "Homologado",
         "obs": "Óleo MYCOM atual. Substitui MYCOLD AB 68 (descontinuado)."},
    ],
    # Painel Mypro Touch — referência operacional
    "mypro_touch_info": {
        "modelos_validos": ["Mypro Touch", "Mypro Touch AD"],
        "modelos_invalidos": ["Mypro Touch+", "MYPRO Touch+", "MyproTouch+"],
        "acessos": [
            {"level": 1, "nome": "Operador",              "login": "ABC", "senha": "1111"},
            {"level": 2, "nome": "Supervisor/Administrador", "login": "XYZ", "senha": "2222"},
        ],
        "set_points": [
            {"id": "#1", "referencia": "-10 °C"},
            {"id": "#2", "referencia": "-40 °C"},
        ],
        "set_point_cut_in":  "Pressão em que o compressor liga automaticamente",
        "set_point_cut_out": "Pressão em que o compressor desliga automaticamente por baixa pressão",
        "obs": (
            "Para partida, parada, reset de alarme, set point e capacidade manual: "
            "use apenas se você for operador autorizado. O Assistente Técnico Pred.IO "
            "não executa comando na máquina."
        ),
    },
    # MYCOLD AB 68 — histórico/inativo apenas para redirecionamento
    "mycold_ab_historico": {
        "nome": "MYCOLD AB 68",
        "status": "Descontinuado",
        "substituido_por": "MYCOLD PAO",
        "obs": "Produto descontinuado. Quando citado pelo cliente, responder que foi substituído por MYCOLD PAO.",
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
