"""Sistema GUT (Gravidade x Urgência x Tendência) — priorização técnica.

GUT é uma ferramenta de priorização, não uma decisão automática. Nenhuma nota
GUT, por maior que seja, autoriza parada de máquina, overhaul ou troca de
rolamento automaticamente — essas decisões dependem sempre de análise
preditiva e avaliação técnica da equipe Pred.IO (ver GUT_DISCLAIMER).
"""

GUT_DISCLAIMER = (
    "GUT é uma ferramenta de priorização e não substitui a avaliação técnica "
    "da equipe Pred.IO."
)

# (score_min, score_max, prioridade) — cobre todo o intervalo 1..125
GUT_FAIXAS = [
    (1,  20,  "Baixa"),
    (21, 50,  "Moderada"),
    (51, 80,  "Alta"),
    (81, 125, "Crítica"),
]

GUT_PRIORIDADES = [p for _, _, p in GUT_FAIXAS]


def calculate_gut(gravidade, urgencia, tendencia) -> dict | None:
    """GUT = Gravidade x Urgência x Tendência — cada nota de 1 a 5.

    Retorna {"score": int, "prioridade": str} ou None se qualquer nota
    estiver vazia/ausente ou fora do intervalo 1-5 (não calcula sem os 3).
    """
    if gravidade in (None, "") or urgencia in (None, "") or tendencia in (None, ""):
        return None
    try:
        g, u, t = int(gravidade), int(urgencia), int(tendencia)
    except (TypeError, ValueError):
        return None
    if not (1 <= g <= 5 and 1 <= u <= 5 and 1 <= t <= 5):
        return None

    score = g * u * t
    prioridade = next(p for lo, hi, p in GUT_FAIXAS if lo <= score <= hi)
    return {"score": score, "prioridade": prioridade}


def gut_acao_recomendada(prioridade: str) -> str:
    """Texto de ação recomendada por faixa — nunca prescreve intervenção
    automática (overhaul/troca/parada), só orienta prazo de análise técnica."""
    return {
        "Crítica":  "Prioridade máxima — solicitar avaliação técnica da equipe Pred.IO o quanto antes.",
        "Alta":     "Agendar avaliação técnica em curto prazo.",
        "Moderada": "Acompanhar e planejar intervenção técnica dentro do prazo normal.",
        "Baixa":    "Manter monitoramento de rotina.",
    }.get(prioridade, "Sem prioridade GUT definida.")
