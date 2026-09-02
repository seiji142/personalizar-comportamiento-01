#!/usr/bin/env python3
"""
Adaptadores de modelo para la suite de tests.

Proporciona una interfaz comun (ModelRunner) para ejecutar modelos
tanto via OpenCode nativo como via API directa (Groq).

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
import socket
import subprocess
import sys
import time

from brain_ai_client import execute_tool, TOOLS_SCHEMA


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OPENCODE_CLI = os.path.join(os.environ.get("LOCALAPPDATA", ""), "opencode", "opencode-cli.exe")


def _load_system_prompt():
    """Carga el system prompt de .ai/."""
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

    def query(self, prompt, tools=None):
        """
        Ejecuta una consulta contra el modelo.

        Returns:
            dict: {text, tool_calls, memory_used, error}
        """
        raise NotImplementedError


class OpenCodeRunner(ModelRunner):
    """Ejecuta modelos nativos via OpenCode server."""

    def __init__(self, model_id, server_port, system_prompt=None):
        super().__init__(model_id, system_prompt)
        self.server_port = server_port

    def query(self, prompt, tools=None):
        """OpenCode maneja MCP via opencode.json. Solo capturamos la respuesta."""
        cmd = [
            OPENCODE_CLI, "run",
            "--attach", f"http://127.0.0.1:{self.server_port}",
            "--model", self.model_id,
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
                env=env, timeout=120
            )
            text = _parse_opencode_response(result.stdout)
            if not text and result.stderr.strip():
                return {"text": "", "tool_calls": [], "memory_used": False,
                        "error": f"[ERROR] {result.stderr.strip()[:500]}"}

            # OpenCode no expone tool_calls en la salida JSON,
            # pero si la respuesta menciona memoria, asumimos que la uso
            memory_used = any(kw in text.lower() for kw in ["memoria", "episodio", "decisión", "busqué", "encontré"])

            return {"text": text, "tool_calls": [], "memory_used": memory_used, "error": None}

        except subprocess.TimeoutExpired:
            return {"text": "", "tool_calls": [], "memory_used": False, "error": "[TIMEOUT]"}
        except Exception as e:
            return {"text": "", "tool_calls": [], "memory_used": False, "error": f"[ERROR] {str(e)}"}


class GroqRunner(ModelRunner):
    """Ejecuta modelos via Groq API con tool calling."""

    def __init__(self, model_id, system_prompt=None, max_tool_rounds=3):
        super().__init__(model_id, system_prompt)
        self.max_tool_rounds = max_tool_rounds

    def query(self, prompt, tools=None):
        """Ejecuta con tool loop: prompt → tool_call → execute → respuesta final."""
        try:
            from openai import OpenAI
        except ImportError:
            return {"text": "", "tool_calls": [], "memory_used": False,
                    "error": "[ERROR] openai package not installed"}

        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        api_key = os.getenv("LLM_API_KEY", "") or os.getenv("GROQ_API_KEY", "")

        if not api_key:
            return {"text": "", "tool_calls": [], "memory_used": False,
                    "error": "[ERROR] No GROQ_API_KEY configured"}

        client = OpenAI(base_url=base_url, api_key=api_key)
        use_tools = tools or TOOLS_SCHEMA

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        all_tool_calls = []
        memory_used = False

        for round_num in range(self.max_tool_rounds):
            try:
                response = client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    tools=use_tools,
                    tool_choice="auto",
                    temperature=0.1,
                    max_tokens=800,
                    timeout=60
                )
            except Exception as e:
                error_str = str(e)
                if "tool" in error_str.lower():
                    # Modelo no soporta tools, reintentar sin tools
                    response = client.chat.completions.create(
                        model=self.model_id,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=800,
                        timeout=60
                    )
                    return {"text": response.choices[0].message.content or "",
                            "tool_calls": [], "memory_used": False, "error": None}
                return {"text": "", "tool_calls": [], "memory_used": False,
                        "error": f"[ERROR] {error_str[:500]}"}

            message = response.choices[0].message

            # Si no hay tool_calls, retornar respuesta final
            if not message.tool_calls:
                return {"text": message.content or "",
                        "tool_calls": all_tool_calls,
                        "memory_used": memory_used,
                        "error": None}

            # Procesar tool_calls
            messages.append(message)

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                # Ejecutar tool
                result = execute_tool(func_name, args)
                success = result.get("ok", False)

                if "memory" in func_name.lower():
                    memory_used = True

                all_tool_calls.append({
                    "name": func_name,
                    "arguments": args,
                    "success": success
                })

                # Agregar resultado al historial
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        # Si llegamos aqui, agotamos los rounds
        return {"text": "[ERROR] Max tool rounds exceeded",
                "tool_calls": all_tool_calls, "memory_used": memory_used,
                "error": "[ERROR] Max tool rounds exceeded"}


def create_runner(model_id, mode="api", server_port=None):
    """Factory para crear el runner apropiado."""
    if mode == "native":
        return OpenCodeRunner(model_id, server_port)
    else:
        return GroqRunner(model_id)
