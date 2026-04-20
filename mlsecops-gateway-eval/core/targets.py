import httpx
import json
from pyrit.models import PromptRequestResponse, PromptRequestPiece
from pyrit.prompt_target import PromptTarget, PromptChatTarget

class AegisTelemetryTarget(PromptTarget):
    """Шлюз Aegis: отправляет промпты на /check и собирает веса из /debug"""
    
    def __init__(self, endpoint_url: str, is_redteam: bool = False):
        super().__init__()
        self.endpoint_url = endpoint_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=10.0)
        self.is_redteam = is_redteam

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        if not prompt_request.request_pieces or not prompt_request.request_pieces[0].original_value:
            raise ValueError("Prompt text cannot be empty.")

    def is_json_response_supported(self) -> bool: return False
    def set_system_prompt(self, **kwargs) -> None: pass

    async def send_prompt_async(self, prompt_request: PromptRequestResponse) -> PromptRequestResponse:
        prompt_text = prompt_request.request_pieces[0].original_value
        
        # --- ВИЗУАЛИЗАЦИЯ 1: Отправка ---
        print(f"\n[📤 ЗАПРОС -> Aegis]: {prompt_text}")

        status, blocker = "ERROR", "None"
        debug_info = {}
        
        try:
            check_resp = await self.client.post(
                f"{self.endpoint_url}/check",
                content=prompt_text.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
            if check_resp.status_code == 200:
                status = "PASSED (200)"
            elif check_resp.status_code == 403:
                status = "BLOCKED (403)"
                blocker = "L1:HEURISTIC" if "Stage 1" in check_resp.text else "L2:ML_MODEL"
        except Exception as e:
            status = f"CONN_ERR: {str(e)[:20]}"

        try:
            debug_resp = await self.client.post(
                f"{self.endpoint_url}/debug",
                content=prompt_text.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
            if debug_resp.status_code == 200:
                debug_info = debug_resp.json()
        except Exception: pass

        # --- ВИЗУАЛИЗАЦИЯ 2: Ответ ---
        print(f"[📥 ОТВЕТ <- Aegis]: {status} | Эшелон: {blocker}")
        if debug_info:
            print(f"[📊 DEBUG DATA]: {json.dumps(debug_info, ensure_ascii=False)}")

        # Формируем сырой JSON (всегда доступен нашему скрипту-судье)
        response_data = {
            "aegis_verdict": status,
            "blocked_by": blocker,
            "debug_raw": debug_info
        }
        raw_response = json.dumps(response_data)

        # --- ИЗОЛЯЦИЯ: Формируем ответ для LLM в зависимости от режима ---
        if self.is_redteam:
            # Жесткий режим: Хакер видит только сухой текст
            display_text = "BLOCKED" if "403" in status else "PASSED"
        else:
            # Статический режим: Возвращаем JSON, чтобы избежать PARSE_ERROR
            display_text = raw_response

        return PromptRequestResponse(request_pieces=[PromptRequestPiece(
            role="assistant", 
            original_value=display_text,  # То, что читает LLM и движок
            converted_value=raw_response, # То, что читает наш Scorer (всегда JSON)
            conversation_id=prompt_request.request_pieces[0].conversation_id,
            prompt_target_identifier=self.get_identifier(),
        )])

    async def close(self):
        await self.client.aclose()


class GeminiNativeTarget(PromptChatTarget):
    """LLM-Судья/Атакующий: использует нативный API Google Gemini"""
    
    def __init__(self, model_name: str, api_key: str):
        super().__init__()
        self.model_name = model_name.split("/")[-1]
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        if not prompt_request.request_pieces: raise ValueError("Empty prompt.")

    def is_json_response_supported(self) -> bool: return False
    def set_system_prompt(self, **kwargs) -> None: pass

    async def send_prompt_async(self, prompt_request: PromptRequestResponse) -> PromptRequestResponse:
        full_prompt = "\n".join([p.original_value for p in prompt_request.request_pieces])
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": full_prompt}]}], "generationConfig": {"temperature": 0.0}}
        
        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            reply = resp.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            reply = f"JUDGE_ERROR: {str(e)}"
            
        return PromptRequestResponse(request_pieces=[PromptRequestPiece(
            role="assistant", original_value=reply, converted_value=reply,
            conversation_id=prompt_request.request_pieces[0].conversation_id,
            prompt_target_identifier=self.get_identifier()
        )])

    async def close(self): 
        await self.client.aclose()