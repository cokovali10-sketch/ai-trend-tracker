# AI Trend Tracker — контейнеризация
FROM python:3.12-slim

WORKDIR /app

# Копируем зависимости отдельно (кэширование слоёв Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники
COPY . .

# Тома для данных и логов (переживают перезапуск контейнера)
VOLUME ["/app/data", "/app/logs"]

# Порт веб-дашборда
EXPOSE 5000

# Запуск дашборда: python main.py dashboard --host 0.0.0.0
CMD ["python", "main.py", "dashboard", "--host", "0.0.0.0"]
