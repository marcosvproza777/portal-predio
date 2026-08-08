"""Resumo Executivo por Período — Portal Pred.IO.

Consolida relatórios, manutenções, alertas, chamados, GUT e recomendações
de um cliente (e, opcionalmente, de um ativo) num resumo pronto para
reuniões de gerência.

SEGURANÇA:
- cliente_id deve SEMPRE vir da sessão (current_client_id()) no Portal do
  Cliente, ou da seleção explícita do staff na Supervisão — nunca de
  input livre do cliente comum.
- modo "cliente" e "admin_cliente" NUNCA incluem rascunhos nem
  observações internas — usam sempre os mesmos getters staff=False já
  usados no restante do Portal do Cliente (get_technical_reports,
  get_maintenance_tasks, get_gut_summary).
- modo "interno_predio" pode incluir rascunhos e observações internas.
  Quem chama esta função é responsável por só usar "interno_predio"
  depois de validar is_staff() — esta função não lê st.session_state
  para permanecer pura e testável fora do contexto Streamlit.
- Nenhuma nota GUT autoriza overhaul, troca de rolamento ou parada de
  máquina automaticamente — este módulo só reaproveita os textos de
  gut.gut_acao_recomendada(), que já respeitam essa regra.
"""
from __future__ import annotations

import datetime as _dt
import pandas as pd

from gut import GUT_DISCLAIMER

TIPOS_RESUMO = ["Resumo para reunião", "Resumo técnico", "Resumo gerencial"]
MODOS = ("cliente", "admin_cliente", "interno_predio")

TEXTO_OBRIGATORIO = (
    "Este resumo consolida informações disponíveis no Portal Pred.IO no período "
    "selecionado e tem objetivo de apoio à gestão. Decisões críticas devem ser "
    "validadas pela equipe técnica Pred.IO."
)

PERIODOS_PRESET = {
    "7d":  ("Últimos 7 dias", 7),
    "30d": ("Últimos 30 dias", 30),
    "90d": ("Últimos 90 dias", 90),
}


# ═══════════════════════════════════════════════════════════════════════════════
# PERÍODO
# ═══════════════════════════════════════════════════════════════════════════════

def resolver_periodo(preset: str, custom_ini: _dt.date | None = None,
                     custom_fim: _dt.date | None = None) -> tuple:
    """Retorna (data_inicio, data_fim) a partir do preset selecionado.
    Preset padrão (desconhecido/ausente): últimos 30 dias."""
    hoje = _dt.date.today()
    if preset == "este_mes":
        return hoje.replace(day=1), hoje
    if preset == "mes_anterior":
        primeiro_atual   = hoje.replace(day=1)
        ultimo_anterior  = primeiro_atual - _dt.timedelta(days=1)
        return ultimo_anterior.replace(day=1), ultimo_anterior
    if preset == "custom" and custom_ini and custom_fim:
        return custom_ini, custom_fim
    _, dias = PERIODOS_PRESET.get(preset, PERIODOS_PRESET["30d"])
    return hoje - _dt.timedelta(days=dias), hoje


def _filtrar_periodo(df: pd.DataFrame, col_data: str, ini: _dt.date, fim: _dt.date) -> pd.DataFrame:
    if df is None or df.empty or col_data not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    d["_dt"] = pd.to_datetime(d[col_data].astype(str), dayfirst=True, errors="coerce")
    dt_ini = pd.Timestamp(ini)
    dt_fim = pd.Timestamp(fim) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    d = d[(d["_dt"] >= dt_ini) & (d["_dt"] <= dt_fim)]
    return d.drop(columns=["_dt"]).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# COLETA DE DADOS
# ═══════════════════════════════════════════════════════════════════════════════

def _coletar_dados(cliente_id: str, ativo_id: str, ini: _dt.date, fim: _dt.date,
                   modo: str, incluir: dict) -> dict:
    from sheets import (
        get_technical_reports, get_maintenance_tasks, get_maintenance_executions,
        get_alertas_sv, get_chamados_v2, get_gut_summary, get_all_ativos_sv,
    )

    staff_mode = modo == "interno_predio"
    dados: dict = {}

    # ── Ativos monitorados ──────────────────────────────────────────────────
    df_ativos = pd.DataFrame()
    try:
        df_ativos = get_all_ativos_sv()
        if not df_ativos.empty and "Client_Id" in df_ativos.columns:
            df_ativos = df_ativos[
                df_ativos["Client_Id"].astype(str).str.strip().str.lower() == cliente_id.strip().lower()
            ]
            if ativo_id:
                df_ativos = df_ativos[df_ativos["Id"].astype(str).str.strip() == ativo_id.strip()]
    except Exception:
        df_ativos = pd.DataFrame()
    dados["ativos"] = df_ativos

    # ── Relatórios publicados (ou todos, em modo interno) ───────────────────
    df_rel = pd.DataFrame()
    if incluir.get("relatorios", True):
        try:
            df_rel = get_technical_reports(client_id=cliente_id, ativo_id=ativo_id, staff=staff_mode)
            df_rel = _filtrar_periodo(df_rel, "Data_Relatorio", ini, fim)
            if not staff_mode and "Obs_Interna" in df_rel.columns:
                df_rel = df_rel.drop(columns=["Obs_Interna"])
        except Exception:
            df_rel = pd.DataFrame()
    dados["relatorios"] = df_rel

    # ── Manutenções executadas no período ───────────────────────────────────
    df_mex = pd.DataFrame()
    if incluir.get("manutencoes", True):
        try:
            df_mex = get_maintenance_executions(client_id=cliente_id, ativo_id=ativo_id, limit=300)
            df_mex = _filtrar_periodo(df_mex, "Executado_Em", ini, fim)
            if not staff_mode and "Obs_Interna" in df_mex.columns:
                df_mex = df_mex.drop(columns=["Obs_Interna"])
        except Exception:
            df_mex = pd.DataFrame()
    dados["manutencoes_executadas"] = df_mex

    # ── Manutenções pendentes/vencidas (situação atual, não é por período) ──
    df_mpend = pd.DataFrame()
    if incluir.get("manutencoes", True):
        try:
            df_mpend = get_maintenance_tasks(client_id=cliente_id, ativo_id=ativo_id, staff=staff_mode)
            if not df_mpend.empty and "Status" in df_mpend.columns:
                df_mpend = df_mpend[~df_mpend["Status"].str.lower().str.contains("conclu|arquiv", na=False)]
        except Exception:
            df_mpend = pd.DataFrame()
    dados["manutencoes_pendentes"] = df_mpend

    # ── Alertas do período ───────────────────────────────────────────────────
    df_al = pd.DataFrame()
    if incluir.get("alertas", True):
        try:
            df_al = get_alertas_sv(cliente_id)
            if not df_al.empty and ativo_id and "Ativo_Id" in df_al.columns:
                df_al = df_al[df_al["Ativo_Id"].astype(str).str.strip() == ativo_id.strip()]
            df_al = _filtrar_periodo(df_al, "Criado_Em", ini, fim)
        except Exception:
            df_al = pd.DataFrame()
    dados["alertas"] = df_al

    # ── Chamados do período ─────────────────────────────────────────────────
    df_cham = pd.DataFrame()
    if incluir.get("chamados", True):
        try:
            df_cham = get_chamados_v2(client_id=cliente_id, ativo_id=ativo_id)
            df_cham = _filtrar_periodo(df_cham, "Aberto_Em", ini, fim)
        except Exception:
            df_cham = pd.DataFrame()
    dados["chamados"] = df_cham

    # ── GUT / prioridades — sempre client-safe (get_gut_summary já filtra
    #    com staff=False internamente, mesmo em modo interno_predio) ─────────
    gut_itens: list = []
    if incluir.get("gut", True):
        try:
            gut_itens = get_gut_summary(cliente_id)
            if ativo_id:
                gut_itens = [i for i in gut_itens if i.get("ativo_id", "") == ativo_id]

            def _no_periodo(item: dict) -> bool:
                d = pd.to_datetime(item.get("created_at", ""), dayfirst=True, errors="coerce")
                if pd.isna(d):
                    return True  # sem data legível — mantém para não perder item relevante
                return pd.Timestamp(ini) <= d <= pd.Timestamp(fim) + pd.Timedelta(hours=23, minutes=59)

            gut_itens = [i for i in gut_itens if _no_periodo(i)]
        except Exception:
            gut_itens = []
    dados["gut_itens"] = gut_itens

    return dados


# ═══════════════════════════════════════════════════════════════════════════════
# MONTAGEM DO TEXTO
# ═══════════════════════════════════════════════════════════════════════════════

def _fmt_data(d: _dt.date) -> str:
    return d.strftime("%d/%m/%Y")


def _linha(rotulo: str, valor) -> str:
    return f"  • {rotulo}: {valor}"


def _montar_texto(cliente_nome: str, ativo_nome: str, periodo_inicio: _dt.date,
                  periodo_fim: _dt.date, tipo_resumo: str, modo: str, dados: dict) -> str:
    df_ativos = dados["ativos"]
    df_rel    = dados["relatorios"]
    df_mex    = dados["manutencoes_executadas"]
    df_mpend  = dados["manutencoes_pendentes"]
    df_al     = dados["alertas"]
    df_cham   = dados["chamados"]
    gut_itens = dados["gut_itens"]

    n_ativos    = len(df_ativos) if df_ativos is not None else 0
    score_medio = None
    if df_ativos is not None and not df_ativos.empty and "Score" in df_ativos.columns:
        scores = pd.to_numeric(df_ativos["Score"], errors="coerce").dropna()
        if len(scores):
            score_medio = round(scores.mean(), 1)

    n_manut_vencidas = 0
    n_manut_proximas = 0
    if df_mpend is not None and not df_mpend.empty and "Status" in df_mpend.columns:
        s = df_mpend["Status"].astype(str).str.lower()
        n_manut_vencidas = int(s.str.contains("vencid|atraso").sum())
        n_manut_proximas = int(s.str.contains("próxim|proxim").sum())

    criticos_gut = [i for i in gut_itens if i.get("prioridade") == "Crítica"]
    altos_gut    = [i for i in gut_itens if i.get("prioridade") == "Alta"]

    linhas: list[str] = []

    # ── Título / subtítulo ──────────────────────────────────────────────────
    linhas.append("RESUMO EXECUTIVO PRED.IO")
    subtitulo = f"Cliente: {cliente_nome}"
    if ativo_nome:
        subtitulo += f"  ·  Ativo: {ativo_nome}"
    subtitulo += f"  ·  Período: {_fmt_data(periodo_inicio)} a {_fmt_data(periodo_fim)}"
    subtitulo += f"  ·  Tipo: {tipo_resumo}"
    linhas.append(subtitulo)
    linhas.append("")
    linhas.append(TEXTO_OBRIGATORIO)
    linhas.append("")

    # ── 1. Sumário executivo ────────────────────────────────────────────────
    linhas.append("1. SUMÁRIO EXECUTIVO")
    linhas.append(
        f"  No período de {_fmt_data(periodo_inicio)} a {_fmt_data(periodo_fim)}, "
        f"{n_ativos} ativo(s) monitorado(s)"
        + (f", com saúde média de {score_medio}/100" if score_medio is not None else "")
        + f". Foram registrados {len(df_rel)} relatório(s), {len(df_al)} alerta(s) e "
        f"{len(df_cham)} chamado(s). {len(criticos_gut)} item(ns) em prioridade GUT crítica."
    )
    linhas.append("")

    # ── 2. Indicadores principais ───────────────────────────────────────────
    linhas.append("2. INDICADORES PRINCIPAIS")
    linhas.append(_linha("Ativos monitorados", n_ativos))
    linhas.append(_linha("Saúde média", f"{score_medio}/100" if score_medio is not None else "—"))
    linhas.append(_linha("Relatórios publicados no período", len(df_rel)))
    linhas.append(_linha("Manutenções executadas no período", len(df_mex)))
    linhas.append(_linha("Manutenções vencidas (situação atual)", n_manut_vencidas))
    linhas.append(_linha("Manutenções próximas do vencimento", n_manut_proximas))
    linhas.append(_linha("Alertas no período", len(df_al)))
    linhas.append(_linha("Chamados no período", len(df_cham)))
    linhas.append(_linha("Itens GUT críticos", len(criticos_gut)))
    linhas.append(_linha("Itens GUT alta prioridade", len(altos_gut)))
    linhas.append("")

    # ── 3. Relatórios analisados ────────────────────────────────────────────
    linhas.append("3. RELATÓRIOS ANALISADOS")
    if df_rel is None or df_rel.empty:
        linhas.append("  Nenhum relatório no período selecionado.")
    else:
        for _, r in df_rel.head(10).iterrows():
            linhas.append(
                f"  • [{str(r.get('Data_Relatorio','')).strip()}] "
                f"{str(r.get('Titulo','')).strip()} — "
                f"{str(r.get('Tipo_Servico','')).strip()} "
                f"(Severidade: {str(r.get('Severidade','Normal')).strip()})"
            )
    linhas.append("")

    # ── 4. Principais pontos técnicos ───────────────────────────────────────
    linhas.append("4. PRINCIPAIS PONTOS TÉCNICOS")
    achados = []
    if df_rel is not None and not df_rel.empty:
        for _, r in df_rel.head(6).iterrows():
            resumo = str(r.get("Resumo", "")).strip()
            if resumo and resumo.lower() not in ("nan", ""):
                achados.append(f"  • {str(r.get('Titulo','Relatório')).strip()}: {resumo[:220]}")
    if achados:
        linhas.extend(achados)
    else:
        linhas.append("  Nenhum achado técnico relevante registrado no período.")
    linhas.append("")

    # ── 5. Manutenções e ações realizadas ───────────────────────────────────
    linhas.append("5. MANUTENÇÕES E AÇÕES REALIZADAS")
    if df_mex is None or df_mex.empty:
        linhas.append("  Nenhuma execução de manutenção registrada no período.")
    else:
        for _, m in df_mex.head(10).iterrows():
            linhas.append(
                f"  • [{str(m.get('Executado_Em','')).strip()}] "
                f"{str(m.get('Descricao_Execucao','Execução de manutenção')).strip()[:160]} "
                f"(Responsável: {str(m.get('Responsavel','—')).strip()})"
            )
    linhas.append("")

    # ── 6. Pendências e próximas ações ──────────────────────────────────────
    linhas.append("6. PENDÊNCIAS E PRÓXIMAS AÇÕES")
    if df_mpend is None or df_mpend.empty:
        linhas.append("  Nenhuma manutenção pendente no momento.")
    else:
        for _, t in df_mpend.head(10).iterrows():
            linhas.append(
                f"  • {str(t.get('Nome_Tarefa','Tarefa')).strip()} — "
                f"Status: {str(t.get('Status','')).strip()} "
                f"(Próxima execução: {str(t.get('Proxima_Execucao_Data','—')).strip()})"
            )
    linhas.append("")

    # ── 7. GUT e prioridades críticas ───────────────────────────────────────
    linhas.append("7. GUT E PRIORIDADES CRÍTICAS")
    linhas.append(f"  {GUT_DISCLAIMER}")
    top_gut = sorted(gut_itens, key=lambda i: i.get("score", 0), reverse=True)[:10]
    if not top_gut:
        linhas.append("  Nenhum item com GUT calculado no período.")
    else:
        for i in top_gut:
            linhas.append(
                f"  • [{i.get('prioridade','')} · score {i.get('score','')}] "
                f"{i.get('titulo','')} ({i.get('origem','')}) — {i.get('acao_recomendada','')}"
            )
    linhas.append("")

    # ── 8. Alertas e chamados relevantes ────────────────────────────────────
    linhas.append("8. ALERTAS E CHAMADOS RELEVANTES")
    if df_al is not None and not df_al.empty:
        linhas.append("  Alertas:")
        for _, a in df_al.head(8).iterrows():
            linhas.append(f"    • [{str(a.get('Prioridade','')).strip()}] {str(a.get('Titulo','')).strip()}")
    else:
        linhas.append("  Nenhum alerta no período.")
    if df_cham is not None and not df_cham.empty:
        linhas.append("  Chamados:")
        for _, c in df_cham.head(8).iterrows():
            linhas.append(
                f"    • [{str(c.get('Status','')).strip()}] {str(c.get('Titulo','')).strip()} "
                f"(Prioridade: {str(c.get('Prioridade','')).strip()})"
            )
    else:
        linhas.append("  Nenhum chamado no período.")
    linhas.append("")

    # ── 9. Recomendações Pred.IO ────────────────────────────────────────────
    linhas.append("9. RECOMENDAÇÕES PRED.IO")
    recs = []
    for i in top_gut[:6]:
        acao = i.get("acao_recomendada", "")
        if acao and acao not in recs:
            recs.append(acao)
    if df_rel is not None and not df_rel.empty:
        for _, r in df_rel.head(6).iterrows():
            rec = str(r.get("Recomendacoes", "")).strip()
            if rec and rec.lower() not in ("nan", "") and rec not in recs:
                recs.append(rec[:200])
    if recs:
        for rec in recs[:10]:
            linhas.append(f"  • {rec}")
    else:
        linhas.append("  Nenhuma recomendação adicional no período.")
    linhas.append(
        "  Observação: overhaul, troca de rolamento e parada de máquina nunca são "
        "automáticos — dependem sempre de análise preditiva e avaliação técnica Pred.IO."
    )
    linhas.append("")

    # ── 10. Conclusão para reunião ──────────────────────────────────────────
    linhas.append("10. CONCLUSÃO PARA REUNIÃO")
    pontos_reuniao = []
    if n_manut_vencidas:
        pontos_reuniao.append(f"{n_manut_vencidas} manutenção(ões) vencida(s) requer(em) atenção imediata")
    if criticos_gut:
        pontos_reuniao.append(f"{len(criticos_gut)} item(ns) em prioridade GUT crítica")
    if df_cham is not None and not df_cham.empty:
        abertos = df_cham[df_cham.get("Status", "").astype(str).str.lower() != "concluído"] if "Status" in df_cham.columns else df_cham
        if len(abertos):
            pontos_reuniao.append(f"{len(abertos)} chamado(s) em aberto no período")
    if not pontos_reuniao:
        pontos_reuniao.append("Nenhum ponto crítico pendente identificado no período — operação estável")
    linhas.append("  Pontos para levar à reunião com a gerência:")
    for p in pontos_reuniao:
        linhas.append(f"  • {p}")
    linhas.append("")
    linhas.append("  Fonte: Pred.IO")

    return "\n".join(linhas)


# ═══════════════════════════════════════════════════════════════════════════════
# SERVIÇO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def generate_executive_summary(
    *,
    usuario_id: str,
    cliente_id: str,
    cliente_nome: str,
    ativo_id: str = "",
    ativo_nome: str = "",
    periodo_inicio: _dt.date,
    periodo_fim: _dt.date,
    tipo_resumo: str = "Resumo para reunião",
    modo: str = "cliente",
    incluir: dict | None = None,
    salvar: bool = True,
) -> dict:
    """Gera (e, por padrão, salva) o resumo executivo consolidado do período.

    Retorna dict:
      ok, titulo, texto, dados (DataFrames/listas usados — auditoria),
      cliente_id, ativo_id, periodo_inicio, periodo_fim, modo, tipo_resumo,
      summary_id (se salvar=True e a gravação funcionar).

    SEGURANÇA: cliente_id deve vir sempre de current_client_id() (Portal do
    Cliente) ou de uma seleção explícita do staff já autenticado como
    is_staff() (Supervisão) — nunca de input livre do cliente comum. Esta
    função não valida perfil porque não tem acesso à sessão Streamlit;
    quem chama (UI) é responsável por essa checagem antes de invocá-la
    com modo != "cliente".
    """
    if not cliente_id:
        return {"ok": False, "erro": "cliente_id obrigatório."}
    if modo not in MODOS:
        modo = "cliente"
    if periodo_fim < periodo_inicio:
        return {"ok": False, "erro": "Período inválido: fim anterior ao início."}

    incluir = incluir or {"relatorios": True, "manutencoes": True,
                          "alertas": True, "chamados": True, "gut": True}

    dados = _coletar_dados(cliente_id, ativo_id, periodo_inicio, periodo_fim, modo, incluir)

    titulo = f"Resumo Executivo Pred.IO — {cliente_nome}"
    if ativo_nome:
        titulo += f" — {ativo_nome}"

    texto = _montar_texto(
        cliente_nome=cliente_nome, ativo_nome=ativo_nome,
        periodo_inicio=periodo_inicio, periodo_fim=periodo_fim,
        tipo_resumo=tipo_resumo, modo=modo, dados=dados,
    )

    resultado = {
        "ok": True, "titulo": titulo, "texto": texto, "dados": dados,
        "cliente_id": cliente_id, "ativo_id": ativo_id,
        "periodo_inicio": periodo_inicio, "periodo_fim": periodo_fim,
        "modo": modo, "tipo_resumo": tipo_resumo,
    }

    if salvar:
        from sheets import add_executive_summary
        summary_id = add_executive_summary(
            cliente_id=cliente_id, titulo=titulo, resumo_texto=texto,
            gerado_por_usuario_id=usuario_id, ativo_id=ativo_id,
            tipo_resumo=tipo_resumo, modo=modo,
            periodo_inicio=periodo_inicio.strftime("%d/%m/%Y"),
            periodo_fim=periodo_fim.strftime("%d/%m/%Y"),
            dados_usados=",".join(k for k, v in incluir.items() if v),
        )
        resultado["summary_id"] = summary_id

    return resultado


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTAÇÃO — WORD (.docx)
# ═══════════════════════════════════════════════════════════════════════════════
# Reaproveita apenas python-docx (já em requirements.txt — ver
# report_word_generator.py). Não há biblioteca de geração de PDF no projeto
# (pdfplumber/PyPDF2 só leem PDF); exportar PDF nesta primeira versão exigiria
# instalar uma dependência nova, o que o pedido explicitamente pede para evitar
# — por isso a exportação desta etapa é Word + copiar texto, conforme o
# projeto já suporta.

_NAVY  = "0F1F3D"
_BLUE  = "2563EB"
_MUTED = "64748B"


def gerar_resumo_executivo_word(resultado: dict) -> bytes:
    """Gera o .docx do resumo executivo a partir do texto já montado por
    generate_executive_summary(). Retorna bytes do arquivo."""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise ImportError("python-docx não instalado. Verifique requirements.txt.")
    import io

    def _rgb(h: str) -> "RGBColor":
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    doc = Document()

    titulo_p = doc.add_paragraph()
    titulo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo_p.add_run(resultado.get("titulo", "Resumo Executivo Pred.IO"))
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = _rgb(_NAVY)

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub_p.add_run(
        f"Período: {resultado['periodo_inicio'].strftime('%d/%m/%Y')} a "
        f"{resultado['periodo_fim'].strftime('%d/%m/%Y')}  ·  Tipo: {resultado.get('tipo_resumo','')}"
    )
    sub_run.italic = True
    sub_run.font.size = Pt(10)
    sub_run.font.color.rgb = _rgb(_MUTED)

    doc.add_paragraph()

    texto = resultado.get("texto", "")
    for linha in texto.split("\n"):
        stripped = linha.strip()
        if not stripped:
            doc.add_paragraph()
            continue
        # Cabeçalho de seção: "1. SUMÁRIO EXECUTIVO" (dígito + ponto + maiúsculas)
        if len(stripped) > 2 and stripped[0].isdigit() and stripped.split(".", 1)[0].isdigit() \
                and stripped.upper() == stripped and any(c.isalpha() for c in stripped):
            p = doc.add_paragraph()
            r = p.add_run(stripped)
            r.bold = True
            r.font.size = Pt(13)
            r.font.color.rgb = _rgb(_BLUE)
            continue
        if stripped.startswith("•"):
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(stripped.lstrip("• ").strip())
            continue
        if stripped == "RESUMO EXECUTIVO PRED.IO" or stripped.startswith("Cliente:"):
            continue  # título/subtítulo já renderizados acima
        if stripped == TEXTO_OBRIGATORIO:
            p = doc.add_paragraph()
            r = p.add_run(stripped)
            r.italic = True
            r.font.size = Pt(9)
            r.font.color.rgb = _rgb(_MUTED)
            continue
        doc.add_paragraph(stripped)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
