import os
import base64
import logging
import torch
from fastapi import FastAPI, Request, Response, HTTPException
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from pydantic import BaseModel

# --- СЕКЦИЯ: ЛОГИРОВАНИЕ ---
# Устанавливаем формат вывода для SRE-мониторинга. 
# Позволяет Vector или Fluentbit легко парсить логи по уровню важности.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- СЕКЦИЯ: ИНИЦИАЛИЗАЦИЯ APP ---
# Создаем экземпляр FastAPI. Это ядро нашего Guard-сервиса.
app = FastAPI(title="Aegis AI Gateway - Guard Service")

# Имя модели Meta на HuggingFace. Используется для идентификации в логах и конфигах.
MODEL_NAME = "meta-llama/Prompt-Guard-86M"

# --- КОНФИГУРАЦИЯ БЕЗОПАСНОСТИ ---
# os.getenv: Извлекает значение из переменных окружения (из .env).
# float(): Преобразует строку в число с плавающей точкой для математического сравнения.
# Параметр "0.8": Дефолтное значение, если переменная GUARD_THRESHOLD не задана.
THRESHOLD = float(os.getenv("GUARD_THRESHOLD", "0.8"))

logger.info(f"Init: Security threshold (Jailbreak) set to {THRESHOLD}")

# --- СЕКЦИЯ: ЗАГРУЗКА ML-ЯДРА (INFERENCE ENGINE) ---
# Оборачиваем в try-except, чтобы сервис не "упал" при старте, если модель повреждена.
try:
    logger.info(f"Loading model {MODEL_NAME} from local cache...")
    # local_files_only=True: Гарантирует Air-gapped режим. Сервис не пойдет в интернет.
    # AutoTokenizer: Превращает текст в набор чисел (токенов), понятных модели.
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
    # AutoModel...: Загружает веса нейросети для классификации последовательностей.
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, local_files_only=True)
    logger.info("SUCCESS: Model loaded and ready for inference.")
except Exception as e:
    # Если загрузка не удалась, помечаем объекты как None. Дальше сработает fallback-логика.
    logger.critical(f"FATAL: Model loading failed. Check /app/model_cache. Error: {e}")
    tokenizer = None
    model = None

# --- СЕКЦИЯ: МОДЕЛИ ДАННЫХ ---
# Pydantic-схема для валидации входного JSON, если запрос идет не через Envoy.
class SecurityCheckRequest(BaseModel):
    input_text: str

# --- ЭНДПОИНТ: HEALTHCHECK ---
# Используется балансировщиками (Envoy/K8s) для проверки живучести сервиса.
@app.get("/health")
def health():
    if model is None:
        raise HTTPException(status_code=503, detail="Model initialization failed")
    return {"status": "ok", "threshold": THRESHOLD, "model": MODEL_NAME}

# --- ЭНДПОИНТ: DIAGNOSTIC (DEBUG) ---
# Служит для "пристрелки" порогов. Выводит вероятности по всем трем классам.
@app.post("/debug")
async def debug_prompt(request: Request):
    """Эндпоинт для диагностики. Показывает сырые веса модели."""
    # Получаем сырое тело запроса напрямую из HTTP-пакета.
    raw_body = await request.body()
    # Декодируем байты в UTF-8. errors="replace" предотвращает падение на битых символах.
    text = raw_body.decode("utf-8", errors="replace") if raw_body else ""
    
    if not text or not model or not tokenizer:
        return {"error": "no text or model"}
    
    # Подготовка данных для нейросети.
    # truncation=True & max_length=512: Обрезает текст под лимит модели (защита от перегрузки GPU/CPU).
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    
    # torch.no_grad(): Отключает вычисление градиентов. Экономит до 50% RAM и ускоряет инференс.
    with torch.no_grad():
        logits = model(**inputs).logits
        
    # Softmax: Превращает абстрактные веса (логиты) в понятные вероятности от 0.0 до 1.0.
    probs = torch.nn.functional.softmax(logits, dim=-1)
    
    # Возвращаем JSON с результатами классификации.
    return {
        "text": text,
        "id2label": model.config.id2label if hasattr(model, "config") else "unknown",
        "raw_scores": {
            "index_0": round(probs[0][0].item(), 4), # Вероятность BENIGN (безопасно)
            "index_1": round(probs[0][1].item(), 4), # Вероятность INJECTION (внедрение)
            "index_2": round(probs[0][2].item(), 4), # Вероятность JAILBREAK (взлом)
        }
    }

# --- ОСНОВНОЙ ЭНДПОИНТ: CHECK (SECURITY GATEWAY) ---
# Сюда Envoy перенаправляет каждый входящий запрос для верификации.
@app.post("/check")
async def check_prompt(request: Request):
    # Пытаемся извлечь тело из заголовка x-envoy-auth-partial-body.
    # Envoy кодирует тело в Base64, если включен флаг pack_as_bytes в ext_authz.
    encoded_body = request.headers.get("x-envoy-auth-partial-body", "")
    if encoded_body:
        try:
            # Декодируем Base64 обратно в текст.
            text = base64.b64decode(encoded_body).decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Failed to decode base64 header: {e}")
            text = ""
    else:
        # Если заголовка нет (тест через curl), читаем напрямую тело запроса.
        raw_body = await request.body()
        text = raw_body.decode("utf-8", errors="replace") if raw_body else ""

    # Если текста нет, пропускаем запрос (пустые промпты не опасны).
    if not text:
        return Response(status_code=200)

    # Процесс проверки ML-моделью.
    if model and tokenizer:
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        with torch.no_grad():
            logits = model(**inputs).logits

        probs = torch.nn.functional.softmax(logits, dim=-1)

        # Извлекаем значения для логики принятия решений.
        # .item() вытаскивает число из тензора PyTorch.
        benign_score    = probs[0][0].item()
        injection_score = probs[0][1].item()
        jailbreak_score = probs[0][2].item()

        # КРИТИЧЕСКАЯ ЛОГИКА: 
        # На основе тестов блокируем ТОЛЬКО по jailbreak_score. 
        # Порог THRESHOLD (0.8) определяет "жесткость" фильтра.
        if jailbreak_score > THRESHOLD:
            logger.warning(
                f"BLOCKED! Jailbreak detected. Jlb={jailbreak_score:.3f} (Threshold: {THRESHOLD})"
            )
            # Возвращаем 403. Envoy интерпретирует это как команду прервать соединение с пользователем.
            raise HTTPException(status_code=403, detail="Access denied by Aegis AI Guard")

        # Если проверка пройдена, пишем результат в логи для дальнейшего анализа в Grafana.
        logger.info(
            f"PASSED: Benign={benign_score:.3f}, Inj={injection_score:.3f}, Jlb={jailbreak_score:.3f}"
        )

    else:
        # FALLBACK: Если ML-модель недоступна, используем старые добрые регулярки (сигнатуры).
        logger.error("ML Model offline. Using heuristic fallback.")
        blacklisted = ["IGNORE ALL PREVIOUS INSTRUCTIONS", "DROP TABLE", "SELECT * FROM"]
        if any(trigger in text.upper() for trigger in blacklisted):
            raise HTTPException(status_code=403, detail="Blocked by Heuristic Guard")

    # Статус 200 OK: Сигнал для Envoy, что запрос безопасен и его можно проксировать к LLM.
    return Response(status_code=200)

# --- ТОЧКА ВХОДА ---
if __name__ == "__main__":
    import uvicorn
    # Запуск сервера на порту 8080.
    uvicorn.run(app, host="0.0.0.0", port=8080)
