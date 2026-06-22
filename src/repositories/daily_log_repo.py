from datetime import date
from typing import Optional, List

from sqlalchemy import select, and_

from src.database import Database
from src.models import DailyLog


class DailyLogRepository:
    def __init__(self, db: Database):
        self._db = db

    async def save(self, log: DailyLog) -> DailyLog:
        async with self._db.get_db_session() as session:
            session.add(log)
            await session.flush()
            return log

    async def get_by_id(self, log_id: int) -> Optional[DailyLog]:
        async with self._db.get_db_session() as session:
            return await session.get(DailyLog, log_id)

    async def get_by_date(self, participant_code: str, log_date: date) -> Optional[DailyLog]:
        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(DailyLog)
                .where(DailyLog.participant_code == participant_code)
                .where(DailyLog.log_date == log_date)
            )
            return result.scalar_one_or_none()

    async def get_or_create_batch(
            self,
            participant_codes: List[str],
            log_date: date
    ) -> List[DailyLog]:
        """
        Получает существующие DailyLog для переданных кодов и даты,
        для отсутствующих создаёт новые записи. Возвращает все записи (существующие и новые).
        Пакетная обработка
        """
        async with self._db.get_db_session() as session:
            stmt = select(DailyLog).where(
                and_(
                    DailyLog.participant_code.in_(participant_codes),
                    DailyLog.log_date == log_date
                )
            )
            result = await session.execute(stmt)
            existing_logs = result.scalars().all()
            existing_codes = {log.participant_code for log in existing_logs}

            new_logs = []
            for code in participant_codes:
                if code not in existing_codes:
                    new_log = DailyLog(
                        participant_code=code,
                        log_date=log_date
                    )
                    session.add(new_log)
                    new_logs.append(new_log)

            if new_logs:
                await session.flush()

            return existing_logs + new_logs

    async def update(self, log: DailyLog) -> DailyLog:
        async with self._db.get_db_session() as session:
            await session.merge(log)
            return log
