"""
Storage de PDFs para Pred.IO — Google Cloud Storage (GCS).

MOTIVO: Service accounts não têm cota de armazenamento no Google Drive.
GCS usa as mesmas credenciais e não tem essa restrição.

CONFIGURAÇÃO (opcional):
  GCS_BUCKET_NAME=predio-biblioteca   ← padrão usado se não definido

Se o bucket não existir, é criado automaticamente na primeira execução
(requer que a service account tenha o papel "Storage Admin" no projeto GCP).
"""
from __future__ import annotations

import io
import os
from datetime import timedelta

_MAX_SIZE_BYTES  = 50 * 1024 * 1024   # 50 MB
_SIGNED_URL_DAYS = 3650               # ~10 anos


# ── Credenciais ───────────────────────────────────────────────────────────────

def _build_creds():
    """Credenciais com escopo cloud-platform — mesma fonte que sheets.py."""
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/cloud-platform"]

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

    import base64 as _b64, json as _json
    for key in ("GCP_CREDENTIALS_B64", "GCP_CREDENTIALS"):
        raw = os.environ.get(key)
        if raw:
            try:
                info = _json.loads(_b64.b64decode(raw))
            except Exception:
                info = _json.loads(raw)
            return Credentials.from_service_account_info(info, scopes=scopes)

    for path in ("/etc/secrets/credentials.json", "credentials.json"):
        if os.path.exists(path):
            return Credentials.from_service_account_file(path, scopes=scopes)

    raise RuntimeError("Credenciais GCP não encontradas.")


# ── Bucket ────────────────────────────────────────────────────────────────────

def _get_bucket_name() -> str:
    bucket = ""
    try:
        import streamlit as st
        bucket = (st.secrets.get("GCS_BUCKET_NAME") or "").strip()
    except Exception:
        pass
    if not bucket:
        bucket = os.environ.get("GCS_BUCKET_NAME", "").strip()
    return bucket or "predio-biblioteca"


def _get_client():
    from google.cloud import storage
    creds = _build_creds()
    project = None
    try:
        # Extrai project_id do e-mail da service account: nome@project.iam...
        project = creds.service_account_email.split("@")[1].split(".iam")[0]
    except Exception:
        pass
    return storage.Client(credentials=creds, project=project)


def _get_or_create_bucket(client, bucket_name: str):
    try:
        return client.get_bucket(bucket_name)
    except Exception:
        try:
            return client.create_bucket(bucket_name)
        except Exception as exc:
            raise RuntimeError(
                f"Bucket GCS '{bucket_name}' não encontrado e não foi possível criar.\n"
                f"Acesse console.cloud.google.com → Cloud Storage → Criar bucket,\n"
                f"dê ao bucket o nome '{bucket_name}' e conceda à service account\n"
                f"o papel 'Storage Object Admin'.\n"
                f"Depois defina GCS_BUCKET_NAME={bucket_name} no Render → Environment.\n"
                f"Detalhe: {exc}"
            ) from exc


# ── Upload público ─────────────────────────────────────────────────────────────

def upload_pdf(
    file_bytes: bytes,
    arquivo_nome: str,
    cliente_id: str,
) -> str:
    """
    Faz upload do PDF para Google Cloud Storage.

    Retorna URL assinada válida por ~10 anos.
    Lança ValueError para arquivo inválido, RuntimeError para falha de storage.
    """
    # ── Validações ────────────────────────────────────────────────────────────
    if not file_bytes:
        raise ValueError("Arquivo vazio.")
    if len(file_bytes) > _MAX_SIZE_BYTES:
        mb = len(file_bytes) // (1024 * 1024)
        raise ValueError(
            f"Arquivo muito grande ({mb} MB). Envie um PDF de até 50 MB."
        )
    if file_bytes[:5] != b"%PDF-":
        raise ValueError("Arquivo não é um PDF válido. Envie um arquivo .pdf.")

    # ── Nome do objeto: {cliente_id}/{nome}.pdf ───────────────────────────────
    base = os.path.splitext(arquivo_nome)[0] if arquivo_nome else "documento"
    safe = "".join(c for c in base if c.isalnum() or c in "-_ ").strip() or "documento"
    blob_name = f"{(cliente_id or 'sem-cliente').lower()}/{safe}.pdf"

    # ── Client GCS ────────────────────────────────────────────────────────────
    try:
        client = _get_client()
    except ImportError:
        raise RuntimeError(
            "Dependência google-cloud-storage não instalada. "
            "Aguarde o próximo deploy e tente novamente."
        )

    bucket = _get_or_create_bucket(client, _get_bucket_name())

    # ── Upload ────────────────────────────────────────────────────────────────
    try:
        blob = bucket.blob(blob_name)
        blob.upload_from_file(io.BytesIO(file_bytes), content_type="application/pdf")
    except Exception as exc:
        raise RuntimeError(f"Falha ao enviar arquivo para o GCS: {exc}") from exc

    # ── URL assinada ~10 anos ─────────────────────────────────────────────────
    try:
        url = blob.generate_signed_url(
            expiration=timedelta(days=_SIGNED_URL_DAYS),
            method="GET",
            version="v2",
        )
    except Exception as exc:
        raise RuntimeError(f"Arquivo enviado, mas falha ao gerar URL: {exc}") from exc

    return url
