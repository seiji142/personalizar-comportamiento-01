#!/usr/bin/env python3
"""
Cliente MCP stdio mínimo: initialize, tools/list, tools/call.

Habla JSON-RPC 2.0 (newline-delimited) con un servidor MCP por stdio.
Reutiliza el mismo camino que usa OpenCode con mcp_bridge.py.
"""

import json
import re
import subprocess
import threading
import queue
import time
import os


# Ruta al MCP bridge (misma que opencode.json)
# Busqueda robusta hacia arriba: el bridge puede vivir a distinta profundidad
# segun la estructura del workspace (tests/lib/../../Proyecto AI/brain-ai-01).
def _find_bridge_path():
    start = os.path.abspath(os.path.dirname(__file__))
    for _ in range(5):
        candidate = os.path.join(start, "..", "..", "brain-ai-01", "mcp_bridge.py")
        candidate = os.path.abspath(candidate)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(start)
        if parent == start:
            break
        start = parent
    return None


MCP_BRIDGE_PATH = _find_bridge_path()
MCP_BRIDGE_COMMAND = ["python", MCP_BRIDGE_PATH]
MCP_INIT_TIMEOUT = 30


class MCPError(Exception):
    pass


class MCPStdioClient:
    """Habla JSON-RPC 2.0 (newline-delimited) con un servidor MCP por stdio."""

    def __init__(self, command=None):
        self.command = command or MCP_BRIDGE_COMMAND
        self.proc = None
        self._id = 0
        self._responses = queue.Queue()
        self._reader = None

    # ── Ciclo de vida ─────────────────────────────────────────────
    def start(self):
        self.proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._initialize()
        return self

    def close(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
            self.proc = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.close()

    # ── Transporte ────────────────────────────────────────────────
    def _read_loop(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Ignoramos notificaciones del servidor (sin "id")
            if "id" in msg:
                self._responses.put(msg)

    def _send(self, method, params=None, notification=False):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notification:
            self._id += 1
            msg["id"] = self._id
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        if notification:
            return None
        return self._wait_response(self._id)

    def _wait_response(self, req_id, timeout=MCP_INIT_TIMEOUT):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self._responses.get(timeout=1)
            except queue.Empty:
                continue
            if msg.get("id") == req_id:
                if "error" in msg:
                    raise MCPError(msg["error"])
                return msg.get("result")
        raise MCPError(f"Timeout esperando respuesta a request {req_id}")

    # ── Protocolo MCP ─────────────────────────────────────────────
    def _initialize(self):
        self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "advanced-tests", "version": "1.0"},
        })
        self._send("notifications/initialized", {}, notification=True)

    def list_tools(self):
        result = self._send("tools/list", {})
        return result.get("tools", [])

    def call_tool(self, name, arguments):
        result = self._send("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        # El contenido MCP viene como lista de bloques; extraemos texto
        blocks = result.get("content", [])
        texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        return "\n".join(texts) if texts else json.dumps(result)


# ── Adaptación MCP → OpenAI tools ─────────────────────────────────
def sanitize_tool_name(name):
    """Groq/OpenAI solo aceptan [a-zA-Z0-9_-] en nombres de tools."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", name)


def mcp_tools_to_openai(mcp_tools):
    """
    Convierte tools MCP al formato OpenAI/Groq.
    Devuelve (tools_openai, name_map) donde name_map traduce
    nombre_api -> nombre_mcp real.
    """
    tools = []
    name_map = {}
    for t in mcp_tools:
        api_name = sanitize_tool_name(t["name"])
        name_map[api_name] = t["name"]
        tools.append({
            "type": "function",
            "function": {
                "name": api_name,
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            },
        })

    return tools, name_map
