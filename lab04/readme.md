# Лабораторная работа №4

**Выполнил:** Михай Даниел, I2402
**Курс:** Automation and Scripting

---

## Задание

Настроить Jenkins для автоматизации DevOps-задач:

1. В `docker-compose.yml` описать два сервиса: Jenkins Controller и SSH-агент;
2. Запустить Jenkins Controller и настроить его по инструкциям на экране;
3. Создать SSH-ключи в папке `secrets`, `Dockerfile` для SSH-агента с PHP и файл `.env` с публичным ключом;
4. Подключить SSH-агента к Jenkins: добавить SSH-ключ в Credentials и создать узел `ssh-agent1` с меткой `php-agent`;
5. Создать pipeline для PHP-проекта с unit-тестами и убедиться, что тесты проходят.

---

## 1. Описание проекта

Проект поднимает в Docker сервер Jenkins и отдельный агент для сборок:

- **jenkins-controller** — главный сервер Jenkins: веб-интерфейс на `http://localhost:8080`, хранит настройки и задачи, распределяет сборки по агентам;
- **ssh-agent** — контейнер на основе `jenkins/ssh-agent`, в который установлены PHP и SQLite. Jenkins подключается к нему по SSH и выполняет на нём сборки.

Оба контейнера находятся в одной сети `jenkins-network`, поэтому контроллер находит агента по имени `ssh-agent`.

```text
Браузер ──► jenkins-controller (:8080) ──SSH──► ssh-agent (PHP + SQLite)
                                                  │
                                                  ├── git clone containers08
                                                  └── php tests/tests.php
```

Для pipeline выбран проект [containers08](https://github.com/mihaidaniel-it/containers08) из курса «Виртуализация и контейнеризация». В нём есть unit-тесты (`tests/testframework.php`, `tests/tests.php`) для класса `Database`, который работает с базой SQLite:

- `Connection` — подключение к базе;
- `Count` — в таблице `page` не меньше 3 записей;
- `Create` — добавление новой записи.

### Структура папки `lab04`

```text
lab04/
├── docker-compose.yml   # сервисы jenkins-controller и ssh-agent, тома и сеть
├── Dockerfile           # образ SSH-агента: jenkins/ssh-agent + PHP + SQLite
├── Jenkinsfile          # pipeline для проекта containers08
├── .env                 # JENKINS_AGENT_SSH_PUBKEY - публичный SSH-ключ агента
├── .gitignore           # папка secrets/ не загружается в GitHub
├── secrets/             # не в git: ключи и пароль администратора
│   ├── jenkins_agent_ssh_key        # приватный ключ (добавлен в Jenkins Credentials)
│   ├── jenkins_agent_ssh_key.pub    # публичный ключ (его содержимое в .env)
│   └── jenkins_admin_password.txt   # пароль пользователя admin в Jenkins
└── readme.md
```

---

## 2. Настройка Jenkins Controller

1. Описал сервис `jenkins-controller` в `docker-compose.yml` (образ `jenkins/jenkins:lts`, порты `8080` и `50000`, том `jenkins_home`, сеть `jenkins-network`) и запустил только его:

   ```bash
   cd lab04
   docker compose up -d jenkins-controller
   ```

   > Порт `8080` должен быть свободен. Например, сервис `lab02prep` из лабораторной работы №2 тоже использует `8080`, поэтому одновременно их запустить нельзя.

2. Открыл `http://localhost:8080`. На странице **Unlock Jenkins** ввёл начальный пароль администратора:

   ```bash
   docker exec jenkins-controller cat /var/jenkins_home/secrets/initialAdminPassword
   ```

3. **Customize Jenkins** → **Install suggested plugins**. В этот набор входят Pipeline, Git, Credentials и SSH Build Agents;
4. **Create First Admin User** — создал пользователя `admin` (пароль хранится в `secrets/jenkins_admin_password.txt`);
5. **Instance Configuration** — оставил адрес `http://localhost:8080/` → **Save and Finish** → **Start using Jenkins**.

Версия Jenkins — **2.580.2 LTS** (Java 21). Настройки хранятся в томе `jenkins_home` и сохраняются после перезапуска контейнера.

---

## 3. Настройка SSH-агента

### 3.1. SSH-ключи

```bash
mkdir secrets
cd secrets
ssh-keygen -f jenkins_agent_ssh_key -N "" -C "jenkins-agent"
```

- `-N ""` — ключ без пароля (passphrase), чтобы Jenkins мог подключаться автоматически;
- `-C` — комментарий ключа. По умолчанию создаётся ключ типа `ed25519`, Jenkins его поддерживает.

Получились два файла: приватный ключ `jenkins_agent_ssh_key` (для Jenkins) и публичный `jenkins_agent_ssh_key.pub` (для агента).

### 3.2. `Dockerfile` для агента

```dockerfile
# Базовый образ - официальный SSH-агент Jenkins (в нем уже есть Java, sshd и пользователь jenkins)
FROM jenkins/ssh-agent

# Устанавливаем PHP-CLI, а также SQLite для PHP и утилиту sqlite3 - они нужны тестам проекта containers08
RUN apt-get update && apt-get install -y php-cli php-sqlite3 sqlite3

# Создаем папку для базы данных (путь из site/config.php проекта) и отдаем ее пользователю jenkins
RUN mkdir -p /var/www/db && chown jenkins:jenkins /var/www/db
```

К `php-cli` из задания добавлены пакеты, без которых тесты проекта не запустятся (см. раздел «Проблемы»):

- `php-sqlite3` — драйвер PDO SQLite;
- `sqlite3` — утилита для создания базы из `sql/schema.sql`;
- папка `/var/www/db` — путь к базе, указанный в `config.php` проекта.

В образе агента: Debian 13, Java 21, PHP 8.4, git.

### 3.3. Сервис `ssh-agent` и файл `.env`

Сервис `ssh-agent` в `docker-compose.yml` собирается из `Dockerfile`, получает публичный ключ из переменной `JENKINS_AGENT_SSH_PUBKEY`, хранит рабочую папку `/home/jenkins/agent` в томе `jenkins_agent_volume` и запускается после контроллера (`depends_on`).

Файл `.env` (Docker Compose читает его автоматически):

```text
# Публичный SSH-ключ агента (содержимое файла secrets/jenkins_agent_ssh_key.pub)
JENKINS_AGENT_SSH_PUBKEY=ssh-ed25519 AAAAC3Nza... jenkins-agent
```

Перезапуск проекта, чтобы применить изменения:

```bash
docker compose down
docker compose up -d --build
```

```text
NAME                 IMAGE                 STATUS         PORTS
jenkins-controller   jenkins/jenkins:lts   Up             0.0.0.0:8080->8080/tcp, 0.0.0.0:50000->50000/tcp
ssh-agent            lab04-ssh-agent       Up             22/tcp
```

### 3.4. Плагин SSH Build Agents

**Manage Jenkins → Plugins → Installed plugins** — плагин **SSH Build Agents** (в задании он назван SSH Agents Plugin) уже установлен вместе с рекомендуемыми плагинами (версия 3.1097).

### 3.5. SSH-ключ в Credentials

**Manage Jenkins → Credentials → System → Global credentials → Add Credentials**:

- тип — **SSH Username with private key** → **Next**;
- ID — `jenkins-agent-ssh-key`;
- Username — `jenkins`;
- Private Key → **Enter directly** → **Add** → вставил содержимое `secrets/jenkins_agent_ssh_key`;
- Passphrase — пусто → **Create**.

### 3.6. Ключ хоста агента в `known_hosts`

Jenkins по умолчанию проверяет SSH-ключ хоста агента по файлу `known_hosts` (защита от подмены сервера). Добавил ключ агента в `known_hosts` контроллера:

```bash
docker exec jenkins-controller sh -c 'mkdir -p ~/.ssh && ssh-keyscan ssh-agent >> ~/.ssh/known_hosts'
```

Отпечатки ключей можно сверить с ключами самого агента — они должны совпадать:

```bash
docker exec jenkins-controller sh -c 'ssh-keygen -lf ~/.ssh/known_hosts'
docker exec ssh-agent sh -c 'for f in /etc/ssh/ssh_host_*_key.pub; do ssh-keygen -lf $f; done'
```

### 3.7. Узел `ssh-agent1`

**Manage Jenkins → Nodes → New Node**: имя `ssh-agent1`, тип **Permanent Agent** → **Create**:

| Параметр                       | Значение                                   |
|--------------------------------|--------------------------------------------|
| Number of executors            | `1`                                        |
| Remote root directory          | `/home/jenkins/agent`                      |
| Labels                         | `php-agent`                                |
| Launch method                  | `Launch agents via SSH`                    |
| Host                           | `ssh-agent`                                |
| Credentials                    | `jenkins` (ключ из п. 3.5)                 |
| Host Key Verification Strategy | `Known hosts file Verification Strategy`   |

После **Save** агент подключился. Лог узла (**Nodes → ssh-agent1 → Log**):

```text
[SSH] SSH host key matches key in Known Hosts file. Connection will be allowed.
[SSH] Authentication successful.
[SSH] Starting agent process: cd "/home/jenkins/agent" && java -jar remoting.jar ...
Agent successfully connected and online
```

---

## 4. Создание и настройка Jenkins Pipeline

1. **Dashboard → New Item** → имя `containers08-pipeline` → тип **Pipeline** → **OK**;
2. В разделе **Pipeline**: Definition — **Pipeline script**, в поле Script вставил содержимое файла `Jenkinsfile` → **Save**;
3. **Build Now** → открыть сборку → **Console Output**.

### `Jenkinsfile`

```groovy
pipeline {
    // Pipeline выполняется на агенте с меткой php-agent (наш SSH-агент)
    agent {
        label 'php-agent'
    }

    stages {
        stage('Install Dependencies') {
            steps {
                // Подготовка проекта: скачиваем код, создаем базу данных и копируем тесты
                echo 'Preparing project...'
                // Скачиваем проект containers08 из GitHub в рабочую папку агента
                git branch: 'main', url: 'https://github.com/mihaidaniel-it/containers08.git'
                // Удаляем базу от прошлой сборки и создаем новую из sql/schema.sql
                sh 'rm -f /var/www/db/db.sqlite && sqlite3 /var/www/db/db.sqlite < sql/schema.sql'
                // Копируем тесты в папку site, т.к. они подключают ../config.php и ../modules
                sh 'cp -r tests site/'
            }
        }

        stage('Test') {
            steps {
                // Запуск тестов
                echo 'Running tests...'
                // Запускаем тесты и сохраняем их вывод в файл tests.log
                sh 'php site/tests/tests.php > tests.log'
                // Выводим результат тестов в консоль Jenkins
                sh 'cat tests.log'
                // Фреймворк тестов не возвращает код ошибки, если тест не прошел,
                // поэтому ищем в выводе строки с ERROR и в этом случае завершаем этап с ошибкой
                sh 'if grep ERROR tests.log; then exit 1; fi'
            }
        }
    }

    // Действия после завершения pipeline
    post {
        always {
            echo 'Pipeline completed.'
        }
        success {
            echo 'All stages completed successfully!'
        }
        failure {
            echo 'Errors detected in the pipeline.'
        }
    }
}
```

- `agent { label 'php-agent' }` — сборка идёт на узле с меткой `php-agent`, то есть на `ssh-agent1`;
- **Install Dependencies** — скачивает проект, создаёт базу SQLite из `sql/schema.sql` и копирует тесты в `site/` (так же делает GitHub Actions самого проекта);
- **Test** — запускает тесты, выводит результат и завершает этап с ошибкой, если какой-то тест не прошёл;
- **post** — сообщения после сборки: `always` — всегда, `success` — при успехе, `failure` — при ошибке.

### Результат

Pipeline выполнился успешно, все 3 теста прошли. Вывод сборки (сокращён):

```text
Started by user Administrator
Running on ssh-agent1 in /home/jenkins/agent/workspace/containers08-pipeline
[Pipeline] { (Install Dependencies)
Preparing project...
Cloning repository https://github.com/mihaidaniel-it/containers08.git
+ rm -f /var/www/db/db.sqlite
+ sqlite3 /var/www/db/db.sqlite
+ cp -r tests site/
[Pipeline] { (Test)
Running tests...
+ php site/tests/tests.php
+ cat tests.log
2026-11-01 18:12:55 [INFO] Running test Connection
2026-11-01 18:12:55 [INFO] Pass
2026-11-01 18:12:55 [INFO] End test Connection
2026-11-01 18:12:55 [INFO] Running test Count
2026-11-01 18:12:55 [INFO] Pass
2026-11-01 18:12:55 [INFO] End test Count
2026-11-01 18:12:55 [INFO] Running test Create
2026-11-01 18:12:55 [INFO] Pass
2026-11-01 18:12:55 [INFO] End test Create
3 / 3
+ grep ERROR tests.log
[Pipeline] { (Declarative: Post Actions)
Pipeline completed.
All stages completed successfully!
Finished: SUCCESS
```

Повторные сборки тоже прошли успешно: #2 — сразу после первой, #3 — после пересоздания контейнеров (`docker compose down` → `up`). База пересоздаётся перед каждым запуском.

---

## 5. Ответы на вопросы

### Какие преимущества у Jenkins для автоматизации DevOps-задач?

- **Бесплатный и open-source**, разворачивается на своём сервере — код и данные остаются внутри своей инфраструктуры;
- **Pipeline as Code** — pipeline описывается в `Jenkinsfile`, который хранится в git вместе с проектом: есть история изменений и code review, сборку легко воспроизвести;
- **Распределённые сборки** — контроллер раздаёт задачи агентам: сборки идут параллельно, у каждого агента своё окружение (как наш агент с PHP);
- **Большое количество плагинов** (Git, GitHub, Docker, Kubernetes, SSH, уведомления в Slack и на почту, отчёты по тестам);
- **Разные способы запуска**: вручную, по расписанию (синтаксис cron), при изменениях в репозитории (webhook или опрос SCM), после других задач;
- **Наглядность** — история сборок, логи каждого шага, этапы pipeline и действия `post` (уведомления, очистка) при успехе или ошибке;
- **Универсальность** — через shell-команды работает с любыми языками и инструментами на Linux, Windows и macOS.

### Какие ещё бывают агенты Jenkins?

- **Built-in node** — сам контроллер. Запускать на нём сборки не рекомендуется из соображений безопасности;
- **Постоянные (Permanent) агенты**:
  - **SSH-агенты** (как в этой работе) — контроллер сам подключается к агенту по SSH и запускает `remoting.jar`;
  - **Inbound-агенты** (раньше JNLP) — агент сам подключается к контроллеру через порт `50000` или WebSocket. Удобно, когда агент находится за NAT или firewall (образ `jenkins/inbound-agent`);
  - **Windows-агенты** — работают как служба Windows или через OpenSSH;
- **Облачные (динамические) агенты** — создаются под сборку и удаляются после неё:
  - **Docker** (плагин Docker) — отдельный контейнер на каждую сборку;
  - **Kubernetes** (плагин Kubernetes) — отдельный pod на каждую сборку;
  - **виртуальные машины в облаке** — плагины Amazon EC2, Azure VM Agents, Google Compute Engine;
- **Docker-агент в pipeline** — `agent { docker { image 'php:8.4-cli' } }`: этап выполняется в контейнере на агенте, где установлен Docker.

### Какие проблемы возникли при настройке Jenkins и как я их решил?

1. **Агент не подключался: «Key exchange was not finished, connection is closed».** По умолчанию Jenkins проверяет ключ хоста агента по `/var/jenkins_home/.ssh/known_hosts`, а этого файла в новом контроллере нет. Отключать проверку («Non verifying Verification Strategy») я не стал, потому что тогда к Jenkins можно подставить чужой сервер. Вместо этого добавил ключ агента в `known_hosts` командой `ssh-keyscan` и сверил отпечатки с ключами самого агента (п. 3.6).
   > Агент создаёт новые ключи хоста при пересоздании контейнера (`docker compose down` → `up`). После этого запись нужно обновить:
   >
   > ```bash
   > docker exec jenkins-controller sh -c 'ssh-keygen -R ssh-agent && ssh-keyscan ssh-agent >> ~/.ssh/known_hosts'
   > ```
2. **На агенте было только `php-cli`, а проекту нужна база SQLite.** Тесты используют `PDO` с драйвером SQLite, а база создаётся из `sql/schema.sql`. Добавил в `Dockerfile` пакеты `php-sqlite3` и `sqlite3`;
3. **Путь к базе жёстко задан в `config.php`: `/var/www/db/db.sqlite`.** На агенте такой папки нет, а пользователь `jenkins` не может создать её сам. Создал папку в `Dockerfile` и отдал её пользователю `jenkins`. Перед каждой сборкой базу пересоздаю, иначе `schema.sql` падает на уже существующей таблице;
4. **Тесты лежат в `tests/`, но подключают `../config.php` и `../modules/`** (рассчитаны на запуск из папки сайта). Как и в GitHub Actions проекта, копирую папку `tests` в `site/` перед запуском;
5. **Фреймворк тестов проекта всегда завершается с кодом 0**, даже если тест не прошёл. Тогда Jenkins показал бы успешную сборку при упавших тестах. Добавил проверку: если в выводе есть `ERROR`, этап завершается с ошибкой. Проверил: если специально сломать тест, PHP всё равно возвращает код 0, а проверка находит `ERROR` и возвращает ошибку;
6. **Названия пунктов меню отличаются от задания** (в Jenkins 2.580): «Manage Plugins» → **Plugins**, «Manage Credentials» → **Credentials**, «Manage Nodes and Clouds» → **Nodes**, «SSH Agents Plugin» → **SSH Build Agents**. Credentials теперь добавляются через окно: сначала выбирается тип, потом **Next**.

---

## Полезные команды

```bash
# запуск (из папки lab04)
docker compose up -d --build

# состояние контейнеров
docker compose ps

# остановка (настройки Jenkins сохраняются в томах)
docker compose down
```

Вход в Jenkins: `http://localhost:8080`, пользователь `admin`, пароль — в файле `secrets/jenkins_admin_password.txt`.

> `docker compose down -v` удаляет и тома — все настройки Jenkins (пользователь, ключи, узел, pipeline) придётся делать заново.
