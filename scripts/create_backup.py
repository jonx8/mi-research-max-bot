import logging
import os
import sqlite3
import argparse
from datetime import datetime


def create_backup(db_path, backup_dir):
    try:
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"База данных не найдена: {db_path}")

        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_name)

        source_conn = sqlite3.connect(db_path)
        backup_conn = sqlite3.connect(backup_path)

        source_conn.backup(backup_conn)

        backup_conn.close()
        source_conn.close()

        logging.info(f"Бэкап успешно создан: {backup_path}")

        size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        logging.info(f"Размер бэкапа: {size_mb:.2f} MB")

        return backup_path

    except Exception as e:
        logging.error(f"Ошибка при создании бэкапа: {e}")
        raise


def cleanup_old_backups(backup_dir, keep_backups):
    try:
        backups = []
        for file in os.listdir(backup_dir):
            if file.startswith("backup_") and file.endswith(".db"):
                file_path = os.path.join(backup_dir, file)
                backups.append((file_path, os.path.getmtime(file_path)))

        backups.sort(key=lambda x: x[1], reverse=True)

        for path, _ in backups[keep_backups:]:
            os.remove(path)
            logging.info(f"Удален старый бэкап: {path}")

    except Exception as e:
        logging.error(f"Ошибка при очистке бэкапов: {e}")


def verify_backup(backup_path):
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()

        if result == "ok":
            logging.info(f"Проверка целостности бэкапа пройдена: {backup_path}")
            return True
        else:
            logging.error(f"Ошибка целостности бэкапа: {backup_path} - {result}")
            return False

    except Exception as e:
        logging.error(f"Ошибка при проверке бэкапа: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Создание бэкапа SQLite базы данных")
    parser.add_argument("--db", required=True, help="Путь к файлу базы данных")
    parser.add_argument("--backup-dir", required=True, help="Директория для хранения бэкапов")
    parser.add_argument("--keep", type=int, default=10, help="Количество хранимых бэкапов (по умолчанию: 10)")

    args = parser.parse_args()

    try:
        backup_path = create_backup(args.db, args.backup_dir)
        if verify_backup(backup_path):
            cleanup_old_backups(args.backup_dir, args.keep)
            print(f"✅ Бэкап успешно создан: {backup_path}")
        else:
            print("❌ Бэкап создан, но проверка целостности не пройдена!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")