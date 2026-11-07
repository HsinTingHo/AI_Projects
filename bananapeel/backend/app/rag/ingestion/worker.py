 # Load model, claim jobs, retry, handle shutdown
import logging
import os
import socket
import time
from uuid import uuid4
from app.database.connection import connect


 # Extract text, generate embeddings, save results


from ingestion import (
    load_model,
    extract_text, #extraction
    save_embeddings, #embeddings
    claim_next_job, 
    mark_succeeded,
    record_failure,
)

logger = logging.getLogger(__name__)

def main():
    model = load_model()
    db_con = connect()
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex}"
    while True:
        # Atomically claims one eligible job, records the attempt,
        # and establishes a lease. Returns None if none are available.
        job = claim_next_job(db_con, worker_id)

        if job is None:
            time.sleep(1)
            continue

        try:
            text = extract_text(job.file_key)
            vectors = model.encode(text)

            # Safe to repeat if this job is retried.
            save_embeddings(job.document_id, vectors)
            mark_succeeded(job.id, job.claim_token)
        except Exception as error:
            logger.exception("Ingestion failed for job %s", job.id)
            record_failure(job.id, job.claim_token, error)

if __name__ == "__main__":
    main()