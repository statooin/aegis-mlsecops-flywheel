import json
import random
from pathlib import Path
from typing import List, Optional

PROMPTS_DIR = Path(__file__).parent / "prompts"

def load_dataset(category: str, limit: Optional[int] = None, shuffle: bool = True) -> List[str]:
    """
    Загружает промпты из конкретного JSON файла (категории).
    
    :param category: Имя файла без .json (например, "jailbreak" или "benign")
    :param limit: Сколько промптов вернуть (защита бюджета)
    :param shuffle: Перемешать ли список для случайной выборки
    """
    if not PROMPTS_DIR.exists():
        PROMPTS_DIR.mkdir(parents=True)
        return []

    file_path = PROMPTS_DIR / f"{category}.json" # Или {category}s.json, смотря как генерируешь
    
    # Поддержка файлов и с 's' на конце, и без
    if not file_path.exists():
        file_path = PROMPTS_DIR / f"{category}s.json"
        
    if not file_path.exists():
        print(f"⚠️ Датасет '{category}' не найден в {PROMPTS_DIR}")
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            if not isinstance(data, list):
                print(f"⚠️ Файл {file_path.name} содержит не список. Игнорируем.")
                return []

            # Перемешиваем, чтобы каждый тест был уникальным
            if shuffle:
                random.shuffle(data)

            # Обрезаем по лимиту
            if limit:
                data = data[:limit]

            return data
            
    except json.JSONDecodeError as e:
        print(f"🚨 Ошибка парсинга {file_path.name}: {e}")
        return []
    except Exception as e:
        print(f"🚨 Непредвиденная ошибка при чтении {file_path.name}: {e}")
        return []

def get_all_test_vectors(limit_per_category: int = 10) -> List[str]:
    """
    Собирает сбалансированный микс из разных категорий для общего теста.
    """
    jailbreaks = load_dataset("jailbreak", limit=limit_per_category)
    benigns = load_dataset("benign", limit=limit_per_category)
    # Если файла samosbor нет, он просто вернет пустой список благодаря нашей SRE-защите
    samosbors = load_dataset("samosbor", limit=limit_per_category) 
    
    mixed = jailbreaks + benigns + samosbors
    random.shuffle(mixed)
    return mixed