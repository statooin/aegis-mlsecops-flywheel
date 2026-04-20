import os
import json
import logging
from datetime import datetime, timezone

# --- SRE СЕКЦИЯ: OBSERVABILITY ---
class JSONFormatter(logging.Formatter):
    """
    Production-grade JSON Formatter для интеграции с Vector/ELK.
    Автоматически разворачивает вложенные JSON-сообщения.
    """
    def format(self, record):
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "service": "aegis-guard"
        }
        
        # SRE трюк: если мы передали в logger.info() готовую JSON-строку, 
        # парсим её, чтобы в логах не было экранированных кавычек (\"\").
        raw_msg = record.getMessage()
        try:
            if raw_msg.strip().startswith("{"):
                log_obj["payload"] = json.loads(raw_msg)
            else:
                log_obj["message"] = raw_msg
        except json.JSONDecodeError:
            log_obj["message"] = raw_msg
            
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def setup_logger(name="aegis_guard"):
    """Синглтон инициализация логгера, чтобы избежать дублирования строк."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
    return logger

# --- SRE СЕКЦИЯ: CONFIGURATION ---
class Config:
    """
    Синглтон конфигурации. Единая точка правды для переменных окружения.
    Иммутабельно в рантайме.
    """
    MODEL_NAME: str = os.getenv("MODEL_NAME", "meta-llama/Llama-Prompt-Guard-2-86M")
    THRESHOLD: float = float(os.getenv("GUARD_THRESHOLD", "0.5"))

# Экспортируем готовые объекты для импорта в других модулях
settings = Config()
logger = setup_logger()