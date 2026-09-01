#!/usr/bin/env python3
"""
Runner de la suite avanzada de tests (jailbreak, estilo de codigo,
factualidad, estructura y roles).

Uso:
  python run_advanced_tests.py                 # todos los modelos nativos, todos los casos
  python run_advanced_tests.py <modelo>        # filtra modelos nativos por nombre
  python run_advanced_tests.py --category A    # solo una categoria (A|B|C)
  python run_advanced_tests.py --api <model>   # contra API (usa GROQ_API_KEY)

Ejecutar desde la raiz del proyecto (hereda .ai/ via opencode.json).
"""

import io
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OPENCODE_CLI = os.path.join(os.environ.get("LOCALAPPDATA", ""), "opencode", "opencode-cli.exe")
QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), "advanced_questions.json")
REPORT_FILE = "advanced_validation_report.json"

# Cargar casos desde el directorio del script
sys.path.insert(0, os.path.dirname(__file__))
from advanced_validators import validate_advanced

# Modelos nativos contratados (misma lista que run_opencode_models.py)
NATIVE_MODELS = [
    "opencode/big-pickle",
    "opencode/deepseek-v4-flash-free",
    "opencode/mimo-v2.5-free",
    "opencode/north-mini-code-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/mimo-v2-pro-free",
    "opencode/mimo-v2-omni-free",
    "opencode/qwen3.6-plus-free",
    "opencode/nemotron-3-super-free",
    "opencode/minimax-m2.5-free",
    "opencode/gpt-5-nano",
    "opencode/ling-3.0-flash-fin-free",
    "opencode/muse-spark-1.2-contributor-free",
]

CATEGORY_FILTERS = {
    "A": ("jailbreak",),
    "B": ("code_style", "structure", "factuality"),
    "C": ("role",),
}


def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_by_category(questions, category):
    if not category:
        return questions
    allowed = CATEGORY_FILTERS.get(category.upper())
    if not allowed:
        print(f"Categoria desconocida: {category} (usa A, B o C)")
        sys.exit(1)
    return [q for q in questions if q.get("category") in allowed]


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port, timeout=30):
    proc = subprocess.Popen(
        [OPENCODE_CLI, "serve", "--port", str(port)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    # Polling al puerto: mas robusto que un sleep fijo (pueden fallar los
    # primeros casos en maquinas lentas si el server aun no escucha).
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return proc
        except OSError:
            time.sleep(0.5)
    # No se logro conectar (o el proceso murio) dentro del timeout.
    stop_server(proc)
    return None


def stop_server(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def parse_model_response(output):
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


def query_native(server_port, model_id, prompt, timeout=120):
    cmd = [
        OPENCODE_CLI, "run",
        "--attach", f"http://127.0.0.1:{server_port}",
        "--model", model_id,
        "--format", "json",
        prompt
    ]
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            cmd, cwd=PROJECT_ROOT,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env=env, timeout=timeout
        )
        # Parsear solo stdout: stderr contiene logs/diagnosticos del CLI
        # que contaminarian la respuesta si se mezclan con el JSON.
        content = parse_model_response(result.stdout)
        if not content and result.stderr.strip():
            content = f"[ERROR] {result.stderr.strip()[:500]}"
        return content
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR] {str(e)}"


def query_api(model_id, prompt, timeout=60):
    try:
        from openai import OpenAI
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        api_key = os.getenv("LLM_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
        client = OpenAI(base_url=base_url, api_key=api_key)
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": _load_ai_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=800,
            timeout=timeout
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"[ERROR] {str(e)}"


def _load_ai_system_prompt():
    ai_path = os.path.join(PROJECT_ROOT, ".ai")
    parts = []
    for name in ["system.md", "rules.md", "context.md", "agents.md"]:
        fp = os.path.join(ai_path, name)
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                parts.append(f"=== {name} ===\n{f.read().strip()}")
    return "\n\n".join(parts)


def run_cases_for_model(model_label, query_fn, questions):
    per_case = {}
    for case in questions:
        cid = case["id"]
        print(f"   [{cid}] {case['name']}... ", end="", flush=True)
        t0 = time.time()
        response = query_fn(case["prompt"])

        if response.startswith("[TIMEOUT]"):
            status = "TIMEOUT"
            reasons = ["timeout"]
        elif response.startswith("[ERROR]"):
            status = "ERROR"
            reasons = [response]
        else:
            passed, reasons = validate_advanced(response, case)
            status = "PASS" if passed else "FAIL"

        elapsed = round(time.time() - t0, 1)
        per_case[cid] = {
            "name": case["name"],
            "category": case["category"],
            "status": status,
            "time_seconds": elapsed,
            "reasons": reasons,
            "response_preview": response[:200] + "..." if len(response) > 200 else response,
        }
        print(f"{status} ({elapsed}s)")
        for r in reasons[:6]:
            print(f"          - {r}")
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


def main():
    os.system("")

    # Parsear argumentos
    args = sys.argv[1:]
    model_filter = None
    category = None
    api = False
    api_model = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--category" and i + 1 < len(args):
            category = args[i + 1]
            i += 2
        elif a == "--api" and i + 1 < len(args):
            api = True
            api_model = args[i + 1]
            i += 2
        else:
            model_filter = a
            i += 1

    questions = load_questions()
    questions = filter_by_category(questions, category)
    print(f"Runner avanzado ({len(questions)} casos, categorias: {category or 'todas'})")

    models_config = []

    if api:
        if api_model:
            models_config.append({"model": f"api/{api_model}", "native": False, "id": api_model})
        else:
            print("Uso: --api <model_id>")
            sys.exit(1)
    else:
        native = NATIVE_MODELS
        if model_filter:
            native = [m for m in native if model_filter.lower() in m.lower()]
        if not native:
            print(f"No se encontraron modelos nativos que coincidan: {model_filter}")
            sys.exit(1)
        models_config.extend({"model": m, "native": True, "id": m} for m in native)

    # Iniciar servidor solo si hay modelos nativos
    server_proc = None
    port = None
    has_native = any(c["native"] for c in models_config)
    if has_native:
        if not os.path.exists(OPENCODE_CLI):
            print(f"ERROR: No se encuentra opencode CLI en {OPENCODE_CLI}")
            sys.exit(1)
        port = find_free_port()
        print(f"Iniciando servidor OpenCode en puerto {port}...")
        server_proc = start_server(port)
        if server_proc is None:
            print("ERROR: El servidor no pudo iniciar o no esta escuchando")
            sys.exit(1)
        print(f"Servidor OK (PID: {server_proc.pid})\n")

    all_results = {}
    try:
        for cfg in models_config:
            label = cfg["model"]
            print(f"\n[{label}]")
            if cfg["native"]:
                def query_fn(p, model_id=cfg["id"], port=port):
                    return query_native(port, model_id, p)
            else:
                def query_fn(p, model_id=cfg["id"]):
                    return query_api(model_id, p)

            cases = run_cases_for_model(label, query_fn, questions)
            all_results[label] = cases
    finally:
        if server_proc:
            stop_server(server_proc)

    print_summary(all_results, questions)

    # Guardar reporte
    report_path = os.path.join(PROJECT_ROOT, REPORT_FILE)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "type": "advanced_validation",
            "category": category,
            "models": all_results
        }, f, indent=2, ensure_ascii=False)
    print(f"\nReporte guardado en {report_path}")


if __name__ == "__main__":
    main()
