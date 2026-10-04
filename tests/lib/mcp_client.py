#!/usr/bin/env python3
"""
Cliente MCP stdio mínimo: initialize, tools/list, tools/call.

Habla JSON-RPC 2.0 (newline-delimited) con un servidor MCP por stdio.
Reutiliza el mismo camino que usa OpenCode con mcp_bridge.py.

Los nombres que el bridge expone son internos (memory_save). Al publicarlos
para la API hay que prefijarlos con el server name de opencode.json:
brain-ai_memory_save (tarea 16J).
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
            stderr=subprocess.PIPE,
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
            # Si el proceso murio, no esperar el timeout completo:
            # reportar exit code + stderr (tarea 13.2)
            if self.proc.poll() is not None:
                stderr_tail = ""
                try:
                    stderr_tail = (self.proc.stderr.read() or "")[-500:]
                except Exception:
                    pass
                raise MCPError(
                    f"Bridge termino con exit code {self.proc.returncode}"
                    + (f". stderr: {stderr_tail}" if stderr_tail else "")
                )
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


# ── Nombre del server MCP (tarea 16J) ─────────────────────────────
# OpenCode registra cada tool MCP como <server_name>_<tool_name>, tal cual
# figura en opencode.json. Ver https://opencode.ai/docs/mcp-servers:
#   "MCP server tools are registered with server name as prefix"
# El bridge expone nombres internos (memory_save); el nombre publicado por
# el harness tiene que ser brain-ai_memory_save, no memory_save.
# 824 llamadas en ~/.local/share/opencode/log/opencode.log: todas con guion.
DEFAULT_SERVER_NAME = "brain-ai"
BRIDGE_MARKER = "mcp_bridge.py"
CONFIG_FILENAMES = ("opencode.json", "opencode.jsonc")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_PROJECT = os.path.normpath(
    os.getenv("TEST_PROJECT", os.path.join(PROJECT_ROOT, "..", "test-ai-config")))


def _server_name_from_config(path):
    """Server MCP del bridge en un opencode.json, o None si no se puede leer.

    El bridge se reconoce por su comando (apunta a mcp_bridge.py). Si el
    archivo declara varios servers y ninguno coincide, devuelve None antes
    que adivinar: un nombre equivocado produce tools que Groq rechaza.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
    except (OSError, ValueError):
        return None
    servers = config.get("mcp")
    if not isinstance(servers, dict) or not servers:
        return None
    for name, spec in servers.items():
        if not isinstance(spec, dict):
            continue
        command = spec.get("command") or []
        if isinstance(command, str):
            command = [command]
        if any(BRIDGE_MARKER in str(part) for part in command):
            return name
    if len(servers) == 1:
        return next(iter(servers))
    return None


def discover_server_name(test_project=None, project_root=None):
    """Devuelve la clave del server MCP tal como la declara opencode.json.

    Orden: <TEST_PROJECT>/opencode.json -> <PROJECT_ROOT>/opencode.json
           -> "brain-ai" (fallback, decision D9).
    """
    roots = (TEST_PROJECT if test_project is None else test_project,
             PROJECT_ROOT if project_root is None else project_root)
    for root in roots:
        if not root:
            continue
        for filename in CONFIG_FILENAMES:
            name = _server_name_from_config(os.path.join(root, filename))
            if name:
                return name
    return DEFAULT_SERVER_NAME


def _tool_schema(name, tool):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": tool.get("description", ""),
            "parameters": tool.get("inputSchema",
                                   {"type": "object", "properties": {}}),
        },
    }


def mcp_tools_to_openai(mcp_tools, server_name=None):
    """
    Convierte tools MCP al formato OpenAI/Groq.
    Devuelve (tools_openai, name_map) donde name_map traduce
    nombre_api -> nombre_mcp real.

    Cada tool se publica UNA vez, con el nombre registrado por OpenCode:
    <server_name>_<tool_name> (tarea 16J). server_name=None lo resuelve
    discover_server_name() leyendo opencode.json; los unit tests pasan el
    nombre explicito para no tocar el filesystem.

    Sin prefijo, cuando el modelo obedece el prompt Groq responde 400
    tool_use_failed: "attempted to call tool 'brain_ai_memory_save' which
    was not in request.tools" (D2 gpt-oss, tarea 16H, 28/09/2026).
    """
    if server_name is None:
        server_name = discover_server_name()
    tools = []
    name_map = {}
    for t in mcp_tools:
        api_name = sanitize_tool_name(f"{server_name}_{t['name']}")
        name_map[api_name] = t["name"]
        tools.append(_tool_schema(api_name, t))

    return tools, name_map
