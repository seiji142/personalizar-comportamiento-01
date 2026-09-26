#!/usr/bin/env python3
"""Diagnostico: que TEST_PROJECT calcula cada script."""
import os
import sys

# Simular __file__ de cada script
scripts = {
    "run_advanced_tests.py": "tests/scripts/run_advanced_tests.py",
    "model_runner.py": "tests/lib/model_runner.py",
    "test_native_simple.py": "tests/scripts/test_native_simple.py",
}

for name, rel_path in scripts.items():
    # os.path.dirname de un path relativo
    d = os.path.dirname(rel_path)
    # Contar ".."
    up_count = rel_path.count("..")
    
    # Lo que hace run_advanced_tests.py (2 niveles)
    if "scripts" in rel_path:
        pr = os.path.abspath(os.path.join(d, "..", ".."))
    else:  # lib (3 niveles)
        pr = os.path.abspath(os.path.join(d, "..", "..", ".."))
    
    tp = os.path.normpath(os.path.join(pr, "..", "test-ai-config"))
    
    print(f"=== {name} ===")
    print(f"  dirname(__file__): {d}")
    print(f"  PROJECT_ROOT:      {pr}")
    print(f"  TEST_PROJECT:      {tp}")
    print(f"  Exists:            {os.path.exists(tp)}")
    print()

# Verificar que el CLI existe
cli = os.path.join(os.environ.get("LOCALAPPDATA", ""), "opencode", "opencode-cli.exe")
print(f"CLI: {cli}")
print(f"CLI exists: {os.path.exists(cli)}")

# Verificar que opencode --version funciona con cwd=TEST_PROJECT
tp = os.path.normpath(os.path.join(os.path.abspath('.'), '..', 'test-ai-config'))
import subprocess
try:
    r = subprocess.run([cli, "--version"], cwd=tp, capture_output=True, text=True, timeout=5)
    print(f"opencode --version: {r.stdout.strip()[:100]}")
    print(f"Return code: {r.returncode}")
except Exception as e:
    print(f"ERROR: {e}")
