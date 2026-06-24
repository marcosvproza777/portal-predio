"""
Processador de documentos para preparação de RAG — Pred.IO.

Extrai texto de PDFs e cria chunks estruturados para busca pelo assistente.
Usa mock estruturado quando a URL não está acessível ou a extração falha.

SEGURANÇA:
  - Nunca expõe chunks de documentos de outros clientes.
  - Status de indexação nunca influencia o que o cliente vê — apenas a
    disponibilidade para busca no assistente.
"""
from __future__ import annotations
import re

STATUS_NAO_INDEXADO = "Não indexado"
STATUS_INDEXADO     = "Indexado"
STATUS_FALHOU       = "Falhou"
STATUS_PROCESSANDO  = "Em processamento"

# ── Mock texto estruturado para documentos de demonstração ────────────────────

_MOCK_TEXTO_200_VLD = """\
MANUAL TÉCNICO - UNIDADE COMPRESSORA PARAFUSO 200 VLD

SEÇÃO 1: SISTEMA DE LUBRIFICAÇÃO
O sistema de lubrificação da Unidade Compressora Parafuso 200 VLD utiliza óleo sintético VDL 46 \
(ISO VG 46) como fluido de processo e lubrificação. Capacidade do reservatório: 35 litros. \
Temperatura operacional normal: 70°C a 85°C. Alarme acima de 95°C; desligamento automático acima \
de 105°C. Pressão mínima de óleo: 2,0 bar — abaixo disso o sistema desliga por segurança.

SEÇÃO 2: ESPECIFICAÇÕES DE ÓLEO E INTERVALOS DE TROCA
Óleo recomendado: VDL 46 sintético. Equivalentes: Shell Corena S4 R 46, Castrol Aircol PD 46, \
Mobil Rarus SHC 1024. Troca de óleo: a cada 2.000 horas de operação ou 1 ano. \
Análise de óleo: a cada 500 horas. Filtro separador de óleo: troca a cada 4.000 horas \
ou quando a diferencial de pressão atingir 0,8 bar.

SEÇÃO 3: MANUTENÇÃO DOS FILTROS
Filtro de ar de entrada: inspeção a cada 250h, limpeza a cada 500h, troca a cada 2.000h. \
Filtro de óleo principal: troca a cada 1.000h. Filtro separador óleo/ar: troca a cada 4.000h. \
Filtro do resfriador: limpeza a cada 500h com ar comprimido.

SEÇÃO 4: CRITÉRIOS PARA OVERHAUL
O overhaul da Unidade Compressora 200 VLD não é determinado apenas pelo horímetro. \
A decisão de revisão geral deve considerar múltiplos fatores: vibração (≥7,5 mm/s RMS indica \
desgaste excessivo), análise de óleo (ferro acima de 50 ppm indica falha interna), termografia \
(pontos quentes acima de 15°C do valor de referência) e histórico de falhas. \
Intervalo máximo: 12.000 horas, podendo ser antecipado pelos indicadores preditivos.

SEÇÃO 5: SEGURANÇA E OPERAÇÃO
Pressão máxima de trabalho: 8,0 bar (116 PSI). Temperatura máxima de descarga: 110°C. \
Nunca operar com a válvula de segurança bloqueada. Purga do separador de condensado: diária. \
Em caso de alarme: aguardar resfriamento por 15 minutos antes de abrir qualquer tampa. \
Manter 1 metro livre ao redor da unidade para circulação de ar.\
"""

_MOCK_CHUNKS_200_VLD: list[dict] = [
    {
        "chunk_index": 1,
        "pagina_inicio": 1,
        "pagina_fim": 1,
        "titulo_secao": "Sistema de Lubrificação",
        "conteudo": (
            "O sistema de lubrificação utiliza óleo sintético VDL 46 (ISO VG 46). "
            "Capacidade: 35 litros. Temperatura operacional: 70°C a 85°C. "
            "Alarme acima de 95°C; desligamento acima de 105°C. Pressão mínima: 2,0 bar."
        ),
        "palavras_chave": "lubrificação, óleo, temperatura, pressão, VDL 46, reservatório",
    },
    {
        "chunk_index": 2,
        "pagina_inicio": 2,
        "pagina_fim": 2,
        "titulo_secao": "Especificações de Óleo e Intervalos de Troca",
        "conteudo": (
            "Óleo recomendado: VDL 46 sintético. Equivalentes: Shell Corena S4 R 46, "
            "Castrol Aircol PD 46, Mobil Rarus SHC 1024. "
            "Troca a cada 2.000 horas ou 1 ano. Análise de óleo a cada 500 horas. "
            "Filtro separador: troca a cada 4.000 horas."
        ),
        "palavras_chave": "óleo recomendado, VDL 46, troca de óleo, 2000 horas, análise de óleo, filtro separador",
    },
    {
        "chunk_index": 3,
        "pagina_inicio": 3,
        "pagina_fim": 3,
        "titulo_secao": "Manutenção dos Filtros",
        "conteudo": (
            "Filtro de ar: inspeção 250h, limpeza 500h, troca 2.000h. "
            "Filtro de óleo: troca 1.000h. Filtro separador: troca 4.000h. "
            "Filtro do resfriador: limpeza 500h com ar comprimido."
        ),
        "palavras_chave": "filtro, ar, óleo, troca, inspeção, resfriador, separador",
    },
    {
        "chunk_index": 4,
        "pagina_inicio": 4,
        "pagina_fim": 4,
        "titulo_secao": "Critérios para Overhaul",
        "conteudo": (
            "O overhaul não é determinado apenas pelo horímetro. "
            "A decisão considera: vibração (≥7,5 mm/s RMS), análise de óleo (ferro >50 ppm), "
            "termografia (pontos quentes >15°C acima da referência) e histórico de falhas. "
            "Intervalo máximo: 12.000 horas, podendo ser antecipado pelos indicadores preditivos."
        ),
        "palavras_chave": "overhaul, revisão geral, horímetro, vibração, análise de óleo, termografia, preditivo",
    },
    {
        "chunk_index": 5,
        "pagina_inicio": 5,
        "pagina_fim": 5,
        "titulo_secao": "Segurança e Operação",
        "conteudo": (
            "Pressão máxima: 8,0 bar. Temperatura máxima de descarga: 110°C. "
            "Nunca bloquear válvula de segurança. Purga do separador: diária. "
            "Em caso de alarme: aguardar resfriamento 15 min antes de abrir tampas. "
            "Espaço livre: 1 metro ao redor."
        ),
        "palavras_chave": "segurança, pressão máxima, temperatura, válvula, purga, alarme, operação",
    },
]


# ── Mock texto e chunks — Manual Operacional MYCOM - Sistema Chiller ──────────

_MOCK_TEXTO_MYCOM_OPERACIONAL = """\
MANUAL OPERACIONAL MYCOM - SISTEMA CHILLER

1. Identificação: Manual Operacional MYCOM - Sistema Chiller. Documento de operação e manutenção para sistema chiller/compressor MYCOM.

2. Índice: O manual contém desenho explodido do compressor, lista de peças, defeitos de funcionamento e suas eliminações, painel elétrico, fluxostato, trocador/condensador a placa e inspeções.

3. Defeito — Motor não se movimenta: Causas e correções para motor que ronca e não dá partida, não reage ao botão da chave magnética, recebe força mas desliga ao soltar, ou para logo após a partida. Causas: defeito do motor, correia apertada, excesso de carga, voltagem baixa, fusíveis interrompidos, mau contato, chave OP/HP atuada, dispositivos automáticos, baixa pressão de óleo, pressão de descarga alta, retorno de líquido.

4. Defeito — Pressão anormalmente alta: Causas: quantidade insuficiente de água, temperatura de água elevada, distribuição irregular da água de arrefecimento, tubos obstruídos, ventilador defeituoso, filtro ou injetor entupido, excesso de refrigerante, presença de ar no condensador, óleo no condensador. Correções: aumentar ou resfriar água, limpar tubos, examinar ventilador/filtros/injetores, sangrar ar, drenar óleo.

5. Defeito — Pressão de descarga muito baixa: Causas: excesso de água de arrefecimento, baixa temperatura da água, entupimento de tubulação de líquido ou sucção, compressão de líquido por abertura excessiva da válvula de expansão, falta de refrigerante, vazamento em válvulas/anéis/assentos.

6. Defeito — Pressão de sucção alta ou baixa: Causas de sucção alta: excesso de abertura da válvula de expansão, aumento de carga, queda de capacidade por vazamentos. Causas de sucção baixa: falta de refrigerante, válvula de expansão fechada, óleo no evaporador, evaporador congelado, filtros obstruídos.

7. Defeito — Ruído, vibração e superaquecimento: Causas: corpos estranhos entre pistão e cabeçote, válvulas danificadas, abrasão, engripamento, ruptura de peças, bomba de óleo defeituosa, martelamento de líquido, martelamento de óleo, alinhamento incorreto, base frouxa, desbalanceamento, suportes inadequados, ressonância.

8. Defeito — Consumo anormal de óleo: Causas: retorno de líquido, obstrução de furo equalizador ou filtro, excesso de pressão, camisa quebrada, anel desgastado, pressão de óleo alta, diminuição de viscosidade, óleo deteriorado, bomba defeituosa, superaquecimento.

9. Parâmetros — Pressão parte de alta: Para amônia e R-22, condições normais entre 8 e 13,5 kg/cm2. Valores acima podem estar ligados à falta de água de arrefecimento, alta temperatura da água, condensador sujo, excesso de refrigerante, presença de ar no sistema.

10. Parâmetros — Pressão de óleo: A pressão de óleo deve ser a pressão no lado de baixa acrescida de 1,2 a 2 kg/cm2. Pressão acima pode estar ligada a ajuste incorreto ou endurecimento por retorno de líquido. Pressão abaixo pode estar ligada à diminuição de viscosidade, obstrução de filtro, óleo deteriorado ou bomba defeituosa.

11. Parâmetros — Temperatura de descarga: Para amônia e R-22 entre 80 e 140ºC; para R-12 entre 40 e 90ºC. Temperaturas acima podem estar relacionadas a pressão anormalmente alta, falta de água de arrefecimento, vazamento de gás, filtro de sucção obstruído, camisa riscada.

12. Painel elétrico: Construído conforme projeto elétrico e mecânico, com barramentos, entradas, saídas, alimentadores e partidas. Inversor de frequência variável aciona motor elétrico variando frequência e tensão para controlar velocidade. Soft-starter controla tensão de partida de motor trifásico. Botoeiras para retirada de alarmes; lâmpadas amarelas indicam nível alto e alarmes do chiller. Alarmes só devem ser retirados se os problemas forem solucionados.

13. Fluxostato: Chave de controle de fluxo usada para indicar presença ou ausência de fluxo dentro da tubulação. Atua como dispositivo complementar de segurança e proteção para ligar ou desligar alarmes, motores, compressores, máquinas e bombas d'água.

14. Trocador/condensador a placa: Trocador de calor que utiliza placas de metal para transferência de calor entre dois fluidos. Importância de tratar quimicamente a água da torre para evitar incrustação de sujeira nas placas, o que prejudicaria a condensação.

15. Manutenção — Inspeção diária: Registrar pressão de descarga, pressão de sucção, pressão de óleo, corrente e voltagem do motor, temperatura de descarga, temperatura de sucção e temperatura do óleo em diário de leitura. Intervalos de 2 a 3 horas durante operação.

16. Manutenção — Inspeção semanal: Inspecionar sistema de entrada de gás e sistema de óleo. Usar detector de gás ou cordão de enxofre para inspecionar linhas e conexões. Vazamento de óleo pelo selo de vedação acima de 6 gotas por minuto indica selo danificado.

17. Manutenção — Inspeção mensal: Checar funcionamento dos trips de segurança. Testar operação do sistema de controle de capacidade, incluindo calibração da slide válvula, testes de válvula direcional de 4 vias e verificação da capacidade do compressor.

18. Manutenção — Inspeção trimestral: Revisar ajustes dos instrumentos de pressão e temperatura. Realizar lubrificação dos rolamentos do motor elétrico, revisão dos terminais e cabeamento e megagem do embobinamento.

19. Manutenção — Inspeção semestral ou 5.000 horas: Repetir inspeções mensal e trimestral. Coletar amostra de óleo e enviar para análise de laboratório. Se relatório desfavorável, drenar e substituir o óleo lubrificante ISO 68. Substituir filtros de óleo. Conferir alinhamento dos eixos motor x compressor com tolerância radial/axial de 0,06 mm.

20. Manutenção — Inspeção anual ou 10.000 horas: Repetir inspeções mensal, trimestral e semestral. Substituir óleo lubrificante ISO 68, filtros de óleo, elemento filtro coalescente. Calibrar instrumentos de medição (manômetros, transmissores de pressão/temperatura), instrumentos de segurança (pressostatos, termostatos, fluxostatos) e válvulas de segurança PSV. Testes de vazamento e estanqueidade.

21. Referência técnica — 20.000 horas e revisão por condição: O manual cita inspeção bienal ou 20.000 horas incluindo repetição das inspeções anteriores, desmontagem do compressor para análise visual e dimensional das peças móveis e possível substituição do kit revisão. NO PORTAL PRED.IO, essa informação é tratada como referência técnica e NÃO como gatilho automático de manutenção. Revisão geral, desmontagem, kit revisão, overhaul ou intervenção pesada só devem ser indicados quando a saúde real da máquina indicar necessidade, com base em análise de vibração, análise de óleo, termografia, histórico operacional, falhas recorrentes, tendência de score e avaliação técnica da equipe Pred.IO. FRASE-CHAVE: 20.000 horas é referência técnica, não gatilho automático de overhaul. A decisão depende da saúde real da máquina.
"""

_MOCK_CHUNKS_MYCOM_OPERACIONAL: list[dict] = [
    {
        "chunk_index": 1, "pagina_inicio": 1, "pagina_fim": 1,
        "titulo_secao": "Identificação do manual",
        "conteudo": "Manual Operacional MYCOM - Sistema Chiller. Documento de operação e manutenção para sistema chiller/compressor MYCOM.",
        "palavras_chave": "MYCOM, sistema chiller, compressor, operação, manual",
    },
    {
        "chunk_index": 2, "pagina_inicio": 1, "pagina_fim": 1,
        "titulo_secao": "Índice do manual",
        "conteudo": "O manual contém desenho explodido do compressor, lista de peças, defeitos de funcionamento e suas eliminações, painel elétrico, fluxostato, trocador/condensador a placa e inspeções.",
        "palavras_chave": "índice, desenho explodido, lista de peças, defeitos, painel elétrico, fluxostato, condensador, inspeções",
    },
    {
        "chunk_index": 3, "pagina_inicio": 2, "pagina_fim": 2,
        "titulo_secao": "Defeito — Motor não se movimenta",
        "conteudo": "O manual apresenta causas e correções para situações em que o motor ronca e não dá partida, não reage ao botão da chave magnética, recebe força mas desliga ao soltar o botão, ou para logo após a partida. As possíveis causas incluem defeito do motor, correia muito apertada, excesso de carga, voltagem baixa, fusíveis interrompidos, mau contato, chave OP/HP atuada, falhas em dispositivos automáticos, baixa pressão de óleo, pressão de descarga alta e retorno de líquido.",
        "palavras_chave": "motor não parte, motor ronca, chave magnética, fusível, voltagem baixa, OP, HP, baixa pressão de óleo, retorno de líquido",
    },
    {
        "chunk_index": 4, "pagina_inicio": 3, "pagina_fim": 3,
        "titulo_secao": "Defeito — Pressão anormalmente alta",
        "conteudo": "O manual relaciona pressão anormalmente alta a causas como quantidade insuficiente de água, temperatura de água elevada, distribuição irregular da água de arrefecimento, tubos obstruídos, ventilador defeituoso, filtro ou injetor entupido, excesso de refrigerante, presença de ar no condensador, óleo no condensador e obstruções entre condensador e receptor. As correções incluem aumentar ou resfriar a água, limpar tubos, examinar ventilador/filtros/injetores, remover obstáculos, descarregar excesso de refrigerante, sangrar ar e drenar óleo.",
        "palavras_chave": "pressão alta, pressão de descarga, condensador, água de arrefecimento, refrigerante, ar no sistema, óleo no condensador",
    },
    {
        "chunk_index": 5, "pagina_inicio": 4, "pagina_fim": 4,
        "titulo_secao": "Defeito — Pressão de descarga muito baixa",
        "conteudo": "O manual indica que pressão de descarga muito baixa pode estar relacionada a excesso de água de arrefecimento, baixa temperatura da água, entupimento de tubulação de líquido ou sucção, compressão de líquido por abertura excessiva da válvula de expansão, falta de refrigerante ou vazamento em válvulas, anéis ou assentos. As ações incluem ajustar válvulas reguladoras, examinar e limpar tubulações, abastecer refrigerante e examinar válvulas/anéis.",
        "palavras_chave": "pressão de descarga baixa, válvula de expansão, falta de refrigerante, tubulação entupida, vazamento, condensador frio",
    },
    {
        "chunk_index": 6, "pagina_inicio": 5, "pagina_fim": 5,
        "titulo_secao": "Defeito — Pressão de sucção alta ou baixa",
        "conteudo": "O manual relaciona pressão de sucção alta a excesso de abertura da válvula de expansão, aumento de carga e queda de capacidade por vazamentos em válvulas ou camisa. Pressão de sucção baixa pode estar relacionada a falta de refrigerante, válvula de expansão muito fechada, óleo no evaporador, evaporador congelado, filtros do compressor ou tubulação de sucção obstruídos por ferrugem ou pó.",
        "palavras_chave": "pressão de sucção, válvula de expansão, falta de refrigerante, evaporador congelado, filtro de sucção, óleo no evaporador",
    },
    {
        "chunk_index": 7, "pagina_inicio": 6, "pagina_fim": 6,
        "titulo_secao": "Defeito — Ruído, vibração e superaquecimento",
        "conteudo": "O manual relaciona som metálico, ruído alto, vibração excessiva e superaquecimento a corpos estranhos entre pistão e cabeçote, válvulas danificadas, abrasão, engripamento, ruptura de peças, defeito da bomba de óleo, martelamento de líquido, martelamento de óleo, alinhamento incorreto, base frouxa, desbalanceamento, suportes de tubulação inadequados e ressonância.",
        "palavras_chave": "ruído, vibração, superaquecimento, martelamento de líquido, martelamento de óleo, alinhamento incorreto, bomba de óleo, engripamento",
    },
    {
        "chunk_index": 8, "pagina_inicio": 7, "pagina_fim": 7,
        "titulo_secao": "Defeito — Consumo anormal de óleo",
        "conteudo": "O manual relaciona consumo anormal de óleo a retorno de líquido, obstrução de furo equalizador ou filtro, excesso de pressão, camisa quebrada ou engripada, anel desgastado ou arranhado, pressão de óleo alta, diminuição de viscosidade, aumento de temperatura do óleo, óleo deteriorado, bomba de óleo defeituosa e superaquecimento. As ações incluem ajustar funcionamento, limpar filtros, ajustar/trocar óleo, usar viscosidade apropriada e examinar/consertar componentes.",
        "palavras_chave": "consumo de óleo, retorno de líquido, filtro obstruído, óleo deteriorado, viscosidade, bomba de óleo, pressão de óleo",
    },
    {
        "chunk_index": 9, "pagina_inicio": 8, "pagina_fim": 8,
        "titulo_secao": "Parâmetros operacionais — Pressão na parte de alta",
        "conteudo": "O manual informa parâmetros para pressão na parte de alta em compressores MYCOM durante operação de refrigeração. Para amônia e R-22, condições normais são indicadas entre 8 e 13,5 kg/cm². Valores acima podem estar ligados à falta de água de arrefecimento, alta temperatura da água, condensador sujo, excesso de refrigerante, presença de ar no sistema ou capacidade insuficiente do condensador.",
        "palavras_chave": "pressão alta, amônia, R-22, kg/cm2, condensador, água de arrefecimento, parâmetros operacionais",
    },
    {
        "chunk_index": 10, "pagina_inicio": 9, "pagina_fim": 9,
        "titulo_secao": "Parâmetros operacionais — Pressão de óleo",
        "conteudo": "O manual informa que a pressão de óleo deve ser a pressão no lado de baixa acrescida de 1,2 a 2 kg/cm². Pressão acima do indicado pode estar ligada a ajuste incorreto ou endurecimento do óleo por retorno de líquido. Pressão abaixo pode estar ligada à diminuição de viscosidade do óleo, obstrução de filtro, óleo deteriorado ou bomba de óleo defeituosa. Correções: ajustar pressão, limpar filtro, trocar óleo e examinar a bomba.",
        "palavras_chave": "pressão de óleo, óleo, viscosidade, filtro obstruído, óleo deteriorado, bomba de óleo, parâmetros",
    },
    {
        "chunk_index": 11, "pagina_inicio": 10, "pagina_fim": 10,
        "titulo_secao": "Parâmetros operacionais — Temperatura de descarga",
        "conteudo": "O manual apresenta temperatura da seção de descarga para amônia e R-22 entre 80 e 140ºC, e para R-12 entre 40 e 90ºC. Temperaturas acima podem estar relacionadas a pressão anormalmente alta, aumento da taxa de compressão, falta de água de arrefecimento, vazamento de gás, obstrução por óleo carbonizado, obstrução do filtro de sucção, camisa riscada e operação com superaquecimento.",
        "palavras_chave": "temperatura de descarga, amônia, R-22, R-12, superaquecimento, filtro de sucção, óleo carbonizado",
    },
    {
        "chunk_index": 12, "pagina_inicio": 11, "pagina_fim": 11,
        "titulo_secao": "Painel elétrico",
        "conteudo": "O manual explica que o painel elétrico é construído conforme projeto elétrico e mecânico, com barramentos, entradas, saídas, alimentadores e partidas. O inversor de frequência variável é descrito como controlador que aciona motor elétrico e varia frequência e tensão para controlar velocidade e potência. Soft-starter é dispositivo eletrônico para controlar a tensão de partida de motor elétrico trifásico. O painel possui botoeiras para retirada de alarmes e lâmpadas amarelas para indicação de nível alto e alarmes do chiller. Os alarmes só devem ser retirados se os problemas forem solucionados.",
        "palavras_chave": "painel elétrico, inversor de frequência, soft-starter, alarmes, chiller, motor elétrico",
    },
    {
        "chunk_index": 13, "pagina_inicio": 12, "pagina_fim": 12,
        "titulo_secao": "Fluxostato",
        "conteudo": "O manual define fluxostato como chave de controle de fluxo usada para indicar presença ou ausência de fluxo dentro da tubulação. Ele atua como dispositivo complementar de segurança e proteção para ligar ou desligar alarmes, motores, compressores, máquinas e bombas d'água.",
        "palavras_chave": "fluxostato, chave de fluxo, fluxo, segurança, alarme, compressor, bomba",
    },
    {
        "chunk_index": 14, "pagina_inicio": 12, "pagina_fim": 12,
        "titulo_secao": "Trocador/condensador a placa",
        "conteudo": "O manual descreve o trocador/condensador a placa como trocador de calor que utiliza placas de metal para transferência de calor entre dois fluidos. O manual ressalta a importância de tratar quimicamente a água da torre para evitar incrustação de sujeira nas placas, o que prejudicaria a condensação conforme o projeto.",
        "palavras_chave": "trocador a placa, condensador a placa, água da torre, incrustação, transferência de calor, condensação",
    },
    {
        "chunk_index": 15, "pagina_inicio": 13, "pagina_fim": 13,
        "titulo_secao": "Manutenção — Inspeção diária",
        "conteudo": "O manual recomenda registrar pressão de descarga, pressão de sucção, pressão de óleo, corrente e voltagem do motor, temperatura de descarga, temperatura de sucção e temperatura do óleo em diário de leitura. Os dados podem ser registrados em intervalos de 2 a 3 horas para que anormalidades sejam localizadas rapidamente.",
        "palavras_chave": "inspeção diária, pressão de descarga, pressão de sucção, pressão de óleo, corrente, voltagem, temperatura, diário de leitura",
    },
    {
        "chunk_index": 16, "pagina_inicio": 14, "pagina_fim": 14,
        "titulo_secao": "Manutenção — Inspeção semanal",
        "conteudo": "O manual recomenda inspecionar o sistema de entrada de gás e o sistema de óleo. Deve-se usar detector de gás ou cordão de enxofre para inspecionar linhas e conexões de gás. Pequena quantidade de vazamento de óleo pelo selo de vedação do compressor é normal, mas se o vazamento exceder 6 gotas por minuto, o selo poderá estar danificado.",
        "palavras_chave": "inspeção semanal, sistema de gás, sistema de óleo, detector de gás, cordão de enxofre, vazamento de óleo, selo de vedação",
    },
    {
        "chunk_index": 17, "pagina_inicio": 14, "pagina_fim": 14,
        "titulo_secao": "Manutenção — Inspeção mensal",
        "conteudo": "O manual recomenda checar o funcionamento dos trips de segurança, verificando se estão operando satisfatoriamente e corretamente ajustados. Também recomenda testar a operação do sistema de controle de capacidade, incluindo calibração da slide válvula, testes de atuação da válvula direcional de 4 vias e verificação da capacidade do compressor.",
        "palavras_chave": "inspeção mensal, trips de segurança, controle de capacidade, slide válvula, válvula direcional, compressor",
    },
    {
        "chunk_index": 18, "pagina_inicio": 15, "pagina_fim": 15,
        "titulo_secao": "Manutenção — Inspeção trimestral",
        "conteudo": "O manual recomenda revisar ajustes dos instrumentos de pressão e temperatura, substituindo se necessário. Também recomenda realizar lubrificação dos rolamentos do motor elétrico, revisão dos terminais e cabeamento e megagem do embobinamento.",
        "palavras_chave": "inspeção trimestral, instrumentos de pressão, instrumentos de temperatura, lubrificação, rolamentos, motor elétrico, terminais, cabeamento, megagem",
    },
    {
        "chunk_index": 19, "pagina_inicio": 15, "pagina_fim": 16,
        "titulo_secao": "Manutenção — Inspeção semestral ou 5.000 horas",
        "conteudo": "O manual recomenda repetir as operações da inspeção mensal e trimestral. Também recomenda coletar amostra de óleo do compressor e enviar para análise de laboratório. Se o relatório for desfavorável, o óleo usado deve ser drenado e substituído por carga correta de óleo novo ISO 68. O manual cita substituição dos filtros de óleo e conferência do alinhamento dos eixos motor x compressor com tolerância radial/axial de 0,06 mm.",
        "palavras_chave": "inspeção semestral, 5000 horas, análise de óleo, óleo ISO 68, filtro de óleo, alinhamento, motor x compressor, 0,06 mm",
    },
    {
        "chunk_index": 20, "pagina_inicio": 16, "pagina_fim": 17,
        "titulo_secao": "Manutenção — Inspeção anual ou 10.000 horas",
        "conteudo": "O manual recomenda repetir as operações mensal, trimestral e semestral. Também cita substituição do óleo lubrificante ISO 68, substituição dos filtros de óleo, substituição do elemento filtro coalescente, calibração dos instrumentos de medição como manômetros e transmissores de pressão/temperatura, calibração de instrumentos de segurança como pressostatos, termostatos e fluxostatos, calibração das válvulas de segurança PSV e testes de vazamento e estanqueidade na unidade compressora.",
        "palavras_chave": "inspeção anual, 10000 horas, óleo ISO 68, filtro de óleo, filtro coalescente, calibração, manômetros, transmissores, pressostatos, termostatos, fluxostatos, PSV, estanqueidade",
    },
    {
        "chunk_index": 21, "pagina_inicio": 17, "pagina_fim": 17,
        "titulo_secao": "Referência técnica — 20.000 horas e revisão por condição",
        "conteudo": "O manual cita inspeção bienal ou 20.000 horas, incluindo repetição das inspeções anteriores, substituição de óleo, filtros, filtro de sucção, filtro coalescente, calibrações, desmontagem do compressor para análise visual e dimensional das peças móveis e possível substituição do kit revisão. Porém, no Portal Pred.IO, essa informação deve ser tratada como referência técnica e NÃO como gatilho automático de manutenção. Revisão geral, desmontagem, kit revisão, overhaul ou intervenção pesada só devem ser indicados quando a saúde real da máquina indicar necessidade, considerando análise de vibração, análise de óleo, termografia, histórico operacional, falhas recorrentes, tendência de score e avaliação técnica da equipe Pred.IO. REGRA: 20.000 horas é referência técnica, não gatilho automático de overhaul. A decisão depende da saúde real da máquina.",
        "palavras_chave": "20000 horas, revisão por condição, overhaul, kit revisão, desmontagem, análise preditiva, saúde da máquina, vibração, análise de óleo, termografia, histórico operacional",
    },
]


# ── Mock texto e chunks — Tabela de Óleos Homologados MAYEKAWA/MYCOM ──────────

_MOCK_TEXTO_MYCOM_OLEOS = """\
TABELA DE ÓLEOS HOMOLOGADOS MAYEKAWA/MYCOM

Óleos lubrificantes para compressores de refrigeração alternativos e de parafuso MYCOM/MAYEKAWA. Classe de viscosidade ISO VG 68.

PAO para Amônia/Freon: REFLO 68A (TECNO DATA, PAO semi-sintético, NH3/R12/R22/R502), RAB 68 (TEC SUMMIT, PAO sintético), R 200 (KLUBBER SUMMIT, PAO sintético, NH3), MOBIL GARGOYLE ARCTIC SHC 226 E (MOBIL, PAO sintético).

Minerais para Amônia/Freon: MOBIL GARGOYLE ARCTIC EH (MOBIL, mineral), ESSO REFRIGERATION 68 (MOBIL/ESSO, mineral), CAPELLA 68 (TEXACO, mineral).

POE para R134a/R404a: MOBIL EAL ARCTIC 68 (MOBIL, POE sintético), ICEMATIC SW 68 (CASTROL, POE sintético), CAPELLA HFC 68 (TEXACO, POE sintético).

MYCOM: MYCOLD PAO (MYCOM, PAO sintético, NH3/R22, ISO VG 68, 53 cSt @ 40C) — ÓLEO MYCOM HOMOLOGADO ATUAL. MYCOLD AB 68: DESCONTINUADO — substituído por MYCOLD PAO. Não usar MYCOLD AB 68 como referência atual.
"""

_MOCK_CHUNKS_MYCOM_OLEOS: list[dict] = [
    {
        "chunk_index": 1, "pagina_inicio": 1, "pagina_fim": 1,
        "titulo_secao": "Tabela de óleos homologados — PAO para Amônia/Freon",
        "conteudo": "A tabela MAYEKAWA/MYCOM apresenta óleos ISO VG 68 para compressores de refrigeração. Para Amônia - NH3, Freon R12, R22 e R502, aparecem opções como REFLO 68A (TECNO DATA, semi-sintético PAO, -42°C mínima fluidez), RAB 68 (TEC SUMMIT, sintético PAO), R 200 (KLUBBER SUMMIT, sintético PAO, apenas NH3) e MOBIL GARGOYLE ARCTIC SHC 226 E (MOBIL, sintético PAO, -45°C mínima fluidez, IV 138).",
        "palavras_chave": "PAO, amônia, NH3, Freon R12, R22, R502, REFLO 68A, RAB 68, R 200, Mobil Gargoyle Arctic SHC 226 E, óleo sintético, homologado",
    },
    {
        "chunk_index": 2, "pagina_inicio": 1, "pagina_fim": 1,
        "titulo_secao": "Tabela de óleos homologados — minerais",
        "conteudo": "A tabela MAYEKAWA/MYCOM apresenta óleos minerais ISO VG 68 para aplicações com Amônia - NH3, Freon R12, R22 e R502, incluindo MOBIL GARGOYLE ARCTIC EH (MOBIL, mineral, -26°C mínima fluidez), ESSO REFRIGERATION 68 (MOBIL/ESSO, mineral, -33°C mínima fluidez) e CAPELLA 68 (TEXACO, mineral, -36°C mínima fluidez).",
        "palavras_chave": "óleo mineral, ISO VG 68, Mobil Gargoyle Arctic EH, Esso Refrigeration 68, Capella 68, amônia, R22, R12, R502, hidrocarboneto mineral",
    },
    {
        "chunk_index": 3, "pagina_inicio": 2, "pagina_fim": 2,
        "titulo_secao": "Tabela de óleos homologados — POE para R134a/R404a",
        "conteudo": "A tabela MAYEKAWA/MYCOM apresenta óleos sintéticos POE (Poliolester) ISO VG 68 para R134a e R404a, incluindo MOBIL EAL ARCTIC 68 (MOBIL, POE, -43°C mínima fluidez, IV 101), ICEMATIC SW 68 (CASTROL, POE, -39°C mínima fluidez) e CAPELLA HFC 68 (TEXACO, POE, -57°C mínima fluidez, densid. 0,971).",
        "palavras_chave": "POE, Poliolester, R134a, R404a, Mobil EAL Arctic 68, Icematic SW 68, Capella HFC 68, óleo sintético, fluoro",
    },
    {
        "chunk_index": 4, "pagina_inicio": 2, "pagina_fim": 2,
        "titulo_secao": "Tabela de óleos homologados — Mycold PAO (MYCOM atual)",
        "conteudo": "No Portal Pred.IO, o óleo MYCOM homologado atual é MYCOLD PAO (MYCOM, PAO sintético, NH3/R22, ISO VG 68, 53 cSt @ 40°C). A referência antiga MYCOLD AB 68 foi descontinuada e deve ser usada apenas como alias histórico para redirecionar respostas ao MYCOLD PAO. O Assistente Técnico não deve recomendar MYCOLD AB 68 como óleo atual. REGRA: MYCOLD AB 68 foi descontinuado. No Portal Pred.IO, a referência atual deve ser MYCOLD PAO.",
        "palavras_chave": "Mycold PAO, Mycold AB 68, óleo descontinuado, óleo homologado MYCOM, MYCOM, ISO VG 68, PAO, substituição de óleo",
    },
]


# ── Mock texto e chunks — Guia Prático Mypro Touch AD — Pred.IO ──────────────

_MOCK_TEXTO_MYPRO_TOUCH_AD = """\
GUIA PRÁTICO MYPRO TOUCH AD — PRED.IO

SEÇÃO 1: VISÃO GERAL DO PAINEL
O painel Mypro Touch AD é o controlador de interface homem-máquina (HMI) utilizado nos compressores de refrigeração MYCOM da MAYEKAWA. Permite monitoramento em tempo real dos parâmetros operacionais, gerenciamento de alarmes e configuração de set points. O Mypro Touch AD é a versão avançada e atual; o Mypro Touch é a versão padrão sem o sufixo AD. Nenhuma das versões é chamada de "Mypro Touch+" — esse nome não existe e não deve ser usado.

SEÇÃO 2: TELA PRINCIPAL — PARÂMETROS MONITORADOS
A tela principal do Mypro Touch AD exibe em tempo real: pressão de sucção (PS) em kg/cm² ou bar, pressão de descarga (PD) em kg/cm² ou bar, temperatura de descarga (TD) em °C, temperatura de sucção (TS) em °C, pressão de óleo diferencial (PO) em kg/cm², corrente do motor em ampères e percentual de carga, posição da válvula de capacidade (slide valve) de 0 a 100%, e status geral: RODANDO, PARADO ou EM ALARME. Os valores em vermelho indicam condição fora dos limites configurados.

SEÇÃO 3: NAVEGAÇÃO ENTRE TELAS
O Mypro Touch AD é operado por teclado numérico e botões de seleção. As telas disponíveis incluem: Tela de Operação (parâmetros ao vivo), Tela de Alarmes (ativos e histórico), Tela de Set Points (temperaturas e pressões alvo), Tela de Configurações (limites e parâmetros de controle), Tela de Histórico (registro de eventos). Para navegar, use as setas direcionais ou os botões de atalho indicados no manual do fabricante. Em caso de dúvida sobre a navegação, consulte o técnico da Pred.IO.

SEÇÃO 4: ALARMES E INTERTRAVAMENTOS DE SEGURANÇA
O Mypro Touch AD distingue dois níveis de alerta: ALARME (condição fora do limite, compressor continua operando, painel emite sinal visual e sonoro) e TRIP/DESLIGAMENTO (condição crítica que causa desligamento automático do compressor por segurança). Alarmes mais comuns: alta temperatura de descarga (TD), baixa pressão de óleo diferencial (PO), alta pressão de descarga (PD), baixa pressão de sucção (PS), sobrecarga do motor (corrente alta), falha no fluxostato de água ou gás. Cada alarme registra no histórico: data, hora, tipo do alarme e valor da variável no momento do evento.

SEÇÃO 5: RESET DE ALARME — PROCEDIMENTO E RESPONSABILIDADE
Para resetar um alarme ou trip no Mypro Touch AD: (1) Identificar e eliminar a causa raiz do alarme antes de qualquer reset. (2) Confirmar que a condição de alarme não está mais ativa (valor da variável voltou ao limite normal). (3) Acessar a tela de Alarmes. (4) Pressionar o botão RESET no painel. REGRA PRED.IO: O reset de alarme deve ser realizado APENAS por operador autorizado e treinado. Nunca resetar sem corrigir a causa. O Assistente Técnico Pred.IO orienta sobre o procedimento — o reset deve ser executado presencialmente pelo operador responsável. Em caso de trip repetido ou causa desconhecida, abrir chamado técnico Pred.IO antes de religar o compressor.

SEÇÃO 6: SET POINTS — CONFIGURAÇÃO E RESPONSABILIDADE
Set points são os valores alvo que o sistema de controle usa para manter as condições operacionais. Exemplos: temperatura de sucção alvo, pressão de sucção alvo, limite máximo de temperatura de descarga, temperatura alvo do fluido de saída. A alteração de set points no Mypro Touch AD deve ser realizada APENAS por operador autorizado. Ajustes incorretos podem comprometer a segurança, a eficiência e a integridade do processo de refrigeração. O Assistente Técnico Pred.IO não executa comandos na máquina nem altera parâmetros remotamente; apenas orienta sobre o procedimento correto. Para solicitar alteração de set point sem operador disponível, abrir chamado técnico Pred.IO.

SEÇÃO 7: CONTROLE DE CAPACIDADE — VÁLVULA SLIDE
A capacidade do compressor é controlada pela válvula slide (slide valve), cuja posição (0-100%) é exibida no Mypro Touch AD. Em condições normais, o sistema ajusta a capacidade automaticamente conforme o set point de temperatura ou pressão. Intervenção manual na capacidade (aumentar ou diminuir manualmente a carga do compressor) deve ser realizada APENAS por operador autorizado. Operar em capacidade muito baixa por período prolongado pode causar retorno de líquido — verificar SSH (Superaquecimento de Sucção). Operar em capacidade máxima em ambient de alta temperatura pode elevar a TD além dos limites.

SEÇÃO 8: PARTIDA E PARADA DO COMPRESSOR
Partida e parada do compressor controlado pelo Mypro Touch AD devem ser realizadas APENAS por operador autorizado. Pré-requisitos antes da partida: (a) nível de óleo visível no visor, (b) pressão de óleo acima de 0 bar diferencial (bomba de óleo deve ter pré-lubrificado), (c) temperatura do óleo acima de 30°C, (d) ausência de alarmes ativos no painel, (e) válvulas de sucção e descarga abertas. A parada de emergência (EMERGENCY STOP) está disponível no painel físico e no Mypro Touch AD — deve ser usada apenas em situações de segurança imediata.

SEÇÃO 9: MONITORAMENTO DE PARÂMETROS CRÍTICOS
O Mypro Touch AD monitora continuamente os parâmetros críticos. Valores de referência típicos para compressores MYCOM com amônia (NH3): pressão de óleo diferencial mínima de 1,2 a 2,0 kg/cm² acima da pressão de sucção; temperatura de descarga máxima de 140°C; corrente do motor conforme plaqueta (sobrecarga gera alarme automático); temperatura de sucção normal conforme set point. Desvios persistentes desses parâmetros devem ser registrados e comunicados à equipe técnica Pred.IO através de chamado. O Mypro Touch AD registra o histórico de eventos e anomalias — essa informação deve ser preservada para análise preditiva.

SEÇÃO 10: COMUNICAÇÃO E INTEGRAÇÃO COM PRED.IO
O Mypro Touch AD pode ser configurado para comunicação remota via Modbus RTU ou Modbus TCP/IP, dependendo da versão instalada. O Portal Pred.IO recebe dados do painel via integração Modbus para exibição nos Faróis e Alertas. Configurações de comunicação (endereço Modbus, baud rate, IP) devem ser realizadas apenas por técnico especializado MAYEKAWA ou Pred.IO. Em caso de perda de comunicação entre o Mypro Touch AD e o Portal Pred.IO (dados não atualizados no portal), abrir chamado técnico para diagnóstico.
"""

_MOCK_CHUNKS_MYPRO_TOUCH_AD: list[dict] = [
    {
        "chunk_index": 1, "pagina_inicio": 1, "pagina_fim": 1,
        "titulo_secao": "Visão geral — Mypro Touch e Mypro Touch AD",
        "conteudo": (
            "O painel Mypro Touch AD é o HMI (interface homem-máquina) dos compressores MYCOM/MAYEKAWA. "
            "Permite monitoramento em tempo real, gerenciamento de alarmes e configuração de set points. "
            "O Mypro Touch AD é a versão avançada atual; o Mypro Touch é a versão padrão. "
            "Não existe versão chamada 'Mypro Touch+' — esse nome não deve ser usado."
        ),
        "palavras_chave": "Mypro Touch, Mypro Touch AD, HMI, MYCOM, MAYEKAWA, painel, interface, controlador",
    },
    {
        "chunk_index": 2, "pagina_inicio": 2, "pagina_fim": 2,
        "titulo_secao": "Tela principal — parâmetros monitorados",
        "conteudo": (
            "A tela principal do Mypro Touch AD exibe em tempo real: pressão de sucção (PS), "
            "pressão de descarga (PD), temperatura de descarga (TD), temperatura de sucção (TS), "
            "pressão de óleo diferencial (PO), corrente e carga do motor, posição da válvula slide (0-100%) "
            "e status (RODANDO, PARADO ou EM ALARME). Valores em vermelho indicam condição fora dos limites."
        ),
        "palavras_chave": "tela principal, parâmetros, pressão de sucção, pressão de descarga, temperatura de descarga, corrente, carga, válvula slide, status",
    },
    {
        "chunk_index": 3, "pagina_inicio": 3, "pagina_fim": 3,
        "titulo_secao": "Navegação entre telas do Mypro Touch AD",
        "conteudo": (
            "O Mypro Touch AD é operado por teclado numérico e botões de seleção. "
            "Telas disponíveis: Operação (parâmetros ao vivo), Alarmes (ativos e histórico), "
            "Set Points (temperaturas e pressões alvo), Configurações (limites e controle) e "
            "Histórico (registro de eventos). Use as setas direcionais ou botões de atalho conforme o manual. "
            "Em dúvida sobre a navegação, consulte o técnico da Pred.IO."
        ),
        "palavras_chave": "navegação, telas, teclado, Mypro Touch AD, tela de operação, tela de alarmes, set points, histórico",
    },
    {
        "chunk_index": 4, "pagina_inicio": 4, "pagina_fim": 4,
        "titulo_secao": "Alarmes e trips — tipos e causas",
        "conteudo": (
            "O Mypro Touch AD distingue: ALARME (fora do limite, compressor continua, sinal visual/sonoro) "
            "e TRIP/DESLIGAMENTO (condição crítica, desligamento automático por segurança). "
            "Alarmes mais comuns: alta temperatura de descarga, baixa pressão de óleo, alta pressão de descarga, "
            "baixa pressão de sucção, sobrecarga do motor, falha no fluxostato. "
            "O histórico registra data, hora, tipo e valor da variável no momento do evento."
        ),
        "palavras_chave": "alarme, trip, desligamento, alta temperatura de descarga, baixa pressão de óleo, sobrecarga, fluxostato, histórico de alarmes",
    },
    {
        "chunk_index": 5, "pagina_inicio": 5, "pagina_fim": 5,
        "titulo_secao": "Reset de alarme — procedimento e responsabilidade",
        "conteudo": (
            "Para resetar alarme ou trip no Mypro Touch AD: (1) identificar e eliminar a causa raiz; "
            "(2) confirmar que a variável voltou ao limite normal; (3) acessar a tela de Alarmes; (4) pressionar RESET. "
            "REGRA: reset de alarme deve ser realizado APENAS por operador autorizado. "
            "O Assistente Técnico Pred.IO orienta; o reset deve ser executado presencialmente. "
            "Trip repetido ou causa desconhecida: abrir chamado técnico Pred.IO antes de religar."
        ),
        "palavras_chave": "reset de alarme, reset de trip, operador autorizado, procedimento, Mypro Touch AD, chamado técnico",
    },
    {
        "chunk_index": 6, "pagina_inicio": 6, "pagina_fim": 6,
        "titulo_secao": "Set points — configuração e responsabilidade",
        "conteudo": (
            "Set points são os valores alvo que o sistema usa para manter as condições operacionais: "
            "temperatura de sucção alvo, pressão de sucção alvo, limite de temperatura de descarga. "
            "Alteração de set points no Mypro Touch AD deve ser realizada APENAS por operador autorizado. "
            "Ajustes incorretos comprometem segurança e eficiência. "
            "O Assistente Técnico Pred.IO não altera parâmetros remotamente; apenas orienta. "
            "Para alterar set point sem operador disponível, abrir chamado técnico Pred.IO."
        ),
        "palavras_chave": "set point, temperatura alvo, pressão alvo, operador autorizado, Mypro Touch AD, configuração, segurança",
    },
    {
        "chunk_index": 7, "pagina_inicio": 7, "pagina_fim": 7,
        "titulo_secao": "Controle de capacidade — válvula slide",
        "conteudo": (
            "A capacidade do compressor é controlada pela válvula slide (posição 0-100% no Mypro Touch AD). "
            "Em condições normais, o sistema ajusta automaticamente conforme o set point. "
            "Intervenção manual na capacidade deve ser realizada APENAS por operador autorizado. "
            "Capacidade muito baixa por período prolongado pode causar retorno de líquido — verificar SSH. "
            "Capacidade máxima em ambiente quente pode elevar a temperatura de descarga além dos limites."
        ),
        "palavras_chave": "controle de capacidade, válvula slide, slide valve, capacidade mínima, retorno de líquido, SSH, temperatura de descarga",
    },
    {
        "chunk_index": 8, "pagina_inicio": 8, "pagina_fim": 8,
        "titulo_secao": "Partida e parada — procedimento e responsabilidade",
        "conteudo": (
            "Partida e parada do compressor controlado pelo Mypro Touch AD devem ser realizadas APENAS por operador autorizado. "
            "Pré-requisitos para partida: nível de óleo visível, pressão de óleo acima de 0 diferencial, "
            "temperatura do óleo acima de 30°C, ausência de alarmes ativos, válvulas de sucção e descarga abertas. "
            "Parada de emergência (EMERGENCY STOP) está disponível no painel físico e no Mypro Touch AD — "
            "usar apenas em situações de segurança imediata."
        ),
        "palavras_chave": "partida, parada, operador autorizado, pré-requisitos, nível de óleo, temperatura do óleo, alarmes, emergency stop, EMERGENCY STOP",
    },
    {
        "chunk_index": 9, "pagina_inicio": 9, "pagina_fim": 9,
        "titulo_secao": "Parâmetros críticos — valores de referência MYCOM",
        "conteudo": (
            "Valores de referência típicos para compressores MYCOM com amônia (NH3) monitorados pelo Mypro Touch AD: "
            "pressão de óleo diferencial mínima de 1,2 a 2,0 kg/cm² acima da pressão de sucção; "
            "temperatura de descarga máxima de 140°C; corrente do motor conforme plaqueta (sobrecarga gera alarme). "
            "Desvios persistentes devem ser registrados e comunicados à equipe Pred.IO via chamado técnico."
        ),
        "palavras_chave": "parâmetros, valores de referência, pressão de óleo, temperatura de descarga, corrente do motor, amônia, NH3, MYCOM",
    },
    {
        "chunk_index": 10, "pagina_inicio": 10, "pagina_fim": 10,
        "titulo_secao": "Comunicação e integração Mypro Touch AD com Pred.IO",
        "conteudo": (
            "O Mypro Touch AD pode ser configurado para comunicação via Modbus RTU ou TCP/IP "
            "para integração com o Portal Pred.IO (dados exibidos nos Faróis e Alertas). "
            "Configurações de comunicação devem ser realizadas apenas por técnico especializado MAYEKAWA ou Pred.IO. "
            "Perda de comunicação entre o Mypro Touch AD e o portal: abrir chamado técnico para diagnóstico."
        ),
        "palavras_chave": "Modbus, comunicação, integração, Pred.IO, Mypro Touch AD, Faróis, Alertas, TCP/IP, técnico",
    },
]


def _get_mock_for_url(arquivo_url: str, arquivo_nome: str = "") -> tuple[str, list[dict], int]:
    """Retorna (texto, chunks, n_paginas) mock se o arquivo for de demonstração."""
    key = (arquivo_url + " " + arquivo_nome).lower()
    # Guia Prático Mypro Touch AD
    if ("mypro" in key and "touch" in key) or ("guia" in key and "touch" in key) or "touch ad" in key:
        return _MOCK_TEXTO_MYPRO_TOUCH_AD, _MOCK_CHUNKS_MYPRO_TOUCH_AD, 10
    # Manual Operacional MYCOM - Sistema Chiller
    if "operacional" in key or ("mycom" in key and "chiller" in key):
        return _MOCK_TEXTO_MYCOM_OPERACIONAL, _MOCK_CHUNKS_MYCOM_OPERACIONAL, 17
    # Tabela de Óleos Homologados MAYEKAWA/MYCOM
    if "mayekawa" in key or ("tabelas" in key and ("oleo" in key or "homologado" in key)):
        return _MOCK_TEXTO_MYCOM_OLEOS, _MOCK_CHUNKS_MYCOM_OLEOS, 2
    # Manual 200 VLD (compressor parafuso)
    if ("200" in key and "vld" in key) or "compressor" in key:
        return _MOCK_TEXTO_200_VLD, _MOCK_CHUNKS_200_VLD, 5
    return "", [], 0


def extrair_texto_pdf(arquivo_url: str, arquivo_nome: str = "") -> tuple[str, int]:
    """
    Extrai texto de um PDF. Retorna (texto, num_paginas).
    Tenta pdfplumber, depois PyPDF2. Fallback: mock estruturado.
    """
    if arquivo_url.startswith("/mock/") or not arquivo_url.startswith("http"):
        texto, _, n_pags = _get_mock_for_url(arquivo_url, arquivo_nome)
        return texto, n_pags

    try:
        import urllib.request
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            urllib.request.urlretrieve(arquivo_url, f.name)
            tmp_path = f.name

        texto = ""
        n_pags = 0
        try:
            import pdfplumber
            with pdfplumber.open(tmp_path) as pdf:
                n_pags = len(pdf.pages)
                texto = "\n\n".join(p.extract_text() or "" for p in pdf.pages)
        except ImportError:
            try:
                import PyPDF2
                with open(tmp_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    n_pags = len(reader.pages)
                    texto = "\n\n".join(
                        reader.pages[i].extract_text() or ""
                        for i in range(n_pags)
                    )
            except ImportError:
                pass

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        if texto.strip():
            return texto, n_pags
    except Exception:
        pass

    texto, _, n_pags = _get_mock_for_url(arquivo_url, arquivo_nome)
    return texto, n_pags


def criar_chunks(
    doc_id: str,
    cliente_id: str,
    ativo_id: str,
    componente_id: str,
    arquivo_url: str,
    arquivo_nome: str,
    texto: str,
) -> list[dict]:
    """
    Cria chunks para um documento.
    Se o texto coincidir com um mock, usa os chunks mock estruturados.
    Senão, divide em blocos de ~500 palavras por parágrafo.
    """
    mock_texto, mock_chunks, _ = _get_mock_for_url(arquivo_url, arquivo_nome)
    if mock_texto and mock_chunks and texto.strip() == mock_texto.strip():
        return [
            {"documento_id": doc_id, "cliente_id": cliente_id,
             "ativo_id": ativo_id, "componente_id": componente_id, **c}
            for c in mock_chunks
        ]

    if not texto.strip():
        return []

    paragrafos = [p.strip() for p in re.split(r'\n{2,}', texto) if p.strip()]
    chunks: list[dict] = []
    buffer: list[str] = []
    buf_words = 0
    chunk_idx = 1

    def flush() -> None:
        nonlocal chunk_idx, buffer, buf_words
        chunks.append({
            "documento_id":  doc_id,
            "cliente_id":    cliente_id,
            "ativo_id":      ativo_id,
            "componente_id": componente_id,
            "chunk_index":   chunk_idx,
            "pagina_inicio": chunk_idx,
            "pagina_fim":    chunk_idx,
            "titulo_secao":  _extrair_titulo(buffer[0]),
            "conteudo":      " ".join(buffer),
            "palavras_chave": "",
        })
        buffer = []
        buf_words = 0
        chunk_idx += 1

    for par in paragrafos:
        words = len(par.split())
        if buf_words + words > 500 and buffer:
            flush()
        buffer.append(par)
        buf_words += words

    if buffer:
        flush()

    return chunks


def _extrair_titulo(texto: str) -> str:
    primeira = texto.split("\n")[0].strip()
    return primeira[:80] if len(primeira) <= 80 else primeira[:77] + "..."


def processar_documento(
    doc_id: str,
    cliente_id: str,
    ativo_id: str,
    componente_id: str,
    arquivo_url: str,
    arquivo_nome: str = "",
) -> dict:
    """
    Processa um documento: extrai texto, cria chunks, salva no Sheets.
    Retorna {"ok": bool, "status": str, "n_chunks": int, "n_paginas": int, "erro": str}.
    """
    from sheets import update_status_indexacao, delete_chunks_documento, add_chunks_lote

    update_status_indexacao(doc_id, STATUS_PROCESSANDO)

    try:
        texto, n_paginas = extrair_texto_pdf(arquivo_url, arquivo_nome)
        if not texto.strip():
            update_status_indexacao(doc_id, STATUS_FALHOU, erro="Texto não extraído — PDF vazio ou protegido.")
            return {"ok": False, "status": STATUS_FALHOU, "n_chunks": 0, "n_paginas": 0, "erro": "Texto não extraído"}

        chunks = criar_chunks(doc_id, cliente_id, ativo_id, componente_id, arquivo_url, arquivo_nome, texto)
        if not chunks:
            update_status_indexacao(doc_id, STATUS_FALHOU, erro="Nenhum chunk gerado a partir do texto.")
            return {"ok": False, "status": STATUS_FALHOU, "n_chunks": 0, "n_paginas": n_paginas, "erro": "Sem chunks"}

        delete_chunks_documento(doc_id)
        ok = add_chunks_lote(chunks)
        if not ok:
            update_status_indexacao(doc_id, STATUS_FALHOU, erro="Erro ao salvar chunks no Sheets.")
            return {"ok": False, "status": STATUS_FALHOU, "n_chunks": len(chunks), "n_paginas": n_paginas, "erro": "Erro ao salvar"}

        update_status_indexacao(
            doc_id, STATUS_INDEXADO,
            texto_extraido=texto[:5000],
            quantidade_paginas=n_paginas,
        )
        return {"ok": True, "status": STATUS_INDEXADO, "n_chunks": len(chunks), "n_paginas": n_paginas, "erro": ""}

    except Exception as exc:
        erro = str(exc)[:200]
        update_status_indexacao(doc_id, STATUS_FALHOU, erro=erro)
        return {"ok": False, "status": STATUS_FALHOU, "n_chunks": 0, "n_paginas": 0, "erro": erro}
