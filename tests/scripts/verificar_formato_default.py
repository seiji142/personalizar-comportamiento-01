#!/usr/bin/env python3
"""Comparar formato default vs json."""
import os, subprocess, socket, time, json

TEST_PROJECT = os.path.normpath(os.path.join(os.path.abspath("."), "..", "test-ai-config"))
OPENCODE_CLI = os.path.join(os.environ.get("APPDATA", ""), "npm", "opencode.cmd")
if not os.path.exists(OPENCODE_CLI):
    OPENCODE_CLI = os.path.join(os.environ.get("LOCALAPPDATA", ""), "opencode", "opencode-cli.exe")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()

proc = subprocess.Popen(
    [OPENCODE_CLI, "serve", "--port", str(port)],
    cwd=TEST_PROJECT,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
for i in range(10):
    time.sleep(1)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            break
    except OSError:
        pass

# Test 1: formato default
print("=== FORMATO DEFAULT ===")
cmd = [OPENCODE_CLI, "run", "--attach", f"http://127.0.0.1:{port}",
       "--model", "opencode/mimo-v2.5-free", "Di hola"]
result = subprocess.run(cmd, cwd=TEST_PROJECT, capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=60)
print(f"STDOUT: {result.stdout[:500]}")
print(f"STDERR: {result.stderr[:500]}")
print(f"Return code: {result.returncode}")

proc.terminate()
