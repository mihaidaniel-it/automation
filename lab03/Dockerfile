# Базовый образ - официальный образ Python (в нем уже есть Python и pip)
FROM python:3.13-slim

# Устанавливаем cron и удаляем кэш apt, чтобы образ занимал меньше места
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Устанавливаем библиотеку requests, которую использует скрипт
RUN pip install --no-cache-dir requests

# Отключаем буферизацию вывода Python, чтобы строки попадали в лог сразу и по порядку
ENV PYTHONUNBUFFERED=1

# Рабочая директория в контейнере
WORKDIR /app

# Копируем скрипт, файл с задачами cron и entrypoint-скрипт в контейнер
COPY currency_exchange_rate.py cronjob entrypoint.sh /app/

# Даем entrypoint-скрипту право на запуск и регистрируем задачи из cronjob в crontab
RUN chmod +x /app/entrypoint.sh && crontab /app/cronjob

# При старте контейнера запускается entrypoint-скрипт: он создает лог и запускает cron
ENTRYPOINT ["/app/entrypoint.sh"]
