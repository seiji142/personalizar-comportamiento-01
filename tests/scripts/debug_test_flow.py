#!/usr/bin/env python3
"""
Script de debug: ejecuta 1 test nativo con logging detallado en cada paso.
No toca test_ai_structure.py ni model_runner.py.

Uso:
  python debug_test_flow.py                           # Test 1 por defecto
  python debug_test_flow.py --test-id 2               # Test especifico
  python debug_test_flow.py --model opencode/big-pickle  # Modelo especifico
"""
import os
import sys
import json
import socket
import subprocess
import time
import argparse

# --- PATHS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_PROJECT = os.path.normpath(os.getenv("TEST_PROJECT", os.path.join(PROJECT_ROOT, "..", "test-ai-config")))
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")
OPENCODE_CLI = os.path.join(os.environ.get("APPDATA", ""), "npm", "opencode.cmd")
if not os.path.exists(OPENCODE_CLI):
    OPENCODE_CLI = os.path.join(os.environ.get("LOCALAPPDATA", ""), "opencode", "opencode-cli.exe")
AI_FOLDER = ".ai"
SYSTEM_PROMPT_FILES = ["system.md", "rules.md", "context.md", "agents.md"]
QUESTIONS_FILE = os.path.join(TESTS_DIR, "questions", "ai_structure_questions.json")


def log(label, value, indent=0):
    prefix = "  " * indent
    print(f"  {prefix}[{label}] {value}")


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-id", type=int, default=1, help="ID del test a ejecutar (default: 1)")
    parser.add_argument("--model", default="opencode/mimo-v2.5-free", help="Modelo a usar")
    args = parser.parse_args()

    # =========================================================
    separator("1. CONFIGURACION / PATHS")
    # =========================================================
    log("PROJECT_ROOT", PROJECT_ROOT)
    log("TEST_PROJECT", TEST_PROJECT)
    log("OPENCODE_CLI", OPENCODE_CLI)
    log("CLI exists", os.path.exists(OPENCODE_CLI))
    log("TEST_PROJECT exists", os.path.exists(TEST_PROJECT))

    # =========================================================
    separator("2. VERIFICAR .ai/ EN TEST_PROJECT")
    # =========================================================
    ai_path = os.path.join(TEST_PROJECT, AI_FOLDER)
    log("ai_path", ai_path)
    log("ai_path exists", os.path.exists(ai_path))

    if os.path.exists(ai_path):
        files_in_ai = os.listdir(ai_path)
        log("files in .ai/", files_in_ai)
        for f in SYSTEM_PROMPT_FILES:
            fp = os.path.join(ai_path, f)
            exists = os.path.exists(fp)
            size = os.path.getsize(fp) if exists else 0
            log(f"  {f}", f"exists={exists}, size={size} bytes", indent=1)
    else:
        log("ERROR", f"No existe {ai_path}")
        return

    # Verificar que NO estamos leyendo de personalizar-comportamiento-01/.ai/
    other_ai = os.path.join(PROJECT_ROOT, ".ai")
    log("other .ai/ (personalizar)", other_ai)
    log("other .ai/ exists", os.path.exists(other_ai))

    # =========================================================
    separator("3. CARGAR SYSTEM PROMPT DESDE .ai/")
    # =========================================================
    parts = []
    for filename in SYSTEM_PROMPT_FILES:
        filepath = os.path.join(ai_path, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            parts.append(f"=== {filename} ===\n{content}")
            log(f"  {filename}", f"loaded, {len(content)} chars", indent=1)
            log(f"  {filename} preview", content[:100] + "...", indent=1)
        else:
            log(f"  {filename}", "NOT FOUND", indent=1)

    system_prompt = "\n\n".join(parts)
    log("total system_prompt", f"{len(system_prompt)} chars")

    # =========================================================
    separator("4. CARGAR QUESTIONS")
    # =========================================================
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    target_q = None
    for q in questions:
        if q["id"] == args.test_id:
            target_q = q
            break

    if not target_q:
        log("ERROR", f"Test {args.test_id} no encontrado")
        return

    log("test id", target_q["id"])
    log("test target", target_q["target"])
    log("test prompt", target_q["prompt"][:200])

    # =========================================================
    separator("5. INICIAR SERVIDOR OPENCODE")
    # =========================================================
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    log("port", port)

    log("starting server", f"cwd={TEST_PROJECT}")
    server_proc = subprocess.Popen(
        [OPENCODE_CLI, "serve", "--port", str(port)],
        cwd=TEST_PROJECT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    log("server PID", server_proc.pid)

    # Wait for server
    for i in range(20):
        time.sleep(1)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                log("server ready", f"after {i+1}s")
                break
        except OSError:
            pass
    else:
        log("ERROR", "Server not ready after 20s")
        server_proc.terminate()
        return

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # Limpiar variables de la desktop app de OpenCode
    # (causa: intenta conectarse al servidor existente en vez de crear sesión nueva)
    env["OPENCODE_SERVER_PASSWORD"] = ""
    env["OPENCODE_SERVER_USERNAME"] = ""
    log("OPENCODE_SERVER_PASSWORD", repr(env["OPENCODE_SERVER_PASSWORD"]))
    log("OPENCODE_SERVER_USERNAME", repr(env["OPENCODE_SERVER_USERNAME"]))

    simple_prompt = "Responde solo: hola"

    formats = [
        ("JSON + SIN ATTACH (cli crea sesión)", "json", False),
        ("JSON + CON ATTACH", "json", True),
    ]

    for label, fmt, attach in formats:
        separator(f"6. EJECUTAR CLI — {label}")
        cmd = [
            OPENCODE_CLI, "run",
            "--model", args.model,
            "--format", fmt,
        ]
        cmd.append("--print-logs")
        if attach:
            cmd.extend(["--attach", f"http://127.0.0.1:{port}"])
        else:
            cmd.extend(["--dir", TEST_PROJECT])
        cmd.append(simple_prompt)

        log("cmd", cmd)
        log("cwd", TEST_PROJECT)
        log("prompt", simple_prompt)

        t0 = time.time()
        try:
            result = subprocess.run(
                cmd, cwd=TEST_PROJECT,
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                env=env, timeout=120
            )
            elapsed = round(time.time() - t0, 1)

            log("returncode", result.returncode)
            log("elapsed", f"{elapsed}s")
            log("stdout length", f"{len(result.stdout)} chars")
            log("stderr length", f"{len(result.stderr)} chars")

            separator(f"7. STDOUT RAW — {label}")
            print(result.stdout[:2000] if result.stdout else "(empty)")

            separator(f"8. STDERR RAW — {label}")
            print(result.stderr[:2000] if result.stderr else "(empty)")

            if fmt == "json":
                separator(f"9. PARSEAR JSON EVENTS — {label}")
                lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
                log("total lines", len(lines))

                text_parts = []
                event_types = {}
                for i, line in enumerate(lines):
                    try:
                        event = json.loads(line)
                        etype = event.get("type", "unknown")
                        event_types[etype] = event_types.get(etype, 0) + 1

                        if etype == "text":
                            part = event.get("part", {})
                            text = part.get("text", "")
                            if text:
                                text_parts.append(text)
                                log(f"  line {i} TYPE=text", f"FOUND: {text[:200]}...", indent=1)
                            else:
                                log(f"  line {i} TYPE=text", "empty text field", indent=1)
                        else:
                            log(f"  line {i} TYPE={etype}", "(skip)", indent=1)

                    except json.JSONDecodeError as e:
                        log(f"  line {i} PARSE ERROR", str(e)[:100], indent=1)
                        log(f"  line {i} raw", line[:200], indent=1)

                log("event_types", event_types)
                log("text_parts count", len(text_parts))
                if text_parts:
                    for i, tp in enumerate(text_parts):
                        log(f"  text_part[{i}]", tp[:300], indent=1)
                else:
                    log("text_parts", "VACIO - no se encontro ningun event type='text'")

            separator(f"10. RESULTADO — {label}")
            if fmt == "json":
                content = "\n".join(text_parts) if 'text_parts' in dir() else ""
                if not content and result.stderr.strip():
                    content = f"[ERROR] {result.stderr.strip()[:500]}"
                log("reply", repr(content[:300]) if content else "(vacio)")
            else:
                reply = result.stdout.strip()
                log("reply (default format)", repr(reply[:500]) if reply else "(vacio)")

        except subprocess.TimeoutExpired:
            log("ERROR", "TIMEOUT after 120s")
        except Exception as e:
            log("ERROR", str(e))

    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_proc.kill()

    print(f"\n{'='*60}")
    print("  FIN DEL DEBUG")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
