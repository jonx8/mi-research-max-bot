import logging
from datetime import datetime
from typing import Dict, List, Any

import gspread
from google.oauth2.service_account import Credentials

from src.database import Database
from src.models import (
    Participant, BaselineQuestionnaire, FollowUp,
    WeeklyCheckIn, DailyLog, SOSUsage, CravingAnalysis, FinalSurvey
)

logger = logging.getLogger(__name__)


class GoogleSheetsExporter:
    """Сервис для экспорта данных в Google Sheets."""

    def __init__(self, credentials_path: str, spreadsheet_id: str, database: Database):
        self._credentials_path = credentials_path
        self._spreadsheet_id = spreadsheet_id
        self._database = database
        self._client = None
        self._spreadsheet = None
        self._batch_size = 5000

    def _connect(self) -> None:
        """Подключение к Google Sheets API."""
        if self._client is None:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                self._credentials_path, scopes=scopes
            )
            self._client = gspread.authorize(creds)
            self._spreadsheet = self._client.open_by_key(self._spreadsheet_id)
            logger.info("Подключение к Google Sheets установлено")

    def _get_or_create_worksheet(self, name: str) -> gspread.Worksheet:
        """Получить или создать лист."""
        try:
            return self._spreadsheet.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            return self._spreadsheet.add_worksheet(title=name, rows=1000, cols=20)

    @staticmethod
    def _format_datetime(dt: Any) -> str:
        """Форматирование datetime."""
        if dt is None:
            return ''
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return str(dt)

    @staticmethod
    def _format_date(dt: Any) -> str:
        """Форматирование даты."""
        if dt is None:
            return ''
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d')
        return str(dt)

    @staticmethod
    def _format_bool(value: Any) -> str:
        """Форматирование булевых значений."""
        if value is None:
            return ''
        if isinstance(value, bool):
            return 'TRUE' if value else 'FALSE'
        return str(value)

    @staticmethod
    def _batch_update_worksheet(worksheet: gspread.Worksheet, headers: List[str], data: List[List[Any]]) -> None:
        """Batch update листа таблицы."""

        if not data:
            worksheet.clear()
            worksheet.update(values=[headers], range_name='A1', value_input_option='USER_ENTERED')
            return

        try:
            worksheet.clear()

            all_rows = [headers] + data

            needed_rows = len(all_rows)
            current_rows = worksheet.row_count
            if needed_rows > current_rows:
                worksheet.add_rows(needed_rows - current_rows)

            cell_list = []
            for i, row in enumerate(all_rows, start=1):
                for j, value in enumerate(row, start=1):
                    if value:
                        cell_list.append(
                            gspread.Cell(i, j, value)
                        )

            if cell_list:
                worksheet.update_cells(cell_list, value_input_option='USER_ENTERED')

            logger.info(f"Записано {len(data)} строк в лист '{worksheet.title}'")

        except Exception as e:
            logger.error(f"Ошибка при обновлении листа {worksheet.title}: {e}")
            raise

    async def _fetch_all_data(self) -> Dict[str, List[Any]]:
        """Загрузка всех данных из БД."""
        async with self._database.get_db_session() as session:
            from sqlalchemy import select

            # Загружаем все данные параллельно
            tables = {
                'participants': select(Participant),
                'baseline': select(BaselineQuestionnaire),
                'follow_ups': select(FollowUp),
                'weekly_checkins': select(WeeklyCheckIn),
                'daily_logs': select(DailyLog),
                'sos_usage': select(SOSUsage),
                'craving_analyses': select(CravingAnalysis),
                'final_surveys': select(FinalSurvey),
            }

            results = {}
            for name, query in tables.items():
                result = await session.execute(query)
                results[name] = result.scalars().all()

            return results

    def export_all_optimized_sync(self) -> Dict[str, int]:
        """Синхронная обертка для вызова из отдельного потока"""
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.export_all_optimized())
        finally:
            loop.close()

    async def export_all_optimized(self) -> Dict[str, int]:
        """Оптимизированный полный экспорт всех данных."""
        self._connect()

        logger.info("Загрузка данных из базы данных...")
        all_data = await self._fetch_all_data()

        export_configs = [
            {
                'name': 'Участники',
                'data': all_data['participants'],
                'headers': ["participant_code", "group_name",
                            "registration_date", "age", "gender", "clinic_center"],
                'row_mapper': lambda p: [
                    p.participant_code, p.group_name,
                    self._format_datetime(p.registration_date), str(p.age), p.gender, p.clinic_center
                ]
            },
            {
                'name': 'Baseline_опросы',
                'data': all_data['baseline'],
                'headers': ["id", "participant_code", "completed_at", "smoking_years",
                            "cigs_per_day", "quit_attempts_before", "uses_vape",
                            "smoker_in_household", "prior_medical_help", "fagerstrom_score",
                            "fagerstrom_level", "prochaska_score", "prochaska_level"],
                'row_mapper': lambda q: [
                    q.id, q.participant_code, self._format_datetime(q.completed_at),
                    str(q.smoking_years), str(q.cigs_per_day), self._format_bool(q.quit_attempts_before),
                    self._format_bool(q.uses_vape), self._format_bool(q.smoker_in_household),
                    self._format_bool(q.prior_medical_help),
                    str(q.fagerstrom_score), q.fagerstrom_level, str(q.prochaska_score), q.prochaska_level
                ]
            },
            {
                'name': 'Промежуточные_опросы',
                'data': all_data['follow_ups'],
                'headers': ["id", "participant_code", "scheduled_date", "sent_at",
                            "completed_at", "ppa_7d", "cigs_per_day"],
                'row_mapper': lambda fu: [
                    fu.id, fu.participant_code, self._format_datetime(fu.scheduled_date),
                    self._format_datetime(fu.sent_at), self._format_datetime(fu.completed_at),
                    self._format_bool(fu.ppa_7d), fu.cigs_per_day
                ]
            },
            {
                'name': 'Еженедельные_чекины',
                'data': all_data['weekly_checkins'],
                'headers': ["id", "participant_code", "week_number", "scheduled_date",
                            "sent_at", "completed_at", "smoking_status", "craving_level", "mood"],
                'row_mapper': lambda ci: [
                    ci.id, ci.participant_code, ci.week_number,
                    self._format_datetime(ci.scheduled_date), self._format_datetime(ci.sent_at),
                    self._format_datetime(ci.completed_at), ci.smoking_status,
                    ci.craving_level, ci.mood
                ]
            },
            {
                'name': 'Ежедневные_логи',
                'data': all_data['daily_logs'],
                'headers': ["id", "participant_code", "log_date", "morning_sent_at",
                            "evening_sent_at", "evening_response", "evening_response_at"],
                'row_mapper': lambda log: [
                    log.id, log.participant_code, self._format_date(log.log_date),
                    self._format_datetime(log.morning_sent_at),
                    self._format_datetime(log.evening_sent_at), log.evening_response,
                    self._format_datetime(log.evening_response_at)
                ]
            },
            {
                'name': 'SOS_использование',
                'data': all_data['sos_usage'],
                'headers': ["id", "participant_code", "triggered_at", "technique_id"],
                'row_mapper': lambda sos: [
                    sos.id, sos.participant_code, self._format_datetime(sos.triggered_at),
                    sos.technique_id
                ]
            },
            {
                'name': 'Анализы_тяги',
                'data': all_data['craving_analyses'],
                'headers': ["id", "participant_code", "completed_at", "trigger_situation",
                            "thoughts", "physical_sensation", "coping_strategy"],
                'row_mapper': lambda a: [
                    a.id, a.participant_code, self._format_datetime(a.completed_at),
                    a.trigger_situation or '', a.thoughts or '',
                    a.physical_sensation or '', a.coping_strategy or ''
                ]
            },
            {
                'name': 'Финальные_опросы',
                'data': all_data['final_surveys'],
                'headers': ["id", "participant_code", "scheduled_date", "sent_at",
                            "completed_at", "ppa_30d", "ppa_7d", "cigs_per_day",
                            "quit_attempt_made", "days_to_first_lapse"],
                'row_mapper': lambda s: [
                    s.id, s.participant_code, self._format_datetime(s.scheduled_date),
                    self._format_datetime(s.sent_at), self._format_datetime(s.completed_at),
                    self._format_bool(s.ppa_30d), self._format_bool(s.ppa_7d), s.cigs_per_day,
                    self._format_bool(s.quit_attempt_made), s.days_to_first_lapse
                ]
            }
        ]

        results = {}
        for config in export_configs:
            worksheet = self._get_or_create_worksheet(config['name'])
            data_rows = [config['row_mapper'](item) for item in config['data']]
            self._batch_update_worksheet(worksheet, config['headers'], data_rows)
            results[config['name']] = len(data_rows)
            logger.info(f"Экспортировано {len(data_rows)} записей в {config['name']}")

        total = sum(results.values())
        logger.info(f"Полный экспорт завершен. Всего: {total} записей")

        return results
