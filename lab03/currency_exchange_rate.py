import argparse
import json
import os
import sys
from datetime import datetime

import requests

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ERROR_LOG = os.path.join(PROJECT_ROOT, "error.log")

DEFAULT_API_URL = "http://localhost:8080/"
DEFAULT_API_KEY = "EXAMPLE_API_KEY"

# Период за который есть данные по курсам валют
MIN_DATE = datetime(2025, 1, 1)
MAX_DATE = datetime(2025, 9, 15)


# Если произошла ошибка, то ошибка выводится в консоль и сохраняется в логах
def log_error(message):
    print(message, file=sys.stderr)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {message}\n")
    except OSError as error:
        print(f"Ошибка: не удалось записать в {ERROR_LOG}: {error}", file=sys.stderr)


# Записывается текст ошибки для лога и скрипт завершается
def fail(message):
    log_error(f"Ошибка: {message}")
    sys.exit(1)


# Валидация вводных данных
def get_arguments():
    parser = argparse.ArgumentParser(
        description="Получение курса одной валюты к другой на указанную дату "
                    "и сохранение результата в JSON-файл.",
        epilog="Пример: python currency_exchange_rate.py USD EUR 2025-01-01",
    )
    parser.add_argument("from_currency", help="Из какой валюты конвертация (пр.: EUR)")
    parser.add_argument("to_currency", help="В какую валюту конвертация (пр.: USD)")
    parser.add_argument("date", help="Дата в формате YYYY-MM-DD")
    parser.add_argument(
        "--url",
        default=os.environ.get("API_URL", DEFAULT_API_URL),
        help=f"Адрес сервиса (по умолчанию: $API_URL или {DEFAULT_API_URL})",
    )

    parser.add_argument(
        "--key",
        default=os.environ.get("API_KEY", DEFAULT_API_KEY),
        help="API-ключ (по умолчанию: $API_KEY или ключ из sample.env)",
    )

    # Если аргументов меньше трёх (и это не вызов справки -h), записываем ошибку в лог,
    # т.к. argparse сам печатает ошибку и выходит с кодом 2, но в лог не пишет
    if len(sys.argv) < 4 and not {"-h", "--help"} & set(sys.argv):
        log_error(
            "Ошибка: ожидается 3 аргумента: ИЗ_ВАЛЮТЫ В_ВАЛЮТУ ДАТА"
        )

    # Разбор аргументов, далее они доступны как args.from_currency, args.date и т.д.
    args = parser.parse_args()

    # Перевод валют в верхний регистр
    args.from_currency = args.from_currency.upper()
    args.to_currency = args.to_currency.upper()

    # Проверка, что код валюты состоит из 3 букв
    for currency in (args.from_currency, args.to_currency):
        if len(currency) != 3 or not currency.isalpha():
            fail(f"неверный код валюты '{currency}'. Используйте код из 3 букв, пр.: USD.")

    # Проверка формата даты: если строка не подходит под YYYY-MM-DD
    try:
        date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        fail(f"неверная дата '{args.date}'. Используйте формат YYYY-MM-DD.")

    # Проверка на вхождение вводных дат по дате в диапозон
    if not MIN_DATE <= date <= MAX_DATE:
        fail(
            f"дата {args.date} вне периода. Доступные данные: "
            f"{MIN_DATE:%Y-%m-%d} .. {MAX_DATE:%Y-%m-%d}."
        )

    return args


# Отправка запроса к серверу
def get_exchange_rate(url, key, currency_from, currency_to, date):
    params = {"from": currency_from, "to": currency_to, "date": date}

    # Обработка ошибок запросов к серверу
    try:
        response = requests.post(url, params=params, data={"key": key}, timeout=10)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        fail(f"Не запущен {url}")
    except requests.exceptions.Timeout:
        fail(f"Слишком долгое ожидание по адресу {url}")
    except requests.exceptions.RequestException as error:
        fail(f"Запрос к API не успешен: {error}")

    try:
        payload = response.json()
    except ValueError:
        fail(f"Сервер вернул неправильный JSON: {response.text[:200]!r}")


    if payload.get("error"):
        fail(f"сервис ответил: {payload['error']}")

    data = payload.get("data")
    if not isinstance(data, dict) or "rate" not in data:
        fail(f"Неправильный ответ сервера: {payload}")

    # Разница между курсами в коротком варианте
    data["rate"] = round(float(data["rate"]), 2)

    return data


# Сохранение результата в формате JSON в папке data
def save_to_json(data):
    filename = f"{data['from']}_{data['to']}_{data['date']}.json"
    filepath = os.path.join(DATA_DIR, filename)

    try:
        os.makedirs(DATA_DIR, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
    except OSError as error:
        fail(f"не удалось сохранить JSON-файл {filepath}: {error}")

    return filepath


def main():
    args = get_arguments()

    print(
        f"Запрос данных для: {args.from_currency}/{args.to_currency} "
        f"для {args.date}..."
    )

    data = get_exchange_rate(
        args.url, args.key, args.from_currency, args.to_currency, args.date
    )

    filepath = save_to_json(data)

    print(f"Разница между валютами: {data['from']} -> {data['to']} = {data['rate']:.2f}")
    print(f"Данные сохранились в: {filepath}")


if __name__ == "__main__":
    main()
