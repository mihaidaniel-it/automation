# Базовый образ - официальный SSH-агент Jenkins (в нем уже есть Java, sshd и пользователь jenkins)
FROM jenkins/ssh-agent

# Устанавливаем PHP-CLI, а также SQLite для PHP и утилиту sqlite3 - они нужны тестам проекта containers08
RUN apt-get update && apt-get install -y php-cli php-sqlite3 sqlite3

# Создаем папку для базы данных (путь из site/config.php проекта) и отдаем ее пользователю jenkins
RUN mkdir -p /var/www/db && chown jenkins:jenkins /var/www/db
