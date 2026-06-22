import random
from typing import Optional, List, Dict, Tuple, Set

from sqlalchemy import select

from src.database import Database
from src.models import InterventionContent, InterventionContentLog


class InterventionContentRepository:
    def __init__(self, db: Database):
        self._db = db

    async def get_educational_content(self, week: int) -> Optional[str]:
        """Получить образовательное сообщение для указанной недели."""
        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(InterventionContent.content)
                .where(InterventionContent.week == week)
                .where(InterventionContent.content_type == 'educational')
            )
            contents = [row[0] for row in result.all()]
            if not contents:
                return None
            return random.choice(contents)

    async def get_motivational_content(self, week: int) -> Optional[str]:
        """Получить мотивационную историю для указанной недели (только четные недели)."""
        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(InterventionContent.content)
                .where(InterventionContent.week == week)
                .where(InterventionContent.content_type == 'motivational')
            )
            contents = [row[0] for row in result.all()]
            if not contents:
                return None
            return random.choice(contents)

    async def get_educational_content_map(self, participant_weeks: Dict[str, int]) -> Dict[str, str]:
        """
        Получить образовательный контент для всех участников одним запросом.

        Args:
            participant_weeks: dict {participant_code: week_number}

        Returns:
            dict {participant_code: content}
        """
        if not participant_weeks:
            return {}

        weeks = list(set(participant_weeks.values()))

        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(InterventionContent.week, InterventionContent.content)
                .where(InterventionContent.week.in_(weeks))
                .where(InterventionContent.content_type == 'educational')
            )

            content_by_week: Dict[int, List[str]] = {}
            for row in result.all():
                week_num, content = row
                if week_num not in content_by_week:
                    content_by_week[week_num] = []
                content_by_week[week_num].append(content)

            result_map = {}
            for participant_code, week_num in participant_weeks.items():
                if week_num in content_by_week and content_by_week[week_num]:
                    result_map[participant_code] = random.choice(content_by_week[week_num])

            return result_map

    async def get_motivational_content_map(self, participant_weeks: Dict[str, int]) -> Dict[str, str]:
        """
        Получить мотивационный контент для всех участников одним запросом.

        Args:
            participant_weeks: dict {participant_code: week_number}

        Returns:
            dict {participant_code: content}
        """
        if not participant_weeks:
            return {}

        weeks = list(set(participant_weeks.values()))

        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(InterventionContent.week, InterventionContent.content)
                .where(InterventionContent.week.in_(weeks))
                .where(InterventionContent.content_type == 'motivational')
            )

            content_by_week: Dict[int, List[str]] = {}
            for row in result.all():
                week_num, content = row
                if week_num not in content_by_week:
                    content_by_week[week_num] = []
                content_by_week[week_num].append(content)

            result_map = {}
            for participant_code, week_num in participant_weeks.items():
                if week_num in content_by_week and content_by_week[week_num]:
                    result_map[participant_code] = random.choice(content_by_week[week_num])

            return result_map

    async def get_educational_content_with_ids(self, participant_weeks: Dict[str, int]) -> Dict[str, Tuple[int, str]]:
        """
        Получить образовательный контент с ID для всех участников одним запросом.

        Args:
            participant_weeks: dict {participant_code: week_number}

        Returns:
            dict {participant_code: (content_id, content)}
        """
        if not participant_weeks:
            return {}

        weeks = list(set(participant_weeks.values()))

        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(InterventionContent.id, InterventionContent.week, InterventionContent.content)
                .where(InterventionContent.week.in_(weeks))
                .where(InterventionContent.content_type == 'educational')
            )

            content_by_week: Dict[int, List[Tuple[int, str]]] = {}
            for row in result.all():
                content_id, week_num, content = row
                if week_num not in content_by_week:
                    content_by_week[week_num] = []
                content_by_week[week_num].append((content_id, content))

            result_map = {}
            for participant_code, week_num in participant_weeks.items():
                if week_num in content_by_week and content_by_week[week_num]:
                    result_map[participant_code] = random.choice(content_by_week[week_num])

            return result_map

    async def get_motivational_content_with_ids(self, participant_weeks: Dict[str, int]) -> Dict[str, Tuple[int, str]]:
        """
        Получить мотивационный контент с ID для всех участников одним запросом.

        Args:
            participant_weeks: dict {participant_code: week_number}

        Returns:
            dict {participant_code: (content_id, content)}
        """
        if not participant_weeks:
            return {}

        weeks = list(set(participant_weeks.values()))

        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(InterventionContent.id, InterventionContent.week, InterventionContent.content)
                .where(InterventionContent.week.in_(weeks))
                .where(InterventionContent.content_type == 'motivational')
            )

            content_by_week: Dict[int, List[Tuple[int, str]]] = {}
            for row in result.all():
                content_id, week_num, content = row
                if week_num not in content_by_week:
                    content_by_week[week_num] = []
                content_by_week[week_num].append((content_id, content))

            result_map = {}
            for participant_code, week_num in participant_weeks.items():
                if week_num in content_by_week and content_by_week[week_num]:
                    result_map[participant_code] = random.choice(content_by_week[week_num])

            return result_map

    async def add_or_update_content(self, content_data: dict):
        """Добавить или обновить контент через merge."""
        async with self._db.get_db_session() as session:
            content = InterventionContent(**content_data)
            await session.merge(content)
            await session.commit()

    async def get_already_sent_content_ids(self, participant_code: str, content_ids: List[int]) -> Set[int]:
        """
        Получить ID контента, который уже был отправлен участнику.

        Args:
            participant_code: код участника
            content_ids: список ID контента для проверки

        Returns:
            set из ID уже отправленного контента
        """
        if not content_ids:
            return set()

        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(InterventionContentLog.content_id)
                .where(InterventionContentLog.participant_code == participant_code)
                .where(InterventionContentLog.content_id.in_(content_ids))
            )
            return {row[0] for row in result.all()}

    async def log_content_sent(self, participant_code: str, content_id: int):
        """Записать факт отправки контента."""
        async with self._db.get_db_session() as session:
            log_entry = InterventionContentLog(
                participant_code=participant_code,
                content_id=content_id
            )
            session.add(log_entry)
            await session.commit()