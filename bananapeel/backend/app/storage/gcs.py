"""Google Cloud Storage adapter using Application Default Credentials."""

from typing import BinaryIO

from app.storage.base import validate_key


class GCSStorage:
    def __init__(self, bucket: str, project: str | None = None):
        if not bucket or "/" in bucket or bucket != bucket.strip():
            raise ValueError("Configure a GCS bucket name, not a gs:// URL")
        self.bucket_name = bucket
        self.project = project

    def _blob(self, key: str):
        validate_key(key)
        try:
            from google.cloud import storage
        except ImportError as error:
            raise RuntimeError("Install the backend's gcs extra: pip install -e '.[gcs]'") from error
        # Lazy creation keeps local startup independent of Google credentials.
        client = storage.Client(project=self.project)
        return client, client.bucket(self.bucket_name).blob(key)

    def save(self, key: str, source: BinaryIO) -> None:
        client, blob = self._blob(key)
        from google.api_core.exceptions import PreconditionFailed
        try:
            blob.upload_from_file(source, content_type="application/pdf", if_generation_match=0, timeout=60)
        except PreconditionFailed as error:
            raise FileExistsError(key) from error
        finally:
            client.close()

    def download_to(self, key: str, destination: BinaryIO) -> None:
        client, blob = self._blob(key)
        from google.api_core.exceptions import NotFound
        try:
            blob.download_to_file(destination, timeout=60)
        except NotFound as error:
            raise FileNotFoundError(key) from error
        finally:
            client.close()

    def delete(self, key: str) -> None:
        client, blob = self._blob(key)
        from google.api_core.exceptions import NotFound
        try:
            blob.reload(timeout=60)
            blob.delete(if_generation_match=blob.generation, timeout=60)
        except NotFound:
            pass
        finally:
            client.close()
