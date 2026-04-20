FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Принимаем токен как аргумент сборки
ARG HF_TOKEN
ENV HF_HOME=/app/model_cache

# Слой с весами модели. Запекается один раз и кэшируется навсегда.
# Меняем код приложения -> этот слой НЕ пересобирается.
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    name = 'meta-llama/Prompt-Guard-86M'; \
    AutoTokenizer.from_pretrained(name, token='${HF_TOKEN}'); \
    AutoModelForSequenceClassification.from_pretrained(name, token='${HF_TOKEN}')"

# Код копируем В САМОМ КОНЦЕ.
COPY app.py .

EXPOSE 8080

# Базовая команда без --reload (для продакшена)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]