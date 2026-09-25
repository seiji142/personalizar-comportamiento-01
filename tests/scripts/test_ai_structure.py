#!/usr/bin/env python3
"""
Suite de validacion automatica para la estructura .ai/ de OpenCode.
Carga los archivos .ai/ como contexto del sistema y valida comportamiento.
Compatible con cualquier endpoint OpenAI-compatible y modelos nativos OpenCode.

Uso:
  python test_ai_structure.py                          # API (Groq)
  python test_ai_structure.py --api openai/gpt-oss-20b  # API explicito
  python test_ai_structure.py --native opencode/big-pickle  # nativo OpenCode
  python test_ai_structure.py --from-json agent_answers.json  # desde JSON
  python test_ai_structure.py --api openai/gpt-oss-20b --only-failures  # solo fallos
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime

# Agregar tests/lib al path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from validation import validate_response
from opencode_cli import OPENCODE_CLI
from rate_limit import (
    BLOCKED_PREFIX,
    DEFAULT_BASE_WAIT_S,
    DEFAULT_MAX_RETRIES,
    EXIT_BLOCKED,
    blocked_message,
    compute_wait,
    parse_rate_limit,
    reclassify_file_tpd,
)

# Mapeo de modelos a variables de entorno en Verificacion-modelos-ai/.env
MODEL_KEY_MAP = {
    "openai/gpt-oss-20b": "GROQ_CUENTA_1",
    "qwen/qwen3.8-27b": "GROQ_CUENTA_2",
}


def load_verificacion_env():
    """Carga API keys desde Verificacion-modelos-ai/.env"""
    verificacion_dir = os.path.join(PROJECT_ROOT, "..", "Verificacion-modelos-ai")
    env_path = os.path.join(verificacion_dir, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


# Configuracion (variables de entorno)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY  = os.getenv("GROQ_API_KEY", "") or os.getenv("LLM_API_KEY", "")
LLM_MODEL    = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b")

# Estado del sondeo 429 TPD dentro de la corrida (tarea 15): una vez que la
# API pide la cuota diaria, el resto de tests no vuelve a llamarla
_api_state = {"blocked": False, "blocked_msg": None}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_PROJECT = os.path.normpath(os.getenv("TEST_PROJECT", os.path.join(PROJECT_ROOT, "..", "test-ai-config")))
AI_FOLDER    = os.getenv("AI_FOLDER", ".ai")
PROJECT_PATH = os.getenv("PROJECT_PATH", TEST_PROJECT)

TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

QUESTIONS_FILE = os.path.join(TESTS_DIR, "questions", "ai_structure_questions.json")

# Archivos obligatorios
REQUIRED_FILES = ["system.md", "rules.md", "context.md", "agents.md"]

# Orden de carga del system prompt (combinando todos los .ai/)
SYSTEM_PROMPT_FILES = ["system.md", "rules.md", "context.md", "agents.md"]


def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_ai_files():
    """Carga todos los archivos .ai/ y los combina en un system prompt."""
    ai_path = os.path.join(PROJECT_PATH, AI_FOLDER)
    parts = []
    for filename in SYSTEM_PROMPT_FILES:
        filepath = os.path.join(ai_path, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            parts.append(f"=== {filename} ===\n{content}")
    return "\n\n".join(parts)


def parse_opencode_response(output):
    text_parts = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text":
            part = event.get("part", {})
            text = part.get("text", "")
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def query_native(model_id, prompt, timeout=180):
    # 180s (antes 120): T4 registro 178.4s en el run del 23/09; el modelo
    # nativo tarda ~70s en promedio pero a veces supera 120s (tarea 14).
    cmd = [
        OPENCODE_CLI, "run",
        "--model", model_id,
        "--format", "json",
        "--dir", TEST_PROJECT,
        prompt
    ]
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["OPENCODE_SERVER_PASSWORD"] = ""
        env["OPENCODE_SERVER_USERNAME"] = ""
        result = subprocess.run(
            cmd, cwd=TEST_PROJECT,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env=env, timeout=timeout
        )
        content = parse_opencode_response(result.stdout)
        if not content and result.stderr.strip():
            content = f"[ERROR] {result.stderr.strip()[:500]}"
        return content
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR] {str(e)}"


def query_api(test_case, system_content, model_id=None):
    """Consulta a la API con retry para 429 (transitorio) y fail-fast TPD.

    - 429 transitorio: espera exacta (<=90s) o backoff 5/10/20s, 3 intentos.
    - 429 TPD diario: devuelve [BLOCKED_TPD] sin reintentar y marca el
      estado del modulo para cortar el resto de tests (tarea 15).
    """
    if _api_state["blocked"]:
        return _api_state["blocked_msg"]

    try:
        from openai import OpenAI, RateLimitError
    except ImportError as e:
        return f"[ERROR] {e}"
    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    model = model_id or LLM_MODEL
    last_error = None

    for retry in range(DEFAULT_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": test_case["prompt"]}
                ],
                temperature=0.1,
                max_tokens=600,
                timeout=30
            )
            return response.choices[0].message.content.lower()
        except RateLimitError as e:
            last_error = e
            info = parse_rate_limit(str(e))
            if info["is_tpd"]:
                _api_state["blocked"] = True
                _api_state["blocked_msg"] = blocked_message(info, model)
                print(_api_state["blocked_msg"])
                return _api_state["blocked_msg"]
            if retry < DEFAULT_MAX_RETRIES:
                wait = compute_wait(retry, info["retry_after_s"], DEFAULT_BASE_WAIT_S)
                print(f"[RATE LIMIT] Esperando {wait:g}s (intento {retry + 1}/{DEFAULT_MAX_RETRIES})...")
                time.sleep(wait)
            else:
                return f"[ERROR] {str(last_error)[:500]}"
        except Exception as e:
            return f"[ERROR] {str(e)[:500]}"
    return f"[ERROR] {str(last_error)[:500]}" if last_error else "[ERROR] No response"


def reply_status(reply):
    """Estado tecnico de una respuesta, o None si es valida para validar.

    Detecta el prefijo de forma case-insensitive: antes un 429 llegaba como
    "[ERROR] ..." en mayusculas, no casaba con "[error]" y el texto de la
    cuota agotada se contaba como FAIL de comportamiento (tarea 15).
    """
    low = (reply or "").lower()
    if low.startswith(BLOCKED_PREFIX.lower()):
        return "BLOCKED_TPD"
    if low.startswith("[error]") or low.startswith("[timeout]"):
        return "ERROR"
    return None


def run_test(test_case, system_content, native_mode=False, model_id=None):
    t0 = time.time()
    if native_mode:
        reply = query_native(model_id, test_case["prompt"])
    else:
        reply = query_api(test_case, system_content, model_id=model_id)

    status = reply_status(reply)
    if status:
        return {"status": status, "reply": reply, "error": reply,
                "time_seconds": round(time.time() - t0, 1)}

    passed, reasons = validate_response(reply.lower(), test_case)

    return {
        "status": "PASS" if passed else "FAIL",
        "reply": reply,
        "reply_preview": reply[:200] + "..." if len(reply) > 200 else reply,
        "reasons": reasons,
        "time_seconds": round(time.time() - t0, 1),
    }


def sanitize(text):
    """Sanitizar texto para consola Windows (cp1252)."""
    return text.encode('ascii', 'replace').decode('ascii')


def load_existing_report(report_path, fresh=False):
    """Carga el reporte previo. Si fresh=True, arranca vacio.
    Migra formato viejo {mode, results} a nuevo {models: {model: {results}}}."""
    if fresh or not os.path.exists(report_path):
        return {"models": {}}
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"models": {}}
    if "models" not in existing:
        old_model = existing.get("mode")
        old_results = existing.get("results", [])
        if old_model and old_results:
            existing = {"models": {old_model: {"results": old_results}}}
        else:
            existing = {"models": {}}
    existing.setdefault("models", {})
    return existing


def generate_report(results, mode_label="api", fresh=False):
    print("\n" + "=" * 60)
    print(f"REPORTE DE VALIDACION .ai/ ({mode_label}) |", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 60)

    pass_count = fail_count = error_count = blocked_count = 0
    for r in results:
        status_icon = {"PASS": "PASS", "ERROR": "ERROR",
                       "BLOCKED_TPD": "BLOCKED_TPD"}.get(r["status"], "FAIL")
        desc = sanitize(r['description'])
        print(f"  Test {r['id']} ({r['target']}) -> {status_icon} | {desc}")
        if r.get("reasons"):
            for reason in r["reasons"]:
                print(f"    - {sanitize(reason)}")
        if r["status"] == "ERROR":
            print(f"    - Error tecnico: {sanitize(str(r['error']))}")
        if r["status"] == "PASS":
            pass_count += 1
            preview = sanitize(r.get('reply_preview', r.get('reply', '')[:200]))
            print(f"    - Respuesta: {preview[:200]}")
        elif r["status"] == "FAIL":
            fail_count += 1
        elif r["status"] == "BLOCKED_TPD":
            blocked_count += 1
        else:
            error_count += 1

    print("=" * 60)
    print(f"Resultado: {pass_count} PASS | {fail_count} FAIL | "
          f"{error_count} ERROR | {blocked_count} BLOCKED_TPD")

    report_path = os.path.join(TESTS_DIR, "answers", "ai_validation_report.json")
    report = load_existing_report(report_path, fresh=fresh)

    report["models"][mode_label] = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
    }
    report["timestamp"] = datetime.now().isoformat()

    tmp_path = report_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, report_path)
    print(f"Reporte completo guardado en {report_path} ({len(report['models'])} modelo(s))")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Suite de validacion .ai/")
    parser.add_argument("--native", metavar="MODEL", help="Modelo nativo OpenCode (ej: opencode/big-pickle)")
    parser.add_argument("--api", metavar="MODEL", help="Modelo API via Groq (ej: openai/gpt-oss-20b)")
    parser.add_argument("--from-json", metavar="FILE", help="Leer respuestas desde JSON (ej: agent_answers.json)")
    parser.add_argument("--only-failures", action="store_true", help="Re-ejecutar solo tests que fallaron antes")
    parser.add_argument("--fresh", action="store_true",
                        help="Borra el reporte JSON existente antes de guardar (solo primera llamada)")
    args = parser.parse_args()

    # Verificar estructura
    ai_path = os.path.join(PROJECT_PATH, AI_FOLDER)
    missing = [f for f in REQUIRED_FILES if not os.path.exists(os.path.join(ai_path, f))]
    if missing:
        print(f"Faltan archivos obligatorios en {ai_path}/: {', '.join(missing)}")
        sys.exit(1)
    print("Estructura .ai/ verificada. Iniciando suite...")

    # Cargar system prompt desde los archivos .ai/
    system_content = load_ai_files()
    print(f"System prompt cargado ({len(system_content)} chars) desde {len(SYSTEM_PROMPT_FILES)} archivos.")

    tests = load_questions()

    # Si --only-failures, filtrar solo tests que fallaron en el reporte anterior
    if args.only_failures:
        report_path = os.path.join(TESTS_DIR, "answers", "ai_validation_report.json")
        if os.path.exists(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                failed_ids = set()
                # Formato nuevo: buscar en todos los modelos
                for model_name, model_data in report.get("models", {}).items():
                    for r in model_data.get("results", []):
                        # BLOCKED_TPD se re-ejecuta: con cuota pasa a PASS,
                        # sin cuota vuelve a BLOCKED_TPD sin gastar API
                        if r.get("status") in ("FAIL", "TIMEOUT", "ERROR", "BLOCKED_TPD"):
                            failed_ids.add(r["id"])
                # Fallback formato viejo
                if not failed_ids:
                    for r in report.get("results", []):
                        if r.get("status") in ("FAIL", "TIMEOUT", "ERROR", "BLOCKED_TPD"):
                            failed_ids.add(r["id"])
                if not failed_ids:
                    print("No hay fallos previos. Nada que re-ejecutar.")
                    sys.exit(0)
                tests = [t for t in tests if t["id"] in failed_ids]
                print(f"Filtrado: {len(tests)} tests con fallos previos")
            except Exception as e:
                print(f"WARN: No se pudo leer reporte anterior: {e}")
        else:
            print("No hay reporte anterior. Ejecutando todos los tests.")

    # Modo desde JSON
    if args.from_json:
        json_path = os.path.join(TESTS_DIR, "answers", args.from_json) if not os.path.isabs(args.from_json) else args.from_json
        if not os.path.exists(json_path):
            print(f"ERROR: No se encontro {json_path}")
            sys.exit(1)
        with open(json_path, "r", encoding="utf-8") as f:
            answers_data = json.load(f)
        # Soporta formato [{id, response}] o {id: response}
        if isinstance(answers_data, list):
            answers_by_id = {a["id"]: a["response"] for a in answers_data}
        else:
            answers_by_id = answers_data

        mode_label = f"json:{os.path.basename(args.from_json)}"
        results = []
        for test in tests:
            tid = test["id"]
            if tid not in answers_by_id:
                print(f"WARNING: Sin respuesta para Test {tid}, saltando...")
                continue
            reply = answers_by_id[tid].lower()
            status = reply_status(reply)
            if status:
                result = {"status": status, "reply": reply, "error": reply}
            else:
                passed, reasons = validate_response(reply, test)
                result = {"status": "PASS" if passed else "FAIL", "reply": reply,
                          "reply_preview": reply[:200] + "..." if len(reply) > 200 else reply,
                          "reasons": reasons}
            result.update({"id": test["id"], "target": test["target"],
                           "description": test["description"]})
            results.append(result)

    # Modo nativo
    elif args.native:
        if not os.path.exists(OPENCODE_CLI):
            print(f"ERROR: No se encuentra opencode CLI en {OPENCODE_CLI}")
            sys.exit(1)

        mode_label = args.native
        results = []
        for test in tests:
            print(f"Ejecutando Test {test['id']} ({test['target']})...")
            res = run_test(test, system_content, native_mode=True,
                           model_id=args.native)
            res.update({"id": test["id"], "target": test["target"],
                        "description": test["description"]})
            results.append(res)
            if res["status"] == "BLOCKED_TPD":
                print("Cortando resto de tests: cuota diaria (TPD) agotada.")
                break
    # Modo API (default o explicito)
    else:
        # Cargar API keys desde Verificacion-modelos-ai
        load_verificacion_env()
        # Mapear GROQ_CUENTA_X a GROQ_API_KEY para el modelo seleccionado
        model_id = args.api or os.getenv("LLM_MODEL", "qwen/qwen3.8-27b")
        env_var = MODEL_KEY_MAP.get(model_id)
        if env_var and os.getenv(env_var):
            os.environ["GROQ_API_KEY"] = os.getenv(env_var)
            os.environ["LLM_API_KEY"] = os.getenv(env_var)
        mode_label = f"api/{model_id}"
        results = []
        for test in tests:
            print(f"Ejecutando Test {test['id']} ({test['target']})...")
            res = run_test(test, system_content, model_id=args.api)
            res.update({"id": test["id"], "target": test["target"],
                        "description": test["description"]})
            results.append(res)
            if res["status"] == "BLOCKED_TPD":
                print("Cortando resto de tests: cuota diaria (TPD) agotada.")
                break

    generate_report(results, mode_label, fresh=args.fresh)

    # Cierre 429 TPD (tarea 15): reclasificar casos que quedaron como
    # ERROR/FAIL con evidencia textual de cuota diaria agotada
    report_file = os.path.join(TESTS_DIR, "answers", "ai_validation_report.json")
    blocked_count = sum(1 for r in results if r["status"] == "BLOCKED_TPD")
    if blocked_count:
        changed = reclassify_file_tpd(report_file, model_labels={mode_label})
        print(f"[TPD] {changed} caso(s) con evidencia 429-TPD -> BLOCKED_TPD")
        sys.exit(EXIT_BLOCKED)


if __name__ == "__main__":
    main()
