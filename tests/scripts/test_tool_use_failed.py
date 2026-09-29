#!/usr/bin/env python3
"""Tests del manejo del 400 tool_use_failed en GroqRunner (tarea 16H).

D2 gpt-oss (suite 28/09) fallo con 400:
  "Tool choice is none, but model called a tool" / "attempted to call tool
  'brain_ai_memory_save' which was not in request.tools" (code=tool_use_failed)

Causa raiz (reproducida 28/09 14:42): el bridge MCP expone memory_* pero
los .ai/ le piden al modelo brain_ai_memory_* / brain-ai_memory_*. Groq
rechaza el tool call cuando el modelo obedece el prompt.

Tarea 16J: el fix definitivo no son alias, es publicar cada tool con el
nombre que OpenCode registra (<server_name>_<tool_name>), leido de
opencode.json. Ver mcp_client.discover_server_name.

Comportamiento esperado:
- mcp_tools_to_openai publica una tool por nombre real (brain-ai_memory_save
  -> memory_save en el bridge), sin duplicados,
- el round usa el techo historico de 800,
- "not in request.tools" -> error explicito con el nombre intentado, sin
  reintento inutil,
- otro tool_use_failed -> un reintento con mas techo,
- el fallback "modelo sin tools" sigue intacto.

Los fixtures del 400 conservan el nombre con underscore a proposito: es lo
que llamaria un modelo que copio la documentacion vieja, y ese es
exactamente el escenario que debe reportar error explicito.

Todo con fakes (sin API ni MCP). Ejecutar:
  python tests/scripts/test_tool_use_failed.py -v
"""

import json
import os
import shutil
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))


# ---- Fakes de OpenAI con guion de llamadas ----
class FakeFunction:
    def __init__(self, name, arguments="{}", call_id="call_1"):
        self.name = name
        self.arguments = arguments
        self.id = call_id


class FakeMessage:
    def __init__(self, tool_names=None, content="done"):
        self.content = content if not tool_names else None
        self.tool_calls = [types.SimpleNamespace(
            function=FakeFunction(n), id=f"call_{i}")
            for i, n in enumerate(tool_names or [])]


class FakeResponse:
    def __init__(self, tool_names=None, content="done", total_tokens=100):
        self.choices = [types.SimpleNamespace(
            message=FakeMessage(tool_names, content),
            finish_reason="stop")]
        self.usage = types.SimpleNamespace(total_tokens=total_tokens)


class ScriptedCompletions:
    """Pasos: ("raise", msg) | ("tool", [names]) | ("text", content)."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.script:
            return FakeResponse(None, "final")
        step = self.script.pop(0)
        if step[0] == "raise":
            raise Exception(step[1])
        if step[0] == "tool":
            return FakeResponse(step[1], "")
        return FakeResponse(None, step[1])


class FakeChat:
    def __init__(self, script):
        self.completions = ScriptedCompletions(script)


class FakeOpenAI:
    last_instance = None
    script = []

    def __init__(self, *args, **kwargs):
        FakeOpenAI.last_instance = self
        self.chat = FakeChat(FakeOpenAI.script)


class FakeMCP:
    def call_tool(self, name, args):
        return "ok guardado"


def _install_fake_openai():
    mod = types.ModuleType("openai")

    class RateLimitError(Exception):
        pass

    mod.OpenAI = FakeOpenAI
    mod.RateLimitError = RateLimitError
    sys.modules["openai"] = mod


_install_fake_openai()
os.environ["GROQ_API_KEY"] = "test-key-sin-uso"

from model_runner import (  # noqa: E402
    GroqRunner,
    PLAIN_ROUND_MAX_TOKENS,
    TOOL_USE_FAILED_RETRY_MAX_TOKENS,
    _attempted_tool_name,
    _failed_generation_len,
    _is_tool_use_failed,
    _tool_not_in_request,
)
from mcp_client import (  # noqa: E402
    DEFAULT_SERVER_NAME,
    discover_server_name,
    mcp_tools_to_openai,
)

# Error 400 real del reporte 28/09. openai arma el mensaje como
# "Error code: 400 - " + str(dict): se construye igual para que
# ast.literal_eval (diagnostico del runner) pueda parsearlo.
FAILED_GENERATION = ('{"name": "brain_ai_memory_save", "arguments": '
                     '{"project":"test-ai-config","decision":"Implementacion"')


def _error_400(message, code=None, generation=None):
    error = {"message": message, "type": "invalid_request_error"}
    if code:
        error["code"] = code
    if generation is not None:
        error["failed_generation"] = generation
    return "Error code: 400 - " + str({"error": error})


NOT_IN_TOOLS_400 = _error_400(
    "Tool call validation failed: attempted to call tool "
    "'brain_ai_memory_save' which was not in request.tools",
    code="tool_use_failed", generation=FAILED_GENERATION)

TRUNCATED_400 = _error_400(
    "Tool choice is none, but model called a tool",
    code="tool_use_failed", generation=FAILED_GENERATION)

NO_TOOLS_400 = _error_400("This model does not support tool calling")


def _make_runner(script, **kwargs):
    FakeOpenAI.script = list(script)
    r = GroqRunner("fake-model", **kwargs)
    r._ensure_mcp = lambda: True
    r.mcp_available = True
    r.tools = [{"type": "function",
                "function": {"name": "brain-ai_memory_save"}}]
    r.name_map = {"brain-ai_memory_save": "memory_save"}
    r.mcp = FakeMCP()
    return r


def _calls():
    return FakeOpenAI.last_instance.chat.completions.calls


class TestNombreUnicoPorTool(unittest.TestCase):
    """16J: cada tool se publica con el nombre que OpenCode registra."""

    MEMORY_SAVE = {"name": "memory_save", "description": "d",
                   "inputSchema": {"type": "object"}}

    def test_memory_save_se_publica_una_sola_vez_con_el_prefijo(self):
        tools, name_map = mcp_tools_to_openai([self.MEMORY_SAVE],
                                              server_name="brain-ai")
        self.assertEqual([t["function"]["name"] for t in tools],
                         ["brain-ai_memory_save"])
        self.assertEqual(name_map, {"brain-ai_memory_save": "memory_save"})

    def test_todas_las_tools_se_prefijan_no_solo_las_de_memoria(self):
        tools, name_map = mcp_tools_to_openai(
            [self.MEMORY_SAVE,
             {"name": "run_command", "description": "",
              "inputSchema": {"type": "object"}},
             {"name": "test_status", "description": "",
              "inputSchema": {"type": "object"}}],
            server_name="brain-ai")
        self.assertEqual([t["function"]["name"] for t in tools],
                         ["brain-ai_memory_save", "brain-ai_run_command",
                          "brain-ai_test_status"])
        self.assertEqual(name_map["brain-ai_run_command"], "run_command")
        self.assertEqual(len(name_map), 3, "sin alias duplicados")

    def test_server_name_explicito_cambia_el_prefijo(self):
        tools, _ = mcp_tools_to_openai([self.MEMORY_SAVE],
                                       server_name="otro-server")
        self.assertEqual([t["function"]["name"] for t in tools],
                         ["otro-server_memory_save"])

    def test_nombre_registrado_por_el_servidor_se_conserva(self):
        tools, _ = mcp_tools_to_openai(
            [{"name": "resolver_referencia", "description": "d",
              "inputSchema": {"type": "object"}}],
            server_name="brain-ai")
        self.assertEqual([t["function"]["name"] for t in tools],
                         ["brain-ai_resolver_referencia"])

    def test_conserva_descripcion_y_schema(self):
        tools, _ = mcp_tools_to_openai(
            [{"name": "memory_search", "description": "busca",
              "inputSchema": {"type": "object", "properties": {"q": {}}}}],
            server_name="brain-ai")
        for tool in tools:
            self.assertEqual(tool["function"]["description"], "busca")
            self.assertIn("properties", tool["function"]["parameters"])


class TestDiscoverServerName(unittest.TestCase):
    """16J: el server name sale de opencode.json, no esta hardcodeado."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write(self, root, config):
        os.makedirs(root, exist_ok=True)
        with open(os.path.join(root, "opencode.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(config, fh)
        return root

    def test_lee_el_server_que_apunta_al_bridge(self):
        root = self._write(self.tmp, {"mcp": {
            "git_publisher": {"command": ["python", "git_tool.py"]},
            "brain-ai": {"command": ["python", "brain-ai-01/mcp_bridge.py"]},
        }})
        self.assertEqual(discover_server_name(root, root), "brain-ai")

    def test_el_test_project_tiene_prioridad_sobre_el_project_root(self):
        test_project = self._write(os.path.join(self.tmp, "test"), {"mcp": {
            "brain-ai": {"command": ["python", "mcp_bridge.py"]}}})
        project_root = self._write(os.path.join(self.tmp, "root"), {"mcp": {
            "otro": {"command": ["python", "mcp_bridge.py"]}}})
        self.assertEqual(discover_server_name(test_project, project_root),
                         "brain-ai")

    def test_fallback_si_no_hay_config(self):
        vacio = os.path.join(self.tmp, "vacio")
        os.makedirs(vacio)
        self.assertEqual(discover_server_name(vacio, vacio),
                         DEFAULT_SERVER_NAME)

    def test_config_invalido_o_sin_seccion_mcp_no_revienta(self):
        for config in ("{no es json", {"model": "x"}, {"mcp": {}},
                       {"mcp": {"a": {"command": ["otro.py"]},
                                "b": {"command": ["otro2.py"]}}}):
            root = os.path.join(self.tmp, f"caso{abs(hash(str(config)))}")
            os.makedirs(root, exist_ok=True)
            with open(os.path.join(root, "opencode.json"), "w",
                      encoding="utf-8") as fh:
                fh.write(config if isinstance(config, str) else json.dumps(config))
            self.assertEqual(discover_server_name(root, root),
                             DEFAULT_SERVER_NAME, config)

    def test_un_solo_server_se_acepta_sin_reconocer_el_bridge(self):
        root = self._write(os.path.join(self.tmp, "solo"), {"mcp": {
            "memoria": {"command": ["python", "otro_servidor.py"]}}})
        self.assertEqual(discover_server_name(root, root), "memoria")

    def test_el_proyecto_real_declara_brain_ai(self):
        self.assertEqual(discover_server_name(), "brain-ai")


class TestToolUseFailed(unittest.TestCase):

    def test_round_usa_techo_historico(self):
        _make_runner([("text", "hola")])._execute_query("p")
        self.assertEqual(_calls()[0]["max_tokens"], PLAIN_ROUND_MAX_TOKENS)
        self.assertIn("tools", _calls()[0])

    def test_not_in_request_tools_da_error_explicito_sin_reintento(self):
        r = _make_runner([("raise", NOT_IN_TOOLS_400)])
        res = r._execute_query("implementa y guarda")
        self.assertIn("no estaba en request.tools", res["error"])
        self.assertIn("brain_ai_memory_save", res["error"])
        self.assertEqual(len(_calls()), 1, "no debe reintentar este 400")

    def test_tool_use_failed_generico_reintenta_con_mas_techo(self):
        r = _make_runner([
            ("raise", TRUNCATED_400),
            ("tool", ["brain-ai_memory_save"]),
            ("text", "Decision guardada."),
        ])
        res = r._execute_query("implementa y guarda")
        self.assertIsNone(res["error"])
        self.assertEqual(len(res["tool_calls"]), 1)
        self.assertTrue(res["memory_used"])
        calls = _calls()
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0]["max_tokens"], PLAIN_ROUND_MAX_TOKENS)
        self.assertEqual(calls[1]["max_tokens"], TOOL_USE_FAILED_RETRY_MAX_TOKENS)
        for call in calls[:2]:
            self.assertIn("tools", call, "el retry no debe quitar las tools")

    def test_doble_tool_use_failed_generico_da_error_explicito(self):
        r = _make_runner([("raise", TRUNCATED_400)] * 2)
        res = r._execute_query("implementa y guarda")
        self.assertIn("Tool call rechazada tras retry", res["error"])
        self.assertIn(str(TOOL_USE_FAILED_RETRY_MAX_TOKENS), res["error"])
        for call in _calls():
            self.assertIn("tools", call)

    def test_error_de_modelo_sin_tools_sigue_usando_el_fallback(self):
        r = _make_runner([("raise", NO_TOOLS_400), ("text", "respuesta")])
        res = r._execute_query("p")
        self.assertIsNone(res["error"])
        self.assertEqual(res["text"], "respuesta")
        self.assertNotIn("tools", _calls()[1])

    def test_helpers_clasifican_los_errores(self):
        self.assertTrue(_is_tool_use_failed(NOT_IN_TOOLS_400))
        self.assertTrue(_tool_not_in_request(NOT_IN_TOOLS_400))
        self.assertFalse(_tool_not_in_request(TRUNCATED_400))
        self.assertFalse(_is_tool_use_failed(NO_TOOLS_400))
        self.assertFalse(_is_tool_use_failed("[RATE LIMIT] 429"))

    def test_extraccion_de_nombre_y_largo_del_failed_generation(self):
        self.assertEqual(_attempted_tool_name(NOT_IN_TOOLS_400),
                         "brain_ai_memory_save")
        self.assertEqual(_failed_generation_len(NOT_IN_TOOLS_400),
                         len(FAILED_GENERATION))
        self.assertEqual(_attempted_tool_name(NO_TOOLS_400), "")
        self.assertEqual(_failed_generation_len(NO_TOOLS_400), -1)


if __name__ == "__main__":
    unittest.main()
