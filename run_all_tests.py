#!/usr/bin/env python3
"""Ejecuta todos los tests del proyecto y guarda resultados.

Lee API keys de Verificacion-modelos-ai/.env (centralizado).
Ejecuta tests de API con AMBOS modelos: gpt-oss-20b (Cuenta 1) y qwen3.8-27b (Cuenta 2).
Ejecuta tests de modelos locales: big-pickle y mimo-v2.6-flash-free (OpenCode).
"""
import sys
import os
import json
import subprocess
import time
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")
TESTS_SCRIPTS = os.path.join(TESTS_DIR, "scripts")
TESTS_LIB = os.path.join(TESTS_DIR, "lib")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
VERIFICACION_DIR = os.path.join(PROJECT_ROOT, "..", "Verificacion-modelos-ai")

sys.path.insert(0, TESTS_LIB)
from rate_limit import EXIT_BLOCKED, QUOTA_STATUS_FILENAME, reclassify_file_tpd  # noqa: E402

QUOTA_PATH = os.path.join(TESTS_DIR, "answers", QUOTA_STATUS_FILENAME)

# Mapeo de modelos a variables de entorno en Verificacion-modelos-ai/.env
MODEL_KEY_MAP = {
    "openai/gpt-oss-20b": "GROQ_CUENTA_1",
    "qwen/qwen3.8-27b": "GROQ_CUENTA_2",
}

# Modelos locales OpenCode
NATIVE_MODELS = [
    "opencode/big-pickle",
    "opencode/mimo-v2.6-flash-free",
]


def get_api_key_for_model(model_name):
    """Retorna la API key correspondiente al modelo desde Verificacion-modelos-ai/.env"""
    env_var = MODEL_KEY_MAP.get(model_name)
    if not env_var:
        raise ValueError(f"No hay key configurada para el modelo: {model_name}")
    key = os.getenv(env_var)
    if not key:
        raise ValueError(f"Variable {env_var} no encontrada en .env de Verificacion-modelos-ai")
    return key


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


# Cargar keys desde Verificacion-modelos-ai
load_verificacion_env()


def load_quota_status():
    """Lee quota_status.json del sondeo (paso 0). None si no existe."""
    try:
        with open(QUOTA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def account_status(quota, account):
    """Estado del sondeo para una cuenta, o None si no hay sondeo."""
    if not quota:
        return None
    return (quota.get("accounts", {}).get(account) or {}).get("status")

# Configurar proyecto de tests externo
os.environ.setdefault("TEST_PROJECT", os.path.join(PROJECT_ROOT, "..", "test-ai-config"))

results = {}


def run_cmd(name, cmd, cwd=None, timeout=300, env=None):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    start = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          cwd=cwd or PROJECT_ROOT, env=env or os.environ)
        elapsed = round(time.time() - start, 1)
        print(r.stdout[-2000:] if len(r.stdout) > 2000 else r.stdout)
        if r.stderr:
            print(f"STDERR: {r.stderr[-500:]}")
        if r.returncode == 0:
            status = "OK"
        elif r.returncode == EXIT_BLOCKED:
            # 429 TPD: cuota diaria agotada, no es FAIL (tarea 15)
            status = "BLOCKED_TPD"
        else:
            status = "FAIL"
        results[name] = {"status": status,
                         "returncode": r.returncode, "elapsed": elapsed}
    except subprocess.TimeoutExpired:
        results[name] = {"status": "TIMEOUT", "elapsed": timeout}
        print(f"  TIMEOUT despues de {timeout}s")
    except Exception as e:
        results[name] = {"status": "ERROR", "error": str(e)}
        print(f"  ERROR: {e}")


# ============================================================
# TESTS LOCALES (sin API)
# ============================================================
print("\n" + "#"*60)
print("# TESTS LOCALES (sin API)")
print("#"*60)

run_cmd("pytest (test_email_validator)",
        [sys.executable, "-m", "pytest", "tests/unit/test_email_validator.py", "-v"])

run_cmd("test_validators.py (35 tests)",
        [sys.executable, os.path.join(TESTS_SCRIPTS, "test_validators.py")])

run_cmd("test_rate_limit_tpd.py (429 TPD)",
        [sys.executable, os.path.join(TESTS_SCRIPTS, "test_rate_limit_tpd.py")])


# ============================================================
# TESTS CON API — AMBOS modelos
# ============================================================
print("\n" + "#"*60)
print("# TESTS CON API — AMBOS MODELOS")
print("#"*60)

# 23/09/2026 (T7): gpt-oss re-incluido. Suite medida en 880.2s < 1200s;
# el "timeout" historico de 1135s eran retries por 429 TPD, no lentitud.
models_to_test = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

fresh_done = False
quota = load_quota_status()
if quota:
    print(f"[SONDEO] Cuota leida de {QUOTA_PATH} ({quota.get('timestamp')})")

for i, model in enumerate(models_to_test):
    account = MODEL_KEY_MAP[model]

    # Paso 3 (tarea 15): cuenta sin cuota diaria -> no se lanza la suite de
    # ese modelo; se registra BLOCKED_TPD y se reclasifican sus casos con
    # evidencia de 429-TPD. Los modelos con cuota y los nativos siguen.
    qstatus = account_status(quota, account)
    if qstatus == "BLOCKED_TPD":
        print(f"\n{'#'*60}")
        print(f"# {model} | {account}: BLOCKED_TPD (cuota diaria agotada)")
        print(f"{'#'*60}")
        print("[SONDEO] Cuenta sin cuota: se corren solo los modelos disponibles.")
        if not fresh_done:
            # El --fresh lo consume esta cuenta para que el primer modelo
            # SI ejecutado no borre los reportes de los demas
            fresh_done = True
        results[f"test_ai_structure.py ({model})"] = {"status": "BLOCKED_TPD", "elapsed": 0}
        results[f"run_advanced_tests.py --api {model}"] = {"status": "BLOCKED_TPD", "elapsed": 0}
        label = f"api/{model}"
        for rep_name in ("advanced_validation_report.json", "ai_validation_report.json"):
            changed = reclassify_file_tpd(os.path.join(TESTS_DIR, "answers", rep_name),
                                          model_labels={label})
            if changed:
                print(f"[TPD] {rep_name}: {changed} caso(s) con evidencia 429-TPD -> BLOCKED_TPD")
        continue

    api_key = get_api_key_for_model(model)

    print(f"\n{'#'*60}")
    print(f"# MODELO: {model} | CUENTA: {account}")
    print(f"{'#'*60}")

    env = os.environ.copy()
    env["LLM_BASE_URL"] = "https://api.groq.com/openai/v1"
    env["LLM_MODEL"] = model
    env["GROQ_API_KEY"] = api_key
    env["LLM_API_KEY"] = api_key
    env["PYTHONIOENCODING"] = "utf-8"

    use_fresh = not fresh_done
    if use_fresh:
        fresh_done = True

    # Test 1: test_ai_structure.py (--fresh solo en la primera llamada global)
    structure_cmd = [sys.executable, os.path.join(TESTS_SCRIPTS, "test_ai_structure.py"),
                     "--api", model]
    if use_fresh:
        structure_cmd.append("--fresh")
    run_cmd(f"test_ai_structure.py ({model})",
            structure_cmd,
            timeout=120, env=env)

    # Test 2: run_advanced_tests.py (--fresh solo en la primera llamada global)
    advanced_cmd = [sys.executable, os.path.join(TESTS_SCRIPTS, "run_advanced_tests.py"),
                    "--api", model]
    if use_fresh:
        advanced_cmd.append("--fresh")
    run_cmd(f"run_advanced_tests.py --api {model}",
            advanced_cmd,
            timeout=1200, env=env)

    # Pausa entre modelos API para evitar rate limit
    if model != models_to_test[-1]:
        print(f"\n[PAUSA] Esperando 10s entre modelos API...")
        time.sleep(10)


# ============================================================
# TESTS CON MODELOS LOCALES (OpenCode)
# ============================================================
print("\n" + "#"*60)
print("# TESTS CON MODELOS LOCALES (OpenCode)")
print("#"*60)

for model in NATIVE_MODELS:
    print(f"\n{'#'*60}")
    print(f"# MODELO NATIVO: {model}")
    print(f"{'#'*60}")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    # Test 1: test_ai_structure.py --native
    run_cmd(f"test_ai_structure.py --native {model}",
            [sys.executable, os.path.join(TESTS_SCRIPTS, "test_ai_structure.py"),
             "--native", model],
            timeout=600, env=env)

    # Test 2: run_advanced_tests.py (sin --api, usa OpenCode nativo)
    run_cmd(f"run_advanced_tests.py {model}",
            [sys.executable, os.path.join(TESTS_SCRIPTS, "run_advanced_tests.py"),
             model],
            timeout=1200, env=env)


# ============================================================
# GENERAR REPORTE HTML (después de todos los tests)
# ============================================================
print("\n" + "#"*60)
print("# GENERANDO REPORTE HTML")
print("#"*60)

run_cmd("generate_html_report.py",
        [sys.executable, os.path.join(SCRIPTS_DIR, "generate_html_report.py")])


# ============================================================
# RESUMEN
# ============================================================
print("\n" + "#"*60)
print("# RESUMEN")
print("#"*60)
for name, r in results.items():
    icon = "OK" if r["status"] == "OK" else r["status"]
    print(f"  [{icon}] {name} ({r.get('elapsed', '?')}s)")

# Guardar resumen
summary_path = os.path.join(TESTS_DIR, "answers", "test_run_summary.json")
os.makedirs(os.path.dirname(summary_path), exist_ok=True)
with open(summary_path, "w") as f:
    json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, indent=2)

print(f"\nResumen guardado en {summary_path}")
