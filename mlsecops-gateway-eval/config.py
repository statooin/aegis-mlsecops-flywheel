import os
import logging

# Настройки Gateway
AEGIS_URL = os.getenv("AEGIS_URL", "http://localhost:8080")

# Настройки Модели
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL = "gemini-1.5-flash"

# Настройка логирования
def setup_logging(verbose: bool = False):
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

# Указываем PyRIT хранить базу DuckDB в папке data/
os.environ["PYRIT_MEMORY_URI"] = "duckdb:///data/pyrit_memory.db"
