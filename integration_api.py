"""
API de integração — App Relatórios Pred.IO -> Portal Pred.IO (Etapa 3).

Por que este arquivo existe: o Portal roda como um único processo Streamlit
(sem rotas HTTP próprias) e o App Relatórios é um site estático (Cloudflare,
sem servidor). Para o App publicar um relatório no Portal, alguém precisa
falar HTTP — este é esse "alguém". Ele NÃO duplica o backend: importa
sheets.py e drive_storage.py direto, ou seja, lê/escreve exatamente a mesma
planilha e o mesmo bucket que o Streamlit usa. Ver arquitetura recomendada em
docs/PREDIO_INTEGRACAO_APP_RELATORIOS_ETAPA_1.md.

Deploy: segundo Web Service no Render, mesmo repositório do Portal.
  startCommand: uvicorn integration_api:app --host 0.0.0.0 --port $PORT
  env vars: as mesmas credenciais Google já usadas pelo Portal
            (GCP_CREDENTIALS_JSON ou GCP_CREDENTIALS_B64, GCS_BUCKET_NAME)
            + INTEGRATION_API_TOKEN (novo — gerar um segredo aleatório)
            + INTEGRATION_ALLOWED_ORIGINS (opcional — domínio do App Relatórios)

Autenticação: header "Authorization: Bearer <INTEGRATION_API_TOKEN>" em toda
rota /api/integrations/*. Token comparado em tempo constante. Este token só
abre estas rotas — nunca a service account do Portal (Sheets/GCS), que
permanece só no servidor.
"""
from __future__ import annotations

import hmac
import json
import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import drive_storage
import gut
import sheets

app = FastAPI(title="Pred.IO Integrations API", version="1.0.0")

_allowed_origins = [
    o.strip() for o in os.environ.get("INTEGRATION_ALLOWED_ORIGINS", "*").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins or ["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Margem de segurança abaixo do limite de ~50.000 caracteres por célula do
# Google Sheets — medições muito grandes ficam truncadas, nunca quebram a escrita.
_MEDICOES_JSON_MAX_CHARS = 45000


def _check_auth(authorization: str | None) -> None:
    token = os.environ.get("INTEGRATION_API_TOKEN", "")
    if not token:
        raise HTTPException(
            status_code=503,
            detail="Integração não configurada no servidor (INTEGRATION_API_TOKEN ausente).",
        )
    provided = ""
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    if not provided or not hmac.compare_digest(provided, token):
        _log("token", "-", "negado", detalhe="token de integração inválido ou ausente")
        raise HTTPException(status_code=401, detail="Token de integração inválido ou ausente.")


def _log(recurso_tipo: str, recurso_id: str, resultado: str,
         client_id: str = "", detalhe: str = "") -> None:
    """Auditoria da integração (aba AcessoAuditoria, mesma usada pelo resto
    do Portal — nada duplicado). NUNCA loga o token em si, só o resultado da
    checagem. Nunca derruba a requisição se o log falhar."""
    try:
        from security import log_acesso
        log_acesso(
            acao="integracao_app_relatorios",
            recurso_tipo=recurso_tipo,
            recurso_id=recurso_id,
            resultado=resultado,
            client_id=client_id,
            rota="api/integrations",
            detalhe=detalhe,
        )
    except Exception:
        pass


@app.get("/")
def root():
    return {"service": "predio-integrations-api", "ok": True}


@app.get("/api/integrations/health")
def health():
    return {"ok": True}


@app.get("/api/integrations/clientes")
def listar_clientes(authorization: str | None = Header(default=None)):
    """Lista clientes do Portal — usado pelo App Relatórios para o técnico
    escolher a que cliente do Portal este relatório pertence."""
    _check_auth(authorization)
    df = sheets.get_all_clientes()
    if df.empty:
        return []
    out = []
    for _, r in df.iterrows():
        empresa = str(r.get("Empresa", "")).strip()
        cid = str(r.get("Client_Id", r.get("Cliente_Id", ""))).strip()
        if empresa and cid:
            out.append({"cliente_id": cid, "empresa": empresa})
    return out


@app.get("/api/integrations/ativos")
def listar_ativos(cliente_id: str, authorization: str | None = Header(default=None)):
    """Lista ativos de um cliente do Portal — mesma função (sheets.get_ativos)
    já usada pelo seletor de ativo na Supervisão, sem lógica duplicada."""
    _check_auth(authorization)
    cliente_id = (cliente_id or "").strip()
    if not cliente_id:
        raise HTTPException(status_code=422, detail="cliente_id é obrigatório.")
    df = sheets.get_ativos(cliente_id)
    if df.empty:
        return []
    out = []
    for _, r in df.iterrows():
        aid = str(r.get("Id", "")).strip()
        tag = str(r.get("Tag", "") or r.get("Nome", "")).strip()
        planta = str(r.get("Planta", "")).strip()
        if aid:
            out.append({"ativo_id": aid, "tag": tag, "planta": planta})
    return out


class ReportPayload(BaseModel):
    report_id: str
    cliente_id: str
    ativo_id: str
    titulo: str
    tipo_relatorio: str
    data_relatorio: str
    tecnico: str = ""
    severidade: str = "Normal"
    resumo: str
    conclusao: str = ""
    recomendacoes: str = ""
    planta: str = ""
    equipamento: str = ""
    gut_gravidade: int | None = None
    gut_urgencia: int | None = None
    gut_tendencia: int | None = None
    gut_score: int | None = None
    gut_prioridade: str = ""
    medicoes: Any = None


@app.post("/api/integrations/reports")
async def publicar_relatorio(
    payload: str = Form(...),
    pdf: UploadFile | None = File(default=None),
    authorization: str | None = Header(default=None),
):
    """
    Recebe um relatório finalizado do App Relatórios e cria/atualiza o
    relatório correspondente no Portal (aba TechnicalReports).

    Idempotência: identifica o relatório pelo App_Report_Id (o report.id do
    App). Reenviar o mesmo report_id atualiza os dados em vez de duplicar.

    PDF é opcional nesta chamada — o App Relatórios gera PDF via impressão
    nativa do navegador, que não expõe o arquivo para o JavaScript enviar
    sozinho. Quando o técnico anexa o PDF manualmente aqui, ele sobe para o
    storage privado do Portal (mesma função usada no Upload Direto da
    Etapa 2). Sem anexo, o relatório entra do mesmo jeito — a equipe Pred.IO
    pode anexar o PDF depois, editando o relatório na Supervisão.
    """
    _check_auth(authorization)

    try:
        dados = ReportPayload.model_validate_json(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"payload inválido: {exc}")

    report_id  = dados.report_id.strip()
    cliente_id = dados.cliente_id.strip()
    ativo_id   = dados.ativo_id.strip()
    if not report_id:
        raise HTTPException(status_code=422, detail="report_id é obrigatório.")
    if not cliente_id:
        raise HTTPException(status_code=422, detail="cliente_id é obrigatório.")
    if not ativo_id:
        raise HTTPException(status_code=422, detail="ativo_id é obrigatório.")
    if not dados.resumo.strip():
        raise HTTPException(status_code=422, detail="resumo é obrigatório.")

    # Cliente precisa existir no Portal — nunca aceitar cliente_id sem validar.
    df_cli = sheets.get_all_clientes()
    cli_ids = set()
    if not df_cli.empty:
        for _, r in df_cli.iterrows():
            cid = str(r.get("Client_Id", r.get("Cliente_Id", ""))).strip().lower()
            if cid:
                cli_ids.add(cid)
    if cliente_id.lower() not in cli_ids:
        _log("relatorio", report_id, "negado", detalhe=f"cliente_id não encontrado: {cliente_id}")
        raise HTTPException(status_code=404, detail="Cliente não encontrado no Portal Pred.IO.")

    # Ativo precisa existir E pertencer ao cliente. Mensagem exata pedida na
    # Etapa 3 quando o ativo simplesmente não existe no Portal ainda — não
    # criamos o ativo automaticamente nesta etapa.
    ativo = sheets.get_ativo_by_id(ativo_id)
    if not ativo:
        _log("relatorio", report_id, "negado", client_id=cliente_id,
             detalhe=f"ativo_id não vinculado ao Portal: {ativo_id}")
        raise HTTPException(
            status_code=404,
            detail="O ativo selecionado ainda não está vinculado ao Portal Pred.IO. "
                   "Cadastre ou vincule o ativo antes de publicar o relatório.",
        )
    if not sheets.ativo_pertence_cliente(ativo_id, cliente_id):
        _log("relatorio", report_id, "negado", client_id=cliente_id,
             detalhe=f"ativo_id {ativo_id} não pertence a {cliente_id}")
        raise HTTPException(status_code=403, detail="O ativo informado pertence a outro cliente.")

    existing = sheets.get_technical_report_by_app_id(report_id)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    medicoes_json = ""
    if dados.medicoes is not None:
        try:
            medicoes_json = json.dumps(dados.medicoes, ensure_ascii=False)[:_MEDICOES_JSON_MAX_CHARS]
        except Exception:
            medicoes_json = ""

    # GUT: só é gravado se o App mandar as 3 notas (Gravidade/Urgência/
    # Tendência) — score e prioridade são SEMPRE recalculados aqui a partir
    # delas (gut.calculate_gut valida 1..5). Um gut_score/gut_prioridade
    # enviado pronto, sem as notas, nunca é aceito — não confiamos em valor
    # já calculado vindo de fora. Se o App não manda GUT, o campo fica
    # em branco e a Supervisão pode defini-lo depois (comportamento já
    # existente desde a Etapa 2/3).
    gut_campos: dict = {}
    if dados.gut_gravidade is not None and dados.gut_urgencia is not None and dados.gut_tendencia is not None:
        resultado = gut.calculate_gut(dados.gut_gravidade, dados.gut_urgencia, dados.gut_tendencia)
        if resultado:
            gut_campos = {
                "Gut_Gravidade":  dados.gut_gravidade,
                "Gut_Urgencia":   dados.gut_urgencia,
                "Gut_Tendencia":  dados.gut_tendencia,
                "Gut_Score":      resultado["score"],
                "Gut_Prioridade": resultado["prioridade"],
            }
        else:
            raise HTTPException(
                status_code=422,
                detail="gut_gravidade/gut_urgencia/gut_tendencia precisam ser números de 1 a 5.",
            )

    campos_comuns = {
        "Cliente_Id":       cliente_id,
        "Ativo_Id":         ativo_id,
        "Titulo":           dados.titulo.strip(),
        "Tipo_Servico":     dados.tipo_relatorio.strip(),
        "Severidade":       dados.severidade.strip() or "Normal",
        "Data_Relatorio":   dados.data_relatorio.strip(),
        "Planta":           dados.planta.strip(),
        "Equipamento":      dados.equipamento.strip(),
        "Resumo":           dados.resumo.strip(),
        "Recomendacoes":    dados.recomendacoes.strip(),
        "Conclusao":        dados.conclusao.strip(),
        "Tecnico":          dados.tecnico.strip(),
        "Origem":           sheets.ORIGEM_APP_RELATORIOS,
        "Medicoes_Json":    medicoes_json,
        "Sincronizado_Em":  now,
    }

    if existing:
        # Atualiza pelo Id real do Portal — nunca cria outro relatório para
        # o mesmo App_Report_Id. Status não é tocado aqui: se a equipe já
        # publicou ou arquivou, uma atualização de conteúdo não deve
        # rebaixar/republicar sozinha.
        portal_id = existing["Id"]
        ok = sheets.update_technical_report(portal_id, {**campos_comuns, **gut_campos})
        if not ok:
            raise HTTPException(status_code=500, detail="Falha ao atualizar relatório no Portal.")
        created = False
        status_atual = existing.get("Status", "Rascunho")
        # Etapa 5 — se o relatório já estava Publicado, o conteúdo mudou:
        # reindexa pro Assistente Técnico não responder com dado desatualizado.
        # Rascunho/Em revisão não são indexados (reindex_technical_report tem
        # o guard de Status internamente também).
        if status_atual.strip() == "Publicado":
            sheets.reindex_technical_report(portal_id)
    else:
        criacao = {
            "cliente_id": cliente_id, "ativo_id": ativo_id, "titulo": dados.titulo.strip(),
            "tipo_servico": dados.tipo_relatorio.strip(), "severidade": dados.severidade.strip() or "Normal",
            "data_relatorio": dados.data_relatorio.strip(), "planta": dados.planta.strip(),
            "equipamento": dados.equipamento.strip(), "resumo": dados.resumo.strip(),
            "recomendacoes": dados.recomendacoes.strip(), "conclusao": dados.conclusao.strip(),
            "tecnico": dados.tecnico.strip(), "origem": sheets.ORIGEM_APP_RELATORIOS,
            "medicoes_json": medicoes_json, "sincronizado_em": now,
            "app_report_id": report_id,
            "status": "Em revisão",  # nunca publica automaticamente — equipe Pred.IO revisa antes
        }
        portal_id = sheets.add_technical_report(criacao, dados.tecnico.strip() or "App Relatórios")
        if not portal_id:
            raise HTTPException(status_code=500, detail="Falha ao criar relatório no Portal.")
        if gut_campos:
            sheets.update_technical_report(portal_id, gut_campos)
        created = True
        status_atual = "Em revisão"

    aviso = None
    if pdf is not None:
        try:
            pdf_bytes = await pdf.read()
            storage_path = drive_storage.upload_report_pdf(
                pdf_bytes, cliente_id, ativo_id, portal_id, pdf.filename or "relatorio.pdf",
            )
            sheets.update_technical_report(portal_id, {
                "Storage_Path": storage_path,
                "Arquivo_Nome": pdf.filename or "relatorio.pdf",
                "Arquivo_Url":  "",
            })
        except Exception as exc:
            aviso = f"Relatório salvo, mas falha ao enviar o PDF: {exc}"

    _log(
        "relatorio", portal_id, "erro" if aviso else "permitido",
        client_id=cliente_id,
        detalhe=f"app_report_id={report_id} criado={created} status={status_atual}"
                 + (f" | aviso: {aviso}" if aviso else ""),
    )

    resp = {"ok": True, "portal_report_id": portal_id, "status": status_atual, "created": created}
    if aviso:
        resp["aviso"] = aviso
    return resp
