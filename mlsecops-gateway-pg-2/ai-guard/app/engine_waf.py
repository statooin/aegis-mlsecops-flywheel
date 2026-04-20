import re
import base64
import hashlib
from typing import Dict, Any

# --- SRE СЕКЦИЯ: СИГНАТУРЫ (ZERO-COST ABSTRACTION) ---
# Компилируем один раз при импорте модуля.
HEURISTIC_PATTERNS = {
    "prompt_injection": re.compile(
        r"(ignore|disregard|forget|override)\b.*\b(instructions|guidelines|rules|prior)", 
        re.IGNORECASE | re.DOTALL
    ),
    "system_access": re.compile(
        r"(system prompt|developer mode|root password|kernel version|env variables)", 
        re.IGNORECASE
    ),
    "sqli_basic": re.compile(
        r"(drop table|select \* from|union select|insert into|delete from)", 
        re.IGNORECASE
    ),
    "rce_attempt": re.compile(
        r"(\bsh\b|\bbash\b|curl|wget|rm -rf|chmod)\s+", 
        re.IGNORECASE
    )
}

def _unwrap_base64(text: str) -> str:
    """
    Anti-Evasion: Ищет токены Base64 ВНУТРИ текста и распаковывает их.
    Решает проблему составных пейлоадов (например: "Exec: aWdub3Jl...").
    """
    words = text.split()
    decoded_fragments = []
    
    for word in words:
        clean_word = word.strip()
        # Эвристика: слово похоже на Base64 (длина > 16, только нужные символы, кратно 4)
        if len(clean_word) > 16 and re.match(r'^[A-Za-z0-9+/]+={0,2}$', clean_word):
            if len(clean_word) % 4 == 0:
                try:
                    decoded = base64.b64decode(clean_word).decode('utf-8', errors='strict')
                    if decoded.isprintable(): 
                        decoded_fragments.append(decoded)
                except Exception:
                    pass # Игнорируем мусор, который случайно совпал по формату
                    
    if decoded_fragments:
        # Склеиваем оригинал и раскодированные куски для прогона по регуляркам
        return f"{text}\n---DECODED---\n" + "\n".join(decoded_fragments)
    return text

def analyze_text(text: str) -> Dict[str, Any]:
    """
    Основная точка входа L1 Guard (Эвристика).
    Возвращает словарь с результатами анализа, готовый для логирования и принятия решений.
    """
    text_to_analyze = _unwrap_base64(text)
    
    detected_threats = []
    for category, pattern in HEURISTIC_PATTERNS.items():
        if pattern.search(text_to_analyze):
            detected_threats.append(category)

    # Хешируем оригинальный текст (Privacy Protocol)
    payload_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    
    return {
        "is_blocked": len(detected_threats) > 0,
        "categories": detected_threats,
        "payload_hash": payload_hash,
        "payload_length": len(text)
    }