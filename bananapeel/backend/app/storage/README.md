# Report storage

Select the adapter explicitly, independently of an environment name:

```dotenv
BANANAPEEL_STORAGE_BACKEND=local
BANANAPEEL_STORAGE_ROOT=data
```

Relative roots resolve against the backend directory, not the shell directory.
The key `reports/<uuid>/annual.pdf` resolves to `backend/data/reports/<uuid>/annual.pdf`.

For Google Cloud Storage, install `.venv/bin/python -m pip install -e '.[gcs]'`
and configure:

```dotenv
BANANAPEEL_STORAGE_BACKEND=gcs
BANANAPEEL_GCS_BUCKET=your-private-reports-bucket
BANANAPEEL_GCS_PROJECT=your-project
```

Provision the bucket separately. The adapter neither creates it nor makes files
public. Use Application Default Credentials: an attached service account in
Google Cloud, or your approved local Google credentials when testing remotely.
No credential file belongs in this repository. Changing the adapter does not
migrate existing files; keep the same keys when transferring files to the bucket.

## Inject into a route and pass to a service

```python
from fastapi import File, UploadFile
from app.storage.dependencies import StorageDep

# Add `storage: StorageDep` to your existing route signature:
async def upload_report(storage: StorageDep, file: UploadFile = File(...)):
    # Keep your validation/finally-close logic.
    return await service.upload_report(file, storage)
```

Inside your existing async service:

```python
from starlette.concurrency import run_in_threadpool
from app.storage.base import ReportStorage

async def upload_report(file: UploadFile, storage: ReportStorage):
    # Generate the UUID and sanitized key in this service.
    report_key = ...
    await file.seek(0)
    await run_in_threadpool(storage.save, report_key, file.file)
    # Next: insert/commit the metadata using the same UUID and storage key.
    # If the DB transaction fails, delete this successfully saved key.
```

This is an integration example, not the completed upload implementation. Storage
methods are synchronous; call them from a sync route or offload them in async
code. The adapters do not close caller-owned streams. Do not close a stream until
its storage operation has finished. No MIME validation, size limits, metadata
inference, or database transactions belong in these adapters.

`save` refuses to overwrite an existing key, `download_to` copies into a stream,
and `delete` tolerates a missing key. Always generate fresh UUID-based keys; do
not reuse them. If an upload fails ambiguously over the network, reconcile its
key before retrying. Do not unconditionally delete a key after a failed save,
because a conflict may mean the object already existed.

Tests use temporary local files. GCS requires separately provisioned credentials
and a bucket for end-to-end verification; no live cloud upload has been performed.
