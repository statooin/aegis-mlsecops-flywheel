


mlsecops-gateway-pg/
├── Dockerfile              # Образ-лаборатория
├── requirements.txt        # Манифест зависимостей
├── config.py               # Централизованные настройки (URLs, Timeouts, Logs)
├── main.py                 # CLI-диспетчер (Menu)
│
├── core/                   # "Стабильное ядро"
│   ├── targets.py          # Логика общения с Aegis и Gemini
│   ├── scorers.py          # Логика оценки (AegisBinaryScorer)
│   └── converters.py       # Кастомные методы обфускации (если нужны)
│
├── engines/                # "Двигатели тестов"
│   ├── static_engine.py    # Режим 1 (Static)
│   ├── obfuscation_engine.py # Режим 2 (Static + Converters)
│   └── redteam_engine.py   # Режим 3 (Dynamic Attack)
│
└── data/                   # "Топливо и результаты"
    ├── prompts/            # Папка с .json/.yaml файлами атак
    │   ├── jailbreaks.json
    │   └── benign.json
    ├── loader.py           # Скрипт загрузки данных из файлов
    └── pyrit_memory.db     # DuckDB (создается автоматически)
