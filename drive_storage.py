"""Upload de PDF para Google Drive usando a conta de serviço existente — Pred.IO.

SEGURANÇA:
  - Credenciais do serviço nunca expostas ao front-end.
  - Arquivos organizados por cliente_id em pastas isoladas.
  - Chaves lidas do mesmo conjunto de fontes que sheets.py.

CONFIGURAÇÃO OBRIGATÓRIA:
  Service accounts não possuem cota de armazenamento própria no Google Drive.
  É necessário:
    1. Criar uma pasta no Google Drive de uma conta real (ex: conta Google do portal).
    2. Compartilhar essa pasta com o e-mail da service account como "Editor".
    3. Copiar o ID da pasta (último segmento da URL no Drive).
    4. Definir a variável de ambiente DRIVE_ROOT_FOLDER_ID=<id_da_pasta> no Render.com.
"""
from __future__ import annotations
import io
import os

_MAX_SIZE_BYTES   = 50 * 1024 * 1024   # 50 MB
_FOLDER_CACHE: dict[str, str] = {}


def _build_creds():
    """Credenciais com escopo Drive — mesma ordem de fontes que sheets.py."""
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/drive"]

    # 1. st.secrets
    try:
        import streamlit as st
        for key in ("GCP_CREDENTIALS_B64", "GCP_CREDENTIALS"):
            raw = st.secrets.get(key)
            if raw:
                import base64, json
                try:
                    info = json.loads(base64.b64decode(raw))
                except Exception:
                    info = json.loads(raw) if isinstance(raw, str) else raw
                return Credentials.from_service_account_info(info, scopes=scopes)
    except Exception:
        pass

    # 2. Variáveis de ambiente
    import base64 as _b64, json as _json
    for key in ("GCP_CREDENTIALS_B64", "GCP_CREDENTIALS"):
        raw = os.environ.get(key)
        if raw:
            try:
                info = _json.loads(_b64.b64decode(raw))
            except Exception:
                info = _json.loads(raw)
            return Credentials.from_service_account_info(info, scopes=scopes)

    # 3. Arquivo em disco
    for path in ("/etc/secrets/credentials.json", "credentials.json"):
        if os.path.exists(path):
            return Credentials.from_service_account_file(path, scopes=scopes)

    raise RuntimeError("Credenciais GCP não encontradas para Google Drive.")


def _build_service():
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=_build_creds(), cache_discovery=False)


def _get_root_folder_id() -> str:
    """Lê DRIVE_ROOT_FOLDER_ID de st.secrets ou variável de ambiente."""
    folder_id = ""
    try:
        import streamlit as st
        folder_id = (st.secrets.get("DRIVE_ROOT_FOLDER_ID") or "").strip()
    except Exception:
        pass
    if not folder_id:
        folder_id = os.environ.get("DRIVE_ROOT_FOLDER_ID", "").strip()
    if not folder_id:
        raise RuntimeError(
            "DRIVE_ROOT_FOLDER_ID não configurado.\n"
            "Passos:\n"
            "  1. Crie uma pasta no Google Drive da sua conta pessoal.\n"
            "  2. Compartilhe-a com o e-mail da service account como Editor.\n"
            "  3. Copie o ID da pasta (último trecho da URL do Drive).\n"
            "  4. Defina DRIVE_ROOT_FOLDER_ID=<id> no painel Render → Environment."
        )
    return folder_id


def _get_or_create_folder(service, name: str, parent_id: str | None = None) -> str:
    cache_key = f"{parent_id}|{name}"
    if cache_key in _FOLDER_CACHE:
        return _FOLDER_CACHE[cache_key]

    safe = name.replace("'", "\\'")
    q = (
        f"name='{safe}' and mimeType='application/vnd.google-apps.folder'"
        f" and trashed=false"
        + (f" and '{parent_id}' in parents" if parent_id else "")
    )
    res   = service.files().list(q=q, fields="files(id)", pageSize=1).execute()
    files = res.get("files", [])
    if files:
        folder_id = files[0]["id"]
    else:
        meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            meta["parents"] = [parent_id]
        folder_id = service.files().create(body=meta, fields="id").execute()["id"]

    _FOLDER_CACHE[cache_key] = folder_id
    return folder_id


def upload_pdf(
    file_bytes: bytes,
    arquivo_nome: str,
    cliente_id: str,
) -> str:
    """
    Faz upload do PDF para Google Drive.

    Retorna a URL de download direto (https://drive.google.com/uc?export=download&id=...).
    Lança ValueError para arquivo inválido ou RuntimeError para falha de storage.

    SEGURANÇA: arquivo salvo em pasta isolada por cliente_id; credenciais nunca
    chegam ao front-end.
    """
    # ── Validações ────────────────────────────────────────────────────────────
    if not file_bytes:
        raise ValueError("Arquivo vazio.")
    if len(file_bytes) > _MAX_SIZE_BYTES:
        mb = len(file_bytes) // (1024 * 1024)
        raise ValueError(
            f"Arquivo muito grande ({mb} MB). Envie um PDF de até 50 MB "
            "ou compacte o documento."
        )
    if file_bytes[:5] != b"%PDF-":
        raise ValueError("Arquivo não é um PDF válido. Envie um arquivo PDF.")

    # ── Nome seguro ───────────────────────────────────────────────────────────
    base = os.path.splitext(arquivo_nome)[0] if arquivo_nome else "documento"
    safe_name = "".join(c for c in base if c.isalnum() or c in "-_ ").strip() or "documento"
    nome_drive = f"{safe_name}.pdf"

    # ── Drive service ─────────────────────────────────────────────────────────
    try:
        service = _build_service()
    except ImportError:
        raise RuntimeError(
            "Dependência google-api-python-client não instalada. "
            "Aguarde o próximo deploy e tente novamente."
        )

    # ── Pasta raiz: lida de DRIVE_ROOT_FOLDER_ID ─────────────────────────────
    root_id = _get_root_folder_id()

    # ── Subpasta por cliente ──────────────────────────────────────────────────
    try:
        client_dir = (cliente_id or "sem-cliente").lower().replace("/", "-")
        folder_id  = _get_or_create_folder(service, client_dir, root_id)
    except Exception as exc:
        raise RuntimeError(f"Erro ao criar subpasta do cliente no Drive: {exc}") from exc

    # ── Upload ────────────────────────────────────────────────────────────────
    try:
        from googleapiclient.http import MediaIoBaseUpload
        buf   = io.BytesIO(file_bytes)
        media = MediaIoBaseUpload(buf, mimetype="application/pdf", resumable=False)
        meta  = {"name": nome_drive, "parents": [folder_id]}
        file_id = service.files().create(
            body=meta, media_body=media, fields="id"
        ).execute()["id"]
    except Exception as exc:
        raise RuntimeError(f"Falha ao enviar arquivo para o Drive: {exc}") from exc

    # ── Permissão: qualquer pessoa com o link pode visualizar ─────────────────
    try:
        service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
        ).execute()
    except Exception:
        pass  # falha silenciosa — arquivo existe, mas acesso externo pode não funcionar

    return f"https://drive.google.com/uc?export=download&id={file_id}"
