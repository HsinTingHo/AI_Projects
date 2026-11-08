#initialize model
from uuid import UUID, uuid4

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")




def claim_next_job(db_con, worker_id: str) -> object:
    """Atomically claim one eligible job, record the attempt, and establish a lease.

    Returns None if no jobs are available. The caller must either mark the job
    succeeded or record a failure before the lease expires.
    """
    new_token = uuid4().hex
    jobs = db_con.execute(
        """
        WITH candidate AS (
            SELECT id
            FROM ingestion_jobs
            WHERE status = 'queued'
            OR (
                status = 'running'
                AND lease_expires_at <= CURRENT_TIMESTAMP
            )
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        UPDATE ingestion_jobs AS job
        SET status = 'running',
            claimed_by = :worker_id,
            claim_token = :new_token,
            lease_expires_at = CURRENT_TIMESTAMP + INTERVAL '60 seconds',
            attempt_count = attempt_count + 1
        FROM candidate
        WHERE job.id = candidate.id
        RETURNING id, report_id, claim_token
        """
    ).fetchone()
    return jobs

def renew_lease(db_con, job_id: UUID, claim_token: UUID) -> None:
    row = db_con.execute(
        """
        UPDATE ingestion_jobs
        SET lease_expires_at = clock_timestamp() + INTERVAL '60 seconds',
            heartbeat_at = clock_timestamp()
        WHERE id = %(job_id)s
          AND claim_token = %(claim_token)s
          AND status = 'running'
          AND lease_expires_at > clock_timestamp()
        RETURNING id
        """,
        {"job_id": job_id, "claim_token": claim_token},
    ).fetchone()

    if row is None:
        raise RuntimeError(f"Lease ownership lost for job {job_id}")

def mark_succeeded(db_con, job_id: int, claim_token: str):
    db_con.execute(
        """
        UPDATE ingestion_jobs
        SET status = 'succeeded',
            claim_token = NULL,
            claimed_by = NULL,
            lease_expires_at = NULL,
            heartbeat_at = clock_timestamp()
        WHERE id = %(job_id)s
          AND claim_token = %(claim_token)s
          AND status = 'running'
        RETURNING id
        """,
        {"job_id": job_id, "claim_token": claim_token},
    ).fetchone()

    if row is None:
        raise RuntimeError(f"mark_succeeded failed for job {job_id}")

    def record_failure(db_con, job_id: int, claim_token: str, error: Exception):
        db_con.execute(
            """
            UPDATE ingestion_jobs
            SET status = 'failed',
                claim_token = NULL,
                claimed_by = NULL,
                lease_expires_at = NULL,
                heartbeat_at = clock_timestamp(),
                last_error = %(error)s
            WHERE id = %(job_id)s
            AND claim_token = %(claim_token)s
            AND status = 'running'
            RETURNING id
            """,
            {"job_id": job_id, "claim_token": claim_token, "error": str(error)},
        ).fetchone()

        if row is None:
            raise RuntimeError(f"record_failure failed for job {job_id}")

