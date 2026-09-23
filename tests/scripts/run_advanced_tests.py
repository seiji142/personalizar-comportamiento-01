#!/usr/bin/env python3
"""
Runner de la suite avanzada de tests (jailbreak, estilo de codigo,
factualidad, estructura, roles, memoria, configuracion y jerarquia).

Uso:
  python run_advanced_tests.py                 # todos los modelos nativos, todos los casos
  python run_advanced_tests.py <modelo>        # filtra modelos nativos por nombre
  python run_advanced_tests.py --api <model>   # contra API (usa GROQ_API_KEY)
  python run_advanced_tests.py --api <model> --only-failures
                                               # re-ejecuta solo los tests que fallaron antes
  python run_advanced_tests.py --only B3       # re-ejecuta solo los IDs indicados (coma-separados)

Ejecutar desde la raiz del proyecto (hereda .ai/ via opencode.json).
"""

import json
import os
import sys
import time
import requests
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_PROJECT = os.path.normpath(os.getenv("TEST_PROJECT", os.path.join(PROJECT_ROOT, "..", "test-ai-config")))
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")
QUESTIONS_FILE = os.path.join(TESTS_DIR, "questions", "advanced_questions.json")
REPORT_FILE = os.path.join(TESTS_DIR, "answers", "advanced_validation_report.json")

# Cargar librerias desde tests/lib
sys.path.insert(0, os.path.join(TESTS_DIR, "lib"))
from advanced_validators import validate_advanced
from model_runner import create_runner
from opencode_cli import OPENCODE_CLI

# Modelos nativos contratados (misma lista que run_opencode_models.py)
NATIVE_MODELS = [
    "opencode/big-pickle",
    "opencode/mimo-v2.6-flash-free",
]


def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def check_brain_ai_health(timeout=5):
    """Verifica que brain-ai-01 este corriendo en localhost:8000 (opcional)."""
    try:
        r = requests.get("http://127.0.0.1:8000/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


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
        print(f"[WARN] No se encontro {env_path}")
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
    print(f"[OK] Keys cargadas desde {env_path}")


def run_cases_for_model(model_label, runner, questions, report_path=None, all_results=None):
    """Ejecuta tests y guarda incrementalmente después de cada uno."""
    per_case = {}
    for case in questions:
        cid = case["id"]
        print(f"   [{cid}] {case['name']}... ", end="", flush=True)
        t0 = time.time()
        result = runner.query(case["prompt"])

        text = result.get("text", "")
        error = result.get("error")
        tool_calls = result.get("tool_calls", [])
        memory_used = result.get("memory_used", False)
        files_read = result.get("files_read", [])
        mcp_available = result.get("mcp_available")
        mcp_error = result.get("mcp_error")

        if error:
            if "TIMEOUT" in error:
                status = "TIMEOUT"
                reasons = ["timeout"]
            else:
                status = "ERROR"
                reasons = [error]
        else:
            passed, reasons = validate_advanced(text, case, tool_calls=tool_calls, memory_used=memory_used, files_read=files_read)
            status = "PASS" if passed else "FAIL"

        elapsed = round(time.time() - t0, 1)
        per_case[cid] = {
            "name": case["name"],
            "category": case["category"],
            "status": status,
            "time_seconds": elapsed,
            "reasons": reasons,
            "response_preview": text[:200] + "..." if len(text) > 200 else text,
            "response_full": text,
            "tool_calls": tool_calls,
            "memory_used": memory_used,
            "mcp_available": mcp_available,
            "mcp_error": mcp_error,
            "tokens_used": result.get("tokens_used", 0),
        }
        print(f"{status} ({elapsed}s)")
        for r in reasons[:6]:
            print(f"          - {r}")
        
        # Guardado incremental después de cada test
        if report_path and all_results is not None:
            all_results[model_label] = per_case
            save_incremental(report_path, all_results)
        
        time.sleep(1)
    return per_case


def print_summary(all_results, questions):
    print("\n" + "=" * 90)
    print(f"VALIDACION AVANZADA .ai/  | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 90)

    headers = [q["id"] for q in questions]
    print(f" {'Modelo':<28} " + " ".join(f"{h:>5}" for h in headers) + "  SCORE")
    print("-" * 90)

    total_cases = len(headers)
    for model, cases in all_results.items():
        cells = []
        passed = 0
        for cid in headers:
            st = cases.get(cid, {}).get("status", "-")
            short = {"PASS": "P", "FAIL": "F", "TIMEOUT": "T", "ERROR": "E"}.get(st, "-")
            cells.append(f"{short:>5}")
            if st == "PASS":
                passed += 1
        print(f" {model:<28} " + " ".join(cells) + f"  {passed}/{total_cases}")

    print("=" * 90)


def merge_models_report(existing, new_results):
    """Fusiona resultados nuevos en un reporte existente (merge por test ID).

    - Con `--only-failures` (o cualquier corrida parcial) conserva los tests
      que NO se re-ejecutaron y solo reemplaza los que SI corrieron.
    - No toca modelos que no aparecen en `new_results`.
    """
    existing.setdefault("models", {})
    for label, cases in new_results.items():
        existing_model = existing["models"].get(label, {})
        existing_model.update(cases)
        existing["models"][label] = existing_model
    return existing


def save_incremental(report_path, all_results):
    """Guarda el reporte incrementalmente después de cada test.

    Si el archivo existe, Fusiona los nuevos modelos en los existentes
    (formato models, no runs). Merge por test ID: no pisa tests que no
    se re-ejecutaron (tarea #12).
    """
    try:
        # Leer JSON existente si existe
        existing = {}
        if os.path.exists(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = {}

        # Fusionar nuevos modelos en existing["models"] (merge por test ID)
        existing = merge_models_report(existing, all_results)

        # Actualizar metadata
        existing["timestamp"] = datetime.now().isoformat()
        existing["type"] = "advanced_validation"

        # Guardar
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"WARN: No se pudo guardar incrementalmente: {e}")


def load_previous_failures():
    """Carga IDs de tests que fallaron en el reporte anterior."""
    if not os.path.exists(REPORT_FILE):
        return None
    try:
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            report = json.load(f)
        failed_ids = set()
        for model_label, cases in report.get("models", {}).items():
            for cid, result in cases.items():
                if result.get("status") in ("FAIL", "TIMEOUT", "ERROR"):
                    failed_ids.add(cid)
        return failed_ids if failed_ids else None
    except Exception as e:
        print(f"WARN: No se pudo leer reporte anterior: {e}")
        return None


def main():
    os.system("")

    # Parsear argumentos
    args = sys.argv[1:]
    model_filter = None
    api = False
    api_model = None
    only_failures = False
    fresh = False
    only_ids = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--api" and i + 1 < len(args):
            api = True
            api_model = args[i + 1]
            i += 2
        elif a == "--only-failures":
            only_failures = True
            i += 1
        elif a == "--fresh":
            fresh = True
            i += 1
        elif a == "--only" and i + 1 < len(args):
            only_ids = {x.strip() for x in args[i + 1].split(",") if x.strip()}
            i += 2
        else:
            model_filter = a
            i += 1

    questions = load_questions()
    print(f"Runner avanzado ({len(questions)} casos)")

    # Solo borrar el JSON si se pasa --fresh (limpieza explícita)
    if fresh and os.path.exists(REPORT_FILE):
        os.remove(REPORT_FILE)
        print(f"[OK] Reporte anterior eliminado (--fresh): {REPORT_FILE}")

    # Si --only, filtrar solo los IDs indicados (ej: --only B3)
    if only_ids:
        questions = [q for q in questions if q["id"] in only_ids]
        if not questions:
            print(f"Ningun test coincide con --only {sorted(only_ids)}")
            sys.exit(1)
        print(f"Filtrado: {len(questions)} tests por --only")

    # Si --only-failures, filtrar solo tests que fallaron en el reporte anterior
    failed_ids = None
    if only_failures:
        failed_ids = load_previous_failures()
        if not failed_ids:
            print("No hay fallos previos. Nada que re-ejecutar.")
            sys.exit(0)
        questions = [q for q in questions if q["id"] in failed_ids]
        print(f"Filtrado: {len(questions)} tests con fallos previos")

    models_config = []

    if api:
        if api_model:
            models_config.append({"model": f"api/{api_model}", "native": False, "id": api_model})
        else:
            print("Uso: --api <model_id>")
            sys.exit(1)
        # Cargar API keys desde Verificacion-modelos-ai
        load_verificacion_env()
        # Mapear GROQ_CUENTA_X a GROQ_API_KEY para el modelo seleccionado
        env_var = MODEL_KEY_MAP.get(api_model)
        if env_var and os.getenv(env_var):
            os.environ["GROQ_API_KEY"] = os.getenv(env_var)
            os.environ["LLM_API_KEY"] = os.getenv(env_var)
        if not os.getenv("GROQ_API_KEY") and not os.getenv("LLM_API_KEY"):
            print("ERROR: No se encontro GROQ_API_KEY o LLM_API_KEY")
            sys.exit(1)
        print(f"API keys OK (modelo: {api_model})\n")
    else:
        native = NATIVE_MODELS
        if model_filter:
            native = [m for m in native if model_filter.lower() in m.lower()]
        if not native:
            print(f"No se encontraron modelos nativos que coincidan: {model_filter}")
            sys.exit(1)
        models_config.extend({"model": m, "native": True, "id": m} for m in native)

    # Verificar CLI solo si hay modelos nativos
    has_native = any(c["native"] for c in models_config)
    if has_native:
        if not os.path.exists(OPENCODE_CLI):
            print(f"ERROR: No se encuentra opencode CLI en {OPENCODE_CLI}")
            sys.exit(1)

    all_results = {}
    report_path = os.path.join(PROJECT_ROOT, REPORT_FILE)
    
    for cfg in models_config:
        label = cfg["model"]
        print(f"\n[{label}]")
        if cfg["native"]:
            runner = create_runner(cfg["id"], mode="native")
        else:
            runner = create_runner(cfg["id"], mode="api")

        cases = run_cases_for_model(
            label, runner, questions,
            report_path=report_path,
            all_results=all_results
        )
        all_results[label] = cases

    print_summary(all_results, questions)

    # El guardado final ya se hace incrementalmente, pero guardamos una última vez
    # para asegurar que todo esté sincronizado
    save_incremental(report_path, all_results)
    print(f"\nReporte guardado en {report_path}")


if __name__ == "__main__":
    main()
