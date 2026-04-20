import logging
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import Dict, Optional

# Импортируем наш синглтон конфигурации
from app.config import settings

# Логгер наследует настройки из config.py, если вызван после его инициализации
logger = logging.getLogger("aegis_guard.ml_engine")

class MLGuardEngine:
    """
    SRE Wrapper для ML-модели. 
    Обеспечивает ленивую загрузку, graceful degradation и скрывает PyTorch-специфику.
    Адаптировано для работы с любой бинарной моделью классификации (вкл. DeBERTa).
    """
    def __init__(self):
        self.model_name = settings.MODEL_NAME
        self.tokenizer = None
        self.model = None
        
        # Дефолтные индексы (будут перезаписаны при инициализации модели)
        self.idx_benign = 0
        self.idx_malicious = 1
        
        self._initialize_engine()

    def _initialize_engine(self) -> None:
        try:
            logger.info(f'{{"event": "ml_init_start", "model": "{self.model_name}"}}')
            # Строго local_files_only=True. Production сервисы не качают веса из интернета при старте.
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=True)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name, local_files_only=True)
            
            # --- ЗАЩИТА ОТ СМЕЩЕНИЯ ЛЕЙБЛОВ ---
            # Модели от разных авторов (Llama vs hlyn) могут менять местами LABEL_0 и LABEL_1.
            # Читаем конфиг модели, чтобы динамически привязать индексы.
            if hasattr(self.model.config, "id2label"):
                for idx, label in self.model.config.id2label.items():
                    l_upper = label.upper()
                    if l_upper in ["SAFE", "BENIGN", "LABEL_0"]:
                        self.idx_benign = int(idx)
                    if l_upper in ["INJECTION", "MALICIOUS", "LABEL_1"]:
                        self.idx_malicious = int(idx)
            
            # SRE Оптимизация: фиксируем граф вычислений для инференса (экономит RAM)
            self.model.eval() 
            logger.info(f'{{"event": "ml_init_success", "label_map": {{"benign": {self.idx_benign}, "malicious": {self.idx_malicious}}}}}')
        except Exception as e:
            logger.critical(f'{{"event": "ml_init_failure", "error": "{str(e)}"}}')
            self.tokenizer = None
            self.model = None

    def is_ready(self) -> bool:
        """Позволяет оркестратору узнать, жив ли ML-движок."""
        return self.model is not None and self.tokenizer is not None

    def analyze(self, text: str) -> Optional[Dict[str, float]]:
        """
        Принимает сырой текст, возвращает бинарные вероятности.
        Если движок упал, безопасно возвращает None (Fail-Safe trigger).
        """
        if not self.is_ready():
            return None

        try:
            # Ограничение 1024 токенов — защита от DoS-атак через длинный контекст
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=1024
            )

            # torch.no_grad() критичен для предотвращения утечек памяти при инференсе
            with torch.no_grad():
                logits = self.model(**inputs).logits
            
            probs = torch.nn.functional.softmax(logits, dim=-1)
            
            # Возвращаем результат, используя динамические индексы
            return {
                "benign_score": probs[0][self.idx_benign].item(),
                "malicious_score": probs[0][self.idx_malicious].item()
            }
        except Exception as e:
            # Ловим OOM (Out Of Memory) или ошибки тензоров, не роняя весь сервис
            logger.error(f'{{"event": "ml_inference_error", "error": "{str(e)}"}}')
            return None

# Инициализируем синглтон движка при импорте модуля
ml_engine = MLGuardEngine()