# mi-research-tg-bot

Telegram-бот для исследований с поддержкой запуска через Docker Compose.

## Требования

- [Docker](https://docs.docker.com/get-docker/) (версия 20.10 или выше)
- [Docker Compose](https://docs.docker.com/compose/install/) (версия 2.0 или выше)
- Токен Telegram-бота (получить у [@BotFather](https://t.me/BotFather))

## Инструкция по настройке через Docker Compose

### Шаг 1: Клонирование репозитория

```bash
git clone https://github.com/jonx8/mi-research-tg-bot.git
cd mi-research-tg-bot
```

### Шаг 2: Настройка переменных окружения

Создайте файл `.env` на основе шаблона `.env.example`:

```bash
cp .env.example .env
```

Откройте файл `.env` и заполните необходимые параметры:

```bash
# Telegram Bot Token - обязательный параметр
BOT_TOKEN=ваш_токен_бота

# Database - путь к базе данных внутри контейнера
DB_NAME=database/participants.db

# Logging - уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Google Sheets Export - опционально, для экспорта данных в Google Таблицы
GOOGLE_SHEETS_CREDENTIALS_PATH=config/mi-research-tg-bot.json
GOOGLE_SHEETS_SPREADSHEET_ID=id_вашей_таблицы
GOOGLE_SHEETS_EXPORT_INTERVAL=3600
GOOGLE_SHEETS_EXPORT_TIMEOUT=300

# Scheduler intervals (in seconds) - интервалы планировщика задач
SURVEY_CHECK_INTERVAL=120
DAILY_LOG_CHECK_INTERVAL=120
INTERVENTION_CONTENT_INTERVAL=120
```

**Важно:** Минимально необходимый параметр — `BOT_TOKEN`. Остальные можно оставить по умолчанию. Если интеграция с Google Sheets не нужна, то следует удалить все, связанные с этим переменные.

### Шаг 3: Настройка Google Sheets (опционально)

Если вы планируете использовать экспорт данных в Google Таблицы:

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите Google Sheets API
3. Создайте сервисный аккаунт и скачайте JSON-файл с учётными данными
4. Сохраните файл как `config/mi-research-tg-bot.json`
5. Добавьте идентификатор вашей таблицы в `GOOGLE_SHEETS_SPREADSHEET_ID`
6. Предоставьте сервисному аккаунту доступ к таблице (поделитесь таблицей с email сервисного аккаунта)

### Шаг 4: Запуск бота

Запустите бота с помощью Docker Compose:

```bash
docker compose up -d
```

Флаг `-d` запускает контейнер в фоновом режиме.

### Шаг 5: Проверка статуса

Проверьте, что контейнер запущен:

```bash
docker compose ps
```

Просмотрите логи бота:

```bash
docker compose logs -f mi-research-tg-bot
```

### Шаг 6: Остановка бота

Для остановки бота выполните:

```bash
docker compose down
```

**Важно:** Эта команда не удалит базу данных, так как она хранится в именованном томе `mi-research-db`.
