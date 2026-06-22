FROM python:3.10-slim

WORKDIR /app

ENV TZ=Europe/Moscow

RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV	PYTHONDONTWRITEBYTECODE=1

CMD sh -c "alembic upgrade head && python -m src.main"