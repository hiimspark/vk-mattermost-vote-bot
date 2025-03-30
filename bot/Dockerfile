FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Настраиваем логирование
RUN mkdir -p /var/log/voting-bot && \
    touch /var/log/voting-bot/voting-bot.log && \
    chmod 666 /var/log/voting-bot/voting-bot.log

# Запускаем бота
CMD ["python", "main.py"]