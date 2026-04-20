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

# Get model name
ARG MODEL_NAME

# Слой с весами модели. Запекается один раз и кэшируется навсегда.
# Меняем код приложения -> этот слой НЕ пересобирается.
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    name = '${MODEL_NAME}'; \
    AutoTokenizer.from_pretrained(name, token='${HF_TOKEN}'); \
    AutoModelForSequenceClassification.from_pretrained(name, token='${HF_TOKEN}')"

# --- ОБНОВЛЕНО: Копируем структуру пакета ---
# Берем локальную папку app/ и кладем ее в контейнер по пути /app/app/
COPY app/ ./app/

EXPOSE 8080

# --- ОБНОВЛЕНО: Новая точка входа ---
# Указываем Uvicorn искать инстанс FastAPI (app) внутри модуля app.main
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]