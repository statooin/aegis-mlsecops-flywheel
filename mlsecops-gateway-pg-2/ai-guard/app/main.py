import base64
import json
from fastapi import FastAPI, Request, Response, HTTPException

# Импортируем наши "кубики" архитектуры
from app.config import settings, logger
from app.engine_waf import analyze_text
from app.engine_ml import ml_engine

# Инициализация приложения
app = FastAPI(title="Aegis AI Gateway - Orchestrator")

@app.get("/health")
def health_check():
    """
    SRE Probe (Liveness/Readiness).
    Вместо жесткого падения (503) при отказе ML, мы отдаем 200 с меткой 'degraded'.
    Это позволяет K8s/Envoy продолжать слать трафик на наш безотказный L1 WAF.
    """
    ml_status = "ready" if ml_engine.is_ready() else "degraded"
    return {
        "status": "ok",
        "ml_engine": ml_status,
        "threshold": settings.THRESHOLD,
        "model": settings.MODEL_NAME
    }

@app.post("/debug")
async def debug_endpoint(request: Request):
    """Эндпоинт для скрипта ai_debug.sh. Возвращает сырые скоры."""
    raw_body = await request.body()
    text = raw_body.decode("utf-8", errors="replace") if raw_body else ""
    
    if not text:
        return {"error": "empty text"}
        
    ml_result = ml_engine.analyze(text) if ml_engine.is_ready() else None
    
    return {
        "text": text,
        "raw_scores": {
            "index_0": round(ml_result["benign_score"], 4) if ml_result else 0.0,
            "index_1": round(ml_result["malicious_score"], 4) if ml_result else 0.0,
        }
    }

@app.post("/check")
async def check_prompt(request: Request):
    """Главный шлюз. Вызывается Envoy через ext_authz."""
    
    # --- 0. ИЗВЛЕЧЕНИЕ ПЕЙЛОАДА ---
    encoded_body = request.headers.get("x-envoy-auth-partial-body", "")
    if encoded_body:
        try:
            text = base64.b64decode(encoded_body).decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f'{{"event": "envoy_decode_error", "error": "{str(e)}"}}')
            text = ""
    else:
        raw_body = await request.body()
        text = raw_body.decode("utf-8", errors="replace") if raw_body else ""

    if not text.strip():
        return Response(status_code=200)

    # --- 1. STAGE 1: WAF (Сверхбыстрая эвристика) ---
    waf_result = analyze_text(text)
    
    if waf_result["is_blocked"]:
        logger.warning(json.dumps({
            "event": "stage1_waf_block",
            "categories": waf_result["categories"],
            "incident_id": waf_result["payload_hash"]
        }))
        raise HTTPException(
            status_code=403, 
            detail={
                "error": "Access denied by Aegis Guard (Stage 1)",
                "categories": waf_result["categories"],
                "incident_id": waf_result["payload_hash"]
            }
        )

    # --- 2. STAGE 2: ML SEMANTIC CHECK (Тяжелая проверка) ---
    if ml_engine.is_ready():
        ml_result = ml_engine.analyze(text)
        
        if ml_result:
            if ml_result["malicious_score"] > settings.THRESHOLD:
                logger.warning(json.dumps({
                    "event": "stage2_ml_block",
                    "score": round(ml_result["malicious_score"], 3),
                    "incident_id": waf_result["payload_hash"]
                }))
                raise HTTPException(status_code=403, detail="Access denied by Aegis Guard (Stage 2)")
            
            # Идеальный запрос прошел обе стадии
            logger.info(json.dumps({
                "event": "request_passed",
                "ml_score": round(ml_result["malicious_score"], 3)
            }))
            return Response(status_code=200)

    # --- 3. FAIL-SAFE ---
    # Срабатывает только если ML-движок упал в рантайме.
    logger.error(json.dumps({
        "event": "ml_offline_bypass", 
        "message": "Permitted by Stage 1 WAF",
        "incident_id": waf_result["payload_hash"]
    }))
    
    return Response(status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)