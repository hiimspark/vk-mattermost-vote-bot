# Бот для проведения голосований в Mattermost (Тестовое задание для стажировки в VK: Backend-разработка)

## Функционал бота

1. Создание голосования (Бот регистрирует голосование и возвращает сообщение с ID голосования и вариантами ответов).
2. Голосование (Пользователь отправляет команду, указывая ID голосования и вариант ответа).
3. Просмотр результатов (Любой пользователь может запросить текущие результаты голосования).
4. Завершение голосования (Создатель голосования может завершить его досрочно).
5. Удаление голосования (Возможность удаления голосования).

## Использования бота

### Доступные команды
```
!vote create -q="Ваш вопрос" -c="Вариант1, Вариант2" - Создать голосование
!vote vote <ID> <номер> - Проголосовать
!vote results <ID> - Показать результаты
!vote end <ID> - Завершить голосование (только для создателя)
!vote delete <ID> - Удалить голосование (только для создателя)
```
### Пример использования
1. Создание голосования.

![Создание голосования](/readme_images/1.jpg)

2. Голосование.

![Голосование](/readme_images/2.jpg)

3. Вывод результатов.

![Вывод результатов](/readme_images/3.jpg)

4. Завершение голосования.

![Завершение голосования](/readme_images/4.jpg)

5. Удаление голосования.

![Удаление голосования](/readme_images/5.jpg)

## Инструкция по сборке и запуску

1. Клонируйте репозиторий.
```bash
git clone https://github.com/hiimspark/vk-mattermost-vote-bot
cd vk-mattermost-vote-bot
```

2. Запустите сервисы:
```bash
docker-compose up -d
```

3. Создайте бота в Mattermost:
```
- Откройте Mattermost (по умолчанию: http://localhost:8065);
- Перейдите в System Console > Integrations > Bot Accounts;
- Включите Enable Bot Account Creation;
- Перейдите в Integrations > Bot Accounts;
- Создайте бота;
- Скопируйте токен бота и добавьте его в .env файл в корневой директории проекта (в формате MM_BOT_TOKEN=your_bot_token);
- Добавьте бота в вашу группу;
```

4. Пересоберите сервисы:
```bash
docker-compose up -d --build
```
