FROM python:3.11-slim

# Метаданные образа
LABEL maintainer="mlsecops-team"
LABEL description="MLSecOps Red Teaming Lab with PyRIT"

# Системные зависимости (добавил curl для healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements.txt (если есть) для лучшего кэширования слоёв
# Если requirements.txt нет, можно пропустить
# COPY requirements.txt . 2>/dev/null || true

# Устанавливаем Python-зависимости одним слоем
RUN pip install --no-cache-dir \
    pyrit==0.9.0 \
    requests \
    litellm \
    google-generativeai \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Верификация окружения
RUN python3 -c "import pyrit; import litellm; import torch; print('✅ PyRIT environment ready!')"

# Создаём непривилегированного пользователя (хорошая практика безопасности)
RUN useradd -m -u 1000 pyrit && chown -R pyrit:pyrit /app
USER pyrit

ENTRYPOINT ["python3"]