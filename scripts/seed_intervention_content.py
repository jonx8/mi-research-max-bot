import asyncio
import csv
from pathlib import Path

from src.config import Config
from src.database import Database
from src.models import InterventionContent


async def seed_intervention_content():
    """Загружает контент из CSV файла в БД, используя merge по id."""

    csv_file_path = Path(__file__).parent.parent / "config" / "intervention_content.csv"

    if not csv_file_path.exists():
        print(f"❌ Файл {csv_file_path} не найден")
        return

    db = Database(Config().DATABASE_URL)

    async with db.get_db_session() as session:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        merged_count = 0
        for row in rows:
            data = {
                "id": int(row["id"]),
                "month": int(row["month"]),
                "week": int(row["week"]),
                "content_type": row["type"],
                "content": row["content"]
            }

            content_obj = InterventionContent(**data)

            await session.merge(content_obj)
            merged_count += 1

        await session.commit()
        print(f"✅ Успешно добавлено (merge) {merged_count} InterventionContent записей.")


if __name__ == "__main__":
    asyncio.run(seed_intervention_content())
