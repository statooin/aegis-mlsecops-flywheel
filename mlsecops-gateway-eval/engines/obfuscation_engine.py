import json
import os
from pyrit.common import initialize_pyrit
from pyrit.orchestrator import PromptSendingOrchestrator
from pyrit.prompt_converter import Base64Converter

from core.targets import AegisTelemetryTarget
# SRE FIX: Используем статический скорер для теста обфускации
from core.scorers_static import AegisStaticScorer as AegisBinaryScorer
from data.datasets import TEST_PROMPTS

async def run(args):
    """Режим 2: Тест эшелона L1 на устойчивость к обфускации (Base64)."""
    initialize_pyrit(memory_db_type="DuckDB")

    aegis_target = AegisTelemetryTarget(endpoint_url=args.url)
    base64_converter = Base64Converter()

    orchestrator = PromptSendingOrchestrator(
        objective_target=aegis_target,
        scorers=[AegisBinaryScorer()],
        prompt_converters=[base64_converter],
        verbose=args.verbose
    )

    # Применяем лимит бюджета
    prompts_to_run = TEST_PROMPTS[:args.limit] if args.limit else TEST_PROMPTS

    print(f"\n🕵️ ЗАПУСК OBFUSCATION ТЕСТА (Base64 Encodings) на {len(prompts_to_run)} векторов...")
    responses = await orchestrator.send_prompts_async(prompt_list=prompts_to_run)

    print("\n" + "="*95)
    print(f"{'📊 OBFUSCATION REPORT: L1 HEURISTIC RESILIENCE':^95}")
    print("="*95)

    for prompt, resp in zip(prompts_to_run, responses):
        try:
            res_data = json.loads(resp.request_pieces[0].original_value)
            verdict = res_data.get("aegis_verdict", "ERROR")
        except:
            verdict = "PARSE_ERROR"

        is_blocked = "BLOCKED" in verdict
        icon = "✅ [SECURE]" if is_blocked else "🔥 [BYPASS]"
        
        # SRE Исключение: шутки и безобидные промпты пропускаем
        if not is_blocked and ("france" in prompt.lower() or "joke" in prompt.lower()):
            icon = "✅ [NORMAL]"

        print(f"\n{icon} Оригинал: {prompt[:50]}...")
        print(f"          Вердикт: {verdict:<15} | Блокировщик: {res_data.get('blocked_by', 'None')}")

    await aegis_target.close()
    print("\n✅ Режим Obfuscation Test завершен.")