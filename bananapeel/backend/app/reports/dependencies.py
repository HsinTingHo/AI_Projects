from typing import Annotated

from fastapi import Depends
from psycopg import AsyncConnection

from app.database.connection import get_db_conn
from app.reports.repository import ReportRepository


def get_report_repository(
    conn: Annotated[AsyncConnection, Depends(get_db_conn)],
) -> ReportRepository:
    return ReportRepository(conn)


ReportRepositoryDep = Annotated[
    ReportRepository,
    Depends(get_report_repository),
]