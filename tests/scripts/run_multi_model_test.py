#!/usr/bin/env python3
"""
Runner multi-modelo para validacion de estructura .ai/.
Ejecuta test_ai_structure.py contra multiples modelos y consolida resultados.

Lee API keys de Verificacion-modelos-ai/.env (centralizado).
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime

# Ruta absoluta al proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_PROJECT = os.getenv("TEST_PROJECT", os.path.join(PROJECT_ROOT, "..", "test-ai-config"))
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")
VERIFICACION_DIR = os.path.join(PROJECT_ROOT, "..", "Verificacion-modelos-ai")
TEST_SCRIPT = os.path.join(TESTS_DIR, "scripts", "test_ai_structure.py")
REPORT_FILE = os.path.join(TESTS_DIR, "answers", "ai_validation_report.json")
MULTI_REPORT = os.path.join(TESTS_DIR, "answers", "multi_model_validation_report.json")

# Mapeo de modelos a variables de entorno en Verificacion-modelos-ai/.env
MODEL_KEY_MAP = {
    "openai/gpt-oss-20b": "GROQ_CUENTA_1",
    "qwen/qwen3.8-27b": "GROQ_CUENTA_2",
}


def load_verificacion_env():
    """Carga variables de Verificacion-modelos-ai/.env"""
    env_path = os.path.join(VERIFICACION_DIR, ".env")
    if not os.path.exists(env_path):
        print(f"[ERROR] No se encontro {env_path}")
        sys.exit(1)
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
    print(f"[OK] Keys cargadas desde {env_path}")


def get_api_key_for_model(model_name):
    """Retorna la API key correspondiente al modelo"""
    env_var = MODEL_KEY_MAP.get(model_name)
    if not env_var:
        raise ValueError(f"No hay key configurada para el modelo: {model_name}")
    key = os.getenv(env_var)
    if not key:
        raise ValueError(f"Variable {env_var} no encontrada en .env")
    return key


# Cargar keys desde Verificacion-modelos-ai
load_verificacion_env()

# Modelos activos (fuente: Verificacion-modelos-ai/models_list.json)
MODELS = [
    {
        "alias": "groq/gpt-oss-20b",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_CUENTA_1",
        "model_id": "openai/gpt-oss-20b"
    },
    {
        "alias": "groq/qwen3.8-27b",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_CUENTA_2",
        "model_id": "qwen/qwen3.8-27b"
    },
]


def run_single_test(config):
    """Ejecuta test_ai_structure.py para un modelo y retorna resultados."""
    env = os.environ.copy()
    env["LLM_BASE_URL"] = config["base_url"]
    env["LLM_API_KEY"] = os.environ.get(config["api_key_env"], "")
    env["LLM_MODEL"] = config["model_id"]
    env["AI_FOLDER"] = ".ai"
    env["PROJECT_PATH"] = "."
    env["PYTHONIOENCODING"] = "utf-8"

    if not env["LLM_API_KEY"]:
        print(f"  [SKIP] {config['alias']}: Variable {config['api_key_env']} no configurada")
        return {
            "alias": config["alias"],
            "model": config["model_id"],
            "status": "SKIP",
            "results": [],
            "tests_pass": 0,
            "tests_total": 5,
            "error": f"Variable {config['api_key_env']} no encontrada"
        }

    print(f"  Ejecutando {config['alias']} ({config['model_id']})...", flush=True)

    try:
        start = time.time()
        result = subprocess.run(
            [sys.executable, TEST_SCRIPT],
            capture_output=True, text=True, timeout=120,
            env=env, cwd=TEST_PROJECT
        )
        elapsed = round(time.time() - start, 1)

        # Leer reporte generado (se genera en PROJECT_ROOT)
        report_path = os.path.join(PROJECT_ROOT, REPORT_FILE)
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
        else:
            report_data = {"models": {}}

        # Extraer resultados (formato nuevo multi-modelo, fallback a viejo)
        if "models" in report_data:
            all_results = []
            for model_data in report_data.get("models", {}).values():
                all_results.extend(model_data.get("results", []))
            results_list = all_results
        else:
            results_list = report_data.get("results", [])

        # Convertir lista a dict por id
        per_test = {}
        for r in results_list:
            tid = r.get("id", 0)
            ttarget = r.get("target", "")
            per_test[tid] = {
                "target": ttarget,
                "status": r.get("status", "UNKNOWN"),
                "reasons": r.get("reasons", [])
            }

        tests_pass = sum(1 for r in results_list if r.get("status") == "PASS")
        tests_total = len(results_list) if results_list else 5

        # Determinar status: si tenemos resultados, usamos esos aunque exit code != 0
        if tests_pass == tests_total and tests_total > 0:
            status = "PASS"
        elif tests_total > 0:
            status = "PARTIAL"
        elif result.returncode != 0:
            status = "ERROR"
        else:
            status = "UNKNOWN"

        error_msg = None
        if result.returncode != 0:
            stderr = result.stderr[:500] if result.stderr else ""
            error_msg = f"Exit code {result.returncode}: {stderr}"
        elif result.stdout and "ERROR" in result.stdout:
            # Buscar errores en stdout
            for line in result.stdout.split("\n"):
                if "Error" in line or "error" in line or "Traceback" in line:
                    error_msg = line[:200]
                    break

        return {
            "alias": config["alias"],
            "model": config["model_id"],
            "status": status,
            "results": per_test,
            "tests_pass": tests_pass,
            "tests_total": tests_total,
            "time_seconds": elapsed,
            "error": error_msg
        }

    except subprocess.TimeoutExpired:
        return {
            "alias": config["alias"],
            "model": config["model_id"],
            "status": "TIMEOUT",
            "results": {},
            "tests_pass": 0,
            "tests_total": 5,
            "error": "Timeout 120s excedido"
        }
    except Exception as e:
        return {
            "alias": config["alias"],
            "model": config["model_id"],
            "status": "ERROR",
            "results": {},
            "tests_pass": 0,
            "tests_total": 5,
            "error": str(e)
        }


def print_summary(all_results):
    """Imprime tabla comparativa."""
    print("\n" + "=" * 80)
    print("VALIDACION MULTI-MODELO .ai/  |", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 80)
    print(f" {'Modelo':<32} {'T1':<6} {'T2':<6} {'T3':<6} {'T4':<6} {'T5':<6} {'PASS':<6} {'TIEMPO':<8}")
    print("-" * 80)

    total_pass = 0
    total_full = 0

    for r in all_results:
        alias = r["alias"]
        status = r["status"]

        if status == "SKIP":
            print(f" {alias:<32} {'SKIP':<6} {'':<6} {'':<6} {'':<6} {'':<6} {'0/5':<6} {'-':<8}")
            continue

        tcount = r.get("tests_pass", 0)
        ttotal = r.get("tests_total", 5)
        elapsed = r.get("time_seconds", 0)
        et = f"{elapsed}s" if elapsed else "ERR"

        # Resultados por test
        per_test = r.get("results", {})
        t1 = per_test.get(1, {}).get("status", "-")
        t2 = per_test.get(2, {}).get("status", "-")
        t3 = per_test.get(3, {}).get("status", "-")
        t4 = per_test.get(4, {}).get("status", "-")
        t5 = per_test.get(5, {}).get("status", "-")

        print(f" {alias:<32} {t1:<6} {t2:<6} {t3:<6} {t4:<6} {t5:<6} {tcount}/{ttotal:<5} {et:<8}")

        if status == "PASS":
            total_full += 1

        total_pass += 1

    print("-" * 80)
    all_count = len([r for r in all_results if r["status"] != "SKIP"])
    error_count = len([r for r in all_results if r["status"] in ("ERROR", "TIMEOUT")])
    print(f" MODELOS EJECUTADOS: {all_count}  |  PASS COMPLETO: {total_full}  |  ERRORES: {error_count}")
    print("=" * 80)


def main():
    # Verificar que el test base existe
    if not os.path.exists(TEST_SCRIPT):
        print(f"ERROR: No se encuentra {TEST_SCRIPT}")
        sys.exit(1)

    print(f"Runner multi-modelo iniciado ({len(MODELS)} modelos)")
    print(f"Test base: {os.path.relpath(TEST_SCRIPT)}")
    print()

    all_results = []

    for i, model_conf in enumerate(MODELS, 1):
        print(f"[{i}/{len(MODELS)}] ", end="")
        result = run_single_test(model_conf)
        all_results.append(result)
        print(f"  -> {result['status']} ({result.get('tests_pass', 0)}/{result.get('tests_total', 5)})")
        print()

    print_summary(all_results)

    # Guardar reporte consolidado
    report = {
        "timestamp": datetime.now().isoformat(),
        "type": "multi_model_validation",
        "models": all_results
    }
    report_path = os.path.join(os.path.dirname(TEST_SCRIPT), MULTI_REPORT)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReporte consolidado guardado en {report_path}")


if __name__ == "__main__":
    main()
