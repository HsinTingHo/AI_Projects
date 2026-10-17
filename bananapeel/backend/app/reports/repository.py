import psycopg
from pathlib import Path
from typing import Any

# report status -> uploaded, processing, ready, failed, archived
# save report -> return status and log
# save report metadata
# update report metadata
# delete report
# delete report metadata
# get report metadata
# get report

class ReportRepository:
    def __init__(self, conn: psycopg.AsyncConnection):
        self.conn = conn

           
    async def save_report_metadata(self, report_info: dict, file_path: str) -> dict[str, Any] | None:
        company = report_info.get("company", "")
        filename = report_info.get("filename", "")
        file_size = report_info.get("file_size", 0)
        report_type = report_info.get("report_type", "")
        sha256_hash = report_info.get("sha256_hash", "")
        status = report_info.get("status", "pending")
        year = report_info.get("year", "")


        query = """
            INSERT INTO reports (company, filename, file_size, report_type, sha256_hash, status, year, file_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, filename, file_path, created_at
        """
        async with self.conn.cursor() as cursor:
            await cursor.execute(query, (company, filename, file_size, report_type, sha256_hash, status, year, file_path))
            result = await cursor.fetchone()
            return result

    