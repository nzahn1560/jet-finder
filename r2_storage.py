"""
Cloudflare R2 (S3-compatible) storage for listing photos and videos.

Architecture decision:
- Railway hosts the Flask app + PostgreSQL only.
- Cloudflare R2 stores all listing photos and videos (object storage).
- PostgreSQL stores only the metadata (see db.ListingMedia).

Env vars (set in Railway):
  R2_ACCOUNT_ID          (e.g. 5ab9... — used as default endpoint)
  R2_ACCESS_KEY_ID
  R2_SECRET_ACCESS_KEY
  R2_BUCKET_NAME         (e.g. jetschool-media)
  R2_ENDPOINT            (optional; default: https://<account>.r2.cloudflarestorage.com)
  R2_PUBLIC_BASE_URL     (e.g. https://media.jetschoolusa.com — the URL we serve to browsers)

Local development:
  If R2 env vars are missing we fall back to a local on-disk store under
  static/uploads/dev/ so the upload flow works end-to-end without R2 credentials.
  This is gated by `is_production()` from db.py — production refuses to fall back.
"""
from __future__ import annotations

import io
import logging
import os
import uuid
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

# Allow-listed content types and reasonable per-file size limits.
PHOTO_CONTENT_TYPES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
}
VIDEO_CONTENT_TYPES = {
    'video/mp4', 'video/webm', 'video/quicktime', 'video/mpeg',
}
PHOTO_MAX_BYTES = 12 * 1024 * 1024     # 12 MB per photo
VIDEO_MAX_BYTES = 250 * 1024 * 1024    # 250 MB per video
MAX_PHOTOS_PER_LISTING = 40
MAX_VIDEOS_PER_LISTING = 5

# Immutable cache-control for uploaded media (object keys are unique UUIDs).
IMMUTABLE_CACHE_CONTROL = 'public, max-age=31536000, immutable'

EXT_BY_CONTENT_TYPE = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
    'image/gif': '.gif',
    'video/mp4': '.mp4',
    'video/webm': '.webm',
    'video/quicktime': '.mov',
    'video/mpeg': '.mpg',
}


def classify_content_type(content_type: str | None) -> str | None:
    """Return 'photo' / 'video' / None for a given content type."""
    if not content_type:
        return None
    ct = content_type.lower()
    if ct in PHOTO_CONTENT_TYPES:
        return 'photo'
    if ct in VIDEO_CONTENT_TYPES:
        return 'video'
    return None


def is_configured() -> bool:
    """True if all required R2 env vars are present."""
    return all(os.environ.get(k) for k in (
        'R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_BUCKET_NAME'
    ))


def _env(key: str, default: str | None = None) -> str | None:
    v = os.environ.get(key)
    return v if v is not None else default


def _r2_endpoint() -> str:
    explicit = _env('R2_ENDPOINT')
    if explicit:
        return explicit.rstrip('/')
    account = _env('R2_ACCOUNT_ID') or ''
    return f'https://{account}.r2.cloudflarestorage.com'


def _public_base_url() -> str:
    """Public URL prefix that browsers use to fetch media (custom domain preferred)."""
    base = _env('R2_PUBLIC_BASE_URL') or _env('R2_CUSTOM_DOMAIN')
    if base:
        return base.rstrip('/')
    # Last resort: direct r2.dev URL (works but slower + counts against worker limits)
    bucket = _env('R2_BUCKET_NAME') or ''
    account = _env('R2_ACCOUNT_ID') or ''
    return f'https://pub-{account}.r2.dev/{bucket}'.rstrip('/')


def public_url_for_key(object_key: str) -> str:
    return f'{_public_base_url()}/{object_key.lstrip("/")}'


def build_object_key(listing_id: int, content_type: str | None, kind: str) -> str:
    """Generate a globally unique R2 object key.

    Format: listings/{listing_id}/{kind}/{uuid}{ext}
    Unique per upload → no cache invalidation ever needed (we set immutable Cache-Control).
    """
    ext = EXT_BY_CONTENT_TYPE.get((content_type or '').lower(), '')
    safe_kind = 'videos' if kind == 'video' else 'photos'
    return f'listings/{int(listing_id)}/{safe_kind}/{uuid.uuid4().hex}{ext}'


# -----------------------------------------------------------------------------
# Local dev fallback (only when R2 is not configured AND not running in prod).
# -----------------------------------------------------------------------------
def _local_dev_root() -> Path:
    return Path(__file__).resolve().parent / 'static' / 'uploads' / 'dev'


def _is_production() -> bool:
    """Mirror db.is_production() without importing (avoid circular import)."""
    if (os.environ.get('FLASK_ENV') or '').lower() == 'production':
        return True
    if (os.environ.get('RAILWAY_ENVIRONMENT') or '').lower() == 'production':
        return True
    if (os.environ.get('DATABASE_URL') or '').startswith('postgres'):
        return True
    return False


def _save_local_dev(object_key: str, fileobj, content_type: str | None) -> str:
    """Save the file locally under static/uploads/dev so dev works without R2."""
    root = _local_dev_root()
    target = root / object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(fileobj, 'seek'):
        try:
            fileobj.seek(0)
        except Exception:
            pass
    with open(target, 'wb') as out:
        while True:
            chunk = fileobj.read(64 * 1024)
            if not chunk:
                break
            out.write(chunk)
    # Served by Flask's existing /static path
    return f'/static/uploads/dev/{object_key}'


# -----------------------------------------------------------------------------
# R2 client (boto3 S3-compatible)
# -----------------------------------------------------------------------------
_client_cache: Any = None


def _get_client():
    """Lazy-build the boto3 S3 client; cached for the process lifetime."""
    global _client_cache
    if _client_cache is not None:
        return _client_cache
    try:
        import boto3  # type: ignore
        from botocore.config import Config  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "boto3 is required for R2 uploads. Add 'boto3' to requirements.txt and redeploy."
        ) from e
    _client_cache = boto3.client(
        's3',
        endpoint_url=_r2_endpoint(),
        aws_access_key_id=_env('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=_env('R2_SECRET_ACCESS_KEY'),
        region_name='auto',
        config=Config(s3={'addressing_style': 'path'}, signature_version='s3v4'),
    )
    return _client_cache


def upload_fileobj(fileobj, object_key: str, content_type: str | None) -> str:
    """Upload a file-like object to R2 (or local dev fallback). Returns the public URL.

    Production with R2 configured  → uploads to R2 with immutable Cache-Control.
    Production without R2          → raises (no silent file-disk fallback in prod).
    Dev with R2 configured         → uploads to R2.
    Dev without R2                 → saves to static/uploads/dev and returns /static URL.
    """
    if is_configured():
        bucket = _env('R2_BUCKET_NAME') or ''
        try:
            client = _get_client()
        except Exception:
            _log.exception('r2_storage: failed to build boto3 client')
            if _is_production():
                raise
            return _save_local_dev(object_key, fileobj, content_type)
        extra = {
            'CacheControl': IMMUTABLE_CACHE_CONTROL,
        }
        if content_type:
            extra['ContentType'] = content_type
        if hasattr(fileobj, 'seek'):
            try:
                fileobj.seek(0)
            except Exception:
                pass
        try:
            client.upload_fileobj(fileobj, bucket, object_key, ExtraArgs=extra)
        except Exception:
            _log.exception('r2_storage: upload failed for %s', object_key)
            if _is_production():
                raise
            return _save_local_dev(object_key, fileobj, content_type)
        return public_url_for_key(object_key)

    # Not configured
    if _is_production():
        raise RuntimeError(
            'R2 is not configured in production. Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, '
            'R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME (and R2_PUBLIC_BASE_URL) and redeploy.'
        )
    return _save_local_dev(object_key, fileobj, content_type)


def delete_object(object_key: str) -> bool:
    """Best-effort delete of an R2 object (or local dev file). Returns True on success."""
    if is_configured():
        try:
            client = _get_client()
            client.delete_object(Bucket=_env('R2_BUCKET_NAME'), Key=object_key)
            return True
        except Exception:
            _log.exception('r2_storage: delete failed for %s', object_key)
            return False
    # Local dev fallback
    try:
        p = _local_dev_root() / object_key
        if p.is_file():
            p.unlink()
        return True
    except Exception:
        _log.exception('r2_storage: local dev delete failed for %s', object_key)
        return False


def storage_status() -> dict:
    """Diagnostic info for /api/data-safety and ops."""
    return {
        'r2_configured': is_configured(),
        'r2_endpoint': _r2_endpoint() if is_configured() else None,
        'r2_public_base_url': _public_base_url() if is_configured() else None,
        'r2_bucket': _env('R2_BUCKET_NAME') if is_configured() else None,
        'local_dev_fallback_active': (not is_configured()) and (not _is_production()),
        'production': _is_production(),
    }
