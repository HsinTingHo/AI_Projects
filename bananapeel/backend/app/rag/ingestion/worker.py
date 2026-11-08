 # Load model, claim jobs, retry, handle shutdown
from asyncio import Event
from email.mime import text
from io import BytesIO
import logging
import os
import socket
import time
from threading import Thread
from uuid import uuid4

from app.config import settings
from app.database.connection import connect
from app.storage.dependencies import create_storage
from app.rag.ingestion.repository import EmbeddingRepository as embed_repository

 # Extract text, generate embeddings, save results


from ingestion import (
    load_model,
    jobs,
    extraction,
    chunking,
    embeddings, 
)

logger = logging.getLogger(__name__)

def heartbeat_loop(stop, lost, job_id, claim_token):
    try:
        with connect() as conn:  # Dedicated heartbeat connection.
            while not stop.wait(20):
                with conn.transaction():
                    jobs.renew_lease(conn, job_id, claim_token)
    except Exception:
        logger.exception("Heartbeat failed for job %s", job_id)
        lost.set()


def main():
    model = load_model()
    tokenizer = model.tokenizer
   
    storage = create_storage(settings)
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex}"
    with connect() as db_con:
        while True:
            with db_con.transaction():
                job = jobs.claim_next_job(db_con, worker_id)

            if job is None:
                time.sleep(1)
                continue

            #start heartbeat after claiming a job
            stop = Event()
            lost = Event()
            heartbeat = Thread(
                target=heartbeat_loop,
                args=(stop, lost, job["id"], job["claim_token"]),
            )
            heartbeat.start()

            try:
                with BytesIO() as pdf:
                    storage.download_to(job.report_id, pdf)
                    pdf.seek(0)
                    pages = extraction.extract_pages(pdf)
                    if not pages:
                        raise ValueError("No pages extracted from PDF")
                    chunks = chunking.chunk_pages( 
                        pages,
                        count_tokens=lambda text: chunking.count_tokens(text, tokenizer),
                        max_tokens=240
                    )
                    if not chunks:
                        raise ValueError("No chunks generated from pages")
                    vectors = embeddings.embed_documents(model, chunks)

                    # Safe to repeat if this job is retried.
                    if vectors and len(vectors[0]) == 384:
                        embed_repository.save_embeddings(job.document_id, vectors)
                        jobs.mark_succeeded(job.id, job.claim_token)
                    else:
                        jobs.record_failure(job.id, job.claim_token, "No chunks or embeddings generated")
            except FileNotFoundError as error:
                pass
            
        
            except extraction.ExtractionError as error:
                pass
            except ValueError as error:
                pass
            except Exception as error:
                logger.exception("Ingestion failed for job %s", job.id)
                jobs.record_failure(job.id, job.claim_token, error)

if __name__ == "__main__":
    main()