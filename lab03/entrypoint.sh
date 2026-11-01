#!/bin/sh
# shebang - говорит ОС, что этот файл нужно выполнить через sh

# Создаем файл для логов cron и даем всем права на чтение и запись
create_log_file() {
    echo "Creating log file..."
    touch /var/log/cron.log
    chmod 666 /var/log/cron.log
    echo "Log file created at /var/log/cron.log"
}

# Выводим новые строки лога в консоль контейнера (их видно через docker compose logs)
monitor_logs() {
    echo "=== Monitoring cron logs ==="
    tail -f /var/log/cron.log
}

# Запускаем cron: -f - работать без отделения от контейнера,
# exec - cron заменяет этот скрипт и становится главным процессом контейнера
run_cron() {
    echo "=== Starting cron daemon ==="
    exec cron -f
}

# Сохраняем переменные окружения контейнера (API_URL, API_KEY и др.) в /etc/environment,
# т.к. cron запускает задачи без них и берет переменные из этого файла
env > /etc/environment
create_log_file
# & - запускаем просмотр логов в фоне, чтобы скрипт не остановился на tail -f
monitor_logs &
run_cron
