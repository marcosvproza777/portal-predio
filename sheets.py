"""Google Sheets — conexão e operações de leitura/escrita."""
import base64
import json
import os
import re
import uuid
from datetime import datetime, timedelta

import gspread
import pandas as pd
import streamlit as st

import gut

SHEET_ID = "1cyDz6nuZ9ro7Inq-DNg9OH9d7GNn17WHZSIikkQ6hOA"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def _build_creds():
    """Retorna credenciais google-auth (gspread 6.x). Tenta todas as fontes.

    DIAGNÓSTICO TEMPORÁRIO (18/08/2026): cada fonte tentada loga em
    stdout/stderr (visível nos Logs do Render) se foi encontrada e, se
    falhou, a classe+mensagem da exceção — NUNCA o valor da credencial em
    si. Objetivo: descobrir por que "Credenciais não encontradas" está
    aparecendo em produção sem nenhum traceback nos logs (as exceções
    reais estavam sendo engolidas silenciosamente). Remover depois que o
    problema for identificado e corrigido."""
    import sys
    from google.oauth2.service_account import Credentials as _SA

    def _diag(msg: str) -> None:
        print(f"[_build_creds] {msg}", file=sys.stderr, flush=True)

    # 1. st.secrets
    try:
        if "gcp_service_account" in st.secrets:
            _diag("st.secrets[gcp_service_account] encontrado, tentando usar...")
            info = dict(st.secrets["gcp_service_account"])
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            return _SA.from_service_account_info(info, scopes=SCOPE)
        _diag("st.secrets[gcp_service_account] ausente.")
    except Exception as e:
        _diag(f"st.secrets falhou: {type(e).__name__}: {e}")

    # 2. env var base64
    try:
        import base64, json as _json
        raw_b64 = os.environ.get("GCP_CREDENTIALS_B64", "")
        if raw_b64:
            _diag(f"GCP_CREDENTIALS_B64 presente (len={len(raw_b64)}), tentando decodificar...")
            raw = base64.b64decode(raw_b64).decode("utf-8")
            return _SA.from_service_account_info(_json.loads(raw), scopes=SCOPE)
        _diag("GCP_CREDENTIALS_B64 ausente/vazia.")
    except Exception as e:
        _diag(f"GCP_CREDENTIALS_B64 falhou: {type(e).__name__}: {e}")

    # 3. env var JSON string
    try:
        import json as _json
        raw_j = os.environ.get("GCP_CREDENTIALS_JSON", "")
        if raw_j:
            _diag(f"GCP_CREDENTIALS_JSON presente (len={len(raw_j)}), tentando usar...")
            return _SA.from_service_account_info(_json.loads(raw_j), scopes=SCOPE)
        _diag("GCP_CREDENTIALS_JSON ausente/vazia.")
    except Exception as e:
        _diag(f"GCP_CREDENTIALS_JSON falhou: {type(e).__name__}: {e}")

    # 4. arquivo em disco
    for path in ("/etc/secrets/credentials.json", "credentials.json"):
        try:
            if os.path.exists(path):
                _diag(f"Arquivo {path} encontrado, tentando usar...")
                return _SA.from_service_account_file(path, scopes=SCOPE)
            _diag(f"Arquivo {path} não existe.")
        except Exception as e:
            _diag(f"Arquivo {path} falhou: {type(e).__name__}: {e}")

    _diag("Nenhuma fonte de credencial funcionou — retornando None.")

    return None


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    try:
        creds = _build_creds()
        if creds is None:
            st.error("Credenciais não encontradas. Configure GCP_CREDENTIALS_B64 no Render.")
            st.stop()
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Planilha não encontrada.")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        st.stop()


@st.cache_data(ttl=30, show_spinner=False)
def load_sheet(tab_name: str) -> pd.DataFrame:
    """Carrega uma aba e normaliza os nomes das colunas. Cache de 30 s."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet(tab_name)
        try:
            records = ws.get_all_records()
        except Exception:
            # Fallback para abas com headers duplicados/vazios (ex.: Ativos corrompida).
            # Lê valores brutos, descarta colunas sem nome e filtra só linhas com dados
            # nos índices válidos (ignora linhas com dados deslocados para colunas extras).
            all_values = ws.get_all_values()
            if not all_values:
                return pd.DataFrame()
            raw_headers = all_values[0]
            valid = [(i, h) for i, h in enumerate(raw_headers) if h.strip()]
            if not valid:
                return pd.DataFrame()
            indices, names = zip(*valid)
            rows = []
            for row in all_values[1:]:
                cells = [row[i] if i < len(row) else "" for i in indices]
                if any(c.strip() for c in cells):
                    rows.append(dict(zip(names, cells)))
            records = rows
        df = pd.DataFrame(records)
        if not df.empty:
            df.columns = [c.strip().title() for c in df.columns]
        return df
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _clear_read_caches() -> None:
    """Limpa load_sheet() e todas as camadas de cache por função construídas
    sobre ele (get_ativos, get_alertas_sv, get_technical_reports,
    get_maintenance_tasks, get_chamados_resumo_assistente,
    get_documentos_tecnicos, count_portal_notifications_unread).

    Mesma filosofia de invalidação ampla que load_sheet.clear() já tinha
    sozinho (qualquer escrita limpa tudo, não só a aba afetada) — TTL curto
    de cada camada já limita o estrago; ter um único ponto central evita
    esquecer de invalidar uma camada nova em algum ponto de escrita futuro.
    Chamada em todo lugar que antes chamava só load_sheet.clear()."""
    load_sheet.clear()
    get_ativos.clear()
    get_alertas_sv.clear()
    get_technical_reports.clear()
    get_maintenance_tasks.clear()
    get_chamados_resumo_assistente.clear()
    get_documentos_tecnicos.clear()
    count_portal_notifications_unread.clear()


def append_row(tab_name: str, values: list) -> bool:
    """Adiciona uma linha ao final da aba. Cria a aba se não existir."""
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title=tab_name, rows=1000, cols=max(len(values), 26))
        # table_range limita a detecção de tabela do gspread às colunas que
        # esta escrita realmente usa. Sem isso, em abas com colunas fantasmas
        # à direita (cabeçalho historicamente mal gerido), o append_row pode
        # "descobrir" uma tabela muito mais larga que o conteúdo real e
        # inserir a nova linha deslocada para a direita — efeito "escada"
        # observado em Ativos e Chamados, onde cada linha nova aparecia mais
        # à direita que a anterior em vez de sempre começar na coluna A.
        last_col = gspread.utils.rowcol_to_a1(1, len(values)).rstrip("0123456789")
        ws.append_row(values, value_input_option="USER_ENTERED", table_range=f"A1:{last_col}1")
        _clear_read_caches()
        try:
            st.session_state.pop("_sheets_last_error", None)
        except Exception:
            pass
        return True
    except Exception as _e:
        try:
            st.session_state["_sheets_last_error"] = str(_e)
        except Exception:
            pass
        import logging
        logging.error("append_row(%s): %s", tab_name, _e)
        return False


# ── Helpers internos ──────────────────────────────────────────────────────────

def _gerar_id(prefixo: str = "CH") -> str:
    """Gera ID único legível: CH-20260621-A3F8D2"""
    suffix = str(uuid.uuid4()).replace("-", "")[:6].upper()
    date_part = datetime.now().strftime("%Y%m%d")
    return f"{prefixo}-{date_part}-{suffix}"


def _mock_chamados() -> pd.DataFrame:
    """Retorna DataFrame vazio — dados de teste removidos."""
    return pd.DataFrame()


def _mock_mensagens(chamado_id: str) -> pd.DataFrame:
    """Mensagens de teste por chamado."""
    mocks = {
        "CH-20260618-C03001": [
            {
                "Id": "MSG-00001",
                "Id_Chamado": "CH-20260618-C03001",
                "Autor": "joao@cocacola.com",
                "Autor_Tipo": "cliente",
                "Mensagem": (
                    "Urgente: o Compressor C-03 apresentou ruído anormal após a partida "
                    "desta manhã. Há oscilação na operação e o operador relatou cheiro de "
                    "queimado na área. Paramos a máquina preventivamente."
                ),
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "mensagem_cliente",
                "Data": "18/06/2026 07:45:00",
            },
            {
                "Id": "MSG-00002",
                "Id_Chamado": "CH-20260618-C03001",
                "Autor": "sistema",
                "Autor_Tipo": "sistema",
                "Mensagem": "Status alterado: Aberto → Em andamento",
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "alteracao_status",
                "Data": "18/06/2026 08:00:00",
            },
            {
                "Id": "MSG-00003",
                "Id_Chamado": "CH-20260618-C03001",
                "Autor": "Marcos",
                "Autor_Tipo": "funcionario",
                "Mensagem": (
                    "João, recebemos o chamado com prioridade crítica. Nossa equipe está "
                    "sendo mobilizada. Por favor mantenha a máquina desligada por segurança. "
                    "Nosso técnico chegará à planta até as 14h de hoje."
                ),
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "resposta_predio",
                "Data": "18/06/2026 08:05:00",
            },
            {
                "Id": "MSG-00004",
                "Id_Chamado": "CH-20260618-C03001",
                "Autor": "Marcos",
                "Autor_Tipo": "funcionario",
                "Mensagem": (
                    "VERIFICAR: histórico indica última manutenção há 210 dias — "
                    "acima do limite de 180 dias. Solicitar ao cliente o log do painel "
                    "de controle antes de enviar técnico."
                ),
                "Visivel_Cliente": "0",
                "Tipo_Mensagem": "observacao_interna",
                "Data": "18/06/2026 08:10:00",
            },
        ],
        "CH-20260619-M10002": [
            {
                "Id": "MSG-00005",
                "Id_Chamado": "CH-20260619-M10002",
                "Autor": "maria@sibele.com",
                "Autor_Tipo": "cliente",
                "Mensagem": (
                    "Solicitamos avaliação do resultado da última análise de óleo do "
                    "Motor M-10. O relatório chegou mas gostaríamos de uma explicação "
                    "técnica dos resultados."
                ),
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "mensagem_cliente",
                "Data": "19/06/2026 14:30:00",
            },
            {
                "Id": "MSG-00006",
                "Id_Chamado": "CH-20260619-M10002",
                "Autor": "Marcos",
                "Autor_Tipo": "funcionario",
                "Mensagem": (
                    "Olá Maria. Recebemos sua solicitação e já estamos analisando os "
                    "resultados do Motor M-10. Identificamos que o índice de viscosidade "
                    "está no limite superior. Retornaremos com o parecer técnico completo "
                    "até amanhã."
                ),
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "resposta_predio",
                "Data": "19/06/2026 16:00:00",
            },
            {
                "Id": "MSG-00007",
                "Id_Chamado": "CH-20260619-M10002",
                "Autor": "Marcos",
                "Autor_Tipo": "funcionario",
                "Mensagem": (
                    "Nota interna: verificar se a última troca de óleo foi dentro do prazo. "
                    "O histórico indica 180 dias desde a última manutenção — acima do "
                    "recomendado para esse equipamento. Confirmar com o relatório anterior."
                ),
                "Visivel_Cliente": "0",
                "Tipo_Mensagem": "observacao_interna",
                "Data": "19/06/2026 16:05:00",
            },
        ],
        "CH-20260620-B204003": [
            {
                "Id": "MSG-00008",
                "Id_Chamado": "CH-20260620-B204003",
                "Autor": "joao@cocacola.com",
                "Autor_Tipo": "cliente",
                "Mensagem": (
                    "Bom dia. Após a última partida da Bomba B-204, notamos aumento "
                    "significativo na vibração. Verificamos na semana passada e estava "
                    "normal. Preciso de uma análise urgente."
                ),
                "Visivel_Cliente": "1",
                "Tipo_Mensagem": "mensagem_cliente",
                "Data": "20/06/2026 09:15:00",
            },
        ],
    }
    rows = mocks.get(chamado_id, [])
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ── Autenticação — verificação de e-mail e gravação de senha ─────────────────

def _digits(s: str) -> str:
    """Extrai apenas dígitos de uma string (para comparação de telefones)."""
    return re.sub(r"[^\d]", "", s)


def _match_row(df: pd.DataFrame, login: str):
    """Busca uma linha por e-mail OU telefone. Retorna Series ou None."""
    valor = login.strip().lower()
    if "Email" in df.columns:
        m = df[df["Email"].str.strip().str.lower() == valor]
        if not m.empty:
            return m.iloc[0]
    if "Telefone" in df.columns:
        digs = _digits(login)
        if digs:
            df2 = df.copy()
            df2["_tel"] = df2["Telefone"].astype(str).apply(_digits)
            m = df2[df2["_tel"] == digs]
            if not m.empty:
                return m.iloc[0]
    return None


def verificar_email(login: str) -> tuple:
    """Verifica se e-mail ou telefone existe na planilha.
    Retorna (existe: bool, primeiro_acesso: bool, dados: dict | None).
    Primeiro acesso = coluna Senha vazia ou com valor 'PRIMEIRO_ACESSO'.
    """
    for tab in ("Clientes", "Usuarios"):
        df = load_sheet(tab)
        if df.empty:
            continue
        row = _match_row(df, login)
        if row is None:
            continue
        senha    = str(row.get("Senha", "")).strip()
        primeiro = senha == "" or senha.upper() == "PRIMEIRO_ACESSO"
        return True, primeiro, row.to_dict()
    return False, False, None


def set_user_senha(login: str, senha_hash: str) -> bool:
    """Grava o hash da senha buscando por e-mail ou telefone. Retorna True se OK."""
    valor = login.strip().lower()
    digs  = _digits(login)
    for tab in ("Clientes", "Usuarios"):
        try:
            ss      = get_spreadsheet()
            ws      = ss.worksheet(tab)
            raw     = ws.row_values(1)
            headers = [h.strip().title() for h in raw]
            if "Senha" not in headers:
                continue
            senha_col = headers.index("Senha") + 1

            # Tenta por e-mail
            if "Email" in headers:
                email_col = headers.index("Email") + 1
                for row_num, v in enumerate(ws.col_values(email_col), start=1):
                    if row_num == 1:
                        continue
                    if v.strip().lower() == valor:
                        ws.update_cell(row_num, senha_col, senha_hash)
                        _clear_read_caches()
                        return True

            # Tenta por telefone
            if "Telefone" in headers and digs:
                tel_col = headers.index("Telefone") + 1
                for row_num, v in enumerate(ws.col_values(tel_col), start=1):
                    if row_num == 1:
                        continue
                    if _digits(v) == digs:
                        ws.update_cell(row_num, senha_col, senha_hash)
                        _clear_read_caches()
                        return True
        except Exception:
            continue
    return False


# ── Relatórios ────────────────────────────────────────────────────────────────

def get_relatorios(client_id: str, filtros: dict | None = None) -> pd.DataFrame:
    """Retorna relatórios do cliente. Filtra SEMPRE por client_id no servidor."""
    df = load_sheet("Relatorios")
    if df.empty:
        return df
    for col in ("Empresa", "Tipo_Servico", "Planta", "Equipamento", "Mes", "Ano",
                "Data_Relatorio", "Arquivo_Url", "Titulo", "Status"):
        if col not in df.columns:
            df[col] = ""
    df = df[df["Empresa"].str.strip().str.lower() == client_id.lower()].copy()
    if filtros:
        if filtros.get("tipo"):
            df = df[df["Tipo_Servico"].str.strip().str.lower() == filtros["tipo"].lower()]
        if filtros.get("planta"):
            df = df[df["Planta"].str.strip().str.lower() == filtros["planta"].lower()]
        if filtros.get("equipamento"):
            df = df[df["Equipamento"].str.lower().str.contains(
                filtros["equipamento"].lower(), na=False)]
        if filtros.get("mes"):
            df = df[df["Mes"].astype(str) == str(filtros["mes"])]
        if filtros.get("ano"):
            df = df[df["Ano"].astype(str) == str(filtros["ano"])]
    if "Data_Relatorio" in df.columns:
        df["_dt"] = pd.to_datetime(
            df["Data_Relatorio"].astype(str), dayfirst=True, errors="coerce")
        df = df.sort_values("_dt", ascending=False).drop(columns=["_dt"])
    return df.reset_index(drop=True)


# ── Ativos ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=20, show_spinner=False)
def get_ativos(client_id: str) -> pd.DataFrame:
    df = load_sheet("Ativos")
    if df.empty:
        return df
    if "Empresa" not in df.columns:
        return df.copy()
    return df[df["Empresa"].str.strip().str.lower() == client_id.lower()].copy()


# ── Delete genérico ──────────────────────────────────────────────────────────

def delete_row_by_id(tab_name: str, id_col: str, row_id: str) -> bool:
    """Remove uma linha de uma aba pelo valor do campo id_col."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet(tab_name)
        headers = ws.row_values(1)
        if id_col not in headers:
            return False
        col_idx = headers.index(id_col) + 1
        all_vals = ws.col_values(col_idx)
        for row_num, v in enumerate(all_vals, start=1):
            if row_num == 1:
                continue
            if str(v).strip() == str(row_id).strip():
                ws.delete_rows(row_num)
                _clear_read_caches()
                return True
        return False
    except Exception:
        return False


def delete_ativo_sv(ativo_id: str) -> bool:
    return delete_row_by_id("Ativos", "Id", ativo_id)


def delete_ativos_por_cliente(client_id: str) -> int:
    """Remove todos os ativos de um cliente. Usado ao excluir o cliente
    (cascade delete). Retorna a quantidade de ativos removidos."""
    cid = client_id.strip().lower()
    if not cid:
        return 0
    df = load_sheet("Ativos")
    if df.empty or "Client_Id" not in df.columns:
        return 0
    ids = df[df["Client_Id"].astype(str).str.strip().str.lower() == cid]["Id"].tolist()
    removidos = 0
    for ativo_id in ids:
        if delete_ativo_sv(str(ativo_id).strip()):
            removidos += 1
    return removidos


def delete_usuario(email: str) -> bool:
    """Remove usuário da aba Usuarios ou Clientes pelo e-mail."""
    valor = email.strip().lower()
    try:
        ss = get_spreadsheet()
        for tab in ("Usuarios", "Clientes"):
            try:
                ws = ss.worksheet(tab)
                headers = ws.row_values(1)
                if "Email" not in headers:
                    continue
                email_col = headers.index("Email") + 1
                for row_num, v in enumerate(ws.col_values(email_col), start=1):
                    if row_num == 1:
                        continue
                    if str(v).strip().lower() == valor:
                        ws.delete_rows(row_num)
                        _clear_read_caches()
                        return True
            except Exception:
                continue
        return False
    except Exception:
        return False


# ── Alertas de Supervisão (Pontos de Atenção manuais) ────────────────────────

_HEADERS_ALERTAS_SV = [
    "Id", "Client_Id", "Empresa", "Titulo", "Descricao", "Prioridade",
    "Criado_Em", "Whatsapp", "Ativo_Id",
    # GUT — ver _HEADERS_GUT / gut.py
    "Gut_Gravidade", "Gut_Urgencia", "Gut_Tendencia",
    "Gut_Score", "Gut_Prioridade", "Gut_Observacao",
    # Resolução (Etapa timeline/comparativo) — alertas antigos sem estas
    # colunas têm Status="" (tratado como não-resolvido, mesmo comportamento
    # de antes desta coluna existir).
    "Status", "Resolvido_Em", "Resolvido_Por",
]


@st.cache_data(ttl=20, show_spinner=False)
def get_alertas_sv(client_id: str | None = None, incluir_resolvidos: bool = False) -> pd.DataFrame:
    """Alertas criados pela supervisão. Filtra por client_id se fornecido.

    incluir_resolvidos=False (padrão, mesmo comportamento de antes da coluna
    Status existir): esconde alertas com Status=="Resolvido" — a lista
    principal de alertas continua mostrando só os ativos/não resolvidos.
    Quem precisa do histórico completo (timeline, comparativo) passa True.
    """
    df = load_sheet("AlertasSV")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_ALERTAS_SV:
        if col not in df.columns:
            df[col] = ""
    if client_id:
        df = df[df["Client_Id"].str.strip().str.lower() == client_id.strip().lower()]
    if not incluir_resolvidos:
        df = df[df["Status"].astype(str).str.strip() != "Resolvido"]
    return df.reset_index(drop=True)


def add_alerta_sv(client_id: str, empresa: str, titulo: str,
                  descricao: str, prioridade: str, whatsapp: str = "",
                  ativo_id: str = "") -> str | None:
    """Adiciona um alerta manual de supervisão. Retorna o Id gerado ou None
    em falha (continua "truthy" em `if add_alerta_sv(...):`, compatível com
    chamadores existentes que só checavam sucesso/falha)."""
    _ensure_tab_headers("AlertasSV", _HEADERS_ALERTAS_SV)
    _ensure_extra_cols("AlertasSV", ["Status", "Resolvido_Em", "Resolvido_Por"])
    alerta_id = _gerar_id("ALS")
    ok = append_row("AlertasSV", [
        alerta_id, client_id.strip().lower(), empresa,
        titulo, descricao, prioridade,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        whatsapp.strip(), ativo_id.strip(),
        "", "", "", "", "", "",  # Gut_* — preenchidos depois via update_alerta_gut, se houver
        "", "", "",              # Status, Resolvido_Em, Resolvido_Por
    ])
    if ok and ativo_id.strip():
        try:
            add_report_timeline_event({
                "ativo_id": ativo_id.strip(), "cliente_id": client_id.strip().lower(),
                "tipo": "alerta_gerado", "titulo": titulo, "descricao": descricao,
                "origem": "Alertas", "visivel_cliente": "true",
            })
        except Exception:
            pass
    return alerta_id if ok else None


def delete_alerta_sv(alerta_id: str) -> bool:
    return delete_row_by_id("AlertasSV", "Id", alerta_id)


def resolver_alerta_sv(alerta_id: str, resolvido_por: str = "") -> bool:
    """Marca um alerta como Resolvido (soft — não apaga a linha, diferente de
    delete_alerta_sv). Alerta resolvido some da lista principal
    (get_alertas_sv padrão) mas continua visível na timeline/comparativo/
    histórico. Grava evento alerta_resolvido na timeline do ativo, se houver."""
    _ensure_extra_cols("AlertasSV", ["Status", "Resolvido_Em", "Resolvido_Por"])
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("AlertasSV")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        cell = ws.find(alerta_id, in_column=headers.index("Id") + 1)
        if not cell:
            return False
        row_vals = ws.row_values(cell.row)

        def _get(col):
            idx = headers.index(col) if col in headers else -1
            return row_vals[idx] if 0 <= idx < len(row_vals) else ""

        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        for campo, valor in {
            "Status": "Resolvido", "Resolvido_Em": agora, "Resolvido_Por": resolvido_por,
        }.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, valor)
        _clear_read_caches()

        ativo_id = _get("Ativo_Id").strip()
        if ativo_id:
            try:
                add_report_timeline_event({
                    "ativo_id": ativo_id, "cliente_id": _get("Client_Id"),
                    "tipo": "alerta_resolvido", "titulo": _get("Titulo"),
                    "descricao": _get("Descricao"),
                    "origem": "Alertas", "visivel_cliente": "true",
                })
            except Exception:
                pass
        return True
    except Exception:
        return False


# ── Biblioteca Técnica ────────────────────────────────────────────────────────

_HEADERS_BIBLIOTECA = [
    "Id", "Titulo", "Tipo_Documento", "Cliente_Id", "Planta_Id",
    "Ativo_Id", "Componente_Id", "Fabricante", "Modelo", "Numero_Serie",
    "Arquivo_Url", "Arquivo_Nome", "Resumo", "Palavras_Chave",
    "Visibilidade", "Status", "Observacoes_Internas",
    "Texto_Extraido", "Embedding_Id", "Data_Indexacao",
    # Indexado_Para_Ia é o nome REAL já em produção na planilha (não
    # "Status_Indexacao" — um nome que o código usava mas nunca existiu
    # de verdade na aba, fazendo toda atualização de status ser
    # silenciosamente ignorada por update_status_indexacao). BUG CORRIGIDO
    # (nº 2): a planilha tinha o cabeçalho escrito "Indexado_Para_IA"
    # (com "IA" maiúsculo), mas load_sheet() normaliza todo nome de coluna
    # com `.strip().title()` — e `"Indexado_Para_IA".title()` vira
    # "Indexado_Para_Ia" ("IA" perde a maiúscula do segundo caractere).
    # Isso fazia o DataFrame nunca ter uma coluna com esse nome exato,
    # então get_documentos_tecnicos() sempre injetava uma coluna em
    # branco por cima do dado real. Corrigido o CABEÇALHO da planilha
    # (só o rótulo, sem tocar em dado nenhum) para já nascer com a grafia
    # que .title() produz — evita manter duas grafias (uma para leitura
    # via DataFrame, outra para escrita via ws.update_cell) em paralelo.
    # Fonte_Original já existe na planilha real, sem uso até agora.
    "Indexado_Para_Ia", "Fonte_Original",
    # Erro_Indexacao/Quantidade_Paginas/Origem_Arquivo NÃO existem ainda na
    # planilha real — criadas via _ensure_extra_cols quando necessário.
    "Erro_Indexacao", "Quantidade_Paginas", "Origem_Arquivo",
    "Created_At", "Updated_At",
    # Etapa Assistente/Biblioteca no chat — aditivos:
    # Storage_Path: path privado no GCS (drive_storage.upload_document_pdf),
    # usado só por uploads NOVOS — documentos antigos continuam só com
    # Arquivo_Url (URL assinada de ~10 anos, sem como tornar privada
    # retroativamente).
    "Storage_Path",
    # Uso_Pela_Ia: ausente/branco = permitido (preserva o comportamento
    # atual, onde todo documento "Ativo" já é usado pelo Assistente).
    "Uso_Pela_Ia",
]

_HEADERS_CHUNKS = [
    "Id", "Documento_Id", "Cliente_Id", "Ativo_Id", "Componente_Id",
    "Chunk_Index", "Pagina_Inicio", "Pagina_Fim", "Titulo_Secao",
    "Conteudo", "Palavras_Chave", "Created_At", "Updated_At",
]

_VIS_INTERNO = "Apenas equipe Pred.IO"


@st.cache_data(ttl=20, show_spinner=False)
def get_documentos_tecnicos(
    client_id: str | None = None,
    staff: bool = False,
) -> pd.DataFrame:
    """Retorna documentos da Biblioteca Técnica.

    SEGURANÇA:
      - client_id SEMPRE da sessão, nunca do front-end.
      - Para clientes (staff=False): exclui documentos internos e de outros clientes.
      - Para staff (staff=True): retorna todos os documentos.
      - Nunca inclui Observacoes_Internas na resposta ao cliente (chamador deve omitir).
    """
    df = load_sheet("BibliotecaTecnica")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_BIBLIOTECA:
        if col not in df.columns:
            df[col] = ""

    # Texto_Extraido nunca é usado nas telas de listagem (Portal ou
    # Supervisão) — só a busca via DocumentoChunks/buscar_chunks() precisa
    # do texto completo, um mecanismo separado. Tirar daqui (client e staff)
    # evita carregar o texto inteiro de todo documento só pra listar título/
    # fabricante.
    if "Texto_Extraido" in df.columns:
        df = df.drop(columns=["Texto_Extraido"])

    if staff:
        return df.reset_index(drop=True)

    # Filtros de segurança para clientes
    df = df[df["Status"].str.strip() == "Ativo"]
    df = df[df["Visibilidade"].str.strip() != _VIS_INTERNO]

    if client_id:
        cid = client_id.strip().lower()
        vis = df["Visibilidade"].str.strip()
        mask_publico = vis == "Público para clientes autorizados"
        mask_cliente = (vis == "Vinculado a cliente específico") & (
            df["Cliente_Id"].str.strip().str.lower() == cid
        )
        # "Vinculado a ativo específico": não existia nenhuma resolução
        # ativo→cliente — só "funcionava" se o Cliente_Id também tivesse
        # sido preenchido à parte (não garantido pelo formulário). Resolve
        # de verdade agora: pega os ativos que pertencem a este cliente e
        # libera os documentos vinculados a qualquer um deles.
        try:
            ativos_do_cliente = set(get_ativos(client_id)["Id"].astype(str).str.strip())
        except Exception:
            ativos_do_cliente = set()
        mask_ativo = (vis == "Vinculado a ativo específico") & (
            df["Ativo_Id"].astype(str).str.strip().isin(ativos_do_cliente)
        )
        df = df[mask_publico | mask_cliente | mask_ativo]

    # Nunca expõe observações internas para clientes
    if "Observacoes_Internas" in df.columns:
        df = df.drop(columns=["Observacoes_Internas"])

    return df.reset_index(drop=True)


def add_documento_tecnico(dados: dict) -> str | None:
    """Cadastra novo documento técnico. Retorna o Id criado ou None em caso de erro.

    BUG CORRIGIDO: esta função gravava a linha por POSIÇÃO (append_row com
    uma lista fixa), assumindo uma ordem de colunas que não bate com a
    planilha real — Created_At ficava sempre em branco e Storage_Path/
    Uso_Pela_Ia recebiam o timestamp que deveria ir em Created_At/
    Updated_At. Agora a linha é montada por NOME, lendo o cabeçalho real
    da planilha — imune a colunas fora de ordem ou extras (ex.:
    Fonte_Original, que existe na planilha mas não em _HEADERS_BIBLIOTECA
    até esta etapa)."""
    _ensure_tab_headers("BibliotecaTecnica", _HEADERS_BIBLIOTECA)
    _ensure_extra_cols("BibliotecaTecnica", _HEADERS_BIBLIOTECA)
    doc_id = _gerar_id("DOC")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    valores_por_coluna = {
        "Id":                   doc_id,
        "Titulo":               dados.get("titulo",               ""),
        "Tipo_Documento":       dados.get("tipo_documento",        ""),
        "Cliente_Id":           dados.get("cliente_id",            ""),
        "Planta_Id":            dados.get("planta_id",             ""),
        "Ativo_Id":             dados.get("ativo_id",              ""),
        "Componente_Id":        dados.get("componente_id",         ""),
        "Fabricante":           dados.get("fabricante",            ""),
        "Modelo":               dados.get("modelo",                ""),
        "Numero_Serie":         dados.get("numero_serie",          ""),
        "Arquivo_Url":          dados.get("arquivo_url",           ""),
        "Arquivo_Nome":         dados.get("arquivo_nome",          ""),
        "Resumo":               dados.get("resumo",                ""),
        "Palavras_Chave":       dados.get("palavras_chave",        ""),
        "Visibilidade":         dados.get("visibilidade",          "Vinculado a cliente específico"),
        "Status":               dados.get("status",                "Ativo"),
        "Observacoes_Internas": dados.get("observacoes_internas",  ""),
        "Texto_Extraido":       "",
        "Embedding_Id":         "",
        "Data_Indexacao":       "",
        "Indexado_Para_Ia":     "Não indexado",
        "Fonte_Original":       dados.get("fonte_original",        ""),
        "Erro_Indexacao":       "",
        "Quantidade_Paginas":   "",
        "Origem_Arquivo":       dados.get("origem_arquivo",        ""),
        "Created_At":           now,
        "Updated_At":           now,
        "Storage_Path":         dados.get("storage_path",          ""),
        "Uso_Pela_Ia":          "",
    }
    ss = get_spreadsheet()
    ws = ss.worksheet("BibliotecaTecnica")
    headers_reais = ws.row_values(1)
    linha = [valores_por_coluna.get(col, "") for col in headers_reais]
    ok = append_row("BibliotecaTecnica", linha)
    return doc_id if ok else None


def update_documento_tecnico(doc_id: str, campos: dict) -> bool:
    """Atualiza campos de um documento técnico (ex.: Storage_Path após
    upload, Arquivo_Nome). Mesmo padrão de update_technical_report."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("BibliotecaTecnica")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(doc_id, in_column=id_col)
        if not cell:
            return False
        campos = dict(campos)
        campos.setdefault("Updated_At", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        _clear_read_caches()
        return True
    except Exception:
        return False


def delete_documento_tecnico(doc_id: str) -> bool:
    return delete_row_by_id("BibliotecaTecnica", "Id", doc_id)


def update_status_indexacao(
    doc_id: str,
    status: str,
    texto_extraido: str = "",
    quantidade_paginas: int = 0,
    erro: str = "",
) -> bool:
    """Atualiza campos de indexação de um documento na BibliotecaTecnica.

    BUG CORRIGIDO: escrevia em "Status_Indexacao", um nome que nunca
    existiu na planilha real (a coluna real, após corrigir também a
    grafia do cabeçalho — ver comentário em _HEADERS_BIBLIOTECA — é
    "Indexado_Para_Ia") — a escrita do status era sempre ignorada
    silenciosamente (só grava `if col_name in headers`). Chunks eram
    criados normalmente, mas o status ficava "Não indexado" pra sempre."""
    _ensure_extra_cols("BibliotecaTecnica", ["Erro_Indexacao", "Quantidade_Paginas"])
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("BibliotecaTecnica")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        all_ids = ws.col_values(id_col)
        for row_num, v in enumerate(all_ids, start=1):
            if row_num == 1:
                continue
            if str(v).strip() == doc_id.strip():
                now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                updates = {
                    "Indexado_Para_Ia":  status,
                    "Erro_Indexacao":    erro,
                    "Data_Indexacao":    now,
                    "Updated_At":        now,
                }
                if texto_extraido:
                    updates["Texto_Extraido"] = texto_extraido[:5000]
                if quantidade_paginas:
                    updates["Quantidade_Paginas"] = str(quantidade_paginas)
                for col_name, value in updates.items():
                    if col_name in headers:
                        ws.update_cell(row_num, headers.index(col_name) + 1, value)
                _clear_read_caches()
                return True
        return False
    except Exception:
        return False


# ── DocumentoChunks ───────────────────────────────────────────────────────────

def get_chunks_documento(doc_id: str) -> pd.DataFrame:
    """Retorna todos os chunks de um documento."""
    df = load_sheet("DocumentoChunks")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_CHUNKS:
        if col not in df.columns:
            df[col] = ""
    df = df[df["Documento_Id"].str.strip() == doc_id.strip()]
    return df.reset_index(drop=True)


def buscar_chunks_documentos(client_id: str, query: str, top_n: int = 5) -> list[dict]:
    """Busca textual nos chunks da Biblioteca Técnica mantendo o
    Documento_Id em cada resultado — diferente de buscar_chunks()/
    get_chunks_para_assistente() (que removem o id para o payload minimizado
    do assistente em JS). Usada para "qual documento fala sobre X",
    onde é preciso saber DE QUAL documento o trecho encontrado veio.

    SEGURANÇA: filtra pelos documentos já autorizados para o client_id via
    get_documentos_tecnicos(staff=False) — nunca lê DocumentoChunks direto
    sem esse filtro (documentos internos/de outro cliente não entram)."""
    import re as _re
    import unicodedata as _ud

    def _norm(s: str) -> str:
        n = _ud.normalize("NFD", s.lower())
        return _re.sub(r"[̀-ͯ]", "", n)

    docs_permitidos = get_documentos_tecnicos(client_id=client_id, staff=False)
    if docs_permitidos.empty or "Id" not in docs_permitidos.columns:
        return []
    ids_permitidos = set(docs_permitidos["Id"].astype(str).str.strip())

    df = load_sheet("DocumentoChunks")
    if df.empty:
        return []
    for col in _HEADERS_CHUNKS:
        if col not in df.columns:
            df[col] = ""
    df = df[df["Documento_Id"].astype(str).str.strip().isin(ids_permitidos)]
    if df.empty:
        return []

    terms = [t for t in _norm(query).split() if len(t) > 2]
    scored = []
    for _, row in df.iterrows():
        conteudo = str(row.get("Conteudo", "")).strip()
        if not conteudo:
            continue
        item = {
            "documento_id": str(row.get("Documento_Id", "")).strip(),
            "titulo_secao": str(row.get("Titulo_Secao", "")).strip(),
            "conteudo": conteudo,
            "palavras_chave": str(row.get("Palavras_Chave", "")).strip(),
        }
        if not terms:
            scored.append((0, item))
            continue
        haystack = _norm(item["titulo_secao"] + " " + conteudo + " " + item["palavras_chave"])
        score = sum(1 for t in terms if t in haystack)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_n]]


def add_chunks_lote(chunks: list[dict]) -> bool:
    """Salva uma lista de chunks. Retorna True se bem-sucedido."""
    if not chunks:
        return True
    _ensure_tab_headers("DocumentoChunks", _HEADERS_CHUNKS)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    rows = []
    for c in chunks:
        rows.append([
            _gerar_id("CHK"),
            c.get("documento_id",  ""),
            c.get("cliente_id",    ""),
            c.get("ativo_id",      ""),
            c.get("componente_id", ""),
            str(c.get("chunk_index",   "")),
            str(c.get("pagina_inicio", "")),
            str(c.get("pagina_fim",    "")),
            c.get("titulo_secao",  ""),
            c.get("conteudo",      ""),
            c.get("palavras_chave",""),
            now, now,
        ])
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("DocumentoChunks")
        ws.append_rows(rows, value_input_option="USER_ENTERED")
        _clear_read_caches()
        return True
    except Exception:
        return False


def get_chunks_para_assistente(client_id: str, limit: int = 60) -> list[dict]:
    """Retorna chunks indexados acessíveis ao cliente para busca no assistente JS.

    SEGURANÇA: client_id deve vir da sessão, nunca do front-end.
    Retorna apenas campos mínimos (sem doc_id, client_id completo etc.)
    para reduzir o payload JS injetado na página.
    """
    df = load_sheet("DocumentoChunks")
    if df.empty:
        return []
    for col in _HEADERS_CHUNKS:
        if col not in df.columns:
            df[col] = ""
    cid = (client_id or "").strip().lower()
    mask = (
        df["Cliente_Id"].str.strip().str.lower() == cid
    ) | (
        df["Cliente_Id"].str.strip() == ""
    )
    df = df[mask].head(limit)
    result = []
    for _, row in df.iterrows():
        conteudo = str(row.get("Conteudo", "")).strip()
        if not conteudo:
            continue
        result.append({
            "t": str(row.get("Titulo_Secao",  "")).strip()[:80],
            "c": conteudo[:500],
            "k": str(row.get("Palavras_Chave","")).strip()[:200],
        })
    return result


def buscar_chunks(client_id: str, query: str, top_n: int = 5) -> list[dict]:
    """Busca textual simples nos chunks indexados de um cliente.

    Retorna até top_n chunks com maior sobreposição de termos com a query.
    Usado pela área de supervisão no botão 'Testar no Assistente'.
    """
    import unicodedata
    import re as _re

    def _norm(s: str) -> str:
        n = unicodedata.normalize("NFD", s.lower())
        return _re.sub(r"[̀-ͯ]", "", n)

    chunks = get_chunks_para_assistente(client_id, limit=200)
    if not chunks:
        return []
    terms = [t for t in _norm(query).split() if len(t) > 2]
    if not terms:
        return chunks[:top_n]
    scored = []
    for ch in chunks:
        haystack = _norm(ch.get("t", "") + " " + ch.get("c", "") + " " + ch.get("k", ""))
        score = sum(1 for t in terms if t in haystack)
        if score > 0:
            scored.append((score, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [ch for _, ch in scored[:top_n]]


# ── AssistantLogs ─────────────────────────────────────────────────────────────

_HEADERS_LOGS = [
    "Id", "Usuario_Id", "Cliente_Id", "Ativo_Id", "Documento_Id",
    "Pergunta", "Resposta", "Fonte", "Chunks_Usados", "Confidence",
    "Origem_Resposta", "Avaliacao_Interna", "Observacao_Interna", "Created_At",
]


def save_assistant_log(
    usuario_id: str,
    cliente_id: str,
    ativo_id: str,
    documento_id: str,
    pergunta: str,
    resposta: str,
    fonte: str,
    chunks_usados: str,
    confidence: str,
    origem_resposta: str,
) -> str:
    """Salva log de interação do assistente na aba AssistantLogs."""
    log_id = _gerar_id("LOG")
    agora  = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("AssistantLogs")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(
                title="AssistantLogs", rows=2000, cols=len(_HEADERS_LOGS)
            )
            ws.append_row(_HEADERS_LOGS, value_input_option="USER_ENTERED")
        ws.append_row(
            [log_id, usuario_id, cliente_id, ativo_id, documento_id,
             pergunta, resposta, fonte, chunks_usados, confidence,
             origem_resposta, "Não avaliada", "", agora],
            value_input_option="USER_ENTERED",
        )
        _clear_read_caches()
    except Exception as _e:
        import logging
        logging.error("save_assistant_log: %s", _e)
    return log_id


def get_assistant_logs(limit: int = 100) -> pd.DataFrame:
    """Retorna logs do assistente (apenas para staff)."""
    df = load_sheet("AssistantLogs")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_LOGS:
        t = col.title()
        if t not in df.columns:
            df[t] = ""
    return df.iloc[-limit:].iloc[::-1].reset_index(drop=True)


# ── WebSearchLogs ─────────────────────────────────────────────────────────────

_HEADERS_WEB_SEARCH_LOGS = [
    "Id", "Cliente_Id", "Pergunta_Original", "Query_Limpa",
    "Provider", "Dominios", "N_Resultados", "Cache_Hit", "Erro", "Created_At",
]


def add_web_search_log(entry: dict) -> None:
    """Registra uma busca web no log de auditoria (apenas staff pode visualizar)."""
    try:
        ss  = get_spreadsheet()
        try:
            ws = ss.worksheet("WebSearchLogs")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(
                title="WebSearchLogs", rows=2000, cols=len(_HEADERS_WEB_SEARCH_LOGS)
            )
            ws.append_row(_HEADERS_WEB_SEARCH_LOGS, value_input_option="USER_ENTERED")
        log_id = _gerar_id("WSL")
        agora  = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ws.append_row([
            log_id,
            entry.get("cliente_id", ""),
            entry.get("pergunta_original", "")[:200],
            entry.get("query_limpa", "")[:200],
            entry.get("provider", ""),
            entry.get("dominios", "")[:300],
            entry.get("n_resultados", "0"),
            entry.get("cache_hit", "Não"),
            entry.get("erro", ""),
            agora,
        ], value_input_option="USER_ENTERED")
        _clear_read_caches()
    except Exception as _e:
        import logging
        logging.error("add_web_search_log: %s", _e)


def get_web_search_logs(limit: int = 50) -> "pd.DataFrame":
    """Retorna logs de busca web (apenas para staff)."""
    df = load_sheet("WebSearchLogs")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_WEB_SEARCH_LOGS:
        t = col.title()
        if t not in df.columns:
            df[t] = ""
    return df.iloc[-limit:].iloc[::-1].reset_index(drop=True)


def update_log_avaliacao(log_id: str, avaliacao: str, observacao: str = "") -> bool:
    """Atualiza avaliação interna de um log do assistente."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("AssistantLogs")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col_idx = headers.index("Id") + 1
        cell = ws.find(log_id, in_column=id_col_idx)
        if not cell:
            return False
        row_idx = cell.row
        if "Avaliacao_Interna" in headers:
            ws.update_cell(row_idx, headers.index("Avaliacao_Interna") + 1, avaliacao)
        if observacao and "Observacao_Interna" in headers:
            ws.update_cell(row_idx, headers.index("Observacao_Interna") + 1, observacao)
        _clear_read_caches()
        return True
    except Exception:
        return False


# ── AssistantFaq ──────────────────────────────────────────────────────────────

_HEADERS_FAQ = [
    "Id", "Pergunta", "Resposta", "Fonte", "Categoria", "Palavras_Chave",
    "Ativo_Id", "Documento_Id", "Status", "Created_At", "Updated_At",
]


def save_assistant_faq(
    pergunta: str,
    resposta: str,
    categoria: str,
    palavras_chave: str,
    ativo_id: str = "",
    documento_id: str = "",
) -> str:
    """Salva nova pergunta frequente na aba AssistantFaq."""
    faq_id = _gerar_id("FAQ")
    agora  = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("AssistantFaq")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(
                title="AssistantFaq", rows=1000, cols=len(_HEADERS_FAQ)
            )
            ws.append_row(_HEADERS_FAQ, value_input_option="USER_ENTERED")
        ws.append_row(
            [faq_id, pergunta, resposta, "Pred.IO", categoria, palavras_chave,
             ativo_id, documento_id, "Ativa", agora, agora],
            value_input_option="USER_ENTERED",
        )
        _clear_read_caches()
    except Exception as _e:
        import logging
        logging.error("save_assistant_faq: %s", _e)
    return faq_id


def get_assistant_faq(status: str = "") -> pd.DataFrame:
    """Retorna perguntas frequentes do assistente."""
    df = load_sheet("AssistantFaq")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_FAQ:
        t = col.title()
        if t not in df.columns:
            df[t] = ""
    if status:
        df = df[df["Status"].str.strip() == status]
    return df.reset_index(drop=True)


def delete_chunks_documento(doc_id: str) -> bool:
    """Remove todos os chunks de um documento (antes de reprocessar)."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("DocumentoChunks")
        headers = ws.row_values(1)
        if "Documento_Id" not in headers:
            return True
        col_idx = headers.index("Documento_Id") + 1
        all_vals = ws.col_values(col_idx)
        to_delete = [
            i + 1 for i, v in enumerate(all_vals)
            if i > 0 and str(v).strip() == doc_id.strip()
        ]
        for row_num in reversed(to_delete):
            ws.delete_rows(row_num)
        _clear_read_caches()
        return True
    except Exception:
        return False


# ── Horímetros ───────────────────────────────────────────────────────────────

def get_horimetro(ativo_id: str) -> int | None:
    """Retorna o horímetro persistido de um ativo. None se não houver registro."""
    df = load_sheet("Horimetros")
    if df.empty or "Ativo_Id" not in df.columns:
        return None
    match = df[df["Ativo_Id"].astype(str).str.strip() == str(ativo_id).strip()]
    if match.empty:
        return None
    try:
        return int(float(str(match.iloc[-1]["Horimetro"])))
    except Exception:
        return None


def save_horimetro(ativo_id: str, horimetro: int) -> bool:
    """Salva ou atualiza o horímetro de um ativo na aba Horimetros."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("Horimetros")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title="Horimetros", rows=1000, cols=5)
            ws.append_row(
                ["Ativo_Id", "Horimetro", "Atualizado_Em"],
                value_input_option="USER_ENTERED",
            )
        headers = ws.row_values(1)
        if not headers or "Ativo_Id" not in headers:
            ws.insert_row(
                ["Ativo_Id", "Horimetro", "Atualizado_Em"],
                index=1,
                value_input_option="USER_ENTERED",
            )
            headers = ws.row_values(1)

        id_col = headers.index("Ativo_Id") + 1
        h_col  = headers.index("Horimetro") + 1
        dt_col = headers.index("Atualizado_Em") + 1

        all_ids = ws.col_values(id_col)
        for row_num, v in enumerate(all_ids, start=1):
            if row_num == 1:
                continue
            if str(v).strip() == str(ativo_id).strip():
                ws.update_cell(row_num, h_col,  str(horimetro))
                ws.update_cell(row_num, dt_col, agora)
                _clear_read_caches()
                return True

        ws.append_row([ativo_id, horimetro, agora], value_input_option="USER_ENTERED")
        _clear_read_caches()
        return True
    except Exception:
        return False


# ── Chamados (cliente) ────────────────────────────────────────────────────────

def abrir_chamado(client_id: str, email: str, titulo: str, descricao: str,
                  planta: str, equipamento: str, prioridade: str,
                  empresa: str = "") -> bool:
    """Abre um novo chamado. Gera ID único."""
    chamado_id = _gerar_id("CH")
    empresa    = empresa or client_id
    return append_row("Chamados", [
        chamado_id, empresa, client_id, email, titulo, descricao,
        planta, equipamento, prioridade, "Aberto", "",
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "", "",
    ])


def get_chamados(client_id: str) -> pd.DataFrame:
    """Chamados do cliente — filtra por Client_Id da sessão."""
    df = load_sheet("Chamados")
    if df.empty:
        return df
    # Nova schema: coluna Client_Id
    if "Client_Id" in df.columns:
        return df[
            df["Client_Id"].str.strip().str.lower() == client_id.lower()
        ].reset_index(drop=True)
    # Schema antiga: coluna Empresa continha o client_id
    for col in ("Empresa", "Cliente"):
        if col in df.columns:
            return df[
                df[col].str.strip().str.lower() == client_id.lower()
            ].reset_index(drop=True)
    return pd.DataFrame()


# ── Chamados (supervisão) ─────────────────────────────────────────────────────

def get_all_chamados(filtros: dict | None = None) -> pd.DataFrame:
    """Retorna todos os chamados sem filtro de cliente (apenas para staff)."""
    df = load_sheet("Chamados")
    if df.empty:
        df = _mock_chamados()

    for col in ("Id", "Empresa", "Client_Id", "Email", "Titulo", "Descricao",
                "Planta", "Equipamento", "Prioridade", "Status", "Responsavel",
                "Data_Abertura", "Data_Atualizacao", "Data_Encerramento"):
        if col not in df.columns:
            df[col] = ""

    if filtros:
        if filtros.get("cliente"):
            df = df[df["Empresa"].str.strip().str.lower().str.contains(
                filtros["cliente"].lower(), na=False)]
        if filtros.get("planta"):
            df = df[df["Planta"].str.strip().str.lower().str.contains(
                filtros["planta"].lower(), na=False)]
        if filtros.get("equipamento"):
            df = df[df["Equipamento"].str.lower().str.contains(
                filtros["equipamento"].lower(), na=False)]
        if filtros.get("status"):
            df = df[df["Status"].str.strip().str.lower() == filtros["status"].lower()]
        if filtros.get("prioridade"):
            df = df[df["Prioridade"].str.strip().str.lower() == filtros["prioridade"].lower()]
        if filtros.get("responsavel"):
            r = filtros["responsavel"].lower()
            mask = (
                df["Responsavel"].str.strip().str.lower().str.contains(r, na=False) |
                (df["Responsavel"].str.strip() == "") & (r in ("sem responsável", "nenhum"))
            )
            df = df[mask]
        if filtros.get("texto"):
            t = filtros["texto"].lower()
            mask = (
                df["Titulo"].str.lower().str.contains(t, na=False) |
                df["Descricao"].str.lower().str.contains(t, na=False) |
                df["Equipamento"].str.lower().str.contains(t, na=False) |
                df["Empresa"].str.lower().str.contains(t, na=False)
            )
            df = df[mask]
        if filtros.get("data_ini"):
            df["_dt"] = pd.to_datetime(df["Data_Abertura"], dayfirst=True, errors="coerce")
            df = df[df["_dt"] >= pd.to_datetime(filtros["data_ini"])]
            df = df.drop(columns=["_dt"])
        if filtros.get("data_fim"):
            df["_dt"] = pd.to_datetime(df["Data_Abertura"], dayfirst=True, errors="coerce")
            df = df[df["_dt"] <= pd.to_datetime(filtros["data_fim"])]
            df = df.drop(columns=["_dt"])

    # Ordenar: mais recentes primeiro
    df["_dt"] = pd.to_datetime(df["Data_Abertura"], dayfirst=True, errors="coerce")
    df = df.sort_values("_dt", ascending=False).drop(columns=["_dt"])
    return df.reset_index(drop=True)


def get_chamado_by_id(chamado_id: str) -> dict | None:
    """Retorna um chamado específico pelo Id."""
    df = load_sheet("Chamados")
    if df.empty:
        df = _mock_chamados()
    if "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == str(chamado_id).strip()]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def delete_chamado(chamado_id: str) -> tuple[bool, str]:
    """
    Remove um chamado da planilha pelo Id.
    Retorna (True, "") em caso de sucesso ou (False, mensagem_erro).
    """
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Chamados")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False, "Coluna 'Id' não encontrada na aba Chamados."
        col_idx = headers.index("Id") + 1
        all_vals = ws.col_values(col_idx)
        for row_num, v in enumerate(all_vals, start=1):
            if row_num == 1:
                continue
            if str(v).strip() == str(chamado_id).strip():
                ws.delete_rows(row_num)
                _clear_read_caches()
                return True, ""
        return False, f"Chamado '{chamado_id}' não encontrado na planilha."
    except Exception as exc:
        return False, str(exc)


def update_chamado(chamado_id: str, campos: dict) -> bool:
    """Atualiza campos de um chamado existente."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Chamados")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(chamado_id, in_column=id_col)
        if not cell:
            return False
        row_idx = cell.row
        campos  = dict(campos)
        campos["Data_Atualizacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        for campo, valor in campos.items():
            if campo in headers:
                col_idx = headers.index(campo) + 1
                ws.update_cell(row_idx, col_idx, str(valor))
        _clear_read_caches()
        return True
    except Exception:
        return False


# ── Mensagens de chamado ──────────────────────────────────────────────────────

def get_mensagens_chamado(chamado_id: str) -> pd.DataFrame:
    """Todas as mensagens de um chamado (incluindo internas — só para staff)."""
    df = load_sheet("ChamadoMensagens")
    if df.empty:
        return _mock_mensagens(chamado_id)
    if "Id_Chamado" not in df.columns:
        return pd.DataFrame()
    df = df[df["Id_Chamado"].astype(str).str.strip() == str(chamado_id).strip()].copy()
    if df.empty:
        return df
    df["_dt"] = pd.to_datetime(df.get("Data", pd.Series(dtype=str)),
                               dayfirst=True, errors="coerce")
    return df.sort_values("_dt", ascending=True).drop(columns=["_dt"]).reset_index(drop=True)


def get_mensagens_visiveis_cliente(chamado_id: str,
                                   client_id: str = "") -> pd.DataFrame:
    """
    Mensagens visíveis ao cliente (Visivel_Cliente = 1).

    SEGURANÇA:
    - Se client_id fornecido, valida ownership do chamado antes de retornar.
    - Nunca retorna mensagens com Visivel_Cliente != "1".
    - Nunca retorna observações internas (Tipo_Mensagem == observacao_interna).
    """
    # Validação de ownership: chamado deve pertencer ao cliente
    if client_id:
        row = get_chamado_v2_by_id(chamado_id, client_id=client_id)
        if row is None:
            return pd.DataFrame()  # chamado não pertence ao cliente — retorna vazio

    df = get_mensagens_chamado(chamado_id)
    if df.empty:
        return df

    # Filtro 1: apenas mensagens com Visivel_Cliente = 1
    if "Visivel_Cliente" in df.columns:
        df = df[df["Visivel_Cliente"].astype(str).str.strip() == "1"]

    # Filtro 2: nunca exibir observações internas mesmo que Visivel_Cliente = 1 (defesa)
    if "Tipo_Mensagem" in df.columns:
        df = df[df["Tipo_Mensagem"].str.strip().str.lower() != "observacao_interna"]

    return df.reset_index(drop=True)


def add_mensagem(chamado_id: str, autor: str, autor_tipo: str,
                 mensagem: str, visivel_cliente: bool,
                 tipo_mensagem: str) -> bool:
    """Adiciona uma mensagem ao chamado."""
    msg_id = _gerar_id("MSG")
    return append_row("ChamadoMensagens", [
        msg_id, chamado_id, autor, autor_tipo, mensagem,
        "1" if visivel_cliente else "0", tipo_mensagem,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    ])


# ── Clientes (supervisão) ─────────────────────────────────────────────────────

def get_all_clientes() -> pd.DataFrame:
    """Lista de clientes distintos — para área de supervisão."""
    df = load_sheet("Clientes")
    if df.empty:
        df = load_sheet("Usuarios")

    if not df.empty:
        if "Perfil" in df.columns:
            df = df[df["Perfil"].str.strip().str.lower() == "cliente"]
        cols_needed = [c for c in ("Empresa", "Client_Id", "Email", "Nome", "Telefone", "Perfil") if c in df.columns]
        df = df[cols_needed].drop_duplicates().reset_index(drop=True)
        if "Client_Id" not in df.columns and "Empresa" in df.columns:
            df["Client_Id"] = df["Empresa"].str.strip().str.lower()
        return df

    # Fallback: derivar de chamados
    df_cham = load_sheet("Chamados")
    if df_cham.empty:
        df_cham = _mock_chamados()
    if "Empresa" in df_cham.columns:
        clientes = (
            df_cham[["Empresa", "Client_Id", "Email"]]
            .drop_duplicates(subset=["Client_Id"])
            .reset_index(drop=True)
        )
        return clientes
    return pd.DataFrame()


@st.cache_data(ttl=30)
def get_usuarios_staff() -> list:
    """Retorna lista de dicts com nome, email, perfil e empresa dos usuários não-cliente."""
    df = load_sheet("Usuarios")
    if df.empty or "Perfil" not in df.columns:
        return []
    mask = df["Perfil"].str.strip().str.lower().isin(["funcionario", "admin"])
    df_staff = df[mask].copy()
    resultado = []
    for _, row in df_staff.iterrows():
        resultado.append({
            "nome":    str(row.get("Nome",    "")).strip(),
            "email":   str(row.get("Email",   "")).strip(),
            "perfil":  str(row.get("Perfil",  "")).strip().lower(),
            "empresa": str(row.get("Empresa", "")).strip(),
        })
    return resultado


@st.cache_data(ttl=30)
def get_contagem_usuarios_global() -> dict:
    """Retorna {"cliente": N, "funcionario": M, "admin": K} com totais globais do sistema."""
    df = load_sheet("Usuarios")
    if df.empty or "Perfil" not in df.columns:
        return {"cliente": 0, "funcionario": 0, "admin": 0}
    contagem: dict = {"cliente": 0, "funcionario": 0, "admin": 0}
    for perfil in df["Perfil"].str.strip().str.lower():
        if perfil in contagem:
            contagem[perfil] += 1
    return contagem


def cadastrar_usuario(empresa: str, email: str, telefone: str,
                      perfil: str, nome: str, senha_hash: str = "") -> bool:
    """Adiciona um novo usuário na aba Usuarios."""
    return append_row("Usuarios", [empresa, email, senha_hash, telefone, perfil, nome])


def get_historico_cliente(client_id: str) -> dict:
    """Histórico completo de um cliente: chamados + relatórios."""
    chamados   = get_chamados(client_id)
    relatorios = get_relatorios(client_id)
    if chamados.empty:
        # tenta no mock — _mock_chamados() está vazio hoje (dados de teste
        # removidos), então "Client_Id" nem existe como coluna; sem esse
        # guard, todo cliente sem chamado real quebrava a página inteira.
        mock = _mock_chamados()
        if not mock.empty and "Client_Id" in mock.columns:
            chamados = mock[mock["Client_Id"].str.lower() == client_id.lower()].copy()
    return {
        "chamados":   chamados,
        "relatorios": relatorios,
    }


# ── Assistente / logs ─────────────────────────────────────────────────────────

_HEADERS_LOGS = [
    "Client_Id", "Email", "Pergunta", "Resposta", "Fontes",
    "Confidence", "Sources_Json", "Data_Hora",
]


def get_historico_assistente(client_id: str, limit: int = 20) -> pd.DataFrame:
    df = load_sheet("AssistenteLogs")
    if df.empty:
        return df
    # Garante colunas mínimas
    for col in ("Confidence", "Sources_Json"):
        if col not in df.columns:
            df[col] = ""
    for col_candidate in ("Client_Id", "Empresa"):
        if col_candidate in df.columns:
            df = df[df[col_candidate].str.strip().str.lower() == client_id.lower()]
            return df.tail(limit).iloc[::-1].reset_index(drop=True)
    return pd.DataFrame()


def get_logs_assistente_staff(limit: int = 100) -> pd.DataFrame:
    """Retorna os logs mais recentes do chat de PRODUÇÃO (AssistenteLogs,
    escrito por salvar_log_assistente()) de TODOS os clientes — uso
    exclusivo da Supervisão (chamador já protegido por require_staff()).

    Diferente de get_assistant_logs() (aba AssistantLogs, separada — é a
    ferramenta de teste/auditoria em page_sv_assistente.py, não reflete o
    chat real do cliente)."""
    df = load_sheet("AssistenteLogs")
    if df.empty:
        return df
    for col in ("Report_Ids_Usados", "Document_Ids_Usados",
                "Current_Report_Id", "Current_Document_Id",
                "Confidence", "Sources_Json"):
        if col not in df.columns:
            df[col] = ""
    return df.tail(limit).iloc[::-1].reset_index(drop=True)


def salvar_log_assistente(
    client_id: str,
    email: str,
    pergunta: str,
    resposta: str,
    fontes: str = "",
    confidence: str = "",
    sources_json: str = "",
    report_ids_usados: str = "",
    document_ids_usados: str = "",
    current_report_id: str = "",
    current_document_id: str = "",
    intent_detectada: str = "",
    tipo_relatorio_detectado: str = "",
    usou_resumo_tecnico: str = "",
) -> None:
    """report_ids_usados/document_ids_usados: Ids (separados por vírgula)
    dos relatórios/documentos que embasaram esta resposta — auditoria de
    fonte pro Assistente localizar/resumir Relatórios e Biblioteca no chat.
    current_report_id/current_document_id: qual ficou "atual" na sessão
    após esta pergunta (para acompanhar o contexto conversacional).
    intent_detectada/tipo_relatorio_detectado/usou_resumo_tecnico: para
    diagnosticar se o Assistente realmente usou resumo_tecnico de um
    relatório ao responder — sem isso não dá pra saber pela planilha se
    uma resposta "errada" foi por o resumo não existir ou por o robô nunca
    ter chegado a olhar o relatório certo.

    ORDEM DAS COLUNAS SEGUE O CABEÇALHO REAL DA PLANILHA — append_row()
    escreve por posição, não por nome. O cabeçalho original do chat de
    produção é Empresa/Email/Data/Pergunta/Resposta/Fontes (nessa ordem);
    Report_Ids_Usados/Document_Ids_Usados/Current_Report_Id/
    Current_Document_Id já existem como colunas extras desta etapa;
    Confidence/Sources_Json são novas aqui. BUG CORRIGIDO: uma versão
    anterior desta função escrevia confidence/sources_json ANTES da data,
    deslocando pergunta/resposta/fontes/data uma coluna para a direita e
    corrompendo Report_Ids_Usados/Document_Ids_Usados com dados errados —
    linhas antigas gravadas com esse bug não são migradas retroativamente."""
    _ensure_extra_cols("AssistenteLogs", [
        "Report_Ids_Usados", "Document_Ids_Usados",
        "Current_Report_Id", "Current_Document_Id",
        "Confidence", "Sources_Json",
        "Intent_Detectada", "Tipo_Relatorio_Detectado", "Usou_Resumo_Tecnico",
    ])
    append_row("AssistenteLogs", [
        client_id, email,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        pergunta, resposta, fontes,
        report_ids_usados, document_ids_usados,
        current_report_id, current_document_id,
        confidence, sources_json,
        intent_detectada, tipo_relatorio_detectado, usou_resumo_tecnico,
    ])


# ── Chats do Assistente Técnico — Novo chat / Apagar último chat ──────────
#
# Diferente de AssistenteLogs (log plano por pergunta, usado só para
# auditoria/"Ver histórico completo" — nunca tocado aqui), estas duas abas
# agrupam as mensagens em CONVERSAS que podem ser criadas e apagadas pelo
# usuário. AssistenteLogs continua sendo gravado normalmente em paralelo
# (trilha de auditoria permanente, sobrevive mesmo que o chat seja apagado).

_HEADERS_ASSISTANT_CHATS = [
    "Id", "Usuario_Id", "Cliente_Id", "Titulo",
    "Created_At", "Updated_At", "Last_Message_At",
    "Status", "Deleted_At", "Deleted_By",
]
_HEADERS_ASSISTANT_CHAT_MESSAGES = [
    "Id", "Chat_Id", "Usuario_Id", "Cliente_Id", "Role", "Content",
    "Report_Id", "Document_Id", "Created_At",
]


def _update_assistant_row_by_id(tab_name: str, row_id: str, campos: dict) -> bool:
    """Helper interno — acha a linha pelo Id e atualiza só os campos
    informados, por nome de coluna (nunca por posição). Mesmo padrão de
    update_technical_report(), restrito às duas abas de chat do Assistente."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet(tab_name)
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell = ws.find(row_id, in_column=id_col)
        if not cell:
            return False
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        _clear_read_caches()
        return True
    except Exception:
        return False


def create_assistant_chat(usuario_id: str, cliente_id: str, titulo: str = "Nova conversa") -> str | None:
    """Cria uma conversa vazia para o usuário/cliente da sessão.
    SEGURANÇA: usuario_id/cliente_id DEVEM vir da sessão — nunca de input livre."""
    usuario_id = (usuario_id or "").strip()
    cliente_id = (cliente_id or "").strip()
    if not usuario_id or not cliente_id:
        return None
    _ensure_tab_headers("AssistantChats", _HEADERS_ASSISTANT_CHATS)
    chat_id = _gerar_id("CHAT")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("AssistantChats", [
        chat_id, usuario_id, cliente_id, titulo,
        now, now, "", "Ativo", "", "",
    ])
    return chat_id if ok else None


def update_assistant_chat_titulo(chat_id: str, titulo: str) -> bool:
    return _update_assistant_row_by_id("AssistantChats", chat_id, {
        "Titulo": titulo,
        "Updated_At": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    })


def add_assistant_chat_message(
    chat_id: str, usuario_id: str, cliente_id: str, role: str, content: str,
    report_id: str = "", document_id: str = "",
) -> bool:
    """Grava uma mensagem (role='user'|'assistant') numa conversa existente
    e atualiza Last_Message_At/Updated_At do chat. SEGURANÇA: quem chama já
    validou que chat_id pertence a usuario_id/cliente_id (criado nesta
    mesma sessão) — esta função só grava, não decide propriedade."""
    if not chat_id or not usuario_id or not cliente_id:
        return False
    _ensure_tab_headers("AssistantChatMessages", _HEADERS_ASSISTANT_CHAT_MESSAGES)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("AssistantChatMessages", [
        _gerar_id("MSG"), chat_id, usuario_id, cliente_id, role, content,
        report_id, document_id, now,
    ])
    if ok:
        _update_assistant_row_by_id("AssistantChats", chat_id, {
            "Last_Message_At": now, "Updated_At": now,
        })
    return ok


def get_ultimo_chat_ativo(usuario_id: str, cliente_id: str) -> dict | None:
    """Retorna a conversa Ativa mais recente do usuário/cliente, ou None.
    SEGURANÇA: usuario_id/cliente_id sempre da sessão."""
    usuario_id = (usuario_id or "").strip().lower()
    cliente_id = (cliente_id or "").strip().lower()
    if not usuario_id or not cliente_id:
        return None
    df = load_sheet("AssistantChats")
    if df.empty:
        return None
    for col in _HEADERS_ASSISTANT_CHATS:
        if col not in df.columns:
            df[col] = ""
    df = df[
        (df["Usuario_Id"].astype(str).str.strip().str.lower() == usuario_id)
        & (df["Cliente_Id"].astype(str).str.strip().str.lower() == cliente_id)
        & (df["Status"].astype(str).str.strip() == "Ativo")
    ]
    if df.empty:
        return None
    df = df.copy()
    ordenar_por = "Last_Message_At" if df["Last_Message_At"].astype(str).str.strip().any() else "Updated_At"
    df["_dt"] = pd.to_datetime(df[ordenar_por].astype(str), dayfirst=True, errors="coerce")
    df = df.sort_values("_dt", ascending=False)
    row = df.iloc[0]
    return {col: str(row.get(col, "")).strip() for col in _HEADERS_ASSISTANT_CHATS}


def get_chat_messages(chat_id: str, usuario_id: str, cliente_id: str) -> pd.DataFrame:
    """Mensagens de uma conversa — SEMPRE filtra por Usuario_Id/Cliente_Id
    além do chat_id (nunca confia só no chat_id, mesma disciplina de
    get_chunks_relatorio/summarize_technical_report)."""
    df = load_sheet("AssistantChatMessages")
    if df.empty:
        return df
    for col in _HEADERS_ASSISTANT_CHAT_MESSAGES:
        if col not in df.columns:
            df[col] = ""
    df = df[
        (df["Chat_Id"].astype(str).str.strip() == (chat_id or "").strip())
        & (df["Usuario_Id"].astype(str).str.strip().str.lower() == (usuario_id or "").strip().lower())
        & (df["Cliente_Id"].astype(str).str.strip().str.lower() == (cliente_id or "").strip().lower())
    ]
    return df.reset_index(drop=True)


def delete_assistant_chat(chat_id: str, usuario_id: str, cliente_id: str) -> dict:
    """Apaga (soft delete) uma conversa do Assistente Técnico.

    SEGURANÇA: revalida que o chat pertence a usuario_id/cliente_id ANTES
    de qualquer alteração — nunca confia que o chat_id recebido já foi
    checado por quem chamou. Cliente A nunca apaga chat do Cliente B.

    Remove de fato as mensagens (AssistantChatMessages não é registro de
    auditoria — quem preserva isso é AssistenteLogs, não tocado aqui);
    marca o chat como Status="Excluído" (soft delete, com Deleted_At/
    Deleted_By) em vez de apagar a linha do chat.
    """
    chat_id = (chat_id or "").strip()
    usuario_id = (usuario_id or "").strip()
    cliente_id = (cliente_id or "").strip()
    if not chat_id or not usuario_id or not cliente_id:
        return {"ok": False, "erro": "Conversa não encontrada."}

    df = load_sheet("AssistantChats")
    if df.empty or "Id" not in df.columns:
        return {"ok": False, "erro": "Conversa não encontrada."}
    match = df[df["Id"].astype(str).str.strip() == chat_id]
    if match.empty:
        return {"ok": False, "erro": "Conversa não encontrada."}
    row = match.iloc[0]
    if (str(row.get("Usuario_Id", "")).strip().lower() != usuario_id.lower()
            or str(row.get("Cliente_Id", "")).strip().lower() != cliente_id.lower()):
        return {"ok": False, "erro": "Conversa não encontrada."}
    if str(row.get("Status", "")).strip() == "Excluído":
        return {"ok": False, "erro": "Esta conversa já foi apagada."}

    # Remove as mensagens desta conversa (mesmo padrão de delete_chunks_relatorio)
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("AssistantChatMessages")
        headers = ws.row_values(1)
        if "Chat_Id" in headers:
            col_idx = headers.index("Chat_Id") + 1
            all_vals = ws.col_values(col_idx)
            to_delete = [
                i + 1 for i, v in enumerate(all_vals)
                if i > 0 and str(v).strip() == chat_id
            ]
            for row_num in reversed(to_delete):
                ws.delete_rows(row_num)
            _clear_read_caches()
    except Exception:
        pass  # aba pode não existir ainda se o chat nunca teve mensagem

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = _update_assistant_row_by_id("AssistantChats", chat_id, {
        "Status": "Excluído", "Deleted_At": now, "Deleted_By": usuario_id,
        "Updated_At": now,
    })
    return {"ok": ok, "erro": None if ok else "Falha ao apagar a conversa."}


# ── Auditoria — Modo Admin "Ver como Cliente" ──────────────────────────────

_HEADERS_AUDIT = [
    "Id", "Usuario_Id", "Perfil_Usuario", "Cliente_Id",
    "Recurso_Tipo", "Recurso_Id", "Acao", "Resultado", "Created_At",
]


def log_audit(usuario_id: str, perfil_usuario: str, cliente_id: str,
              acao: str, recurso_tipo: str = "", recurso_id: str = "",
              resultado: str = "sucesso") -> bool:
    """Registra uma ação de auditoria (ex.: admin visualizando/editando
    dados de um cliente em modo preview). Nunca lança exceção para não
    interromper o fluxo principal por falha de log — falha silenciosa,
    só retorna False.
    """
    try:
        _ensure_tab_headers("AccessAuditLogs", _HEADERS_AUDIT)
        log_id = _gerar_id("AUD")
        return append_row("AccessAuditLogs", [
            log_id, usuario_id, perfil_usuario, cliente_id,
            recurso_tipo, recurso_id, acao, resultado,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        ])
    except Exception:
        return False


def get_audit_logs(cliente_id: str = "", limit: int = 200) -> pd.DataFrame:
    """Retorna logs de auditoria, mais recentes primeiro. Uso interno da
    Supervisão apenas — sem filtro de segurança de client_id porque quem
    chama já é staff (mesma regra de get_all_ativos_sv etc.)."""
    df = load_sheet("AccessAuditLogs")
    if df.empty:
        return df
    if cliente_id:
        cid = cliente_id.strip().lower()
        df = df[df["Cliente_Id"].astype(str).str.strip().str.lower() == cid]
    return df.iloc[::-1].head(limit).reset_index(drop=True)


# ── Ativos (supervisão) ──────────────────────────────────────────────────────

def get_all_ativos_sv(filtros: dict | None = None) -> pd.DataFrame:
    """Todos os ativos — sem filtro de cliente. Somente staff deve chamar."""
    df = load_sheet("Ativos")
    if df.empty:
        return df
    for col in ("Id", "Empresa", "Client_Id", "Planta", "Tag", "Tipo", "Modelo",
                "Ns", "Mb", "Inversor", "Analise_Oleo", "Status", "Score",
                "Criticidade", "Detalhes", "Observacoes_Internas", "Data", "Criado_Em"):
        if col not in df.columns:
            df[col] = ""
    if filtros:
        if filtros.get("cliente"):
            df = df[df["Empresa"].str.strip().str.lower().str.contains(
                filtros["cliente"].lower(), na=False)]
        if filtros.get("planta"):
            df = df[df["Planta"].str.strip().str.lower().str.contains(
                filtros["planta"].lower(), na=False)]
        if filtros.get("status"):
            df = df[df["Status"].str.strip().str.lower() == filtros["status"].lower()]
        if filtros.get("criticidade"):
            df = df[df["Criticidade"].str.strip().str.lower() == filtros["criticidade"].lower()]
    return df.reset_index(drop=True)


_HEADERS_ATIVOS = [
    "Id", "Empresa", "Client_Id", "Planta", "Tag", "Tipo", "Modelo",
    "Ns", "Mb", "Inversor", "Analise_Oleo", "Status", "Score",
    "Criticidade", "Detalhes", "Observacoes_Internas", "Data", "Criado_Em",
    "Modelo_Bomba_Oleo", "Num_Coalescer", "Modelo_Painel", "Horimetro",
]

_HEADERS_COMPONENTES = [
    "Id", "Ativo_Id", "Nome", "Tipo", "Modelo", "Ns", "Mb",
    "Inversor", "Status", "Score", "Criticidade", "Detalhes", "Data", "Criado_Em",
]


def _ensure_tab_headers(tab_name: str, headers: list) -> None:
    """Garante que a aba existe e tem cabeçalhos. Cria se necessário."""
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title=tab_name, rows=1000, cols=len(headers) + 2)
            ws.append_row(headers, value_input_option="USER_ENTERED")
            _clear_read_caches()
            return
        # Tab existe — verificar se tem cabeçalhos
        first_row = ws.row_values(1)
        if not first_row or first_row[0].strip() == "":
            ws.insert_row(headers, index=1, value_input_option="USER_ENTERED")
            _clear_read_caches()
    except Exception:
        pass


def cadastrar_ativo_sv(dados: dict) -> str | None:
    """Cadastra ativo principal. Retorna o ID gerado ou None em falha."""
    _ensure_tab_headers("Ativos", _HEADERS_ATIVOS)
    ativo_id = _gerar_id("AT")
    ok = append_row("Ativos", [
        ativo_id,
        dados.get("empresa", ""),
        dados.get("client_id", ""),
        dados.get("planta", ""),
        dados.get("nome", ""),
        dados.get("tipo", ""),
        dados.get("modelo", ""),
        dados.get("numero_serie", ""),
        dados.get("mb", ""),
        dados.get("inversor_frequencia", ""),
        dados.get("analise_oleo_aplicavel", "Não"),
        dados.get("status", ""),
        dados.get("score_saude", ""),
        dados.get("criticidade", ""),
        dados.get("recomendacao", ""),
        dados.get("observacoes_internas", ""),
        dados.get("ultima_atualizacao", datetime.now().strftime("%d/%m/%Y")),
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        dados.get("modelo_bomba_oleo", ""),
        dados.get("num_coalescer", ""),
        dados.get("modelo_painel", ""),
        str(dados.get("horimetro_atual", "")),
    ])
    return ativo_id if ok else None


def get_componentes_sv(ativo_id: str) -> pd.DataFrame:
    """Componentes vinculados a um ativo. Somente staff deve chamar."""
    df = load_sheet("ComponentesAtivos")
    if df.empty:
        return df
    if "Ativo_Id" not in df.columns:
        return pd.DataFrame()
    return df[
        df["Ativo_Id"].astype(str).str.strip() == str(ativo_id).strip()
    ].reset_index(drop=True)


def cadastrar_componente_sv(dados: dict) -> bool:
    """Cadastra componente vinculado a um ativo principal."""
    _ensure_tab_headers("ComponentesAtivos", _HEADERS_COMPONENTES)
    comp_id = _gerar_id("COMP")
    return append_row("ComponentesAtivos", [
        comp_id,
        dados.get("ativo_id", ""),
        dados.get("nome", ""),
        dados.get("tipo", ""),
        dados.get("modelo", ""),
        dados.get("numero_serie", ""),
        dados.get("mb", ""),
        dados.get("inversor_frequencia", ""),
        dados.get("status", ""),
        dados.get("score_saude", ""),
        dados.get("criticidade", ""),
        dados.get("recomendacao", ""),
        dados.get("ultima_atualizacao", datetime.now().strftime("%d/%m/%Y")),
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    ])


# ── Chamados de suporte ───────────────────────────────────────────────────────

def get_chamados_sv(client_id: str) -> pd.DataFrame:
    """Alias para compatibilidade."""
    return get_chamados(client_id)


def abrir_chamado_sv(client_id: str, email: str, titulo: str, descricao: str,
                     planta: str, equipamento: str, prioridade: str) -> bool:
    """Alias legado."""
    return abrir_chamado(client_id, email, titulo, descricao, planta, equipamento, prioridade)


# ── Sessões persistentes ──────────────────────────────────────────────────────

_HEADERS_SESSIONS = [
    "Token", "Empresa", "Email", "Telefone", "Client_Id",
    "Criado_Em", "Expira_Em", "Ativo", "Perfil", "Nome",
]


def _ensure_sessions_tab() -> None:
    """Garante que a aba Sessions existe com cabeçalhos corretos na linha 1."""
    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("Sessions")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title="Sessions", rows=10000, cols=12)
            ws.append_row(_HEADERS_SESSIONS, value_input_option="USER_ENTERED")
            _clear_read_caches()
            return
        first = ws.row_values(1)
        if not first or first[0].strip() != "Token":
            ws.insert_row(_HEADERS_SESSIONS, index=1, value_input_option="USER_ENTERED")
            _clear_read_caches()
    except Exception:
        pass


def save_session(token: str, empresa: str, email: str,
                 telefone: str, client_id: str,
                 perfil: str = "cliente", nome: str = "") -> None:
    _ensure_sessions_tab()
    expiry = (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y %H:%M:%S")
    append_row("Sessions", [
        token, empresa, email, telefone, client_id,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"), expiry, "1",
        perfil, nome or empresa,
    ])


def get_session(token: str) -> dict | None:
    df = load_sheet("Sessions")
    if df.empty or "Token" not in df.columns:
        return None
    match = df[df["Token"].astype(str).str.strip() == token.strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    if str(row.get("Ativo", "1")).strip() != "1":
        return None
    try:
        expiry = datetime.strptime(
            str(row.get("Expira_Em", "")).strip(), "%d/%m/%Y %H:%M:%S")
        if datetime.now() > expiry:
            return None
    except Exception:
        pass
    return {
        "empresa":   str(row.get("Empresa",   "")).strip(),
        "email":     str(row.get("Email",     "")).strip(),
        "telefone":  str(row.get("Telefone",  "")).strip(),
        "client_id": str(row.get("Client_Id", "")).strip(),
        "perfil":    str(row.get("Perfil",    "cliente")).strip().lower() or "cliente",
        "nome":      str(row.get("Nome",      "")).strip(),
    }


# ── Notificações do Portal (internas) ────────────────────────────────────────

_HEADERS_PORTAL_NOTIF = [
    "Id", "Cliente_Id", "Usuario_Id",
    "Ativo_Id", "Report_Id", "Ticket_Id",
    "MaintenanceTask_Id", "Alert_Id", "Document_Id",
    "Tipo_Evento", "Titulo", "Mensagem", "Prioridade",
    "Canal", "Status", "Link_Page", "Link_Id",
    "Lida_Em", "Created_At", "Updated_At",
]

_HEADERS_EVENT_PREFS = [
    "Id", "Cliente_Id", "Evento",
    "Canal_Portal", "Canal_Email", "Canal_Whatsapp",
    "Prioridade_Minima", "Frequencia", "Ativo",
    "Created_At", "Updated_At",
]


def add_portal_notification(dados: dict) -> str | None:
    """
    Cria notificação interna do portal.
    SEGURANÇA: client_id SEMPRE da sessão, nunca do front-end.
    Canal E-mail e WhatsApp são registrados mas NÃO enviados nesta etapa.
    """
    if not dados.get("cliente_id"):
        return None
    _ensure_tab_headers("NotificacoesPortal", _HEADERS_PORTAL_NOTIF)
    notif_id = _gerar_id("NP")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("NotificacoesPortal", [
        notif_id,
        dados.get("cliente_id",         ""),
        dados.get("usuario_id",         ""),
        dados.get("ativo_id",           ""),
        dados.get("report_id",          ""),
        dados.get("ticket_id",          ""),
        dados.get("maintenance_task_id",""),
        dados.get("alert_id",           ""),
        dados.get("document_id",        ""),
        dados.get("tipo_evento",        ""),
        dados.get("titulo",             ""),
        dados.get("mensagem",           ""),
        dados.get("prioridade",         "Média"),
        dados.get("canal",              "Portal"),
        "Não lida",
        dados.get("link_page",          ""),
        dados.get("link_id",            ""),
        "",    # Lida_Em
        now,
        now,
    ])
    return notif_id if ok else None


def get_portal_notifications(
    client_id: str,
    apenas_nao_lidas: bool = False,
    limit: int = 50,
) -> pd.DataFrame:
    """
    Retorna notificações do portal para o cliente.
    SEGURANÇA: client_id sempre da sessão — filtra por Cliente_Id.
    """
    if not client_id:
        return pd.DataFrame()
    df = load_sheet("NotificacoesPortal")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_PORTAL_NOTIF:
        if col not in df.columns:
            df[col] = ""
    df = df[
        df["Cliente_Id"].astype(str).str.strip().str.lower()
        == client_id.strip().lower()
    ].copy()
    if apenas_nao_lidas:
        df = df[df["Status"].str.strip() == "Não lida"]
    dt_col = "Created_At"
    if dt_col in df.columns:
        df["_dt"] = pd.to_datetime(df[dt_col].astype(str), dayfirst=True, errors="coerce")
        df = df.sort_values("_dt", ascending=False).drop(columns=["_dt"])
    return df.head(limit).reset_index(drop=True)


@st.cache_data(ttl=15, show_spinner=False)
def count_portal_notifications_unread(client_id: str) -> int:
    """Conta notificações não lidas do portal para o cliente.
    Cache curto (15s) — usado no badge do topnav, recalculado antes em toda
    navegação; chave inclui client_id, sem risco de misturar clientes."""
    if not client_id:
        return 0
    df = get_portal_notifications(client_id, apenas_nao_lidas=True)
    return len(df)


def mark_portal_notification_read(notif_id: str, client_id: str) -> bool:
    """
    Marca notificação como lida.
    SEGURANÇA: valida que a notificação pertence ao client_id.
    """
    if not notif_id or not client_id:
        return False
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("NotificacoesPortal")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(notif_id, in_column=id_col)
        if not cell:
            return False
        # Valida ownership
        row_vals = ws.row_values(cell.row)
        cid_idx  = headers.index("Cliente_Id") if "Cliente_Id" in headers else -1
        if cid_idx >= 0:
            row_cid = (row_vals[cid_idx] if cid_idx < len(row_vals) else "").strip().lower()
            if row_cid != client_id.strip().lower():
                return False  # não pertence ao cliente
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        def _c(name): return headers.index(name) + 1 if name in headers else 0
        ws.update_cell(cell.row, _c("Status"),  "Lida")
        ws.update_cell(cell.row, _c("Lida_Em"), now)
        ws.update_cell(cell.row, _c("Updated_At"), now)
        _clear_read_caches()
        return True
    except Exception:
        return False


def mark_all_portal_notifications_read(client_id: str) -> int:
    """Marca todas as notificações não lidas do cliente como lidas. Retorna contagem."""
    df = get_portal_notifications(client_id, apenas_nao_lidas=True)
    count = 0
    for _, row in df.iterrows():
        nid = str(row.get("Id", "")).strip()
        if nid and mark_portal_notification_read(nid, client_id):
            count += 1
    return count


# ── Preferências por Evento ───────────────────────────────────────────────────

def get_event_preferences(client_id: str) -> pd.DataFrame:
    """
    Retorna preferências por evento do cliente.
    SEGURANÇA: client_id da sessão — filtra por Cliente_Id.
    """
    if not client_id:
        return pd.DataFrame()
    df = load_sheet("PreferenciasEvento")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_EVENT_PREFS:
        if col not in df.columns:
            df[col] = ""
    return df[
        df["Cliente_Id"].astype(str).str.strip().str.lower()
        == client_id.strip().lower()
    ].reset_index(drop=True)


def upsert_event_preference(client_id: str, evento: str, dados: dict) -> bool:
    """
    Cria ou atualiza preferência de evento.
    SEGURANÇA: client_id sempre da sessão.
    """
    if not client_id or not evento:
        return False
    _ensure_tab_headers("PreferenciasEvento", _HEADERS_EVENT_PREFS)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("PreferenciasEvento")
        headers = ws.row_values(1)
        # Busca linha existente para este client_id + evento
        all_vals = ws.get_all_values()
        row_num  = None
        cid_idx  = headers.index("Cliente_Id") if "Cliente_Id" in headers else -1
        ev_idx   = headers.index("Evento")     if "Evento"     in headers else -1
        if cid_idx >= 0 and ev_idx >= 0:
            for i, row in enumerate(all_vals[1:], start=2):
                cid_v = row[cid_idx].strip().lower() if cid_idx < len(row) else ""
                ev_v  = row[ev_idx].strip()           if ev_idx  < len(row) else ""
                if cid_v == client_id.strip().lower() and ev_v == evento:
                    row_num = i
                    break

        pref_id = dados.get("id", "") or _gerar_id("EP")
        row_vals = [
            pref_id,
            client_id,
            evento,
            str(dados.get("canal_portal",    True)).lower(),
            str(dados.get("canal_email",      False)).lower(),
            str(dados.get("canal_whatsapp",   False)).lower(),
            dados.get("prioridade_minima", "Baixa"),
            dados.get("frequencia",        "Imediata"),
            str(dados.get("ativo",         True)).lower(),
            dados.get("created_at", now),
            now,
        ]
        if row_num:
            end_col = chr(64 + len(_HEADERS_EVENT_PREFS))
            ws.update(f"A{row_num}:{end_col}{row_num}", [row_vals],
                      value_input_option="USER_ENTERED")
        else:
            ws.append_row(row_vals, value_input_option="USER_ENTERED")
        _clear_read_caches()
        return True
    except Exception:
        return False


def init_default_event_preferences(client_id: str) -> bool:
    """
    Inicializa preferências padrão para novo cliente.
    Apenas cria se não existirem preferências ainda.
    """
    if not client_id:
        return False
    existing = get_event_preferences(client_id)
    if not existing.empty:
        return True  # já tem preferências

    from notifications import _DEFAULT_EVENT_PREFS
    ok = True
    for evento, pref in _DEFAULT_EVENT_PREFS.items():
        r = upsert_event_preference(client_id, evento, pref)
        if not r:
            ok = False
    return ok


# ── Notificações Externas ─────────────────────────────────────────────────────

_HEADERS_NOTIFICACOES = [
    "Id", "Cliente_Id", "Cliente_Nome", "Usuario_Id", "Usuario_Nome",
    "Email_Destinatario", "Whatsapp_Destinatario", "Evento_Tipo", "Canal",
    "Titulo", "Mensagem", "Link_Portal", "Status", "Tentativas",
    "Erro", "Enviado_Por", "Enviado_Em", "Created_At", "Updated_At",
]

_HEADERS_PREFS_NOTIF = [
    "Id", "Usuario_Id", "Cliente_Id", "Nome", "Email", "Whatsapp",
    "Receber_Email", "Receber_Whatsapp", "Receber_Relatorios",
    "Receber_Alertas_Criticos", "Receber_Manutencao", "Receber_Chamados",
    "Ativo", "Created_At", "Updated_At",
    # Etapa 6.7 — campos de consentimento
    "Consentimento_Email", "Consentimento_Whatsapp",
    "Consentimento_Data", "Consentimento_Origem",
    "Telefone_Whatsapp",
]

# Mapeamento: tipo de evento → campo de preferência que o habilita
_EVENTO_PREF_MAP: dict = {
    "report_published":             "Receber_Relatorios",
    "technical_document_available": "Receber_Relatorios",
    "critical_alarm":               "Receber_Alertas_Criticos",
    "asset_critical":               "Receber_Alertas_Criticos",
    "maintenance_due":              "Receber_Manutencao",
    "maintenance_overdue":          "Receber_Manutencao",
    "ticket_replied":               "Receber_Chamados",
    "ticket_waiting_customer":      "Receber_Chamados",
}


def get_notificacoes(client_id: str = "") -> pd.DataFrame:
    """Carrega notificações externas. Staff chama sem filtro; cliente passa o próprio client_id."""
    df = load_sheet("NotificacoesExternas")
    if df.empty:
        return pd.DataFrame()
    if client_id:
        df = df[
            df["Cliente_Id"].astype(str).str.strip().str.lower()
            == client_id.strip().lower()
        ]
    return df.reset_index(drop=True)


def add_notificacao(dados: dict) -> str | None:
    """Registra uma notificação externa. Retorna ID ou None."""
    _ensure_tab_headers("NotificacoesExternas", _HEADERS_NOTIFICACOES)
    notif_id = _gerar_id("NOTIF")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("NotificacoesExternas", [
        notif_id,
        dados.get("cliente_id",            ""),
        dados.get("cliente_nome",          ""),
        dados.get("usuario_id",            ""),
        dados.get("usuario_nome",          ""),
        dados.get("email_destinatario",    ""),
        dados.get("whatsapp_destinatario", ""),
        dados.get("evento_tipo",           ""),
        dados.get("canal",                 ""),
        dados.get("titulo",                ""),
        dados.get("mensagem",              ""),
        dados.get("link_portal",           ""),
        dados.get("status",                "Pendente"),
        "0",
        "",
        dados.get("enviado_por",           ""),
        dados.get("enviado_em",            ""),
        now,
        now,
    ])
    return notif_id if ok else None


def update_notificacao_status(
    notif_id: str,
    status: str,
    enviado_em: str = "",
    erro: str = "",
) -> bool:
    """Atualiza o status de uma notificação externa. Retorna True em caso de sucesso."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("NotificacoesExternas")
        headers = ws.row_values(1)
        cell = ws.find(notif_id)
        if not cell:
            return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        row = cell.row

        def _col(name: str) -> int:
            return headers.index(name) + 1 if name in headers else 0

        ws.update_cell(row, _col("Status"),     status)
        ws.update_cell(row, _col("Updated_At"), now)
        if enviado_em:
            ws.update_cell(row, _col("Enviado_Em"), enviado_em)
        if erro:
            ws.update_cell(row, _col("Erro"), erro)
        if status == "Enviado":
            tc = _col("Tentativas")
            if tc:
                try:
                    current_t = int(ws.cell(row, tc).value or 0)
                    ws.update_cell(row, tc, str(current_t + 1))
                    ws.update_cell(row, _col("Enviado_Em"), enviado_em or now)
                except Exception:
                    pass
        _clear_read_caches()
        return True
    except Exception:
        return False


def get_preferencias_notificacao(usuario_id: str = "", client_id: str = "") -> pd.DataFrame:
    """Carrega preferências de notificação. Filtra por usuario_id ou client_id."""
    df = load_sheet("PreferenciasNotificacao")
    if df.empty:
        return pd.DataFrame()
    if usuario_id:
        df = df[df["Usuario_Id"].astype(str).str.strip() == usuario_id.strip()]
    elif client_id:
        df = df[
            df["Cliente_Id"].astype(str).str.strip().str.lower()
            == client_id.strip().lower()
        ]
    return df.reset_index(drop=True)


def get_contatos_notificacao(client_id: str) -> list:
    """Retorna contatos disponíveis para notificação de um cliente.

    Prioriza PreferenciasNotificacao; fallback para dados básicos do cliente.
    SECURITY: client_id deve vir de fonte confiável (sessão/staff), nunca do front-end.
    """
    contacts: list = []

    df = get_preferencias_notificacao(client_id=client_id)
    if not df.empty:
        for _, r in df.iterrows():
            if str(r.get("Ativo", "true")).strip().lower() == "false":
                continue
            email    = str(r.get("Email",    "")).strip()
            whatsapp = str(r.get("Whatsapp", r.get("Telefone_Whatsapp", ""))).strip()
            uid      = str(r.get("Id",       "")).strip() or f"pref_{client_id}_{len(contacts)}"
            consent_email = str(r.get("Consentimento_Email",    "true")).strip().lower()
            consent_wa    = str(r.get("Consentimento_Whatsapp", "true")).strip().lower()
            contacts.append({
                "id":                    uid,
                "usuario_id":            str(r.get("Usuario_Id", "")).strip(),
                "nome":                  str(r.get("Nome",       "")).strip() or str(r.get("Usuario_Id", "")).strip(),
                "email":                 email,
                "whatsapp":              whatsapp,
                "telefone_whatsapp":     whatsapp,
                "tem_email":             bool(email    and str(r.get("Receber_Email",    "false")).strip().lower() == "true"),
                "tem_whatsapp":          bool(whatsapp and str(r.get("Receber_Whatsapp", "false")).strip().lower() == "true"),
                "consentimento_email":   consent_email in ("true", "1", "sim", "yes"),
                "consentimento_whatsapp": consent_wa in ("true", "1", "sim", "yes"),
                "consentimento_data":    str(r.get("Consentimento_Data",   "")).strip(),
                "consentimento_origem":  str(r.get("Consentimento_Origem", "")).strip(),
                "ativo":                 True,
            })

    if contacts:
        return contacts

    # Fallback: dados básicos do cliente na aba Clientes/Usuarios
    try:
        df_cli = get_all_clientes()
        if not df_cli.empty and "Empresa" in df_cli.columns:
            match = df_cli[
                df_cli["Empresa"].str.strip().str.lower() == client_id.strip().lower()
            ]
            if match.empty and "Client_Id" in df_cli.columns:
                match = df_cli[
                    df_cli["Client_Id"].astype(str).str.strip().str.lower() == client_id.strip().lower()
                ]
            if not match.empty:
                r        = match.iloc[0]
                email    = str(r.get("Email",    "")).strip()
                telefone = str(r.get("Telefone", "")).strip()
                nome_emp = str(r.get("Empresa",  client_id)).strip()
                if email or telefone:
                    contacts.append({
                        "id":           f"cli_{client_id}",
                        "usuario_id":    email or client_id,
                        "nome":         f"Contato principal — {nome_emp}",
                        "email":         email,
                        "whatsapp":      telefone,
                        "tem_email":     bool(email),
                        "tem_whatsapp":  bool(telefone),
                    })
    except Exception:
        pass

    return contacts


def upsert_preferencias_notificacao(dados: dict) -> bool:
    """Cria ou atualiza preferências de notificação de um usuário."""
    _ensure_tab_headers("PreferenciasNotificacao", _HEADERS_PREFS_NOTIF)
    usuario_id = dados.get("usuario_id", "")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("PreferenciasNotificacao")
        try:
            cell = ws.find(usuario_id)
        except Exception:
            cell = None

        row_vals = [
            dados.get("id", "") or _gerar_id("PREF"),
            usuario_id,
            dados.get("cliente_id", ""),
            dados.get("nome", ""),
            dados.get("email", ""),
            dados.get("whatsapp", ""),
            str(dados.get("receber_email",            False)).lower(),
            str(dados.get("receber_whatsapp",         False)).lower(),
            str(dados.get("receber_relatorios",       True)).lower(),
            str(dados.get("receber_alertas_criticos", True)).lower(),
            str(dados.get("receber_manutencao",       True)).lower(),
            str(dados.get("receber_chamados",         True)).lower(),
            "true",
            dados.get("created_at", now),
            now,
        ]

        if cell:
            end_col = chr(64 + len(_HEADERS_PREFS_NOTIF))
            ws.update(
                f"A{cell.row}:{end_col}{cell.row}",
                [row_vals],
                value_input_option="USER_ENTERED",
            )
        else:
            ws.append_row(row_vals, value_input_option="USER_ENTERED")

        _clear_read_caches()
        return True
    except Exception:
        return False


def notify_event(
    client_id: str,
    evento_tipo: str,
    titulo: str,
    mensagem: str,
    link_portal: str,
) -> list:
    """Cria registros de notificação externa conforme preferências do cliente.

    Nesta versão cria registros como Pendente.
    Integração futura: POST /api/notifications/dispatch → n8n, e-mail ou API WhatsApp.

    SECURITY:
    - client_id SEMPRE vem da sessão/autenticação, nunca do frontend.
    - mensagem deve ser resumo apenas; nunca incluir conteúdo técnico sensível completo.
    - WhatsApp recebe apenas resumo + link seguro.
    - Observações internas da Pred.IO nunca são incluídas.
    - Links devem apontar para o portal autenticado (não expõem dados diretamente).
    """
    prefs_df = get_preferencias_notificacao(client_id=client_id)
    if prefs_df.empty:
        return []

    pref_key = _EVENTO_PREF_MAP.get(evento_tipo)
    created: list = []

    for _, pref in prefs_df.iterrows():
        if str(pref.get("Ativo", "true")).lower() != "true":
            continue
        if pref_key and str(pref.get(pref_key, "false")).lower() != "true":
            continue

        uid = str(pref.get("Usuario_Id", "")).strip()

        if str(pref.get("Receber_Email", "false")).lower() == "true":
            nid = add_notificacao({
                "cliente_id":  client_id,
                "usuario_id":  uid,
                "evento_tipo": evento_tipo,
                "canal":       "E-mail",
                "titulo":      titulo,
                "mensagem":    mensagem,
                "link_portal": link_portal,
            })
            if nid:
                created.append(nid)

        if str(pref.get("Receber_Whatsapp", "false")).lower() == "true":
            # WhatsApp: apenas resumo + link — nunca conteúdo técnico completo
            resumo_wa = f"{titulo}. Acesse o portal: {link_portal}"
            nid = add_notificacao({
                "cliente_id":  client_id,
                "usuario_id":  uid,
                "evento_tipo": evento_tipo,
                "canal":       "WhatsApp",
                "titulo":      titulo,
                "mensagem":    resumo_wa,
                "link_portal": link_portal,
            })
            if nid:
                created.append(nid)

    return created


# ── Relatórios Técnicos ──────────────────────────────────────────────────────

_HEADERS_TECH_REPORTS = [
    "Id", "Cliente_Id", "Ativo_Id", "Titulo", "Tipo_Servico", "Severidade",
    "Data_Relatorio", "Planta", "Equipamento", "Resumo", "Recomendacoes",
    "Arquivo_Url", "Score_Impacto", "Status", "Obs_Interna",
    "Created_By", "Created_At", "Updated_At",
    # GUT da recomendação técnica — ver _HEADERS_GUT / gut.py
    "Gut_Gravidade", "Gut_Urgencia", "Gut_Tendencia",
    "Gut_Score", "Gut_Prioridade", "Gut_Observacao",
    # Etapa 2 — upload direto de PDF (integração App Relatórios, ver
    # docs/PREDIO_INTEGRACAO_APP_RELATORIOS_ETAPA_1.md). Colunas adicionadas
    # de forma não-destrutiva por _ensure_extra_cols em add_technical_report.
    "Origem", "Arquivo_Nome", "Storage_Path", "Tecnico", "Conclusao",
    "Status_Indexacao", "Quantidade_Chunks", "Uso_Pela_Ia",
    # Etapa 3 — publicação direta do App Relatórios (integration_api.py).
    # App_Report_Id é o report.id do App (Firestore/IndexedDB) — usado para
    # idempotência: reenviar o mesmo report_id atualiza em vez de duplicar.
    "App_Report_Id", "Medicoes_Json", "Sincronizado_Em",
    # Assistente Técnico IA — resumo técnico manual. Diagnóstico é um campo
    # próprio (distinto de Resumo/Conclusao); "resumo_tecnico" pedido pela
    # Supervisão é a própria coluna Resumo — já existia e já era prioridade
    # na indexação (ver index_relatorio_tecnico), só reaproveitada aqui.
    "Diagnostico",
]

# Origem do relatório — usado pelo seletor na Supervisão e pela integração.
ORIGEM_UPLOAD_DIRETO          = "upload_direto"
ORIGEM_GOOGLE_DRIVE           = "google_drive_url"
ORIGEM_APP_RELATORIOS         = "app_relatorios"
ORIGEM_UPLOAD_MANUAL_VIBRACAO = "upload_manual_vibracao"


def _ativo_pertence_cliente(ativo_id: str, cliente_id: str) -> bool:
    """Valida no backend que o ativo pertence ao cliente informado.

    NUNCA confiar apenas no front-end — o seletor de ativo já filtra por
    cliente, mas esta checagem é a garantia real contra um ativo_id de
    outro cliente sendo enviado (ex.: manipulação de formulário).
    Ativo é opcional em relatórios legados: ativo_id vazio é válido.
    """
    ativo_id   = (ativo_id or "").strip()
    cliente_id = (cliente_id or "").strip().lower()
    if not ativo_id:
        return True
    if not cliente_id:
        return False
    df = load_sheet("Ativos")
    if df.empty or "Id" not in df.columns:
        return False
    match = df[df["Id"].astype(str).str.strip() == ativo_id]
    if match.empty:
        return False
    row = match.iloc[0]
    empresa    = str(row.get("Empresa", "")).strip().lower()
    ativo_cli  = str(row.get("Client_Id", "")).strip().lower()
    return cliente_id in (empresa, ativo_cli) and bool(empresa or ativo_cli)


# Alias público — usado por integration_api.py (Etapa 3), fora deste módulo.
# Mesma função de _ativo_pertence_cliente, só com nome sem "_" para uso externo.
ativo_pertence_cliente = _ativo_pertence_cliente


def get_ativo_by_id(ativo_id: str) -> dict | None:
    """Retorna dict do ativo pelo Id, ou None se não existir. Uso: integration_api.py."""
    ativo_id = (ativo_id or "").strip()
    if not ativo_id:
        return None
    df = load_sheet("Ativos")
    if df.empty or "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == ativo_id]
    if match.empty:
        return None
    return {col: str(match.iloc[0].get(col, "")).strip() for col in df.columns}

_TIPO_SERVICO_TO_TIMELINE = {
    "análise de vibração": "analise_vibracao",
    "analise de vibracao": "analise_vibracao",
    "análise de óleo":     "analise_oleo",
    "analise de oleo":     "analise_oleo",
    "termografia":         "termografia",
}

_SCORE_DELTA_MAP = {
    "urgente": -25,
    "crítico": -15,
    "critico": -15,
    "atenção": -7,
    "atencao": -7,
    "normal":   2,
}


def _calc_new_score(current: int, severidade: str) -> int:
    delta = _SCORE_DELTA_MAP.get(severidade.strip().lower(), 0)
    return max(5, min(100, current + delta))


def add_technical_report(dados: dict, created_by: str = "") -> str | None:
    """Cria relatório técnico em rascunho. cliente_id DEVE vir da sessão.

    SEGURANÇA: valida no backend que ativo_id (se informado) pertence a
    cliente_id — nunca confia apenas no filtro do seletor no front-end.
    """
    cliente_id = dados.get("cliente_id", "")
    ativo_id   = dados.get("ativo_id", "")
    if not cliente_id:
        return None
    if not _ativo_pertence_cliente(ativo_id, cliente_id):
        return None
    _ensure_tab_headers("TechnicalReports", _HEADERS_TECH_REPORTS)
    # Aba pode já existir com o cabeçalho antigo (sem as colunas da Etapa 2) —
    # garante as colunas novas ao final, sem apagar/reordenar as existentes.
    _ensure_extra_cols("TechnicalReports", _HEADERS_TECH_REPORTS)
    rep_id = _gerar_id("REP")
    now    = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("TechnicalReports", [
        rep_id,
        cliente_id,
        ativo_id,
        dados.get("titulo", ""),
        dados.get("tipo_servico", ""),
        dados.get("severidade", "Normal"),
        dados.get("data_relatorio", datetime.now().strftime("%d/%m/%Y")),
        dados.get("planta", ""),
        dados.get("equipamento", ""),
        dados.get("resumo", ""),
        dados.get("recomendacoes", ""),
        dados.get("arquivo_url", ""),
        "",
        dados.get("status", "Rascunho"),
        dados.get("obs_interna", ""),
        created_by,
        now,
        now,
        "", "", "", "", "", "",  # Gut_* — definidos depois via update_report_gut
        dados.get("origem", ORIGEM_UPLOAD_DIRETO),
        dados.get("arquivo_nome", ""),
        dados.get("storage_path", ""),
        dados.get("tecnico", created_by),
        dados.get("conclusao", ""),
        "", "", "",  # Status_Indexacao, Quantidade_Chunks, Uso_Pela_Ia
        dados.get("app_report_id", ""),
        dados.get("medicoes_json", ""),
        dados.get("sincronizado_em", ""),
        dados.get("diagnostico", ""),
    ])
    return rep_id if ok else None


def get_technical_report_by_app_id(app_report_id: str) -> dict | None:
    """Busca relatório técnico pelo report_id de origem do App Relatórios
    (App_Report_Id) — usado por integration_api.py para idempotência:
    reenviar o mesmo report_id atualiza o relatório existente em vez de
    criar um duplicado."""
    app_report_id = (app_report_id or "").strip()
    if not app_report_id:
        return None
    df = load_sheet("TechnicalReports")
    if df.empty or "App_Report_Id" not in df.columns:
        return None
    match = df[df["App_Report_Id"].astype(str).str.strip() == app_report_id]
    if match.empty:
        return None
    row = match.iloc[0]
    return {col: str(row.get(col, "")).strip() for col in _HEADERS_TECH_REPORTS}


@st.cache_data(ttl=20, show_spinner=False)
def get_technical_reports(
    client_id: str = "",
    status: str = "",
    ativo_id: str = "",
    staff: bool = True,
) -> pd.DataFrame:
    """Retorna relatórios técnicos.
    staff=False → somente publicados do cliente (requer client_id).
    """
    df = load_sheet("TechnicalReports")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_TECH_REPORTS:
        if col not in df.columns:
            df[col] = ""
    if not staff:
        if not client_id:
            return pd.DataFrame()
        df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
        df = df[df["Status"].str.strip() == "Publicado"]
    else:
        if client_id:
            df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
        if status:
            df = df[df["Status"].str.strip() == status]
        if ativo_id:
            df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]
    df = df.copy()
    df["_dt"] = pd.to_datetime(df["Data_Relatorio"].astype(str), dayfirst=True, errors="coerce")
    df = df.sort_values("_dt", ascending=False).drop(columns=["_dt"])
    return df.reset_index(drop=True)


def get_technical_report_by_id(report_id: str) -> dict | None:
    """Retorna dict com campos do relatório ou None."""
    df = load_sheet("TechnicalReports")
    if df.empty or "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == report_id.strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    return {col: str(row.get(col, "")).strip() for col in _HEADERS_TECH_REPORTS}


def update_technical_report(report_id: str, campos: dict) -> bool:
    """Atualiza campos de um relatório técnico.

    SEGURANÇA: se Ativo_Id estiver sendo alterado, valida no backend que o
    ativo pertence ao Cliente_Id efetivo do relatório (o informado em
    `campos`, ou o já salvo caso não esteja sendo trocado nesta chamada).
    """
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("TechnicalReports")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(report_id, in_column=id_col)
        if not cell:
            return False
        if campos.get("Ativo_Id"):
            cliente_id_efetivo = campos.get("Cliente_Id", "")
            if not cliente_id_efetivo and "Cliente_Id" in headers:
                cliente_id_efetivo = ws.cell(cell.row, headers.index("Cliente_Id") + 1).value or ""
            if not _ativo_pertence_cliente(campos["Ativo_Id"], cliente_id_efetivo):
                return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        campos.setdefault("Updated_At", now)
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        _clear_read_caches()
        return True
    except Exception:
        return False


def _get_ativo_score(ativo_id: str) -> int | None:
    """Lê Score atual de um ativo pelo Id."""
    df = load_sheet("Ativos")
    if df.empty or "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == ativo_id.strip()]
    if match.empty:
        return None
    try:
        return int(float(str(match.iloc[0].get("Score", "75"))))
    except Exception:
        return None


def _faixa_score(score: int) -> str:
    """Faixa textual do score — mesmos limiares usados em page_ativos.py
    (_score_band), duplicado aqui porque sheets.py não deve importar módulo
    de UI. Se um dia os limiares mudarem, atualizar os dois lugares."""
    if score >= 85: return "Bom"
    if score >= 60: return "Atenção"
    if score >= 30: return "Crítico"
    return "Urgente"


def _update_ativo_score(ativo_id: str, new_score: int) -> bool:
    """Atualiza Score do ativo na aba Ativos. Se a FAIXA (Bom/Atenção/
    Crítico/Urgente) mudar, grava um evento status_alterado na timeline —
    sinal de mudança relevante mesmo sem esperar o snapshot periódico do
    comparativo (Etapa timeline/comparativo)."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Ativos")
        headers = ws.row_values(1)
        if "Id" not in headers or "Score" not in headers:
            return False
        id_col    = headers.index("Id") + 1
        score_col = headers.index("Score") + 1
        cell = ws.find(ativo_id, in_column=id_col)
        if not cell:
            return False

        old_score = None
        row_vals = ws.row_values(cell.row)
        try:
            old_score_raw = row_vals[score_col - 1] if len(row_vals) >= score_col else ""
            old_score = int(float(old_score_raw)) if old_score_raw not in ("", "nan") else None
        except Exception:
            old_score = None

        ws.update_cell(cell.row, score_col, str(new_score))
        _clear_read_caches()

        if old_score is not None and _faixa_score(old_score) != _faixa_score(new_score):
            try:
                tag_col = headers.index("Tag") + 1 if "Tag" in headers else None
                cid_col = headers.index("Client_Id") + 1 if "Client_Id" in headers else None
                nome = row_vals[tag_col - 1] if tag_col and len(row_vals) >= tag_col else ativo_id
                cliente_id = row_vals[cid_col - 1] if cid_col and len(row_vals) >= cid_col else ""
                add_report_timeline_event({
                    "ativo_id": ativo_id, "cliente_id": cliente_id,
                    "tipo": "status_alterado",
                    "titulo": f"{nome}: {_faixa_score(old_score)} → {_faixa_score(new_score)}",
                    "descricao": f"Score de saúde: {old_score} → {new_score}.",
                    "origem": "Score de Saúde", "visivel_cliente": "true",
                })
            except Exception:
                pass
        return True
    except Exception:
        return False


def publish_technical_report(report_id: str, published_by: str = "") -> dict:
    """Publica relatório: atualiza status, score, timeline, alertas, notificações.

    SEGURANÇA: Obs_Interna nunca é enviada ao cliente.
    Retorna dict com ações executadas.
    """
    rep = get_technical_report_by_id(report_id)
    if not rep:
        return {"ok": False, "erro": "Relatório não encontrado."}
    if rep.get("Status") == "Publicado":
        return {"ok": False, "erro": "Relatório já publicado."}

    severidade   = rep.get("Severidade", "Normal")
    ativo_id     = rep.get("Ativo_Id", "").strip()
    cliente_id   = rep.get("Cliente_Id", "").strip()
    titulo       = rep.get("Titulo", "")
    data_rel     = rep.get("Data_Relatorio", datetime.now().strftime("%d/%m/%Y"))
    tipo_servico = rep.get("Tipo_Servico", "")
    planta       = rep.get("Planta", "")
    equipamento  = rep.get("Equipamento", "")
    resumo       = rep.get("Resumo", "")
    recomend     = rep.get("Recomendacoes", "")

    actions: dict = {
        "ok": True,
        "score_delta": 0,
        "score_atualizado": False,
        "timeline": False,
        "alerta": False,
        "notificado": False,
    }

    campos_upd: dict = {
        "Status": "Publicado",
    }
    if published_by:
        campos_upd["Created_By"] = published_by

    # Atualiza score do ativo
    if ativo_id:
        current = _get_ativo_score(ativo_id) or 75
        new_sc  = _calc_new_score(current, severidade)
        delta   = new_sc - current
        if _update_ativo_score(ativo_id, new_sc):
            campos_upd["Score_Impacto"] = str(delta)
            actions["score_delta"]       = delta
            actions["score_atualizado"]  = True

    update_technical_report(report_id, campos_upd)

    # Evento na timeline — resumo/recomendações entram como texto curto no
    # histórico do ativo (nunca o PDF inteiro, só a referência ao relatório).
    ev_tipo_key = tipo_servico.strip().lower()
    ev_tipo = _TIPO_SERVICO_TO_TIMELINE.get(ev_tipo_key, "relatorio_publicado")
    descr   = f"{tipo_servico} — {titulo}. Severidade: {severidade}."
    if equipamento:
        descr += f" Equipamento: {equipamento}."
    if actions["score_delta"]:
        descr += f" Score impactado em {actions['score_delta']:+d} pontos."
    if resumo.strip():
        descr += f" Resumo: {resumo.strip()[:220]}{'…' if len(resumo.strip()) > 220 else ''}"
    if recomend.strip():
        descr += f" Recomendação: {recomend.strip()[:220]}{'…' if len(recomend.strip()) > 220 else ''}"
    add_report_timeline_event({
        "ativo_id":        ativo_id or cliente_id,
        "cliente_id":      cliente_id,
        "tipo":            ev_tipo,
        "titulo":          f"Relatório publicado: {titulo}",
        "descricao":       descr,
        "data":            data_rel,
        "origem":          "Relatórios Técnicos",
        "report_id":       report_id,
        "visivel_cliente": "true",
        "obs_interna":     "",
    })
    actions["timeline"] = True

    # Alerta interno se Crítico ou Urgente
    sev_lower = severidade.strip().lower()
    if sev_lower in ("crítico", "critico", "urgente"):
        prio_alerta = "Urgente" if sev_lower == "urgente" else "Alta"
        msg_al = (
            f"Relatório '{titulo}' publicado com severidade {severidade}."
            + (f" Equipamento: {equipamento}." if equipamento else "")
            + f" Cliente: {cliente_id}."
        )
        try:
            df_cli  = get_all_clientes()
            empresa = ""
            if not df_cli.empty:
                cid_col = "Client_Id" if "Client_Id" in df_cli.columns else "Cliente_Id"
                if cid_col in df_cli.columns:
                    m = df_cli[
                        df_cli[cid_col].astype(str).str.strip().str.lower()
                        == cliente_id.lower()
                    ]
                    empresa = str(m.iloc[0].get("Empresa", "")) if not m.empty else ""
        except Exception:
            empresa = ""
        add_alerta_sv(
            client_id  = cliente_id,
            empresa    = empresa or cliente_id,
            titulo     = f"Relatório {severidade}: {titulo}",
            descricao  = msg_al,
            prioridade = prio_alerta,
        )
        actions["alerta"] = True

    # Notificação externa
    try:
        msg_nf = f"Novo relatório técnico disponível: {titulo} ({data_rel})."
        if planta:
            msg_nf += f" Planta: {planta}."
        notifs = notify_event(
            client_id   = cliente_id,
            evento_tipo = "report_published",
            titulo      = f"Novo relatório: {titulo}",
            mensagem    = msg_nf,
            link_portal = "/",
        )
        actions["notificado"] = len(notifs) > 0
    except Exception:
        pass

    # Indexa para o Assistente Técnico — centralizado aqui (Etapa 5) para que
    # NUNCA fique dependendo de quem chamou publish_technical_report() lembrar
    # de indexar depois. index_relatorio_tecnico() só é chamada quando o
    # Status já está "Publicado" (linha acima) — rascunho/Em revisão nunca
    # passam por aqui.
    actions["indexado"] = reindex_technical_report(report_id).get("ok", False)

    return actions


def archive_technical_report(report_id: str) -> bool:
    """Arquiva um relatório técnico publicado."""
    return update_technical_report(report_id, {"Status": "Arquivado"})


def delete_technical_report(report_id: str) -> bool:
    """Remove relatório somente se ainda for Rascunho."""
    rep = get_technical_report_by_id(report_id)
    if not rep or rep.get("Status") != "Rascunho":
        return False
    return delete_row_by_id("TechnicalReports", "Id", report_id)


def delete_technical_report_full(report_id: str) -> dict:
    """Remove um relatório técnico em QUALQUER status (diferente de
    delete_technical_report(), que só apaga Rascunho), com limpeza completa:

    - Se estava Publicado: reverte o impacto no Score do ativo
      (Score_Impacto) e remove o alerta interno gerado na publicação não é
      feito aqui (alertas não guardam Report_Id — ficam no histórico normal).
    - Remove os chunks indexados no Assistente Técnico (TechnicalReportChunks).
    - Remove o(s) evento(s) da timeline do ativo (ReportTimeline).
    - Remove a linha do relatório em si.

    Não desfaz notificações já enviadas ao cliente (mensagem já entregue).
    """
    rep = get_technical_report_by_id(report_id)
    if not rep:
        return {"ok": False, "erro": "Relatório não encontrado."}

    ativo_id = rep.get("Ativo_Id", "").strip()
    if rep.get("Status", "").strip() == "Publicado" and ativo_id:
        try:
            delta = int(float(rep.get("Score_Impacto", "0") or "0"))
        except Exception:
            delta = 0
        if delta:
            current = _get_ativo_score(ativo_id)
            if current is not None:
                _update_ativo_score(ativo_id, max(5, min(100, current - delta)))

    delete_chunks_relatorio(report_id)
    delete_report_timeline_events(report_id)

    ok = delete_row_by_id("TechnicalReports", "Id", report_id)
    return {"ok": ok, "erro": "" if ok else "Falha ao remover o relatório."}


# ── Timeline de Relatórios ───────────────────────────────────────────────────

_HEADERS_REPORT_TIMELINE = [
    "Id", "Ativo_Id", "Cliente_Id", "Tipo", "Titulo", "Descricao",
    "Data", "Origem", "Report_Id", "Visivel_Cliente", "Obs_Interna", "Created_At",
]


def add_report_timeline_event(dados: dict) -> str | None:
    """Adiciona evento à timeline de relatórios."""
    _ensure_tab_headers("ReportTimeline", _HEADERS_REPORT_TIMELINE)
    ev_id = _gerar_id("TL")
    now   = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("ReportTimeline", [
        ev_id,
        dados.get("ativo_id",        ""),
        dados.get("cliente_id",      ""),
        dados.get("tipo",            "relatorio_publicado"),
        dados.get("titulo",          ""),
        dados.get("descricao",       ""),
        dados.get("data",            datetime.now().strftime("%d/%m/%Y")),
        dados.get("origem",          "Relatórios Técnicos"),
        dados.get("report_id",       ""),
        dados.get("visivel_cliente", "true"),
        dados.get("obs_interna",     ""),
        now,
    ])
    return ev_id if ok else None


def get_report_timeline_events(
    ativo_id: str = "",
    cliente_id: str = "",
    staff: bool = True,
    limit: int | None = None,
) -> pd.DataFrame:
    """Retorna eventos da timeline de relatórios.

    limit (opcional): corta para os N eventos mais recentes DEPOIS de
    ordenar — usado por telas como "Atividade recente" (visão agregada do
    cliente) que nunca devem carregar o histórico completo de uma vez."""
    df = load_sheet("ReportTimeline")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_REPORT_TIMELINE:
        if col not in df.columns:
            df[col] = ""
    if ativo_id:
        df = df[df["Ativo_Id"].astype(str).str.strip() == ativo_id.strip()]
    if cliente_id:
        df = df[df["Cliente_Id"].astype(str).str.strip().str.lower() == cliente_id.strip().lower()]
    if not staff:
        df = df[df["Visivel_Cliente"].astype(str).str.strip().str.lower() != "false"]
        if "Obs_Interna" in df.columns:
            df = df.drop(columns=["Obs_Interna"])
    df = df.copy()

    def _dtkey(d: str) -> tuple:
        try:
            p = str(d).split("/")
            return (int(p[2]), int(p[1]), int(p[0]))
        except Exception:
            return (0, 0, 0)

    df["_s"] = df["Data"].apply(_dtkey)
    df = df.sort_values("_s", ascending=False).drop(columns=["_s"])
    if limit:
        df = df.head(limit)
    return df.reset_index(drop=True)


def delete_report_timeline_events(report_id: str) -> bool:
    """Remove todos os eventos da timeline associados a um Report_Id
    (usado ao apagar um relatório técnico por completo)."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("ReportTimeline")
        headers = ws.row_values(1)
        if "Report_Id" not in headers:
            return True
        col_idx = headers.index("Report_Id") + 1
        all_vals = ws.col_values(col_idx)
        to_delete = [
            i + 1 for i, v in enumerate(all_vals)
            if i > 0 and str(v).strip() == report_id.strip()
        ]
        for row_num in reversed(to_delete):
            ws.delete_rows(row_num)
        _clear_read_caches()
        return True
    except Exception:
        return False


# ── Planos e Tarefas de Manutenção ──────────────────────────────────────────

_HEADERS_MAINT_PLANS = [
    "Id", "Cliente_Id", "Ativo_Id", "Nome", "Descricao", "Status", "Created_At", "Updated_At",
]

_HEADERS_MAINT_TASKS = [
    "Id", "Cliente_Id", "Ativo_Id", "Componente_Id", "Plano_Id", "Nome_Tarefa",
    "Categoria", "Tipo_Manutencao", "Periodicidade_Dias", "Periodicidade_Horas",
    "Ultima_Execucao_Data", "Ultima_Execucao_Horimetro",
    "Proxima_Execucao_Data", "Proxima_Execucao_Horimetro",
    "Status", "Prioridade", "Depende_Relatorio", "Origem",
    "Descricao", "Recomendacao", "Obs_Interna", "Created_At", "Updated_At",
    # GUT — ver _HEADERS_GUT / gut.py
    "Gut_Gravidade", "Gut_Urgencia", "Gut_Tendencia",
    "Gut_Score", "Gut_Prioridade", "Gut_Observacao",
]

_HEADERS_MAINT_EXEC = [
    "Id", "Cliente_Id", "Ativo_Id", "Task_Id", "Executado_Em", "Horimetro_Execucao",
    "Responsavel", "Descricao_Execucao", "Evidencias", "Arquivo_Url", "Obs_Interna", "Created_At",
]


def calc_task_status(task: dict, horimetro_atual: int = 0, as_of=None) -> str:
    """Calcula status dinâmico de uma tarefa de manutenção (sem chamada ao Sheets).

    Funciona com o formato do Sheets (campos Title_Case):
    Tipo_Manutencao, Proxima_Execucao_Data, Proxima_Execucao_Horimetro,
    Periodicidade_Dias, Periodicidade_Horas, Ultima_Execucao_Data, Ultima_Execucao_Horimetro.

    Regras:
    - Condição → "Depende de análise preditiva" (sempre)
    - Calendário: diff dias → Vencida (<0) / Próxima do vencimento (≤15) / Em dia
    - Horímetro: diff horas → Vencida (h≥prox) / Próxima do vencimento (h≥prox-500) / Em dia

    as_of (date, opcional): calcula o status COMO ESTARIA numa data passada,
    em vez de hoje — só afeta o ramo Calendário (comparação de datas). Usado
    pelo comparativo "o que mudou" pra saber se uma tarefa JÁ estava vencida
    no período anterior. Não existe equivalente para Horímetro: não há log
    histórico de leitura de horímetro, só o valor atual (`horimetro_atual`)
    — retroatividade por horímetro não é possível com os dados de hoje.
    """
    from datetime import datetime as _dt, timedelta as _td
    _agora = _dt.combine(as_of, _dt.min.time()) if as_of is not None else _dt.now()

    tipo = str(task.get("Tipo_Manutencao", "")).strip()
    if not tipo:
        # fallback para formato mock (lowercase)
        tipo_mock = str(task.get("tipo", "")).strip()
        if tipo_mock == "condicao":
            return "Depende de análise preditiva"
        if tipo_mock == "calendario":
            tipo = "Calendário"
        elif tipo_mock == "horimetro":
            tipo = "Horímetro"

    if tipo in ("Condição", "Condicao"):
        return "Depende de análise preditiva"

    if tipo in ("Calendário", "Calendario"):
        prox = str(task.get("Proxima_Execucao_Data", "")).strip()
        if not prox or prox in ("", "nan"):
            ultima = str(task.get("Ultima_Execucao_Data", "")).strip()
            period = 0
            try:
                period = int(float(str(task.get("Periodicidade_Dias", 0) or 0)))
            except Exception:
                pass
            if ultima and period:
                try:
                    prox = (_dt.strptime(ultima, "%d/%m/%Y") + _td(days=period)).strftime("%d/%m/%Y")
                except Exception:
                    return "Em dia"
            else:
                return "Em dia"
        try:
            diff = (_dt.strptime(prox, "%d/%m/%Y") - _agora).days
            if diff < 0:
                return "Vencida"
            if diff <= 15:
                return "Próxima do vencimento"
            return "Em dia"
        except Exception:
            return "Em dia"

    if tipo in ("Horímetro", "Horimetro"):
        prox_h = str(task.get("Proxima_Execucao_Horimetro", "")).strip()
        if not prox_h or prox_h in ("", "nan"):
            ultima_h = str(task.get("Ultima_Execucao_Horimetro", "")).strip()
            period_h = 0
            try:
                period_h = int(float(str(task.get("Periodicidade_Horas", 0) or 0)))
            except Exception:
                pass
            if period_h:
                try:
                    base = int(float(ultima_h)) if ultima_h and ultima_h not in ("", "nan") else 0
                    prox_h = str(base + period_h)
                except Exception:
                    return "Em dia"
            else:
                return "Em dia"
        try:
            ph = int(float(prox_h))
            if horimetro_atual >= ph:
                return "Vencida"
            if horimetro_atual >= ph - 500:
                return "Próxima do vencimento"
            return "Em dia"
        except Exception:
            return "Em dia"

    return "Em dia"


def get_maintenance_plans(
    client_id: str = "",
    ativo_id: str = "",
    status: str = "",
    staff: bool = True,
) -> pd.DataFrame:
    """Retorna planos de manutenção. staff=False → somente do próprio cliente."""
    df = load_sheet("MaintenancePlans")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_MAINT_PLANS:
        if col not in df.columns:
            df[col] = ""
    if not staff:
        if not client_id:
            return pd.DataFrame()
        df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
    else:
        if client_id:
            df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
    if ativo_id:
        df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]
    if status:
        df = df[df["Status"].str.strip() == status]
    return df.reset_index(drop=True)


def add_maintenance_plan(dados: dict, created_by: str = "") -> str | None:
    """Cria plano de manutenção. cliente_id DEVE vir da sessão do supervisor."""
    if not dados.get("cliente_id"):
        return None
    _ensure_tab_headers("MaintenancePlans", _HEADERS_MAINT_PLANS)
    plan_id = _gerar_id("PLAN")
    now     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("MaintenancePlans", [
        plan_id,
        dados.get("cliente_id", ""),
        dados.get("ativo_id", ""),
        dados.get("nome", ""),
        dados.get("descricao", ""),
        dados.get("status", "Ativo"),
        now,
        now,
    ])
    return plan_id if ok else None


def update_maintenance_plan(plan_id: str, campos: dict) -> bool:
    """Atualiza campos de um plano de manutenção."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("MaintenancePlans")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        cell = ws.find(plan_id, in_column=headers.index("Id") + 1)
        if not cell:
            return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        campos.setdefault("Updated_At", now)
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        _clear_read_caches()
        return True
    except Exception:
        return False


@st.cache_data(ttl=20, show_spinner=False)
def get_maintenance_tasks(
    client_id: str = "",
    plan_id: str = "",
    ativo_id: str = "",
    tipo: str = "",
    staff: bool = True,
) -> pd.DataFrame:
    """Retorna tarefas de manutenção. staff=False → somente do cliente, sem Obs_Interna."""
    df = load_sheet("MaintenanceTasks")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_MAINT_TASKS:
        if col not in df.columns:
            df[col] = ""
    if not staff:
        if not client_id:
            return pd.DataFrame()
        df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
        # Nunca expõe obs_interna ao cliente
        if "Obs_Interna" in df.columns:
            df = df.drop(columns=["Obs_Interna"])
    else:
        if client_id:
            df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
    if plan_id:
        df = df[df["Plano_Id"].str.strip() == plan_id.strip()]
    if ativo_id:
        df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]
    if tipo:
        df = df[df["Tipo_Manutencao"].str.strip() == tipo.strip()]
    return df.reset_index(drop=True)


def get_maintenance_task_by_id(task_id: str) -> dict | None:
    """Retorna dict da tarefa ou None."""
    df = load_sheet("MaintenanceTasks")
    if df.empty or "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == task_id.strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    return {col: str(row.get(col, "")).strip() for col in df.columns}


def add_maintenance_task(dados: dict, created_by: str = "") -> str | None:
    """Cria tarefa de manutenção. cliente_id DEVE vir da sessão do supervisor.

    SEGURANÇA:
    - Tarefas por Condição NUNCA têm próxima_execucao automática.
    - 20.000h não cria tarefa automática de overhaul.
    - Obs_Interna nunca é exibida ao cliente.
    """
    if not dados.get("cliente_id"):
        return None
    _ensure_tab_headers("MaintenanceTasks", _HEADERS_MAINT_TASKS)
    task_id = _gerar_id("TASK")
    now     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    tipo    = dados.get("tipo_manutencao", "Calendário")
    # Condição: status fixo "Depende de análise preditiva", sem proxima execucao
    status_inicial = (
        "Depende de análise preditiva" if tipo == "Condição"
        else dados.get("status", "Em dia")
    )
    ok = append_row("MaintenanceTasks", [
        task_id,
        dados.get("cliente_id", ""),
        dados.get("ativo_id", ""),
        dados.get("componente_id", ""),
        dados.get("plano_id", ""),
        dados.get("nome_tarefa", ""),
        dados.get("categoria", ""),
        tipo,
        str(dados.get("periodicidade_dias", "") or ""),
        str(dados.get("periodicidade_horas", "") or ""),
        dados.get("ultima_execucao_data", ""),
        str(dados.get("ultima_execucao_horimetro", "") or ""),
        dados.get("proxima_execucao_data", ""),
        str(dados.get("proxima_execucao_horimetro", "") or ""),
        status_inicial,
        dados.get("prioridade", "Média"),
        "Sim" if dados.get("depende_relatorio") else "Não",
        dados.get("origem", "Cadastro manual"),
        dados.get("descricao", ""),
        dados.get("recomendacao", ""),
        dados.get("obs_interna", ""),
        now,
        now,
    ])
    if ok and tipo == "Condição" and dados.get("ativo_id"):
        try:
            add_report_timeline_event({
                "ativo_id": dados.get("ativo_id", ""), "cliente_id": dados.get("cliente_id", ""),
                "tipo": "recomendacao_tecnica",
                "titulo": dados.get("nome_tarefa", "Recomendação por condição"),
                "descricao": dados.get("recomendacao", "") or dados.get("descricao", ""),
                "origem": "Manutenção por Condição", "visivel_cliente": "true",
            })
        except Exception:
            pass
    return task_id if ok else None


def update_maintenance_task(task_id: str, campos: dict) -> bool:
    """Atualiza campos de uma tarefa de manutenção."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("MaintenanceTasks")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        cell = ws.find(task_id, in_column=headers.index("Id") + 1)
        if not cell:
            return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        campos.setdefault("Updated_At", now)
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        _clear_read_caches()
        return True
    except Exception:
        return False


def delete_maintenance_task(task_id: str) -> bool:
    """Remove tarefa de manutenção."""
    return delete_row_by_id("MaintenanceTasks", "Id", task_id)


def get_maintenance_executions(
    client_id: str = "",
    task_id: str = "",
    ativo_id: str = "",
    limit: int = 50,
) -> pd.DataFrame:
    """Retorna execuções de manutenção."""
    df = load_sheet("MaintenanceExecutions")
    if df.empty:
        return pd.DataFrame()
    for col in _HEADERS_MAINT_EXEC:
        if col not in df.columns:
            df[col] = ""
    if client_id:
        df = df[df["Cliente_Id"].str.strip().str.lower() == client_id.strip().lower()]
    if ativo_id:
        df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]
    if task_id:
        df = df[df["Task_Id"].str.strip() == task_id.strip()]
    return df.iloc[-limit:].iloc[::-1].reset_index(drop=True)


def add_maintenance_execution(dados: dict) -> str | None:
    """Registra execução de uma tarefa de manutenção."""
    _ensure_tab_headers("MaintenanceExecutions", _HEADERS_MAINT_EXEC)
    exec_id = _gerar_id("EXEC")
    now     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("MaintenanceExecutions", [
        exec_id,
        dados.get("cliente_id", ""),
        dados.get("ativo_id", ""),
        dados.get("task_id", ""),
        dados.get("executado_em", now[:10].replace("-", "/")),
        str(dados.get("horimetro_execucao", "") or ""),
        dados.get("responsavel", ""),
        dados.get("descricao_execucao", ""),
        dados.get("evidencias", ""),
        dados.get("arquivo_url", ""),
        dados.get("obs_interna", ""),
        now,
    ])
    return exec_id if ok else None


def complete_maintenance_task(task_id: str, exec_dados: dict, executed_by: str = "") -> dict:
    """Conclui tarefa: registra execução, atualiza próxima execução, cria evento na timeline.

    SEGURANÇA:
    - Obs_Interna nunca é enviada ao cliente.
    - Não conclui automaticamente tarefas por Condição sem avaliação técnica.
    - 20.000h não dispara overhaul automático.
    """
    from datetime import timedelta as _td, datetime as _dt

    task = get_maintenance_task_by_id(task_id)
    if not task:
        return {"ok": False, "erro": "Tarefa não encontrada."}

    tipo        = str(task.get("Tipo_Manutencao", "")).strip()
    nome        = str(task.get("Nome_Tarefa", "")).strip()
    cliente_id  = str(task.get("Cliente_Id", "")).strip()
    ativo_id    = str(task.get("Ativo_Id", "")).strip()
    period_dias = 0
    period_h    = 0
    try:
        period_dias = int(float(str(task.get("Periodicidade_Dias", 0) or 0)))
    except Exception:
        pass
    try:
        period_h = int(float(str(task.get("Periodicidade_Horas", 0) or 0)))
    except Exception:
        pass

    data_exec = exec_dados.get("executado_em", _dt.now().strftime("%d/%m/%Y"))
    h_exec    = exec_dados.get("horimetro_execucao", "")

    # 1. Registro de execução
    exec_id = add_maintenance_execution({
        "cliente_id":         cliente_id,
        "ativo_id":           ativo_id,
        "task_id":            task_id,
        "executado_em":       data_exec,
        "horimetro_execucao": h_exec,
        "responsavel":        executed_by,
        "descricao_execucao": exec_dados.get("descricao", ""),
        "evidencias":         exec_dados.get("evidencias", ""),
        "arquivo_url":        exec_dados.get("arquivo_url", ""),
        "obs_interna":        exec_dados.get("obs_interna", ""),
    })

    # 2. Calcula próxima execução e atualiza tarefa
    upd: dict = {
        "Ultima_Execucao_Data":      data_exec,
        "Ultima_Execucao_Horimetro": str(h_exec or ""),
    }

    if tipo in ("Calendário", "Calendario") and period_dias:
        try:
            prox = (_dt.strptime(data_exec, "%d/%m/%Y") + _td(days=period_dias)).strftime("%d/%m/%Y")
            upd["Proxima_Execucao_Data"] = prox
        except Exception:
            pass

    elif tipo in ("Horímetro", "Horimetro") and period_h and h_exec:
        try:
            prox_h = int(float(str(h_exec))) + period_h
            upd["Proxima_Execucao_Horimetro"] = str(prox_h)
        except Exception:
            pass

    update_maintenance_task(task_id, upd)

    # 3. Evento na timeline
    descr_tl = (
        f"Tarefa '{nome}' concluída em {data_exec}"
        + (f" com horímetro {h_exec}h." if h_exec else ".")
        + (f" Responsável: {executed_by}." if executed_by else "")
    )
    add_report_timeline_event({
        "ativo_id":        ativo_id or cliente_id,
        "cliente_id":      cliente_id,
        "tipo":            "manutencao_concluida",
        "titulo":          f"Manutenção concluída: {nome}",
        "descricao":       descr_tl,
        "data":            data_exec,
        "origem":          "Plano de Manutenção",
        "report_id":       "",
        "visivel_cliente": "true",
        "obs_interna":     exec_dados.get("obs_interna", ""),
    })

    return {"ok": True, "exec_id": exec_id}


def generate_maintenance_alerts(client_id: str = "", ativo_id: str = "") -> int:
    """Escaneia tarefas e gera alertas internos para próximas do vencimento / vencidas.

    SEGURANÇA:
    - Tarefas por Condição nunca geram alerta automático.
    - 20.000h não gera alerta de overhaul.
    - Sem WhatsApp / e-mail.
    """
    df = get_maintenance_tasks(client_id=client_id, ativo_id=ativo_id, staff=True)
    if df.empty:
        return 0

    count = 0
    for _, row in df.iterrows():
        task     = row.to_dict()
        tipo     = str(task.get("Tipo_Manutencao", "")).strip()
        if tipo in ("Condição", "Condicao"):
            continue   # condição nunca vira alerta automático

        aid      = str(task.get("Ativo_Id", "")).strip()
        cid      = str(task.get("Cliente_Id", "")).strip()
        h_atual  = get_horimetro(aid) or 0
        status   = calc_task_status(task, h_atual)

        if status not in ("Próxima do vencimento", "Vencida"):
            continue

        nome    = str(task.get("Nome_Tarefa", "")).strip()
        prio    = "Urgente" if status == "Vencida" else "Alta"
        titulo  = f"{'Manutenção vencida' if status == 'Vencida' else 'Manutenção próxima'}: {nome}"
        msg     = f"Tarefa '{nome}' está com status '{status}'."
        if aid:
            msg += f" Ativo: {aid}."

        # Empresa para o alerta
        empresa = cid
        try:
            df_cli = get_all_clientes()
            cid_col = "Client_Id" if "Client_Id" in df_cli.columns else "Cliente_Id"
            if cid_col in df_cli.columns:
                m = df_cli[
                    df_cli[cid_col].astype(str).str.strip().str.lower() == cid.lower()
                ]
                empresa = str(m.iloc[0].get("Empresa", cid)) if not m.empty else cid
        except Exception:
            pass

        add_alerta_sv(
            client_id  = cid,
            empresa    = empresa,
            titulo     = titulo,
            descricao  = msg,
            prioridade = prio,
        )
        count += 1

    return count


# ── Chamados V2 — campos estendidos ──────────────────────────────────────────

# ── Sistema GUT (Gravidade x Urgência x Tendência) ────────────────────────────
# Colunas adicionadas de forma não-destrutiva (ver _ensure_extra_cols) em
# MaintenanceTasks, AlertasSV, Chamados e TechnicalReports.
_HEADERS_GUT = [
    "Gut_Gravidade", "Gut_Urgencia", "Gut_Tendencia",
    "Gut_Score", "Gut_Prioridade", "Gut_Observacao",
]


def _ensure_extra_cols(tab_name: str, needed_cols: list) -> None:
    """Garante que colunas extras existam num sheet já existente, sem apagar
    nem reordenar dados — adiciona ao final do cabeçalho as que faltarem.
    Mesmo padrão usado por _ensure_chamados_v2_cols, generalizado para
    qualquer aba (usado pelas colunas GUT em várias abas).

    BUG CORRIGIDO: a grade da planilha (ws.col_count) tem um limite físico
    fixo (visto na prática: BibliotecaTecnica tinha só 28 colunas) — tentar
    escrever além dele lança APIError "exceeds grid limits", e como esta
    função sempre engoliu a exceção (try/except: pass), a coluna faltante
    ficava faltando pra sempre, sem nenhum aviso. Agora expande a grade
    (ws.add_cols) antes de tentar escrever, quando necessário."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet(tab_name)
        headers = ws.row_values(1)
        if not headers:
            return
        faltantes = [col for col in needed_cols if col not in headers]
        if not faltantes:
            return
        vagas_livres = ws.col_count - len(headers)
        if len(faltantes) > vagas_livres:
            ws.add_cols(len(faltantes) - vagas_livres)
        for col in faltantes:
            ws.update_cell(1, len(headers) + 1, col)
            headers.append(col)
        _clear_read_caches()
    except Exception:
        pass


def _gut_campos(gravidade, urgencia, tendencia, observacao: str = "") -> dict:
    """Monta os campos Gut_* para as funções update_*() — recalcula score e
    prioridade a partir de G/U/T sempre que chamada, nunca grava um score
    desatualizado. Se G/U/T não formarem um GUT válido, grava as notas que
    vieram (podem estar parcialmente preenchidas) e deixa score/prioridade
    em branco em vez de um valor errado."""
    resultado = gut.calculate_gut(gravidade, urgencia, tendencia)
    return {
        "Gut_Gravidade":  gravidade if gravidade not in (None, "") else "",
        "Gut_Urgencia":   urgencia if urgencia not in (None, "") else "",
        "Gut_Tendencia":  tendencia if tendencia not in (None, "") else "",
        "Gut_Score":      resultado["score"] if resultado else "",
        "Gut_Prioridade": resultado["prioridade"] if resultado else "",
        "Gut_Observacao": observacao,
    }


def update_maintenance_task_gut(task_id: str, gravidade, urgencia, tendencia,
                                observacao: str = "") -> bool:
    """Define/atualiza a prioridade GUT de uma tarefa de manutenção.
    Uso: Supervisão define G/U/T aqui; o cliente só visualiza o resultado."""
    _ensure_extra_cols("MaintenanceTasks", _HEADERS_GUT)
    return update_maintenance_task(
        task_id, _gut_campos(gravidade, urgencia, tendencia, observacao))


def update_alerta_gut(alerta_id: str, gravidade, urgencia, tendencia,
                      observacao: str = "") -> bool:
    """Define/atualiza a prioridade GUT de um alerta técnico."""
    _ensure_extra_cols("AlertasSV", _HEADERS_GUT)
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("AlertasSV")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        cell = ws.find(alerta_id, in_column=headers.index("Id") + 1)
        if not cell:
            return False
        campos = _gut_campos(gravidade, urgencia, tendencia, observacao)
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        _clear_read_caches()
        return True
    except Exception:
        return False


def update_chamado_gut(chamado_id: str, gravidade, urgencia, tendencia,
                       observacao: str = "") -> bool:
    """Define/atualiza a prioridade GUT de um chamado técnico."""
    _ensure_extra_cols("Chamados", _HEADERS_GUT)
    return update_chamado(
        chamado_id, _gut_campos(gravidade, urgencia, tendencia, observacao))


def update_report_gut(report_id: str, gravidade, urgencia, tendencia,
                      observacao: str = "") -> bool:
    """Define/atualiza a prioridade GUT da recomendação de um relatório técnico."""
    _ensure_extra_cols("TechnicalReports", _HEADERS_GUT)
    return update_technical_report(
        report_id, _gut_campos(gravidade, urgencia, tendencia, observacao))


def get_gut_summary(client_id: str) -> list[dict]:
    """Agrega itens com GUT calculado do cliente — manutenção, alertas,
    chamados e recomendações de relatórios — numa lista única ordenada por
    score GUT decrescente. Usado por Dashboard, detalhe do Ativo e Assistente.

    Cada item também funciona como uma "recomendação por condição" no
    formato pedido (ativo_id, cliente_id, origem, descrição, ação
    recomendada, GUT, status, created_at) — não existe uma aba separada só
    de recomendações; este é o registro consolidado, calculado a partir dos
    4 sistemas de origem (não persistido — sempre recalculado na leitura).
    Tarefas de manutenção do tipo "Condição" vêm com "subtipo": "Condição",
    para quem quiser distinguir recomendação por condição das preventivas
    comuns sem quebrar quem já filtra só por origem == "manutencao".

    SEGURANÇA: todas as fontes já filtram por client_id/staff=False — nunca
    lê dado de outro cliente, rascunho ou observação interna.

    Cada item: {"origem": "manutencao"|"alerta"|"chamado"|"relatorio",
                "titulo": str, "ativo_id": str, "score": int, "prioridade": str,
                "id": str, "cliente_id": str, "descricao": str,
                "acao_recomendada": str, "status": str, "created_at": str,
                "subtipo": str (só em "manutencao")}
    """
    itens: list[dict] = []
    if not client_id:
        return itens

    try:
        df = get_maintenance_tasks(client_id=client_id, staff=False)
        if not df.empty:
            for _, row in df.iterrows():
                r = gut.calculate_gut(row.get("Gut_Gravidade"), row.get("Gut_Urgencia"),
                                      row.get("Gut_Tendencia"))
                if r:
                    itens.append({
                        "origem": "manutencao",
                        "titulo": str(row.get("Nome_Tarefa", "")).strip() or "Tarefa preventiva",
                        "ativo_id": str(row.get("Ativo_Id", "")).strip(),
                        "score": r["score"], "prioridade": r["prioridade"],
                        "id": str(row.get("Id", "")).strip(),
                        "cliente_id": client_id,
                        "descricao": str(row.get("Descricao", "")).strip(),
                        "acao_recomendada": gut.gut_acao_recomendada(r["prioridade"]),
                        "status": str(row.get("Status", "")).strip(),
                        "created_at": str(row.get("Created_At", "")).strip(),
                        "subtipo": str(row.get("Tipo_Manutencao", "")).strip(),
                    })
    except Exception:
        pass

    try:
        df = get_alertas_sv(client_id)
        if not df.empty:
            for _, row in df.iterrows():
                r = gut.calculate_gut(row.get("Gut_Gravidade"), row.get("Gut_Urgencia"),
                                      row.get("Gut_Tendencia"))
                if r:
                    itens.append({
                        "origem": "alerta",
                        "titulo": str(row.get("Titulo", "")).strip() or "Alerta",
                        "ativo_id": str(row.get("Ativo_Id", "")).strip(),
                        "score": r["score"], "prioridade": r["prioridade"],
                        "id": str(row.get("Id", "")).strip(),
                        "cliente_id": client_id,
                        "descricao": str(row.get("Descricao", "")).strip(),
                        "acao_recomendada": gut.gut_acao_recomendada(r["prioridade"]),
                        "status": "",
                        "created_at": str(row.get("Criado_Em", "")).strip(),
                    })
    except Exception:
        pass

    try:
        df = get_chamados_v2(client_id=client_id)
        if not df.empty:
            for _, row in df.iterrows():
                r = gut.calculate_gut(row.get("Gut_Gravidade"), row.get("Gut_Urgencia"),
                                      row.get("Gut_Tendencia"))
                if r:
                    itens.append({
                        "origem": "chamado",
                        "titulo": str(row.get("Titulo", "")).strip() or "Chamado técnico",
                        "ativo_id": str(row.get("Ativo_Id", "")).strip(),
                        "score": r["score"], "prioridade": r["prioridade"],
                        "id": str(row.get("Id", "")).strip(),
                        "cliente_id": client_id,
                        "descricao": str(row.get("Descricao", "")).strip(),
                        "acao_recomendada": gut.gut_acao_recomendada(r["prioridade"]),
                        "status": str(row.get("Status", "")).strip(),
                        "created_at": str(row.get("Aberto_Em", "")).strip(),
                    })
    except Exception:
        pass

    try:
        df = get_technical_reports(client_id=client_id, staff=False)
        if not df.empty:
            for _, row in df.iterrows():
                r = gut.calculate_gut(row.get("Gut_Gravidade"), row.get("Gut_Urgencia"),
                                      row.get("Gut_Tendencia"))
                if r:
                    itens.append({
                        "origem": "relatorio",
                        "titulo": str(row.get("Titulo", "")).strip() or "Recomendação técnica",
                        "ativo_id": str(row.get("Ativo_Id", "")).strip(),
                        "score": r["score"], "prioridade": r["prioridade"],
                        "id": str(row.get("Id", "")).strip(),
                        "cliente_id": client_id,
                        "descricao": str(row.get("Recomendacoes", "")).strip()
                                     or str(row.get("Resumo", "")).strip(),
                        "acao_recomendada": gut.gut_acao_recomendada(r["prioridade"]),
                        "status": str(row.get("Status", "")).strip(),
                        "created_at": str(row.get("Created_At", "")).strip(),
                    })
    except Exception:
        pass

    itens.sort(key=lambda x: x["score"], reverse=True)
    return itens


def get_recomendacoes_condicao(client_id: str) -> list[dict]:
    """Só as tarefas de manutenção por Condição com GUT — o subconjunto de
    get_gut_summary() que representa "Recomendação por Condição" no sentido
    estrito (overhaul, troca de rolamento, kit revisão — nunca automáticos
    por horímetro, sempre dependem de avaliação técnica)."""
    return [i for i in get_gut_summary(client_id)
            if i["origem"] == "manutencao" and i.get("subtipo") == "Condição"]


# ── Snapshots do cliente (GUT/Score) — base para o comparativo ────────────────
# GUT e Score de saúde não têm histórico (sempre recalculados na leitura —
# ver docstring de get_gut_summary). snapshot_cliente() grava uma foto leve
# a cada reunião registrada / primeiro comparativo sem reunião anterior, pra
# que comparativos FUTUROS tenham uma base real de "antes". O snapshot mais
# antigo nunca é apagado automaticamente (histórico cresce devagar — 1 linha
# por reunião/comparativo, não por dia).
_HEADERS_CLIENT_SNAPSHOTS = [
    "Id", "Cliente_Id", "Data", "Score_Medio", "Gut_Top_Json",
    "Ativos_Criticos", "Ativos_Atencao", "Created_At",
]


def snapshot_cliente(cliente_id: str) -> str | None:
    """Grava um snapshot leve de GUT/score do cliente. Retorna o Id gerado.

    Se o snapshot ANTERIOR mostrar uma mudança relevante no maior item GUT
    (score mudou, ou prioridade Alta/Crítica mudou de quantidade), grava um
    evento gut_alterado na timeline do ativo do item de maior GUT — sinal de
    mudança sem esperar o usuário abrir o comparativo.
    """
    if not cliente_id:
        return None
    cliente_id = cliente_id.strip().lower()
    import json as _json

    try:
        df_ativos = get_all_ativos_sv()
        if not df_ativos.empty and "Client_Id" in df_ativos.columns:
            df_ativos = df_ativos[df_ativos["Client_Id"].astype(str).str.strip().str.lower() == cliente_id]
        scores = pd.to_numeric(df_ativos.get("Score", pd.Series(dtype=float)), errors="coerce").dropna()
        score_medio = round(float(scores.mean()), 1) if len(scores) else None
        st_norm = df_ativos.get("Status", pd.Series(dtype=str)).astype(str).str.strip().str.lower()
        ativos_criticos = int(st_norm.isin(["critico", "crítico", "urgente"]).sum())
        ativos_atencao  = int(st_norm.isin(["atencao", "atenção"]).sum())
    except Exception:
        score_medio, ativos_criticos, ativos_atencao = None, 0, 0

    try:
        gut_itens = get_gut_summary(cliente_id)
        gut_top = gut_itens[:10]
    except Exception:
        gut_top = []

    _ensure_tab_headers("ClientSnapshots", _HEADERS_CLIENT_SNAPSHOTS)
    snap_id = _gerar_id("SNAP")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("ClientSnapshots", [
        snap_id, cliente_id, datetime.now().strftime("%d/%m/%Y"),
        str(score_medio) if score_medio is not None else "",
        _json.dumps(gut_top, ensure_ascii=False),
        str(ativos_criticos), str(ativos_atencao), now,
    ])
    if not ok:
        return None

    # Compara com o snapshot anterior (se houver) pra sinalizar gut_alterado
    try:
        anterior = get_last_snapshot(cliente_id, excluir_id=snap_id)
        if anterior and gut_top:
            top_novo = gut_top[0]
            top_antigo_lista = anterior.get("gut_top", [])
            top_antigo = top_antigo_lista[0] if top_antigo_lista else None
            mudou = (
                top_antigo is None
                or top_antigo.get("id") != top_novo.get("id")
                or top_antigo.get("score") != top_novo.get("score")
            )
            if mudou and top_novo.get("ativo_id"):
                add_report_timeline_event({
                    "ativo_id": top_novo["ativo_id"], "cliente_id": cliente_id,
                    "tipo": "gut_alterado",
                    "titulo": f"Maior GUT: {top_novo.get('titulo', 'item')} (score {top_novo.get('score')})",
                    "descricao": top_novo.get("descricao", ""),
                    "origem": "GUT", "visivel_cliente": "true",
                })
    except Exception:
        pass

    return snap_id


def get_last_snapshot(cliente_id: str, excluir_id: str = "") -> dict | None:
    """Snapshot mais recente do cliente (por Data/Created_At), ou None se
    nunca houve um. excluir_id evita comparar o snapshot que acabou de ser
    criado com ele mesmo."""
    if not cliente_id:
        return None
    import json as _json
    df = load_sheet("ClientSnapshots")
    if df.empty or "Cliente_Id" not in df.columns:
        return None
    df = df[df["Cliente_Id"].astype(str).str.strip().str.lower() == cliente_id.strip().lower()]
    if excluir_id:
        df = df[df["Id"].astype(str).str.strip() != excluir_id]
    if df.empty:
        return None
    df = df.copy()
    df["_dt"] = pd.to_datetime(df.get("Created_At", ""), dayfirst=True, errors="coerce", format="%d/%m/%Y %H:%M:%S")
    df = df.sort_values("_dt", ascending=False)
    row = df.iloc[0]
    try:
        gut_top = _json.loads(row.get("Gut_Top_Json", "") or "[]")
    except Exception:
        gut_top = []
    score_medio = row.get("Score_Medio", "")
    try:
        score_medio = float(score_medio) if score_medio not in ("", "nan") else None
    except Exception:
        score_medio = None
    return {
        "id": str(row.get("Id", "")), "data": str(row.get("Data", "")),
        "score_medio": score_medio,
        "ativos_criticos": int(float(row.get("Ativos_Criticos", 0) or 0)),
        "ativos_atencao": int(float(row.get("Ativos_Atencao", 0) or 0)),
        "gut_top": gut_top,
    }


# ── Reuniões com o cliente (client_meetings) ──────────────────────────────────
# Permite que o comparativo "O que mudou desde a última reunião?" saiba qual
# foi a última reunião registrada, sem precisar de escolha manual de período
# toda vez. Observacao é sempre interna — nunca aparece pro cliente (mesmo
# padrão de Obs_Interna usado no resto do projeto).
_HEADERS_CLIENT_MEETINGS = [
    "Id", "Cliente_Id", "Titulo", "Data_Reuniao",
    "Periodo_Inicio", "Periodo_Fim", "Observacao", "Criado_Por", "Created_At",
]


def add_client_meeting(
    cliente_id: str, titulo: str, data_reuniao: str,
    periodo_inicio: str, periodo_fim: str,
    observacao: str = "", criado_por: str = "",
) -> str | None:
    """Registra uma reunião com o cliente. Retorna o Id ou None em falha.
    SEGURANÇA: cliente_id sempre da seleção do staff na Supervisão (nunca de
    input livre do cliente comum — reuniões só são registradas ali)."""
    if not cliente_id:
        return None
    _ensure_tab_headers("ClientMeetings", _HEADERS_CLIENT_MEETINGS)
    meeting_id = _gerar_id("MTG")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("ClientMeetings", [
        meeting_id, cliente_id.strip().lower(), titulo, data_reuniao,
        periodo_inicio, periodo_fim, observacao, criado_por, now,
    ])
    return meeting_id if ok else None


def get_client_meetings(cliente_id: str, limit: int = 50) -> pd.DataFrame:
    """Histórico de reuniões do cliente, mais recentes primeiro."""
    if not cliente_id:
        return pd.DataFrame(columns=_HEADERS_CLIENT_MEETINGS)
    df = load_sheet("ClientMeetings")
    if df.empty:
        return pd.DataFrame(columns=_HEADERS_CLIENT_MEETINGS)
    for col in _HEADERS_CLIENT_MEETINGS:
        if col not in df.columns:
            df[col] = ""
    df = df[df["Cliente_Id"].astype(str).str.strip().str.lower() == cliente_id.strip().lower()]
    if df.empty:
        return df
    df = df.copy()
    df["_dt"] = pd.to_datetime(df["Data_Reuniao"], dayfirst=True, errors="coerce")
    df = df.sort_values("_dt", ascending=False).drop(columns=["_dt"])
    return df.head(limit).reset_index(drop=True)


def get_last_meeting(cliente_id: str) -> dict | None:
    """Reunião mais recente do cliente, ou None se nunca houve uma."""
    df = get_client_meetings(cliente_id, limit=1)
    if df.empty:
        return None
    row = df.iloc[0]
    return {
        "id": str(row.get("Id", "")), "titulo": str(row.get("Titulo", "")),
        "data_reuniao": str(row.get("Data_Reuniao", "")),
        "periodo_inicio": str(row.get("Periodo_Inicio", "")),
        "periodo_fim": str(row.get("Periodo_Fim", "")),
        "observacao": str(row.get("Observacao", "")),
        "criado_por": str(row.get("Criado_Por", "")),
    }


_HEADERS_CHAMADOS_V2 = [
    "Id", "Client_Id", "Usuario_Id", "Empresa", "Email",
    "Ativo_Id", "Componente_Id", "Report_Id", "Maintenance_Task_Id", "Alert_Id",
    "Titulo", "Descricao", "Categoria", "Prioridade", "Status", "Origem",
    "Responsavel", "Planta", "Equipamento",
    "Aberto_Em", "Atualizado_Em", "Concluido_Em",
    # legado — mantidos para compatibilidade
    "Data_Abertura", "Data_Atualizacao", "Data_Encerramento",
]


def _ensure_chamados_v2_cols() -> None:
    """Garante que colunas V2 existam no sheet Chamados sem apagar dados."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Chamados")
        headers = ws.row_values(1)
        needed  = ["Ativo_Id", "Componente_Id", "Report_Id",
                   "Maintenance_Task_Id", "Alert_Id", "Categoria", "Origem"]
        for col in needed:
            if col not in headers:
                ws.update_cell(1, len(headers) + 1, col)
                headers.append(col)
    except Exception:
        pass


def abrir_chamado_v2(dados: dict) -> str | None:
    """
    Abre chamado técnico com todos os campos da V2.
    Retorna o chamado_id gerado ou None em caso de erro.
    SEGURANÇA: client_id deve vir SEMPRE da sessão antes de chamar esta função.
    """
    _ensure_chamados_v2_cols()
    chamado_id = _gerar_id("CH")
    agora      = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    # Mapa campo->valor, gravado na ORDEM REAL do cabeçalho da planilha (não
    # necessariamente a ordem de _HEADERS_CHAMADOS_V2) — a aba Chamados tem
    # cabeçalho legado com as colunas V2 anexadas ao final por
    # _ensure_chamados_v2_cols(), então uma lista posicional fixa gravava
    # cada valor na coluna errada.
    campos = {
        "Id": chamado_id,
        "Client_Id": dados.get("client_id", ""),
        "Usuario_Id": dados.get("usuario_id", ""),
        "Empresa": dados.get("empresa", dados.get("client_id", "")),
        "Email": dados.get("email", ""),
        "Ativo_Id": dados.get("ativo_id", ""),
        "Componente_Id": dados.get("componente_id", ""),
        "Report_Id": dados.get("report_id", ""),
        "Maintenance_Task_Id": dados.get("maintenance_task_id", ""),
        "Alert_Id": dados.get("alert_id", ""),
        "Titulo": dados.get("titulo", ""),
        "Descricao": dados.get("descricao", ""),
        "Categoria": dados.get("categoria", "Dúvida técnica"),
        "Prioridade": dados.get("prioridade", "Média"),
        "Status": "Aberto",
        "Origem": dados.get("origem", "Portal do Cliente"),
        "Responsavel": "",
        "Planta": dados.get("planta", ""),
        "Equipamento": dados.get("equipamento", ""),
        "Aberto_Em": agora, "Atualizado_Em": agora, "Concluido_Em": "",
        "Data_Abertura": agora, "Data_Atualizacao": agora, "Data_Encerramento": "",
    }
    try:
        headers = get_spreadsheet().worksheet("Chamados").row_values(1)
    except Exception:
        headers = []
    if headers:
        ok = append_row("Chamados", [campos.get(h, "") for h in headers])
    else:
        ok = append_row("Chamados", [campos.get(h, "") for h in _HEADERS_CHAMADOS_V2])
    if ok:
        # Cria evento no histórico técnico do ativo
        ativo_id  = dados.get("ativo_id", "")
        client_id = dados.get("client_id", "")
        titulo    = dados.get("titulo", "")
        if ativo_id:
            try:
                add_report_timeline_event({
                    "ativo_id":       ativo_id,
                    "cliente_id":     client_id,
                    "tipo":           "chamado_aberto",
                    "titulo":         f"Chamado aberto: {titulo}",
                    "descricao":      f"Chamado técnico #{chamado_id} aberto para o ativo.",
                    "data":           agora[:10],
                    "origem":         "Chamados Técnicos",
                    "report_id":      dados.get("report_id", ""),
                    "visivel_cliente": True,
                })
            except Exception:
                pass
        _clear_read_caches()
        return chamado_id
    return None


def get_chamados_v2(client_id: str, status: str = "", ativo_id: str = "") -> pd.DataFrame:
    """
    Chamados do cliente com colunas V2.
    SEGURANÇA: client_id vem da sessão — nunca do front-end.
    """
    df = load_sheet("Chamados")
    if df.empty:
        return df
    # Garante colunas mínimas
    for col in ("Client_Id", "Id", "Titulo", "Status", "Prioridade", "Categoria",
                "Origem", "Ativo_Id", "Descricao", "Aberto_Em", "Atualizado_Em"):
        if col not in df.columns:
            df[col] = ""
    # Filtro por cliente — SEMPRE
    cid_col = "Client_Id" if "Client_Id" in df.columns else "Empresa"
    df = df[df[cid_col].str.strip().str.lower() == client_id.strip().lower()]
    if status:
        df = df[df["Status"].str.strip().str.lower() == status.lower()]
    if ativo_id:
        df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]
    df["_dt"] = pd.to_datetime(df.get("Aberto_Em", pd.Series(dtype=str)), dayfirst=True, errors="coerce")
    return df.sort_values("_dt", ascending=False).drop(columns=["_dt"]).reset_index(drop=True)


def get_chamado_v2_by_id(chamado_id: str, client_id: str = "") -> dict | None:
    """
    Retorna chamado pelo Id.
    Se client_id fornecido, valida que o chamado pertence ao cliente.
    SEGURANÇA: client_id sempre da sessão.
    """
    df = load_sheet("Chamados")
    if df.empty:
        df = _mock_chamados()
    if "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == str(chamado_id).strip()]
    if match.empty:
        return None
    row = match.iloc[0].to_dict()
    # Validação de ownership
    if client_id:
        cid_col = "Client_Id" if "Client_Id" in row else "Empresa"
        if str(row.get(cid_col, "")).strip().lower() != client_id.strip().lower():
            return None  # cliente não pode ver chamado de outro cliente
    return row


def concluir_chamado(chamado_id: str, concluded_by: str = "") -> bool:
    """
    Conclui um chamado: atualiza status, data e cria evento no histórico do ativo.
    """
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = update_chamado(chamado_id, {
        "Status":            "Concluído",
        "Concluido_Em":      agora,
        "Data_Encerramento": agora,
    })
    if ok:
        # Busca ativo_id do chamado para criar evento
        chamado = get_chamado_by_id(chamado_id)
        if chamado:
            ativo_id  = str(chamado.get("Ativo_Id", "")).strip()
            client_id = str(chamado.get("Client_Id",
                           chamado.get("Empresa", ""))).strip()
            titulo    = str(chamado.get("Titulo", "")).strip()
            if ativo_id:
                try:
                    add_report_timeline_event({
                        "ativo_id":       ativo_id,
                        "cliente_id":     client_id,
                        "tipo":           "chamado_concluido",
                        "titulo":         f"Chamado concluído: {titulo}",
                        "descricao":      f"Chamado técnico #{chamado_id} concluído por {concluded_by or 'Pred.IO'}.",
                        "data":           agora[:10],
                        "origem":         "Chamados Técnicos",
                        "visivel_cliente": True,
                    })
                except Exception:
                    pass
    return ok


def responder_chamado(chamado_id: str, mensagem: str, autor: str,
                      novo_status: str = "") -> bool:
    """
    Registra resposta visível ao cliente + atualiza status se informado.
    Cria evento no histórico do ativo quando há ativo vinculado.
    """
    ok = add_mensagem(
        chamado_id    = chamado_id,
        autor         = autor,
        autor_tipo    = "funcionario",
        mensagem      = mensagem,
        visivel_cliente = True,
        tipo_mensagem = "resposta_predio",
    )
    if ok and novo_status:
        chamado    = get_chamado_by_id(chamado_id)
        status_ant = str(chamado.get("Status", "")) if chamado else ""
        update_chamado(chamado_id, {"Status": novo_status})
        if chamado and status_ant and status_ant != novo_status:
            add_mensagem(
                chamado_id    = chamado_id,
                autor         = "sistema",
                autor_tipo    = "sistema",
                mensagem      = f"Status alterado: {status_ant} → {novo_status}",
                visivel_cliente = True,
                tipo_mensagem = "alteracao_status",
            )
        # Evento no histórico do ativo quando respondido
        if chamado:
            ativo_id  = str(chamado.get("Ativo_Id", "")).strip()
            client_id = str(chamado.get("Client_Id",
                           chamado.get("Empresa", ""))).strip()
            titulo    = str(chamado.get("Titulo", "")).strip()
            if ativo_id:
                try:
                    add_report_timeline_event({
                        "ativo_id":       ativo_id,
                        "cliente_id":     client_id,
                        "tipo":           "chamado_respondido",
                        "titulo":         f"Chamado respondido: {titulo}",
                        "descricao":      f"Pred.IO respondeu o chamado #{chamado_id}.",
                        "data":           datetime.now().strftime("%d/%m/%Y"),
                        "origem":         "Chamados Técnicos",
                        "visivel_cliente": True,
                    })
                except Exception:
                    pass
    return ok


@st.cache_data(ttl=20, show_spinner=False)
def get_chamados_resumo_assistente(client_id: str, ativo_id: str = "") -> list[dict]:
    """
    Resumo de chamados para o Assistente Técnico.
    Nunca retorna observações internas.
    SEGURANÇA: client_id sempre da sessão.
    """
    df = get_chamados_v2(client_id=client_id, ativo_id=ativo_id)
    if df.empty:
        # Fallback para função legada
        df = get_chamados(client_id)
    if df.empty:
        return []
    result = []
    for _, r in df.iterrows():
        result.append({
            "id":         str(r.get("Id", "")).strip(),
            "titulo":     str(r.get("Titulo", "")).strip(),
            "status":     str(r.get("Status", "")).strip(),
            "prioridade": str(r.get("Prioridade", "")).strip(),
            "categoria":  str(r.get("Categoria", "")).strip(),
            "ativo_id":   str(r.get("Ativo_Id", "")).strip(),
            "aberto_em":  str(r.get("Aberto_Em", r.get("Data_Abertura", ""))).strip(),
        })
    return result


def delete_session(token: str) -> None:
    """Invalida o token marcando coluna Ativo=0."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Sessions")
        headers = ws.row_values(1)
        ativo_col = headers.index("Ativo") + 1 if "Ativo" in headers else 8
        cell = ws.find(token)
        if cell:
            ws.update_cell(cell.row, ativo_col, "0")
        _clear_read_caches()
    except Exception:
        pass


# ── Logos de clientes ─────────────────────────────────────────────────────────

_HEADERS_CLIENTE_LOGOS = ["Client_Id", "Logo_B64", "Updated_At"]


def _ensure_logos_tab() -> None:
    try:
        ss = get_spreadsheet()
        try:
            ss.worksheet("ClienteLogos")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title="ClienteLogos", rows=500, cols=3)
            ws.append_row(_HEADERS_CLIENTE_LOGOS, value_input_option="USER_ENTERED")
            _clear_read_caches()
    except Exception:
        pass


def get_client_logo(client_id: str) -> str:
    """Retorna o Logo_B64 do cliente ou string vazia."""
    df = load_sheet("ClienteLogos")
    if df.empty or "Client_Id" not in df.columns:
        return ""
    match = df[df["Client_Id"].str.strip().str.lower() == client_id.lower()]
    if match.empty:
        return ""
    return str(match.iloc[0].get("Logo_B64", "")).strip()


def save_client_logo(client_id: str, logo_b64: str) -> bool:
    """Salva ou atualiza a logo de um cliente (upsert por Client_Id)."""
    try:
        _ensure_logos_tab()
        ss = get_spreadsheet()
        ws = ss.worksheet("ClienteLogos")
        all_values = ws.get_all_values()
        if len(all_values) > 1:
            headers = [h.strip().title() for h in all_values[0]]
            cid_col  = headers.index("Client_Id") if "Client_Id" in headers else 0
            logo_col = (headers.index("Logo_B64") + 1) if "Logo_B64" in headers else 2
            upd_col  = (headers.index("Updated_At") + 1) if "Updated_At" in headers else 3
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) > cid_col and row[cid_col].strip().lower() == client_id.lower():
                    ws.update_cell(i, logo_col, logo_b64)
                    ws.update_cell(i, upd_col, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                    _clear_read_caches()
                    return True
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ws.append_row([client_id, logo_b64, now], value_input_option="USER_ENTERED")
        _clear_read_caches()
        return True
    except Exception:
        return False


# ── Edição de registros existentes ───────────────────────────────────────────

def update_usuario(email: str, campos: dict) -> bool:
    """Atualiza campos de um usuário/cliente pelo e-mail (busca em Usuarios e Clientes)."""
    try:
        ss = get_spreadsheet()
        for tab in ("Usuarios", "Clientes"):
            try:
                ws = ss.worksheet(tab)
            except gspread.exceptions.WorksheetNotFound:
                continue
            headers = ws.row_values(1)
            if "Email" not in headers:
                continue
            email_col = headers.index("Email") + 1
            cell = ws.find(email.strip().lower(), in_column=email_col)
            if not cell:
                continue
            row_idx = cell.row
            for campo, valor in campos.items():
                if campo in headers:
                    ws.update_cell(row_idx, headers.index(campo) + 1, str(valor))
            _clear_read_caches()
            return True
        return False
    except Exception:
        return False


def update_ativo(ativo_id: str, campos: dict) -> bool:
    """Atualiza campos de um ativo existente pelo Id."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("Ativos")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell = ws.find(ativo_id, in_column=id_col)
        if not cell:
            return False
        row_idx = cell.row
        campos = dict(campos)
        campos["Data"] = datetime.now().strftime("%d/%m/%Y")
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(row_idx, headers.index(campo) + 1, str(valor))
        _clear_read_caches()
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# RELATÓRIOS EXECUTIVOS — aba RelatoriosExecutivos
# ═══════════════════════════════════════════════════════════════════════════════

_HEADERS_RELATORIOS_EXEC = [
    "Id", "Client_Id", "Ativo_Id", "Titulo", "Status",
    "Gerado_Em", "Atualizado_Em", "Publicado_Em", "Gerado_Por",
    "Periodo_Inicio", "Periodo_Fim",
    "Versao", "Resumo_Executivo", "Obs_Interna",
    "Arquivo_Revisado_Url", "Arquivo_Revisado_Nome",
]


@st.cache_data(ttl=30)
def get_relatorios_executivos(client_id: str, ativo_id: str = "") -> pd.DataFrame:
    """
    Retorna relatórios executivos do cliente.
    SEGURANÇA: client_id vem sempre da sessão.
    """
    try:
        df = load_sheet("RelatoriosExecutivos")
    except Exception:
        return pd.DataFrame(columns=_HEADERS_RELATORIOS_EXEC)

    if df.empty:
        return df

    for col in _HEADERS_RELATORIOS_EXEC:
        if col not in df.columns:
            df[col] = ""

    df = df[df["Client_Id"].str.strip().str.lower() == client_id.strip().lower()]

    if ativo_id:
        df = df[df["Ativo_Id"].str.strip() == ativo_id.strip()]

    df["_dt"] = pd.to_datetime(df.get("Gerado_Em", pd.Series(dtype=str)), dayfirst=True, errors="coerce")
    return df.sort_values("_dt", ascending=False).drop(columns=["_dt"]).reset_index(drop=True)


def add_relatorio_executivo(
    client_id: str,
    ativo_id: str,
    titulo: str,
    gerado_por: str = "",
    periodo_inicio: str = "",
    periodo_fim: str = "",
    obs_interna: str = "",
) -> str | None:
    """
    Registra um novo relatório executivo (status inicial: Rascunho gerado).
    Retorna o Id gerado ou None em caso de erro.
    SEGURANÇA: client_id sempre da sessão.
    """
    relatorio_id = str(uuid.uuid4())[:8].upper()
    agora        = datetime.now().strftime("%d/%m/%Y %H:%M")

    row = {
        "Id":             relatorio_id,
        "Client_Id":      client_id,
        "Ativo_Id":       ativo_id,
        "Titulo":         titulo,
        "Status":         "Rascunho gerado",
        "Gerado_Em":      agora,
        "Atualizado_Em":  agora,
        "Gerado_Por":     gerado_por,
        "Periodo_Inicio": periodo_inicio,
        "Periodo_Fim":    periodo_fim,
        "Versao":         "1",
        "Obs_Interna":    obs_interna,
    }

    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("RelatoriosExecutivos")
        except Exception:
            ws = ss.add_worksheet("RelatoriosExecutivos", rows=1000, cols=len(_HEADERS_RELATORIOS_EXEC))
            ws.append_row(_HEADERS_RELATORIOS_EXEC)

        headers = ws.row_values(1)
        if not headers:
            ws.append_row(_HEADERS_RELATORIOS_EXEC)
            headers = _HEADERS_RELATORIOS_EXEC

        new_row = [str(row.get(h, "")) for h in headers]
        ws.append_row(new_row)
        _clear_read_caches()
        return relatorio_id
    except Exception:
        return None


def update_relatorio_executivo(relatorio_id: str, client_id: str, **campos) -> bool:
    """
    Atualiza campos de um relatório executivo.
    client_id é validado para garantir que o supervisor só edita relatórios do cliente correto.
    SEGURANÇA: client_id sempre da sessão.
    """
    try:
        ss      = get_spreadsheet()
        ws      = ss.worksheet("RelatoriosExecutivos")
        headers = ws.row_values(1)

        if "Id" not in headers:
            return False

        id_col  = headers.index("Id") + 1
        cell    = ws.find(relatorio_id, in_column=id_col)
        if not cell:
            return False

        row_idx = cell.row

        # Valida client_id antes de gravar
        if "Client_Id" in headers:
            cid_col_idx = headers.index("Client_Id") + 1
            existing_cid = ws.cell(row_idx, cid_col_idx).value or ""
            if existing_cid.strip().lower() != client_id.strip().lower():
                return False

        campos["Atualizado_Em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(row_idx, headers.index(campo) + 1, str(valor))
            else:
                # Coluna nova — adiciona ao cabeçalho e grava na linha
                try:
                    next_col = len(headers) + 1
                    ws.update_cell(1, next_col, campo)
                    ws.update_cell(row_idx, next_col, str(valor))
                    headers.append(campo)
                except Exception:
                    pass

        _clear_read_caches()
        return True
    except Exception:
        return False


@st.cache_data(ttl=60)
def get_relatorios_executivos_publicados(client_id: str, ativo_id: str = "") -> pd.DataFrame:
    """
    Retorna SOMENTE relatórios executivos publicados do cliente.
    Usado pelo Portal do Cliente — NUNCA retorna rascunhos ou obs_interna.
    SEGURANÇA: client_id vem sempre da sessão.
    """
    df = get_relatorios_executivos(client_id, ativo_id=ativo_id)
    if df.empty:
        return df

    # Filtra apenas publicados
    df = df[df["Status"].str.strip().str.lower() == "publicado"].copy()

    if df.empty:
        return df

    # Garante campos extras
    for col in ("Resumo_Executivo", "Arquivo_Revisado_Url", "Arquivo_Revisado_Nome", "Publicado_Em"):
        if col not in df.columns:
            df[col] = ""

    # Remove campos internos — nunca expõe ao cliente
    for col_int in ("Obs_Interna", "Gerado_Por"):
        if col_int in df.columns:
            df = df.drop(columns=[col_int])

    return df.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CHUNKS DE RELATÓRIOS TÉCNICOS — aba TechnicalReportChunks
# ═══════════════════════════════════════════════════════════════════════════════

_HEADERS_REPORT_CHUNKS = [
    "Id", "Report_Id", "Client_Id", "Ativo_Id",
    "Chunk_Index", "Titulo_Secao", "Conteudo", "Palavras_Chave", "Indexado_Em",
    # Assistente Técnico IA — metadados de filtro/auditoria por chunk
    # (colunas adicionadas de forma não-destrutiva por _ensure_extra_cols,
    # mesmo padrão de _HEADERS_TECH_REPORTS). Fonte é sempre "Pred.IO".
    "Tipo_Relatorio", "Severidade", "Data_Relatorio", "Fonte",
]

# Fonte exibida ao cliente — constante, nunca outro valor.
_FONTE_PREDIO = "Pred.IO"


def index_relatorio_tecnico(report_id: str, client_id: str, ativo_id: str, dados: dict) -> bool:
    """
    Cria/atualiza chunks do relatório técnico na aba TechnicalReportChunks.

    Ordem de prioridade dos chunks estruturados (o Assistente Técnico lê
    nesta ordem, ver ai_assistant._SYSTEM_PROMPT): Resumo Técnico (fonte
    prioritária quando preenchido) → Diagnóstico → Conclusão →
    Recomendações → medições estruturadas (Medicoes_Json). O PDF em
    Storage_Path é indexado por último — fonte ADICIONAL, nunca a única:
    falha ao ler o PDF nunca impede a indexação dos campos estruturados.

    SEGURANÇA: Obs_Interna nunca é indexada.
    """
    if not report_id or not client_id:
        return False

    _ensure_tab_headers("TechnicalReportChunks", _HEADERS_REPORT_CHUNKS)
    _ensure_extra_cols("TechnicalReportChunks", _HEADERS_REPORT_CHUNKS)

    agora      = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    titulo     = str(dados.get("Titulo",         "")).strip()
    tipo       = str(dados.get("Tipo_Servico",   "")).strip()
    sev        = str(dados.get("Severidade",     "")).strip()
    data_rel   = str(dados.get("Data_Relatorio", "")).strip()
    equip      = str(dados.get("Equipamento",    "")).strip() or ativo_id
    resumo     = str(dados.get("Resumo",         "")).strip()
    recomend   = str(dados.get("Recomendacoes",  "")).strip()
    conclusao  = str(dados.get("Conclusao",      "")).strip()
    diagnostico = str(dados.get("Diagnostico",   "")).strip()
    cid_lower  = client_id.strip().lower()

    chunks_to_insert: list[list] = []

    def _add_chunk(indice: str, titulo_secao: str, conteudo: str, palavras_chave: str) -> None:
        chunks_to_insert.append([
            _gerar_id("RCK"), report_id, cid_lower, ativo_id,
            indice, titulo_secao, conteudo, palavras_chave, agora,
            tipo, sev, data_rel, _FONTE_PREDIO,
        ])

    # Chunk 0 — ficha técnica
    meta_conteudo = (
        f"Relatório: {titulo}. "
        f"Tipo: {tipo}. Severidade: {sev}. Data: {data_rel}. Equipamento/Ativo: {equip}."
    )
    _add_chunk("0", "Ficha técnica", meta_conteudo, f"{titulo},{tipo},{sev}")

    # Resumo Técnico — fonte prioritária (resumo_tecnico), sempre o primeiro
    # chunk de conteúdo quando preenchido.
    if resumo:
        _add_chunk("1", "Resumo Técnico (fonte prioritária)", resumo, f"resumo,resumo_tecnico,{sev},{tipo}")

    if diagnostico:
        _add_chunk("2", "Diagnóstico", diagnostico, f"diagnostico,{sev},{tipo}")

    if conclusao:
        _add_chunk("3", "Conclusão", conclusao, f"conclusao,{sev},{tipo}")

    if recomend:
        _add_chunk("4", "Recomendações", recomend, f"recomendacoes,acao,{tipo}")

    # Medições estruturadas (Medicoes_Json) — pontos de vibração/inspeção
    # cadastrados manualmente na Supervisão viram texto legível para a IA.
    medicoes_json = str(dados.get("Medicoes_Json", "")).strip()
    if medicoes_json:
        try:
            import json as _json
            pontos = _json.loads(medicoes_json)
            if isinstance(pontos, list) and pontos:
                linhas_medicao = []
                for p in pontos:
                    if not isinstance(p, dict):
                        continue
                    partes_p = [f"{k}: {v}" for k, v in p.items() if str(v).strip()]
                    if partes_p:
                        linhas_medicao.append("; ".join(partes_p))
                if linhas_medicao:
                    _add_chunk("5", "Medições estruturadas", "\n".join(linhas_medicao),
                              f"medicoes,{tipo}")
        except Exception:
            pass

    # ── PDF do relatório (Etapa 6) ───────────────────────────────────────────
    # Prioridade: campos estruturados acima sempre são indexados primeiro,
    # independente do PDF. O PDF é uma fonte ADICIONAL — nunca a única
    # dependência: se o download/extração falhar, os chunks estruturados
    # já montados continuam sendo salvos normalmente (guard isolado abaixo).
    # has_conteudo_estruturado / pdf_status decidem o Status_Indexacao final
    # mais abaixo (não inventa texto se o PDF for escaneado sem OCR).
    has_conteudo_estruturado = bool(resumo or diagnostico or recomend or conclusao)
    storage_path = str(dados.get("Storage_Path", "")).strip()
    arquivo_nome_pdf = str(dados.get("Arquivo_Nome", "")).strip()
    pdf_status = None  # None (sem PDF) | "ok" | "sem_texto" | "erro"
    if storage_path:
        try:
            import drive_storage
            import document_processor
            pdf_bytes = drive_storage.download_report_pdf_bytes(storage_path)
            texto_pdf, _n_pags = document_processor.extrair_texto_pdf_bytes(
                pdf_bytes, arquivo_nome_pdf,
            )
            if texto_pdf.strip():
                pdf_status = "ok"
                doc_chunks = document_processor.criar_chunks(
                    doc_id=report_id, cliente_id=client_id, ativo_id=ativo_id,
                    componente_id="", arquivo_url=storage_path,
                    arquivo_nome=arquivo_nome_pdf, texto=texto_pdf,
                )
                base_idx = len(chunks_to_insert)
                for i, c in enumerate(doc_chunks):
                    titulo_secao = f"PDF — {c.get('titulo_secao', 'trecho')}"[:80]
                    _add_chunk(str(base_idx + i), titulo_secao,
                              c.get("conteudo", ""), f"pdf,{tipo},{sev}")
            else:
                pdf_status = "sem_texto"  # PDF escaneado, sem texto extraível
        except Exception:
            pdf_status = "erro"

    try:
        ss = get_spreadsheet()
        try:
            ws = ss.worksheet("TechnicalReportChunks")
        except Exception:
            ws = ss.add_worksheet("TechnicalReportChunks", rows=2000, cols=len(_HEADERS_REPORT_CHUNKS))
            ws.append_row(_HEADERS_REPORT_CHUNKS)

        headers = ws.row_values(1)
        if not headers:
            ws.append_row(_HEADERS_REPORT_CHUNKS)

        # Remove chunks antigos para este report_id
        all_values = ws.get_all_values()
        if len(all_values) > 1:
            hdrs = all_values[0]
            if "Report_Id" in hdrs:
                rid_col = hdrs.index("Report_Id")
                rows_to_delete = [
                    i + 2  # 1-based, +1 for header
                    for i, row in enumerate(all_values[1:])
                    if len(row) > rid_col and row[rid_col].strip() == report_id
                ]
                for row_num in reversed(rows_to_delete):
                    ws.delete_rows(row_num)

        for _i_chunk, chunk_row in enumerate(chunks_to_insert):
            try:
                ws.append_row(chunk_row)
            except Exception as e:
                import sys as _sys
                print(f"[index_relatorio_tecnico] falhou ao gravar chunk {_i_chunk + 1}/{len(chunks_to_insert)} "
                      f"do report {report_id}: {type(e).__name__}: {e}", file=_sys.stderr, flush=True)
                raise

        _clear_read_caches()

        # Etapa 2/6 — marca o relatório como preparado para o Assistente
        # Técnico. Status reflete o que de fato foi indexado: campos
        # estruturados sempre entram quando preenchidos; PDF é adicional e
        # nunca impede a indexação dos campos estruturados se falhar.
        if pdf_status == "ok":
            status_indexacao = "Indexado (texto+pdf)"
        elif has_conteudo_estruturado:
            status_indexacao = "Indexado (texto)"
        elif pdf_status == "sem_texto":
            status_indexacao = "Requer OCR"
        elif pdf_status == "erro":
            status_indexacao = "Falhou"
        else:
            # Sem PDF e sem Resumo/Recomendacoes/Conclusao preenchidos — só a
            # ficha técnica (sempre gerada) foi indexada.
            status_indexacao = "Indexado (texto)"
        try:
            _ensure_extra_cols("TechnicalReports", _HEADERS_TECH_REPORTS)
            update_technical_report(report_id, {
                "Status_Indexacao":  status_indexacao,
                "Quantidade_Chunks": str(len(chunks_to_insert)),
                "Uso_Pela_Ia":       "true",
            })
        except Exception:
            pass

        return True
    except Exception as e:
        import sys as _sys
        print(f"[index_relatorio_tecnico] falhou para report {report_id}: {type(e).__name__}: {e}",
              file=_sys.stderr, flush=True)
        return False


def reindex_technical_report(report_id: str) -> dict:
    """
    Recria os chunks de um relatório técnico para o Assistente Técnico a
    partir do conteúdo atual salvo (Resumo/Recomendações/Conclusão).

    SEGURANÇA: só indexa relatórios com Status == "Publicado". Rascunho e
    "Em revisão" nunca entram no índice — mesmo que esta função seja chamada
    para eles (ex.: por engano), o guard abaixo bloqueia. Esta é a única
    porta de entrada para (re)indexação — publish_technical_report() chama
    isto na primeira publicação; quem atualizar o CONTEÚDO de um relatório
    já publicado (edição na Supervisão, reenvio do App Relatórios) deve
    chamar de novo para os chunks não ficarem desatualizados.

    Idempotente: index_relatorio_tecnico() sempre apaga os chunks antigos do
    mesmo report_id antes de inserir os novos — nunca duplica.
    """
    rep = get_technical_report_by_id(report_id)
    if not rep:
        return {"ok": False, "erro": "Relatório não encontrado."}
    if rep.get("Status", "").strip() != "Publicado":
        return {"ok": False, "erro": "Só relatórios publicados são indexados."}
    ok = index_relatorio_tecnico(
        report_id,
        rep.get("Cliente_Id", ""),
        rep.get("Ativo_Id", ""),
        rep,
    )
    if not ok:
        return {
            "ok": False,
            "erro": "Falha ao gravar no Google Sheets — pode ser limite temporário de "
                    "requisições da API. Aguarde alguns segundos e tente novamente.",
        }
    return {"ok": ok}


@st.cache_data(ttl=60)
def get_chunks_relatorio(report_id: str, client_id: str = "") -> pd.DataFrame:
    """
    Retorna chunks do relatório técnico indexado.
    SEGURANÇA: filtra por client_id se fornecido.
    """
    df = load_sheet("TechnicalReportChunks")
    if df.empty:
        return pd.DataFrame()

    for col in _HEADERS_REPORT_CHUNKS:
        if col not in df.columns:
            df[col] = ""

    df = df[df["Report_Id"].str.strip() == report_id.strip()]

    if client_id:
        df = df[df["Client_Id"].str.strip().str.lower() == client_id.strip().lower()]

    return df.reset_index(drop=True)


def buscar_chunks_relatorios(client_id: str, query: str, top_n: int = 5) -> list[dict]:
    """Busca textual simples nos chunks de relatórios técnicos indexados de
    um cliente — mesmo algoritmo de buscar_chunks() (Biblioteca), mas em
    TechnicalReportChunks. Diferente de buscar_chunks(), mantém o Report_Id
    em cada resultado (aqui o objetivo é descobrir QUAL relatório fala
    sobre um assunto, não só mostrar um trecho solto).

    SEGURANÇA: filtra só pelos chunks do client_id — não valida Status do
    relatório (chunks só existem pra relatórios Publicados, já que
    reindex_technical_report() exige isso antes de indexar — ver
    index_relatorio_tecnico())."""
    import re as _re
    import unicodedata as _ud

    def _norm(s: str) -> str:
        n = _ud.normalize("NFD", s.lower())
        return _re.sub(r"[̀-ͯ]", "", n)

    df = load_sheet("TechnicalReportChunks")
    if df.empty:
        return []
    for col in _HEADERS_REPORT_CHUNKS:
        if col not in df.columns:
            df[col] = ""
    cid = (client_id or "").strip().lower()
    df = df[df["Client_Id"].astype(str).str.strip().str.lower() == cid]
    if df.empty:
        return []

    terms = [t for t in _norm(query).split() if len(t) > 2]
    scored = []
    for _, row in df.iterrows():
        conteudo = str(row.get("Conteudo", "")).strip()
        if not conteudo:
            continue
        item = {
            "report_id": str(row.get("Report_Id", "")).strip(),
            "titulo_secao": str(row.get("Titulo_Secao", "")).strip(),
            "conteudo": conteudo,
            "palavras_chave": str(row.get("Palavras_Chave", "")).strip(),
        }
        if not terms:
            scored.append((0, item))
            continue
        haystack = _norm(item["titulo_secao"] + " " + conteudo + " " + item["palavras_chave"])
        score = sum(1 for t in terms if t in haystack)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_n]]


def delete_chunks_relatorio(report_id: str) -> bool:
    """Remove todos os chunks indexados de um relatório técnico (usado ao
    apagar o relatório por completo, para não deixar o Assistente respondendo
    com base em um relatório que não existe mais)."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("TechnicalReportChunks")
        headers = ws.row_values(1)
        if "Report_Id" not in headers:
            return True
        col_idx = headers.index("Report_Id") + 1
        all_vals = ws.col_values(col_idx)
        to_delete = [
            i + 1 for i, v in enumerate(all_vals)
            if i > 0 and str(v).strip() == report_id.strip()
        ]
        for row_num in reversed(to_delete):
            ws.delete_rows(row_num)
        _clear_read_caches()
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ETAPA 6.7 — TEMPLATES DE NOTIFICAÇÃO  (aba NotificationTemplates)
# ═══════════════════════════════════════════════════════════════════════════════

_HEADERS_NOTIF_TEMPLATES = [
    "Id", "Nome", "Tipo_Evento", "Canal", "Assunto", "Corpo",
    "Variaveis_Permitidas", "Status", "Created_At", "Updated_At",
]


@st.cache_data(ttl=60)
def get_notification_templates(status: str = "") -> pd.DataFrame:
    """Retorna templates de notificação. status='' → todos; status='Ativo' → apenas ativos."""
    df = load_sheet("NotificationTemplates")
    if df.empty:
        return pd.DataFrame(columns=_HEADERS_NOTIF_TEMPLATES)
    for col in _HEADERS_NOTIF_TEMPLATES:
        if col not in df.columns:
            df[col] = ""
    if status:
        df = df[df["Status"].str.strip() == status]
    return df.reset_index(drop=True)


def get_notification_template_by_id(template_id: str) -> dict | None:
    """Retorna template por ID ou None."""
    df = load_sheet("NotificationTemplates")
    if df.empty or "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == template_id.strip()]
    if match.empty:
        return None
    return {col: str(match.iloc[0].get(col, "")).strip() for col in _HEADERS_NOTIF_TEMPLATES}


def add_notification_template(dados: dict) -> bool:
    """Cria um novo template de notificação."""
    _ensure_tab_headers("NotificationTemplates", _HEADERS_NOTIF_TEMPLATES)
    tpl_id = _gerar_id("TPL")
    now    = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("NotificationTemplates", [
        tpl_id,
        dados.get("nome",                 ""),
        dados.get("tipo_evento",          ""),
        dados.get("canal",                ""),
        dados.get("assunto",              ""),
        dados.get("corpo",                ""),
        dados.get("variaveis_permitidas", ""),
        dados.get("status",               "Rascunho"),
        now, now,
    ])
    if ok:
        get_notification_templates.clear()
    return ok


def update_notification_template(template_id: str, campos: dict) -> bool:
    """Atualiza campos de um template de notificação."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("NotificationTemplates")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(template_id, in_column=id_col)
        if not cell:
            return False
        campos["Updated_At"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(cell.row, headers.index(campo) + 1, str(valor))
        _clear_read_caches()
        get_notification_templates.clear()
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ETAPA 6.7 — FILA DE NOTIFICAÇÕES  (aba NotificationQueue)
# ═══════════════════════════════════════════════════════════════════════════════

_HEADERS_NOTIF_QUEUE = [
    "Id", "Client_Id", "Contato_Id", "Notification_Id", "Template_Id",
    "Tipo_Evento", "Canal", "Destinatario", "Assunto", "Corpo_Renderizado",
    "Link_Portal", "Prioridade", "Status", "Modo", "Erro_Validacao",
    "Created_At", "Updated_At",
]


def add_notification_queue_item(dados: dict) -> str:
    """
    Enfileira uma notificação em modo=Teste.
    SEGURANÇA: modo sempre 'Teste' nesta etapa. Nunca envia mensagem real.
    """
    _ensure_tab_headers("NotificationQueue", _HEADERS_NOTIF_QUEUE)
    item_id = _gerar_id("NQ")
    now     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("NotificationQueue", [
        item_id,
        dados.get("client_id",          ""),
        dados.get("contato_id",         ""),
        dados.get("notification_id",    ""),
        dados.get("template_id",        ""),
        dados.get("tipo_evento",        ""),
        dados.get("canal",              ""),
        dados.get("destinatario",       ""),
        dados.get("assunto",            ""),
        dados.get("corpo_renderizado",  ""),
        dados.get("link_portal",        ""),
        dados.get("prioridade",         "Média"),
        dados.get("status",             "Simulado"),
        "Teste",  # modo sempre Teste nesta etapa
        dados.get("erro_validacao",     ""),
        now, now,
    ])
    return item_id if ok else ""


@st.cache_data(ttl=30)
def get_notification_queue(client_id: str = "", status: str = "", limit: int = 100) -> pd.DataFrame:
    """
    Retorna fila de notificações.
    SEGURANÇA: staff chama sem client_id; por cliente, filtra pelo client_id.
    """
    df = load_sheet("NotificationQueue")
    if df.empty:
        return pd.DataFrame(columns=_HEADERS_NOTIF_QUEUE)
    for col in _HEADERS_NOTIF_QUEUE:
        if col not in df.columns:
            df[col] = ""
    if client_id:
        df = df[df["Client_Id"].str.strip().str.lower() == client_id.strip().lower()]
    if status:
        df = df[df["Status"].str.strip() == status]
    return df.tail(limit).reset_index(drop=True)


def update_notification_queue_status(item_id: str, new_status: str) -> bool:
    """Atualiza status de item da fila."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("NotificationQueue")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell   = ws.find(item_id, in_column=id_col)
        if not cell:
            return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if "Status" in headers:
            ws.update_cell(cell.row, headers.index("Status") + 1, new_status)
        if "Updated_At" in headers:
            ws.update_cell(cell.row, headers.index("Updated_At") + 1, now)
        _clear_read_caches()
        get_notification_queue.clear()
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# RESUMO EXECUTIVO POR PERÍODO — aba ExecutiveSummaries
# ═══════════════════════════════════════════════════════════════════════════════

_HEADERS_EXEC_SUMMARY = [
    "Id", "Cliente_Id", "Ativo_Id", "Gerado_Por_Usuario_Id",
    "Tipo_Resumo", "Modo", "Periodo_Inicio", "Periodo_Fim",
    "Titulo", "Resumo_Texto", "Dados_Usados", "Arquivo_Url",
    "Status", "Created_At", "Updated_At", "Report_Ids_Usados",
]


def add_executive_summary(
    cliente_id: str,
    titulo: str,
    resumo_texto: str,
    gerado_por_usuario_id: str = "",
    ativo_id: str = "",
    tipo_resumo: str = "Resumo para reunião",
    modo: str = "cliente",
    periodo_inicio: str = "",
    periodo_fim: str = "",
    dados_usados: str = "",
    report_ids_usados: str = "",
) -> str | None:
    """Registra um resumo executivo gerado. Retorna o Id ou None.

    report_ids_usados: Ids (separados por vírgula) dos TechnicalReports que
    entraram neste resumo — auditoria de fonte, permite saber exatamente de
    onde vieram as informações mostradas.

    SEGURANÇA: cliente_id sempre da sessão (ou do cliente selecionado pelo
    staff na Supervisão) — nunca de input livre do cliente comum."""
    if not cliente_id:
        return None
    _ensure_tab_headers("ExecutiveSummaries", _HEADERS_EXEC_SUMMARY)
    # Sheets criadas antes desta coluna existir não a têm no cabeçalho —
    # _ensure_tab_headers só cria cabeçalho do zero, não adiciona coluna
    # nova a uma aba já existente.
    _ensure_extra_cols("ExecutiveSummaries", ["Report_Ids_Usados"])
    summary_id = _gerar_id("RES")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok = append_row("ExecutiveSummaries", [
        summary_id, cliente_id, ativo_id, gerado_por_usuario_id,
        tipo_resumo, modo, periodo_inicio, periodo_fim,
        titulo, resumo_texto, dados_usados, "",
        "Gerado", now, now, report_ids_usados,
    ])
    return summary_id if ok else None


def get_executive_summaries(cliente_id: str, ativo_id: str = "", limit: int = 50) -> pd.DataFrame:
    """Histórico de resumos executivos do cliente, mais recentes primeiro.
    SEGURANÇA: cliente_id sempre da sessão/seleção staff."""
    if not cliente_id:
        return pd.DataFrame(columns=_HEADERS_EXEC_SUMMARY)
    df = load_sheet("ExecutiveSummaries")
    if df.empty:
        return df
    for col in _HEADERS_EXEC_SUMMARY:
        if col not in df.columns:
            df[col] = ""
    df = df[df["Cliente_Id"].astype(str).str.strip().str.lower() == cliente_id.strip().lower()]
    if ativo_id:
        df = df[df["Ativo_Id"].astype(str).str.strip() == ativo_id.strip()]
    df = df.copy()
    df["_dt"] = pd.to_datetime(df.get("Created_At", pd.Series(dtype=str)), dayfirst=True, errors="coerce")
    return df.sort_values("_dt", ascending=False).drop(columns=["_dt"]).head(limit).reset_index(drop=True)


def get_executive_summary_by_id(summary_id: str, cliente_id: str = "") -> dict | None:
    """Retorna dict do resumo pelo Id. Se cliente_id for informado, valida
    ownership — nunca retorna resumo de outro cliente."""
    df = load_sheet("ExecutiveSummaries")
    if df.empty or "Id" not in df.columns:
        return None
    match = df[df["Id"].astype(str).str.strip() == summary_id.strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    if cliente_id and str(row.get("Cliente_Id", "")).strip().lower() != cliente_id.strip().lower():
        return None
    return {col: str(row.get(col, "")).strip() for col in _HEADERS_EXEC_SUMMARY}


def update_executive_summary(summary_id: str, cliente_id: str, **campos) -> bool:
    """Atualiza campos de um resumo executivo (ex.: Status='Arquivado').
    Valida ownership pelo cliente_id antes de gravar."""
    try:
        ss = get_spreadsheet()
        ws = ss.worksheet("ExecutiveSummaries")
        headers = ws.row_values(1)
        if "Id" not in headers:
            return False
        id_col = headers.index("Id") + 1
        cell = ws.find(summary_id, in_column=id_col)
        if not cell:
            return False
        row_idx = cell.row
        if "Cliente_Id" in headers:
            cid_col_idx = headers.index("Cliente_Id") + 1
            existing_cid = ws.cell(row_idx, cid_col_idx).value or ""
            if existing_cid.strip().lower() != cliente_id.strip().lower():
                return False
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        campos = dict(campos)
        campos.setdefault("Updated_At", now)
        for campo, valor in campos.items():
            if campo in headers:
                ws.update_cell(row_idx, headers.index(campo) + 1, str(valor))
        _clear_read_caches()
        return True
    except Exception:
        return False
