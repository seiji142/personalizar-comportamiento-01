#!/usr/bin/env python3
"""
Runner multi-modelo para validacion de estructura .ai/.
Ejecuta test_ai_structure.py contra multiples modelos y consolida resultados.
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime

# Ruta absoluta al proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TEST_SCRIPT = os.path.join(PROJECT_ROOT, "src", "doc", "ESTRUCTURA", "test_ai_structure.py")
REPORT_FILE = "ai_validation_report.json"
MULTI_REPORT = "multi_model_validation_report.json"

# Modelos a probar
MODELS = [
    {
        "alias": "groq/llama-3.3-70b",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model_id": "llama-3.3-70b-versatile"
    },
    {
        "alias": "groq/llama-3.1-8b",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model_id": "llama-3.1-8b-instant"
    },
    {
        "alias": "groq/llama-4-scout",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model_id": "meta-llama/llama-4-scout-17b-16e-instruct"
    },
    {
        "alias": "z-ai/glm-4.7",
        "base_url": "https://api.z.ai/api/paas/v4",
        "api_key_env": "ZAI_API_KEY",
        "model_id": "glm-4.7-flash"
    },
    {
        "alias": "nvidia/minimax",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "model_id": "minimaxai/minimax-m2.7"
    },
    {
        "alias": "openrouter/free",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model_id": "openrouter/free"
    },
    {
        "alias": "openrouter/gemma-4",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model_id": "google/gemma-4-31b-it:free"
    }
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
            env=env, cwd=PROJECT_ROOT
        )
        elapsed = round(time.time() - start, 1)

        # Leer reporte generado (se genera en PROJECT_ROOT)
        report_path = os.path.join(PROJECT_ROOT, REPORT_FILE)
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
        else:
            report_data = {"results": []}

        # Extraer resultados
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
