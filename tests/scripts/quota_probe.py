#!/usr/bin/env python3
"""Sondeo de cuota Groq por cuenta (paso 0 del plan 429 TPD).

Envia 1 query minima por cuenta para saber ANTES de correr la suite si la
cuota diaria (TPD) esta agotada. Escribe tests/answers/quota_status.json
que consumen suite_runner (gate api_disponible) y run_all_tests.py
(cuenta bloqueada -> correr solo nativos).

Uso:
  python tests/scripts/quota_probe.py            # sondeo de ambas cuentas
  python tests/scripts/quota_probe.py --reclassify
        # ademas reclasifica en los reportes los ERROR/FAIL con evidencia
        # de 429-TPD a BLOCKED_TPD (decision 2 de la tarea 15)

Nunca imprime valores de API keys.
"""

import json
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TESTS_LIB = os.path.join(PROJECT_ROOT, "tests", "lib")
sys.path.insert(0, TESTS_LIB)

from rate_limit import (  # noqa: E402
    QUOTA_STATUS_FILENAME,
    classify_probe,
    parse_rate_limit,
    reclassify_file_tpd,
)

ANSWERS_DIR = os.path.join(PROJECT_ROOT, "tests", "answers")
QUOTA_PATH = os.path.join(ANSWERS_DIR, QUOTA_STATUS_FILENAME)
ENV_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "Verificacion-modelos-ai", ".env"))

# Misma tabla que run_all_tests.py / run_advanced_tests.py
MODEL_KEY_MAP = {
    "openai/gpt-oss-20b": "GROQ_CUENTA_1",
    "qwen/qwen3.8-27b": "GROQ_CUENTA_2",
}

PROBE_TIMEOUT_S = 30


def load_verificacion_env():
    """Carga API keys desde Verificacion-modelos-ai/.env (sin imprimirlas)."""
    if not os.path.exists(ENV_PATH):
        print(f"[WARN] No se encontro {ENV_PATH}")
        return
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def probe_account(model_id, api_key):
    """1 query minima a la cuenta. Retorna dict con status/used/limit."""
    try:
        from openai import OpenAI
    except ImportError:
        return {"model": model_id, "status": "ERROR",
                "detail": "openai package not installed"}

    result = {"model": model_id, "status": None, "used": None, "limit": None,
              "retry_after_s": None, "detail": "", "rate_limit_headers": {}}
    try:
        client = OpenAI(
            base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=api_key,
            timeout=PROBE_TIMEOUT_S,
        )
        resp = client.chat.completions.with_raw_response.create(
            model=model_id,
            messages=[{"role": "user", "content": "ping"}],
            temperature=0.1,
            max_tokens=8,
        )
        result["status"] = "OK"
        result["detail"] = "query minima exitosa"
        # Headers x-ratelimit-*: ventana corta (RPM/TPM). El consumo DIARIO
        # (TPD) solo llega en los mensajes 429 (Used/Limit) — paso 5
        try:
            headers = {k: v for k, v in dict(resp.headers).items()
                       if k.lower().startswith("x-ratelimit")}
        except Exception:
            headers = {}
        result["rate_limit_headers"] = headers
    except Exception as e:
        message = str(e)
        info = parse_rate_limit(message)
        result["status"] = classify_probe(False, message)
        result["used"] = info["used"]
        result["limit"] = info["limit"]
        result["retry_after_s"] = info["retry_after_s"]
        result["detail"] = message[:500]
    return result


def run_probe():
    """Sondea todas las cuentas de MODEL_KEY_MAP y escribe quota_status.json.

    Returns:
        dict: {accounts: {GROQ_CUENTA_N: {...}}}
    """
    load_verificacion_env()
    accounts = {}
    for model_id, account in MODEL_KEY_MAP.items():
        api_key = os.getenv(account, "")
        if not api_key:
            accounts[account] = {"model": model_id, "status": "ERROR",
                                 "detail": f"{account} no encontrada en .env"}
            continue
        res = probe_account(model_id, api_key)
        accounts[account] = res
        extra = ""
        if res.get("used") is not None:
            extra = f" | Used {res['used']}/{res.get('limit')}"
        if res.get("retry_after_s") is not None:
            extra += f" | reintentar en {int(round(res['retry_after_s']))}s"
        headers = res.get("rate_limit_headers") or {}
        if headers:
            extra += " | " + ", ".join(f"{k}={v}" for k, v in sorted(headers.items()))
        print(f"[{account}] {model_id}: {res['status']}{extra}")

    payload = {"timestamp": datetime.now().isoformat(), "accounts": accounts}
    os.makedirs(ANSWERS_DIR, exist_ok=True)
    tmp = QUOTA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, QUOTA_PATH)
    print(f"Quota status guardado en {QUOTA_PATH}")
    return payload


def main():
    args = sys.argv[1:]
    payload = run_probe()

    if "--reclassify" in args:
        blocked = [acct for acct, res in payload["accounts"].items()
                   if res.get("status") == "BLOCKED_TPD"]
        if not blocked:
            print("[OK] Sin cuentas BLOCKED_TPD: nada que reclasificar.")
        else:
            label_by_account = {v: f"api/{k}" for k, v in MODEL_KEY_MAP.items()}
            labels = [label_by_account[a] for a in blocked if a in label_by_account]
            for name in ("advanced_validation_report.json", "ai_validation_report.json"):
                path = os.path.join(ANSWERS_DIR, name)
                changed = reclassify_file_tpd(path, model_labels=labels)
                print(f"[TPD] {name}: {changed} caso(s) reclasificados a BLOCKED_TPD")

    statuses = [res.get("status") for res in payload["accounts"].values()]
    # Exit 0 siempre que el sondeo se completo (es informativo por diseno:
    # quien decide es suite_runner/run_all_tests leyendo quota_status.json)
    sys.exit(0 if statuses else 1)


if __name__ == "__main__":
    main()
