#!/usr/bin/env python3
"""
Aegis Evaluator - Главный диспетчер (CLI)
Точка входа для всех режимов тестирования MLSecOps шлюза.
"""

import os
import sys
import argparse
import asyncio
import logging
import traceback

def setup_logging(verbose: bool):
    """Настройка централизованного логгера для всех модулей."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    # Подавляем спам от HTTP-клиентов, оставляем только важные логи
    logging.getLogger("httpx").setLevel(logging.WARNING)

async def run_all_modes(args):
    """Последовательный запуск всей пирамиды тестирования."""
    # Отложенные импорты для изоляции отказов
    from engines import static_engine, obfuscation_engine, redteam_engine
    
    print("\n" + "="*70)
    print(f"{'🚀 ЗАПУСК ПОЛНОГО ЦИКЛА АУДИТА (MODE: ALL)':^70}")
    print("="*70)

    print("\n" + "-"*30 + " ЭТАП 1: STATIC TEST " + "-"*30)
    await static_engine.run(args)

    print("\n" + "-"*30 + " ЭТАП 2: OBFUSCATION TEST " + "-"*30)
    await obfuscation_engine.run(args)

    print("\n" + "-"*30 + " ЭТАП 3: RED TEAMING " + "-"*30)
    await redteam_engine.run(args)

    print("\n" + "="*70)
    print(f"{'🏁 ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН':^70}")
    print("="*70)

def main():
    parser = argparse.ArgumentParser(
        description="Aegis Gateway Security Evaluator (PyRIT-based)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="URL шлюза Aegis")
    parser.add_argument("--model", default="gemini/gemini-3.1-pro-preview", help="Версия модели Gemini")
    parser.add_argument("-v", "--verbose", action="store_true", help="Включить подробный вывод логов")
    parser.add_argument(
        "--mode",
        choices=["static", "obfuscation", "redteam", "all"],
        default="static",
        help="Режим тестирования"
    )
    parser.add_argument("--limit", type=int, default=None, help="Лимит векторов")

    args = parser.parse_args()

    # Базовая валидация (Fail-fast)
    if "GEMINI_API_KEY" not in os.environ:
        print("❌ ОШИБКА: Переменная окружения GEMINI_API_KEY не задана.")
        sys.exit(1)

    setup_logging(args.verbose)

    # Диспетчеризация (Routing) с безопасной загрузкой модулей
    try:
        if args.mode == "static":
            from engines import static_engine
            asyncio.run(static_engine.run(args))
            
        elif args.mode == "obfuscation":
            from engines import obfuscation_engine
            asyncio.run(obfuscation_engine.run(args))
            
        elif args.mode == "redteam":
            from engines import redteam_engine
            asyncio.run(redteam_engine.run(args))
            
        elif args.mode == "all":
            asyncio.run(run_all_modes(args))
            
    except ImportError:
        print("\n❌ ДЕТАЛЬНАЯ ОШИБКА ИМПОРТА (Трассировка):")
        # Этот код покажет тебе ТОЧНЫЙ файл и строчку, где ломается импорт
        traceback.print_exc()
        print("\n💡 ПОДСКАЗКА: Если вы видите в ошибке 'core.scorers', зайдите в указанный файл")
        print("и исправьте импорт на 'core.scorers_static' или 'core.scorers_redteam'")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n🛑 Процесс прерван пользователем.")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n🚨 Ошибка выполнения: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()