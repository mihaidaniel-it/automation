#!/bin/bash
# shebang - говорит ОС, что этот файл нужно выполнить через bash

set -euo pipefail

# Проверяем условием, что если в перменной $1 нету названия папки, то выводим ..
if [ -z "$1" ]; then
    echo "Ошибка: путь директории неправильный."
    echo "Usage: ./backup.sh <source_directory> [backup_directory]"
    exit 1
fi

# Присваиваем переменной аргумент $1
SOURCE_DIR="$1"

# Если не указан второй аргумент, то мы сохраняем пусть по /backup
# Если указан второй аргумент, то сохраняем название аргумента
BACKUP_DIR="${2:-/backup}"

if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
fi

# Проверяем, НЕ(!) существует ли исходная директория
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Ошибка: директории '$SOURCE_DIR' не существует."
    exit 1
fi

# Проверяем, НЕ(!) существует ли бэкап директория
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Ошибка: директории '$BACKUP_DIR' не существует."
    exit 1
fi

# Переменная с текущей датой
CURRENT_DATE=$(date +"%Y-%m-%d")

# Получаем название исходной директории через basename
DIR_NAME=$(basename "$SOURCE_DIR")

# Название файла бэкапа
BACKUP_FILE="$BACKUP_DIR/${DIR_NAME}_${CURRENT_DATE}.tar.gz"

# Создаем архив
tar -czf "$BACKUP_FILE" "$SOURCE_DIR"

echo "Бэкап сделан успешно"
echo "Бэкап файл: $BACKUP_FILE"