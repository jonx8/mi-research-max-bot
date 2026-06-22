import asyncio
import csv
from pathlib import Path

from src.config import Config
from src.database import Database
from src.models import MorningTip


async def seed_morning_tips(csv_path: str = "config/morning_tips.csv"):
    file_path = Path(csv_path) if Path(csv_path).is_absolute() else Path(__file__).parent.parent / csv_path

    if not file_path.exists():
        print(f"❌ Файл {file_path} не найден")
        return

    db = Database(Config().DATABASE_URL)

    merged_count = 0
    async with db.get_db_session() as session:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tips_id = int(row['id'])
                month = int(row['month'])
                tip_type = row['type']
                content = row['content']

                tip = MorningTip(id=tips_id, month=month, type=tip_type, content=content)
                await session.merge(tip)
                merged_count += 1
            await session.commit()
    print(f"✅ Успешно добавлено (merge) {merged_count} MorningTips записей.")


if __name__ == "__main__":
    import sys

    csv_file = sys.argv[1] if len(sys.argv) > 1 else "config/morning_tips.csv"
    asyncio.run(seed_morning_tips(csv_file))
