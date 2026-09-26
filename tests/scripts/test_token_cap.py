#!/usr/bin/env python3
"""
Tests del techo de tokens por test en GroqRunner (tarea 16C).

D8-qwen quemo ~28k tokens en un solo test con un loop improductivo
(run_command -> command_status). El runner debe abortar el loop al superar
MAX_TOKENS_PER_TEST con TIMEOUT explicito (no ERROR generico).

Todo con fakes (sin API ni MCP reales). Ejecutar:
  python tests/scripts/test_token_cap.py
"""

import json
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))


# ---- Fakes de OpenAI ----
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
    def __init__(self, tool_names=None, content="done", total_tokens=0):
        self.choices = [types.SimpleNamespace(message=FakeMessage(tool_names, content))]
        self.usage = types.SimpleNamespace(total_tokens=total_tokens)


class FakeCompletions:
    def __init__(self, script):
        self.script = list(script)  # [(tool_names|None, tokens), ...]
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        tool_names, tokens = self.script.pop(0) if self.script else (None, 0)
        content = "final" if tool_names is None else ""
        return FakeResponse(tool_names, content, tokens)


class FakeChat:
    def __init__(self, script):
        self.completions = FakeCompletions(script)


class FakeOpenAI:
    last_instance = None

    def __init__(self, *args, **kwargs):
        FakeOpenAI.last_instance = self
        # script global seteado por el test antes de cada corrida
        self.chat = FakeChat(FakeOpenAI.script)

    script = []


class FakeMCP:
    def call_tool(self, name, args):
        return "ok"


def _install_fake_openai():
    mod = types.ModuleType("openai")

    class RateLimitError(Exception):
        pass

    mod.OpenAI = FakeOpenAI
    mod.RateLimitError = RateLimitError
    sys.modules["openai"] = mod


_install_fake_openai()

os.environ["GROQ_API_KEY"] = "test-key-sin-uso"

from model_runner import GroqRunner, MAX_TOKENS_PER_TEST  # noqa: E402


def _make_runner(script, **kwargs):
    FakeOpenAI.script = list(script)
    r = GroqRunner("fake-model", **kwargs)
    r._ensure_mcp = lambda: True  # sin bridge real
    r.mcp_available = True
    r.tools = [{"type": "function", "function": {"name": "dummy"}}]
    r.name_map = {"dummy": "dummy"}
    r.mcp = FakeMCP()
    return r


class TestTokenCap(unittest.TestCase):

    def test_aborta_loop_improductivo_con_timeout_explicito(self):
        # 9000 tokens/round: r0->9000, r1->18000, r2 aborta antes de llamar
        script = [(["dummy"], 9000)] * 5
        r = _make_runner(script)
        res = r._execute_query("hola")
        self.assertIn("TIMEOUT", res["error"])
        self.assertIn("Tope de tokens", res["error"])
        self.assertGreaterEqual(res["tokens_used"], MAX_TOKENS_PER_TEST)
        self.assertEqual(FakeOpenAI.last_instance.chat.completions.calls, 2)

    def test_d8_historico_habria_cortado_antes(self):
        # D8-qwen real: ~5.5k/round x5 = 27325. Con techo corta en ~16.5k.
        script = [(["dummy"], 5500)] * 5
        r = _make_runner(script)
        res = r._execute_query("hola")
        self.assertIn("TIMEOUT", res["error"])
        self.assertLess(res["tokens_used"], 27325)
        self.assertGreaterEqual(res["tokens_used"], MAX_TOKENS_PER_TEST)

    def test_bajo_el_tope_completa_normal(self):
        script = [(["dummy"], 3000), (None, 500)]
        r = _make_runner(script)
        res = r._execute_query("hola")
        self.assertIsNone(res["error"])
        self.assertEqual(res["text"], "final")

    def test_tope_configurable(self):
        script = [(["dummy"], 6000)] * 5
        r = _make_runner(script, max_tokens_per_test=5000)
        res = r._execute_query("hola")
        self.assertIn("TIMEOUT", res["error"])
        self.assertEqual(FakeOpenAI.last_instance.chat.completions.calls, 1)


if __name__ == "__main__":
    unittest.main()
