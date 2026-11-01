# Лабораторная работа №3

**Выполнил:** Михай Даниел, I2402
**Курс:** Automation and Scripting

---

## Задание

Настроить планировщик задач `cron` для автоматического запуска скрипта `currency_exchange_rate.py` из лабораторной работы №2. Файлы лабораторной работы №2 скопированы в директорию `lab03`.

1. Создать файл `cronjob` с задачами для скрипта:
   - каждый день в 6:00 — получить курс `MDL` к `EUR` за предыдущий день;
   - каждую пятницу в 17:00 — получить курс `MDL` к `USD` за предыдущую неделю;
2. Создать `Dockerfile` на основе официального образа Python, который:
   - устанавливает cron, Python и нужные библиотеки;
   - копирует в контейнер скрипт, файл `cronjob` и entrypoint-скрипт;
   - настраивает cron на выполнение задач из `cronjob`;
   - запускает cron при старте контейнера;
   - записывает вывод задач в `/var/log/cron.log`;
3. Создать `docker-compose.yml`, который собирает образ из `Dockerfile` и запускает контейнер.

---

## Структура проекта

```text
lab03/
├── currency_exchange_rate.py   # скрипт из лабораторной работы №2 (без изменений)
├── cronjob                     # задачи cron
├── entrypoint.sh               # настраивает и запускает cron при старте контейнера
├── Dockerfile                  # сборка образа: Python + cron + requests
├── docker-compose.yml          # сборка образа и запуск контейнера
├── .gitignore                  # из лабораторной работы №2
└── readme.md                   # описание работы
```

### `currency_exchange_rate.py`

Скрипт из лабораторной работы №2, скопирован без изменений. Получает у сервиса `lab02prep` курс одной валюты к другой на указанную дату и сохраняет его в `data/<FROM>_<TO>_<DATE>.json`. Ошибки выводит в консоль и записывает в `error.log`. В контейнере это `/app/data/` и `/app/error.log`. Адрес сервиса и API-ключ берёт из переменных окружения `API_URL` и `API_KEY`.

### `cronjob`

Задачи cron. Формат строки: `минута час день_месяца месяц день_недели команда`.

```text
0 6 * * * /usr/local/bin/python3 /app/currency_exchange_rate.py MDL EUR $(date -d "yesterday" +\%Y-\%m-\%d) >> /var/log/cron.log 2>&1
0 17 * * 5 /usr/local/bin/python3 /app/currency_exchange_rate.py MDL USD $(date -d "last week" +\%Y-\%m-\%d) >> /var/log/cron.log 2>&1
```

- `0 6 * * *` — каждый день в 6:00; `0 17 * * 5` — каждую пятницу (5-й день недели) в 17:00;
- `date -d "yesterday"` — вчерашняя дата, `date -d "last week"` — дата неделю назад (формат `YYYY-MM-DD`);
- `\%` — в cron символ `%` означает перевод строки, поэтому он экранирован;
- `>> /var/log/cron.log 2>&1` — вывод и ошибки скрипта дописываются в лог;
- `python3` указан полным путём, т.к. cron ищет команды только в `/usr/bin` и `/bin`.

### `Dockerfile`

- `FROM python:3.13-slim` — официальный образ Python, в нём уже есть Python и pip;
- устанавливает `cron` через `apt-get` и библиотеку `requests` через `pip`;
- `PYTHONUNBUFFERED=1` — вывод скрипта сразу попадает в лог, строки идут по порядку;
- копирует скрипт, `cronjob` и `entrypoint.sh` в `/app`;
- `crontab /app/cronjob` — регистрирует задачи из `cronjob` в cron (для пользователя root);
- `ENTRYPOINT` — при старте контейнера запускается `entrypoint.sh`.

### `entrypoint.sh`

Скрипт запуска контейнера (на основе примера из задания):

1. `env > /etc/environment` — сохраняет переменные окружения контейнера (`API_URL`, `API_KEY` и др.), т.к. cron запускает задачи без них и берёт переменные из этого файла;
2. создаёт файл `/var/log/cron.log`;
3. в фоне (`&`) выводит новые строки лога через `tail -f`, поэтому вывод задач виден в `docker compose logs`;
4. запускает `cron -f`. Благодаря `exec` cron становится главным процессом контейнера, и контейнер работает, пока работает cron.

### `docker-compose.yml`

- `build: .` — собирает образ из `Dockerfile` в папке `lab03`;
- `environment` — передаёт скрипту `API_URL` и `API_KEY`. Внутри контейнера `localhost` — это сам контейнер, поэтому сервис `lab02prep`, запущенный на компьютере, доступен по адресу `host.docker.internal:8080`;
- `extra_hosts` — чтобы `host.docker.internal` работал и на Linux (в Docker Desktop он есть по умолчанию).

---

## Сборка и запуск

Нужны Docker и Docker Compose. Для получения курсов должен быть запущен сервис `lab02prep` (см. лабораторную работу №2) на порту `8080`.

```bash
cd lab03
docker compose up --build -d
```

- `--build` — собрать образ из `Dockerfile`;
- `-d` — запустить контейнер в фоновом режиме.

Проверить, что контейнер запущен:

```bash
docker compose ps
```

```text
NAME           IMAGE        COMMAND                SERVICE   CREATED          STATUS          PORTS
lab03-cron-1   lab03-cron   "/app/entrypoint.sh"   cron      10 seconds ago   Up 10 seconds
```

Остановить и удалить контейнер:

```bash
docker compose down
```

---

## Проверка работы cron

### 1. Задачи загружены в cron

```bash
docker compose exec cron crontab -l
```

Команда выводит содержимое файла `cronjob` — значит, обе задачи зарегистрированы.

### 2. cron запущен

```bash
docker compose top
```

```text
CMD
cron -f
/bin/sh /app/entrypoint.sh
tail -f /var/log/cron.log
```

### 3. Вывод задач пишется в `/var/log/cron.log`

```bash
docker compose exec cron cat /var/log/cron.log
```

Или смотреть вывод в реальном времени (выход — `Ctrl+C`):

```bash
docker compose logs -f
```

Сначала выводятся сообщения `entrypoint.sh`, а после запуска задач — новые строки из `/var/log/cron.log`:

```text
cron-1  | Creating log file...
cron-1  | Log file created at /var/log/cron.log
cron-1  | === Starting cron daemon ===
cron-1  | === Monitoring cron logs ===
```

### 4. Проверка без ожидания 6:00 и пятницы

Задачи запускаются по времени контейнера (UTC). Чтобы не ждать, можно временно поменять расписание в работающем контейнере на «каждую минуту» (файл `cronjob` при этом не меняется):

```bash
docker compose exec cron sh -c 'crontab -l | sed "s/^0 6 \* \* \*/* * * * */; s/^0 17 \* \* 5/* * * * */" | crontab -'
```

Через минуту в логе появится вывод обеих задач:

```bash
docker compose exec cron cat /var/log/cron.log
```

```text
Ошибка: дата 2026-10-25 вне периода. Доступные данные: 2025-01-01 .. 2025-09-15.
Ошибка: дата 2026-10-31 вне периода. Доступные данные: 2025-01-01 .. 2025-09-15.
```

Вернуть расписание из файла `cronjob`:

```bash
docker compose exec cron crontab /app/cronjob
```

> Сервис `lab02prep` содержит данные только за период `2025-01-01` — `2025-09-15`, а cron передаёт скрипту текущие даты (вчера и неделю назад). Поэтому скрипт записывает в лог ошибку «дата вне периода» — это проверка из лабораторной работы №2. Эти строки подтверждают, что cron запустил задачи и их вывод попал в `/var/log/cron.log`.

Получение курса из контейнера можно проверить ручным запуском с датой из периода (сервис `lab02prep` должен быть запущен):

```bash
docker compose exec cron python3 /app/currency_exchange_rate.py MDL EUR 2025-09-14
```

Скрипт выведет курс и сохранит его в файл `/app/data/MDL_EUR_2025-09-14.json` внутри контейнера.
