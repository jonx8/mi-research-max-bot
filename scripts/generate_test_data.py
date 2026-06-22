import os
import random
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "participants.db"


def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            participant_code TEXT PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            group_name TEXT NOT NULL,
            registration_date TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS baseline_questionnaires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_code TEXT UNIQUE NOT NULL,
            completed_at TEXT NOT NULL,
            smoking_years INTEGER NOT NULL,
            cigs_per_day INTEGER NOT NULL,
            quit_attempts_before INTEGER NOT NULL,
            uses_vape INTEGER NOT NULL,
            smoker_in_household INTEGER NOT NULL,
            prior_medical_help TEXT NOT NULL,
            fagerstrom_score INTEGER NOT NULL,
            fagerstrom_level TEXT NOT NULL,
            fagerstrom_1 INTEGER NOT NULL,
            fagerstrom_2 INTEGER NOT NULL,
            fagerstrom_3 INTEGER NOT NULL,
            fagerstrom_4 INTEGER NOT NULL,
            fagerstrom_5 INTEGER NOT NULL,
            fagerstrom_6 INTEGER NOT NULL,
            prochaska_score INTEGER NOT NULL,
            prochaska_level TEXT NOT NULL,
            prochaska_1 INTEGER NOT NULL,
            prochaska_2 INTEGER NOT NULL,
            FOREIGN KEY (participant_code) REFERENCES participants (participant_code)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS follow_ups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_code TEXT NOT NULL,
            scheduled_date TEXT NOT NULL,
            sent_at TEXT,
            completed_at TEXT,
            ppa_7d INTEGER,
            cigs_per_day INTEGER,
            FOREIGN KEY (participant_code) REFERENCES participants (participant_code)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_code TEXT NOT NULL,
            week_number INTEGER NOT NULL,
            scheduled_date TEXT NOT NULL,
            sent_at TEXT,
            completed_at TEXT,
            smoking_status TEXT,
            craving_level INTEGER,
            mood TEXT,
            FOREIGN KEY (participant_code) REFERENCES participants (participant_code)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_code TEXT NOT NULL,
            log_date TEXT NOT NULL,
            morning_sent_at TEXT,
            evening_sent_at TEXT,
            evening_response TEXT,
            evening_response_at TEXT,
            FOREIGN KEY (participant_code) REFERENCES participants (participant_code)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sos_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_code TEXT NOT NULL,
            triggered_at TEXT NOT NULL,
            technique_id TEXT,
            FOREIGN KEY (participant_code) REFERENCES participants (participant_code)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS craving_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_code TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            trigger_situation TEXT,
            thoughts TEXT,
            physical_sensation TEXT,
            coping_strategy TEXT,
            FOREIGN KEY (participant_code) REFERENCES participants (participant_code)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS final_surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_code TEXT UNIQUE NOT NULL,
            scheduled_date TEXT NOT NULL,
            sent_at TEXT,
            completed_at TEXT,
            ppa_30d INTEGER,
            ppa_7d INTEGER,
            cigs_per_day INTEGER,
            quit_attempt_made INTEGER,
            days_to_first_lapse INTEGER,
            FOREIGN KEY (participant_code) REFERENCES participants (participant_code)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS techniques (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            type TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Все таблицы созданы/проверены")


def generate_participant_code(index):
    return f"P{index:04d}"


def generate_participants(num_participants=100):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM participants")

    batch = []
    used_telegram_ids = set()

    print(f"🚀 Генерация {num_participants} участников...")

    for i in range(1, num_participants + 1):
        participant_code = generate_participant_code(i)

        while True:
            telegram_id = random.randint(100000000, 999999999)
            if telegram_id not in used_telegram_ids:
                used_telegram_ids.add(telegram_id)
                break

        group_name = 'A' if i % 2 == 0 else 'B'

        registration_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d %H:%M:%S')

        age = random.randint(25, 65)
        gender = 'male' if random.random() < 0.5 else 'female'

        batch.append((participant_code, telegram_id, group_name, registration_date, age, gender))

        if len(batch) >= 100:
            cursor.executemany("""
                INSERT INTO participants 
                (participant_code, telegram_id, group_name, registration_date, age, gender)
                VALUES (?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            batch = []

    if batch:
        cursor.executemany("""
            INSERT INTO participants 
            (participant_code, telegram_id, group_name, registration_date, age, gender)
            VALUES (?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()

    conn.close()
    print(f"🎉 Создано {num_participants} участников (50% группа А, 50% группа Б)")


def generate_baseline_questionnaires():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT participant_code FROM participants")
    participants = [row[0] for row in cursor.fetchall()]

    batch = []
    fagerstrom_levels = ['Низкая', 'Средняя', 'Высокая', 'Очень высокая']
    prochaska_levels = ['Преконтемпляция', 'Контемпляция', 'Подготовка', 'Действие', 'Поддержание']

    for participant_code in participants:
        registration = cursor.execute(
            "SELECT registration_date FROM participants WHERE participant_code = ?",
            (participant_code,)
        ).fetchone()[0]
        reg_date = datetime.strptime(registration, '%Y-%m-%d %H:%M:%S')
        completed_at = (reg_date + timedelta(days=random.randint(0, 3))).strftime('%Y-%m-%d %H:%M:%S')

        smoking_years = random.randint(1, 40)
        cigs_per_day = random.randint(5, 40)
        quit_attempts_before = random.choice([0, 1])
        uses_vape = random.choice([0, 1])
        smoker_in_household = random.choice([0, 1])
        prior_medical_help = random.choice(['Нет', 'Не помню', 'Да'])

        fagerstrom_1 = random.randint(0, 1)
        fagerstrom_2 = random.randint(0, 1)
        fagerstrom_3 = random.randint(0, 1)
        fagerstrom_4 = random.randint(0, 1)
        fagerstrom_5 = random.randint(0, 3)
        fagerstrom_6 = random.randint(0, 1)
        fagerstrom_score = fagerstrom_1 + fagerstrom_2 + fagerstrom_3 + fagerstrom_4 + fagerstrom_5 + fagerstrom_6
        fagerstrom_level = fagerstrom_levels[min(fagerstrom_score // 3, 3)]

        prochaska_1 = random.randint(1, 5)
        prochaska_2 = random.randint(1, 5)
        prochaska_score = prochaska_1 + prochaska_2
        prochaska_level = prochaska_levels[min(prochaska_score // 2, 4)]

        batch.append((
            participant_code, completed_at, smoking_years, cigs_per_day, quit_attempts_before,
            uses_vape, smoker_in_household, prior_medical_help, fagerstrom_score, fagerstrom_level,
            fagerstrom_1, fagerstrom_2, fagerstrom_3, fagerstrom_4, fagerstrom_5, fagerstrom_6,
            prochaska_score, prochaska_level, prochaska_1, prochaska_2
        ))

    cursor.executemany("""
        INSERT INTO baseline_questionnaires 
        (participant_code, completed_at, smoking_years, cigs_per_day, quit_attempts_before,
         uses_vape, smoker_in_household, prior_medical_help, fagerstrom_score, fagerstrom_level,
         fagerstrom_1, fagerstrom_2, fagerstrom_3, fagerstrom_4, fagerstrom_5, fagerstrom_6,
         prochaska_score, prochaska_level, prochaska_1, prochaska_2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)

    conn.commit()
    conn.close()
    print(f"✅ Создано {len(batch)} базовых опросников")


def generate_follow_ups():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT participant_code, registration_date FROM participants")
    participants = cursor.fetchall()

    batch = []
    responses = [0, 1]

    for participant_code, registration in participants:
        reg_date = datetime.strptime(registration, '%Y-%m-%d %H:%M:%S')

        for month in [1, 3]:
            scheduled_date = reg_date + timedelta(days=month * 30)

            sent_at = scheduled_date + timedelta(minutes=random.randint(-60, 60))
            sent_at = sent_at.strftime('%Y-%m-%d %H:%M:%S')

            completed_at = (scheduled_date + timedelta(days=random.randint(0, 3))).strftime('%Y-%m-%d %H:%M:%S')
            ppa_7d = random.choice(responses)

            if ppa_7d == 1:
                cigs_per_day = 0
            else:
                cigs_per_day = random.randint(5, 40)

            batch.append((
                participant_code,
                scheduled_date.strftime('%Y-%m-%d %H:%M:%S'),
                sent_at,
                completed_at,
                ppa_7d,
                cigs_per_day
            ))

    cursor.executemany("""
        INSERT INTO follow_ups 
        (participant_code, scheduled_date, sent_at, completed_at, ppa_7d, cigs_per_day)
        VALUES (?, ?, ?, ?, ?, ?)
    """, batch)

    conn.commit()
    conn.close()
    print(f"✅ Создано {len(batch)} follow-up записей (по 2 на участника)")


def generate_weekly_checkins():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT participant_code, registration_date FROM participants WHERE group_name = 'Б'")
    participants = cursor.fetchall()

    batch = []
    smoking_statuses = ['Курю', 'Не курю', 'Иногда курю']
    moods = ['Отличное', 'Хорошее', 'Нормальное', 'Плохое', 'Ужасное']

    for participant_code, registration in participants:
        reg_date = datetime.strptime(registration, '%Y-%m-%d %H:%M:%S')

        for week in range(1, 25):
            scheduled_date = reg_date + timedelta(days=week * 7)

            sent_at = scheduled_date + timedelta(minutes=random.randint(-120, 60))
            sent_at = sent_at.strftime('%Y-%m-%d %H:%M:%S')

            completed_at = (scheduled_date + timedelta(days=random.randint(0, 2))).strftime('%Y-%m-%d %H:%M:%S')
            smoking_status = random.choice(smoking_statuses)
            craving_level = random.randint(0, 10)
            mood = random.choice(moods)

            batch.append((
                participant_code, week, scheduled_date.strftime('%Y-%m-%d %H:%M:%S'),
                sent_at, completed_at, smoking_status, craving_level, mood
            ))

    cursor.executemany("""
        INSERT INTO weekly_checkins 
        (participant_code, week_number, scheduled_date, sent_at, completed_at, 
         smoking_status, craving_level, mood)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)

    conn.commit()
    conn.close()
    print(f"✅ Создано {len(batch)} weekly check-in записей (по 24 на участника группы Б)")


def generate_daily_logs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT participant_code, registration_date FROM participants WHERE group_name = 'Б'")
    participants = cursor.fetchall()

    batch = []

    for participant_code, registration in participants:
        reg_date = datetime.strptime(registration, '%Y-%m-%d %H:%M:%S').date()

        for day in range(180):
            current_date = reg_date + timedelta(days=day)

            morning_time = datetime.strptime("09:00", "%H:%M") + timedelta(minutes=random.randint(-30, 30))
            morning_sent = f"{current_date} {morning_time.strftime('%H:%M:%S')}"

            evening_time = datetime.strptime("20:00", "%H:%M") + timedelta(minutes=random.randint(-30, 30))
            evening_sent = f"{current_date} {evening_time.strftime('%H:%M:%S')}"

            responses = ['✅ Да', '❌ Трудности', '🆘 Тяга']
            weights = [0.5, 0.3, 0.2]
            evening_response = random.choices(responses, weights=weights)[0]

            response_offset = random.randint(1, 120)
            response_time = evening_time + timedelta(minutes=response_offset)
            evening_response_at = f"{current_date} {response_time.strftime('%H:%M:%S')}"

            batch.append((
                participant_code, current_date.isoformat(),
                morning_sent, evening_sent, evening_response, evening_response_at
            ))

    cursor.executemany("""
        INSERT INTO daily_logs 
        (participant_code, log_date, morning_sent_at, evening_sent_at, 
         evening_response, evening_response_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, batch)

    conn.commit()
    conn.close()
    print(f"✅ Создано {len(batch)} daily log записей (по 180 на участника группы Б)")


def generate_sos_usage():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT participant_code, registration_date FROM participants WHERE group_name = 'Б'")
    participants = cursor.fetchall()

    cursor.execute("SELECT id FROM techniques")
    techniques = [row[0] for row in cursor.fetchall()]

    batch = []

    for participant_code, registration in participants:
        reg_date = datetime.strptime(registration, '%Y-%m-%d %H:%M:%S')

        for sos_num in range(360):
            days_after = random.randint(0, 180)
            minutes_in_day = random.randint(0, 1440)
            triggered_at = reg_date + timedelta(days=days_after, minutes=minutes_in_day)

            technique_id = random.choice(techniques)

            batch.append((
                participant_code,
                triggered_at.strftime('%Y-%m-%d %H:%M:%S'),
                technique_id
            ))

    cursor.executemany("""
        INSERT INTO sos_usage 
        (participant_code, triggered_at, technique_id)
        VALUES (?, ?, ?)
    """, batch)

    conn.commit()
    conn.close()
    print(f"✅ Создано {len(batch)} SOS использований (по 360 на участника группы Б)")


def generate_craving_analyses():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT participant_code, registration_date FROM participants WHERE group_name = 'Б'")
    participants = cursor.fetchall()

    batch = []
    trigger_situations = [
        "Стресс на работе", "Ссора с близкими", "Употребление алкоголя",
        "После еды", "Утром с кофе", "В компании курящих"
    ]
    thoughts = [
        "Одна сигарета не повредит", "Я не справлюсь", "Мне это нужно",
        "Я уже проиграл", "Сейчас не время бросать"
    ]
    physical_sensations = [
        "Напряжение в груди", "Головная боль", "Дрожь в руках",
        "Сухость во рту", "Ощущение голода"
    ]
    coping_strategies = [
        "Глубокое дыхание", "Физическая активность", "Позвонил другу",
        "Выпил воду", "Отвлекся на работу"
    ]

    for participant_code, registration in participants:
        reg_date = datetime.strptime(registration, '%Y-%m-%d %H:%M:%S')

        for analysis_num in range(180):
            days_after = random.randint(0, 180)
            minutes_in_day = random.randint(0, 1440)
            completed_at = reg_date + timedelta(days=days_after, minutes=minutes_in_day)

            batch.append((
                participant_code,
                completed_at.strftime('%Y-%m-%d %H:%M:%S'),
                random.choice(trigger_situations),
                random.choice(thoughts),
                random.choice(physical_sensations),
                random.choice(coping_strategies)
            ))

    cursor.executemany("""
        INSERT INTO craving_analyses 
        (participant_code, completed_at, trigger_situation, thoughts, 
         physical_sensation, coping_strategy)
        VALUES (?, ?, ?, ?, ?, ?)
    """, batch)

    conn.commit()
    conn.close()
    print(f"✅ Создано {len(batch)} craving analysis записей (по 180 на участника группы Б)")


def generate_final_surveys():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT participant_code, registration_date FROM participants")
    participants = cursor.fetchall()

    batch = []

    for participant_code, registration in participants:
        reg_date = datetime.strptime(registration, '%Y-%m-%d %H:%M:%S')
        scheduled_date = reg_date + timedelta(days=180)

        sent_at = scheduled_date + timedelta(minutes=random.randint(-60, 60))
        sent_at = sent_at.strftime('%Y-%m-%d %H:%M:%S')

        completed_at = (scheduled_date + timedelta(days=random.randint(0, 7))).strftime('%Y-%m-%d %H:%M:%S')
        ppa_30d = random.choice([0, 1])
        ppa_7d = random.choice([0, 1])

        if ppa_7d == 1:
            cigs_per_day = 0
        else:
            cigs_per_day = random.randint(5, 40)

        quit_attempt_made = random.choice([0, 1])

        if quit_attempt_made == 1:
            days_to_first_lapse = random.randint(1, 30)
        else:
            days_to_first_lapse = None

        batch.append((
            participant_code, scheduled_date.strftime('%Y-%m-%d %H:%M:%S'),
            sent_at, completed_at, ppa_30d, ppa_7d, cigs_per_day,
            quit_attempt_made, days_to_first_lapse
        ))

    cursor.executemany("""
        INSERT INTO final_surveys 
        (participant_code, scheduled_date, sent_at, completed_at, ppa_30d, ppa_7d,
         cigs_per_day, quit_attempt_made, days_to_first_lapse)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)

    conn.commit()
    conn.close()
    print(f"✅ Создано {len(batch)} финальных опросников (по 1 на участника)")


def generate_techniques():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    techniques_data = [
        ('T001', 'Дыхательная гимнастика', 'Глубокое дыхание на 5 секунд', 'дыхание',
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('T002', 'Прогулка', 'Выйдите на 10-минутную прогулку', 'активность',
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('T003', 'Стакан воды', 'Медленно выпейте стакан воды', 'отвлечение',
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('T004', 'Отвлечение', 'Займитесь делом на 5 минут', 'отвлечение',
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('T005', 'Позитивный диалог', 'Скажите себе "Я справлюсь"', 'самоподдержка',
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('T006', 'Физическая активность', '10 приседаний или отжиманий', 'активность',
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO techniques (id, name, description, type, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, techniques_data)

    conn.commit()
    conn.close()
    print(f"✅ Создано {len(techniques_data)} техник")


def show_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n" + "=" * 50)
    print("📊 СТАТИСТИКА БАЗЫ ДАННЫХ")
    print("=" * 50)

    tables = [
        ('participants', 'Участники'),
        ('baseline_questionnaires', 'Базовые опросники'),
        ('follow_ups', 'Follow-up опросы'),
        ('weekly_checkins', 'Weekly check-ins'),
        ('daily_logs', 'Daily logs'),
        ('sos_usage', 'SOS использования'),
        ('craving_analyses', 'Craving анализы'),
        ('final_surveys', 'Финальные опросы'),
        ('techniques', 'Техники')
    ]

    for table, name in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  • {name}: {count:,}")

    db_size = os.path.getsize(DB_PATH)
    print(f"\n💾 Размер БД: {db_size / (1024 * 1024):.2f} MB")

    conn.close()


def generate_full_dataset():
    print("\n" + "=" * 50)
    print("ГЕНЕРАТОР ПОЛНОЙ БАЗЫ ДАННЫХ")
    print("=" * 50)

    participants = int(input("\nКоличество участников (четное для 50/50): "))

    if participants % 2 != 0:
        participants += 1
        print(f"ℹ️ Скорректировано до {participants} (четное число)")

    print("\n🚀 Генерация данных...\n")

    create_tables()
    generate_techniques()
    generate_participants(participants)
    generate_baseline_questionnaires()
    generate_follow_ups()
    generate_final_surveys()
    generate_weekly_checkins()
    generate_daily_logs()
    generate_sos_usage()
    generate_craving_analyses()

    show_stats()


if __name__ == "__main__":
    generate_full_dataset()