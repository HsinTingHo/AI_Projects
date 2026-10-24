"""Report persistence; every save attempt owns a complete transaction."""
from typing import Any

import psycopg
from psycopg.rows import dict_row


class ReportRepository:
    def __init__(self, conn: psycopg.AsyncConnection):
        self.conn = conn

    async def save_report_metadata(self, report_info: dict, file_path: str) -> dict[str, Any]:
        # The dependency supplies an autocommit connection, so this is a top-level
        # transaction. Exit commits before returning, or rolls back before retry.
        async with self.conn.transaction():
            async with self.conn.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(
                    """INSERT INTO reports
                    (id, company, filename, file_size_bytes, report_type, sha256,
                     status, report_year, storage_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, filename, storage_key, status, created_at""",
                    (report_info["id"], report_info.get("company"), report_info["filename"],
                     report_info.get("file_size_bytes"), report_info.get("report_type"),
                     report_info.get("sha256"), report_info.get("status", "queued"),
                     report_info.get("report_year"), file_path),
                )
                result = await cursor.fetchone()
                if result is None:
                    raise RuntimeError("Report insert returned no row")
        return result
