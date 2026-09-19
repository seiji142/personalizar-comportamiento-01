#!/usr/bin/env python3
"""Verificar formato JSON del output de OpenCode CLI."""
import os
import subprocess
import socket
import time
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_PROJECT = os.path.normpath(os.path.join(PROJECT_ROOT, "..", "test-ai-config"))
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

cmd = [
    OPENCODE_CLI, "run",
    "--attach", f"http://127.0.0.1:{port}",
    "--model", "opencode/mimo-v2.5-free",
    "--format", "json",
    "Di hola"
]
result = subprocess.run(
    cmd, cwd=TEST_PROJECT,
    capture_output=True, text=True,
    encoding="utf-8", errors="replace",
    timeout=60
)

print("=== STDOUT (raw) ===")
for line in result.stdout.strip().split("\n"):
    if not line.strip():
        continue
    try:
        event = json.loads(line)
        etype = event.get("type", "?")
        if etype == "text":
            print(f"  TYPE=text -> part.text={repr(event.get('part',{}).get('text','')[:200])}")
        elif etype == "step_start" or etype == "step-start":
            print(f"  TYPE={etype} (skip)")
        elif etype == "message_start" or etype == "message-start":
            print(f"  TYPE={etype} (skip)")
        else:
            print(f"  TYPE={etype} -> {json.dumps(event)[:200]}")
    except json.JSONDecodeError:
        print(f"  NON-JSON: {line[:100]}")

print(f"\n=== STDERR ===")
print(result.stderr[:500] if result.stderr else "(empty)")
print(f"\nReturn code: {result.returncode}")

proc.terminate()
