#!/usr/bin/env python3
"""
Test minimal: ejecuta UNA pregunta contra UN modelo y muestra el ciclo completo.
Sin imports de tests/lib. Sin server. Solo opencode run --dir.

Uso:
  python test_minimal.py
  python test_minimal.py --model opencode/big-pickle
  python test_minimal.py --prompt "Cual es tu rol?"
  python test_minimal.py --model opencode/mimo-v2.6-flash-free --prompt "Di hola"
"""
import os
import sys
import json
import subprocess
import argparse


def log(label, value, indent=0):
    prefix = "  " * indent
    print(f"  {prefix}[{label}] {value}")


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_config(project_root, test_project, cli_path):
    separator("1. CONFIGURACION")
    log("PROJECT_ROOT", project_root)
    log("TEST_PROJECT", test_project)
    log("OPENCODE_CLI", cli_path)
    log("CLI exists", os.path.exists(cli_path))
    log("TEST_PROJECT exists", os.path.exists(test_project))

    # Env vars de desktop app
    log("OPENCODE_SERVER_PASSWORD", repr(os.environ.get("OPENCODE_SERVER_PASSWORD", "(not set)")))
    log("OPENCODE_SERVER_USERNAME", repr(os.environ.get("OPENCODE_SERVER_USERNAME", "(not set)")))

    # Archivos .ai/ en TEST_PROJECT
    separator("2. ARCHIVOS .ai/ EN TEST_PROJECT")
    ai_path = os.path.join(test_project, ".ai")
    log("ai_path", ai_path)
    log("ai_path exists", os.path.exists(ai_path))

    if os.path.exists(ai_path):
        for f in ["system.md", "rules.md", "context.md", "agents.md", "MEMORY.md"]:
            fp = os.path.join(ai_path, f)
            if os.path.exists(fp):
                size = os.path.getsize(fp)
                log(f"  {f}", f"{size} bytes")
            else:
                log(f"  {f}", "NOT FOUND")
    else:
        log("ERROR", f"No existe {ai_path}")


def run_cli(cli_path, model, prompt, test_project):
    separator("3. EJECUTAR CLI")
    cmd = [
        cli_path, "run",
        "--model", model,
        "--format", "json",
        "--dir", test_project,
        prompt
    ]

    # Limpiar env vars de desktop app
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["OPENCODE_SERVER_PASSWORD"] = ""
    env["OPENCODE_SERVER_USERNAME"] = ""

    log("cmd", " ".join(cmd))
    log("cwd", test_project)
    log("prompt", prompt)

    t0 = __import__("time").time()
    try:
        result = subprocess.run(
            cmd, cwd=test_project,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env=env, timeout=120
        )
        elapsed = round(__import__("time").time() - t0, 1)

        log("returncode", result.returncode)
        log("elapsed", f"{elapsed}s")
        log("stdout length", f"{len(result.stdout)} chars")
        log("stderr length", f"{len(result.stderr)} chars")

        separator("4. STDOUT RAW")
        print(result.stdout[:3000] if result.stdout else "(empty)")

        separator("5. STDERR RAW")
        print(result.stderr[:2000] if result.stderr else "(empty)")

        return result

    except subprocess.TimeoutExpired:
        log("ERROR", "TIMEOUT after 120s")
        return None
    except Exception as e:
        log("ERROR", str(e))
        return None


def parse_output(stdout):
    separator("6. PARSEAR EVENTOS")
    if not stdout or not stdout.strip():
        log("ERROR", "stdout vacio, nada que parsear")
        return ""

    lines = [l.strip() for l in stdout.strip().split("\n") if l.strip()]
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
                    log(f"  line {i} TYPE=text", f"FOUND: {text[:200]}", indent=1)
                else:
                    log(f"  line {i} TYPE=text", "empty text field", indent=1)
            else:
                log(f"  line {i} TYPE={etype}", "(skip)", indent=1)

        except json.JSONDecodeError as e:
            log(f"  line {i} PARSE ERROR", str(e)[:100], indent=1)
            log(f"  line {i} raw", line[:200], indent=1)

    log("event_types", event_types)
    log("text_parts found", len(text_parts))

    separator("7. RESULTADO FINAL")
    content = "\n".join(text_parts)
    if content:
        log("reply", content[:500])
    else:
        log("reply", "VACIO - no se encontro ningun event type='text'")
        log("hint", "Verifica que --dir apunta al proyecto correcto con .ai/")

    return content


def find_cli():
    """Busca el CLI de opencode en las ubicaciones conocidas."""
    candidates = [
        # npm global install (nuevo)
        os.path.join(os.environ.get("APPDATA", ""), "npm", "opencode.cmd"),
        # Desktop app (viejo)
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "opencode", "opencode-cli.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]  # fallback al primero


def main():
    parser = argparse.ArgumentParser(description="Test minimal del ciclo CLI")
    parser.add_argument("--model", default="opencode/mimo-v2.6-flash-free",
                        help="Modelo a usar (default: opencode/mimo-v2.6-flash-free)")
    parser.add_argument("--prompt", default="Di hola",
                        help="Prompt a enviar (default: 'Di hola')")
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    test_project = os.path.normpath(os.getenv(
        "TEST_PROJECT", os.path.join(project_root, "..", "test-ai-config")))
    cli_path = find_cli()

    print_config(project_root, test_project, cli_path)
    result = run_cli(cli_path, args.model, args.prompt, test_project)
    if result:
        parse_output(result.stdout)

    separator("FIN")


if __name__ == "__main__":
    main()
