"""Comparativo "O que mudou desde a última reunião?" — Pred.IO.

Reaproveita a coleta de dados já existente em `executive_summary.py` (mesmas
fontes, mesmo isolamento por cliente_id/staff/Status Publicado) chamada DUAS
VEZES — uma por período — em vez de duplicar lógica de coleta. Eventos de
"melhorou"/"piorou" vêm principalmente da timeline (`ReportTimeline`,
`status_alterado`/`alerta_gerado`/`alerta_resolvido` — ver `sheets.py`), que
já é escrita no momento em que a mudança acontece; isso evita depender de um
histórico completo de status/GUT por ativo, que não existe.

SEGURANÇA: mesmo padrão do resto do projeto — cliente_id sempre do chamador
(sessão do cliente ou seleção do staff), nunca de input livre; relatórios só
entram se Status=="Publicado" (via _coletar_dados -> get_technical_reports).

LIMITAÇÕES DE DADOS ACEITAS (ver docs/PREDIO_TIMELINE_COMPARATIVO_REUNIOES.md):
- GUT/score de saúde não têm histórico completo — só o que os snapshots
  (`sheets.snapshot_cliente`) capturaram a partir de quando essa etapa foi
  implementada. Sem snapshot anterior, "antes" fica em branco (nunca um
  valor inventado).
- Manutenção por horímetro não é retroativa (sem log de leitura histórica).
"""
from __future__ import annotations

import datetime as _dt

import pandas as pd

import sheets
from executive_summary import _coletar_dados, _status_ativo_norm

_FAIXA_RANK = {"Bom": 0, "Atenção": 1, "Crítico": 2, "Urgente": 3}


def _parse_data_br(s: str) -> _dt.date | None:
    try:
        return _dt.datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except Exception:
        return None


def resolver_periodo_comparativo(
    cliente_id: str,
    usar_ultima_reuniao: bool = True,
    periodo_atual_ini: _dt.date | None = None,
    periodo_atual_fim: _dt.date | None = None,
    periodo_anterior_ini: _dt.date | None = None,
    periodo_anterior_fim: _dt.date | None = None,
) -> dict:
    """Resolve os dois períodos a comparar.

    Se usar_ultima_reuniao=True e existir reunião registrada: período
    ANTERIOR = o período que foi analisado na própria última reunião;
    período ATUAL = do dia seguinte até hoje.

    Senão, usa os 4 parâmetros manuais — os que faltarem caem num padrão de
    30 dias vs os 30 dias anteriores.

    Retorna: {"atual": (ini,fim), "anterior": (ini,fim),
              "usando_reuniao": bool, "reuniao": dict|None}
    """
    reuniao = sheets.get_last_meeting(cliente_id) if usar_ultima_reuniao else None
    if reuniao:
        anterior_ini = _parse_data_br(reuniao["periodo_inicio"])
        anterior_fim = _parse_data_br(reuniao["periodo_fim"])
        if anterior_ini and anterior_fim:
            atual_ini = anterior_fim + _dt.timedelta(days=1)
            atual_fim = _dt.date.today()
            if atual_fim < atual_ini:
                atual_fim = atual_ini
            return {
                "atual": (atual_ini, atual_fim), "anterior": (anterior_ini, anterior_fim),
                "usando_reuniao": True, "reuniao": reuniao,
            }

    hoje = _dt.date.today()
    periodo_atual_fim    = periodo_atual_fim or hoje
    periodo_atual_ini    = periodo_atual_ini or (periodo_atual_fim - _dt.timedelta(days=30))
    periodo_anterior_fim = periodo_anterior_fim or (periodo_atual_ini - _dt.timedelta(days=1))
    periodo_anterior_ini = periodo_anterior_ini or (periodo_anterior_fim - _dt.timedelta(days=30))
    return {
        "atual": (periodo_atual_ini, periodo_atual_fim),
        "anterior": (periodo_anterior_ini, periodo_anterior_fim),
        "usando_reuniao": False, "reuniao": None,
    }


def _eventos_timeline_periodo(cliente_id: str, ini: _dt.date, fim: _dt.date,
                              ativo_id: str = "", staff: bool = True) -> pd.DataFrame:
    df = sheets.get_report_timeline_events(ativo_id=ativo_id, cliente_id=cliente_id, staff=staff)
    if df.empty:
        return df
    df = df.copy()
    df["_dt"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    return df[(df["_dt"].dt.date >= ini) & (df["_dt"].dt.date <= fim)]


def gerar_comparativo(
    cliente_id: str, periodo_atual: tuple, periodo_anterior: tuple,
    ativo_id: str = "", modo: str = "cliente",
) -> dict:
    """Gera o comparativo entre dois períodos para um cliente (e,
    opcionalmente, um ativo específico). Retorna dict com ok, melhorou,
    piorou, novidades, pendencias, pontos_gerencia, charts, tem_snapshot."""
    if not cliente_id:
        return {"ok": False, "erro": "cliente_id obrigatório."}

    ini_a, fim_a = periodo_atual
    ini_p, fim_p = periodo_anterior
    incluir = {"relatorios": True, "manutencoes": True, "alertas": True,
              "chamados": True, "gut": True}
    staff_mode = modo == "interno_predio"

    dados_atual    = _coletar_dados(cliente_id, ativo_id, ini_a, fim_a, modo, incluir)
    dados_anterior = _coletar_dados(cliente_id, ativo_id, ini_p, fim_p, modo, incluir)

    snap_anterior  = sheets.get_last_snapshot(cliente_id)
    tem_snapshot   = snap_anterior is not None

    tl_atual = _eventos_timeline_periodo(cliente_id, ini_a, fim_a, ativo_id, staff=staff_mode)

    melhorou: list = []
    piorou: list = []
    novidades: list = []
    pendencias: list = []
    # (rank, texto) — rank menor = mais importante; ordenado e cortado em 7
    # ao final. 1=piora crítica, 2=GUT crítico/alto, 3=manutenção vencida,
    # 4=alerta crítico, 5=recomendação relevante, 6=melhoria importante.
    pontos_rank: list = []

    # ── status_alterado (score de saúde) — melhorou/piorou por ativo ────────
    if not tl_atual.empty:
        for _, ev in tl_atual[tl_atual["Tipo"] == "status_alterado"].iterrows():
            titulo = str(ev.get("Titulo", ""))
            if "→" not in titulo:
                continue
            nome_parte, _, resto = titulo.partition(":")
            antiga, _, nova = resto.strip().partition("→")
            antiga, nova = antiga.strip(), nova.strip()
            if antiga not in _FAIXA_RANK or nova not in _FAIXA_RANK:
                continue
            texto = f"{nome_parte.strip()} passou de {antiga} para {nova}."
            if _FAIXA_RANK[nova] < _FAIXA_RANK[antiga]:
                melhorou.append(texto)
                pontos_rank.append((6, texto))
            elif _FAIXA_RANK[nova] > _FAIXA_RANK[antiga]:
                piorou.append(texto)
                rank = 1 if nova in ("Crítico", "Urgente") else 3
                pontos_rank.append((rank, texto))

        # ── alertas gerados/resolvidos ───────────────────────────────────────
        for _, ev in tl_atual[tl_atual["Tipo"] == "alerta_resolvido"].iterrows():
            texto = f"Alerta resolvido: {ev.get('Titulo', '')}."
            melhorou.append(texto)
        for _, ev in tl_atual[tl_atual["Tipo"] == "alerta_gerado"].iterrows():
            texto = f"Novo alerta: {ev.get('Titulo', '')}."
            piorou.append(texto)
            pontos_rank.append((4, texto))

        # ── GUT alterado — sinal de mudança, vai pra novidades (não temos
        #    delta limpo old->new pra classificar como melhora/piora) ────────
        for _, ev in tl_atual[tl_atual["Tipo"] == "gut_alterado"].iterrows():
            texto = str(ev.get("Titulo", "GUT alterado"))
            novidades.append(texto)
            pontos_rank.append((2, texto))

        # ── recomendação técnica nova ────────────────────────────────────────
        n_recom = len(tl_atual[tl_atual["Tipo"] == "recomendacao_tecnica"])
        if n_recom:
            texto = f"{n_recom} nova(s) recomendação(ões) por condição."
            novidades.append(texto)
            pontos_rank.append((5, texto))

    # ── Relatórios publicados no período atual ──────────────────────────────
    df_rel_atual = dados_atual.get("relatorios")
    if df_rel_atual is not None and not df_rel_atual.empty:
        n_rel = len(df_rel_atual)
        novidades.append(f"{n_rel} relatório(s) publicado(s) no período.")
        if "Severidade" in df_rel_atual.columns:
            criticos = df_rel_atual[df_rel_atual["Severidade"].astype(str).str.strip().isin(["Crítico", "Urgente"])]
            for _, r in criticos.iterrows():
                texto = f"Relatório crítico: {str(r.get('Titulo', '')).strip()}."
                piorou.append(texto)
                pontos_rank.append((1, texto))

    # ── Chamados novos no período atual ──────────────────────────────────────
    df_cham_atual = dados_atual.get("chamados")
    if df_cham_atual is not None and not df_cham_atual.empty:
        novidades.append(f"{len(df_cham_atual)} novo(s) chamado(s) no período.")

    # ── Manutenções concluídas no período atual ──────────────────────────────
    df_mex_atual = dados_atual.get("manutencoes_executadas")
    if df_mex_atual is not None and not df_mex_atual.empty:
        melhorou.append(f"{len(df_mex_atual)} manutenção(ões) concluída(s) no período.")

    # ── Manutenção vencida agora × vencida como estava no período anterior ──
    # O campo Status de MaintenanceTasks é um texto gravado na criação/última
    # edição — não é recalculado com o tempo. "Vencida" de verdade só existe
    # via calc_task_status() (dinâmico), por isso não usamos
    # dados_atual["manutencoes_pendentes"]["Status"] aqui (ele ficaria sempre
    # "Em dia" mesmo pra tarefa realmente vencida há semanas).
    try:
        df_tasks = sheets.get_maintenance_tasks(client_id=cliente_id, ativo_id=ativo_id, staff=staff_mode)
        if not df_tasks.empty and "Status" in df_tasks.columns:
            df_tasks = df_tasks[~df_tasks["Status"].astype(str).str.lower().str.contains("conclu|arquiv", na=False)]
        if not df_tasks.empty:
            novas_vencidas = 0
            vencidas_agora = 0
            for _, t in df_tasks.iterrows():
                task_dict = t.to_dict()
                status_antes = sheets.calc_task_status(task_dict, as_of=ini_a)
                status_agora = sheets.calc_task_status(task_dict, as_of=fim_a)
                if status_agora == "Vencida":
                    vencidas_agora += 1
                    if status_antes != "Vencida":
                        novas_vencidas += 1
            if novas_vencidas:
                texto = f"{novas_vencidas} manutenção(ões) venceu(ram) no período."
                piorou.append(texto)
                pontos_rank.append((3, texto))
            if vencidas_agora:
                pendencias.append(f"{vencidas_agora} manutenção(ões) vencida(s).")
    except Exception:
        pass

    try:
        df_cham_abertos = sheets.get_chamados_v2(client_id=cliente_id, ativo_id=ativo_id)
        if not df_cham_abertos.empty and "Status" in df_cham_abertos.columns:
            n_abertos = int((df_cham_abertos["Status"].astype(str).str.strip() != "Concluído").sum())
            if n_abertos:
                pendencias.append(f"{n_abertos} chamado(s) em aberto.")
    except Exception:
        pass

    try:
        gut_atual = sheets.get_gut_summary(cliente_id)
        if ativo_id:
            gut_atual = [i for i in gut_atual if i.get("ativo_id") == ativo_id]
        gut_alto_critico = [i for i in gut_atual if i.get("prioridade") in ("Alta", "Crítica")]
        if gut_alto_critico:
            pendencias.append(f"{len(gut_alto_critico)} item(ns) GUT Alta/Crítica ainda aberto(s).")
            pontos_rank.append((2, f"{len(gut_alto_critico)} item(ns) GUT Alta/Crítica em aberto."))
    except Exception:
        gut_atual = []

    pontos_rank.sort(key=lambda t: t[0])
    pontos_gerencia = [texto for _, texto in pontos_rank[:7]]

    charts = _montar_charts(dados_atual, snap_anterior, tem_snapshot, gut_atual)

    return {
        "ok": True, "cliente_id": cliente_id, "ativo_id": ativo_id,
        "periodo_atual": periodo_atual, "periodo_anterior": periodo_anterior,
        "tem_snapshot_anterior": tem_snapshot,
        "melhorou": melhorou, "piorou": piorou,
        "novidades": novidades, "pendencias": pendencias,
        "pontos_gerencia": pontos_gerencia, "charts": charts,
        "dados_atual": dados_atual, "dados_anterior": dados_anterior,
    }


def _montar_charts(dados_atual: dict, snap_anterior: dict | None,
                   tem_snapshot: bool, gut_atual: list) -> dict:
    """Dados de gráfico "antes×depois" — nunca gera gráfico vazio (mesma
    regra de executive_summary.compute_chart_data)."""
    charts: dict = {}

    df_ativos = dados_atual.get("ativos")
    if df_ativos is not None and not df_ativos.empty and "Status" in df_ativos.columns:
        st_norm = df_ativos["Status"].astype(str).apply(_status_ativo_norm)
        ativos_por_status = {}
        for label in ("Bom", "Atenção", "Crítico", "Urgente"):
            n = int((st_norm == label).sum())
            if n:
                ativos_por_status[label] = n
        if ativos_por_status:
            charts["ativos_por_status"] = ativos_por_status

        if tem_snapshot and snap_anterior.get("score_medio") is not None:
            scores = pd.to_numeric(df_ativos.get("Score", pd.Series(dtype=float)), errors="coerce").dropna()
            if len(scores):
                charts["saude_antes_depois"] = {
                    "antes": snap_anterior["score_medio"],
                    "depois": round(float(scores.mean()), 1),
                }

    if tem_snapshot:
        gut_antigo = snap_anterior.get("gut_top", [])
        n_antigo = len([i for i in gut_antigo if i.get("prioridade") in ("Alta", "Crítica")])
        n_novo = len([i for i in gut_atual if i.get("prioridade") in ("Alta", "Crítica")])
        if n_antigo or n_novo:
            charts["gut_critico_antes_depois"] = {"antes": n_antigo, "depois": n_novo}

    df_rel = dados_atual.get("relatorios")
    if df_rel is not None and not df_rel.empty and "Severidade" in df_rel.columns:
        rel_sev = {}
        for label in ("Normal", "Atenção", "Crítico", "Urgente"):
            n = int(df_rel["Severidade"].astype(str).str.strip().eq(label).sum())
            if n:
                rel_sev[label] = n
        if rel_sev:
            charts["relatorios_por_severidade"] = rel_sev

    return charts
