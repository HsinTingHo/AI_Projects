"""One configured storage adapter per FastAPI application."""

from typing import Annotated
from fastapi import Depends, Request

from app.core.config import BACKEND_ROOT, Settings
from app.storage.base import ReportStorage
from app.storage.gcs import GCSStorage
from app.storage.local import LocalStorage


def create_storage(settings: Settings) -> ReportStorage:
    if settings.storage_backend == "gcs":
        if not settings.gcs_bucket:
            raise ValueError("BANANAPEEL_GCS_BUCKET is required for gcs storage")
        return GCSStorage(settings.gcs_bucket, settings.gcs_project)
    root = settings.storage_root
    return LocalStorage(root if root.is_absolute() else BACKEND_ROOT / root)


def get_storage(request: Request) -> ReportStorage:
    return request.app.state.report_storage


StorageDep = Annotated[ReportStorage, Depends(get_storage)]
