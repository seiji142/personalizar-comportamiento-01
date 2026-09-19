#!/usr/bin/env python3
"""Test nativo simple: inicia servidor OpenCode y ejecuta un prompt."""
import os
import subprocess
import socket
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_PROJECT = os.path.normpath(os.path.join(PROJECT_ROOT, "..", "test-ai-config"))
OPENCODE_CLI = os.path.join(os.environ.get("APPDATA", ""), "npm", "opencode.cmd")
if not os.path.exists(OPENCODE_CLI):
    OPENCODE_CLI = os.path.join(os.environ.get("LOCALAPPDATA", ""), "opencode", "opencode-cli.exe")

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"TEST_PROJECT: {TEST_PROJECT}")
print(f"TEST_PROJECT exists: {os.path.exists(TEST_PROJECT)}")
print(f"CLI: {OPENCODE_CLI}")
print(f"CLI exists: {os.path.exists(OPENCODE_CLI)}")

# Find free port
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
print(f"Port: {port}")

# Start server
print("Starting server...")
proc = subprocess.Popen(
    [OPENCODE_CLI, "serve", "--port", str(port)],
    cwd=TEST_PROJECT,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
print(f"Server PID: {proc.pid}")

# Wait for server to be ready
for i in range(20):
    time.sleep(1)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            print(f"Server ready after {i+1}s")
            break
    except OSError:
        pass
else:
    print("Server not ready after 20s")
    proc.terminate()
    exit(1)

# Query
print("Running query...")
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
print(f"Return code: {result.returncode}")
print(f"STDOUT: {result.stdout[:500]}")
print(f"STDERR: {result.stderr[:500]}")

proc.terminate()
