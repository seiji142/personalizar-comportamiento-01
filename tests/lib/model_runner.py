#!/usr/bin/env python3
"""
Adaptadores de modelo para la suite de tests.

Proporciona una interfaz comun (ModelRunner) para ejecutar modelos
tanto via OpenCode nativo como via API directa (Groq) con MCP.

Resultado estandarizado:
{
    "text": str,              # Respuesta final del modelo
    "tool_calls": list,       # Tools ejecutadas (nombre, args, exito)
    "memory_used": bool,      # Si uso brain-ai memory
    "error": str | None       # Error si lo hubo
}
"""

import json
import os
import subprocess
import sys
import time
import threading

from mcp_client import MCPStdioClient, mcp_tools_to_openai, MCPError
from opencode_cli import OPENCODE_CLI
from opencode_events import parse_ndjson
from rate_limit import blocked_message, compute_wait, parse_rate_limit


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_PROJECT = os.path.normpath(os.getenv("TEST_PROJECT", os.path.join(PROJECT_ROOT, "..", "test-ai-config")))

# Límites
QUERY_TIMEOUT = 180  # antes 120; C2 big-pickle llego a 138s (tarea 4)
GROQ_QUERY_TIMEOUT = 180  # 3 minutos máximo para Groq
MAX_TOOL_ITERATIONS = 5
MAX_TOKENS_PER_TEST = 15000
# Tope de tokens por test (tarea 16C): D8-qwen quemo ~28k tokens en un solo
# test con un loop improductivo; un test normal usa 4-10k. Al superarlo se
# aborta el loop con TIMEOUT explicito (no ERROR generico).

# Retry de MCP (tarea #11): si bridge tarda en arrancar/falla, reintentar
MAX_MCP_RETRIES = 3
MCP_RETRY_WAIT = 2  # segundos base, backoff lineal (2s, 4s)

# Retry con backoff para rate limits (429)
MAX_RETRIES = 3
BASE_WAIT_SECONDS = 5


def _load_system_prompt():
    """Carga el system prompt de .ai/ (proyecto de tests o produccion)."""
    ai_path = os.path.join(TEST_PROJECT, ".ai")
    if not os.path.exists(ai_path):
        ai_path = os.path.join(PROJECT_ROOT, ".ai")
    parts = []
    for name in ["system.md", "rules.md", "context.md", "agents.md", "MEMORY.md"]:
        fp = os.path.join(ai_path, name)
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                parts.append(f"=== {name} ===\n{f.read().strip()}")
    return "\n\n".join(parts)


def _parse_opencode_response(output):
    """Parsea la respuesta JSON de OpenCode CLI."""
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


class ModelRunner:
    """Interfaz base para ejecutar modelos."""

    def __init__(self, model_id, system_prompt=None):
        self.model_id = model_id
        self.system_prompt = system_prompt or _load_system_prompt()

    def query(self, prompt):
        """
        Ejecuta una consulta contra el modelo.

        Returns:
            dict: {text, tool_calls, memory_used, error}
        """
        raise NotImplementedError

    def close(self):
        pass


class OpenCodeRunner(ModelRunner):
    """Ejecuta modelos nativos via OpenCode CLI (sin server)."""

    def __init__(self, model_id, system_prompt=None):
        super().__init__(model_id, system_prompt)

    def query(self, prompt):
        """OpenCode crea su propia sesion con --dir. Parsea NDJSON para tool_calls y tokens."""
        cmd = [
            OPENCODE_CLI, "run",
            "--model", self.model_id,
            "--format", "json",
            "--dir", TEST_PROJECT,
            prompt
        ]

        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["OPENCODE_SERVER_PASSWORD"] = ""
            env["OPENCODE_SERVER_USERNAME"] = ""
            result = subprocess.run(
                cmd, cwd=TEST_PROJECT,
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                env=env, timeout=QUERY_TIMEOUT
            )

            parsed = parse_ndjson(result.stdout.splitlines())

            text = parsed.text
            if not text and result.stderr.strip():
                return {"text": "", "tool_calls": [], "memory_used": False,
                        "tokens_used": 0, "error": f"[ERROR] {result.stderr.strip()[:500]}"}

            tool_calls = [
                {"name": tc.name, "args": tc.args, "output": tc.output,
                 "status": tc.status, "success": tc.status == "completed"}
                for tc in parsed.tool_calls
            ]

            return {
                "text": text,
                "tool_calls": tool_calls,
                "memory_used": parsed.memory_used,
                "tokens_used": parsed.tokens.total,
                "files_read": parsed.files_read,
                "error": None,
            }

        except subprocess.TimeoutExpired:
            return {"text": "", "tool_calls": [], "memory_used": False,
                    "tokens_used": 0, "error": "[TIMEOUT]"}
        except Exception as e:
            return {"text": "", "tool_calls": [], "memory_used": False,
                    "tokens_used": 0, "error": f"[ERROR] {str(e)}"}


class GroqRunner(ModelRunner):
    """
    Ejecuta modelos via Groq API con tool calling.
    
    Usa MCP client para descubrir y ejecutar tools dinámicamente,
    mismo camino que OpenCode con mcp_bridge.py.
    """

    def __init__(self, model_id, system_prompt=None, max_tool_rounds=MAX_TOOL_ITERATIONS,
                 max_tokens_per_test=MAX_TOKENS_PER_TEST):
        super().__init__(model_id, system_prompt)
        self.max_tool_rounds = max_tool_rounds
        self.max_tokens_per_test = max_tokens_per_test
        self.mcp = None
        self.tools = []
        self.name_map = {}
        self.mcp_available = False
        self.mcp_error = None
        self._mcp_started = False
        # 429 TPD diario (tarea 15): una vez detectado, fail-fast en el
        # resto de tests del modelo sin volver a llamar a la API
        self.tpd_blocked = False
        self._tpd_message = None

    def _ensure_mcp(self):
        """Inicializa MCP client y descubre tools con reintentos.

        Si el bridge tarda en arrancar (MCP_INIT_TIMEOUT) o falla, reintenta
        antes de rendirse. Expone mcp_available y mcp_error en vez de tragar
        el error en silencio (tarea #11). Solo intenta UNA vez por runner:
        el resultado queda cacheado (_mcp_started) para no repetir el retry
        completo en cada query.
        """
        if self._mcp_started:
            return self.mcp_available

        self._mcp_started = True

        last_error = None
        for attempt in range(1, MAX_MCP_RETRIES + 1):
            try:
                self.mcp = MCPStdioClient().start()
                mcp_tools = self.mcp.list_tools()
                self.tools, self.name_map = mcp_tools_to_openai(mcp_tools)
                self.mcp_available = True
                self.mcp_error = None
                return True
            except MCPError as e:
                last_error = e
                if self.mcp:
                    self.mcp.close()
                    self.mcp = None
            except Exception as e:
                last_error = e
                if self.mcp:
                    self.mcp.close()
                    self.mcp = None

            if attempt < MAX_MCP_RETRIES:
                wait = MCP_RETRY_WAIT * attempt
                print(f"[MCP] Intento {attempt}/{MAX_MCP_RETRIES} fallo: {last_error}. Esperando {wait}s... ", end="", flush=True)
                time.sleep(wait)

        self.mcp_available = False
        self.mcp_error = str(last_error) if last_error else "unknown error"
        return False

    def query(self, prompt):
        """Ejecuta con timeout general via threading."""
        # Inicializar MCP aqui para que mcp_available/error consten incluso en timeout/error
        self._ensure_mcp()

        result = [None]
        error = [None]
        
        def run():
            try:
                result[0] = self._execute_query(prompt)
            except Exception as e:
                error[0] = str(e)
        
        thread = threading.Thread(target=run)
        thread.start()
        thread.join(timeout=GROQ_QUERY_TIMEOUT)
        
        if thread.is_alive():
            return {"text": "", "tool_calls": [], "memory_used": False,
                    "mcp_available": self.mcp_available, "mcp_error": self.mcp_error,
                    "tokens_used": 0,
                    "error": f"[TIMEOUT] {GROQ_QUERY_TIMEOUT}s"}
        
        if error[0]:
            return {"text": "", "tool_calls": [], "memory_used": False,
                    "mcp_available": self.mcp_available, "mcp_error": self.mcp_error,
                    "tokens_used": 0,
                    "error": f"[ERROR] {error[0][:500]}"}
        
        res = result[0] or {"text": "", "tool_calls": [], "memory_used": False,
                            "error": "[ERROR] No response"}
        res.setdefault("mcp_available", self.mcp_available)
        res.setdefault("mcp_error", self.mcp_error)
        return res

    def _execute_query(self, prompt):
        """Ejecuta la consulta real con tool loop via MCP y retry para 429."""
        # Fail-fast 429 TPD (tarea 15): la cuota diaria no se recupera en
        # minutos, asi que no se vuelve a llamar a la API en este runner
        if self.tpd_blocked:
            return {"text": "", "tool_calls": [], "memory_used": False,
                    "tokens_used": 0,
                    "error": self._tpd_message or blocked_message(model_id=self.model_id)}

        try:
            from openai import OpenAI, RateLimitError
        except ImportError:
            return {"text": "", "tool_calls": [], "memory_used": False,
                    "error": "[ERROR] openai package not installed"}

        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        api_key = os.getenv("GROQ_API_KEY", "") or os.getenv("LLM_API_KEY", "")

        if not api_key:
            return {"text": "", "tool_calls": [], "memory_used": False,
                    "error": "[ERROR] No GROQ_API_KEY configured"}

        # Inicializar MCP (opcional para API - si falla, continua sin tools)
        mcp_available = self._ensure_mcp()

        client = OpenAI(base_url=base_url, api_key=api_key)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        all_tool_calls = []
        memory_used = False

        tokens_from_api = 0
        
        for round_num in range(self.max_tool_rounds):
            # Tope de tokens por test (tarea 16C): abortar loops improductivos
            # tipo D8-qwen (~28k en un test) antes de quemar la cuota diaria.
            if tokens_from_api >= self.max_tokens_per_test:
                capped = (f"[TIMEOUT] Tope de tokens por test superado "
                          f"({tokens_from_api} >= {self.max_tokens_per_test}): "
                          f"loop de tools abortado en round {round_num}")
                print(capped)
                return {"text": "", "tool_calls": all_tool_calls,
                        "memory_used": memory_used,
                        "tokens_used": tokens_from_api, "error": capped}
            response = None
            last_error = None
            
            # Retry loop para rate limits (429)
            for retry in range(MAX_RETRIES + 1):
                try:
                    # Solo usar tools si MCP esta disponible
                    kwargs = dict(
                        model=self.model_id,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=800,
                        timeout=60
                    )
                    if mcp_available and self.tools:
                        kwargs["tools"] = self.tools
                        kwargs["tool_choice"] = "auto"
                    
                    response = client.chat.completions.create(**kwargs)
                    # Extraer uso de tokens (Groq API)
                    usage = getattr(response, 'usage', None)
                    if usage:
                        tokens_from_api += getattr(usage, 'total_tokens', 0)
                    break  # Éxito, salir del retry loop
                except RateLimitError as e:
                    last_error = e
                    info = parse_rate_limit(str(e))
                    if info["is_tpd"]:
                        # 429 TPD diario: 1 intento, sin esperas futiles
                        # (el backoff 5/10/20s nunca alcanza 9-36 min de cuota)
                        self.tpd_blocked = True
                        self._tpd_message = blocked_message(info, self.model_id)
                        print(self._tpd_message)
                        return {"text": "", "tool_calls": [], "memory_used": False,
                                "tokens_used": 0, "error": self._tpd_message}
                    if retry < MAX_RETRIES:
                        # Transitorio: espera exacta si la API la indica (<=90s),
                        # si no el backoff original (paso 2 del plan)
                        wait = compute_wait(retry, info["retry_after_s"], BASE_WAIT_SECONDS)
                        print(f"[RATE LIMIT] Esperando {wait:g}s (intento {retry + 1}/{MAX_RETRIES})... ", end="", flush=True)
                        time.sleep(wait)
                    else:
                        print(f"[RATE LIMIT] Agotados {MAX_RETRIES} reintentos")
                        return {"text": "", "tool_calls": [], "memory_used": False,
                                "tokens_used": 0,
                                "error": f"[RATE LIMIT] {str(last_error)[:500]}"}
                except Exception as e:
                    error_str = str(e)
                    if "tool" in error_str.lower():
                        # Modelo no soporta tools, reintentar sin tools
                        try:
                            response = client.chat.completions.create(
                                model=self.model_id,
                                messages=messages,
                                temperature=0.1,
                                max_tokens=800,
                                timeout=60
                            )
                            usage = getattr(response, 'usage', None)
                            if usage:
                                tokens_from_api += getattr(usage, 'total_tokens', 0)
                            text = response.choices[0].message.content or ""
                            tokens_estimated = len(text) // 4
                            return {"text": text,
                                    "tool_calls": [], "memory_used": False,
                                    "tokens_used": tokens_from_api or tokens_estimated,
                                    "error": None}
                        except Exception as e2:
                            return {"text": "", "tool_calls": [], "memory_used": False,
                                    "tokens_used": 0,
                                    "error": f"[ERROR] {str(e2)[:500]}"}
                    return {"text": "", "tool_calls": [], "memory_used": False,
                            "tokens_used": 0,
                            "error": f"[ERROR] {error_str[:500]}"}

            if response is None:
                return {"text": "", "tool_calls": [], "memory_used": False,
                        "tokens_used": 0,
                        "error": f"[ERROR] No response after retries"}

            message = response.choices[0].message

            # Si no hay tool_calls, retornar respuesta final
            if not message.tool_calls:
                text = message.content or ""
                tokens_estimated = len(text) // 4
                return {"text": text,
                        "tool_calls": all_tool_calls,
                        "memory_used": memory_used,
                        "tokens_used": tokens_from_api or tokens_estimated,
                        "error": None}

            # Procesar tool_calls
            messages.append(message)

            for tool_call in message.tool_calls:
                api_name = tool_call.function.name
                mcp_name = self.name_map.get(api_name, api_name)
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                # Ejecutar tool via MCP (mismo camino que OpenCode)
                try:
                    tool_result = self.mcp.call_tool(mcp_name, args)
                    success = True
                except Exception as e:
                    tool_result = f"ERROR: {e}"
                    success = False

                if "memory" in api_name.lower():
                    memory_used = True

                all_tool_calls.append({
                    "name": api_name,
                    "arguments": args,
                    "success": success,
                    "result": str(tool_result)[:500]
                })

                # Agregar resultado al historial
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_result)
                })

        # Si llegamos aqui, agotamos los rounds
        return {"text": "[ERROR] Max tool rounds exceeded",
                "tool_calls": all_tool_calls, "memory_used": memory_used,
                "tokens_used": tokens_from_api,
                "error": "[ERROR] Max tool rounds exceeded"}

    def close(self):
        """Cierra la conexión MCP."""
        if self.mcp:
            self.mcp.close()
            self.mcp = None


def create_runner(model_id, mode="api"):
    """Factory para crear el runner apropiado."""
    if mode == "native":
        return OpenCodeRunner(model_id)
    else:
        return GroqRunner(model_id)
